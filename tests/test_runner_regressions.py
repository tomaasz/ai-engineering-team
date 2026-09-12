import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_team import runner
from ai_team.config import validate
from ai_team.installer import install
from ai_team.utils import load_json, save_json


def git(path, *args):
    return subprocess.run(['git', *args], cwd=path, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def project(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.test')
    git(tmp_path, 'config', 'commit.gpgsign', 'false')
    git(tmp_path, 'config', 'core.whitespace', 'trailing-space,space-before-tab,cr-at-eol')
    (tmp_path / 'README.md').write_text('Initial\n', encoding='utf-8')
    install(tmp_path, 'core')
    cfg = load_json(tmp_path / 'ai-team.config.json')
    cfg['verification']['commands'] = [{'argv': [sys.executable, '-c', 'print("verified")'], 'cwd': '.', 'timeoutSeconds': 10}]
    save_json(tmp_path / 'ai-team.config.json', cfg)
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'setup')
    return tmp_path


def configure(project, **values):
    cfg = load_json(project / 'ai-team.config.json')
    cfg.update(values)
    save_json(project / 'ai-team.config.json', cfg)
    git(project, 'add', 'ai-team.config.json')
    git(project, 'commit', '-m', 'configure')


def report(project):
    run_id = (project / '.ai/latest.txt').read_text(encoding='utf-8')
    return load_json(project / '.ai/runs' / run_id / 'result.json')


def mock_agents(monkeypatch, risk='LOW', effect=None):
    calls = []
    def ask(config, project, rd, provider, prompt, role, filename, readonly=False):
        calls.append((provider, role))
        if effect:
            answer = effect(project, role, filename)
            if answer is not None:
                return answer
        if role == 'triage':
            return json.dumps({'risk': risk})
        return json.dumps({'verdict': 'PASS', 'unresolved': [], 'summary': 'reviewed'})
    monkeypatch.setattr(runner, '_ask', ask)
    monkeypatch.setattr(runner, 'which', lambda x: x)
    return calls


def test_actual_check_failure_overrides_model_pass(project, monkeypatch):
    configure(project, verification={'commands': [{'argv': [sys.executable, '-c', 'raise SystemExit(7)']}]})
    mock_agents(monkeypatch)
    assert runner.run_team(project, 'Task') == 2
    result = report(project)
    assert result['status'] == 'CHANGES_REQUIRED'
    assert result['checks'][0]['exitCode'] == 7


def test_actual_check_success_recorded(project, monkeypatch):
    mock_agents(monkeypatch)
    assert runner.run_team(project, 'Task') == 0
    assert report(project)['checks'][0]['exitCode'] == 0


def test_new_branch_even_when_already_on_ai_branch(project, monkeypatch):
    mock_agents(monkeypatch)
    git(project, 'switch', '-c', 'ai/existing')
    runner.run_team(project, 'Task')
    first = git(project, 'branch', '--show-current')
    runner.run_team(project, 'Task')
    second = git(project, 'branch', '--show-current')
    assert first.startswith('ai/') and second.startswith('ai/')
    assert len({'ai/existing', first, second}) == 3


def test_missing_review_never_falls_back(project, monkeypatch):
    configure(project, availabilityFallback=True)
    calls = mock_agents(monkeypatch, 'HIGH')
    monkeypatch.setattr(runner, 'which', lambda x: None if x == 'claude' else x)
    with pytest.raises(RuntimeError, match='Required reviewers missing'):
        runner.run_team(project, 'Task')
    assert not any(role == 'orchestrator' for _, role in calls)
    assert report(project)['status'] == 'FAILED'


def test_failed_reviewer_stops_run(project, monkeypatch):
    def effect(project, role, filename):
        if role == 'reviewer':
            raise RuntimeError('Reviewer exited 9')
    mock_agents(monkeypatch, 'HIGH', effect)
    with pytest.raises(RuntimeError, match='Reviewer exited'):
        runner.run_team(project, 'Task')
    assert report(project)['status'] == 'FAILED'


def test_real_diff_escalates_low_to_high_including_new_files(project, monkeypatch):
    def effect(project, role, filename):
        if role == 'orchestrator':
            (project / 'authentication.py').write_text('# auth\n', encoding='utf-8')
    calls = mock_agents(monkeypatch, effect=effect)
    runner.run_team(project, 'Task')
    assert report(project)['risk'] == 'HIGH'
    assert ('claude', 'reviewer') in calls and ('codex', 'reviewer') in calls


def test_diff_check_failure_blocks_pass(project, monkeypatch):
    def effect(project, role, filename):
        if role == 'orchestrator':
            (project / 'README.md').write_text('trailing whitespace   \n', encoding='utf-8')
    mock_agents(monkeypatch, effect=effect)
    assert runner.run_team(project, 'Task') == 2
    assert report(project)['diffCheckExitCode'] != 0


def test_repairs_require_fresh_review(project, monkeypatch):
    def effect(project, role, filename):
        if role == 'reviewer' and filename.startswith('review-1-'):
            return json.dumps({'verdict': 'CHANGES_REQUIRED', 'unresolved': ['bug'], 'summary': 'bug'})
        if role == 'integrator':
            (project / 'README.md').write_text('Fixed\n', encoding='utf-8')
    calls = mock_agents(monkeypatch, 'MEDIUM', effect)
    assert runner.run_team(project, 'Task') == 0, report(project)
    assert calls.count(('codex', 'reviewer')) == 2
    assert len(report(project)['reviews']) == 2


def test_review_round_limit_blocks_unresolved_findings(project, monkeypatch):
    configure(project, maxReviewRounds=1)
    def effect(project, role, filename):
        if role == 'reviewer':
            return json.dumps({'verdict': 'CHANGES_REQUIRED', 'unresolved': ['bug'], 'summary': 'bug'})
    mock_agents(monkeypatch, 'MEDIUM', effect)
    with pytest.raises(RuntimeError, match='maxReviewRounds'):
        runner.run_team(project, 'Task')


@pytest.mark.parametrize('value', ['VERDICT: PASS', '{"verdict":"PASS"}', '{"verdict":"PASS","unresolved":["bug"],"summary":"x"}'])
def test_unstructured_or_contradictory_verdict_rejected(value):
    with pytest.raises(RuntimeError):
        runner._result(value, 'verdict', {'PASS'})


def test_readonly_stage_mutations_detected(project, tmp_path, monkeypatch):
    def capture(cmd, cwd, out, err, allow_failure=False):
        (project / 'README.md').write_text('unauthorized\n', encoding='utf-8')
        out.write_text('{}', encoding='utf-8')
        return 0
    monkeypatch.setattr(runner, '_capture', capture)
    with pytest.raises(RuntimeError, match='Read-only stage'):
        runner._ask({}, project, tmp_path, 'agy', 'task', 'verifier', 'answer.json', True)


def test_codex_readonly_explicit_and_final_answer_path(tmp_path):
    cmd = runner._command({}, 'codex', 'task', 'reviewer', True, tmp_path / 'answer')
    assert cmd[cmd.index('--sandbox') + 1] == 'read-only'
    assert cmd[cmd.index('--output-last-message') + 1] == str(tmp_path / 'answer')


def test_agy_readonly_overrides_fullauto():
    cmd = runner._command({'antigravity': {'fullAuto': True, 'sandbox': False}}, 'agy', 'task', 'triage', True)
    assert '--dangerously-skip-permissions' not in cmd
    assert '--sandbox' in cmd and cmd[cmd.index('--mode') + 1] == 'plan'


def test_monorepo_command_cwd(project, monkeypatch):
    (project / 'packages/app').mkdir(parents=True)
    configure(project, verification={'commands': [{'argv': [sys.executable, '-c', 'import pathlib; assert pathlib.Path.cwd().name == "app"'], 'cwd': 'packages/app'}]})
    mock_agents(monkeypatch)
    assert runner.run_team(project, 'Task') == 0


@pytest.mark.parametrize('provider,policy', [
    ('codex', {'LOW': [], 'MEDIUM': ['claude'], 'HIGH': ['agy', 'claude']}),
    ('claude', {'LOW': [], 'MEDIUM': ['codex'], 'HIGH': ['agy', 'codex']}),
])
def test_alternative_primary_provider(project, monkeypatch, provider, policy):
    configure(project, primaryProvider=provider, reviewPolicy=policy)
    calls = mock_agents(monkeypatch)
    assert runner.run_team(project, 'Task') == 0
    assert (provider, 'orchestrator') in calls


def test_timeout_recorded_as_failure(project, monkeypatch):
    configure(project, verification={'commands': [{'argv': [sys.executable, '-c', 'import time; time.sleep(10)'], 'timeoutSeconds': 1}]})
    mock_agents(monkeypatch)
    with pytest.raises(RuntimeError, match='timeout'):
        runner.run_team(project, 'Task')
    assert report(project)['status'] == 'FAILED'


@pytest.mark.parametrize('values', [
    {'primaryProvider': 'unknown'},
    {'reviewPolicy': {'LOW': [], 'MEDIUM': [], 'HIGH': []}},
    {'verification': {'commands': [{'argv': ['echo'], 'cwd': '../'}]}},
    {'verification': {'commands': [{'argv': 'echo test'}]}},
    {'maxReviewRounds': 0}, {'agentTimeoutSeconds': True},
])
def test_invalid_configuration_rejected(project, values):
    cfg = load_json(project / 'ai-team.config.json')
    cfg.update(values)
    with pytest.raises((ValueError, RuntimeError)):
        validate(cfg, project)


def test_doctor_rejects_unconfigured_checks(project, monkeypatch):
    configure(project, verification={'commands': [], 'noChecksReason': ''})
    monkeypatch.setattr(runner, 'which', lambda x: x)
    assert runner.doctor(project) == 1
