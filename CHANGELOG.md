# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
