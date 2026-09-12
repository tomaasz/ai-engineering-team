# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [3.0.1] - 2026-09-11

### Added
- Durable run manifests, safe retrying resume for failed/pending stages, redacted JSONL traces, and atomic evaluation artifacts. Resume refuses changed branch/base or dirty trees and requires persisted inputs.
- Sanitized subprocess environments with an explicit `AI_TEAM_SUBPROCESS` marker and repository CWD boundary checks.
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
