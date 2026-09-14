# Installation

**English** · [Polski](INSTALL.pl.md)

## Central CLI

Install Python 3.10+, Git, and `pipx`, then install the verified release:

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.2.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.3.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.4.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.5.0"
ai-team --version
```

Do not tag an unreleased commit as a release. Updating the CLI and updating project templates are separate operations:

```bash
pipx upgrade ai-engineering-team
ai-team update /path/to/project
```

For local development, use `./install-local.sh` on Linux or `.\install-local.ps1` on Windows.

## Project Setup

```bash
ai-team profiles
ai-team install . --auto --lang en
# or with an explicit profile:
ai-team install . --profile core --lang en
```

Available profiles: `core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, and `full`. The profile selects templates and skills; it does not automatically inspect the stack or verify commands.
Available profiles: `core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, and `full`. `--auto` automatically inspects the repository stack markers and selects the recommended profile.

`--lang` selects the language for installed agent instructions and skills (`en` default or `pl`). Only one language version is installed in a project, and the runner forms prompts in that same language. The chosen language is stored in `.ai-team/state.json` and as `language` in `ai-team.config.json`; `ai-team update . --lang pl` switches both.

Installation preserves existing files. On collision, the project version is kept, the incoming template is stored under `.ai-team/conflicts/<path>`, and the conflict is tracked. Local configuration (`PROJECT_CONTEXT.md`, `ai-team.config.json`, `.agents/skills/project/`, `.claude/skills/project/`) is never overwritten during updates.

```bash
ai-team status .
ai-team resolve . AGENTS.md --strategy keep
# or
ai-team resolve . AGENTS.md --strategy upstream
```

`keep` retains the project file. `upstream` overwrites with the incoming template. Neither performs semantic three-way merging; diff both copies first.

VS Code tasks are merged by task and input identifiers. JSONC comments and trailing commas are parsed, but a successful merge normalizes JSON and backs up the original.

Profile changes can be applied via `ai-team update . --profile web`.

## Automated Updates & Git Hygiene

To automate template updates in your CI pipeline, install the GitHub Actions workflow:
```bash
ai-team workflow .
```
This generates `.github/workflows/ai-team-update.yml` to automatically create weekly update Pull Requests.

To configure Git ignore rules:
```bash
# Ignore runtime logs and conflicts in .gitignore:
ai-team gitignore .

# Or run in local private mode (only via .git/info/exclude):
ai-team gitignore . --private
```

## Readiness

Complete `PROJECT_CONTEXT.md` — `doctor` reports unresolved `TODO` items as problems — and configure real verification commands or an explicit `noChecksReason`. If provider CLIs authenticate via environment variables, declare them in `passthroughEnv`; otherwise, credentials are stripped from child processes. Review and commit installation changes. By default, `run` requires a clean working tree, an initial commit, and no unresolved conflicts.

```bash
ai-team doctor . --probe
```

`doctor` verifies configuration, Git repository state, executable paths, conflicts, verification setup, and `TODO` placeholders in `PROJECT_CONTEXT.md`. `--probe` runs `--help` on CLIs. It does not verify authentication, model quotas, or network connectivity.

Remote SSH setups require `ai-team` and provider CLIs installed on the remote host.
