import pytest
from pathlib import Path
import subprocess
from ai_team.skills import (
    detect_stack,
    suggest_skills,
    list_skills,
    add_skill,
    remove_skill,
    filter_skills_for_task,
    proactive_skill_provision,
)
from ai_team.installer import install, status
from ai_team.cli import main, parser


def init_git_repo(path: Path):
    subprocess.run(['git', 'init'], cwd=path, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=path, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=path, check=True, capture_output=True)


def test_detect_stack_python(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "test"\n', encoding='utf-8')
    stack = detect_stack(tmp_path)
    assert 'python' in stack['languages']
    assert 'pyproject.toml' in stack['markers']
    assert stack['recommended_profile'] == 'python'


def test_detect_stack_postgres(tmp_path):
    (tmp_path / 'alembic.ini').write_text('# config', encoding='utf-8')
    migrations = tmp_path / 'migrations'
    migrations.mkdir()
    (migrations / '001_initial.sql').write_text('CREATE TABLE t();', encoding='utf-8')
    stack = detect_stack(tmp_path)
    assert 'postgres' in stack['databases']
    assert stack['recommended_profile'] == 'postgres'


def test_detect_stack_web(tmp_path):
    (tmp_path / 'playwright.config.ts').write_text('export default {}', encoding='utf-8')
    stack = detect_stack(tmp_path)
    assert 'browser' in stack['tools']
    assert stack['recommended_profile'] == 'web'


def test_detect_stack_docker(tmp_path):
    (tmp_path / 'Dockerfile').write_text('FROM alpine\n', encoding='utf-8')
    stack = detect_stack(tmp_path)
    assert 'docker' in stack['tools']
    assert 'Dockerfile' in stack['markers']


def test_detect_stack_empty(tmp_path):
    stack = detect_stack(tmp_path)
    assert stack['languages'] == []
    assert stack['recommended_profile'] == 'core'


def test_suggest_skills_en_and_pl(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "test"\n', encoding='utf-8')
    (tmp_path / 'Dockerfile').write_text('FROM python:3.11\n', encoding='utf-8')

    sugs_en = suggest_skills(tmp_path, lang='en')
    ids_en = {s['id'] for s in sugs_en}
    assert 'core/code-review' in ids_en
    assert 'python/python-quality' in ids_en
    assert 'devops/docker-quality' in ids_en
    assert 'security/secure-coding' in ids_en

    sugs_pl = suggest_skills(tmp_path, lang='pl')
    py_sug_pl = next(s for s in sugs_pl if s['id'] == 'python/python-quality')
    assert 'Python' in py_sug_pl['reason']


def test_list_skills_in_installed_project(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    data = list_skills(tmp_path)
    installed_ids = {s['id'] for s in data['installed']}
    assert 'core/code-review' in installed_ids
    assert 'core/task-planning' in installed_ids
    assert 'core/testing' in installed_ids

    review_item = next(s for s in data['installed'] if s['id'] == 'core/code-review')
    assert review_item['status'] == 'MANAGED'
    assert len(review_item['description']) > 0

    available_ids = {s['id'] for s in data['available']}
    assert 'devops/docker-quality' in available_ids
    assert 'security/secure-coding' in available_ids


def test_add_and_remove_skill(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    # Add docker-quality
    res_add = add_skill(tmp_path, 'devops/docker-quality')
    assert res_add['id'] == 'devops/docker-quality'
    assert (tmp_path / '.agents/skills/devops/docker-quality/SKILL.md').exists()
    assert (tmp_path / '.claude/skills/devops/docker-quality/SKILL.md').exists()

    data = list_skills(tmp_path)
    docker_item = next(s for s in data['installed'] if s['id'] == 'devops/docker-quality')
    assert docker_item['status'] == 'MANAGED'

    # Remove docker-quality
    res_rem = remove_skill(tmp_path, 'devops/docker-quality')
    assert res_rem['id'] == 'devops/docker-quality'
    assert not (tmp_path / '.agents/skills/devops/docker-quality/SKILL.md').exists()
    assert not (tmp_path / '.claude/skills/devops/docker-quality/SKILL.md').exists()


def test_add_skill_by_short_name(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    res = add_skill(tmp_path, 'secure-coding')
    assert res['id'] == 'security/secure-coding'
    assert (tmp_path / '.agents/skills/security/secure-coding/SKILL.md').exists()


def test_remove_skill_protection_for_local_project(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    local_skill = tmp_path / '.agents/skills/project/my-guidelines/SKILL.md'
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text('---\nname: my-guidelines\n---\n# My guidelines', encoding='utf-8')

    with pytest.raises(RuntimeError, match="Cannot remove project-local skill"):
        remove_skill(tmp_path, 'project/my-guidelines', force=False)

    remove_skill(tmp_path, 'project/my-guidelines', force=True)
    assert not local_skill.exists()


def test_filter_skills_for_task(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'full')

    # Test filtering with SQL prompt
    sql_skills = filter_skills_for_task(tmp_path, prompt='Fix postgres query in migration')
    sql_names = [p.parent.name for p in sql_skills]
    assert 'code-review' in sql_names
    assert 'postgres' in sql_names

    # Test filtering with touched python files
    py_skills = filter_skills_for_task(tmp_path, touched_files=['src/main.py'])
    py_names = [p.parent.name for p in py_skills]
    assert 'python-quality' in py_names


def test_install_auto_detect(tmp_path):
    init_git_repo(tmp_path)
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "demo"\n', encoding='utf-8')

    install(tmp_path, 'auto')
    st = status(tmp_path)
    assert st['installed'] is True
    assert st['profile'] == 'python'
    assert (tmp_path / '.agents/skills/python/python-quality/SKILL.md').exists()


def test_cli_skills_commands(tmp_path, monkeypatch, capsys):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    # 1. CLI skills list
    monkeypatch.setattr('sys.argv', ['ai-team', 'skills', 'list', str(tmp_path)])
    code = main()
    assert code == 0
    out = capsys.readouterr().out
    assert 'Installed' in out
    assert 'core/code-review' in out

    # 2. CLI skills suggest
    (tmp_path / 'Dockerfile').write_text('FROM alpine\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['ai-team', 'skill', 'suggest', str(tmp_path)])
    code = main()
    assert code == 0
    out = capsys.readouterr().out
    assert 'Tech Stack Analysis' in out
    assert 'Dockerfile' in out

    # 3. CLI skills add
    monkeypatch.setattr('sys.argv', ['ai-team', 'skill', 'add', 'devops/docker-quality', str(tmp_path)])
    code = main()
    assert code == 0
    out = capsys.readouterr().out
    assert '[ADDED] devops/docker-quality' in out
    assert (tmp_path / '.agents/skills/devops/docker-quality/SKILL.md').exists()

    # 4. CLI skills remove
    monkeypatch.setattr('sys.argv', ['ai-team', 'skill', 'remove', 'devops/docker-quality', str(tmp_path)])
    code = main()
    assert code == 0
    out = capsys.readouterr().out
    assert '[REMOVED] devops/docker-quality' in out
    assert not (tmp_path / '.agents/skills/devops/docker-quality/SKILL.md').exists()


def test_proactive_skill_provision_from_prompt(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    # Agent detects requirement from prompt and autonomously provisions the skill
    provisioned = proactive_skill_provision(tmp_path, prompt="Please containerize application with Dockerfile")
    assert any(p['id'] == 'devops/docker-quality' for p in provisioned)
    assert (tmp_path / '.agents/skills/devops/docker-quality/SKILL.md').exists()
    assert (tmp_path / '.claude/skills/devops/docker-quality/SKILL.md').exists()

    # Calling again is a no-op (skill already provisioned)
    provisioned_again = proactive_skill_provision(tmp_path, prompt="Please containerize application with Dockerfile")
    assert provisioned_again == []


def test_proactive_skill_provision_from_touched_files(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, 'core')

    # Agent completed an implementation that touched/created a SQL migration
    provisioned = proactive_skill_provision(tmp_path, touched_files=['migrations/001_create_users.sql'])
    assert any(p['id'] == 'postgres/postgres' for p in provisioned)
    assert (tmp_path / '.agents/skills/postgres/postgres/SKILL.md').exists()
    assert (tmp_path / '.claude/skills/postgres/postgres/SKILL.md').exists()


def test_cli_no_auto_skills_flag():
    p = parser()
    args = p.parse_args(['run', '.', 'test prompt', '--no-auto-skills'])
    assert args.no_auto_skills is True
