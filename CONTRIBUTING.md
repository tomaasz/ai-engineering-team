# Contributing to AI Engineering Team

**English** · [Polski](CONTRIBUTING.pl.md)

Thank you for your interest in contributing to AI Engineering Team! This document provides guidelines and instructions for contributing to this project.

---

## Code of Conduct & Principles

- **Security First**: AI Engineering Team orchestrates autonomous AI agents that run local commands and edit code. All contributions must maintain strict security boundaries (sandboxing, permission gates, zero auto-push/auto-deploy).
- **Cross-Platform**: Every feature, path manipulation, and task runner must work seamlessly on both Windows and Linux (including VS Code Remote SSH). Always use `pathlib.Path` and avoid shell-specific assumptions.
- **Minimal Dependencies**: The core package strives to have zero runtime dependencies beyond Python's standard library.

---

## Development Setup

### Requirements

- Python 3.10+
- Git
- `pip` or `pipx`

### Setup Workflow

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/tomaasz/ai-engineering-team.git
   cd ai-engineering-team
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. Install the package in editable mode with development dependencies:
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

---

## Running Tests

We use `pytest` for testing. All unit tests mock external CLI calls (`agy`, `claude`, `codex`) and do not require active model API subscriptions or credentials.

Run the test suite:
```bash
pytest -v
```

Before submitting a pull request, ensure:
1. All tests pass on your environment.
2. New features or bug fixes include corresponding unit tests.
3. Package build succeeds:
   ```bash
   python -m build
   ```

### Documentation is part of the test suite

The test suite validates documentation consistency with code, as they previously drifted apart:

- Every key in `templates/ai-team.config.json` and in `antigravity` must be documented in `docs/CONFIGURATION.md`.
- Both prompt versions in `docs/BOOTSTRAP.md` must cover settings critical for bootstrap.
- Every human-facing document requires a `.pl.md` counterpart with the same heading structure and reciprocal link.
- Every template in `templates/` requires a `.pl.md` variant.

When adding a configuration option or document, update both language versions in the same PR.

---

## Branching & Commit Guidelines

### Branch Naming

- Features: `feature/<short-description>`
- Bug fixes: `fix/<short-description>`
- Documentation: `docs/<short-description>`
- Release prep: `public-prep/<version>`

### Commit Messages

Write clear, concise commit messages following standard conventions:
```text
<type>(<scope>): <summary>

[optional body]
```
Examples:
- `feat(installer): add support for custom template manifests`
- `fix(paths): normalize backslashes on Windows`
- `docs(readme): update quick start guide`
- `test(runner): add mock tests for triage risk evaluation`

Never commit secrets, API keys, private credentials, or local environment paths.

---

## Pull Request Workflow

1. Push your changes to your feature branch on your fork.
2. Open a Pull Request targeting the `main` branch of `tomaasz/ai-engineering-team`.
3. Provide a clear summary of what changed, rationale, test results, and any security considerations.
4. Ensure CI passes on both Ubuntu and Windows matrix environments.
5. Address any review feedback.

