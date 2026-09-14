from pathlib import Path
import subprocess
import pytest
from ai_team.cli import parser
from ai_team.skills import suggest_skills, list_skills
from ai_team.installer import install
from ai_team.utils import template_root, profiles_root, load_json


def init_git_repo(path: Path):
    subprocess.run(['git', 'init'], cwd=path, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=path, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=path, check=True, capture_output=True)


def test_audit_cli_args_parsing():
    p = parser()

    # Default invocation
    args = p.parse_args(['audit'])
    assert args.command == 'audit'
    assert args.project == '.'
    assert args.output == 'docs/AUDIT.md'
    assert args.lang == 'pl'
    assert args.worktree is True
    assert args.solo is None
    assert args.auto_merge is False

    # Custom options
    args = p.parse_args([
        'audit', '/path/to/proj',
        '--output', 'audit-report.md',
        '--lang', 'en',
        '--no-worktree',
        '--solo',
        '--auto-merge'
    ])
    assert args.command == 'audit'
    assert args.project == '/path/to/proj'
    assert args.output == 'audit-report.md'
    assert args.lang == 'en'
    assert args.worktree is False
    assert args.solo is True
    assert args.auto_merge is True


def test_audit_templates_exist():
    root = template_root()

    # Skill files
    agents_skill_en = root / '.agents/skills/audit/full-app-audit/SKILL.md'
    agents_skill_pl = root / '.agents/skills/audit/full-app-audit/SKILL.pl.md'
    claude_skill_en = root / '.claude/skills/audit/full-app-audit/SKILL.md'
    claude_skill_pl = root / '.claude/skills/audit/full-app-audit/SKILL.pl.md'

    assert agents_skill_en.is_file()
    assert agents_skill_pl.is_file()
    assert claude_skill_en.is_file()
    assert claude_skill_pl.is_file()

    content = agents_skill_en.read_text(encoding='utf-8')
    assert 'OWASP' in content
    assert 'Architecture' in content
    assert 'Reliability' in content
    assert 'Performance' in content
    assert 'Testing' in content
    assert 'DevOps' in content
    assert 'Findings Matrix' in content

    # Agent persona files
    assert (root / '.agents/agents/auditor.md').is_file()
    assert (root / '.agents/agents/auditor.pl.md').is_file()
    assert (root / '.claude/agents/auditor.md').is_file()
    assert (root / '.claude/agents/auditor.pl.md').is_file()


def test_audit_profiles_inclusion():
    for profile_name in ['core', 'python', 'web', 'postgres', 'ocr', 'geneteka']:
        prof = load_json(profiles_root() / f'{profile_name}.json')
        included = prof['include']
        assert '.agents/skills/audit' in included
        assert '.claude/skills/audit' in included


def test_audit_suggest_skills(tmp_path):
    sugs_pl = suggest_skills(tmp_path, lang='pl')
    audit_pl = next(s for s in sugs_pl if s['id'] == 'audit/full-app-audit')
    assert audit_pl['name'] == 'full-app-audit'
    assert '360°' in audit_pl['reason']

    sugs_en = suggest_skills(tmp_path, lang='en')
    audit_en = next(s for s in sugs_en if s['id'] == 'audit/full-app-audit')
    assert '360°' in audit_en['reason']


def test_audit_installation_in_project(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core', lang='en')

    assert (tmp_path / '.agents/skills/audit/full-app-audit/SKILL.md').is_file()
    assert (tmp_path / '.claude/skills/audit/full-app-audit/SKILL.md').is_file()
    assert (tmp_path / '.agents/agents/auditor.md').is_file()
    assert (tmp_path / '.claude/agents/auditor.md').is_file()

    skills_data = list_skills(tmp_path)
    installed_ids = {s['id'] for s in skills_data['installed']}
    assert 'audit/full-app-audit' in installed_ids
