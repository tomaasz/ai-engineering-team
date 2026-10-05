import json
import subprocess
import sys
from pathlib import Path
import pytest

from ai_team import runner
from ai_team.config import validate
from ai_team.installer import install
from ai_team.utils import load_json, save_json
from ai_team.artifact_verifier import (
    ArtifactVerificationResult,
    get_git_changes,
    verify_completion_artifacts,
)


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.com')
    git(tmp_path, 'config', 'commit.gpgsign', 'false')
    (tmp_path / 'README.md').write_text('Initial\n', encoding='utf-8')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'Initial commit')
    return tmp_path


def test_get_git_changes_clean(git_repo):
    modified, untracked = get_git_changes(git_repo)
    assert modified == []
    assert untracked == []


def test_get_git_changes_modified_file(git_repo):
    (git_repo / 'README.md').write_text('Modified\n', encoding='utf-8')
    modified, untracked = get_git_changes(git_repo)
    assert modified == ['README.md']
    assert untracked == []


def test_get_git_changes_untracked_file(git_repo):
    (git_repo / 'new_module.py').write_text('x = 1\n', encoding='utf-8')
    modified, untracked = get_git_changes(git_repo)
    assert modified == []
    assert untracked == ['new_module.py']


def test_get_git_changes_ignores_internal_dirs(git_repo):
    (git_repo / '.ai').mkdir(parents=True, exist_ok=True)
    (git_repo / '.ai' / 'temp.txt').write_text('cache', encoding='utf-8')
    (git_repo / '.ai-team').mkdir(parents=True, exist_ok=True)
    (git_repo / '.ai-team' / 'state.json').write_text('{}', encoding='utf-8')
    modified, untracked = get_git_changes(git_repo)
    assert modified == []
    assert untracked == []


def test_verify_completion_artifacts_ghost_completion_rejected(git_repo):
    # Agent reports PASS but no changes in repo
    res = verify_completion_artifacts(git_repo, verdict={'verdict': 'PASS'}, require_changes=True)
    assert res.valid is False
    assert res.has_physical_changes is False
    assert len(res.reasons) == 1
    assert 'ghost completion' in res.reasons[0]


def test_verify_completion_artifacts_with_changes_accepted(git_repo):
    (git_repo / 'feature.py').write_text('def run(): pass\n', encoding='utf-8')
    res = verify_completion_artifacts(git_repo, verdict={'verdict': 'PASS'}, require_changes=True)
    assert res.valid is True
    assert res.has_physical_changes is True
    assert 'feature.py' in res.untracked_files
    assert res.reasons == []


def test_verify_completion_artifacts_failed_checks_rejected(git_repo):
    (git_repo / 'feature.py').write_text('def run(): pass\n', encoding='utf-8')
    checks = [{'argv': ['pytest'], 'exitCode': 1}]
    res = verify_completion_artifacts(git_repo, checks=checks, verdict={'verdict': 'PASS'}, require_changes=True)
    assert res.valid is False
    assert len(res.failed_checks) == 1
    assert 'nieudanych testów' in res.reasons[0]


def test_verify_completion_artifacts_disabled_allows_clean_repo(git_repo):
    res = verify_completion_artifacts(git_repo, verdict={'verdict': 'PASS'}, require_changes=False)
    assert res.valid is True
    assert res.has_physical_changes is False


def test_config_validation_require_artifacts():
    base_cfg = {
        'primaryProvider': 'agy',
        'singleProvider': True,
        'verification': {'commands': [], 'noChecksReason': 'docs'},
    }
    # Valid boolean
    cfg = validate({**base_cfg, 'requireArtifacts': True}, Path('.'))
    assert cfg['requireArtifacts'] is True
    cfg = validate({**base_cfg, 'requireArtifacts': False}, Path('.'))
    assert cfg['requireArtifacts'] is False

    # Invalid type
    with pytest.raises(ValueError, match='requireArtifacts must be boolean'):
        validate({**base_cfg, 'requireArtifacts': 'yes'}, Path('.'))


@pytest.fixture
def project(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.com')
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


def mock_agents(monkeypatch, effect=None):
    calls = []
    def ask(config, project, rd, provider, prompt, role, filename, readonly=False):
        calls.append((provider, role))
        if effect:
            answer = effect(project, role, filename, rd)
            if answer is not None:
                return answer
        if role == 'triage':
            return json.dumps({'risk': 'LOW'})
        return json.dumps({'verdict': 'PASS', 'unresolved': [], 'summary': 'reviewed'})
    monkeypatch.setattr(runner, '_ask', ask)
    monkeypatch.setattr(runner, 'which', lambda x: x)
    return calls


def test_runner_ghost_completion_blocks_pass_when_enforced(project, monkeypatch):
    mock_agents(monkeypatch)
    # Agent modifies no files and reports PASS
    rc = runner.run_team(project, 'Task', require_artifacts=True)
    assert rc == 2
    run_id = (project / '.ai/latest.txt').read_text(encoding='utf-8')
    res = load_json(project / '.ai/runs' / run_id / 'result.json')
    assert res['status'] == 'CHANGES_REQUIRED'
    assert res['artifactVerification']['valid'] is False
    assert res['artifactVerification']['has_physical_changes'] is False
    assert any('ghost completion' in r for r in res['artifactVerification']['reasons'])


def test_runner_physical_changes_passes_when_enforced(project, monkeypatch):
    def effect(project, role, filename, rd):
        if role == 'orchestrator':
            (project / 'feature.py').write_text('# new feature\n', encoding='utf-8')
    mock_agents(monkeypatch, effect=effect)
    rc = runner.run_team(project, 'Task', require_artifacts=True)
    assert rc == 0
    run_id = (project / '.ai/latest.txt').read_text(encoding='utf-8')
    res = load_json(project / '.ai/runs' / run_id / 'result.json')
    assert res['status'] in ('PASS', 'PASS_WITH_NOTES')
    assert res['artifactVerification']['valid'] is True
    assert res['artifactVerification']['has_physical_changes'] is True
    assert 'feature.py' in res['artifactVerification']['untracked_files']


def test_cli_check_artifacts_fails_on_clean_repo(git_repo, monkeypatch, capsys):
    from ai_team.cli import main
    monkeypatch.setattr('sys.argv', ['ai-team', 'check-artifacts', str(git_repo)])
    rc = main()
    assert rc == 1
    out = capsys.readouterr().out
    assert 'Completion artifacts verification failed' in out


def test_cli_check_artifacts_passes_with_modifications(git_repo, monkeypatch, capsys):
    from ai_team.cli import main
    (git_repo / 'patch.txt').write_text('content', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['ai-team', 'check-artifacts', str(git_repo)])
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    assert 'All completion artifacts verified successfully' in out
    assert 'patch.txt' in out
