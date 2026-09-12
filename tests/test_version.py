from pathlib import Path
import re
import ai_team
from ai_team.installer import VERSION as INSTALLER_VERSION


def _parse_pyproject_version(pyproject_text: str) -> str:
    try:
        import tomllib

        data = tomllib.loads(pyproject_text)
        return data["project"]["version"]
    except ModuleNotFoundError:
        try:
            import tomli

            data = tomli.loads(pyproject_text)
            return data["project"]["version"]
        except ModuleNotFoundError:
            match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject_text)
            if match:
                return match.group(1)
            raise ValueError("Could not parse version from pyproject.toml")


def test_version_consistency():
    root = Path(__file__).resolve().parent.parent
    version_file = (root / "VERSION").read_text(encoding="utf-8").strip()

    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_version = _parse_pyproject_version(pyproject_text)

    pkg_version = ai_team.__version__

    assert version_file == "3.0.1"
    assert pyproject_version == "3.0.1"
    assert pkg_version == "3.0.1"
    assert INSTALLER_VERSION == "3.0.1"

