import json
from pathlib import Path
import pytest
from ai_team.cli import parser, main
from ai_team.sarif import (
    parse_markdown_findings,
    findings_to_sarif,
    markdown_to_sarif,
    export_sarif,
    SARIF_SCHEMA,
    SARIF_VERSION,
)


SAMPLE_AUDIT_MARKDOWN_PL = """# Raport z audytu 360°

## Executive Summary
System w dobrym stanie, ale wykryto krytyczne podatności.

## Matryca Znalezisk
| Poziom | Kategoria | Lokalizacja | Opis | Zalecana akcja |
|:---|:---|:---|:---|:---|
| CRITICAL | Bezpieczeństwo | `src/auth.py:42` | Wyciek klucza JWT | Użyć zmiennej środowiskowej |
| HIGH | Architektura | [src/runner.py:105-110](file://src/runner.py) | Monolityczna funkcja runnera | Rozbić na mniejsze moduły |
| MEDIUM | Wydajność | src/db.py:200 | Pętla zapytań N+1 | Zastosować eager loading |
| LOW | DevOps | Dockerfile:1 | Obraz bazowy bez sha256 | Przypiąć digest obrazu |

## Szczegółowa Analiza
...
"""

SAMPLE_AUDIT_MARKDOWN_EN = """# 360° Audit Report

## Findings Matrix
| Severity | Category | Location | Description | Recommended Action |
|:---|:---|:---|:---|:---|
| CRITICAL | Security | src/api.py:15 | SQL Injection in query | Use parameterized query |
| MEDIUM | Testing | tests/test_core.py:50 | Missing boundary condition test | Add edge case tests |
"""


def test_parse_markdown_findings_pl():
    findings = parse_markdown_findings(SAMPLE_AUDIT_MARKDOWN_PL)
    assert len(findings) == 4

    f0 = findings[0]
    assert f0["severity"] == "CRITICAL"
    assert "Bezpieczeństwo" in f0["category"]
    assert f0["file"] == "src/auth.py"
    assert f0["line"] == 42
    assert "JWT" in f0["description"]
    assert "środowiskowej" in f0["action"]

    f1 = findings[1]
    assert f1["severity"] == "HIGH"
    assert f1["file"] == "src/runner.py"
    assert f1["line"] == 105
    assert f1["end_line"] == 110


def test_parse_markdown_findings_en():
    findings = parse_markdown_findings(SAMPLE_AUDIT_MARKDOWN_EN)
    assert len(findings) == 2
    assert findings[0]["severity"] == "CRITICAL"
    assert findings[0]["file"] == "src/api.py"
    assert findings[0]["line"] == 15
    assert findings[1]["severity"] == "MEDIUM"


def test_parse_markdown_empty_or_no_table():
    findings = parse_markdown_findings("# Only text\nNo findings here.")
    assert findings == []


def test_findings_to_sarif_structure():
    findings = parse_markdown_findings(SAMPLE_AUDIT_MARKDOWN_PL)
    sarif_doc = findings_to_sarif(findings)

    assert sarif_doc["$schema"] == SARIF_SCHEMA
    assert sarif_doc["version"] == SARIF_VERSION
    assert len(sarif_doc["runs"]) == 1

    run = sarif_doc["runs"][0]
    driver = run["tool"]["driver"]
    assert driver["name"] == "ai-engineering-team"
    assert len(driver["rules"]) >= 1

    results = run["results"]
    assert len(results) == 4

    # CRITICAL finding -> error level
    res0 = results[0]
    assert res0["level"] == "error"
    assert res0["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/auth.py"
    assert res0["locations"][0]["physicalLocation"]["region"]["startLine"] == 42

    # MEDIUM finding -> warning level
    res2 = results[2]
    assert res2["level"] == "warning"
    assert res2["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/db.py"

    # LOW finding -> note level
    res3 = results[3]
    assert res3["level"] == "note"


def test_export_sarif_file(tmp_path):
    md_path = tmp_path / "docs/AUDIT.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(SAMPLE_AUDIT_MARKDOWN_PL, encoding="utf-8")

    sarif_out = tmp_path / "docs/audit.sarif"
    exported = export_sarif(md_path, sarif_out)

    assert exported == sarif_out
    assert sarif_out.is_file()

    data = json.loads(sarif_out.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    assert len(data["runs"][0]["results"]) == 4


def test_sarif_cli_args_parsing():
    p = parser()

    # audit --sarif without path uses default docs/audit.sarif
    args = p.parse_args(['audit', '--sarif'])
    assert args.command == 'audit'
    assert args.sarif == 'docs/audit.sarif'

    # audit --sarif with custom path
    args = p.parse_args(['audit', '--sarif', 'build/custom.sarif'])
    assert args.command == 'audit'
    assert args.sarif == 'build/custom.sarif'

    # sarif command
    args = p.parse_args(['sarif'])
    assert args.command == 'sarif'
    assert args.source == 'docs/AUDIT.md'
    assert args.output == 'docs/audit.sarif'

    # sarif command with arguments
    args = p.parse_args(['sarif', 'reports/in.md', '--output', 'out.sarif'])
    assert args.command == 'sarif'
    assert args.source == 'reports/in.md'
    assert args.output == 'out.sarif'


def test_sarif_command_execution(tmp_path, monkeypatch):
    md_path = tmp_path / "docs/AUDIT.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(SAMPLE_AUDIT_MARKDOWN_EN, encoding="utf-8")

    sarif_out = tmp_path / "docs/audit.sarif"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["ai-team", "sarif", str(md_path), "--output", str(sarif_out)])
    ret = main()
    assert ret == 0
    assert sarif_out.is_file()

    data = json.loads(sarif_out.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    assert len(data["runs"][0]["results"]) == 2
