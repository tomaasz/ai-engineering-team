"""Artifact Verifier: Validation of physical repository artifacts and test execution to prevent hallucinated completion."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class ArtifactVerificationResult:
    valid: bool
    has_physical_changes: bool
    modified_files: List[str]
    untracked_files: List[str]
    failed_checks: List[Dict[str, Any]]
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


IGNORED_PREFIXES = ('.ai/', '.ai-team/', '.git/')


def get_git_changes(project_path: Path, base_ref: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Discover modified tracked files and non-ignored untracked files."""
    project_path = Path(project_path)
    base = base_ref or 'HEAD'

    modified: List[str] = []
    untracked: List[str] = []

    # 1. Tracked modifications against base
    diff_cmd = ['git', 'diff', '--name-only', base]
    proc_diff = subprocess.run(diff_cmd, cwd=str(project_path), capture_output=True, text=True, check=False)
    if proc_diff.returncode == 0:
        for line in proc_diff.stdout.splitlines():
            f = line.strip()
            if f and not any(f == p.rstrip('/') or f.startswith(p) for p in IGNORED_PREFIXES):
                if f not in modified:
                    modified.append(f)
    else:
        # Fallback to status porcelain if base diff failed (e.g. initial commit / unborn branch)
        proc_status = subprocess.run(['git', 'status', '--porcelain'], cwd=str(project_path), capture_output=True, text=True, check=False)
        if proc_status.returncode == 0:
            for line in proc_status.stdout.splitlines():
                if len(line) > 3:
                    code = line[:2]
                    f = line[3:].strip()
                    if f and not any(f == p.rstrip('/') or f.startswith(p) for p in IGNORED_PREFIXES):
                        if code == '??':
                            if f not in untracked:
                                untracked.append(f)
                        else:
                            if f not in modified:
                                modified.append(f)

    # 2. Untracked files (excluding standard gitignores)
    untracked_cmd = ['git', 'ls-files', '--others', '--exclude-standard']
    proc_untracked = subprocess.run(untracked_cmd, cwd=str(project_path), capture_output=True, text=True, check=False)
    if proc_untracked.returncode == 0:
        for line in proc_untracked.stdout.splitlines():
            f = line.strip()
            if f and not any(f == p.rstrip('/') or f.startswith(p) for p in IGNORED_PREFIXES):
                if f not in untracked:
                    untracked.append(f)

    return sorted(modified), sorted(untracked)


def verify_completion_artifacts(
    project_path: Path,
    base_ref: Optional[str] = None,
    checks: Optional[List[Dict[str, Any]]] = None,
    verdict: Optional[Dict[str, Any]] = None,
    require_changes: bool = True,
) -> ArtifactVerificationResult:
    """Verify physical repository changes and test results before allowing a task completion to succeed."""
    project_path = Path(project_path)
    modified, untracked = get_git_changes(project_path, base_ref)
    has_physical_changes = bool(modified or untracked)

    failed_checks = [c for c in (checks or []) if c.get('exitCode', 0) != 0]
    reasons: List[str] = []

    verdict_val = verdict.get('verdict') if verdict else 'PASS'

    # Rule 1: Ghost completion detection
    # If the agent declares or is evaluated for PASS, but made no physical changes in the repository
    if require_changes and not has_physical_changes and verdict_val in ('PASS', 'PASS_WITH_NOTES'):
        reasons.append(
            'Brak fizycznych modyfikacji w repozytorium (wykryto halucynację sukcesu / ghost completion). '
            'Agent zaraportował status sukcesu, lecz żaden plik projektu nie został zmieniony ani utworzony.'
        )

    # Rule 2: Non-zero test / check exit codes
    if failed_checks:
        reasons.append(
            f'Wykryto {len(failed_checks)} nieudanych testów/poleceń weryfikacyjnych (kod wyjścia != 0).'
        )

    # Rule 3: Explicit CHANGES_REQUIRED verdict
    if verdict_val == 'CHANGES_REQUIRED':
        reasons.append('Ocena weryfikatora/recenzenta to CHANGES_REQUIRED.')

    valid = len(reasons) == 0
    return ArtifactVerificationResult(
        valid=valid,
        has_physical_changes=has_physical_changes,
        modified_files=modified,
        untracked_files=untracked,
        failed_checks=failed_checks,
        reasons=reasons,
    )
