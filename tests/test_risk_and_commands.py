"""Risk escalation and per-role provider control from the 2026-09 framework audit."""
import subprocess

import pytest

from ai_team.runner import _risk, _command


def git(path, *args):
    return subprocess.run(['git', *args], cwd=path, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.test')
    git(tmp_path, 'config', 'commit.gpgsign', 'false')
    (tmp_path / 'README.md').write_text('Initial\n', encoding='utf-8')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'base')
    return tmp_path


def change(repo, relative, content='updated\n'):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return git(repo, 'rev-parse', 'HEAD')


@pytest.mark.parametrize('relative', ['ai-team.config.json', 'AI_TEAM.md', 'PROJECT_CONTEXT.md',
                                      '.agents/agents/reviewer.md'])
def test_guardrail_files_always_escalate_to_high(repo, relative):
    """An agent must not be able to weaken its own review policy unreviewed."""
    base = change(repo, relative)
    assert _risk(repo, base, 'LOW', {}) == 'HIGH'


@pytest.mark.parametrize('relative', [
    'src/middleware/session_guard.py',
    'app/api/checkout.py',
    'src/billing/charge_card.py',
    'alembic/versions/8f1c_add_role_column.py',
    'src/access/rbac.py',
    'src/core/jwt.py',
    'src/sso/saml_handler.py',
    'ops/terraform.tfvars',
    'Containerfile',
    '.gitlab-ci.yml',
    'Jenkinsfile',
])
def test_sensitive_paths_missed_by_the_old_globs_now_escalate(repo, relative):
    base = change(repo, relative)
    assert _risk(repo, base, 'LOW', {}) == 'HIGH'


def test_destructive_sql_in_a_generic_file_escalates(repo):
    """Filenames are a weak signal; escalate on what the change actually does."""
    base = change(repo, 'src/reports/export.py', 'def purge():\n    db.execute("DELETE FROM users")\n')
    assert _risk(repo, base, 'LOW', {}) == 'HIGH'


def test_ordinary_change_stays_low(repo):
    base = change(repo, 'src/utils/format.py', 'def title(text):\n    return text.title()\n')
    assert _risk(repo, base, 'LOW', {}) == 'LOW'


def test_multiple_ordinary_files_still_reach_medium(repo):
    base = change(repo, 'src/utils/format.py', 'def a():\n    return 1\n')
    change(repo, 'src/utils/parse.py', 'def b():\n    return 2\n')
    assert _risk(repo, base, 'LOW', {}) == 'MEDIUM'


def test_agy_effort_comes_from_configuration(repo):
    config = {'antigravity': {'triageEffort': 'medium', 'implementationEffort': 'low',
                              'verificationEffort': 'high'}}
    triage = _command(config, 'agy', 'p', 'triage')
    assert triage[triage.index('--effort') + 1] == 'medium'
    orchestrator = _command(config, 'agy', 'p', 'orchestrator')
    assert orchestrator[orchestrator.index('--effort') + 1] == 'low'
    verifier = _command(config, 'agy', 'p', 'verifier', readonly=True)
    assert verifier[verifier.index('--effort') + 1] == 'high'


def test_agy_effort_defaults_are_cheap_for_read_only_roles():
    assert _command({}, 'agy', 'p', 'triage')[-1] != '--effort'
    triage = _command({}, 'agy', 'p', 'triage')
    assert triage[triage.index('--effort') + 1] == 'low'
    verifier = _command({}, 'agy', 'p', 'verifier', readonly=True)
    assert verifier[verifier.index('--effort') + 1] == 'medium'


def test_provider_args_reach_codex_per_role():
    config = {'providerArgs': {'codex': {'reviewer': ['--reasoning-effort', 'medium']}}}
    cmd = _command(config, 'codex', 'p', 'reviewer', readonly=True)
    assert cmd[cmd.index('--reasoning-effort') + 1] == 'medium'
    assert '--reasoning-effort' not in _command(config, 'codex', 'p', 'triage', readonly=True)


def test_provider_args_override_the_default_claude_turn_limit():
    config = {'providerArgs': {'claude': {'reviewer': ['--max-turns', '12']}}}
    cmd = _command(config, 'claude', 'p', 'reviewer', readonly=True)
    assert cmd.count('--max-turns') == 1
    assert cmd[cmd.index('--max-turns') + 1] == '12'


def test_provider_args_default_role_applies_to_every_stage():
    config = {'providerArgs': {'claude': {'default': ['--verbose']}}}
    assert '--verbose' in _command(config, 'claude', 'p', 'triage', readonly=True)


def test_models_can_be_selected_per_role():
    config = {'models': {'claude': {'default': 'opus', 'triage': 'haiku'}}}
    triage = _command(config, 'claude', 'p', 'triage', readonly=True)
    assert triage[triage.index('--model') + 1] == 'haiku'
    orchestrator = _command(config, 'claude', 'p', 'orchestrator')
    assert orchestrator[orchestrator.index('--model') + 1] == 'opus'


def test_legacy_flat_model_mapping_still_works():
    cmd = _command({'models': {'claude': 'opus'}}, 'claude', 'p', 'reviewer', readonly=True)
    assert cmd[cmd.index('--model') + 1] == 'opus'
