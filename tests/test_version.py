from pathlib import Path
import tomllib
import ai_team
from ai_team.installer import VERSION as INSTALLER_VERSION

def test_version_consistency():
    root = Path(__file__).resolve().parent.parent
    version_file = (root / "VERSION").read_text(encoding="utf-8").strip()

    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_data = tomllib.loads(pyproject_text)
    pyproject_version = pyproject_data["project"]["version"]

    pkg_version = ai_team.__version__

    assert version_file == "3.0.1"
    assert pyproject_version == "3.0.1"
    assert pkg_version == "3.0.1"
    assert INSTALLER_VERSION == "3.0.1"
