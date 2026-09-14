"""Pipeline fixes from the 2026-09 framework audit."""
import json
import subprocess
import sys

import pytest

from ai_team import runner
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
    git(tmp_path, 'config', 'core.whitespace', '-trailing-space')
    git(tmp_path, 'config', 'core.autocrlf', 'false')
    (tmp_path / 'README.md').write_text('Initial\n', encoding='utf-8')
    install(tmp_path, 'core')
    cfg = load_json(tmp_path / 'ai-team.config.json')
    cfg['verification']['commands'] = [{'argv': [sys.executable, '-c', 'print("ok")'],
                                        'cwd': '.', 'timeoutSeconds': 10}]
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
    prompts = {}

    def ask(config, project, rd, provider, prompt, role, filename, readonly=False):
        calls.append((provider, role))
        prompts[role] = prompt
        if effect:
            answer = effect(project, role, filename, rd)
            if answer is not None:
                return answer
        if role == 'triage':
            return json.dumps({'risk': risk})
        return json.dumps({'verdict': 'PASS', 'unresolved': [], 'summary': 'reviewed'})

    monkeypatch.setattr(runner, '_ask', ask)
    monkeypatch.setattr(runner, 'which', lambda x: x)
    return calls, prompts


def test_reviewers_receive_the_diff_instead_of_rediscovering_it(project, monkeypatch):
    calls, prompts = mock_agents(monkeypatch, 'MEDIUM')
    assert runner.run_team(project, 'Task') == 0, report(project)
    run_id = (project / '.ai/latest.txt').read_text(encoding='utf-8')
    assert (project / '.ai/runs' / run_id / 'diff.patch').exists()
    assert 'diff.patch' in prompts['reviewer']


def test_malformed_verdict_names_the_provider_and_the_raw_output(project, monkeypatch):
    def effect(project, role, filename, rd):
        if role == 'reviewer':
            return 'I think it looks fine!'
    mock_agents(monkeypatch, 'MEDIUM', effect)
    with pytest.raises(RuntimeError, match=r'codex.*review-1-codex\.json'):
        runner.run_team(project, 'Task')


def test_agent_tampering_with_the_config_aborts_the_run(project, monkeypatch):
    def effect(project, role, filename, rd):
        if role == 'orchestrator':
            cfg = load_json(project / 'ai-team.config.json')
            cfg['maxReviewRounds'] = 5
            save_json(project / 'ai-team.config.json', cfg)
    mock_agents(monkeypatch, 'LOW', effect)
    with pytest.raises(RuntimeError, match='ai-team.config.json'):
        runner.run_team(project, 'Task')


def test_exhausted_review_rounds_report_changes_required_without_crashing(project, monkeypatch):
    configure(project, maxReviewRounds=1)

    def effect(project, role, filename, rd):
        if role == 'reviewer':
            return json.dumps({'verdict': 'CHANGES_REQUIRED', 'unresolved': ['bug'], 'summary': 'bug'})
    mock_agents(monkeypatch, 'MEDIUM', effect)
    assert runner.run_team(project, 'Task') == 2
    result = report(project)
    assert result['status'] == 'CHANGES_REQUIRED'
    assert result['unresolved'] == ['bug']


def test_resume_with_extra_rounds_continues_past_the_limit(project, monkeypatch):
    configure(project, maxReviewRounds=1)
    state = {'fixed': False}

    def effect(project, role, filename, rd):
        if role == 'reviewer':
            if state['fixed']:
                return json.dumps({'verdict': 'PASS', 'unresolved': [], 'summary': 'ok'})
            return json.dumps({'verdict': 'CHANGES_REQUIRED', 'unresolved': ['bug'], 'summary': 'bug'})
        if role == 'integrator':
            state['fixed'] = True
            (project / 'README.md').write_text('Fixed\n', encoding='utf-8')
    mock_agents(monkeypatch, 'MEDIUM', effect)
    assert runner.run_team(project, 'Task') == 2
    run_id = (project / '.ai/latest.txt').read_text(encoding='utf-8')
    assert runner.resume_team(project, run_id, extra_rounds=2) == 0, report(project)


def test_missing_escalation_reviewer_is_caught_before_any_model_runs(project, monkeypatch):
    calls, _ = mock_agents(monkeypatch, 'LOW')
    monkeypatch.setattr(runner, 'which', lambda x: None if x == 'claude' else x)
    with pytest.raises(RuntimeError, match='risk escalation'):
        runner.run_team(project, 'Task')
    assert not calls, 'no model should be paid for before readiness is known'


def test_follow_up_run_can_reuse_the_current_ai_branch(project, monkeypatch):
    mock_agents(monkeypatch, 'LOW')
    assert runner.run_team(project, 'First') == 0
    first = git(project, 'branch', '--show-current')
    configure(project, reuseBranchForFollowUp=True)
    assert runner.run_team(project, 'Second') == 0
    assert git(project, 'branch', '--show-current') == first


def test_low_risk_skips_the_primary_self_verification(project, monkeypatch):
    calls, _ = mock_agents(monkeypatch, 'LOW')
    assert runner.run_team(project, 'Task') == 0, report(project)
    assert ('codex', 'reviewer') in calls
    assert not any(role == 'verifier' for _, role in calls)


def test_medium_risk_still_runs_the_final_verifier(project, monkeypatch):
    calls, _ = mock_agents(monkeypatch, 'MEDIUM')
    assert runner.run_team(project, 'Task') == 0, report(project)
    assert any(role == 'verifier' for _, role in calls)


def test_integration_can_be_routed_to_a_dedicated_provider(project, monkeypatch):
    configure(project, reviewPolicy={'LOW': ['claude'], 'MEDIUM': ['claude', 'codex'],
                                     'HIGH': ['claude', 'codex']},
              roleProviders={'integrator': 'codex'})
    rounds = {'n': 0}

    def effect(project, role, filename, rd):
        if role == 'reviewer' and filename.startswith('review-1-'):
            return json.dumps({'verdict': 'CHANGES_REQUIRED', 'unresolved': ['bug'], 'summary': 'bug'})
        if role == 'integrator':
            rounds['n'] += 1
            (project / 'README.md').write_text('Fixed\n', encoding='utf-8')
    calls, _ = mock_agents(monkeypatch, 'MEDIUM', effect)
    assert runner.run_team(project, 'Task') == 0, report(project)
    assert ('codex', 'integrator') in calls
    assert ('agy', 'integrator') not in calls


def test_doctor_flags_unfilled_project_context(project, capsys):
    assert runner.doctor(project) == 1
    assert 'TODO' in capsys.readouterr().out


def test_dirty_working_tree_message_is_english(project, monkeypatch):
    monkeypatch.setattr(runner, 'which', lambda x: x)
    (project / 'scratch.txt').write_text('wip\n', encoding='utf-8')
    with pytest.raises(RuntimeError) as excinfo:
        runner.run_team(project, 'Task')
    assert 'nie jest czysty' not in str(excinfo.value)
    assert 'not clean' in str(excinfo.value)


def test_runs_listing_shows_each_branch_and_its_status(project, monkeypatch, capsys):
    """Branch-per-run piles up; the user needs to see which ones still matter."""
    mock_agents(monkeypatch, 'LOW')
    assert runner.run_team(project, 'First') == 0
    git(project, 'switch', 'main')
    assert runner.runs(project) == 0
    out = capsys.readouterr().out
    assert 'ai/' in out and 'PASS' in out
    assert 'git branch -d' in out, 'deletion stays the user decision'


def test_runs_listing_never_deletes_a_branch(project, monkeypatch):
    mock_agents(monkeypatch, 'LOW')
    runner.run_team(project, 'First')
    branch = git(project, 'branch', '--show-current')
    git(project, 'switch', 'main')
    runner.runs(project)
    assert branch in git(project, 'branch', '--list', branch)


def test_runs_counts_uncommitted_work_on_the_checked_out_branch(project, monkeypatch, capsys):
    """The runner never commits, so a run's output lives in the working tree, not in a commit."""
    def effect(project, role, filename, rd):
        if role == 'orchestrator':
            (project / 'feature.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
    mock_agents(monkeypatch, 'LOW', effect)
    assert runner.run_team(project, 'Task', auto_skills=False) == 0, report(project)
    assert runner.runs(project) == 0
    out = capsys.readouterr().out
    assert '1 file(s)' in out
    assert 'git branch -d' not in out, 'a branch holding uncommitted work is not disposable'
