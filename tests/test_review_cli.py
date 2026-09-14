import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ai_team.runner import review_run
from ai_team.utils import save_json

def test_review_run_not_found(tmp_path, capsys):
    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path):
        code = review_run(tmp_path, "nonexistent-run")
        assert code == 1
        out, _ = capsys.readouterr()
        assert "No runs recorded" in out

def test_review_run_summary(tmp_path, capsys):
    runs_dir = tmp_path / ".ai" / "runs"
    runs_dir.mkdir(parents=True)
    run_dir = runs_dir / "20260914-test-1234"
    run_dir.mkdir()
    (tmp_path / ".ai" / "latest.txt").write_text("20260914-test-1234", encoding="utf-8")
    (run_dir / "prompt.txt").write_text("Add health check endpoint", encoding="utf-8")
    (run_dir / "branch.txt").write_text("ai/20260914-test-1234", encoding="utf-8")
    (run_dir / "base-ref.txt").write_text("main", encoding="utf-8")

    save_json(run_dir / "result.json", {
        "status": "PASS",
        "risk": "LOW",
        "reviews": [{"provider": "codex", "round": 1, "verdict": "PASS", "summary": "Looks great"}],
        "checks": [{"argv": ["pytest"], "exitCode": 0}],
        "verification": {"verdict": "PASS", "summary": "All tests passed"}
    })

    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path), \
         patch("ai_team.runner._git") as mock_git:
        mock_git.return_value.stdout = "main"
        code = review_run(tmp_path, "latest")

    assert code == 0
    out, _ = capsys.readouterr()
    assert "20260914-test-1234" in out
    assert "PASS" in out
    assert "LOW" in out
    assert "Add health check endpoint" in out
    assert "Looks great" in out
    assert "[OK] pytest" in out

def test_review_run_diff(tmp_path, capsys):
    runs_dir = tmp_path / ".ai" / "runs"
    run_dir = runs_dir / "20260914-test-diff"
    run_dir.mkdir(parents=True)
    (run_dir / "diff.patch").write_text("+def test_endpoint(): pass\n", encoding="utf-8")
    (run_dir / "branch.txt").write_text("ai/test-diff", encoding="utf-8")
    (run_dir / "base-ref.txt").write_text("main", encoding="utf-8")

    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path), \
         patch("ai_team.runner._git") as mock_git:
        mock_git.return_value.returncode = 1 # branch not in local git
        mock_git.return_value.stdout = ""
        code = review_run(tmp_path, "20260914-test-diff", action="diff")

    assert code == 0
    out, _ = capsys.readouterr()
    assert "+def test_endpoint(): pass" in out

def test_review_run_discard(tmp_path, capsys):
    runs_dir = tmp_path / ".ai" / "runs"
    run_dir = runs_dir / "20260914-test-discard"
    run_dir.mkdir(parents=True)
    (run_dir / "branch.txt").write_text("ai/test-discard", encoding="utf-8")

    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path), \
         patch("ai_team.runner._git") as mock_git:
        # branch --show-current
        mock_git.return_value.stdout = "main"
        # rev-parse --verify
        mock_git.return_value.returncode = 0
        code = review_run(tmp_path, "20260914-test-discard", action="discard")

    assert code == 0
    out, _ = capsys.readouterr()
    assert "Discarded and deleted branch ai/test-discard" in out


def test_review_run_merge_deletes_branch(tmp_path, capsys):
    runs_dir = tmp_path / ".ai" / "runs"
    run_dir = runs_dir / "20260914-test-merge"
    run_dir.mkdir(parents=True)
    (run_dir / "branch.txt").write_text("ai/test-merge", encoding="utf-8")

    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path), \
         patch("ai_team.runner._git") as mock_git:
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "branch" in args and "--show-current" in args:
                m.stdout = "main"
            elif "status" in args:
                m.stdout = ""
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        code = review_run(tmp_path, "20260914-test-merge", action="merge")
        assert code == 0

        # Verify merge was called
        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 1
        assert "ai/test-merge" in merge_calls[0][0]

        # Verify branch was deleted
        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 1
        assert "ai/test-merge" in branch_d_calls[0][0]

        out, _ = capsys.readouterr()
        assert "deleted temporary branch" in out


def test_review_run_merge_keep_branch(tmp_path, capsys):
    runs_dir = tmp_path / ".ai" / "runs"
    run_dir = runs_dir / "20260914-test-merge-keep"
    run_dir.mkdir(parents=True)
    (run_dir / "branch.txt").write_text("ai/test-merge-keep", encoding="utf-8")

    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path), \
         patch("ai_team.runner._git") as mock_git:
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "branch" in args and "--show-current" in args:
                m.stdout = "main"
            elif "status" in args:
                m.stdout = ""
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        code = review_run(tmp_path, "20260914-test-merge-keep", action="merge", keep_branch=True)
        assert code == 0

        # Verify branch -D was NOT called
        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 0

        out, _ = capsys.readouterr()
        assert "Successfully merged ai/test-merge-keep into main" in out
