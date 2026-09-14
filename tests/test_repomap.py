import pytest
from pathlib import Path
from ai_team.repomap import generate_repomap, _extract_py_symbols

def test_extract_py_symbols(tmp_path):
    py_file = tmp_path / "sample.py"
    py_file.write_text("""class Calculator:
    def add(self, a, b):
        return a + b

def helper(x: int) -> bool:
    return x > 0
""", encoding="utf-8")

    defs = _extract_py_symbols(py_file)
    assert any("class Calculator" in d for d in defs)
    assert any("def add(self, a, b)" in d for d in defs)
    assert any("def helper(x)" in d for d in defs)

def test_generate_repomap(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("class App:\n    def run(self): pass\n", encoding="utf-8")
    (src / "utils.py").write_text("def log(msg): pass\n", encoding="utf-8")
    
    # Hidden/ignored directory
    hidden = tmp_path / ".venv"
    hidden.mkdir()
    (hidden / "ignored.py").write_text("def secret(): pass\n", encoding="utf-8")

    repomap = generate_repomap(tmp_path)
    assert "src/main.py" in repomap.replace("\\", "/")
    assert "class App" in repomap
    assert "src/utils.py" in repomap.replace("\\", "/")
    assert "def log" in repomap
    assert "ignored.py" not in repomap
