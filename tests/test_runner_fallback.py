import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from ai_team.runner import doctor, run_team
from ai_team.installer import install
from ai_team.utils import save_json, load_json
from ai_team.cli import parser


def _init_git_repo(path: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True, capture_output=True)
    readme = path / "README.md"
    readme.write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "init"], cwd=path, check=True, capture_output=True)


def _setup_repo(path: Path, single_provider=False):
    _init_git_repo(path)
    install(path, "core")
    (path / "PROJECT_CONTEXT.md").write_text("# Test Repo\nContext ready.\n", encoding="utf-8")
    cfg_file = path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["verification"]["noChecksReason"] = "test fallback suite"
    if single_provider:
        cfg["singleProvider"] = True
    save_json(cfg_file, cfg)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "setup repo"], cwd=path, check=True, capture_output=True)


def _fake_capture_builder(fail_reviewer=None):
    def fake_capture(cmd, cwd, out, err, allow_failure=False):
        out.parent.mkdir(parents=True, exist_ok=True)
        filename = out.name
        if "triage" in filename:
            out.write_text(json.dumps({"risk": "LOW"}), encoding="utf-8")
        elif "verif" in filename:
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "All tests passed"}), encoding="utf-8")
        elif fail_reviewer and fail_reviewer in filename and not "fallback" in filename:
            err.write_text("API rate limit / quota exceeded (429)", encoding="utf-8")
            return 1
        elif "--output-last-message" in cmd:
            idx = cmd.index("--output-last-message")
            output_file = Path(cmd[idx + 1])
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Reviewed"}), encoding="utf-8")
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Reviewed"}), encoding="utf-8")
        elif "review" in filename or "claude" in str(cmd) or "agy" in str(cmd):
            out.write_text(json.dumps({"verdict": "PASS", "unresolved": [], "summary": "Reviewed"}), encoding="utf-8")
        else:
            out.write_text("OK", encoding="utf-8")
        err.write_text("", encoding="utf-8")
        return 0
    return fake_capture


def test_cli_flags_solo_and_fallback():
    p = parser()
    args = p.parse_args(["run", "--solo", "--prompt", "test solo"])
    assert args.solo is True
    assert args.availability_fallback is None

    args = p.parse_args(["run", "--single-provider", "--no-availability-fallback", "--prompt", "test"])
    assert args.solo is True
    assert args.availability_fallback is False

    args = p.parse_args(["doctor", "--solo"])
    assert args.solo is True


def test_doctor_solo_ignores_missing_codex_claude(tmp_path):
    _setup_repo(tmp_path, single_provider=True)
    with patch("ai_team.runner.which") as mock_which:
        mock_which.side_effect = lambda cmd: f"/bin/{cmd}" if cmd in ("git", "agy") else None
        rc = doctor(tmp_path, solo=True)
        assert rc == 0


def test_run_team_solo_executes_with_primary_only(tmp_path):
    _setup_repo(tmp_path)
    called_cmds = []

    def recording_capture(cmd, cwd, out, err, allow_failure=False):
        called_cmds.append(cmd)
        return _fake_capture_builder()(cmd, cwd, out, err, allow_failure)

    with patch("ai_team.runner.which") as mock_which, \
         patch("ai_team.runner._capture", side_effect=recording_capture):
        # codex and claude missing from PATH entirely
        mock_which.side_effect = lambda cmd: f"/bin/{cmd}" if cmd in ("git", "agy") else None
        rc = run_team(tmp_path, "Run in solo mode", solo=True)
        assert rc == 0

        # Verify only agy was used as executable head, never codex or claude
        for cmd in called_cmds:
            executable_head = cmd[0]
            assert executable_head not in ("codex", "claude")
        assert any(cmd[0] == "agy" for cmd in called_cmds)


def test_run_team_fallback_when_reviewer_fails_at_runtime(tmp_path):
    _setup_repo(tmp_path)
    cfg_file = tmp_path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["reviewPolicy"]["LOW"] = ["codex"]
    cfg["test_marker"] = "runtime_fail"
    save_json(cfg_file, cfg)
    subprocess.run(["git", "commit", "-am", "marker runtime fail"], cwd=tmp_path, check=True, capture_output=True)

    with patch("ai_team.runner.which", return_value="/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=_fake_capture_builder(fail_reviewer="codex")):
        rc = run_team(tmp_path, "Run with runtime fallback when codex quota fails", availability_fallback=True)
        assert rc == 0

        runs_dir = tmp_path / ".ai/runs"
        latest_run = (runs_dir / (tmp_path / ".ai/latest.txt").read_text(encoding="utf-8").strip())
        res = load_json(latest_run / "result.json")
        reviews = res.get("reviews", [])
        assert any(r.get("provider") == "agy" and r.get("fallbackFrom") == "codex" for r in reviews)
        assert (latest_run / "review-1-codex-fallback.json").exists()


def test_run_team_no_fallback_raises_on_failure(tmp_path):
    _setup_repo(tmp_path)
    cfg_file = tmp_path / "ai-team.config.json"
    cfg = load_json(cfg_file)
    cfg["reviewPolicy"]["LOW"] = ["codex"]
    cfg["test_marker"] = "no_fallback"
    save_json(cfg_file, cfg)
    subprocess.run(["git", "commit", "-am", "marker no fallback"], cwd=tmp_path, check=True, capture_output=True)

    with patch("ai_team.runner.which", return_value="/bin/tool"), \
         patch("ai_team.runner._capture", side_effect=_fake_capture_builder(fail_reviewer="codex")):
        with pytest.raises(RuntimeError):
            run_team(tmp_path, "Run without fallback", availability_fallback=False)

