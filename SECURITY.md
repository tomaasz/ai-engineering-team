# Security Policy

**English** · [Polski](SECURITY.pl.md)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.0.x   | :white_check_mark: |
| 3.0.x   | :white_check_mark: |
| < 3.0   | :x:                |

---

## Reporting a Vulnerability

We take the security of AI Engineering Team seriously. If you discover a security vulnerability, **please do not disclose it in a public GitHub issue, discussion, or pull request.**

To report a vulnerability responsibly:

1. **GitHub Security Advisories (Recommended)**: Go to the repository's [Security Advisories](https://github.com/tomaasz/ai-engineering-team/security/advisories) tab and click **"Report a vulnerability"** to submit a private report.
2. If GitHub Security Advisories are unavailable, contact the repository maintainers via private channels on GitHub.

When submitting a report, please include:
- A description of the vulnerability and its potential impact.
- Step-by-step reproduction instructions or a minimal proof-of-concept.
- Affected components and operating system / environment details.

You will receive an acknowledgment within 48 hours, followed by updates as the issue is investigated and remediated.

---

## Security Model & Sensitive Areas

AI Engineering Team is an orchestrator that interacts with external AI CLI tools (Antigravity/Gemini CLI `agy`, Claude Code CLI `claude`, OpenAI Codex CLI `codex`) and manages local repository workspaces.

### Local Command Execution
- The framework invokes AI agents that can generate, modify, and test application code on your system.
- Agents operate with the privileges of the local user running the `ai-team` CLI.

### Sandboxing & Permissions
- By default, Antigravity runs with `sandbox: true` and `fullAuto: false`.
- Do **not** enable `--dangerously-skip-permissions` or `"fullAuto": true` unless operating within an isolated container or virtual machine.
- Independent reviewers (`claude`, `codex`) are strictly invoked in **read-only / plan-only** modes and forbidden from modifying source files or running mutations.

### Safe Defaults
- The framework **never** performs `git push`, `git merge`, or deployment automatically.
- Work is isolated to run branches (`ai/...`), leaving `main` untouched.
- Clean working trees are enforced before running tasks (`requireCleanWorkingTree: true`).

### Sensitive Information & Secrets
- Never pass private API tokens, passwords, `.env` files, or production credentials to agent prompts or commits.
- Ensure project `.gitignore` files exclude all credential formats (`.env`, `*.pem`, `*.key`, `.ai/runs/`).
- Subprocess environments are sanitized: variables matching credential patterns, connection strings (`_URL`, `_URI`, `_DSN`), agent sockets, and static blocklist entries (`KUBECONFIG`, `AWS_PROFILE`, ...) are stripped. Provider API keys needed by CLIs can be listed in `passthroughEnv`.
- **Environment filtering is not container isolation.** Agents run with the invoking user's privileges and can read `~/.aws/credentials`, `~/.ssh/`, and `.env` directly from disk. Use containers or virtual machines when this is a concern.

### Guardrails
- Files defining how the team reviews code (`ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, `.agents/**`, `.claude/**`) always escalate to HIGH risk and cannot pass unreviewed.
- Modifying `ai-team.config.json` during a run aborts the run.
- `verification.commands` execute with user privileges. Re-introducing shells in `argv[0]` is rejected without `allowShellWrapper`, but any interpreter can still run code: treat `ai-team.config.json` as trusted, reviewed configuration.
