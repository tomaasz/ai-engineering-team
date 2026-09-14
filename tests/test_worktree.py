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


def test_prompt_worktree_merge_tak(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git, \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="t"):
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 1 file changed, 5 insertions(+)\n"
            elif "status" in args:
                m.stdout = ""
            elif "merge" in args:
                m.stdout = "Merged"
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-1", "main", "test-1", {"language": "pl"})

        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 1
        assert "ai/test-1" in merge_calls[0][0]

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 1
        assert "ai/test-1" in branch_d_calls[0][0]

        out, _ = capsys.readouterr()
        assert "Pomyślnie wdrożono zmiany na 'main'" in out


def test_prompt_worktree_merge_odrzuc(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git, \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="o"):
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 1 file changed, 5 insertions(+)\n"
            elif "status" in args:
                m.stdout = ""
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-1", "main", "test-1", {"language": "pl"})

        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 0

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 1
        assert "ai/test-1" in branch_d_calls[0][0]

        out, _ = capsys.readouterr()
        assert "Zmiany odrzucone. Gałąź 'ai/test-1' została usunięta" in out


def test_prompt_worktree_merge_diff_then_tak(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git, \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", side_effect=["p", "t"]):
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 1 file changed, 5 insertions(+)\n"
            elif "diff" in args:
                m.stdout = "+def new_feature(): pass\n"
            elif "status" in args:
                m.stdout = ""
            elif "merge" in args:
                m.stdout = "Merged"
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-1", "main", "test-1", {"language": "pl"})

        out, _ = capsys.readouterr()
        assert "+def new_feature(): pass" in out
        assert "Pomyślnie wdrożono zmiany na 'main'" in out


def test_prompt_worktree_merge_nie(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git, \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="n"):
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 1 file changed, 5 insertions(+)\n"
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-1", "main", "test-1", {"language": "pl"})

        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 0

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 0

        out, _ = capsys.readouterr()
        assert "Gałąź 'ai/test-1' zachowana" in out


def test_prompt_worktree_empty_diff_auto_cleans(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git:
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""  # empty diff
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-empty", "main", "test-empty", {"language": "pl"})

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 1
        assert "ai/test-empty" in branch_d_calls[0][0]

        out, _ = capsys.readouterr()
        assert "Brak zmian w kodzie" in out


def test_prompt_worktree_auto_merge(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git:
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 2 files changed\n"
            elif "status" in args:
                m.stdout = ""
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-auto", "main", "test-auto", {"language": "en"}, auto_merge=True)

        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 1

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 1

        out, _ = capsys.readouterr()
        assert "Successfully deployed changes to 'main'" in out


def test_prompt_worktree_auto_discard(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git:
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 2 files changed\n"
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-discard", "main", "test-discard", {"language": "en"}, auto_discard=True)

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 1
        out, _ = capsys.readouterr()
        assert "Changes discarded" in out


def test_prompt_worktree_non_interactive(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git:
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 1 file changed\n"
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-headless", "main", "test-headless", {"language": "en"}, non_interactive=True)

        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 0

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 0

        out, _ = capsys.readouterr()
        assert "Non-interactive session. Branch 'ai/test-headless' kept" in out


def test_prompt_worktree_dirty_working_tree_blocks_merge(tmp_path, capsys):
    from ai_team.runner import _prompt_worktree_merge
    with patch("ai_team.runner._git") as mock_git, \
         patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="t"):
        def git_side_effect(proj, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "diff" in args and "--stat" in args:
                m.stdout = " 1 file changed\n"
            elif "status" in args:
                m.stdout = " M dirty.py\n"  # uncommitted local changes
            else:
                m.stdout = ""
            return m
        mock_git.side_effect = git_side_effect

        _prompt_worktree_merge(tmp_path, "base123", "ai/test-dirty", "main", "test-dirty", {"language": "pl"})

        merge_calls = [c for c in mock_git.call_args_list if "merge" in c[0]]
        assert len(merge_calls) == 0

        branch_d_calls = [c for c in mock_git.call_args_list if "branch" in c[0] and "-D" in c[0]]
        assert len(branch_d_calls) == 0

        out, _ = capsys.readouterr()
        assert "katalog roboczy zawiera nieskomitowane zmiany" in out


def test_cli_worktree_and_merge_flags():
    from ai_team.cli import parser
    p = parser()
    args1 = p.parse_args(['run', '.', 'test prompt', '--worktree', '--auto-merge', '--non-interactive'])
    assert args1.worktree is True
    assert args1.auto_merge is True
    assert args1.non_interactive is True

    args2 = p.parse_args(['run', '.', 'test prompt', '--merge', '--auto-discard'])
    assert args2.auto_merge is True
    assert args2.auto_discard is True

    args3 = p.parse_args(['review', 'latest', '--keep-branch'])
    assert args3.keep_branch is True
