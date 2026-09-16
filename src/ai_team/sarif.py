"""SARIF 2.1.0 (Static Analysis Results Interchange Format) exporter for 360° audit findings.

Produces standard OASIS SARIF v2.1.0 JSON artifacts compatible with
GitHub Code Scanning, SonarQube, and CI/CD security quality gates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import __version__

SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
SARIF_VERSION = "2.1.0"

SEVERITY_LEVEL_MAP = {
    "CRITICAL": "error",
    "HIGH": "error",
    "ERROR": "error",
    "MEDIUM": "warning",
    "WARN": "warning",
    "WARNING": "warning",
    "LOW": "note",
    "INFO": "note",
    "NOTE": "note",
}

CATEGORY_PREFIX_MAP = {
    "arch": "ARCH",
    "architecture": "ARCH",
    "architektura": "ARCH",
    "sec": "SEC",
    "security": "SEC",
    "bezpieczeństwo": "SEC",
    "rel": "REL",
    "reliability": "REL",
    "niezawodność": "REL",
    "perf": "PERF",
    "performance": "PERF",
    "wydajność": "PERF",
    "test": "TEST",
    "testing": "TEST",
    "testy": "TEST",
    "ops": "OPS",
    "devops": "OPS",
    "kontenery": "OPS",
}


def _clean_cell(text: str) -> str:
    """Strip markdown formatting, backticks, and extra whitespace from a table cell."""
    t = text.strip()
    if t.startswith('`') and t.endswith('`') and len(t) >= 2:
        t = t[1:-1].strip()
    return t


def _parse_location(loc_str: str) -> tuple[str, int, int | None]:
    """Parse file location string into (file_path, start_line, end_line)."""
    clean = _clean_cell(loc_str)
    # Strip markdown links [text](url)
    md_link = re.match(r'\[([^\]]+)\]\([^)]+\)', clean)
    if md_link:
        clean = md_link.group(1).strip()

    # Match file:line or file:start-end
    m = re.match(r'^(.*?):(\d+)(?:-(\d+))?$', clean)
    if m:
        fpath = m.group(1).strip()
        start = int(m.group(2))
        end = int(m.group(3)) if m.group(3) else None
        return fpath, max(1, start), end

    return clean if clean else "unknown", 1, None


def parse_markdown_findings(markdown_text: str) -> list[dict[str, Any]]:
    """Parse findings table from markdown audit report."""
    findings: list[dict[str, Any]] = []
    lines = markdown_text.splitlines()

    table_lines: list[str] = []
    in_table = False

    for line in lines:
        s = line.strip()
        if s.startswith('|') and s.endswith('|'):
            table_lines.append(s)
            in_table = True
        else:
            if in_table:
                if len(table_lines) >= 2:
                    parsed = _parse_table_block(table_lines)
                    if parsed:
                        findings.extend(parsed)
                table_lines = []
                in_table = False

    if in_table and len(table_lines) >= 2:
        parsed = _parse_table_block(table_lines)
        if parsed:
            findings.extend(parsed)

    return findings


def _parse_table_block(lines: list[str]) -> list[dict[str, Any]]:
    """Parse a single markdown table block if it represents findings."""
    header_cells = [_clean_cell(c).lower() for c in lines[0].split('|')[1:-1]]
    
    # Identify columns
    sev_idx = -1
    cat_idx = -1
    loc_idx = -1
    desc_idx = -1
    act_idx = -1

    for i, col in enumerate(header_cells):
        if any(k in col for k in ('poziom', 'severity', 'level')):
            sev_idx = i
        elif any(k in col for k in ('kategoria', 'category', 'wymiar', 'dimension')):
            cat_idx = i
        elif any(k in col for k in ('lokalizacja', 'location', 'plik', 'file', 'ścieżka', 'path')):
            loc_idx = i
        elif any(k in col for k in ('opis', 'description', 'problem', 'finding', 'issue', 'tytuł', 'title')):
            desc_idx = i
        elif any(k in col for k in ('akcja', 'action', 'remediation', 'zalecenie', 'naprawa')):
            act_idx = i

    if sev_idx == -1 and loc_idx == -1:
        return []

    results: list[dict[str, Any]] = []
    for row_line in lines[1:]:
        # Skip separator rows
        if re.match(r'^\|[\s\-:|]+\|$', row_line):
            continue
        raw_cells = [_clean_cell(c) for c in row_line.split('|')[1:-1]]
        if not raw_cells:
            continue

        def get_cell(idx: int) -> str:
            return raw_cells[idx] if 0 <= idx < len(raw_cells) else ""

        sev_raw = get_cell(sev_idx).upper()
        # Extract standard severity keyword
        sev = "INFO"
        for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
            if k in sev_raw:
                sev = k
                break

        cat = get_cell(cat_idx) or "General"
        loc_raw = get_cell(loc_idx)
        desc = get_cell(desc_idx) or "Audit finding"
        act = get_cell(act_idx)

        fpath, start_line, end_line = _parse_location(loc_raw)

        results.append({
            "severity": sev,
            "category": cat,
            "location": loc_raw,
            "file": fpath,
            "line": start_line,
            "end_line": end_line,
            "description": desc,
            "action": act,
        })

    return results


def findings_to_sarif(
    findings: list[dict[str, Any]],
    tool_name: str = "ai-engineering-team",
    tool_version: str = __version__,
) -> dict[str, Any]:
    """Convert structured audit findings into SARIF 2.1.0 document."""
    rules_dict: dict[str, dict[str, Any]] = {}
    sarif_results: list[dict[str, Any]] = []

    for idx, f in enumerate(findings, start=1):
        cat = f.get("category", "General").strip()
        cat_key = cat.lower().split()[0] if cat else "gen"
        prefix = CATEGORY_PREFIX_MAP.get(cat_key, "AUDIT")
        rule_id = f"AIT-{prefix}-{idx:03d}"

        sev = f.get("severity", "MEDIUM").upper()
        level = SEVERITY_LEVEL_MAP.get(sev, "warning")
        desc = f.get("description", "Audit finding")
        action = f.get("action", "")

        fpath = f.get("file", "unknown")
        line = max(1, int(f.get("line", 1)))
        end_line = f.get("end_line")

        # Register rule if not already present
        if rule_id not in rules_dict:
            rules_dict[rule_id] = {
                "id": rule_id,
                "name": f"{prefix}_{idx:03d}",
                "shortDescription": {
                    "text": desc[:120]
                },
                "defaultConfiguration": {
                    "level": level
                },
                "properties": {
                    "category": cat,
                    "severity": sev,
                    "tags": ["ai-team", "audit", prefix.lower()]
                }
            }

        message_text = desc
        if action:
            message_text = f"{desc}\n\nRemediation: {action}"

        region: dict[str, Any] = {
            "startLine": line,
            "startColumn": 1
        }
        if end_line and end_line >= line:
            region["endLine"] = end_line

        sarif_results.append({
            "ruleId": rule_id,
            "level": level,
            "message": {
                "text": message_text
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": fpath,
                            "uriBaseId": "%SRCROOT%"
                        },
                        "region": region
                    }
                }
            ]
        })

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": tool_version,
                        "informationUri": "https://github.com/tomaasz/ai-engineering-team",
                        "rules": list(rules_dict.values())
                    }
                },
                "results": sarif_results
            }
        ]
    }


def markdown_to_sarif(
    markdown_text: str,
    tool_name: str = "ai-engineering-team",
    tool_version: str = __version__,
) -> dict[str, Any]:
    """Parse markdown audit report and convert its findings matrix to SARIF 2.1.0."""
    findings = parse_markdown_findings(markdown_text)
    return findings_to_sarif(findings, tool_name=tool_name, tool_version=tool_version)


def export_sarif(
    source: list[dict[str, Any]] | str | Path,
    output_path: str | Path,
    tool_name: str = "ai-engineering-team",
    tool_version: str = __version__,
) -> Path:
    """Export audit findings (or markdown path/text) to a SARIF JSON file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(source, list):
        sarif_doc = findings_to_sarif(source, tool_name=tool_name, tool_version=tool_version)
    elif isinstance(source, Path) or (isinstance(source, str) and Path(source).is_file()):
        text = Path(source).read_text(encoding="utf-8")
        sarif_doc = markdown_to_sarif(text, tool_name=tool_name, tool_version=tool_version)
    elif isinstance(source, str):
        sarif_doc = markdown_to_sarif(source, tool_name=tool_name, tool_version=tool_version)
    else:
        sarif_doc = findings_to_sarif([], tool_name=tool_name, tool_version=tool_version)

    out.write_text(json.dumps(sarif_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
