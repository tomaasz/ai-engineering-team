# Layer 3: Boundary Contracts - Deterministic Guardrails
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional

class BoundaryViolationError(RuntimeError):
    pass

PREFIX = r"(^|[^a-zA-Z0-9_.-])"

DESTRUCTIVE_SHELL_PATTERNS = [
    re.compile(PREFIX + r"rm\s+.*(-[a-zA-Z]*[rf][a-zA-Z]*|-r\s+-f|--recursive|--force)", re.I),
    re.compile(PREFIX + r"rmdir\s+.*(--ignore-fail-on-non-empty)", re.I),
    re.compile(PREFIX + r"(mkfs(\.[a-z0-9]+)?|fdisk|parted|sfdisk)\s+", re.I),
    re.compile(PREFIX + r"dd\s+.*of=\s*/dev/(sd[a-z]|nvme[0-9]|vd[a-z]|hd[a-z]|mapper|null|zero)", re.I),
    re.compile(r">\s*/dev/(sd[a-z]|nvme[0-9]|vd[a-z]|hd[a-z]|mapper)", re.I),
    re.compile(PREFIX + r"(shutdown|reboot|poweroff|init\s+[06]|halt)(\s+|$)", re.I),
    re.compile(PREFIX + r"chmod\s+(-R\s+)?(000|777\s+/)", re.I),
    re.compile(r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;\s*:", re.I),
    re.compile(PREFIX + r"(gcloud\s+projects\s+delete|terraform\s+destroy|aws\s+s3\s+rb)", re.I),
    re.compile(PREFIX + r"(dropdb|dropuser)(\s+|$)", re.I),
]

DESTRUCTIVE_SQL_PATTERNS = [
    re.compile(PREFIX + r"DROP\s+(TABLE|DATABASE|SCHEMA|VIEW)(\s+|$)", re.I),
    re.compile(PREFIX + r"TRUNCATE(\s+TABLE)?(\s+|$)", re.I),
    re.compile(PREFIX + r"DELETE\s+FROM(\s+|$)", re.I),
    re.compile(PREFIX + r"ALTER\s+TABLE\s+.*\bDROP\s+COLUMN", re.I),
]

DANGEROUS_TOOL_NAMES = {
    "wipe_database", "drop_database", "delete_cache",
    "destroy_infrastructure", "wipe_all_data", "format_disk",
    "destroy_cluster", "purge_all_records"
}

@dataclass
class BoundaryResult:
    approved: bool
    status: str
    reason: str
    matched_patterns: List[str] = field(default_factory=list)
    action: Optional[str] = None

class BoundaryContractGate:
    def __init__(self, require_explicit_approval_for_destructive: bool = True):
        self.require_explicit_approval = require_explicit_approval_for_destructive

    def inspect_command(self, command: str) -> List[str]:
        matches = []
        for pattern in DESTRUCTIVE_SHELL_PATTERNS:
            if pattern.search(command):
                matches.append(f"Shell destructive pattern: {pattern.pattern}")
        for pattern in DESTRUCTIVE_SQL_PATTERNS:
            if pattern.search(command):
                matches.append(f"SQL destructive pattern: {pattern.pattern}")
        return matches

    def check_command(self, command: str, boundary_approved: bool = False) -> BoundaryResult:
        matches = self.inspect_command(command)
        if not matches:
            return BoundaryResult(approved=True, status="APPROVED_SAFE", reason="Command does not match any destructive patterns.", action=command)
        if not boundary_approved and self.require_explicit_approval:
            return BoundaryResult(approved=False, status="BLOCKED_BY_BOUNDARY", reason="[🔥] BOUNDARY BLOCKED: Command requires explicit Human-In-The-Loop approval! (Zero Blast Radius)", matched_patterns=matches, action=command)
        return BoundaryResult(approved=True, status="APPROVED_EXECUTIVE", reason="Destructive command authorized by explicit Human-In-The-Loop boundary approval.", matched_patterns=matches, action=command)

    def enforce_command(self, command: str, boundary_approved: bool = False) -> str:
        res = self.check_command(command, boundary_approved=boundary_approved)
        if not res.approved:
            raise BoundaryViolationError(f"{res.reason} Command: {command}, Violations: {res.matched_patterns}")
        return res.status

    def check_tool_call(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, boundary_approved: bool = False) -> BoundaryResult:
        arguments = arguments or {}
        matches = []
        if tool_name.lower() in DANGEROUS_TOOL_NAMES:
            matches.append(f"Direct dangerous tool name: {tool_name}")
        action = str(arguments.get("action", "")).lower()
        if action in DANGEROUS_TOOL_NAMES or action in {"delete_cache", "wipe_database", "destroy_env"}:
            matches.append(f"Dangerous payload action: {action}")
        cmd = arguments.get("command") or arguments.get("cmd") or arguments.get("code")
        if isinstance(cmd, str):
            matches.extend(self.inspect_command(cmd))
        sql = arguments.get("sql") or arguments.get("query")
        if isinstance(sql, str):
            for pattern in DESTRUCTIVE_SQL_PATTERNS:
                if pattern.search(sql):
                    matches.append(f"SQL destructive query: {pattern.pattern}")
        if not matches:
            return BoundaryResult(approved=True, status="APPROVED_SAFE", reason=f"Tool {tool_name} and arguments are safe.", action=tool_name)
        if not boundary_approved and self.require_explicit_approval:
            return BoundaryResult(approved=False, status="BLOCKED_BY_BOUNDARY", reason=f"[🔥] BOUNDARY BLOCKED: Tool {tool_name} requires explicit Human-In-The-Loop approval! (Zero Blast Radius)", matched_patterns=matches, action=tool_name)
        return BoundaryResult(approved=True, status="APPROVED_EXECUTIVE", reason=f"Tool {tool_name} authorized by explicit Human-In-The-Loop approval.", matched_patterns=matches, action=tool_name)

    def enforce_tool_call(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, boundary_approved: bool = False) -> str:
        res = self.check_tool_call(tool_name, arguments, boundary_approved=boundary_approved)
        if not res.approved:
            raise BoundaryViolationError(f"{res.reason} Tool: {tool_name}, Arguments: {arguments}, Violations: {res.matched_patterns}")
        return res.status

default_gate = BoundaryContractGate()
