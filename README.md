# AI Engineering Team

[English](README.md) | [Polski](README.pl.md)

[![CI](https://github.com/tomaasz/ai-engineering-team/actions/workflows/ci.yml/badge.svg)](https://github.com/tomaasz/ai-engineering-team/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/tomaasz/ai-engineering-team?include_prereleases)](https://github.com/tomaasz/ai-engineering-team/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Cross-platform multi-agent software engineering team orchestrator for Gemini / Google Antigravity, Codex, and Claude Code.

---

## What It Is

**AI Engineering Team** is a multi-agent orchestration framework for software developers, designed to embed an autonomous, role-specialized software engineering team directly into any Git repository.

Rather than relying on a single prompt or a one-size-fits-all assistant model, AI Engineering Team coordinates specialized agent roles — Architect, Researcher, Implementer, Test Engineer, and Reviewer — combined with automatic risk triage and **independent cross-model verification**.

## The Problem It Solves

- **Verification hallucinations**: Single agents often claim tests pass without actually executing them, or fail to notice regressions in their own solutions.
- **Cognitive echo-chambers**: A model reviewing its own code reproduces its initial assumptions, overlooking security flaws and architectural degradation.
- **Repository pollution and breakage risk**: Uncontrolled agents can overwrite uncommitted user work, alter configuration files, force-push branches, or trigger accidental deployments.
- **Cross-platform headaches**: Script-based agent configurations break frequently when transitioning between Windows, Linux servers, and Remote SSH sessions.

AI Engineering Team solves these issues through:
1. Enforced isolation on dedicated Git branches (`ai/...`) and requiring a clean working tree.
2. Routing tasks through an automated **Triage & Risk Gate**: LOW, MEDIUM, HIGH.
3. Leveraging **external, independent models** (Claude Code and OpenAI Codex) to perform read-only inspection audits before code is finalized.
4. Protecting user-customized files with checksum tracking and automatic conflict detection during framework updates.

---

## Architecture

### Orchestration Pipeline

```text
User prompt
    ↓
Triage
    ↓
Gemini / Antigravity Team
    ├── Architect
    ├── Researcher
    ├── Implementer
    ├── Test Engineer
    └── Reviewer
    ↓
Risk Gate
    ├── LOW    → Gemini
    ├── MEDIUM → + Codex
    └── HIGH   → + Claude + Codex
    ↓
Integrator
    ↓
Final Verifier
    ↓
Git branch + report
```

### Model Roles

| Model / CLI | Primary Role | Execution Characteristics |
| ----------- | ------------ | ------------------------- |
| **Google Antigravity / Gemini (`agy`)** | Core Team & Orchestration | Primary implementation engine: Architect, Researcher, Implementer, Test Engineer, and Integrator. Operates inside a secure sandbox. |
| **OpenAI Codex (`codex`)** | Independent Reviewer (MEDIUM & HIGH) | Operates in an ephemeral read-only inspection mode. Analyzes correctness, edge cases, and regressions without visibility into other reviews. |
| **Anthropic Claude Code (`claude`)** | Independent Reviewer (HIGH) | Operates in strict plan/read-only mode for critical tasks (security, database migrations, auth). Generates evidence reports without modifying files. |

### Why Independent Multi-Model Review?

Different model architectures have distinct training biases, limitations, and blind spots. When a model implements a complex refactoring, it tends to rationalize its own bugs during self-review. Introducing Codex and Claude as independent reviewers creates an adversarial verification dynamic. Reviewers cannot see each other's reports, ensuring an unbiased assessment. The Integrator then verifies every reported concern directly against the codebase.

### Risk Classification

- **LOW**: Minor, fully reversible changes (e.g., typos, local helpers, formatting). Handled entirely by the core Gemini/Antigravity team without external review overhead.
- **MEDIUM**: Multi-file modifications, new features, public API changes, or significant refactoring. Automatically triggers an independent review by Codex.
- **HIGH**: Critical modifications: authentication, authorization, cryptography, secrets management, database migrations, infrastructure, or core business logic. Requires dual independent reviews by Claude Code and Codex.

---

## Features

- **Role specialization**: Dedicated agent personas for architecture, research, implementation, testing, integration, and final verification.
- **Git Worktree Isolation**: Run agent teams in isolated worktrees (`--worktree`) without switching your active branch or interrupting ongoing local edits.
- **Interactive Review CLI**: `ai-team review` allows inspecting verdicts, viewing diffs (`--diff`), cleanly merging (`--merge`), or discarding (`--discard`) run branches.
- **AST Codebase Map**: Fast zero-dependency symbol mapping of classes and functions keeps model prompts context-aware without token bloat.
- **Dynamic Team Memory**: Review findings and lessons are automatically preserved in `.ai/LEARNINGS.md` and fed into future runs.
- **Deterministic state tracking**: SHA-256 checksums in `.ai-team/state.json`. Updates never overwrite locally modified files — conflicts are moved to `.ai-team/conflicts/`.
- **Project context preservation**: `PROJECT_CONTEXT.md`, `ai-team.config.json`, and `.agents/skills/project/` are protected and preserved during updates.
- **Full cross-platform support**: Native support for Windows 11 (PowerShell) and Linux (bash/zsh), including VS Code Remote SSH.
- **VS Code integration**: Automatic generation and non-destructive merging of tasks in `.vscode/tasks.json` (prompt execution, doctor diagnostics, updating).
- **Strict safety model**: No automatic push, merge, or deployment. All work occurs on dedicated `ai/...` branches.

---

## Requirements

- **Python**: 3.10 or newer
- **Git**: Installed and accessible in `$PATH`
- **Agent CLI Tools**:
  - `agy` (Google Antigravity CLI) — **Required** (primary executor; powers both full multi-model teams and solo mode)
  - `codex` (OpenAI Codex CLI) — Optional (used for consensus reviews; automatic fallback to `agy` if missing or quota exhausted)
  - `claude` (Anthropic Claude Code CLI) — Optional (used for high-risk reviews; automatic fallback to `agy` if missing or quota exhausted)

> [!NOTE]
> Log in to `agy`, `claude`, and `codex` interactively in your terminal at least once before running unattended tasks.

---

## Installation

The recommended installation method across all platforms is [`pipx`](https://pypa.github.io/pipx/):

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"
```

### Installing a Specific Version

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.2.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.3.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.4.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.5.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.6.0"
```

### Upgrading

```bash
pipx upgrade ai-engineering-team
```

### Developer Installation via SSH (Optional)

```bash
pipx install "git+ssh://git@github.com/tomaasz/ai-engineering-team.git"
```

### Local Repository Installation

**Windows (PowerShell):**
```powershell
.\install-local.ps1
```

**Linux (Bash):**
```bash
./install-local.sh
```

---

## Quick Start

### Option A: One-Command Automated Onboarding (Recommended)

To fully configure and prepare any existing or new project in seconds:

```bash
ai-team onboard .
# or in solo mode (single provider, e.g. Claude or Gemini only):
ai-team onboard . --solo
```

*This command automatically:*
1. Initializes Git repository (if missing).
2. Auto-detects project tech stack and installs matching profile (`--auto`).
3. Automatically resolves any template conflicts (`--strategy upstream`).
4. Configures `ai-team.config.json` (auto-detects test runners, permits unreviewed LOW-risk runs, sets solo/multi provider rules).
5. Populates initial `PROJECT_CONTEXT.md` (cleans TODO placeholders with inferred metadata).
6. Commits setup to Git and executes system readiness verification (`ai-team doctor`).

Standalone onboarding scripts are also available:
- **Linux / WSL (Bash):** `./setup-project.sh /path/to/project`
- **Windows (PowerShell):** `.\setup-project.ps1 C:\path\to\project`

---

### Option B: Manual Step-by-Step Installation

1. Navigate to your target project directory:
   ```bash
   cd /path/to/your-project
   ```

2. Install AI Engineering Team with your chosen profile:
   ```bash
   ai-team install . --profile python
   ```

3. Verify environment configuration:
   ```bash
   ai-team doctor .
   ```

4. Run a task (optionally in an isolated worktree or solo mode):
   ```bash
   ai-team run . "Add CSV export feature with full test coverage" --worktree
   # or run in solo mode (100% agy/Gemini, no external CLIs/quotas required):
   ai-team run . "Add CSV export feature" --solo
   ```
   *In `--worktree` mode, changes are isolated in a temporary worktree. When the run finishes, the CLI automatically prompts:*
   ```text
   Deploy changes to active branch 'main'?
     [y]es       - merge changes into 'main' and delete temporary branch
     [d]iff      - view full diff of changes
     [x] discard - discard changes and delete temporary branch
     [n]o        - keep branch for manual review later
   Choice [y/d/x/n]:
   ```
   *Choosing **[y]es** merges into your branch and immediately deletes the temporary branch, maintaining a clean repository with zero branch clutter.*

5. Review the run and merge or discard later (if kept):
   ```bash
   ai-team review            # View summary of verdicts and checks
   ai-team review --diff     # View complete patch
   ai-team review --merge    # Cleanly merge into current branch (auto-deletes branch)
   ai-team review --discard  # Discard and delete the run branch
   ```

---

### Option C: 360° Comprehensive Application Audit (`ai-team audit`)

Perform an exhaustive, multi-dimensional code, architecture, and security inspection without writing manual audit prompts:

```bash
ai-team audit .
# or in solo mode inside an isolated worktree:
ai-team audit . --worktree --solo
# generate English report into a custom location:
ai-team audit . --output docs/SECURITY_AUDIT.md --lang en
```

*What `ai-team audit` inspects across 6 critical dimensions:*
1. **Architecture & Code Quality**: modularity, domain boundaries, code smells, technical debt, dead code, DRY violations.
2. **Security & Vulnerabilities**: OWASP Top 10 (2025), CWE, secret leaks, injection flaws (SQLi/Command), XSS, CSRF, SSRF, IDOR, dependency CVEs.
3. **Reliability & Error Handling**: swallowed exceptions, unhandled Promise rejections, race conditions, resource leaks, open descriptors.
4. **Performance & Database**: N+1 queries, missing indexes, event loop blocking, caching opportunities.
5. **Testing & QA**: coverage gaps on critical flows, test integrity, mock veracity.
6. **DevOps & Operations**: Dockerfile hygiene (multi-stage, non-root), structured logging, health checks (`/health`), fail-fast env validation.

The resulting audit report is saved to `docs/AUDIT.md` (or your custom `--output` path) featuring an Executive Summary, Findings Matrix with severity levels (`[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]`), exact code proofs, and a prioritized remediation roadmap (P0/P1/P2).

---

## Installation Profiles

Profiles determine the set of skills and templates installed:

| Profile | Target Domain | Key Components |
| ------- | ------------- | -------------- |
| `core` | Universal baseline | Base agents, code review, task planning, general testing. |
| `python` | Python applications | Base skills + Python quality, type annotations, pytest standards. |
| `web` | Web & Frontend | Base skills + browser automation, DOM inspection, UI testing. |
| `postgres` | Database projects | Base skills + PostgreSQL safety, migrations, lock analysis. |
| `ocr` | Document processing | Base skills + OCR pipelines, layout parsing, text extraction. |
| `geneteka` | Genealogical records | Base skills + specialized ETL pipelines for dataset parsing. |
| `full` | Multi-domain projects | Complete set of all available skills and roles. |

---

## Skill Management and Auto-Discovery

`ai-team` provides built-in tech stack detection, skill catalog management, and task-based dynamic context routing:

- **Auto-Detect Profile**:
  ```bash
  ai-team install . --auto
  ```
  Scans repository markers (`pyproject.toml`, `package.json`, `alembic`, `Dockerfile`, etc.) and installs the recommended profile.

- **Inspect Installed & Available Skills**:
  ```bash
  ai-team skill list
  ```

- **Suggest Skills for Current Codebase**:
  ```bash
  ai-team skill suggest
  ```

- **Add or Remove Specific Skills**:
  ```bash
  ai-team skill add devops/docker-quality
  ai-team skill add security/secure-coding
  ai-team skill remove devops/docker-quality
  ```

- **Dynamic Task Routing in Runner**:
  During `ai-team run`, the orchestrator prioritizes relevant skills (e.g. `postgres` for SQL/migration tasks, `python` for Python scripts) while always enforcing baseline safety and review criteria.

- **Autonomous & Proactive Provisioning by AI Agents**:
  You do not need to manually install skills. When executing `ai-team run`, the AI orchestrator automatically detects missing skills for the task or newly introduced technologies in the implementation diff (e.g. adding `devops/docker-quality` when Docker files are created, or `postgres/postgres` for SQL migrations) and provisions them autonomously before independent review.
  - To disable automatic provisioning: use `--no-auto-skills` or set `"autoSkills": false` in `ai-team.config.json`.
  - Agents can also proactively formulate project-specific conventions under `.agents/skills/project/`.

---

## VS Code Integration

During installation, `ai-team` inspects `.vscode/tasks.json`. If it exists, it cleanly appends AI Team tasks without modifying or duplicating user tasks.

### Available Tasks:
- **`AI Team: Run prompt`**: Prompts for a task description via an input modal and runs `ai-team run`.
- **`AI Team: Doctor`**: Runs environment diagnostics inside the integrated terminal.
- **`AI Team: Update`**: Synchronizes project skills and templates with the installed framework version.

To run: `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS) → `Tasks: Run Task` → Select task.

---

## Windows

- Full support on Windows 10/11 using PowerShell 7 or Windows PowerShell 5.1.
- Ensure Python and Git are present in your `PATH`.
- File paths are handled cross-platform with normalized path separators.

## Linux

- Full support on Ubuntu, Debian, Fedora, Arch, Alpine, and other distributions.
- Operates seamlessly in `bash` and `zsh`.

## VS Code Remote SSH

When working on a remote server or container:
- Install `ai-team` and the agent CLIs (`agy`, `claude`, `codex`) **on the remote machine**.
- VS Code tasks execute directly in the remote environment, accessing remote files, containers, and development services.

---

## Updating Framework in a Project

To update templates and skills in a project:
```bash
cd /path/to/project
ai-team update .
```

- **Protected files**: `PROJECT_CONTEXT.md`, `ai-team.config.json`, and `.agents/skills/project/` are never overwritten.
- **Conflict handling**: If a template file was modified locally, `ai-team update` preserves your local changes and writes the upstream version to `.ai-team/conflicts/<path>`, preventing accidental data loss.

### Checking for Available Updates

```bash
ai-team update --check
ai-team status
```

### Automated Updates with GitHub Actions

To enable automated weekly PRs whenever templates or skills are updated upstream:
```bash
ai-team workflow .
```
This generates `.github/workflows/ai-team-update.yml` in your project repository. When committed, it runs weekly on Monday or on demand via `workflow_dispatch`, executing `ai-team update .` and opening a PR if changes are detected.

### Git and Repository Hygiene (.gitignore vs Private Mode)

`ai-team` automatically creates `.ai/.gitignore` (ignoring `runs/` and `latest.txt`) and `.ai-team/.gitignore` (ignoring `conflicts/` and `backups/`).

To configure the root repository:
```bash
# Standard team mode: ignores runtime logs and conflicts in .gitignore
ai-team gitignore .

# Private solo developer mode: ignores all AI files in local .git/info/exclude
ai-team gitignore . --private
```

---

## Security Model

> [!WARNING]
> **Local Code Execution**: AI Engineering Team runs AI models that can generate and execute shell commands, install packages, and modify files on your system.

To protect your system and repositories, the framework enforces:
1. **No automatic push or merge**: `ai-team` **never** pushes to remote repositories or merges changes into primary branches.
2. **No automatic deployment**: The runner does not execute deployment scripts or modify production infrastructure.
3. **Branch isolation**: All work is performed on isolated branches prefixed with `ai/`.
4. **Sandbox enabled by default**: Antigravity runs with `"sandbox": true`.
5. **Full Auto disabled by default**: `"fullAuto": false` prevents permission bypassing (`--dangerously-skip-permissions`). Only enable this inside isolated containers.
6. **Read-only external reviewers**: Reviewer agents (`claude`, `codex`) run in strict read-only / plan-only mode and cannot modify files.

See [SECURITY.md](SECURITY.md) for full security policies and vulnerability reporting.

---

## Project Bootstrap (Initialization Prompts)

If you want an autonomous agent to configure AI Engineering Team in a new or existing repository, paste one of the following prompts into its interface.

### English Prompt (EN)

```text
Install and configure the AI Engineering Team framework in this repository from the public repository:

https://github.com/tomaasz/ai-engineering-team

Your goal is not only to install the framework, but to adapt it to this specific project so that later `ai-team run . "<prompt>"` can safely analyze, implement, test, and review changes.

RULES:
- First, thoroughly inspect the repository.
- Do not modify application or business logic code during this setup task.
- Do not run git push, merge, deployment, force push, git reset --hard, or git clean.
- Do not delete existing project configuration.
- If AI Engineering Team is already installed, do not reinstall blindly — check `ai-team status .` and use `ai-team update .` when appropriate.
- Do not guess test, build, or technology commands. Derive them from verified project files.
- Preserve existing local Skills and AI configuration if present.
- If any information is uncertain, mark it as unverified instead of inventing a value.

PHASE 1 — PROJECT DISCOVERY
Inspect the repository and determine:
1. Operating system and environment you are currently running in;
2. Programming languages and runtime versions;
3. Frameworks and libraries;
4. Package manager and dependency installation workflow;
5. Project structure and entry points;
6. Application startup and local dev commands;
7. Existing test suites (unit, integration, e2e);
8. Linting, formatting, and type-checking commands;
9. Build and compilation steps;
10. Database and migrations workflow;
11. Docker / container setup;
12. CI/CD pipelines;
13. Especially sensitive or risky areas (auth, migrations, data loss points);
14. Parts of the codebase that agents should never modify without explicit approval.

PHASE 2 — CHECK AI ENGINEERING TEAM
Run:
ai-team --help
ai-team status .

If `ai-team` is unavailable, install it:
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"

PHASE 3 — SELECT A PROFILE
Based on the actual repository contents, choose the most appropriate available AI Engineering Team profile:
- core
- python
- web
- postgres
- ocr
- geneteka
- full

Choose the smallest profile that sensibly covers the project. If capabilities from multiple domains are needed, choose the closest base profile and add missing capabilities as project-specific Skills rather than installing unnecessary components.

PHASE 4 — INSTALL OR UPDATE
If not installed:
ai-team install . --profile <SELECTED_PROFILE>

If already installed:
ai-team update .

Then run:
ai-team status .
ai-team doctor .

PHASE 5 — CUSTOMIZE PROJECT_CONTEXT.md
Populate `PROJECT_CONTEXT.md` based on verified facts from the repository:
- Project Purpose
- Tech Stack
- Main Verified Commands (install, dev, run, lint, format, typecheck, unit tests, integration tests, build, migrations)
- Architecture Overview
- Critical Areas & Failure Points
- Areas Requiring Explicit Approval
- Definition of Done

PHASE 6 — PROJECT-SPECIFIC SKILLS
Determine whether this project needs repository-specific Skills under:
.agents/skills/project/
Create them only for knowledge unique to this repository. Do not duplicate generic language rules already provided by standard profiles.

PHASE 7 — REVIEW ai-team.config.json
Ensure default safety policies remain active:
- requireCleanWorkingTree: true
- createBranchForEachRun: true
- antigravity.sandbox: true
- antigravity.fullAuto: false
- No automatic push, merge, or deployment.

PHASE 8 — VALIDATION
Run:
ai-team doctor .
ai-team status .
git status
git diff

If safe and fast tests exist, run them to verify the commands recorded in PROJECT_CONTEXT.md.

PHASE 9 — FINAL REPORT
Provide a concise summary:
- Detected stack and components
- Installed profile and version
- Doctor status
- Verified commands recorded in PROJECT_CONTEXT.md
- Project-specific skills created
- List of created or modified files
- Conclude with: `AI_TEAM_READY: YES` (or `NO` with specific missing items).
```

### Polish Prompt (PL)

```text
Zainstaluj i skonfiguruj w tym repozytorium framework AI Engineering Team z publicznego repozytorium:

https://github.com/tomaasz/ai-engineering-team

Twoim celem jest nie tylko zainstalowanie frameworka, ale przede wszystkim dopasowanie go do tego konkretnego projektu, tak aby później polecenie `ai-team run . "<prompt>"` mogło bezpiecznie analizować, implementować, testować i reviewować zmiany.

ZASADY:
- Najpierw dokładnie przeanalizuj repozytorium.
- Nie zmieniaj kodu biznesowego aplikacji podczas tej konfiguracji.
- Nie wykonuj git push, merge, deployment, force push, git reset --hard ani git clean.
- Nie usuwaj istniejącej konfiguracji projektu.
- Jeżeli AI Engineering Team jest już zainstalowany, nie instaluj go ponownie w ciemno — sprawdź `ai-team status .` i w razie potrzeby użyj `ai-team update .`.
- Nie zgaduj komend testowych, buildów ani technologii. Ustal je z istniejących plików projektu.
- Zachowaj istniejące lokalne Skills i konfigurację AI, jeśli już istnieją.
- Jeżeli jakaś informacja jest niepewna, oznacz ją jako niezweryfikowaną zamiast wymyślać wartość.

ETAP 1 — ROZPOZNANIE PROJEKTU
Przeanalizuj repozytorium i ustal:
1. System operacyjny i środowisko;
2. Języki programowania i runtime;
3. Frameworki i biblioteki;
4. Package manager i sposób instalowania zależności;
5. Strukturę projektu i entry points;
6. Sposób uruchamiania aplikacji w dev;
7. Istniejące testy (unit, integration, e2e);
8. Linting, formatowanie i type checking;
9. Proces budowania (build);
10. Bazę danych i migracje;
11. Docker / kontenery;
12. CI/CD;
13. Obszary szczególnie ryzykowne (auth, migracje, utrata danych);
14. Części projektu, których agent nie powinien modyfikować bez wyraźnej zgody.

ETAP 2 — SPRAWDZENIE AI ENGINEERING TEAM
Sprawdź:
ai-team --help
ai-team status .

Jeżeli `ai-team` nie jest dostępny, zainstaluj go:
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"

ETAP 3 — DOBÓR PROFILU
Wybierz optymalny profil AI Engineering Team dla projektu:
- core
- python
- web
- postgres
- ocr
- geneteka
- full

Wybierz najmniejszy profil, który sensownie pokrywa projekt. Brakujące specyficzne kompetencje dodaj jako project-specific Skills zamiast instalować niepotrzebne komponenty.

ETAP 4 — INSTALACJA LUB AKTUALIZACJA
Jeżeli framework nie jest zainstalowany:
ai-team install . --profile <WYBRANY_PROFIL>

Jeżeli jest już zainstalowany:
ai-team update .

Następnie sprawdź:
ai-team status .
ai-team doctor .

ETAP 5 — DOSTOSOWANIE PROJECT_CONTEXT.md
Uzupełnij `PROJECT_CONTEXT.md` na podstawie faktycznej analizy repozytorium:
- Cel projektu
- Stack technologiczny
- Rzeczywiste, zweryfikowane komendy (install, dev, run, lint, format, typecheck, testy, build, migracje)
- Architektura
- Krytyczne obszary
- Obszary wymagające jawnej zgody
- Definition of Done

ETAP 6 — PROJEKTOWE SKILLS
Oceń, czy projekt wymaga własnych Skills w `.agents/skills/project/`. Twórz je tylko dla wiedzy specyficznej dla tego repozytorium.

ETAP 7 — KONFIGURACJA ai-team.config.json
Zachowaj domyślne reguły bezpieczeństwa:
- requireCleanWorkingTree: true
- createBranchForEachRun: true
- antigravity.sandbox: true
- antigravity.fullAuto: false
- Brak automatycznego push, merge i deployment.

ETAP 8 — WALIDACJA
Uruchom:
ai-team doctor .
ai-team status .
git status
git diff

Jeżeli istnieją bezpieczne, szybkie testy projektu, uruchom je w celu potwierdzenia komend z PROJECT_CONTEXT.md.

ETAP 9 — RAPORT KOŃCOWY
Przedstaw krótki raport końcowy:
- Wykryty stack i komponenty
- Wybrany profil i wersja
- Status doctor
- Zapisane komendy i ograniczenia bezpieczeństwa
- Utworzone Skills projektowe
- Lista zmienionych plików
- Zakończ jednoznacznym: `AI_TEAM_READY: YES` (lub `NO` z listą braków).
```

---

## Development

Clone the repository and install in editable mode with development dependencies:
```bash
git clone https://github.com/tomaasz/ai-engineering-team.git
cd ai-engineering-team
python -m pip install -e ".[dev]"
```

Run test suite:
```bash
pytest -v
```

Build package:
```bash
python -m build
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards, testing requirements, and the pull request process.

---

## License

This project is licensed under the [MIT License](LICENSE).
