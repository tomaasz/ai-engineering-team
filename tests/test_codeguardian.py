import os
import subprocess
from pathlib import Path
import pytest

from ai_team.codeguardian import (
    SecretFinding,
    SECRET_PATTERNS,
    redact_token,
    scan_diff_for_secrets,
    validate_git_diff,
    install_git_hook,
    main as codeguardian_main,
)

def init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True, capture_output=True)

def test_redact_token():
    assert redact_token("short") == "***"
    assert redact_token("12345678") == "***"
    long_token = "sk-1234567890abcdef1234"
    preview = redact_token(long_token)
    assert preview.startswith("sk-1")
    assert preview.endswith("1234")
    assert "..." in preview
    assert "abcdef" not in preview

def test_secret_patterns_detection():
    # OpenAI
    dummy_openai = "sk-" + "a" * 30
    findings = scan_diff_for_secrets(f"+api_key = '{dummy_openai}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "OpenAI API Key"

    # Anthropic
    dummy_anthropic = "sk-ant-" + "b" * 30
    findings = scan_diff_for_secrets(f"+anthropic_key = '{dummy_anthropic}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "Anthropic API Key"

    # Google / Gemini
    dummy_gemini = "AIza" + "c" * 35
    findings = scan_diff_for_secrets(f"+gemini_token = '{dummy_gemini}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "Google AI / Gemini API Key"

    # GitHub
    dummy_github = "ghp_" + "d" * 36
    findings = scan_diff_for_secrets(f"+token = '{dummy_github}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "GitHub Token"

    # AWS
    dummy_aws = "AKIA" + "E" * 16
    findings = scan_diff_for_secrets(f"+aws_id = '{dummy_aws}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "AWS Access Key ID"

    # Stripe
    dummy_stripe = "sk_test_" + "f" * 24
    findings = scan_diff_for_secrets(f"+stripe_key = '{dummy_stripe}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "Stripe Secret Key"

    # Private key
    dummy_key = "-----BEGIN RSA PRIVATE KEY-----"
    findings = scan_diff_for_secrets(f"+{dummy_key}\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "Private Key Header"

    # Database URI
    dummy_db = "postgres://admin:supersecretpass123@localhost:5432/mydb"
    findings = scan_diff_for_secrets(f"+DATABASE_URL = '{dummy_db}'\n")
    assert len(findings) == 1
    assert findings[0].secret_type == "Database Connection URI"

def test_placeholder_suppression():
    # Placeholders should not trigger Generic Secret Assignment
    diff = "+api_key = 'YOUR_API_KEY_HERE'\n+token = '<PLACEHOLDER>'\n+secret = '${API_SECRET}'\n"
    findings = scan_diff_for_secrets(diff)
    assert len(findings) == 0

def test_scan_diff_file_and_line_tracking():
    sample_diff = "diff --git a/src/config.py b/src/config.py\n--- a/src/config.py\n+++ b/src/config.py\n@@ -10,3 +10,4 @@ def get_settings():\n     debug = True\n+    secret_token = 'sk-1234567890abcdef1234567890'\n     return debug\n"
    findings = scan_diff_for_secrets(sample_diff)
    assert len(findings) == 1
    assert findings[0].file_path == "src/config.py"
    assert findings[0].line_number == 11
    assert findings[0].secret_type == "OpenAI API Key"

def test_deleted_lines_not_flagged():
    diff = "-    secret_token = 'sk-1234567890abcdef1234567890'\n+    secret_token = os.getenv('API_KEY')\n"
    findings = scan_diff_for_secrets(diff)
    assert len(findings) == 0

def test_install_git_hook(tmp_path):
    init_git_repo(tmp_path)
    hook_path = install_git_hook(tmp_path)
    assert hook_path is not None
    assert hook_path.is_file()
    assert os.access(hook_path, os.X_OK)
    content = hook_path.read_text(encoding="utf-8")
    assert "CodeGuardian" in content

    # Idempotence check
    second_install = install_git_hook(tmp_path)
    assert second_install == hook_path
    assert content.count("CodeGuardian") == 1

def test_pre_commit_hook_blocks_secret_commit(tmp_path):
    init_git_repo(tmp_path)
    install_git_hook(tmp_path)

    dummy_key = "sk-ant-" + "1234567890" * 3
    test_file = tmp_path / "service.py"
    test_file.write_text(f"ANTHROPIC_KEY = '{dummy_key}'\n", encoding="utf-8")
    subprocess.run(["git", "add", "service.py"], cwd=tmp_path, check=True)

    res = subprocess.run(["git", "commit", "-m", "add secret"], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode != 0
    output = res.stdout + res.stderr
    assert "CodeGuardian ERROR" in output or "Security leak detected" in output

def test_validate_git_diff_staged(tmp_path):
    init_git_repo(tmp_path)
    dummy_key = "AIza" + "c" * 35
    file_path = tmp_path / "keys.py"
    file_path.write_text(f"GOOGLE_KEY = '{dummy_key}'\n", encoding="utf-8")
    subprocess.run(["git", "add", "keys.py"], cwd=tmp_path, check=True)

    findings = validate_git_diff(tmp_path, staged=True)
    assert len(findings) == 1
    assert findings[0].secret_type == "Google AI / Gemini API Key"

def test_cli_check_secrets(tmp_path, monkeypatch):
    init_git_repo(tmp_path)
    dummy_key = "ghp_" + "0" * 36
    file_path = tmp_path / "auth.py"
    file_path.write_text(f"GITHUB_TOKEN = '{dummy_key}'\n", encoding="utf-8")
    subprocess.run(["git", "add", "auth.py"], cwd=tmp_path, check=True)

    monkeypatch.setattr("sys.argv", ["ai-team", "check-secrets", str(tmp_path), "--staged"])
    from ai_team.cli import main
    rc = main()
    assert rc == 1

    file_path.write_text("GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')\n", encoding="utf-8")
    subprocess.run(["git", "add", "auth.py"], cwd=tmp_path, check=True)
    rc_clean = main()
    assert rc_clean == 0

def test_onboard_blocks_commit_on_secret(tmp_path):
    init_git_repo(tmp_path)
    from ai_team.installer import onboard
    dummy_key = "sk-" + "9" * 30
    (tmp_path / "leak.py").write_text(f"OPENAI_API_KEY = '{dummy_key}'\n", encoding="utf-8")
    
    rc = onboard(tmp_path, profile_name="core", solo=True, lang="en")
    assert rc == 1
