import subprocess
from pathlib import Path
import pytest
from ai_team.installer import install, update, status, uninstall, install_workflow, configure_gitignore, VERSION
from ai_team.utils import load_json, sha256_file

def init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True, capture_output=True)

def test_install_empty_repo(tmp_path):
    init_git_repo(tmp_path)
    managed = install(tmp_path, "core")

    # State verification
    st = status(tmp_path)
    assert st["installed"] is True
    assert st["frameworkVersion"] == VERSION
    assert st["profile"] == "core"
    assert st["managedFiles"] > 0

    # Files presence
    assert (tmp_path / "AI_TEAM.md").is_file()
    assert (tmp_path / "PROJECT_CONTEXT.md").is_file()
    assert (tmp_path / "ai-team.config.json").is_file()
    assert (tmp_path / ".vscode" / "tasks.json").is_file()
    assert (tmp_path / ".ai" / "runs").is_dir()
    assert (tmp_path / ".ai-team" / "state.json").is_file()

def test_install_profile_selection(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "python")
    st = status(tmp_path)
    assert st["profile"] == "python"

    # Python profile specific files
    assert (tmp_path / ".agents" / "skills" / "python" / "python-quality" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "skills" / "python" / "python-quality" / "SKILL.md").is_file()
    # Web skills should not be present in python profile
    assert not (tmp_path / ".agents" / "skills" / "browser").exists()

def test_install_preserves_existing_project_context(tmp_path):
    init_git_repo(tmp_path)
    custom_content = "# My Custom Project Context\nSpecial domain logic here."
    (tmp_path / "PROJECT_CONTEXT.md").write_text(custom_content, encoding="utf-8")

    install(tmp_path, "core")
    assert (tmp_path / "PROJECT_CONTEXT.md").read_text(encoding="utf-8") == custom_content

def test_install_preserves_existing_config(tmp_path):
    init_git_repo(tmp_path)
    custom_cfg = '{"customSetting": true}'
    (tmp_path / "ai-team.config.json").write_text(custom_cfg, encoding="utf-8")

    install(tmp_path, "core")
    assert (tmp_path / "ai-team.config.json").read_text(encoding="utf-8") == custom_cfg

def test_update_clean(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")
    conflicts = update(tmp_path)
    assert conflicts == []

def test_update_conflict_detection(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    # Manually modify a managed file (e.g. AI_TEAM.md)
    ai_team_file = tmp_path / "AI_TEAM.md"
    ai_team_file.write_text("Locally customized rules.", encoding="utf-8")

    conflicts = update(tmp_path)
    assert "AI_TEAM.md" in conflicts
    # Verify local modified file was NOT overwritten
    assert ai_team_file.read_text(encoding="utf-8") == "Locally customized rules."
    # Verify upstream template was placed in conflicts directory
    conflict_copy = tmp_path / ".ai-team" / "conflicts" / "AI_TEAM.md"
    assert conflict_copy.is_file()
    assert conflict_copy.read_text(encoding="utf-8") != "Locally customized rules."

def test_uninstall_and_dry_run(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    # Modify one managed file locally
    (tmp_path / "AGENTS.md").write_text("User custom agents config", encoding="utf-8")

    # Dry-run uninstall
    removed_dry, skipped_dry = uninstall(tmp_path, dry_run=True)
    assert "AI_TEAM.md" in removed_dry
    assert "AGENTS.md" in skipped_dry  # skipped because hash changed
    assert ".vscode/tasks.json" in skipped_dry  # skipped by design in uninstall

    # Verify files still exist after dry-run
    assert (tmp_path / "AI_TEAM.md").is_file()
    assert (tmp_path / ".ai-team" / "state.json").is_file()

    # Actual uninstall
    removed, skipped = uninstall(tmp_path, dry_run=False)
    assert "AI_TEAM.md" in removed
    assert not (tmp_path / "AI_TEAM.md").exists()
    assert (tmp_path / "AGENTS.md").exists()  # locally modified file preserved
    assert not (tmp_path / ".ai-team" / "state.json").exists()  # state removed

def test_uninstall_uninstalled_raises(tmp_path):
    with pytest.raises(RuntimeError, match="Framework nie jest zainstalowany"):
        uninstall(tmp_path)

def test_update_uninstalled_raises(tmp_path):
    with pytest.raises(RuntimeError, match="Framework nie jest zainstalowany"):
        update(tmp_path)


def test_ensure_gitignores_on_install_and_update(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    ai_ign = tmp_path / ".ai" / ".gitignore"
    team_ign = tmp_path / ".ai-team" / ".gitignore"

    assert ai_ign.is_file()
    assert "runs/" in ai_ign.read_text(encoding="utf-8")
    assert "latest.txt" in ai_ign.read_text(encoding="utf-8")

    assert team_ign.is_file()
    assert "conflicts/" in team_ign.read_text(encoding="utf-8")
    assert "backups/" in team_ign.read_text(encoding="utf-8")

    # Remove them and ensure update() restores them
    ai_ign.unlink()
    team_ign.unlink()
    update(tmp_path)
    assert ai_ign.is_file()
    assert team_ign.is_file()


def test_install_workflow(tmp_path):
    init_git_repo(tmp_path)
    dest = install_workflow(tmp_path)
    assert dest.is_file()
    assert dest == tmp_path / ".github" / "workflows" / "ai-team-update.yml"
    content = dest.read_text(encoding="utf-8")
    assert "AI Engineering Team Update" in content
    assert "ai-team update" in content


def test_configure_gitignore_standard(tmp_path):
    init_git_repo(tmp_path)
    res = configure_gitignore(tmp_path, private=False)
    assert res == "configured"
    ign_file = tmp_path / ".gitignore"
    assert ign_file.is_file()
    text = ign_file.read_text(encoding="utf-8")
    assert ".ai/runs/" in text
    assert ".ai-team/conflicts/" in text

    # Calling again should be idempotent
    res2 = configure_gitignore(tmp_path, private=False)
    assert res2 == "up-to-date"


def test_configure_gitignore_private(tmp_path):
    init_git_repo(tmp_path)
    res = configure_gitignore(tmp_path, private=True)
    assert res == "private-configured"
    exclude_file = tmp_path / ".git" / "info" / "exclude"
    assert exclude_file.is_file()
    text = exclude_file.read_text(encoding="utf-8")
    assert ".ai/" in text
    assert ".agents/" in text
    assert "PROJECT_CONTEXT.md" in text

    # Calling again should be idempotent
    res2 = configure_gitignore(tmp_path, private=True)
    assert res2 == "up-to-date"


def test_status_upstream_check(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    # Mock check_upstream_version to simulate newer version
    import ai_team.utils
    monkeypatch.setattr(ai_team.utils, "check_upstream_version", lambda: "99.0.0")

    st = status(tmp_path, check_upstream=True)
    assert st["installed"] is True
    assert st["upstreamVersion"] == "99.0.0"
    assert st["outdated"] is True

    # When up to date
    monkeypatch.setattr(ai_team.utils, "check_upstream_version", lambda: VERSION)
    st2 = status(tmp_path, check_upstream=True)
    assert st2["upstreamVersion"] == VERSION
    assert st2["outdated"] is False
