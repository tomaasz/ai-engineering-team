"""CodeGuardian: Secret and credential leak protection for ai-engineering-team."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

@dataclass
class SecretFinding:
    secret_type: str
    file_path: str
    line_number: int
    line_content: str
    redacted_preview: str

    def to_dict(self) -> dict:
        return asdict(self)

SECRET_PATTERNS = [
    ("Anthropic API Key", re.compile(r"\b(sk-ant-[a-zA-Z0-9_-]{20,})\b")),
    ("OpenAI API Key", re.compile(r"\b(sk-[a-zA-Z0-9_-]{20,})\b")),
    ("Google AI / Gemini API Key", re.compile(r"\b(AIza[0-9A-Za-z_-]{30,40})\b")),
    ("GitHub Token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{22,})\b")),
    ("AWS Access Key ID", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b")),
    ("Slack Token", re.compile(r"\b(xox[baprs]-[0-9a-zA-Z-]{10,})\b")),
    ("Stripe Secret Key", re.compile(r"\b([sr]k_(?:live|test)_[0-9a-zA-Z]{24,})\b")),
    ("HuggingFace Token", re.compile(r"\b(hf_[a-zA-Z0-9]{34,})\b")),
    ("Private Key Header", re.compile(r"(-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY(?: BLOCK)?-----)")),
    ("Database Connection URI", re.compile(r"(?i)\b(?:postgres|postgresql|mysql|mongodb|redis):\/\/[a-zA-Z0-9_.-]+:([^@\s]+)@[a-zA-Z0-9_.-]+")),
    ("Generic Secret Assignment", re.compile(r'''(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['"]([a-zA-Z0-9_-]{16,})['"]''')),
]

_PLACEHOLDER_REGEX = re.compile(r"(?i)^(?:your[_-]?api[_-]?key.*|placeholder.*|changeme.*|todo.*|<.+>|\$\{.+\})$")

def redact_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return token[:4] + "..." + token[-4:]

def scan_diff_for_secrets(diff_text: str) -> List[SecretFinding]:
    """Scan a git diff and identify potential secrets on added lines (+ lines)."""
    findings: List[SecretFinding] = []
    current_file = "unknown"
    line_no = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3].lstrip("b/")
        elif line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                line_no = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            line_no += 1
            content = line[1:]
            for secret_type, pattern in SECRET_PATTERNS:
                match = pattern.search(content)
                if match:
                    token = match.group(1) if match.groups() else match.group(0)
                    if secret_type == "Generic Secret Assignment" and _PLACEHOLDER_REGEX.match(token.strip()):
                        continue
                    findings.append(SecretFinding(
                        secret_type=secret_type,
                        file_path=current_file,
                        line_number=line_no,
                        line_content=content.strip(),
                        redacted_preview=redact_token(token)
                    ))
                    break
        elif not line.startswith("-"):
            line_no += 1
    return findings

def get_git_hooks_dir(project_path: Path) -> Optional[Path]:
    try:
        proc = subprocess.run(["git", "rev-parse", "--git-path", "hooks"],
                              cwd=str(project_path), capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            raw = proc.stdout.strip()
            p = Path(raw)
            return p if p.is_absolute() else (project_path / p).resolve()
    except Exception:
        pass
    dot_git = project_path / ".git"
    if dot_git.is_dir():
        return dot_git / "hooks"
    return None

def validate_git_diff(project_path: Path, base_ref: Optional[str] = None, staged: bool = False) -> List[SecretFinding]:
    """Run git diff and scan the output for secrets."""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--cached")
    elif base_ref:
        cmd.append(base_ref)
    else:
        try:
            has_head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"],
                                      cwd=str(project_path), capture_output=True, check=False).returncode == 0
            if has_head:
                cmd.append("HEAD")
            else:
                cmd.append("--cached")
        except Exception:
            cmd.append("--cached")
    try:
        proc = subprocess.run(cmd, cwd=str(project_path), capture_output=True, text=True, check=False)
        return scan_diff_for_secrets(proc.stdout)
    except Exception as exc:
        return [SecretFinding(secret_type="Scan Error", file_path=str(project_path), line_number=0, line_content=str(exc), redacted_preview="N/A")]

def generate_pre_commit_hook(project_path: Path) -> str:
    py_exe = sys.executable or "python3"
    try:
        module_parent = str(Path(__file__).resolve().parent.parent)
    except Exception:
        module_parent = ""
    return f"""#!/bin/sh
# CodeGuardian Pre-Commit Secret Scanner
if [ -d "src" ]; then
    export PYTHONPATH="src:${{PYTHONPATH}}"
elif [ -n "{module_parent}" ] && [ -d "{module_parent}" ]; then
    export PYTHONPATH="{module_parent}:${{PYTHONPATH}}"
fi

if command -v ai-team >/dev/null 2>&1 && ai-team check-secrets --help >/dev/null 2>&1; then
    ai-team check-secrets --staged
    exit $?
fi

for py in "{py_exe}" .venv/bin/python venv/bin/python python3; do
    if [ -x "$py" ] || command -v "$py" >/dev/null 2>&1; then
        if "$py" -c "import ai_team.codeguardian" >/dev/null 2>&1; then
            "$py" -m ai_team.codeguardian --staged
            exit $?
        fi
    fi
done

python3 -m ai_team.codeguardian --staged
exit $?
"""

def generate_pre_commit_snippet(project_path: Path) -> str:
    py_exe = sys.executable or "python3"
    try:
        module_parent = str(Path(__file__).resolve().parent.parent)
    except Exception:
        module_parent = ""
    return f"""# CodeGuardian Pre-Commit Secret Scanner
if [ -d "src" ]; then
    export PYTHONPATH="src:${{PYTHONPATH}}"
elif [ -n "{module_parent}" ] && [ -d "{module_parent}" ]; then
    export PYTHONPATH="{module_parent}:${{PYTHONPATH}}"
fi

if command -v ai-team >/dev/null 2>&1 && ai-team check-secrets --help >/dev/null 2>&1; then
    ai-team check-secrets --staged || exit $?
else
    _found_py=""
    for py in "{py_exe}" .venv/bin/python venv/bin/python python3; do
        if [ -x "$py" ] || command -v "$py" >/dev/null 2>&1; then
            if "$py" -c "import ai_team.codeguardian" >/dev/null 2>&1; then
                _found_py="$py"
                break
            fi
        fi
    done
    if [ -n "$_found_py" ]; then
        "$_found_py" -m ai_team.codeguardian --staged || exit $?
    else
        python3 -m ai_team.codeguardian --staged || exit $?
    fi
fi
"""

def install_git_hook(project_path: Path) -> Optional[Path]:
    hooks_dir = get_git_hooks_dir(project_path)
    if not hooks_dir:
        return None
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"
    if hook_file.exists():
        content = hook_file.read_text(encoding="utf-8")
        if "CodeGuardian" in content:
            return hook_file
        new_content = content.rstrip() + "\n\n" + generate_pre_commit_snippet(project_path)
        hook_file.write_text(new_content, encoding="utf-8")
    else:
        hook_file.write_text(generate_pre_commit_hook(project_path), encoding="utf-8")
    hook_file.chmod(0o755)
    return hook_file

def main() -> int:
    parser = argparse.ArgumentParser(description="CodeGuardian: Git diff secret scanner for ai-engineering-team")
    parser.add_argument("project", nargs="?", default=".", help="Project directory")
    parser.add_argument("--staged", action="store_true", help="Check only staged git changes")
    parser.add_argument("--base", default=None, help="Base git ref to diff against")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    findings = validate_git_diff(project, base_ref=args.base, staged=args.staged)
    if findings:
        print('[CodeGuardian ERROR] Security leak detected! Commit blocked.')
        print('The following secrets/credentials were discovered in the git diff:')
        for f in findings:
            print(f'  - [{f.secret_type}] {f.file_path}:{f.line_number} -> {f.redacted_preview}')
        print('Please remove sensitive credentials before committing changes.')
        return 1
    print('[CodeGuardian OK] No secrets or API credentials found in diff.')
    return 0

if __name__ == "__main__":
    sys.exit(main())
