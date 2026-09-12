import os
import sys

from ai_team.runner import _capture


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
