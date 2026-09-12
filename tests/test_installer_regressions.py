import json
import subprocess
from pathlib import Path

import pytest

import ai_team.installer as installer
from ai_team.utils import load_json, load_jsonc, save_json, sha256_file, template_root


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)


def _state(project: Path) -> dict:
    return load_json(project / ".ai-team" / "state.json")


def test_successive_conflicting_updates_preserve_local_file_and_uninstall_skips(tmp_path):
    _init_repo(tmp_path)
    installer.install(tmp_path, "core")
    target = tmp_path / "AI_TEAM.md"
    local = "local rules must survive\n"
    target.write_text(local, encoding="utf-8")

    assert "AI_TEAM.md" in installer.update(tmp_path)
    assert "AI_TEAM.md" in installer.update(tmp_path)
    assert target.read_text(encoding="utf-8") == local

    removed, skipped = installer.uninstall(tmp_path)
    assert "AI_TEAM.md" not in removed
    assert "AI_TEAM.md" in skipped
    assert target.read_text(encoding="utf-8") == local


@pytest.mark.parametrize("name", ["AGENTS.md", "CLAUDE.md", "GEMINI.md"])
def test_first_install_preserves_existing_ai_instruction_files(tmp_path, name):
    _init_repo(tmp_path)
    original = f"# Existing {name}\nproject-specific instructions\n"
    (tmp_path / name).write_text(original, encoding="utf-8")

    installer.install(tmp_path, "core")

    assert (tmp_path / name).read_text(encoding="utf-8") == original
    state = _state(tmp_path)
    assert name in state["conflicts"]
    assert (tmp_path / ".ai-team" / "conflicts" / name).is_file()


def test_repeated_install_is_idempotent_and_preserves_local_changes(tmp_path):
    _init_repo(tmp_path)
    installer.install(tmp_path, "core")
    target = tmp_path / "AGENTS.md"
    target.write_text("my local agent instructions\n", encoding="utf-8")

    installer.install(tmp_path, "core")
    installer.install(tmp_path, "core")

    assert target.read_text(encoding="utf-8") == "my local agent instructions\n"
    assert _state(tmp_path)["conflicts"].count("AGENTS.md") == 1


def test_operations_from_subdirectory_use_git_root(tmp_path):
    _init_repo(tmp_path)
    nested = tmp_path / "packages" / "app"
    nested.mkdir(parents=True)

    installer.install(nested, "core")
    assert (tmp_path / ".ai-team" / "state.json").is_file()
    assert installer.status(nested)["installed"] is True

    (tmp_path / "AI_TEAM.md").write_text("local\n", encoding="utf-8")
    assert "AI_TEAM.md" in installer.update(nested)
    _, skipped = installer.uninstall(nested)
    assert "AI_TEAM.md" in skipped
    assert not (tmp_path / ".ai-team" / "state.json").exists()


def test_jsonc_tasks_merge_preserves_existing_semantics(tmp_path):
    vscode = tmp_path / ".vscode"
    vscode.mkdir()
    tasks = vscode / "tasks.json"
    tasks.write_text(
        '''{
  // user task must remain valid
  "version": "2.0.0",
  "tasks": [{
    "label": "User task",
    "type": "shell",
    "command": "echo https://example.test/a//b",
    "args": ["/* literal */",],
  },],
  "inputs": [],
}
''',
        encoding="utf-8",
    )

    assert installer._merge_tasks(tmp_path, template_root() / ".vscode" / "tasks.json") == "merged"

    merged = load_jsonc(tasks)
    user_task = next(task for task in merged["tasks"] if task["label"] == "User task")
    assert user_task["command"] == "echo https://example.test/a//b"
    assert user_task["args"] == ["/* literal */"]


@pytest.mark.parametrize(
    "document",
    [
        {"version": "2.0.0", "tasks": {}, "inputs": []},
        {"version": "2.0.0", "tasks": ["bad"], "inputs": []},
        {"version": "2.0.0", "tasks": [], "inputs": {}},
    ],
)
def test_malformed_task_shape_is_never_overwritten(tmp_path, document):
    vscode = tmp_path / ".vscode"
    vscode.mkdir()
    tasks = vscode / "tasks.json"
    original = json.dumps(document, indent=2) + "\n"
    tasks.write_text(original, encoding="utf-8")

    result = installer._merge_tasks(tmp_path, template_root() / ".vscode" / "tasks.json")

    assert result.startswith("conflict:")
    assert tasks.read_text(encoding="utf-8") == original
    assert (tmp_path / ".ai-team" / "conflicts" / ".vscode" / "tasks.ai-team.json").is_file()


def test_retired_managed_template_remains_tracked_until_uninstall(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    source = tmp_path / "upstream.txt"
    source.write_text("framework content\n", encoding="utf-8")
    selected = {"retired-template.md": source}
    monkeypatch.setattr(installer, "_selected", lambda profile: dict(selected))

    installer.install(tmp_path, "core")
    selected.clear()
    installer.update(tmp_path)

    assert "retired-template.md" in _state(tmp_path)["managed"]
    removed, skipped = installer.uninstall(tmp_path)
    assert "retired-template.md" in removed
    assert "retired-template.md" not in skipped
    assert not (tmp_path / "retired-template.md").exists()


@pytest.mark.parametrize("strategy", ["keep", "upstream"])
def test_resolve_clears_conflict_and_applies_requested_strategy(tmp_path, strategy):
    _init_repo(tmp_path)
    installer.install(tmp_path, "core")
    target = tmp_path / "AI_TEAM.md"
    target.write_text("local version\n", encoding="utf-8")
    installer.update(tmp_path)
    upstream = tmp_path / ".ai-team" / "conflicts" / "AI_TEAM.md"
    upstream_content = upstream.read_text(encoding="utf-8")

    resolve = getattr(installer, "resolve", None)
    assert callable(resolve), "installer.resolve(project, relative, strategy=...) is required"
    resolve(tmp_path, "AI_TEAM.md", strategy=strategy)

    state = _state(tmp_path)
    assert "AI_TEAM.md" not in state["conflicts"]
    assert not upstream.exists()
    if strategy == "keep":
        assert target.read_text(encoding="utf-8") == "local version\n"
        assert "AI_TEAM.md" not in state["managed"]
        installer.update(tmp_path)
        _, skipped = installer.uninstall(tmp_path)
        assert target.read_text(encoding="utf-8") == "local version\n"
        assert "AI_TEAM.md" not in skipped
    else:
        assert target.read_text(encoding="utf-8") == upstream_content
        assert state["managed"]["AI_TEAM.md"] == sha256_file(target)


def test_same_label_task_updates_only_when_framework_owned(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    installer.install(tmp_path, "core")
    tasks_path = tmp_path / ".vscode" / "tasks.json"
    installed = load_json(tasks_path)
    doctor = next(task for task in installed["tasks"] if task["label"] == "AI Team: Doctor")
    doctor["command"] = "user-custom-doctor"
    save_json(tasks_path, installed)

    upstream = load_json(template_root() / ".vscode" / "tasks.json")
    run_task = next(task for task in upstream["tasks"] if task["label"] == "AI Team: Run prompt")
    doctor_upstream = next(task for task in upstream["tasks"] if task["label"] == "AI Team: Doctor")
    run_task["command"] = "ai-team-next"
    doctor_upstream["command"] = "ai-team-next"
    new_template = tmp_path / "new-tasks.json"
    save_json(new_template, upstream)

    original_selected = installer._selected

    def selected(profile):
        files = original_selected(profile)
        files[".vscode/tasks.json"] = new_template
        return files

    monkeypatch.setattr(installer, "_selected", selected)
    installer.update(tmp_path)

    updated = load_json(tasks_path)
    by_label = {task["label"]: task for task in updated["tasks"]}
    assert by_label["AI Team: Run prompt"]["command"] == "ai-team-next"
    assert by_label["AI Team: Doctor"]["command"] == "user-custom-doctor"
