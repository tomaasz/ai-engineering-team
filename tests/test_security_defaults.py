from pathlib import Path
from ai_team.utils import template_root, load_json
import ai_team.runner as runner_module

def test_template_config_security_defaults():
    config_file = template_root() / "ai-team.config.json"
    assert config_file.is_file()
    cfg = load_json(config_file)

    # Crucial security controls
    assert cfg.get("requireCleanWorkingTree") is True
    assert cfg.get("createBranchForEachRun") is True
    assert cfg.get("branchPrefix") == "ai/"

    antigravity_cfg = cfg.get("antigravity", {})
    assert antigravity_cfg.get("sandbox") is True
    assert antigravity_cfg.get("fullAuto") is False

    # Ensure no dangerous auto-actions are enabled or configured
    assert "autoPush" not in cfg or cfg["autoPush"] is False
    assert "autoDeploy" not in cfg or cfg["autoDeploy"] is False
    assert "autoMerge" not in cfg or cfg["autoMerge"] is False

def test_runner_code_has_no_destructive_git_commands():
    runner_src = Path(runner_module.__file__).read_text(encoding="utf-8")

    # Ensure forbidden git operations are never invoked in runner code
    forbidden_terms = [
        "push",
        "merge",
        "reset --hard",
        "clean -fd",
        "clean -f",
        "branch -D",
        "branch -d",
    ]

    for term in forbidden_terms:
        # Check that runner does not execute any of these as git command calls
        # Note: 'git push', 'git merge' etc.
        assert f"['git', '{term}']" not in runner_src
        assert f"['git', *['{term}']" not in runner_src
        assert f"git {term}" not in runner_src or "Nie wykonuj" in runner_src
