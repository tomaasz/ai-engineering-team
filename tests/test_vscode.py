import json
from pathlib import Path
from ai_team.installer import _merge_tasks
from ai_team.utils import template_root, save_json, load_json

def test_tasks_json_creation(tmp_path):
    template = template_root() / ".vscode" / "tasks.json"
    result = _merge_tasks(tmp_path, template)
    assert result == "created"

    created = tmp_path / ".vscode" / "tasks.json"
    assert created.is_file()
    data = load_json(created)
    assert "tasks" in data
    labels = [t["label"] for t in data["tasks"]]
    assert "AI Team: Run prompt" in labels
    assert "AI Team: Doctor" in labels
    assert "AI Team: Update" in labels

def test_tasks_json_merge_preserves_user_tasks(tmp_path):
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    existing_tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "User Custom Task",
                "type": "shell",
                "command": "npm test"
            }
        ],
        "inputs": [
            {
                "id": "userInput",
                "type": "promptString",
                "description": "Custom prompt"
            }
        ]
    }
    save_json(vscode_dir / "tasks.json", existing_tasks)

    template = template_root() / ".vscode" / "tasks.json"
    result = _merge_tasks(tmp_path, template)
    assert result == "merged"

    merged = load_json(vscode_dir / "tasks.json")
    labels = [t["label"] for t in merged["tasks"]]
    assert "User Custom Task" in labels
    assert "AI Team: Run prompt" in labels
    assert "AI Team: Doctor" in labels
    assert "AI Team: Update" in labels

    input_ids = [inp["id"] for inp in merged["inputs"]]
    assert "userInput" in input_ids
    assert "aiPrompt" in input_ids

def test_tasks_json_merge_does_not_duplicate(tmp_path):
    template = template_root() / ".vscode" / "tasks.json"
    _merge_tasks(tmp_path, template)
    # Merge a second time
    result2 = _merge_tasks(tmp_path, template)
    assert result2 == "merged"

    merged = load_json(tmp_path / ".vscode" / "tasks.json")
    labels = [t["label"] for t in merged["tasks"]]
    assert labels.count("AI Team: Run prompt") == 1
    assert labels.count("AI Team: Doctor") == 1
    assert labels.count("AI Team: Update") == 1

def test_tasks_json_corrupted_creates_conflict(tmp_path):
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "tasks.json").write_text("{corrupted json", encoding="utf-8")

    template = template_root() / ".vscode" / "tasks.json"
    result = _merge_tasks(tmp_path, template)
    assert result.startswith("conflict:")

    conflict_file = tmp_path / ".ai-team" / "conflicts" / ".vscode" / "tasks.ai-team.json"
    assert conflict_file.is_file()
    # Original corrupted file is untouched
    assert (vscode_dir / "tasks.json").read_text(encoding="utf-8") == "{corrupted json"

