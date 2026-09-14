"""Durability and subprocess-isolation fixes from the 2026-09 framework audit."""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ai_team import runner
from ai_team.runner import _ask, _capture, _sanitized_env
from ai_team.installer import install


def git(path, *args):
    return subprocess.run(['git', *args], cwd=path, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def project(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.test')
    git(tmp_path, 'config', 'commit.gpgsign', 'false')
    (tmp_path / 'README.md').write_text('Initial\n', encoding='utf-8')
    install(tmp_path, 'core')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'setup')
    return tmp_path


def test_timeout_leaves_no_stage_output_behind(tmp_path):
    """A partially written answer must never survive to look like a completed stage."""
    out, err = tmp_path / 'primary.md', tmp_path / 'primary.md.stderr'
    script = [sys.executable, '-u', '-c',
              "import sys,time; sys.stdout.write('PARTIAL'); sys.stdout.flush(); time.sleep(10)"]
    with pytest.raises(RuntimeError, match='timeout'):
        _capture(script, tmp_path, out, err, timeout=1)
    assert not out.exists()
    assert not list(tmp_path.glob('*.partial'))


def test_failed_command_leaves_no_stage_output_behind(tmp_path):
    out, err = tmp_path / 'primary.md', tmp_path / 'primary.md.stderr'
    script = [sys.executable, '-c', "import sys; sys.stdout.write('half'); sys.exit(3)"]
    with pytest.raises(RuntimeError, match='exited 3'):
        _capture(script, tmp_path, out, err)
    assert not out.exists()


def test_timeout_kills_descendant_processes(tmp_path):
    """A timed-out agent must not keep writing to the repository after the runner returns."""
    marker = tmp_path / 'descendant.txt'
    child = f"import time; time.sleep(4); open(r'{marker}','w').write('x')"
    parent = (f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); "
              "time.sleep(20)")
    with pytest.raises(RuntimeError, match='timeout'):
        _capture([sys.executable, '-c', parent], tmp_path, tmp_path / 'o', tmp_path / 'e', timeout=1)
    time.sleep(6)
    assert not marker.exists(), 'descendant survived the runner timeout'


def test_partial_stage_output_is_not_treated_as_completed(tmp_path):
    """The exact resume defect: a stale answer file must not skip the stage."""
    rd = tmp_path / 'run'
    rd.mkdir()
    (rd / 'primary.md').write_text('PARTIAL IMPLEMENTATION ONLY', encoding='utf-8')
    calls = []

    def capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
        calls.append(cmd)
        out.write_text('complete answer', encoding='utf-8')
        return 0

    runner._capture = capture
    try:
        answer = _ask({}, tmp_path, rd, 'claude', 'task', 'orchestrator', 'primary.md')
    finally:
        runner._capture = _capture
    assert calls, 'stage without a completion marker must be re-run'
    assert answer == 'complete answer'


def test_completed_stage_is_reused_on_resume(tmp_path):
    rd = tmp_path / 'run'
    rd.mkdir()
    calls = []

    def capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
        calls.append(cmd)
        out.write_text('first answer', encoding='utf-8')
        return 0

    runner._capture = capture
    try:
        _ask({}, tmp_path, rd, 'claude', 'task', 'orchestrator', 'primary.md')
        again = _ask({}, tmp_path, rd, 'claude', 'task', 'orchestrator', 'primary.md')
    finally:
        runner._capture = _capture
    assert len(calls) == 1
    assert again == 'first answer'


@pytest.mark.parametrize('name', ['DATABASE_URL', 'SENTRY_DSN', 'KUBECONFIG',
                                  'DOCKER_AUTH_CONFIG', 'GH_PAT', 'SESSION_SIGNING_SALT'])
def test_credential_bearing_variables_are_stripped(monkeypatch, name):
    monkeypatch.setenv(name, 'sensitive')
    assert name not in _sanitized_env(passthrough=())


def test_ssh_agent_socket_is_never_forwarded(monkeypatch):
    monkeypatch.setenv('SSH_AUTH_SOCK', '/tmp/agent.sock')
    assert 'SSH_AUTH_SOCK' not in _sanitized_env(passthrough=())


def test_provider_auth_can_be_passed_through_explicitly(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-test')
    assert 'ANTHROPIC_API_KEY' not in _sanitized_env(passthrough=())
    assert _sanitized_env(passthrough=('ANTHROPIC_API_KEY',))['ANTHROPIC_API_KEY'] == 'sk-test'


def test_readonly_stage_writing_to_the_run_directory_is_detected(project):
    rd = project / '.ai/runs/test-run'
    rd.mkdir(parents=True)

    def capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
        out.write_text('{"verdict":"PASS"}', encoding='utf-8')
        (rd / 'review-2-codex.json').write_text('{"verdict":"PASS"}', encoding='utf-8')
        return 0

    runner._capture = capture
    try:
        with pytest.raises(RuntimeError, match='run directory'):
            _ask({}, project, rd, 'claude', 'review', 'reviewer', 'review-1-claude.json', readonly=True)
    finally:
        runner._capture = _capture


def test_readonly_stage_writing_to_protected_ignored_path_is_detected(project):
    (project / '.gitignore').write_text('.env\n', encoding='utf-8')
    (project / '.env').write_text('TOKEN=old\n', encoding='utf-8')
    git(project, 'add', '.gitignore')
    git(project, 'commit', '-m', 'ignore env')
    rd = project / '.ai/runs/test-run'
    rd.mkdir(parents=True)

    def capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
        out.write_text('{"verdict":"PASS"}', encoding='utf-8')
        (project / '.env').write_text('TOKEN=exfiltrated\n', encoding='utf-8')
        return 0

    runner._capture = capture
    try:
        with pytest.raises(RuntimeError, match='read-only'):
            _ask({}, project, rd, 'claude', 'review', 'reviewer', 'review-1-claude.json', readonly=True)
    finally:
        runner._capture = _capture


def test_review_prompt_carries_the_project_skills(project):
    rd = project / '.ai/runs/test-run'
    rd.mkdir(parents=True)
    prompts = []

    def capture(cmd, cwd, out, err, allow_failure=False, timeout=None):
        prompts.append(' '.join(cmd))
        out.write_text('{"verdict":"PASS"}', encoding='utf-8')
        return 0

    runner._capture = capture
    try:
        _ask({}, project, rd, 'claude', 'review this', 'reviewer', 'review-1-claude.json', readonly=True)
    finally:
        runner._capture = _capture
    assert 'correctness > security > data loss' in prompts[0], 'code-review skill was not injected'
