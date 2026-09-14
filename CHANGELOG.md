# Changelog

**English** · [Polski](CHANGELOG.pl.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.1.0] - 2026-09-14

Autonomous workflow and review improvements inspired by modern agentic architectures (Git worktrees, living memory, AST repository mapping, and dedicated review inspection).

### Added
- **Git Worktree Isolation (`--worktree`)**: Execute multi-agent runs inside `.ai/worktrees/<run_id>` without switching the user's active branch or disrupting local editing. Changes are preserved and cleanly committed to `ai/<run_id>` upon completion. Can also be enabled project-wide via `"useWorktree": true` in `ai-team.config.json`.
- **Run Review CLI (`ai-team review`)**: Inspect run statuses, risk verdicts, reviewer notes, and checks. Supports `--diff` (view full patch vs base), `--merge` (clean non-fast-forward merge into active branch), and `--discard` (prune and delete run branch).
- **AST Codebase Map (`src/ai_team/repomap.py`)**: Zero-dependency structural symbol map (classes, methods, functions) automatically injected into triage and orchestrator/architect prompts for accurate codebase navigation with minimal token footprint.
- **Dynamic Team Memory (`.ai/LEARNINGS.md`)**: Automatically logs reviewer findings, unresolved issues, and verification notes after each run, and injects recent learnings into subsequent runs to prevent repeated mistakes.

## [4.0.0] - 2026-09-12

Implementation of conclusions from the framework audit. Several default settings have changed so that they reject previously valid configurations — see Migration.

### Security
- Guardrail files (`ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, AI instruction files, `.agents/**`, `.claude/**`) always escalate to `HIGH`, so an agent cannot weaken its own review policy in a single unreviewed change. Modifying configuration during a run aborts the run.
- Environment sanitization now covers connection strings, agent sockets, and credential file pointers (`DATABASE_URL`, `SENTRY_DSN`, `SSH_AUTH_SOCK`, `KUBECONFIG`, `DOCKER_AUTH_CONFIG`, ...). TLS trust anchors are preserved explicitly, and provider API keys can be passed through per project via `passthroughEnv`.
- Read-only stage snapshots include run directories and `protectedIgnoredPaths`, preventing a stage from writing to Git-ignored files or tampering with another stage's saved responses.
- Verification command argv headers re-introducing shell wrappers (`bash -c`, `sh`, `pwsh`, `env`, `xargs`, ...) are rejected unless explicitly allowed via `allowShellWrapper`.
- Risk globs cover paths omitted in earlier versions (`session`, `jwt`, `rbac`, `sso`, `billing`, `checkout`, `*/versions/*`, `*.tfvars`, `Containerfile`, `.gitlab-ci.yml`, `Jenkinsfile`), and added lines are scanned for destructive SQL, disabled TLS checks, and unsafe deserialization.
- `LOW` risk now requires at least one independent reviewer; accepting unreviewed `LOW` requires explicit `allowUnreviewedLowRisk`.

### Fixed
- Stage outputs are written atomically and marked `.done` only upon successful completion. An interrupted run no longer resumes as if incomplete stages succeeded.
- Timeouts terminate the full agent process tree rather than only direct child processes, preventing zombie agents from modifying the repository after timeout.
- Every reviewer referenced in `reviewPolicy` is validated before starting a run, preventing failure after implementation when risk escalates.
- Exhausted review rounds complete as `CHANGES_REQUIRED` (exit code 2) with resume hints, preserving actionable progress.
- Invalid verdicts report provider, stage file, and response excerpt.
- `antigravity.triageEffort`, `implementationEffort`, and `verificationEffort` are correctly wired and validated. Unknown keys in `antigravity` are rejected to prevent configuration drift.
- Normalized working tree status messages into consistent English.

### Added
- `providerArgs` gives `codex` and `claude` per-role cost/quality controls overriding default runner flags.
- `models` accepts per-role mappings so read-only stages can use cheaper/faster models than implementation.
- `roleProviders.integrator` routes review remediation to a provider distinct from primary.
- `skipFinalVerificationAtLow` (default true) substitutes primary self-verification at `LOW` with independent reviewer verdict.
- `reuseBranchForFollowUp` continues work on current `ai/` branch instead of spawning another.
- `ai-team resume <run-id> --extra-rounds N` re-opens review rounds.
- `ai-team runs` lists run branches with status, diff vs base, and cleanup guidance.
- Review prompts carry explicit quality criteria and contents of project `SKILL.md` files.
- Reviewers receive generated `diff.patch` instead of reconstructing changes from scratch.
- `.claude/skills/project/` is installed and tracked as project-owned.
- Domain profiles seed sensitive `riskPaths` during configuration creation.
- `doctor` reports unfulfilled TODO markers in `PROJECT_CONTEXT.md`.
- VS Code tasks merge reports comment stripping and backup locations.
- Bootstrap prompts in `docs/BOOTSTRAP.md` updated for hardened configuration.
- `ai-team install . --lang pl` (and `--lang en`) installs localized agent instructions and skills.
- Every documentation file has a synchronized `.pl.md` equivalent with bidirectional navigation.

### Migration
- `reviewPolicy.LOW` must specify a reviewer, or `allowUnreviewedLowRisk: true` must be set.
- Remove `availabilityFallback` from `antigravity`; top-level key is maintained.
- Verification commands invoking shell wrappers require `"allowShellWrapper": true`.
- Provider CLIs authenticating via custom environment variables must be listed in `passthroughEnv`.
- Antigravity verification and reviewer stages default to `medium` effort. Set `antigravity.verificationEffort` to `high` for prior behavior.

---

## [Unreleased]

### Fixed
- Preserve pre-existing AI instructions and local changes across repeated installs and conflicting updates.
- Keep retired templates tracked; normalize project operations to the Git root.
- Merge JSONC VS Code tasks using ownership baselines and preserve custom entries.
- Required reviewer failures, missing reviewers, failed checks and invalid verdicts now prevent success.
- Create a unique branch for each run, including runs started on an existing `ai/` branch.

### Added
- Explicit conflict resolution (`resolve --strategy keep|upstream`), profile migration, profile listing and CLI version.
- Validated provider selection (`agy`, `codex`, `claude`), structured results, risk escalation from changed paths and bounded review rounds.
- Direct verification commands with working directories and timeouts, recorded exit codes and `result.json`.
- Expanded readiness diagnostics, optional CLI probes, regression tests and bilingual bootstrap prompts.
- `ai-team resume <run-id>|latest` continues an interrupted run, skipping already-completed agent/review stages, after verifying the branch still matches.
- Sanitized subprocess environments (secret-like variables stripped, `AI_TEAM_SUBPROCESS` marker) and process-group isolation for every spawned CLI and verification command.

### Migration
- Existing project configuration is preserved. Add `verification.commands` or a documented `verification.noChecksReason` before running.
- Review policies require one independent provider for MEDIUM and two for HIGH; availability fallback no longer permits success.
- Agent decision stages must emit the JSON format documented in `docs/ARCHITECTURE.md`.

---

## [3.0.1] - 2026-09-11

### Added
- Standard MIT License (`LICENSE`).
- Comprehensive bilingual documentation (`README.md` in English and `README.pl.md` in Polish) with language switchers.
- Project documents: `CONTRIBUTING.md`, `SECURITY.md`, and `CHANGELOG.md`.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) supporting Ubuntu and Windows on Python 3.10, 3.11, 3.12, and 3.13.
- Expanded test suite covering installer lifecycle, profiles, VS Code task merging, cross-platform path handling, runner routing/doctor, and security defaults.
- Expanded `.gitignore` covering Python cache, virtual environments, IDEs, OS artifacts, secrets, and AI run artifacts.
- Package packaging configuration in `pyproject.toml` including full metadata, project URLs, and dotfile inclusion for templates (`.agents`, `.claude`, `.vscode`).

### Changed
- Replaced private repository installation references with public HTTPS repository endpoints.
- Updated project bootstrap prompts (both EN and PL) for public distribution.
- Standardized package versioning across `pyproject.toml`, `VERSION`, and `src/ai_team/__init__.py`.

### Removed
- Legacy static `MANIFEST.txt` in favor of declarative `pyproject.toml` package-data.

---

## [3.0.0] - 2026-09-11

### Added
- Initial release of AI Engineering Team v3.
- Cross-platform CLI orchestrator (`ai-team`) with `install`, `update`, `status`, `doctor`, `run`, and `uninstall` commands.
- Multi-agent orchestration integrating Google Antigravity / Gemini CLI (`agy`), Anthropic Claude Code CLI (`claude`), and OpenAI Codex CLI (`codex`).
- Automated risk classification (LOW / MEDIUM / HIGH) with independent cross-model review pipelines.
- Profile-based installation system (`core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, `full`).
- VS Code task automation templates and non-destructive configuration management with conflict detection.
- Cross-platform support for Windows (PowerShell) and Linux (bash/zsh, VS Code Remote SSH).
