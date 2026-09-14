"""Bootstrap language choice propagates to the installed templates and to runner prompts."""
import subprocess

import pytest

from ai_team.installer import install, update, status
from ai_team.utils import load_json, template_root


def git(path, *args):
    return subprocess.run(['git', *args], cwd=path, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.test')
    return tmp_path


def test_package_ships_both_languages_for_every_agent_facing_template():
    """A Polish project must not fall back to English instructions for some roles."""
    english = {p.relative_to(template_root()).as_posix()
               for p in template_root().rglob('*.md') if not p.name.endswith('.pl.md')}
    polish = {p.relative_to(template_root()).as_posix().replace('.pl.md', '.md')
              for p in template_root().rglob('*.pl.md')}
    assert english, 'no English templates found'
    assert not english - polish, f'templates without a Polish variant: {sorted(english - polish)}'


def test_english_install_writes_english_templates_under_canonical_names(repo):
    install(repo, 'core', lang='en')
    assert not list(repo.rglob('*.pl.md')), 'language variants must not be installed verbatim'
    assert 'AI Engineering Team' in (repo / 'AI_TEAM.md').read_text(encoding='utf-8')
    assert 'Risk' in (repo / 'AI_TEAM.md').read_text(encoding='utf-8')


def test_polish_install_writes_polish_templates_under_canonical_names(repo):
    install(repo, 'core', lang='pl')
    assert not list(repo.rglob('*.pl.md'))
    text = (repo / 'AI_TEAM.md').read_text(encoding='utf-8')
    assert 'Ryzyko' in text
    assert (repo / '.agents/agents/reviewer.md').is_file()


def test_installed_language_is_recorded_and_reused_by_update(repo):
    install(repo, 'core', lang='pl')
    assert status(repo)['language'] == 'pl'
    update(repo)
    assert status(repo)['language'] == 'pl'
    assert 'Ryzyko' in (repo / 'AI_TEAM.md').read_text(encoding='utf-8')


def test_update_can_switch_language(repo):
    install(repo, 'core', lang='pl')
    update(repo, lang='en')
    assert status(repo)['language'] == 'en'


def test_unknown_language_is_rejected(repo):
    with pytest.raises(RuntimeError, match='language'):
        install(repo, 'core', lang='de')


def test_install_seeds_the_language_into_the_project_config(repo):
    install(repo, 'core', lang='pl')
    assert load_json(repo / 'ai-team.config.json')['language'] == 'pl'


def test_runner_prompts_follow_the_configured_language():
    from ai_team.runner import _command, _verdict_prompt
    assert 'Zwróć' in _verdict_prompt({'language': 'pl'})
    assert 'Return' in _verdict_prompt({})
    polish = _command({'language': 'pl'}, 'claude', 'task', 'reviewer', readonly=True)
    assert any('Twoja rola' in part for part in polish)
    english = _command({}, 'claude', 'task', 'reviewer', readonly=True)
    assert any('Your role is' in part for part in english)


def test_skill_injection_uses_only_the_installed_language(repo):
    """The point of choosing at install time is that a run never carries both languages."""
    from ai_team.runner import _skill_context
    install(repo, 'core', lang='pl')
    context = _skill_context(repo)
    assert 'Priorytet' in context
    assert 'Priority:' not in context


def test_cli_exposes_the_language_flag():
    from ai_team.cli import parser
    args = parser().parse_args(['install', '.', '--profile', 'core', '--lang', 'pl'])
    assert args.lang == 'pl'
    assert parser().parse_args(['update', '.', '--lang', 'en']).lang == 'en'
    assert parser().parse_args(['install', '.']).lang is None


def test_config_validates_the_language_key(tmp_path):
    from ai_team.config import validate
    base = {'primaryProvider': 'agy',
            'reviewPolicy': {'LOW': ['codex'], 'MEDIUM': ['codex'], 'HIGH': ['claude', 'codex']},
            'verification': {'commands': [], 'noChecksReason': 'docs only'}}
    assert validate({**base, 'language': 'pl'}, tmp_path)['language'] == 'pl'
    with pytest.raises(ValueError, match='language'):
        validate({**base, 'language': 'de'}, tmp_path)
