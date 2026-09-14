from datetime import datetime
from contextvars import ContextVar
from fnmatch import fnmatch
from pathlib import Path
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

from .utils import run, which, load_json, save_json, ensure_git_repo, safe_slug, sha256_file, project_path
from .config import load_config, DEFAULT_POLICY, DEFAULT_PROTECTED_IGNORED, GUARDRAIL_FILES
from .repomap import generate_repomap

_deadline = ContextVar('deadline', default=None)
_agent_timeout = ContextVar('agent_timeout', default=3600)
_passthrough_env = ContextVar('passthrough_env', default=())
_protected_ignored = ContextVar('protected_ignored', default=DEFAULT_PROTECTED_IGNORED)

# Substrings and whole names that make a variable unsafe to hand to a model CLI. Connection
# strings and agent sockets carry credentials without ever spelling "secret".
_SECRET_RE = re.compile(
    r'(KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASS|COOKIE|CREDENTIAL|AUTH|PRIVATE|CERT|SALT|SIGNING'
    r'|SESSION|_DSN|_URI|_URL|(^|_)(PAT|DSN|JWT|SK|API)(_|$))', re.I)
_SECRET_NAMES = {'KUBECONFIG', 'AWS_PROFILE', 'AWS_CONFIG_FILE', 'DOCKER_CONFIG',
                 'GIT_ASKPASS', 'SSH_ASKPASS', 'NETRC', 'PGSERVICEFILE', 'PGPASSFILE'}
# Trust anchors are paths, not secrets; stripping them silently breaks TLS behind a proxy.
_ALWAYS_KEEP = {'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE',
                'NODE_EXTRA_CA_CERTS', 'PATH', 'SYSTEMROOT', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR'}
_NEW_GROUP = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0


def _sanitized_env(passthrough=None):
    """Strip secret-looking environment variables before spawning any subprocess."""
    allowed = set(passthrough if passthrough is not None else _passthrough_env.get())
    env = {k: v for k, v in os.environ.items()
           if k in allowed or k.upper() in _ALWAYS_KEEP
           or (k.upper() not in _SECRET_NAMES and not _SECRET_RE.search(k))}
    env['AI_TEAM_SUBPROCESS'] = '1'
    return env


def _terminate_tree(process):
    """Kill descendants too; an orphaned agent keeps writing to the repository."""
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(process.pid)],
                           capture_output=True, timeout=30)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        process.kill()


def _capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
    """Write the answer atomically: a stage file exists only if the stage really finished."""
    out.parent.mkdir(parents=True, exist_ok=True)
    seconds = timeout or _agent_timeout.get()
    deadline = _deadline.get()
    if deadline is not None:
        seconds = min(seconds, deadline - time.monotonic())
    if seconds <= 0:
        raise RuntimeError('Run timeout exceeded')
    partial = out.with_name(out.name + '.partial')
    failed = out.with_name(out.name + '.failed')
    try:
        with partial.open('w', encoding='utf-8') as fo, err.open('w', encoding='utf-8') as fe:
            process = subprocess.Popen(cmd, cwd=str(cwd), text=True, stdout=fo, stderr=fe,
                                       stdin=subprocess.DEVNULL,
                                       env=_sanitized_env(),
                                       start_new_session=(sys.platform != 'win32'),
                                       creationflags=_NEW_GROUP)
            try:
                code = process.wait(timeout=seconds)
            except subprocess.TimeoutExpired as exc:
                _terminate_tree(process)
                process.wait(timeout=30)
                with err.open('a', encoding='utf-8') as fe2:
                    fe2.write(f'Command timeout after {seconds}s: {exc}\n')
                raise RuntimeError(f'Command timeout after {seconds}s. '
                                   f'Partial output: {failed}. Log: {err}') from exc
        if code and not allow_failure:
            raise RuntimeError(f'Command exited {code}. Partial output: {failed}. Log: {err}')
        os.replace(partial, out)
        return code
    finally:
        if partial.exists():
            os.replace(partial, failed)


def _git(project, *args, check=True):
    return run(['git', *args], cwd=project, capture=True, check=check)


def _read(path):
    return path.read_text(encoding='utf-8') if path.exists() else ''


# Read-only stages are cheap by default; only the writing roles pay for maximum effort.
_EFFORT_KEYS = {'triage': ('triageEffort', 'low'), 'reviewer': ('verificationEffort', 'medium'),
                'verifier': ('verificationEffort', 'medium')}


def _effort(config, role):
    key, default = _EFFORT_KEYS.get(role, ('implementationEffort', 'high'))
    return config.get('antigravity', {}).get(key, default)


def _model(config, provider, role):
    value = config.get('models', {}).get(provider)
    if isinstance(value, dict):
        return value.get(role) or value.get('default')
    return value


def _provider_args(config, provider, role):
    roles = config.get('providerArgs', {}).get(provider, {})
    return list(roles.get(role, roles.get('default', [])))


def _apply_args(cmd, extra):
    """Configured arguments win over runner defaults for the same flag."""
    if not extra:
        return cmd
    valued = {extra[i] for i in range(len(extra) - 1)
              if extra[i].startswith('-') and not extra[i + 1].startswith('-')}
    bare = {x for x in extra if x.startswith('-')} - valued
    result, skip = [], False
    for item in cmd:
        if skip:
            skip = False
        elif item in valued:
            skip = True
        elif item not in bare:
            result.append(item)
    return result + list(extra)


def _agy(config, prompt, agent, effort):
    ac = config.get('antigravity', {})
    cmd = ['agy', '-p', prompt, '--agent', agent, '--output-format', 'text']
    model = _model(config, 'agy', agent) or ac.get('model')
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
    prompt = _text(config, 'role').format(role=role) + prompt
    if provider == 'agy':
        cmd = _agy(config, prompt, role, _effort(config, role))
        if readonly:
            cmd = [x for x in cmd if x != '--dangerously-skip-permissions']
            if '--sandbox' not in cmd:
                cmd.append('--sandbox')
            cmd += ['--mode', 'plan']
        return _apply_args(cmd, _provider_args(config, provider, role))
    if provider == 'codex':
        cmd = ['codex', 'exec', '--ephemeral', '--sandbox', 'read-only' if readonly else 'workspace-write']
        if output is not None:
            cmd += ['--output-last-message', str(output)]
        cmd += [prompt]
    else:
        perm = 'plan' if readonly else 'acceptEdits'
        cmd = ['claude', '-p', prompt, '--permission-mode', perm,
               '--output-format', 'text', '--max-turns', '30']
        if not readonly and (config.get('antigravity', {}).get('fullAuto', False) or config.get('fullAuto', False)):
            cmd.append('--dangerously-skip-permissions')
    model = _model(config, provider, role)
    if model:
        cmd += ['--model', model]
    return _apply_args(cmd, _provider_args(config, provider, role))


def _protected(name):
    lowered = name.lower()
    return any(fnmatch(lowered, glob.lower()) or fnmatch(Path(lowered).name, glob.lower())
               for glob in _protected_ignored.get())


def _snapshot(project):
    """Include new files and protected ignored files; exclude ignored runtime artifacts."""
    tracked = _git(project, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').stdout.split('\0')
    ignored = _git(project, 'ls-files', '-z', '--others', '--ignored', '--exclude-standard').stdout.split('\0')
    result = {}
    for name in list(tracked) + [x for x in ignored if x and _protected(x)]:
        if not name or name.startswith('.ai/runs/') or name.startswith('.ai/worktrees/') or name == '.ai/latest.txt' or name == '.ai/LEARNINGS.md':
            continue
        path = project_path(project, name)
        result[name] = sha256_file(path) if path.is_file() else None
    return result


def _run_snapshot(rd, own_prefix):
    """Guard the run directory itself: stage answers are the runner's cache, not model output."""
    return {p.name: sha256_file(p) for p in sorted(rd.iterdir())
            if p.is_file() and not p.name.startswith(own_prefix)}


def _skill_context(project, header='\n\nPROJECT SKILLS - apply these criteria:\n', task_prompt='', touched_files=None):
    """Reviewers must not depend on each CLI discovering skills on its own."""
    try:
        from .skills import filter_skills_for_task
        skill_paths = filter_skills_for_task(project, task_prompt, touched_files)
    except Exception:
        skill_paths = sorted(project.glob('.agents/skills/*/*/SKILL.md'))
    parts = [f'\n--- {p.relative_to(project).as_posix()} ---\n{_read(p)}'
             for p in skill_paths]
    text = ''.join(parts)
    if not text or len(text) > 20000:
        return ''
    return header + text


def _repomap_context(project, header='\n\nCODEBASE MAP (AST):\n'):
    """Inject concise AST summary of repository definitions into planning stages."""
    try:
        repomap = generate_repomap(project)
        if repomap and len(repomap) <= 25000:
            return header + repomap + '\n'
    except Exception:
        pass
    return ''


def _learnings_context(project, header='\n\nTEAM MEMORY & PAST LEARNINGS (avoid repeating these mistakes):\n'):
    """Inject accumulated review findings and lessons into stage prompts."""
    learnings_file = project_path(project, '.ai/LEARNINGS.md')
    if learnings_file.is_file():
        content = _read(learnings_file).strip()
        if content:
            lines = content.splitlines()
            if len(lines) > 50:
                content = '\n'.join(lines[-50:])
            return header + content + '\n'
    return ''


def _record_learnings(project, run_id, report):
    """Capture review findings and notes into .ai/LEARNINGS.md so future runs learn from them."""
    items = []
    for rev in report.get('reviews', []):
        for unf in rev.get('unresolved', []):
            if isinstance(unf, str) and unf.strip():
                items.append(f"- [{rev.get('provider', 'reviewer')}] {unf.strip()}")
            elif isinstance(unf, dict):
                msg = unf.get('finding') or unf.get('message') or unf.get('description') or str(unf)
                items.append(f"- [{rev.get('provider', 'reviewer')}] {msg}")
    if report.get('verification', {}).get('summary'):
        summary = report['verification']['summary']
        verdict = report['verification'].get('verdict', '')
        if verdict == 'PASS_WITH_NOTES':
            items.append(f"- [verification-notes] {summary}")
    if not items:
        return
    learnings_file = project_path(project, '.ai/LEARNINGS.md')
    learnings_file.parent.mkdir(parents=True, exist_ok=True)
    existing = _read(learnings_file) if learnings_file.exists() else '# AI Engineering Team - Learnings\n\n'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_entry = f"\n### Run `{run_id}` ({timestamp})\n" + '\n'.join(items) + '\n'
    learnings_file.write_text(existing + new_entry, encoding='utf-8')


def _ask(config, project, rd, provider, prompt, role, filename, readonly=False):
    out, done = rd / filename, rd / (filename + '.done')
    if out.exists() and done.exists():
        # Resuming a run: a completed stage is cached; a partial one is re-run.
        return _read(out)
    prompt += _learnings_context(project, _text(config, 'learnings'))
    if role in ('triage', 'orchestrator'):
        prompt += _repomap_context(project, _text(config, 'repomap'))
    if readonly:
        prompt += _skill_context(project, _text(config, 'skills'), task_prompt=prompt)
    before = _snapshot(project) if readonly else None
    run_before = _run_snapshot(rd, filename) if readonly else None
    final = rd / (filename + '.answer') if provider == 'codex' else None
    _capture(_command(config, provider, prompt, role, readonly, final), project,
             out, rd / (filename + '.stderr'))
    if final is not None:
        if not final.exists():
            raise RuntimeError(f'Missing final answer from {provider} ({role}): {final}')
        out.write_text(_read(final), encoding='utf-8')
    if readonly:
        if run_before != _run_snapshot(rd, filename):
            raise RuntimeError(f'Stage {role} ({provider}) is read-only but wrote to the run directory')
        if before != _snapshot(project):
            raise RuntimeError(f'Stage {role} ({provider}) is read-only but modified project files')
    done.write_text(datetime.now().isoformat(timespec='seconds'), encoding='utf-8')
    return _read(out)


def _extract_json(text):
    """Extract a JSON object from text, handling markdown fences, preambles, and postambles."""
    if not isinstance(text, str):
        raise TypeError('Expected string input')
    stripped = text.strip()
    if not stripped:
        raise ValueError('Empty output')

    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except (ValueError, TypeError):
        pass

    fence_pattern = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
    for match in fence_pattern.findall(stripped):
        try:
            data = json.loads(match)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            continue

    first_brace = stripped.find('{')
    last_brace = stripped.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        try:
            data = json.loads(stripped[first_brace:last_brace + 1])
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass

    for i, char in enumerate(stripped):
        if char == '{':
            depth = 0
            in_string = False
            escape = False
            for j in range(i, len(stripped)):
                c = stripped[j]
                if in_string:
                    if escape:
                        escape = False
                    elif c == '\\':
                        escape = True
                    elif c == '"':
                        in_string = False
                else:
                    if c == '"':
                        in_string = True
                    elif c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            sub = stripped[i:j + 1]
                            try:
                                data = json.loads(sub)
                                if isinstance(data, dict):
                                    return data
                            except (ValueError, TypeError):
                                pass
                            break
    raise ValueError('No valid JSON object found in text')


def _result(text, key, allowed, provider=None, source=None):
    """Errors must name who answered and where the raw output is; the user has to act on it."""
    origin = f' from {provider}' if provider else ''
    where = f'. Raw output: {source}' if source else ''
    excerpt = f' Got: {text.strip()[:200]!r}' if text and text.strip() else ''
    try:
        data = _extract_json(text)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f'Expected a JSON object with {key}{origin}{where}.{excerpt}') from exc
    if not isinstance(data, dict) or not isinstance(data.get(key), str) or data[key] not in allowed:
        raise RuntimeError(f'Invalid {key} in structured result{origin}{where}.{excerpt}')
    if key == 'verdict':
        if not isinstance(data.get('unresolved'), list) or not isinstance(data.get('summary'), str):
            raise RuntimeError(f'Verdict requires unresolved array and summary string{origin}{where}')
        if data['unresolved'] and data['verdict'] != 'CHANGES_REQUIRED':
            raise RuntimeError(f'Passing verdict cannot contain unresolved findings{origin}{where}')
    return data


BUILTIN_RISK_GLOBS = {'HIGH': [
    '*auth*', '*authz*', '*login*', '*signin*', '*session*', '*token*', '*jwt*', '*oauth*',
    '*sso*', '*saml*', '*ldap*', '*rbac*', '*permission*', '*access*', '*privilege*', '*admin*',
    '*secret*', '*credential*', '*crypt*', '*password*', '*.pem', '*.key',
    '*migration*', '*/versions/*', '*schema*', '*payment*', '*billing*', '*checkout*',
    '*charge*', '*invoice*', '*subscription*', '*.tf', '*.tfvars', '*.tfstate', '*.tf.json',
    '*dockerfile*', '*containerfile*', '*docker-compose*', '.github/workflows/*',
    '.gitlab-ci.yml', 'jenkinsfile', '*.tfbackend',
]}
# A filename never proves intent; escalate on what the change actually does.
RISKY_CONTENT = re.compile(
    r'(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE|DELETE\s+FROM|ALTER\s+TABLE|GRANT\s+ALL'
    r'|os\.system\(|shell\s*=\s*True|pickle\.loads?\(|yaml\.load\|((^|[^\w.])eval\()'
    r'|verify\s*=\s*False|check_hostname\s*=\s*False|rejectUnauthorized\s*:\s*false'
    r'|BEGIN [A-Z ]*PRIVATE KEY)', re.I | re.M)


def _is_guardrail(name):
    """Files that define how the team reviews itself must never slip through unreviewed."""
    return name in GUARDRAIL_FILES or name.startswith(('.agents/agents/', '.claude/agents/',
                                                       '.agents/skills/', '.claude/skills/'))


def _changed_content(project, base, untracked):
    added = [line for line in _git(project, 'diff', '-U0', base).stdout.splitlines()
             if line.startswith('+') and not line.startswith('+++')]
    for name in untracked:
        path = project / name
        try:
            if path.is_file() and path.stat().st_size <= 512 * 1024:
                added.append(path.read_text(encoding='utf-8', errors='ignore'))
        except OSError:
            continue
    return '\n'.join(added)


def _risk(project, base, initial, config):
    untracked = [x for x in _git(project, 'ls-files', '--others', '--exclude-standard').stdout.splitlines() if x]
    names = set(_git(project, 'diff', '--name-only', base).stdout.splitlines()) | set(untracked)
    levels = ['LOW', 'MEDIUM', 'HIGH']
    level = levels.index(initial)
    if len(names) > 1:
        level = max(level, 1)
    if any(_is_guardrail(name) for name in names):
        return 'HIGH'
    patterns = {risk: list(globs) for risk, globs in BUILTIN_RISK_GLOBS.items()}
    for risk, globs in config.get('riskPaths', {}).items():
        patterns.setdefault(risk, []).extend(globs)
    for risk, globs in patterns.items():
        if any(fnmatch(name.lower(), pattern.lower()) for name in names for pattern in globs):
            level = max(level, levels.index(risk))
    if level < 2 and RISKY_CONTENT.search(_changed_content(project, base, untracked)):
        level = 2
    return levels[level]


def doctor(project, probe=False, solo=None):
    """Static readiness; optional help probes do not claim authentication success."""
    problems = []
    try:
        project = ensure_git_repo(project.resolve())
        config = load_config(project)
    except Exception as exc:
        print(f'[FAIL] {exc}')
        return 1
    if solo is not None:
        config['singleProvider'] = bool(solo)
    single_provider = config.get('singleProvider', False)
    primary = config.get('primaryProvider', 'agy')
    required = {'git', primary}
    if not single_provider:
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
    context_file = project / 'PROJECT_CONTEXT.md'
    if not context_file.is_file():
        problems.append('Missing PROJECT_CONTEXT.md')
    elif 'TODO' in _read(context_file):
        problems.append('PROJECT_CONTEXT.md still contains TODO placeholders; '
                        'models cannot match conventions they were never told')
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


QUALITY_RUBRIC = (
    'Judge in this order: correctness > security > data loss > regressions > compatibility > '
    'maintainability > style. Then judge the change as a change: is it the minimal edit that '
    'satisfies the requirement, does it avoid abstraction introduced before a second caller '
    'exists, does its naming and structure match the surrounding code, and does it leave dead '
    'or duplicated code behind? Every finding needs Severity, Evidence (file:line), Impact and '
    'a minimal fix. Working code that is needlessly complex is still a finding.')

QUALITY_RUBRIC_PL = (
    'Oceniaj w tej kolejności: poprawność > bezpieczeństwo > utrata danych > regresje > '
    'kompatybilność > utrzymywalność > styl. Następnie oceń samą zmianę: czy jest minimalną '
    'edycją spełniającą wymaganie, czy nie wprowadza abstrakcji przed drugim użyciem, czy jej '
    'nazewnictwo i struktura są spójne z sąsiadującym kodem, czy nie zostawia martwego lub '
    'zduplikowanego kodu. Każdy finding wymaga: Severity, Evidence (plik:linia), Impact i '
    'minimalnej poprawki. Działający, ale niepotrzebnie złożony kod to nadal finding.')

VERDICT_PROMPT = (QUALITY_RUBRIC +
                  ' Return ONLY JSON: {"verdict":"PASS|PASS_WITH_NOTES|CHANGES_REQUIRED",'
                  '"unresolved":[],"summary":"evidence and reasoning"}. '
                  'List unresolved blocking/high findings in unresolved. No markdown fences.')

VERDICT_PROMPT_PL = (QUALITY_RUBRIC_PL +
                     ' Zwróć WYŁĄCZNIE JSON: {"verdict":"PASS|PASS_WITH_NOTES|CHANGES_REQUIRED",'
                     '"unresolved":[],"summary":"dowody i uzasadnienie"}. '
                     'Nierozwiązane findingi blocking/high wpisz do unresolved. Bez bloków markdown.')

# Stage wording follows the installed templates, so a run never mixes two languages in one prompt.
PROMPTS = {
    'en': {
        'verdict': VERDICT_PROMPT,
        'role': ('Read AI_TEAM.md and PROJECT_CONTEXT.md and relevant project skills. '
                 'Your role is {role}. Do not push, merge or deploy.\n'),
        'skills': '\n\nPROJECT SKILLS - apply these criteria:\n',
        'repomap': '\n\nCODEBASE MAP (AST):\n',
        'learnings': '\n\nTEAM MEMORY & PAST LEARNINGS (avoid repeating these mistakes):\n',
        'triage': 'Analyze risk without edits. Return ONLY JSON: {"risk":"LOW|MEDIUM|HIGH"}.',
        'implement': ('Implement and test. For LOW use a minimal workflow; delegate only when '
                      'complexity warrants it. External reviews are handled by the dispatcher.'),
        'review': ('The change under review is in {patch} (regenerate with git diff {base} if needed). '
                   'Independently review the current working tree including untracked files. '
                   'Do not read other review reports. Do not edit. '),
        'integrate': 'Resolve review findings with evidence. Reports:\n',
        'verify': ('The change is in {patch}. Verify the final requirement and diff without edits. '
                   'The runner executes configured checks. '),
    },
    'pl': {
        'verdict': VERDICT_PROMPT_PL,
        'role': ('Przeczytaj AI_TEAM.md i PROJECT_CONTEXT.md oraz odpowiednie skille projektu. '
                 'Twoja rola to {role}. Nie wykonuj push, merge ani deploy.\n'),
        'skills': '\n\nSKILLE PROJEKTU - stosuj te kryteria:\n',
        'repomap': '\n\nMAPA KODU (AST):\n',
        'learnings': '\n\nBIEŻĄCA PAMIĘĆ ZESPOŁU I POPRZEDNIE WNIOSKI (unikaj powtarzania tych błędów):\n',
        'triage': 'Oceń ryzyko bez edycji. Zwróć WYŁĄCZNIE JSON: {"risk":"LOW|MEDIUM|HIGH"}.',
        'implement': ('Zaimplementuj i przetestuj. Dla LOW użyj minimalnego przebiegu; deleguj tylko '
                      'gdy uzasadnia to złożoność. Recenzje zewnętrzne obsługuje dispatcher.'),
        'review': ('Recenzowana zmiana jest w {patch} (w razie potrzeby odtwórz przez git diff {base}). '
                   'Niezależnie zrecenzuj bieżące drzewo robocze, łącznie z plikami nieśledzonymi. '
                   'Nie czytaj raportów innych recenzentów. Nie edytuj. '),
        'integrate': 'Rozstrzygnij findingi z review, podając dowody. Raporty:\n',
        'verify': ('Zmiana jest w {patch}. Zweryfikuj końcowe wymaganie i diff bez edycji. '
                   'Runner uruchamia skonfigurowane kontrole. '),
    },
}


def _text(config, key):
    return PROMPTS.get(config.get('language', 'en'), PROMPTS['en'])[key]


def _verdict_prompt(config):
    return _text(config, 'verdict')


def _enter_limits(config):
    """Bind every per-run context variable at once so none can be left set on exit."""
    return [(var, var.set(value)) for var, value in [
        (_deadline, time.monotonic() + config.get('runTimeoutSeconds', 14400)),
        (_agent_timeout, config.get('agentTimeoutSeconds', 3600)),
        (_passthrough_env, tuple(config.get('passthroughEnv', []))),
        (_protected_ignored, tuple(config.get('protectedIgnoredPaths', DEFAULT_PROTECTED_IGNORED))),
    ]]


def _write_diff(project, base, rd):
    """Hand reviewers the change itself instead of paying each one to rediscover it."""
    patch = rd / 'diff.patch'
    diff = _git(project, 'diff', base, check=False)
    untracked = [x for x in _git(project, 'ls-files', '--others', '--exclude-standard').stdout.splitlines() if x]
    patch.write_text((diff.stdout or '') + '\n\nUNTRACKED FILES:\n' + '\n'.join(untracked),
                     encoding='utf-8')
    return patch


def _execute(project, config, rd, run_id, base, branch, user_prompt, primary, verification, main_repo=None):
    report = {'runId': run_id, 'base': base, 'branch': branch, 'status': 'RUNNING', 'reviews': [], 'checks': []}
    config_file = project / 'ai-team.config.json'
    config_hash = sha256_file(config_file) if config_file.is_file() else None
    max_rounds = config.get('maxReviewRounds', 2)
    limits = _enter_limits(config)
    save_json(rd / 'result.json', report)
    try:
        context = f'USER TASK:\n{user_prompt}\nBASE REF: {base}\n'
        triage = _ask(config, project, rd, primary, context + _text(config, 'triage'),
                      'triage', 'triage.json', True)
        risk = _result(triage, 'risk', {'LOW', 'MEDIUM', 'HIGH'}, primary, rd / 'triage.json')['risk']

        def require_reviewers(level):
            if config.get('singleProvider', False):
                return [primary]
            reviewers = config.get('reviewPolicy', DEFAULT_POLICY)[level]
            missing = [x for x in reviewers if not which(x)]
            if missing:
                raise RuntimeError('Required reviewers missing: ' + ', '.join(missing))
            return reviewers

        def guard_config():
            if config_hash and (not config_file.is_file() or sha256_file(config_file) != config_hash):
                raise RuntimeError('ai-team.config.json changed during the run; the guardrails this '
                                   'run started under no longer match the file. Review the diff on '
                                   f'branch {branch} before rerunning.')

        if config.get('autoSkills', True):
            try:
                from .skills import proactive_skill_provision
                proactive_skill_provision(project, prompt=user_prompt, lang=config.get('language', 'en'))
            except Exception:
                pass
        require_reviewers(risk)
        _ask(config, project, rd, primary, context + f'RISK: {risk}\n' + _text(config, 'implement'),
             'orchestrator', 'primary.md')
        guard_config()
        for round_number in range(1, max_rounds + 1):
            if config.get('autoSkills', True):
                try:
                    from .skills import proactive_skill_provision
                    diff_names = _git(project, 'diff', '--name-only', base, check=False).stdout.splitlines()
                    untracked_names = [x for x in _git(project, 'ls-files', '--others', '--exclude-standard').stdout.splitlines() if x]
                    all_touched = [x.strip() for x in diff_names + untracked_names if x.strip()]
                    proactive_skill_provision(project, prompt=user_prompt, touched_files=all_touched, lang=config.get('language', 'en'))
                except Exception:
                    pass
            risk = _risk(project, base, risk, config)
            report['risk'] = risk
            reviewers = require_reviewers(risk)
            patch = _write_diff(project, base, rd)
            reviews = []
            before = _snapshot(project)
            for reviewer in reviewers:
                filename = f'review-{round_number}-{reviewer}.json'
                fallback_enabled = config.get('availabilityFallback', False)
                try:
                    text = _ask(config, project, rd, reviewer, context + f'RISK: {risk}\n'
                        + _text(config, 'review').format(patch=patch, base=base) + _verdict_prompt(config),
                        'reviewer', filename, True)
                    result = _result(text, 'verdict', {'PASS', 'PASS_WITH_NOTES', 'CHANGES_REQUIRED'},
                                     reviewer, rd / filename)
                    report['reviews'].append({'provider': reviewer, 'round': round_number, **result})
                    reviews.append((filename, result))
                except Exception as exc:
                    if fallback_enabled and reviewer != primary:
                        print(f"[FALLBACK] Reviewer '{reviewer}' failed ({exc}). Falling back to isolated '{primary}' reviewer.")
                        fallback_filename = f'review-{round_number}-{reviewer}-fallback.json'
                        text = _ask(config, project, rd, primary, context + f'RISK: {risk}\n'
                            + _text(config, 'review').format(patch=patch, base=base) + _verdict_prompt(config),
                            'reviewer', fallback_filename, True)
                        result = _result(text, 'verdict', {'PASS', 'PASS_WITH_NOTES', 'CHANGES_REQUIRED'},
                                         primary, rd / fallback_filename)
                        result['fallbackFrom'] = reviewer
                        report['reviews'].append({'provider': primary, 'fallbackFrom': reviewer, 'round': round_number, **result})
                        reviews.append((fallback_filename, result))
                    else:
                        raise
            if not any(result['verdict'] == 'CHANGES_REQUIRED' for _, result in reviews):
                break
            if round_number == max_rounds:
                report['status'] = 'CHANGES_REQUIRED'
                report['unresolved'] = [x for _, result in reviews for x in result['unresolved']]
                report['note'] = ('maxReviewRounds reached with unresolved findings. The work is on '
                                  f'branch {branch}; continue with: ai-team resume {run_id} '
                                  '--extra-rounds 1')
                return 2
            integrator = config.get('roleProviders', {}).get('integrator', primary)
            _ask(config, project, rd, integrator, context + _text(config, 'integrate') +
                 '\n'.join(str(rd / name) for name, _ in reviews), 'integrator', f'integration-{round_number}.md')
            guard_config()
            if before == _snapshot(project):
                raise RuntimeError('Review findings remain unresolved; integrator made no changes')
        if risk == 'LOW' and report['reviews'] and config.get('skipFinalVerificationAtLow', True):
            # An independent reviewer already passed; a second primary-run opinion adds cost, not safety.
            verdict = {'verdict': 'PASS', 'unresolved': [],
                       'summary': 'LOW risk accepted on the independent review; '
                                  'final verification skipped by skipFinalVerificationAtLow'}
        else:
            final = _ask(config, project, rd, primary, context +
                         _text(config, 'verify').format(patch=rd / 'diff.patch') + _verdict_prompt(config),
                         'verifier', 'final-verification.md', True)
            verdict = _result(final, 'verdict', {'PASS', 'PASS_WITH_NOTES', 'CHANGES_REQUIRED'},
                              primary, rd / 'final-verification.md')
        report['verification'] = verdict
        guard_config()
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
        for var, token in limits:
            var.reset(token)
        try:
            _record_learnings(main_repo or project, run_id, report)
        except Exception:
            pass
        print(f"Run: {run_id}\nBranch: {branch}\nStatus: {report['status']}\nReports: {rd}")
        if report.get('note'):
            print(report['note'])


def _prompt_worktree_merge(project, base, branch, current, run_id, config,
                           auto_merge=None, auto_discard=None, non_interactive=False,
                           status_val='UNKNOWN'):
    """Prompt user or execute automated actions after worktree run completes."""
    lang = config.get('language', 'en')

    # Verify if branch exists
    if _git(project, 'rev-parse', '--verify', branch, check=False).returncode != 0:
        return

    # Check diff against base
    diff_proc = _git(project, 'diff', '--stat', f'{base}...{branch}', check=False)
    diff_stat = diff_proc.stdout.strip()
    if not diff_stat:
        # No code changes; automatically clean up empty branch
        _git(project, 'branch', '-D', branch, check=False)
        if lang == 'pl':
            print(f"\nBrak zmian w kodzie. Gałąź robocza '{branch}' została automatycznie usunięta.")
        else:
            print(f"\nNo code changes detected. Temporary branch '{branch}' was automatically deleted.")
        return

    if auto_discard:
        _git(project, 'branch', '-D', branch, check=False)
        if lang == 'pl':
            print(f"\n[OK] Zmiany odrzucone (--auto-discard). Gałąź robocza '{branch}' została usunięta.")
        else:
            print(f"\n[OK] Changes discarded (--auto-discard). Temporary branch '{branch}' has been deleted.")
        return

    if auto_merge or config.get('autoMerge', False):
        if _git(project, 'status', '--porcelain').stdout.strip():
            if lang == 'pl':
                print(f"\n[BŁĄD] Nie można scalić automatycznie: nieskomitowane zmiany w katalogu roboczym.")
                print(f"Gałąź '{branch}' zachowana. Scal ręcznie: ai-team review {run_id} --merge")
            else:
                print(f"\n[FAIL] Cannot auto-merge: working tree has uncommitted changes.")
                print(f"Branch '{branch}' kept. Merge manually: ai-team review {run_id} --merge")
            return
        proc = _git(project, 'merge', '--no-ff', '-m', f"Merge branch '{branch}' (run {run_id})", branch, check=False)
        if proc.returncode == 0:
            _git(project, 'branch', '-D', branch, check=False)
            if lang == 'pl':
                print(f"\n[OK] Pomyślnie wdrożono zmiany na '{current}'. Gałąź robocza '{branch}' została usunięta.")
            else:
                print(f"\n[OK] Successfully deployed changes to '{current}'. Temporary branch '{branch}' has been deleted.")
        else:
            if lang == 'pl':
                print(f"\n[BŁĄD] Konflikt scalania:\n{proc.stdout}\n{proc.stderr}")
            else:
                print(f"\n[FAIL] Merge conflict or error:\n{proc.stdout}\n{proc.stderr}")
        return

    is_interactive = not non_interactive and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty()
    if not is_interactive:
        if lang == 'pl':
            print(f"\nŚrodowisko nieinteraktywne. Gałąź '{branch}' zachowana. Aby scalić: ai-team review {run_id} --merge")
        else:
            print(f"\nNon-interactive session. Branch '{branch}' kept. To merge: ai-team review {run_id} --merge")
        return

    if lang == 'pl':
        header = (
            f"\n" + "=" * 60 + "\n"
            f"Zadanie agentów zakończone w izolacji (gałąź '{branch}').\n"
            f"Status zadania: {status_val}\n"
            f"Podsumowanie zmian:\n{diff_stat}\n"
            f"=" * 60 + "\n"
            f"Czy wdrożyć zmiany na gałąź główną '{current}'?\n"
            f"  [t]ak       - scal (merge) zmiany na '{current}' i usuń gałąź roboczą\n"
            f"  [p]odgląd   - zobacz pełny diff zmian\n"
            f"  [o]drzuć    - odrzuć zmiany i usuń gałąź roboczą\n"
            f"  [n]ie       - pozostaw gałąź '{branch}' do późniejszego wglądu\n"
        )
        prompt_str = "Wybór [t/p/o/n]: "
    else:
        header = (
            f"\n" + "=" * 60 + "\n"
            f"Agent run completed in isolation (branch '{branch}').\n"
            f"Run status: {status_val}\n"
            f"Changes summary:\n{diff_stat}\n"
            f"=" * 60 + "\n"
            f"Deploy changes to active branch '{current}'?\n"
            f"  [y]es       - merge changes into '{current}' and delete temporary branch\n"
            f"  [d]iff      - view full diff of changes\n"
            f"  [x] discard - discard changes and delete temporary branch\n"
            f"  [n]o        - keep branch '{branch}' for manual review later\n"
        )
        prompt_str = "Choice [y/d/x/n]: "

    print(header)
    while True:
        try:
            choice = input(prompt_str).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = 'n'

        if choice in ('t', 'tak', 'y', 'yes'):
            if _git(project, 'status', '--porcelain').stdout.strip():
                if lang == 'pl':
                    print("\nNie można scalić: katalog roboczy zawiera nieskomitowane zmiany.")
                    print("Zabezpiecz je najpierw (stash/commit).")
                    print(f"Gałąź '{branch}' zachowana. Scal ręcznie: ai-team review {run_id} --merge")
                else:
                    print("\nCannot merge: working tree has uncommitted changes.")
                    print("Stash or commit your changes first.")
                    print(f"Branch '{branch}' kept. Merge manually: ai-team review {run_id} --merge")
                break
            proc = _git(project, 'merge', '--no-ff', '-m', f"Merge branch '{branch}' (run {run_id})", branch, check=False)
            if proc.returncode == 0:
                _git(project, 'branch', '-D', branch, check=False)
                if lang == 'pl':
                    print(f"[OK] Pomyślnie wdrożono zmiany na '{current}'. Gałąź robocza '{branch}' została usunięta.")
                else:
                    print(f"[OK] Successfully deployed changes to '{current}'. Temporary branch '{branch}' has been deleted.")
            else:
                if lang == 'pl':
                    print(f"[BŁĄD] Wystąpił konflikt scalania:\n{proc.stdout}\n{proc.stderr}")
                    print(f"Dokończ scalanie ręcznie lub użyj: git merge --abort")
                else:
                    print(f"[FAIL] Merge error or conflict:\n{proc.stdout}\n{proc.stderr}")
                    print(f"Resolve conflict manually or run: git merge --abort")
            break
        elif choice in ('p', 'podgląd', 'podglad', 'd', 'diff', 'v', 'view'):
            full_diff = _git(project, 'diff', f'{base}...{branch}', check=False).stdout
            print('\n' + (full_diff if full_diff.strip() else "(no diff)"))
            continue
        elif choice in ('o', 'odrzuć', 'odrzuc', 'x', 'discard'):
            _git(project, 'branch', '-D', branch, check=False)
            if lang == 'pl':
                print(f"[OK] Zmiany odrzucone. Gałąź '{branch}' została usunięta.")
            else:
                print(f"[OK] Changes discarded. Temporary branch '{branch}' has been deleted.")
            break
        elif choice in ('n', 'nie', 'no', 'k', 'keep'):
            if lang == 'pl':
                print(f"Gałąź '{branch}' zachowana. Przegląd i scalanie: ai-team review {run_id} --merge")
            else:
                print(f"Branch '{branch}' kept. Review or merge later: ai-team review {run_id} --merge")
            break
        else:
            if lang == 'pl':
                print("Nieprawidłowy wybór. Wybierz: [t]ak, [p]odgląd, [o]drzuć, [n]ie.")
            else:
                print("Invalid choice. Please choose: [y]es, [d]iff, [x] discard, [n]o.")


def run_team(project, user_prompt, use_worktree=None, auto_merge=None, auto_discard=None,
             non_interactive=False, auto_skills=None, solo=None, availability_fallback=None):
    project = ensure_git_repo(project.resolve())
    config = load_config(project)
    if solo is not None:
        config['singleProvider'] = bool(solo)
    if availability_fallback is not None:
        config['availabilityFallback'] = bool(availability_fallback)
    if auto_skills is not None:
        config['autoSkills'] = auto_skills
    if use_worktree is None:
        use_worktree = config.get('useWorktree', False)
    primary = config.get('primaryProvider', 'agy')
    if not which(primary):
        raise RuntimeError(f'Missing primary CLI: {primary}')
    single_provider = config.get('singleProvider', False)
    if single_provider:
        config['reviewPolicy'] = {k: [primary] for k in ('LOW', 'MEDIUM', 'HIGH')}
    else:
        missing = sorted({x for reviewers in config.get('reviewPolicy', DEFAULT_POLICY).values()
                          for x in reviewers if not which(x)})
        if missing:
            raise RuntimeError('Reviewer CLI missing and may be required after risk escalation: '
                               + ', '.join(missing))
    state = load_json(project / '.ai-team/state.json')
    if state.get('conflicts'):
        raise RuntimeError('Resolve installation conflicts before running')
    if not use_worktree and config.get('requireCleanWorkingTree', True) and _git(project, 'status', '--porcelain').stdout.strip():
        raise RuntimeError('Working tree is not clean. Review and commit/stash your changes.')
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
    prefix = config.get('branchPrefix', 'ai/')
    branch = prefix + run_id

    if use_worktree:
        worktree_dir = project_path(project, f'.ai/worktrees/{run_id}')
        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        _git(project, 'worktree', 'add', '-b', branch, str(worktree_dir), base)
        (rd / 'base-ref.txt').write_text(base, encoding='utf-8')
        (rd / 'branch.txt').write_text(branch, encoding='utf-8')
        (rd / 'worktree.txt').write_text(str(worktree_dir), encoding='utf-8')
        rc = 1
        try:
            if (project / '.ai-team').is_dir() and not (worktree_dir / '.ai-team').exists():
                shutil.copytree(project / '.ai-team', worktree_dir / '.ai-team')
            rc = _execute(worktree_dir, config, rd, run_id, base, branch, user_prompt, primary, verification, main_repo=project)
        finally:
            status_out = _git(worktree_dir, 'status', '--porcelain', check=False).stdout.strip()
            if status_out:
                _git(worktree_dir, 'add', '-A', check=False)
                _git(worktree_dir, 'commit', '-m', f"ai({run_id}): {user_prompt[:72]}", check=False)
            _git(project, 'worktree', 'remove', '--force', str(worktree_dir), check=False)
            if worktree_dir.exists():
                shutil.rmtree(worktree_dir, ignore_errors=True)
        res_file = rd / 'result.json'
        status_val = load_json(res_file).get('status', 'UNKNOWN') if res_file.exists() else 'UNKNOWN'
        _prompt_worktree_merge(project, base, branch, current, run_id, config,
                               auto_merge=auto_merge, auto_discard=auto_discard,
                               non_interactive=non_interactive, status_val=status_val)
        return rc
    else:
        branch = current
        reuse = config.get('reuseBranchForFollowUp', False) and current.startswith(prefix)
        if config.get('createBranchForEachRun', True) and not reuse:
            branch = prefix + run_id
            _git(project, 'switch', '-c', branch)
        (rd / 'base-ref.txt').write_text(base, encoding='utf-8')
        (rd / 'branch.txt').write_text(branch, encoding='utf-8')
        return _execute(project, config, rd, run_id, base, branch, user_prompt, primary, verification, main_repo=project)


def runs(project):
    """Branch-per-run accumulates; show what each branch holds. Deleting stays the user's call."""
    project = ensure_git_repo(project.resolve())
    root = project_path(project, '.ai/runs')
    if not root.is_dir():
        print('No runs recorded')
        return 0
    current = _git(project, 'branch', '--show-current').stdout.strip()
    stale = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        result = load_json(directory / 'result.json') if (directory / 'result.json').exists() else {}
        branch = _read(directory / 'branch.txt').strip() or result.get('branch', '')
        exists = branch and not _git(project, 'rev-parse', '--verify', branch, check=False).returncode
        base = _read(directory / 'base-ref.txt').strip() or result.get('base', '')
        changed = ''
        if exists and base:
            # The runner never commits, so the checked-out branch's work is in the working tree.
            if branch == current:
                names = set(_git(project, 'diff', '--name-only', base, check=False).stdout.split())
                names.update(_git(project, 'ls-files', '--others', '--exclude-standard').stdout.split())
            else:
                names = set(_git(project, 'diff', '--name-only', base, branch, check=False).stdout.split())
            changed = f'{len(names)} file(s)' if names else 'no changes'
            if not names and branch != current:
                stale.append(branch)
        marker = '*' if branch == current else ' '
        stat_label = 'merged/deleted' if branch and not exists else changed
        print(f"{marker} {directory.name}  {result.get('status', 'UNKNOWN'):<17} "
              f"{branch or '(no branch)'}  {stat_label}")
    if stale:
        print('\nBranches with no changes against their base:')
        print('  git branch -d ' + ' '.join(stale))
    return 0


def review_run(project, run_id=None, action=None, keep_branch=False):
    """Inspect, diff, merge, or discard a run."""
    # If run_id looks like a path or repo directory, redirect to project
    if run_id in ('.', './', '.\\') or (isinstance(run_id, str) and Path(run_id).is_dir() and (Path(run_id) / '.git').exists()):
        project = Path(run_id)
        run_id = 'latest'

    project = ensure_git_repo(project.resolve())
    runs_dir = project_path(project, '.ai/runs')
    if not runs_dir.is_dir():
        print('No runs recorded')
        return 1

    if not run_id or run_id == 'latest':
        marker = project_path(project, '.ai/latest.txt')
        if not marker.exists():
            print('No latest run recorded')
            return 1
        run_id = _read(marker).strip()

    rd = runs_dir / run_id
    if not rd.is_dir():
        matches = [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith(run_id)]
        if len(matches) == 1:
            rd = matches[0]
            run_id = rd.name
        else:
            print(f'Run not found: {run_id}')
            return 1

    result_file = rd / 'result.json'
    result = load_json(result_file) if result_file.exists() else {}
    branch = _read(rd / 'branch.txt').strip() or result.get('branch', '')
    base = _read(rd / 'base-ref.txt').strip() or result.get('base', '')
    current = _git(project, 'branch', '--show-current').stdout.strip()
    prompt = _read(rd / 'prompt.txt').strip()

    if action == 'diff':
        if branch and _git(project, 'rev-parse', '--verify', branch, check=False).returncode == 0:
            diff_proc = _git(project, 'diff', f'{base}...{branch}' if base else branch, check=False)
            output = diff_proc.stdout
            if not output.strip() and branch == current:
                output = _git(project, 'diff', base, check=False).stdout
            if output.strip():
                print(output)
                return 0
        patch_file = rd / 'diff.patch'
        if patch_file.exists():
            print(_read(patch_file))
            return 0
        print(f'No diff available for run {run_id}')
        return 0

    if action == 'merge':
        if not branch:
            print(f'Run {run_id} has no associated branch')
            return 1
        if _git(project, 'rev-parse', '--verify', branch, check=False).returncode != 0:
            print(f'Branch {branch} does not exist in repository')
            return 1
        if current == branch:
            print(f'Already on branch {branch}')
            return 0
        if _git(project, 'status', '--porcelain').stdout.strip():
            print('Cannot merge: working tree has uncommitted changes. Stash or commit first.')
            return 1
        print(f"Merging branch '{branch}' into '{current}'...")
        proc = _git(project, 'merge', '--no-ff', '-m', f"Merge branch '{branch}' (run {run_id})", branch, check=False)
        if proc.returncode != 0:
            print(f"[FAIL] Merge conflict or error:\n{proc.stdout}\n{proc.stderr}")
            return proc.returncode
        print(f"[OK] Successfully merged {branch} into {current}")
        if not keep_branch:
            _git(project, 'branch', '-D', branch, check=False)
            print(f"[OK] Successfully merged {branch} into {current} and deleted temporary branch")
        else:
            print(f"[OK] Successfully merged {branch} into {current}")
        return 0

    if action == 'discard':
        if not branch:
            print(f'Run {run_id} has no associated branch')
            return 1
        if current == branch:
            print(f'Cannot discard active branch {branch}. Switch to another branch first.')
            return 1
        if _git(project, 'rev-parse', '--verify', branch, check=False).returncode == 0:
            _git(project, 'branch', '-D', branch)
            print(f"[OK] Discarded and deleted branch {branch}")
        else:
            print(f'Branch {branch} not found or already deleted')
        return 0

    # Default action: summary
    status_val = result.get('status', 'UNKNOWN')
    risk_val = result.get('risk', 'UNKNOWN')
    print('=' * 60)
    print(f'AI Engineering Team - Run Review')
    print('=' * 60)
    print(f'Run ID:       {run_id}')
    print(f'Status:       {status_val}')
    print(f'Risk:         {risk_val}')
    print(f'Branch:       {branch or "(none)"}')
    print(f'Base:         {base or "(none)"}')
    if prompt:
        print(f'Prompt:       {prompt[:120]}{"..." if len(prompt) > 120 else ""}')

    reviews = result.get('reviews', [])
    if reviews:
        print('\nReview Verdicts:')
        for r in reviews:
            provider = r.get('provider', 'unknown')
            round_no = r.get('round', 1)
            v = r.get('verdict', 'UNKNOWN')
            summary = r.get('summary', '')
            print(f'  - Round {round_no} [{provider}]: {v}')
            if summary:
                print(f'    Summary: {summary[:100]}')
            for unf in r.get('unresolved', []):
                print(f'    * Unresolved: {unf}')

    checks = result.get('checks', [])
    if checks:
        print('\nChecks:')
        for c in checks:
            cmd_str = ' '.join(c.get('argv', []))
            ec = c.get('exitCode', -1)
            icon = 'OK' if ec == 0 else 'FAIL'
            print(f'  - [{icon}] {cmd_str} (exit {ec})')

    verification = result.get('verification', {})
    if verification:
        print(f"\nFinal Verification: {verification.get('verdict', 'NONE')}")
        if verification.get('summary'):
            print(f"  Summary: {verification['summary'][:120]}")

    print('\nActions:')
    print(f'  ai-team review {run_id} --diff      # View full patch')
    print(f'  ai-team review {run_id} --merge     # Merge branch into current branch')
    print(f'  ai-team review {run_id} --discard   # Discard and delete branch')
    print('=' * 60)
    return 0


def _reopen_last_round(rd, extra_rounds):
    """Drop the final round's cached answers so resume can actually retry it."""
    rounds = sorted({int(p.name.split('-')[1]) for p in rd.glob('review-*-*.json')
                     if p.name.split('-')[1].isdigit()})
    if not rounds:
        return
    last = rounds[-1]
    for path in list(rd.glob(f'review-{last}-*')) + list(rd.glob(f'integration-{last}.*')):
        path.unlink()
    print(f'Reopened review round {last} for {extra_rounds} additional round(s)')


def resume_team(project, run_id, extra_rounds=0):
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
    if extra_rounds:
        config['maxReviewRounds'] = config.get('maxReviewRounds', 2) + extra_rounds
        _reopen_last_round(rd, extra_rounds)
    return _execute(project, config, rd, run_id, base, branch, _read(prompt_file), primary, config.get('verification', {}), main_repo=project)
