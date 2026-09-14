"""Installer and profile fixes from the 2026-09 framework audit."""
import json
import subprocess

import pytest

from ai_team.installer import install, update, LOCAL_PREFIXES
from ai_team.utils import load_json, template_root, profiles_root


def git(path, *args):
    return subprocess.run(['git', *args], cwd=path, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 'test@example.test')
    return tmp_path


def test_claude_reviewers_also_get_a_project_skills_directory():
    """A project-specific skill only agy could read left Claude reviewing without it."""
    assert (template_root() / '.claude/skills/project/README.md').is_file()
    assert '.claude/skills/project/' in LOCAL_PREFIXES


@pytest.mark.parametrize('profile', ['core', 'python', 'web', 'postgres', 'ocr', 'geneteka', 'full'])
def test_every_profile_ships_both_project_skill_directories(profile):
    included = load_json(profiles_root() / f'{profile}.json')['include']
    assert any(x.startswith('.agents/skills/project') or x == '.agents' for x in included)
    assert any(x.startswith('.claude/skills/project') or x == '.claude' for x in included)


def test_project_owned_claude_skill_survives_update(repo):
    install(repo, 'core')
    custom = repo / '.claude/skills/project/house-style/SKILL.md'
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text('# house style\nUse dataclasses.\n', encoding='utf-8')
    assert not update(repo, 'core')
    assert 'dataclasses' in custom.read_text(encoding='utf-8')


def test_data_profile_seeds_sensitive_risk_paths(repo):
    """A Postgres project should not start with an empty riskPaths list."""
    install(repo, 'postgres')
    risk_paths = load_json(repo / 'ai-team.config.json')['riskPaths']
    assert any('migrations' in glob for glob in risk_paths['HIGH'])
    assert any(glob.endswith('.sql') for glob in risk_paths['HIGH'])


def test_profile_defaults_never_overwrite_an_existing_config(repo):
    (repo / 'ai-team.config.json').write_text(json.dumps({'primaryProvider': 'codex'}), encoding='utf-8')
    install(repo, 'postgres')
    assert load_json(repo / 'ai-team.config.json') == {'primaryProvider': 'codex'}


def test_merge_reports_when_vscode_comments_were_dropped(repo, capsys):
    tasks = repo / '.vscode/tasks.json'
    tasks.parent.mkdir(parents=True)
    tasks.write_text('{\n  // keep me\n  "version": "2.0.0",\n  "tasks": []\n}\n', encoding='utf-8')
    install(repo, 'core')
    assert 'comments removed' in capsys.readouterr().out


@pytest.mark.parametrize('name,heading', [('PROJECT_CONTEXT.md', 'Patterns to imitate'),
                                          ('PROJECT_CONTEXT.pl.md', 'Wzorce do naśladowania')])
def test_project_context_asks_for_concrete_style_references(name, heading):
    """Models copy style from named examples far better than from abstract rules."""
    assert heading in (template_root() / name).read_text(encoding='utf-8')
