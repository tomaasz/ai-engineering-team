import json
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


def _setup_installed_repo(path: Path):
    init_git_repo(path)
    install(path, "core")
    (path / "PROJECT_CONTEXT.md").write_text("# Test Project\nContext ready without placeholders.\n", encoding="utf-8")
    cfg_file = path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["verification"]["noChecksReason"] = "test suite running mock verification"
    save_json(cfg_file, cfg)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "install ai-team and configure"], cwd=path, check=True, capture_output=True)


def test_doctor_success(tmp_path):
    _setup_installed_repo(tmp_path)

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
            "model": "gemini-2.5-pro",
            "fullAuto": False,
            "sandbox": True
        }
    }
    cmd = _agy(config, "prompt text", agent="orchestrator", effort="high")

    assert cmd[0] == "agy"
    assert "-p" in cmd
    assert "prompt text" in cmd
    assert "--agent" in cmd
    assert "orchestrator" in cmd
    assert "--effort" in cmd
    assert "high" in cmd
    assert "--model" in cmd
    assert "gemini-2.5-pro" in cmd
    assert "--sandbox" in cmd
    assert "--dangerously-skip-permissions" not in cmd


def test_agy_command_builder_full_auto():
    config = {
        "antigravity": {
            "model": "gemini-2.5-flash",
            "fullAuto": True,
            "sandbox": False
        }
    }
    cmd = _agy(config, "prompt text", agent="developer", effort=None)

    assert "--dangerously-skip-permissions" in cmd
    assert "--sandbox" not in cmd


def test_run_team_dirty_working_tree_raises(tmp_path):
    _setup_installed_repo(tmp_path)

    # Dirty the working tree
    (tmp_path / "dirty.txt").write_text("uncommitted", encoding="utf-8")

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"):
        with pytest.raises(RuntimeError, match="Working tree"):
            run_team(tmp_path, "test task")


def test_run_team_triage_routing_low(tmp_path):
    _setup_installed_repo(tmp_path)
    cfg_file = tmp_path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["reviewPolicy"]["LOW"] = []
    cfg["allowUnreviewedLowRisk"] = True
    save_json(cfg_file, cfg)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "allow unreviewed low risk"], cwd=tmp_path, check=True, capture_output=True)

    called_commands = []

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        called_commands.append(cmd)
        out.parent.mkdir(parents=True, exist_ok=True)
        filename = out.name
        if "triage" in filename:
            out.write_text(json.dumps({"risk": "LOW"}), encoding="utf-8")
        elif "verif" in filename:
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "All tests passed"}), encoding="utf-8")
        elif "--output-last-message" in cmd:
            idx = cmd.index("--output-last-message")
            output_file = Path(cmd[idx + 1])
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Reviewed"}), encoding="utf-8")
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Reviewed"}), encoding="utf-8")
        elif "review" in filename or "claude" in str(cmd):
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Reviewed"}), encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        code = run_team(tmp_path, "Fix typo in readme")
        assert code == 0

        # In LOW risk: no external reviewer should be called
        assert not any("claude" in cmd for cmd in called_commands)
        assert not any("codex" in cmd for cmd in called_commands)


def test_run_team_triage_routing_medium(tmp_path):
    _setup_installed_repo(tmp_path)

    called_commands = []

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        called_commands.append(cmd)
        out.parent.mkdir(parents=True, exist_ok=True)
        filename = out.name
        if "triage" in filename:
            out.write_text(json.dumps({"risk": "MEDIUM"}), encoding="utf-8")
        elif "--output-last-message" in cmd:
            idx = cmd.index("--output-last-message")
            output_file = Path(cmd[idx + 1])
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Codex Review: Looks good"}), encoding="utf-8")
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Codex Review: Looks good"}), encoding="utf-8")
        elif "verif" in filename:
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Verified"}), encoding="utf-8")
        elif "review" in filename or "claude" in str(cmd):
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Looks good"}), encoding="utf-8")
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
    _setup_installed_repo(tmp_path)

    called_commands = []

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        called_commands.append(cmd)
        out.parent.mkdir(parents=True, exist_ok=True)
        filename = out.name
        if "triage" in filename:
            out.write_text(json.dumps({"risk": "HIGH"}), encoding="utf-8")
        elif "--output-last-message" in cmd:
            idx = cmd.index("--output-last-message")
            output_file = Path(cmd[idx + 1])
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps({"verdict": "PASS_WITH_NOTES", "unresolved": [], "summary": "Approved"}), encoding="utf-8")
            out.write_text(json.dumps({"verdict": "PASS_WITH_NOTES", "unresolved": [], "summary": "Approved"}), encoding="utf-8")
        elif "verif" in filename:
            out.write_text(json.dumps({"verdict": "PASS_WITH_NOTES", "unresolved": [], "summary": "Approved"}), encoding="utf-8")
        elif "review" in filename or "claude" in str(cmd):
            out.write_text(json.dumps({"verdict": "PASS_WITH_NOTES", "unresolved": [], "summary": "Approved"}), encoding="utf-8")
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
    _setup_installed_repo(tmp_path)
    cfg_file = tmp_path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["skipFinalVerificationAtLow"] = False
    save_json(cfg_file, cfg)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "do not skip final verifier"], cwd=tmp_path, check=True, capture_output=True)

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        out.parent.mkdir(parents=True, exist_ok=True)
        filename = out.name
        if "triage" in filename:
            out.write_text(json.dumps({"risk": "LOW"}), encoding="utf-8")
        elif "verif" in filename:
            out.write_text(json.dumps({"verdict": "CHANGES_REQUIRED", "unresolved": ["tests failed"], "summary": "Tests failed."}), encoding="utf-8")
        elif "--output-last-message" in cmd:
            idx = cmd.index("--output-last-message")
            output_file = Path(cmd[idx + 1])
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "review pass"}), encoding="utf-8")
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "review pass"}), encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0

    with patch("ai_team.runner.which", return_value="/usr/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=fake_capture):
        code = run_team(tmp_path, "Failing change")
        assert code == 2


def test_availability_fallback_disabled_raises(tmp_path):
    _setup_installed_repo(tmp_path)
    # Set availabilityFallback to false in config
    cfg_file = tmp_path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["availabilityFallback"] = False
    save_json(cfg_file, cfg)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "update config"], cwd=tmp_path, check=True, capture_output=True)

    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        out.parent.mkdir(parents=True, exist_ok=True)
        filename = out.name
        if "triage" in filename:
            out.write_text(json.dumps({"risk": "HIGH"}), encoding="utf-8")
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
        with pytest.raises(RuntimeError, match=r"(?:Reviewer CLI missing|wymagany)"):
            run_team(tmp_path, "High risk task without claude")
