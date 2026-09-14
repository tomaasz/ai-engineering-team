# Changelog

**English** · [Polski](CHANGELOG.pl.md)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.8.1] - 2026-09-15

### Fixed
- **Resilient JSON Output Extraction (`_extract_json`)**:
  - Fixed an issue where reviewer verdicts and triage responses wrapped in conversational preambles (e.g. `Confirmed: HEAD equals base commit... {"verdict": ...}`), markdown code fences (```` ```json ... ``` ````), or trailing commentary caused strict `json.loads` parsing failures (`Expected a JSON object with verdict...`).
  - Added robust 4-stage JSON extraction: fast-path direct parsing, markdown code fence extraction, outermost brace pair detection, and balanced brace depth scanner.
- **Claude Headless Batch Mode Permissions (`acceptEdits`)**:
  - Fixed Claude provider invocation in modifying stages (orchestrator / integrator). Changed `--permission-mode default` (which prompts interactively on stdin and blocks headless execution) to `--permission-mode acceptEdits`, enabling Claude to write deliverables and execute repository modifications without hanging.
  - Read-only stages (reviewer / verifier / triage) continue to strictly enforce `--permission-mode plan`.
  - Propagated `--dangerously-skip-permissions` to Claude when `fullAuto: true` is configured.
- **Subprocess stdin Disconnection (`stdin=DEVNULL`)**:
  - Redirected spawned agent subprocess stdin to `subprocess.DEVNULL`, eliminating Claude's 3-second stdin timeout warning (`no stdin data received in 3s`) and avoiding hangs in headless CI/CD and terminal execution.

## [4.8.0] - 2026-09-14

### Added
- **360° Application Audit Command (`ai-team audit`)**:
  - New built-in CLI command: `ai-team audit [project] [--output docs/AUDIT.md] [--lang pl|en] [--worktree] [--solo] [--auto-merge]`.
  - Conducts an end-to-end, rigorous inspection across 6 critical dimensions:
    1. **Architecture & Code Structure**: modularity, domain boundaries, technical debt, code smells, duplication, dead code.
    2. **Security & Vulnerabilities**: OWASP Top 10, CWE, secret/credential leaks, SQLi/Command injection, XSS, CSRF, SSRF, IDOR, dependency vulnerabilities.
    3. **Reliability & Error Handling**: swallowed errors, unhandled rejections, race conditions, memory leaks, open descriptors.
    4. **Performance & Database**: N+1 queries, missing indexes, event loop blocking, caching opportunities.
    5. **Testing & QA**: coverage gaps on critical flows, test integrity, mock veracity.
    6. **DevOps & Containers**: Dockerfile hygiene (multi-stage, non-root), structured logging, health checks (`/health`), fail-fast env validation.
  - Automatically produces a structured `docs/AUDIT.md` report with:
    - Executive Summary & Overall Health Score (A–F / 0–100%).
    - Findings Matrix with severity levels (`[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]`), exact `file:line` locations, and suggested fixes.
    - Deep-Dive Analysis with code proofs, security/stability impact, and minimal remediation snippets.
    - Prioritized Action Plan organized into Phase 1 (P0 immediate blockers), Phase 2 (P1), and Phase 3 (P2 backlog).
- **New Audit Skill (`audit/full-app-audit`)**:
  - Cross-platform skill templates in English (`SKILL.md`) and Polish (`SKILL.pl.md`) for both `.agents/skills/audit/full-app-audit/` and `.claude/skills/audit/full-app-audit/`.
  - Included across all project profiles (`core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, `full`).
- **Specialized Auditor Agent Persona (`auditor`)**:
  - Dedicated agent role configured for deep analysis and zero destructive code modifications (`.agents/agents/auditor.md` and `.claude/agents/auditor.md`).
  - Auto-suggested via `ai-team skills suggest` and auto-provisioned during audit tasks.

## [4.7.0] - 2026-09-14

### Added
- **One-Command Project Onboarding (`ai-team onboard` / `ai-team quickstart` / `ai-team setup`)**:
  - Automatically initializes Git (if not present), installs or updates `ai-team` with tech stack detection.
  - Automatically resolves template conflicts with `--strategy upstream`.
  - Automatically configures `ai-team.config.json` with safe defaults (`allowUnreviewedLowRisk: true`, smart verification commands for npm/pytest/cargo/go, solo/multi provider rules).
  - Automatically cleans `PROJECT_CONTEXT.md` (removes `TODO` placeholders with inferred metadata).
  - Automatically commits changes to Git and runs full healthcheck diagnostics (`ai-team doctor`).
- **Automated Onboarding Scripts (`setup-project.sh` & `setup-project.ps1`)**:
  - Universal Bash and PowerShell scripts enabling instant zero-config setup across multiple repositories with a single command.
- **Bulk Conflict Resolution (`ai-team resolve <project> all --strategy <keep|upstream>`)**:
  - Resolves all pending template update conflicts in a single command.

### Added
- **Single-Provider Solo Mode (`--solo` / `--single-provider` / `"singleProvider": true`)**:
  - Run the entire AI Engineering Team process on a single provider (`agy` / Gemini 3.8 Flash High) without requiring external CLI tools (`codex`, `claude`) or external quotas.
  - Review policy dynamically adapts: in solo mode, independent review roles execute using isolated read-only `primaryProvider` processes (`--mode plan`, `--sandbox`, zero write permissions).
  - Works seamlessly with `ai-team run --solo` or by setting `"singleProvider": true` in `ai-team.config.json`.
  - Added `--solo` flag to `ai-team doctor` to verify system readiness specifically for solo workflows without flagging missing multi-provider CLIs.
- **Reviewer Availability Fallback (`availabilityFallback`)**:
  - Automatically enabled by default to prevent workflow interruptions when external reviewer services hit quota limits, rate limits (HTTP 429), auth failures, or network timeouts.
  - If an external reviewer CLI fails during review execution, the runner catches the error, logs `[FALLBACK] Reviewer '<reviewer>' failed (...). Falling back to isolated '<primary>' reviewer.`, and immediately re-executes the review using an isolated read-only primary provider.
  - Saves dedicated fallback artifacts (`review-<round>-<reviewer>-fallback.json`) and flags `fallbackFrom` in the final review report.
  - Configurable via `"availabilityFallback": true/false` in `ai-team.config.json` or CLI flags `--availability-fallback` / `--no-availability-fallback`.

## [4.5.0] - 2026-09-14

### Added
- **Automated Upstream Updates Workflow (`ai-team workflow [project]`)**:
  - Installs a ready-to-use GitHub Actions workflow (`.github/workflows/ai-team-update.yml`) in the target project.
  - Automatically runs on a weekly schedule (or on manual trigger), upgrades `ai-engineering-team`, executes `ai-team update .`, and creates a Pull Request (`chore/ai-team-update`) when template or skill updates are available.
- **Enhanced Repository Git Hygiene (`ai-team gitignore [project] [--private]`)**:
  - Automatically provisions `.ai-team/.gitignore` during installation and updates to protect temporary merge conflicts and backups from untracked repository pollution.
  - `ai-team gitignore`: Configures standard runtime ignore rules (`.ai/runs/`, `.ai-team/conflicts/`, etc.) in the project's root `.gitignore`.
  - `ai-team gitignore --private`: Configures a completely private solo developer mode in `.git/info/exclude` so that all AI Engineering Team files remain local and invisible to team/remote repositories.
- **Upstream Version Checking (`ai-team update --check` and `ai-team status`)**:
  - Satiates offline reliability while allowing `ai-team update --check` and `ai-team status` to notify developers when a newer release is published on GitHub.

## [4.4.0] - 2026-09-14

### Added
- **Proactive & Autonomous Skill Provisioning by AI Agents**:
  - The AI Orchestrator now automatically and autonomously manages skills without requiring user intervention or manual CLI commands.
  - **Pre-Implementation Stage**: Prior to starting work, the runner inspects project tech stack markers and task prompt intent to automatically install missing matching skills from the catalog.
  - **Post-Implementation Stage**: Inspects files touched or introduced during implementation diff (e.g. Dockerfiles, SQL schemas, migrations) and automatically provisions matching skills before independent review rounds.
  - **Autonomous Project Skills**: Instructed agents in `AI_TEAM.md` and `AGENTS.md` to formulate and maintain project-specific conventions and patterns under `.agents/skills/project/<name>/SKILL.md`.
  - **Configuration & Opt-Out**: Enabled by default (`"autoSkills": true`), with optional manual opt-out via `--no-auto-skills` flag in `ai-team run` or setting `"autoSkills": false` in `ai-team.config.json`.

## [4.3.0] - 2026-09-14

### Added
- **Intelligent Tech Stack Detection & Auto-Install (`ai-team install --auto`)**: Automatically analyzes repository markers (`pyproject.toml`, `package.json`, `alembic`, `Dockerfile`, etc.) to detect languages, frameworks, and databases, and installs the optimal domain profile.
- **Dedicated Skill Management CLI (`ai-team skill` / `ai-team skills`)**:
  - `list`: Inspect all installed skills (with status `MANAGED`, `LOCAL`, `CUSTOM`) and catalog skills.
  - `suggest`: Analyze repository stack and display skill recommendations with detailed rationales.
  - `add <skill>`: Install a specific skill from the catalog into both `.agents/skills/` and `.claude/skills/` and track in `.ai-team/state.json`.
  - `remove <skill>`: Safely remove a managed skill and unregister from tracking.
- **Dynamic Task-Based Skill Routing**: The orchestrator in `runner.py` intelligently matches domain skills against the task prompt and modified files, prioritizing relevant instructions while avoiding context window waste.
- **Expanded Skill Catalog**: Added `devops/docker-quality` (container security, multi-stage builds, non-root users) and `security/secure-coding` (OWASP defense, input sanitization, least privilege) in both English and Polish.

## [4.2.0] - 2026-09-14

### Added
- **Automated Merge Prompt after Worktree Isolation**: After completing a task in an isolated Git worktree (`--worktree`), the CLI automatically prompts whether to deploy/merge changes directly into the active branch (`main`).
  - `[y]es`: Merges the run branch (`git merge --no-ff`) and automatically deletes the temporary branch (`git branch -D`) to keep the repository completely clean with zero branch clutter.
  - `[d]iff`: Displays the full patch and re-prompts.
  - `[x] discard`: Discards changes and immediately removes the temporary branch.
  - `[n]o`: Keeps the branch for later review via `ai-team review <run_id>`.
- **Automatic Empty Run Cleanup**: If agents made no code changes during the run, the temporary branch is automatically pruned without interrupting the user.
- **Automation Flags for CI & Scripting**: Added `--auto-merge` (`--merge`), `--auto-discard` (`--discard`), and `--non-interactive` flags to `ai-team run`, as well as the `"autoMerge": true` configuration setting.
- **Auto-Deletion on CLI Merge**: `ai-team review <run_id> --merge` now automatically removes the merged branch by default to prevent orphan branch accumulation (supported with `--keep-branch` if preservation is desired).

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
