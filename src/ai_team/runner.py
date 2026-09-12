from datetime import datetime
from contextvars import ContextVar
from fnmatch import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import uuid

from .utils import run, which, load_json, save_json, ensure_git_repo, safe_slug, sha256_file, project_path
from .config import load_config, DEFAULT_POLICY

_deadline = ContextVar('deadline', default=None)
_agent_timeout = ContextVar('agent_timeout', default=3600)

_SECRET_RE = re.compile(r'(KEY|TOKEN|SECRET|PASSWORD|PASS|COOKIE|CREDENTIAL)', re.I)


def _sanitized_env():
    """Strip secret-looking environment variables before spawning any subprocess."""
    env = {k: v for k, v in os.environ.items() if not _SECRET_RE.search(k)}
    env['AI_TEAM_SUBPROCESS'] = '1'
    return env


def _capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
    out.parent.mkdir(parents=True, exist_ok=True)
    seconds = timeout or _agent_timeout.get()
    deadline = _deadline.get()
    if deadline is not None:
        seconds = min(seconds, deadline - time.monotonic())
    if seconds <= 0:
        raise RuntimeError('Run timeout exceeded')
    try:
        with out.open('w', encoding='utf-8') as fo, err.open('w', encoding='utf-8') as fe:
            p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=fo, stderr=fe, timeout=seconds,
                                env=_sanitized_env(), start_new_session=(sys.platform != 'win32'))
    except subprocess.TimeoutExpired as exc:
        with err.open('a', encoding='utf-8') as fe:
            fe.write(f'Command timeout after {seconds}s: {exc}\n')
        raise RuntimeError(f'Command timeout. Log: {err}') from exc
    if p.returncode and not allow_failure:
        raise RuntimeError(f'Command exited {p.returncode}. Log: {err}')
    return p.returncode


def _git(project, *args, check=True):
    return run(['git', *args], cwd=project, capture=True, check=check)


def _read(path):
    return path.read_text(encoding='utf-8') if path.exists() else ''


def _agy(config, prompt, agent, effort):
    ac = config.get('antigravity', {})
    cmd = ['agy', '-p', prompt, '--agent', agent, '--output-format', 'text']
    model = config.get('models', {}).get('agy') or ac.get('model')
    if model:
        cmd += ['--model', model]
    if effort:
        cmd += ['--effort', effort]
    if ac.get('sandbox', True):
        cmd += ['--sandbox']
    if ac.get('fullAuto', False):
        cmd += ['--dangerously-skip-permissions']
    cmd += ['--print-timeout', str(ac.get('printTimeout', '60m'))]
    return cmd


def _command(config, provider, prompt, role, readonly=False, output=None):
    prompt = ('Read AI_TEAM.md and PROJECT_CONTEXT.md and relevant project skills. '
              f'Your role is {role}. Do not push, merge or deploy.\n' + prompt)
    if provider == 'agy':
        cmd = _agy(config, prompt, role, 'low' if role == 'triage' else 'high')
        if readonly:
            cmd = [x for x in cmd if x != '--dangerously-skip-permissions']
            if '--sandbox' not in cmd:
                cmd.append('--sandbox')
            cmd += ['--mode', 'plan']
        return cmd
    if provider == 'codex':
        cmd = ['codex', 'exec', '--ephemeral', '--sandbox', 'read-only' if readonly else 'workspace-write']
        if output is not None:
            cmd += ['--output-last-message', str(output)]
        cmd += [prompt]
    else:
        cmd = ['claude', '-p', prompt, '--permission-mode', 'plan' if readonly else 'default',
               '--output-format', 'text', '--max-turns', '30']
    model = config.get('models', {}).get(provider)
    if model:
        cmd += ['--model', model]
    return cmd


def _snapshot(project):
    """Include new files; exclude ignored runtime artifacts."""
    names = _git(project, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').stdout.split('\0')
    result = {}
    for name in names:
        if not name or name.startswith('.ai/runs/') or name == '.ai/latest.txt':
            continue
        path = project_path(project, name)
        result[name] = sha256_file(path) if path.is_file() else None
    return result


def _ask(config, project, rd, provider, prompt, role, filename, readonly=False):
    out = rd / filename
    if out.exists():
        # Resuming a run: a cached answer means this stage already completed.
        return _read(out)
    before = _snapshot(project) if readonly else None
    final = rd / (filename + '.answer') if provider == 'codex' else None
    _capture(_command(config, provider, prompt, role, readonly, final), project,
             out, rd / (filename + '.stderr'))
    if final is not None:
        if not final.exists():
            raise RuntimeError(f'Missing final answer: {final}')
        out.write_text(_read(final), encoding='utf-8')
    if readonly and before != _snapshot(project):
        raise RuntimeError(f'Read-only stage {role} modified project files')
    return _read(out)


def _result(text, key, allowed):
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f'Expected a JSON object with {key}') from exc
    if not isinstance(data, dict) or not isinstance(data.get(key), str) or data[key] not in allowed:
        raise RuntimeError(f'Invalid {key} in structured result')
    if key == 'verdict':
        if not isinstance(data.get('unresolved'), list) or not isinstance(data.get('summary'), str):
            raise RuntimeError('Verdict requires unresolved array and summary string')
        if data['unresolved'] and data['verdict'] != 'CHANGES_REQUIRED':
            raise RuntimeError('Passing verdict cannot contain unresolved findings')
    return data


def _risk(project, base, initial, config):
    names = set(_git(project, 'diff', '--name-only', base).stdout.splitlines())
    names.update(_git(project, 'ls-files', '--others', '--exclude-standard').stdout.splitlines())
    levels = ['LOW', 'MEDIUM', 'HIGH']
    level = levels.index(initial)
    if len(names) > 1:
        level = max(level, 1)
    patterns = {'HIGH': ['*auth*', '*secret*', '*migration*', '*.tf', '*Dockerfile*',
                         '.github/workflows/*', '*payment*', '*permission*', '*schema*']}
    for risk, globs in config.get('riskPaths', {}).items():
        patterns.setdefault(risk, []).extend(globs)
    for risk, globs in patterns.items():
        if any(fnmatch(name.lower(), pattern.lower()) for name in names for pattern in globs):
            level = max(level, levels.index(risk))
    return levels[level]


def doctor(project, probe=False):
    """Static readiness; optional help probes do not claim authentication success."""
    problems = []
    try:
        project = ensure_git_repo(project.resolve())
        config = load_config(project)
    except Exception as exc:
        print(f'[FAIL] {exc}')
        return 1
    required = {'git', config.get('primaryProvider', 'agy')}
    for reviewers in config.get('reviewPolicy', DEFAULT_POLICY).values():
        required.update(reviewers)
    for name in sorted(required):
        executable = which(name)
        print(f"[{'OK' if executable else 'FAIL'}] {name}: {executable or 'missing'}")
        if not executable:
            problems.append(name)
        elif probe:
            try:
                p = subprocess.run([name, '--help'], cwd=str(project), capture_output=True, text=True, timeout=15)
                if p.returncode:
                    problems.append(f'{name} --help failed')
            except (OSError, subprocess.TimeoutExpired) as exc:
                problems.append(f'{name}: {exc}')
    try:
        state = load_json(project / '.ai-team/state.json')
        if state.get('conflicts'):
            problems.append('Unresolved installation conflicts: ' + ', '.join(state['conflicts']))
    except (OSError, ValueError, AttributeError):
        problems.append('Missing or invalid installation state')
    if not (project / 'PROJECT_CONTEXT.md').is_file():
        problems.append('Missing PROJECT_CONTEXT.md')
    verification = config.get('verification', {})
    if not verification.get('commands') and not verification.get('noChecksReason', '').strip():
        problems.append('Configure verification.commands or an explicit noChecksReason')
    if config.get('requireCleanWorkingTree', True) and _git(project, 'status', '--porcelain').stdout.strip():
        problems.append('Working tree is not clean; review and commit setup before run')
    if _git(project, 'rev-parse', '--verify', 'HEAD', check=False).returncode:
        problems.append('Repository needs an initial commit')
    for problem in problems:
        print('[FAIL]', problem)
    print('[UNVERIFIED] Model availability and authentication require an interactive provider check.')
    return 1 if problems else 0


VERDICT_PROMPT = ('Return ONLY JSON: {"verdict":"PASS|PASS_WITH_NOTES|CHANGES_REQUIRED",'
                  '"unresolved":[],"summary":"evidence and reasoning"}. '
                  'List unresolved blocking/high findings in unresolved. No markdown fences.')


def _execute(project, config, rd, run_id, base, branch, user_prompt, primary, verification):
    report = {'runId': run_id, 'base': base, 'branch': branch, 'status': 'RUNNING', 'reviews': [], 'checks': []}
    token = _deadline.set(time.monotonic() + config.get('runTimeoutSeconds', 14400))
    timeout_token = _agent_timeout.set(config.get('agentTimeoutSeconds', 3600))
    save_json(rd / 'result.json', report)
    try:
        context = f'USER TASK:\n{user_prompt}\nBASE REF: {base}\n'
        triage = _ask(config, project, rd, primary, context +
                      'Analyze risk without edits. Return ONLY JSON: {"risk":"LOW|MEDIUM|HIGH"}.',
                      'triage', 'triage.json', True)
        risk = _result(triage, 'risk', {'LOW', 'MEDIUM', 'HIGH'})['risk']

        def require_reviewers(level):
            reviewers = config.get('reviewPolicy', DEFAULT_POLICY)[level]
            missing = [x for x in reviewers if not which(x)]
            if missing:
                raise RuntimeError('Required reviewers missing: ' + ', '.join(missing))
            return reviewers

        require_reviewers(risk)
        _ask(config, project, rd, primary, context + f'RISK: {risk}\nImplement and test. '
             'For LOW use a minimal workflow; delegate only when complexity warrants it. '
             'External reviews are handled by the dispatcher.', 'orchestrator', 'primary.md')
        for round_number in range(1, config.get('maxReviewRounds', 2) + 1):
            risk = _risk(project, base, risk, config)
            report['risk'] = risk
            reviewers = require_reviewers(risk)
            reviews = []
            before = _snapshot(project)
            for reviewer in reviewers:
                filename = f'review-{round_number}-{reviewer}.json'
                text = _ask(config, project, rd, reviewer, context + f'RISK: {risk}\n'
                    'Independently review the current working tree including untracked files. '
                    'Do not read other review reports. Do not edit. ' + VERDICT_PROMPT,
                    'reviewer', filename, True)
                result = _result(text, 'verdict', {'PASS', 'PASS_WITH_NOTES', 'CHANGES_REQUIRED'})
                report['reviews'].append({'provider': reviewer, 'round': round_number, **result})
                reviews.append((filename, result))
            if not any(result['verdict'] == 'CHANGES_REQUIRED' for _, result in reviews):
                break
            if round_number == config.get('maxReviewRounds', 2):
                raise RuntimeError('Unresolved review findings; maxReviewRounds reached')
            _ask(config, project, rd, primary, context + 'Resolve review findings with evidence. Reports:\n' +
                 '\n'.join(str(rd / name) for name, _ in reviews), 'integrator', f'integration-{round_number}.md')
            if before == _snapshot(project):
                raise RuntimeError('Review findings remain unresolved; integrator made no changes')
        final = _ask(config, project, rd, primary, context +
                     'Verify the final requirement and diff without edits. The runner executes configured checks. ' +
                     VERDICT_PROMPT, 'verifier', 'final-verification.md', True)
        verdict = _result(final, 'verdict', {'PASS', 'PASS_WITH_NOTES', 'CHANGES_REQUIRED'})
        report['verification'] = verdict
        check_snapshot = _snapshot(project)
        for i, command in enumerate(verification.get('commands', [])):
            rc = _capture(command['argv'], project_path(project, command.get('cwd', '.')),
                          rd / f'check-{i}.stdout', rd / f'check-{i}.stderr', True,
                          timeout=command.get('timeoutSeconds', 300))
            report['checks'].append({'argv': command['argv'], 'cwd': command.get('cwd', '.'), 'exitCode': rc})
        if check_snapshot != _snapshot(project):
            raise RuntimeError('Verification commands changed project files; review changes before rerunning')
        if not report['checks']:
            report['noChecksReason'] = verification['noChecksReason']
        diff_check = _git(project, 'diff', '--check', base, check=False)
        (rd / 'final-diff-check.txt').write_text((diff_check.stdout or '') + (diff_check.stderr or ''), encoding='utf-8')
        report['diffCheckExitCode'] = diff_check.returncode
        if _git(project, 'branch', '--show-current').stdout.strip() != branch:
            raise RuntimeError('Agent changed the active branch')
        if verdict['verdict'] == 'CHANGES_REQUIRED' or diff_check.returncode or any(x['exitCode'] for x in report['checks']):
            report['status'] = 'CHANGES_REQUIRED'
            return 2
        report['status'] = 'PASS_WITH_NOTES' if not report['checks'] or verdict['verdict'] == 'PASS_WITH_NOTES' else 'PASS'
        return 0
    except Exception as exc:
        report['status'] = 'FAILED'
        report['error'] = str(exc)
        raise
    finally:
        save_json(rd / 'result.json', report)
        _deadline.reset(token)
        _agent_timeout.reset(timeout_token)
        print(f"Run: {run_id}\nBranch: {branch}\nStatus: {report['status']}\nReports: {rd}")


def run_team(project, user_prompt):
    project = ensure_git_repo(project.resolve())
    config = load_config(project)
    primary = config.get('primaryProvider', 'agy')
    if not which(primary):
        raise RuntimeError(f'Missing primary CLI: {primary}')
    state = load_json(project / '.ai-team/state.json')
    if state.get('conflicts'):
        raise RuntimeError('Resolve installation conflicts before running')
    if config.get('requireCleanWorkingTree', True) and _git(project, 'status', '--porcelain').stdout.strip():
        raise RuntimeError('Working tree nie jest czysty. Review and commit/stash your changes.')
    verification = config.get('verification', {})
    if not verification.get('commands') and not verification.get('noChecksReason', '').strip():
        raise RuntimeError('Configure verification.commands or explicit verification.noChecksReason')
    current = _git(project, 'branch', '--show-current').stdout.strip()
    if not current:
        raise RuntimeError('Detached HEAD')
    base = _git(project, 'rev-parse', 'HEAD').stdout.strip()
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + safe_slug(user_prompt) + '-' + uuid.uuid4().hex[:8]
    rd = project_path(project, '.ai/runs/' + run_id)
    rd.mkdir(parents=True, exist_ok=False)
    (rd / 'prompt.txt').write_text(user_prompt, encoding='utf-8')
    project_path(project, '.ai/latest.txt').write_text(run_id, encoding='utf-8')
    branch = current
    if config.get('createBranchForEachRun', True):
        branch = config.get('branchPrefix', 'ai/') + run_id
        _git(project, 'switch', '-c', branch)
    (rd / 'base-ref.txt').write_text(base, encoding='utf-8')
    (rd / 'branch.txt').write_text(branch, encoding='utf-8')
    return _execute(project, config, rd, run_id, base, branch, user_prompt, primary, verification)


def resume_team(project, run_id):
    project = ensure_git_repo(project.resolve())
    if run_id == 'latest':
        marker = project_path(project, '.ai/latest.txt')
        if not marker.exists():
            raise RuntimeError('No latest run recorded')
        run_id = _read(marker).strip()
    rd = project_path(project, '.ai/runs/' + run_id)
    prompt_file, branch_file, base_file = rd / 'prompt.txt', rd / 'branch.txt', rd / 'base-ref.txt'
    if not (rd.is_dir() and prompt_file.exists() and branch_file.exists() and base_file.exists()):
        raise RuntimeError(f'Cannot resume: run context is incomplete for {run_id}')
    branch, base = _read(branch_file).strip(), _read(base_file).strip()
    current = _git(project, 'branch', '--show-current').stdout.strip()
    if current != branch:
        raise RuntimeError(f'Unsafe branch context: expected {branch}, got {current}')
    config = load_config(project)
    primary = config.get('primaryProvider', 'agy')
    if not which(primary):
        raise RuntimeError(f'Missing primary CLI: {primary}')
    return _execute(project, config, rd, run_id, base, branch, _read(prompt_file), primary, config.get('verification', {}))
