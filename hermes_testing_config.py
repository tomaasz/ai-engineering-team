import os
from pathlib import Path
import pytest
from ai_team.boundary import (
    BoundaryContractGate, BoundaryResult, BoundaryViolationError, default_gate,
    DESTRUCTIVE_SHELL_PATTERNS, DESTRUCTIVE_SQL_PATTERNS, DANGEROUS_TOOL_NAMES
)

HERMES_ENV = os.getenv("HERMES_ENV", "testing")
OBSIDIAN_TEST_REPORTS_PATH = os.getenv("OBSIDIAN_TEST_REPORTS_PATH", "/home/tomaasz/obsidian-vault/reports/hermes_testing/")
SHADOW_DIVERGENCE_THRESHOLD = 0.15

@pytest.mark.parametrize("cmd", [
    "rm -rf /",
    "rm -rf /tmp/data",
    "rm -r -f *",
    "mkfs.ext4 /dev/sda1",
    "dd if=/dev/zero of=/dev/sda bs=1M",
    "fdisk /dev/nvme0n1",
    "> /dev/sda",
    "shutdown -h now",
    "reboot",
    "chmod -R 777 /",
    ":(){ :|:& };:",
    "gcloud projects delete prod-cluster-99",
    "terraform destroy -auto-approve",
    "aws s3 rb s3://prod-backups --force",
    "dropdb production_main",
])
def test_boundary_contract_blocks_destructive_shell_command(cmd):
    gate = BoundaryContractGate()
    res = gate.check_command(cmd, boundary_approved=False)
    assert not res.approved
    assert res.status == "BLOCKED_BY_BOUNDARY"
    assert len(res.matched_patterns) > 0
    with pytest.raises(BoundaryViolationError) as exc_info:
        gate.enforce_command(cmd, boundary_approved=False)
    assert "Zero Blast Radius" in str(exc_info.value)
@pytest.mark.parametrize("tool_name,args", [
    ('wipe_database', {'target': 'production'}),
    ('drop_database', {'db': 'users_db'}),
    ('delete_cache', {'target': 'redis_cluster'}),
    ('destroy_infrastructure', {'env': 'prod'}),
    ('terminal', {'command': 'rm -rf /var/lib/postgresql/data'}),
    ('terminal', {'command': 'dd if=/dev/zero of=/dev/sda'}),
    ('execute_code', {'code': 'import os; os.system("rm -rf /")'}),
    ('run_command', {'command': 'mkfs.ext4 /dev/vda1'}),
    ('sql_executor', {'sql': 'DROP DATABASE production_clients'}),
    ('sql_executor', {'query': 'DELETE FROM users'}),
    ('sql_executor', {'sql': 'TRUNCATE TABLE transactions'}),
])
def test_boundary_contract_blocks_dangerous_tool_invocation(tool_name, args):
    gate = BoundaryContractGate()
    res = gate.check_tool_call(tool_name, arguments=args, boundary_approved=False)
    assert not res.approved
    assert res.status == "BLOCKED_BY_BOUNDARY"
    with pytest.raises(BoundaryViolationError) as exc_info:
        gate.enforce_tool_call(tool_name, arguments=args, boundary_approved=False)
    assert "Zero Blast Radius" in str(exc_info.value)


def test_boundary_contract_allows_safe_commands_and_tools():
    gate = BoundaryContractGate()
    safe_cmds = ["pytest", "git status", "ls -la", "echo hello", "python -m build"]
    for cmd in safe_cmds:
        res = gate.check_command(cmd, boundary_approved=False)
        assert res.approved
        assert res.status == "APPROVED_SAFE"
        assert gate.enforce_command(cmd) == "APPROVED_SAFE"

    safe_tools = [
        ("read_file", {"path": "/etc/hosts"}),
        ("search_files", {"pattern": "boundary"}),
        ("terminal", {"command": "git status"}),
    ]
    for tool, args in safe_tools:
        res = gate.check_tool_call(tool, arguments=args, boundary_approved=False)
        assert res.approved
        assert res.status == "APPROVED_SAFE"
        assert gate.enforce_tool_call(tool, arguments=args) == "APPROVED_SAFE"


def test_boundary_contract_allows_destructive_with_explicit_approval():
    gate = BoundaryContractGate()
    res = gate.check_command("rm -rf /tmp/scratch", boundary_approved=True)
    assert res.approved
    assert res.status == "APPROVED_EXECUTIVE"
    assert gate.enforce_command("rm -rf /tmp/scratch", boundary_approved=True) == "APPROVED_EXECUTIVE"

    res_tool = gate.check_tool_call("wipe_database", {"target": "test_db"}, boundary_approved=True)
    assert res_tool.approved
    assert res_tool.status == "APPROVED_EXECUTIVE"
    assert gate.enforce_tool_call("wipe_database", {"target": "test_db"}, boundary_approved=True) == "APPROVED_EXECUTIVE"
