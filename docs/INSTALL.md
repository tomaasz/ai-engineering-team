# Installation

## Central CLI

Install Python 3.10+, Git, and `pipx`, then install a revision you have inspected:

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@<verified-commit-or-release>"
ai-team --version
```

Do not present the existing `v3.0.1` tag as containing unreleased changes from the current branch. Pin the reviewed commit or a release created from it. Upgrading the CLI and updating project templates are separate actions:

```bash
pipx upgrade ai-engineering-team
ai-team update /path/to/project
```

For local development, use `./install-local.sh` on Linux or `.\install-local.ps1` on Windows.

## Project setup

```bash
ai-team profiles
ai-team install . --profile core
```

Packaged profiles include `core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, and `full`. A profile selects templates and skills; it does not discover the stack or prove commands are correct.

Installation preserves existing files. On collision it keeps the project copy, stages the incoming template in `.ai-team/conflicts/<path>`, and records a conflict. Local configuration (`PROJECT_CONTEXT.md`, `ai-team.config.json`, and `.agents/skills/project/`) is preserved on updates.

```bash
ai-team status .
ai-team resolve . AGENTS.md --strategy keep
# or
ai-team resolve . AGENTS.md --strategy upstream
```

`keep` accepts the project file. `upstream` installs the staged template. Neither performs a semantic merge; compare both copies first.

VS Code tasks are merged by identifiers. JSONC comments and trailing commas can be read, but a successful merge creates a backup and writes normalized JSON, so formatting and comments may be lost.

Change profile during update with `ai-team update . --profile web`. Files retired by a smaller profile can remain tracked until `uninstall`; review them when changing profiles.

## Readiness

Complete `PROJECT_CONTEXT.md` and configure real verification commands or an explicit `noChecksReason`. Review and commit installation changes. With default settings, `run` requires a clean working tree, an initial commit, and no unresolved conflicts.

```bash
ai-team doctor . --probe
```

`doctor` checks configuration, Git state, executable paths, conflicts, and verification presence. `--probe` only invokes CLI help. It cannot validate login, credentials, model availability, quota, network access, or permissions. Run a harmless real request through each configured provider before reporting full readiness.

Remote SSH installations need `ai-team` and provider CLIs installed on the remote host.
