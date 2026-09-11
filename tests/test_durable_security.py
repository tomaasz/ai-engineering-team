import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_team.cli import parser
from ai_team.runner import _capture, _load_manifest, _validate_resume_context, run_team


def test_capture_sanitizes_secret_environment_and_marks_child(tmp_path):
    out, err = tmp_path / "out", tmp_path / "err"
    script = [sys.executable, "-c", "import os; print(os.getenv('AI_TEAM_SUBPROCESS')); print(os.getenv('SUPER_SECRET'))"]
    old = os.environ.get("SUPER_SECRET")
    os.environ["SUPER_SECRET"] = "do-not-leak"
    try:
        _capture(script, tmp_path, out, err)
    finally:
        if old is None: os.environ.pop("SUPER_SECRET", None)
        else: os.environ["SUPER_SECRET"] = old
    assert out.read_text().splitlines() == ["1", "None"]


def test_capture_rejects_cwd_outside_repo_root(tmp_path):
    with pytest.raises(RuntimeError, match="outside"):
        _capture([sys.executable, "-c", ""], tmp_path / "outside", tmp_path / "o", tmp_path / "e", repo_root=tmp_path)


def test_run_writes_manifest_trace_and_eval_without_prompt(tmp_path, monkeypatch):
    (tmp_path / "ai-team.config.json").write_text(json.dumps({"requireCleanWorkingTree": False, "createBranchForEachRun": False, "reviewPolicy": {"LOW": []}}))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "a@b"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    def fake_capture(cmd, cwd, out, err, allow_failure=False, **kwargs):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("RISK: LOW\n" if "triage" in cmd else ("VERDICT: PASS\n" if "verifier" in cmd else "OK\n"))
        err.write_text("")
        return 0
    monkeypatch.setattr("ai_team.runner.which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr("ai_team.runner._capture", fake_capture)
    secret_prompt = "password=super-secret do thing"
    assert run_team(tmp_path, secret_prompt) == 0
    run_id = (tmp_path / ".ai/latest.txt").read_text().strip()
    rd = tmp_path / ".ai/runs" / run_id
    manifest = json.loads((rd / "run.json").read_text())
    assert manifest["run_id"] == run_id and manifest["final_verdict"] == "PASS"
    assert all("super-secret" not in p.read_text() for p in [rd / "trace.jsonl", rd / "eval.json"])
    rows = [json.loads(x) for x in (rd / "trace.jsonl").read_text().splitlines()]
    assert {r["stage"] for r in rows} >= {"triage", "primary", "verifier"}
    evaluation = json.loads((rd / "eval.json").read_text())
    assert evaluation["passed"] is True and "reasons" in evaluation


def test_resume_parser_and_missing_manifest_refusal(tmp_path):
    args = parser().parse_args(["resume", "abc", str(tmp_path)])
    assert args.command == "resume"
    with pytest.raises(RuntimeError, match="manifest"):
        _load_manifest(tmp_path, "missing")


def test_resume_refuses_changed_branch(tmp_path):
    run_dir = tmp_path / ".ai/runs/x"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps({"branch": "expected", "base_ref": "abc"}))
    with pytest.raises(RuntimeError, match="branch"):
        _validate_resume_context(tmp_path, json.loads((run_dir / "run.json").read_text()))
