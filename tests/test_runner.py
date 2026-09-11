import re
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from ai_team.runner import doctor, run_team, _agy
from ai_team.installer import install
from ai_team.utils import save_json, load_json

def init_git_repo(path: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True, capture_output=True)
    readme = path / "README.md"
    readme.write_text("# Test Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "initial commit"], cwd=path, check=True, capture_output=True)

def test_doctor_success(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    with patch("ai_team.runner.which") as mock_which:
        mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}"
        result = doctor(tmp_path)
        assert result == 0

def test_doctor_missing_required_cli(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    with patch("ai_team.runner.which") as mock_which:
        # agy is missing
        mock_which.side_effect = lambda cmd: None if cmd == "agy" else f"/usr/bin/{cmd}"
        result = doctor(tmp_path)
        assert result == 1

def test_agy_command_builder():
    config = {
        "antigravity": {
            "model": "gemini-test",
            "sandbox": True,
            "fullAuto": False,
            "printTimeout": "30m"
        }
    }
    cmd = _agy(config, "test prompt", "architect", "high")
    assert "agy" in cmd
    assert "-p" in cmd
    assert "test prompt" in cmd
    assert "--agent" in cmd
    assert "architect" in cmd
    assert "--model" in cmd
    assert "gemini-test" in cmd
    assert "--effort" in cmd
    assert "high" in cmd
    assert "--sandbox" in cmd
    assert "--dangerously-skip-permissions" not in cmd

def test_agy_command_builder_full_auto():
    config = {
        "antigravity": {
            "sandbox": False,
            "fullAuto": True
        }
    }
    cmd = _agy(config, "prompt", "implementer", "low")
    assert "--dangerously-skip-permissions" in cmd
    assert "--sandbox" not in cmd

def test_run_team_dirty_working_tree_raises(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")

    # Dirty the working tree
    (tmp_path / "dirty.txt").write_text("uncommitted", encoding="utf-8")

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"):
        with pytest.raises(RuntimeError, match="Working tree nie jest czysty"):
            run_team(tmp_path, "test task")

def test_run_team_triage_routing_low(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")
    # Commit installation so working tree is clean
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "install ai-team"], cwd=tmp_path, check=True, capture_output=True)

    called_commands = []

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        called_commands.append(cmd)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Check if triage
        if "triage" in cmd:
            out.write_text("RISK: LOW\nAnalysis: simple typo fix", encoding="utf-8")
        elif "verifier" in cmd:
            out.write_text("VERDICT: PASS\nAll tests passed", encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        code = run_team(tmp_path, "Fix typo in readme")
        assert code == 0

        # In LOW risk: no external reviewer (neither claude nor codex) should be called
        assert not any("claude" in cmd for cmd in called_commands)
        assert not any("codex" in cmd for cmd in called_commands)

def test_run_team_triage_routing_medium(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "install ai-team"], cwd=tmp_path, check=True, capture_output=True)

    called_commands = []

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        called_commands.append(cmd)
        out.parent.mkdir(parents=True, exist_ok=True)
        if "triage" in cmd:
            out.write_text("RISK: MEDIUM\nFeature addition", encoding="utf-8")
        elif "codex" in cmd:
            out.write_text("Codex Review: Looks good", encoding="utf-8")
        elif "verifier" in cmd:
            out.write_text("VERDICT: PASS\nVerified", encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        code = run_team(tmp_path, "Add helper module")
        assert code == 0

        # Codex must be called, Claude must NOT be called for MEDIUM
        assert any("codex" in cmd for cmd in called_commands)
        assert not any("claude" in cmd for cmd in called_commands)

def test_run_team_triage_routing_high(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "install ai-team"], cwd=tmp_path, check=True, capture_output=True)

    called_commands = []

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        called_commands.append(cmd)
        out.parent.mkdir(parents=True, exist_ok=True)
        if "triage" in cmd:
            out.write_text("RISK: HIGH\nAuth change", encoding="utf-8")
        elif "claude" in cmd:
            out.write_text("Claude review findings", encoding="utf-8")
        elif "codex" in cmd:
            out.write_text("Codex review findings", encoding="utf-8")
        elif "verifier" in cmd:
            out.write_text("VERDICT: PASS_WITH_NOTES\nApproved", encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        code = run_team(tmp_path, "Refactor authentication")
        assert code == 0

        # Both Claude and Codex must be called for HIGH
        assert any("claude" in cmd for cmd in called_commands)
        assert any("codex" in cmd for cmd in called_commands)

def test_run_team_changes_required_exit_code(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "install ai-team"], cwd=tmp_path, check=True, capture_output=True)

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        out.parent.mkdir(parents=True, exist_ok=True)
        if "triage" in cmd:
            out.write_text("RISK: LOW", encoding="utf-8")
        elif "verifier" in cmd:
            out.write_text("VERDICT: CHANGES_REQUIRED\nTests failed.", encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        code = run_team(tmp_path, "Failing change")
        assert code == 2

def test_availability_fallback_disabled_raises(tmp_path):
    init_git_repo(tmp_path)
    install(tmp_path, "core")
    # Set availabilityFallback to false in config
    cfg_file = tmp_path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["availabilityFallback"] = False
    save_json(cfg_file, cfg)

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update config"], cwd=tmp_path, check=True, capture_output=True)

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        out.parent.mkdir(parents=True, exist_ok=True)
        if "triage" in cmd:
            out.write_text("RISK: HIGH", encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    def mock_which(cmd):
        if cmd in {"git", "agy"}:
            return f"/usr/bin/{cmd}"
        return None  # claude and codex missing

    with patch("ai_team.runner.which", side_effect=mock_which), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        with pytest.raises(RuntimeError, match="Claude wymagany przez policy"):
            run_team(tmp_path, "High risk task without claude")
