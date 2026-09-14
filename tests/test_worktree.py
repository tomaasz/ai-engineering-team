import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ai_team.runner import run_team
from ai_team.utils import save_json

def test_worktree_execution_flow(tmp_path):
    # Setup dummy project
    (tmp_path / "ai-team.config.json").write_text('{"primaryProvider": "agy", "verification": {"noChecksReason": "testing"}}', encoding="utf-8")
    (tmp_path / ".ai-team").mkdir()
    save_json(tmp_path / ".ai-team" / "state.json", {"conflicts": []})

    with patch("ai_team.runner.ensure_git_repo", return_value=tmp_path), \
         patch("ai_team.runner.which", return_value="/bin/agy"), \
         patch("ai_team.runner._git") as mock_git, \
         patch("ai_team.runner._execute", return_value=0) as mock_exec:
        
        # Git responses
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "status" in args:
                m.stdout = ""
            elif "branch" in args and "--show-current" in args:
                m.stdout = "main"
            elif "rev-parse" in args:
                m.stdout = "abc123commit"
            else:
                m.stdout = ""
            return m

        mock_git.side_effect = git_side_effect

        rc = run_team(tmp_path, "Implement new feature", use_worktree=True)
        assert rc == 0

        # Verify worktree add was called
        worktree_calls = [call for call in mock_git.call_args_list if "worktree" in call[0]]
        assert len(worktree_calls) >= 2  # add and remove
        assert any("add" in call[0] for call in worktree_calls)
        assert any("remove" in call[0] for call in worktree_calls)
        
        # Verify _execute was called with worktree directory as target
        executed_dir = mock_exec.call_args[0][0]
        assert ".ai" in str(executed_dir)
        assert "worktrees" in str(executed_dir)
