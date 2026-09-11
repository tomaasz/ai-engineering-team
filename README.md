# AI Engineering Team v3
# AI Engineering Team

Prywatny, wieloplatformowy framework do instalowania zespołu agentów AI w dowolnym repozytorium.
[English](README.md) | [Polski](README.pl.md)

```bash
ai-team install . --profile python
ai-team doctor .
ai-team run . "Dodaj import CSV wraz z testami"
ai-team resume latest .  # safe validation; conservative retry semantics
ai-team update .
```
Cross-platform multi-agent software engineering orchestrator for Gemini / Google Antigravity, Codex and Claude Code.

## Platformy
- Windows 11 / PowerShell / VS Code
- Linux / bash lub zsh / VS Code lub VS Code Remote SSH
---

## Role modeli
- Antigravity / Gemini — główny orkiestrator i wykonawca.
- Codex — domyślnie niezależny reviewer dla MEDIUM.
- Claude + Codex — niezależne review dla HIGH.
## What It Is

## Durable runs and artifacts
Each run stores `run.json`, append-only `trace.jsonl`, and atomic `eval.json` under `.ai/runs/<run-id>/`. Prompts are represented only by a SHA-256 hash in the manifest; traces never contain prompts or environment values. `ai-team resume <run-id> .` (or `latest`) validates branch, base commit, and clean working tree before retrying. The first version intentionally refuses unsafe or unsupported automatic retries; successful stages are never repeated.

## Bezpieczeństwo
Każdy run pracuje na branchu `ai/...`. V3 nie wykonuje automatycznie `git push`, merge ani deployment. Subprocesses receive a sanitized environment and `AI_TEAM_SUBPROCESS=1`; configure only non-secret allowlisted names in code integrations. CWD must remain inside the repository boundary.
**AI Engineering Team** is a developer-focused multi-agent orchestration framework designed to embed an autonomous, role-specialized software engineering team directly into any existing git repository.

## Prywatne repo
Po wrzuceniu tego katalogu do prywatnego GitHub repo instaluj menedżer przez `pipx`:
Rather than relying on a single prompt or single model acting as an all-in-one assistant, AI Engineering Team coordinates specialized agent roles—Architect, Researcher, Implementer, Test Engineer, and Reviewer—combined with automated risk classification and **isolated multi-model cross-examination**.

```bash
pipx install "git+ssh://git@github.com/OWNER/ai-engineering-team.git"
```
## The Problem It Solves

Następnie w dowolnym repo:
- **Hallucinated verification**: Single agents frequently claim tests pass without executing them or fail to detect regressions in their own solutions.
- **Echo-chamber reviews**: Having the same model review its own generated code misses blind spots, security vulnerabilities, and subtle architectural degradations.
- **Repository pollution & high blast radius**: Uncontrolled AI agents can overwrite unstaged user work, modify configuration files without permission, force-push changes, or attempt uncontrolled production deployments.
- **Setup friction across platforms**: Setting up agent environments with system-specific tools often breaks when switching between Windows, Linux servers, or remote SSH workspaces.

```bash
ai-team install . --profile core
```
AI Engineering Team solves this by:
1. Enforcing strict git branch isolation (`ai/...`) and requiring clean working trees.
2. Routing tasks through an automated **Triage & Risk Gate** (LOW, MEDIUM, HIGH).
3. Utilizing **independent external models** (Claude Code and OpenAI Codex) to perform read-only reviews on non-trivial changes before code is approved.
4. Preserving user-customized files through state tracking and automatic conflict detection during framework updates.

Pełna instrukcja: `docs/INSTALL.md`.

---

# Bootstrap prompt for a project agent
## Architecture

Poniższe prompty służą do uruchomienia agenta już działającego **wewnątrz konkretnego projektu**. Agent ma przeanalizować repozytorium, dobrać profil AI Engineering Team, zainstalować lub zaktualizować framework oraz dostosować konfigurację do faktycznego stacku i workflow projektu.
### Orchestration Pipeline

## PL — prompt instalacyjno-konfiguracyjny

```text
Zainstaluj i skonfiguruj w tym repozytorium mój framework AI Engineering Team z prywatnego repozytorium:
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

https://github.com/tomaasz/ai-engineering-team
### Model Roles

Twoim celem jest nie tylko zainstalowanie frameworka, ale przede wszystkim dopasowanie go do tego konkretnego projektu, tak aby później polecenie `ai-team run . "<prompt>"` mogło bezpiecznie analizować, implementować, testować i reviewować zmiany.
| Model / CLI | Primary Role | Execution Characteristics |
| ----------- | ------------ | ------------------------- |
| **Google Antigravity / Gemini (`agy`)** | Core Team & Orchestration | Acts as the primary implementation engine: Architect, Researcher, Implementer, Test Engineer, and Integrator. Runs in sandboxed execution mode. |
| **OpenAI Codex (`codex`)** | Independent Reviewer (MEDIUM & HIGH) | Operates in an ephemeral, read-only inspection mode. Evaluates correctness, potential edge-case failures, and regressions without seeing prior reviews. |
| **Anthropic Claude Code (`claude`)** | Independent Reviewer (HIGH) | Operates in strict plan/read-only mode for mission-critical tasks (security, schema migrations, auth). Delivers evidentiary audit reports without modifying files. |

ZASADY
### Why Independent Multi-Model Review?

- Najpierw dokładnie przeanalizuj repozytorium.
- Nie zmieniaj kodu biznesowego aplikacji podczas tej konfiguracji.
- Nie wykonuj `git push`, merge, deployment, force push, `git reset --hard` ani `git clean`.
- Nie usuwaj istniejącej konfiguracji projektu.
- Jeżeli AI Engineering Team jest już zainstalowany, nie instaluj go ponownie w ciemno — sprawdź `ai-team status .` i w razie potrzeby użyj `ai-team update .`.
- Nie zgaduj komend testowych, buildów ani technologii. Ustal je z istniejących plików projektu.
- Zachowaj istniejące lokalne Skills i konfigurację AI, jeśli już istnieją.
- Jeżeli jakaś informacja jest niepewna, oznacz ją jako niezweryfikowaną zamiast wymyślać wartość.
Model architectures have distinct biases, training cutoffs, and blind spots. When a primary agent implements a complex refactor, it often rationalizes its own design errors during self-review. Introducing Codex and Claude as independent reviewers creates an adversarial verification layer. Reviewers do not see each other's assessments in advance, ensuring truly independent analysis. The Integrator then examines all findings against empirical evidence in the codebase.

ETAP 1 — ROZPOZNANIE PROJEKTU
### Risk Classification

Przeanalizuj repozytorium i ustal:
- **LOW**: Minor, easily reversible modifications (e.g., typos, localized helper functions, formatting). Handled entirely by the primary Gemini/Antigravity team without external review overhead.
- **MEDIUM**: Multi-file changes, new features, public API modifications, or significant refactoring. Automatically triggers independent cross-review by Codex.
- **HIGH**: Sensitive domains including authentication, authorization, cryptography, secrets, database schema migrations, infrastructure, or high-blast-radius business logic. Requires dual independent review by both Claude Code and Codex.

1. system operacyjny i środowisko, w którym aktualnie pracujesz;
2. języki programowania;
3. frameworki;
4. package manager;
5. strukturę projektu;
6. sposób instalowania zależności;
7. sposób uruchamiania aplikacji;
8. istniejące testy;
9. linting;
10. type checking;
11. build;
12. bazę danych;
13. Docker / Docker Compose;
14. CI/CD;
15. automatyzację przeglądarki, jeśli występuje;
16. migracje bazy danych;
17. istotne pliki konfiguracyjne;
18. katalogi wygenerowane, cache i build output;
19. obszary szczególnie ryzykowne;
20. części projektu, których agent nie powinien modyfikować bez wyraźnej zgody.
---

Sprawdź odpowiednio do projektu m.in.:
## Features

- `pyproject.toml`
- `requirements*.txt`
- `uv.lock`
- `poetry.lock`
- `package.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `package-lock.json`
- `Dockerfile`
- `docker-compose*.yml`
- `Makefile`
- `Taskfile.yml`
- `.github/workflows/`
- `pytest.ini`
- `tox.ini`
- `ruff.toml`
- `mypy.ini`
- `tsconfig.json`
- konfigurację ESLint
- konfigurację Playwright/Cypress
- pliki migracji
- README
- istniejące pliki `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.agents/`, `.claude/`.
- **Multi-Agent Specialization**: Distinct agent personas for architecture, research, coding, testing, integration, and verification.
- **Deterministic State Tracking**: Tracks file hashes in `.ai-team/state.json`. Updates never overwrite locally modified managed files; conflicts are diverted to `.ai-team/conflicts/`.
- **Project-Specific Knowledge Retention**: Keeps `PROJECT_CONTEXT.md`, `ai-team.config.json`, and `.agents/skills/project/` strictly intact across updates.
- **Full Cross-Platform Support**: Built natively for Windows 11 (PowerShell) and Linux (bash/zsh), with first-class support for VS Code Remote SSH development.
- **VS Code Integration**: Automatically generates and merges non-destructive `.vscode/tasks.json` tasks for prompt execution, health checks, and updates.
- **Strict Safety Boundaries**: Zero auto-push, zero auto-merge, zero auto-deployment. All agent modifications occur on designated run branches.

ETAP 2 — SPRAWDZENIE AI ENGINEERING TEAM
---

Sprawdź:
## Requirements

`ai-team --help`
`ai-team status .`
- **Python**: 3.10 or higher
- **Git**: Installed and available in `$PATH`
- **CLI Agents**:
  - `agy` (Google Antigravity CLI) — **Required** (primary executor)
  - `codex` (OpenAI Codex CLI) — Optional (recommended for MEDIUM/HIGH review)
  - `claude` (Anthropic Claude Code CLI) — Optional (recommended for HIGH review)

Jeżeli `ai-team` nie jest dostępny, spróbuj zainstalować go z prywatnego repozytorium:
> [!NOTE]
> Authenticate `agy`, `claude`, and `codex` interactively in your terminal at least once before invoking unattended runs.

`git+https://github.com/tomaasz/ai-engineering-team.git`
---

Preferuj `pipx`.
## Installation

Jeżeli uwierzytelnienie do prywatnego GitHuba nie działa, nie próbuj obchodzić zabezpieczeń. Zatrzymaj ten etap i dokładnie podaj, czego brakuje.
The recommended installation method across all platforms is via [`pipx`](https://pypa.github.io/pipx/):

ETAP 3 — DOBÓR PROFILU
```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"
```

Na podstawie rzeczywistej zawartości projektu wybierz najlepszy dostępny profil AI Engineering Team.
### Installing a Specific Version

Dostępne profile mogą obejmować:
```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v3.0.1"
```

- `core`
- `python`
- `web`
- `postgres`
- `ocr`
- `geneteka`
- `full`
### Upgrading

Nie wybieraj `full` automatycznie tylko dlatego, że zawiera najwięcej komponentów.
```bash
pipx upgrade ai-engineering-team
```

Wybierz najmniejszy profil, który sensownie pokrywa projekt.
### Developer Installation via SSH (Optional)

Jeżeli projekt wymaga kompetencji z kilku profili, wybierz najbliższy profil bazowy, a brakujące kompetencje dodaj jako project-specific Skills zamiast instalować niepotrzebne elementy.
```bash
pipx install "git+ssh://git@github.com/tomaasz/ai-engineering-team.git"
```

Napisz krótko, jaki profil wybierasz i dlaczego.
### Local Repository Installation

ETAP 4 — INSTALACJA LUB AKTUALIZACJA
**Windows (PowerShell):**
```powershell
.\install-local.ps1
```

Jeżeli framework nie jest zainstalowany:
**Linux (Bash):**
```bash
./install-local.sh
```

`ai-team install . --profile <WYBRANY_PROFIL>`
---

Jeżeli jest już zainstalowany:
## Quick Start

`ai-team update .`
1. Navigate to your target repository:
   ```bash
   cd /path/to/your-project
   ```

Po operacji uruchom:
2. Install AI Engineering Team with a selected profile:
   ```bash
   ai-team install . --profile python
   ```

`ai-team status .`
`ai-team doctor .`
3. Validate your environment:
   ```bash
   ai-team doctor .
   ```

Nie ignoruj błędów `doctor`.
4. Execute a task:
   ```bash
   ai-team run . "Add CSV export endpoint with comprehensive unit tests"
   ```

ETAP 5 — DOSTOSOWANIE PROJECT_CONTEXT.md
5. Check the generated branch and verification logs:
   ```bash
   git status
   git diff main
   cat .ai/runs/<run-id>/final-verification.md
   ```

To najważniejsza część zadania.
---

Uzupełnij `PROJECT_CONTEXT.md` na podstawie faktycznej analizy repozytorium.
## Profiles

Powinien zawierać co najmniej:
Profiles determine which skill modules and configuration templates are installed into the repository:

### Cel projektu
Krótko i konkretnie opisz, do czego służy projekt.
| Profile | Target Stack / Purpose | Key Components Included |
| ------- | ---------------------- | ----------------------- |
| `core` | Universal baseline | Basic agents, core code review, task planning, testing skills. |
| `python` | Python applications | Core skills + Python quality, typing, pytest standards. |
| `web` | Web & frontend apps | Core skills + browser automation, DOM inspection, frontend testing. |
| `postgres` | Database-heavy projects | Core skills + PostgreSQL safety, schema migrations, lock prevention. |
| `ocr` | Document processing | Core skills + OCR pipeline, document layout parsing, text extraction. |
| `geneteka` | Genealogical records | Core skills + specialized ETL pipeline for genealogical datasets. |
| `full` | Multi-disciplinary systems | All available skills and agent roles across all profiles. |

### Stack
Wymień faktycznie używane języki, frameworki, runtime, bazę danych, narzędzia i ważne biblioteki.
---

### Główne komendy
Ustal rzeczywiste komendy:
## VS Code

- install
- dev
- run
- lint
- format
- typecheck
- unit tests
- integration tests
- e2e tests
- build
- database migrations
- docker start
- docker stop
During installation, `ai-team` inspects `.vscode/tasks.json`. If one exists, it cleanly merges the AI Team tasks without altering or duplicating your custom tasks.

Jeżeli dana kategoria nie występuje, wpisz `N/A`.
Nie wpisuj komendy, której nie potrafisz potwierdzić z repozytorium.
### Available Tasks:
- **`AI Team: Run prompt`**: Opens an interactive input box in VS Code asking for your prompt, then executes `ai-team run`.
- **`AI Team: Doctor`**: Runs environment verification and outputs diagnostics directly into the VS Code terminal.
- **`AI Team: Update`**: Synchronizes framework templates and skills with the installed version.

### Architektura
Krótko opisz:
- najważniejsze moduły,
- przepływ danych,
- główne entry points,
- istotne zależności pomiędzy komponentami.
Run via: `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS) → `Tasks: Run Task` → Select task.

### Krytyczne obszary
Wskaż m.in.:
- dane użytkownika,
- migracje,
- auth,
- uprawnienia,
- schemat bazy,
- integracje zewnętrzne,
- scraping,
- filesystem,
- deployment,
- miejsca podatne na utratę danych.
---

### Obszary wymagające jawnej zgody
Wskaż operacje, których agent nie powinien wykonywać automatycznie, np.:
- usuwanie danych,
- zmiana produkcyjnej bazy,
- deployment,
- zmiana sekretów,
- force push,
- destructive migrations,
- modyfikacja infrastruktury.
## Windows

### Definition of Done
Dostosuj do projektu. Minimum:
- kod przechodzi lint;
- type checking przechodzi, jeśli jest używany;
- testy jednostkowe przechodzą;
- odpowiednie testy integracyjne przechodzą;
- build przechodzi, jeśli występuje;
- brak niezamierzonych zmian w diff;
- migracja posiada rollback, jeśli dotyczy;
- zmiana MEDIUM/HIGH przechodzi niezależny review.
- Fully supported under Windows 10/11 using PowerShell 7 or Windows PowerShell 5.1.
- Ensure Python and Git are present in your system `PATH`.
- Path handling is entirely cross-platform and handles Windows backslashes transparently.

ETAP 6 — PROJEKTOWE SKILLS
## Linux

Oceń, czy projekt wymaga własnych Skills w:
- Fully supported on Ubuntu, Debian, Fedora, Arch, and Alpine.
- Works in both `bash` and `zsh` interactive environments.

`.agents/skills/project/`
## VS Code Remote SSH

Twórz je tylko wtedy, gdy dotyczą wiedzy charakterystycznej dla tego repo, której nie powinno się trzymać w ogólnym frameworku.
When developing on a remote VPS or container using VS Code Remote SSH:
- Install `ai-team` and the required agent CLIs (`agy`, `claude`, `codex`) **on the remote machine**.
- VS Code tasks execute within the remote host environment, ensuring full access to remote project files, containers, and development services.

Przykłady:
- specyficzny model danych;
- zasady konkretnego API;
- format importowanych plików;
- konwencje projektu;
- nietypowy pipeline ETL;
- zasady parsera;
- struktura danych domenowych;
- sposób wykonywania migracji;
- specyficzne wymagania testowe.
---

Nie kopiuj do project Skills ogólnych zasad Pythona, Git, PostgreSQL itd., jeśli framework już je posiada.
## Updating

Każdy utworzony Skill powinien być krótki, konkretny i oparty na faktach z repozytorium.
To update the framework templates within a project:
```bash
cd /path/to/project
ai-team update .
```

ETAP 7 — KONFIGURACJA ai-team.config.json
- **Protected User Files**: `PROJECT_CONTEXT.md`, `ai-team.config.json`, and `.agents/skills/project/` are never overwritten.
- **Conflict Handling**: If you modified a managed template file locally, `ai-team update` retains your local version and saves the latest upstream template to `.ai-team/conflicts/<path>`, preventing accidental overwrites.

Przejrzyj `ai-team.config.json`.
---

Dostosuj go tylko wtedy, gdy masz konkretny powód wynikający z projektu.
## Security Model

Domyślnie zachowaj model działania:
> [!WARNING]
> **Local Code Execution**: AI Engineering Team invokes AI models that can generate and run arbitrary shell commands, install dependencies, and modify files on your local machine.

LOW → Gemini/Antigravity
MEDIUM → Gemini/Antigravity + Codex review
HIGH → Gemini/Antigravity + Claude review + Codex review
To protect your system and repositories, AI Engineering Team enforces these core security constraints:
1. **No Automatic Push or Merge**: `ai-team` **never** performs `git push` or merges code into upstream branches.
2. **No Automatic Deployment**: The runner never triggers deployment commands or infrastructure provisioning.
3. **Isolated Run Branches**: All primary modifications take place on dedicated branches prefixed with `ai/`.
4. **Sandboxing Enabled by Default**: Antigravity is configured with `"sandbox": true`.
5. **Full Auto Disabled by Default**: `"fullAuto": false` prevents dangerous permission skipping (`--dangerously-skip-permissions`). Never enable full auto unless operating inside an isolated disposable container.
6. **Read-Only External Reviewers**: Independent review agents (`claude`, `codex`) are invoked with strict read-only / plan-only constraints and cannot mutate files.

Nie włączaj automatycznie nieograniczonego `fullAuto`.
Review [SECURITY.md](SECURITY.md) for full vulnerability reporting guidelines.

Nie włączaj automatycznego:
- push,
- merge,
- deployment.
---

ETAP 8 — WALIDACJA
## Project Bootstrap

Po zakończeniu konfiguracji uruchom ponownie:
When you want an AI agent to onboard and configure AI Engineering Team in a new or existing repository, copy and paste one of the bootstrap prompts below into your agent's chat interface.

`ai-team doctor .`
`ai-team status .`
`git status`
`git diff`
### English Bootstrap Prompt

Jeżeli istnieją bezpieczne, szybkie testy projektu, uruchom je również, żeby potwierdzić poprawność komend zapisanych w `PROJECT_CONTEXT.md`.

Nie uruchamiaj testów, które:
- zmieniają dane produkcyjne,
- wykonują deployment,
- korzystają z płatnych usług bez potrzeby,
- mają destrukcyjne skutki.

ETAP 9 — RAPORT KOŃCOWY

Na końcu przedstaw krótki raport:

### Wykryty projekt
- stack
- główne komponenty

### AI Engineering Team
- wersja
- profil
- status `doctor`

### Dostosowana konfiguracja
- jakie komendy zostały wykryte
- jakie krytyczne obszary zostały zapisane
- jakie ograniczenia bezpieczeństwa ustawiono

### Skills
- jakie project-specific Skills utworzono
- dlaczego

### Zmienione pliki
Podaj wszystkie zmienione lub utworzone pliki.

### Problemy / TODO
Wymień rzeczy, których nie udało się pewnie ustalić.

### Gotowość
Na końcu określ wyłącznie technicznie:

`AI_TEAM_READY: YES`

jeżeli `ai-team doctor .` nie zgłasza blokujących problemów i konfiguracja projektu jest kompletna.

W przeciwnym razie:

`AI_TEAM_READY: NO`

i podaj konkretne brakujące elementy.

Nie commituj ani nie pushuj zmian bez mojego wyraźnego polecenia.
```

## EN — installation and configuration prompt

```text
Install and configure my AI Engineering Team framework in this repository from the private repository:
Install and configure the AI Engineering Team framework in this repository from the public repository:

https://github.com/tomaasz/ai-engineering-team

Your goal is not only to install the framework, but to adapt it to this specific project so that later `ai-team run . "<prompt>"` can safely analyze, implement, test, and review changes.

RULES

RULES:
- First, thoroughly inspect the repository.
- Do not modify application/business code during this setup task.
- Do not run `git push`, merge, deployment, force push, `git reset --hard`, or `git clean`.
- Do not modify application or business logic code during this setup task.
- Do not run git push, merge, deployment, force push, git reset --hard, or git clean.
- Do not delete existing project configuration.
- If AI Engineering Team is already installed, do not reinstall it blindly — check `ai-team status .` and use `ai-team update .` when appropriate.
- Do not guess test, build, or technology commands. Derive them from existing project files.
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

1. operating system and environment you are currently running in;
2. programming languages;
3. frameworks;
4. package manager;
5. project structure;
6. dependency installation workflow;
7. application startup workflow;
8. existing tests;
9. linting;
10. type checking;
11. build process;
12. database;
13. Docker / Docker Compose;
14. CI/CD;
15. browser automation, if present;
16. database migrations;
17. important configuration files;
18. generated directories, cache, and build output;
19. especially risky areas;
20. parts of the project that agents should not modify without explicit approval.

Inspect, where relevant:

- `pyproject.toml`
- `requirements*.txt`
- `uv.lock`
- `poetry.lock`
- `package.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `package-lock.json`
- `Dockerfile`
- `docker-compose*.yml`
- `Makefile`
- `Taskfile.yml`
- `.github/workflows/`
- `pytest.ini`
- `tox.ini`
- `ruff.toml`
- `mypy.ini`
- `tsconfig.json`
- ESLint configuration
- Playwright/Cypress configuration
- migration files
- README
- existing `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.agents/`, and `.claude/` files/directories.

PHASE 2 — CHECK AI ENGINEERING TEAM

Run:
ai-team --help
ai-team status .

`ai-team --help`
`ai-team status .`
If `ai-team` is unavailable, install it:
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"

If `ai-team` is unavailable, try to install it from the private repository:

`git+https://github.com/tomaasz/ai-engineering-team.git`

Prefer `pipx`.

If private GitHub authentication fails, do not bypass security controls. Stop this phase and report exactly what is missing.

PHASE 3 — SELECT A PROFILE
Based on the actual repository contents, choose the most appropriate available AI Engineering Team profile:
- core
- python
- web
- postgres
- ocr
- geneteka
- full

Based on the actual repository contents, choose the most appropriate available AI Engineering Team profile.
Choose the smallest profile that sensibly covers the project. If capabilities from multiple domains are needed, choose the closest base profile and add missing capabilities as project-specific Skills rather than installing unnecessary components.

Available profiles may include:

- `core`
- `python`
- `web`
- `postgres`
- `ocr`
- `geneteka`
- `full`

Do not automatically choose `full` just because it contains the most components.

Choose the smallest profile that sensibly covers the project.

If the project needs capabilities from multiple profiles, choose the closest base profile and add missing capabilities as project-specific Skills rather than installing unnecessary components.

Briefly state which profile you selected and why.

PHASE 4 — INSTALL OR UPDATE
If not installed:
ai-team install . --profile <SELECTED_PROFILE>

If the framework is not installed:
If already installed:
ai-team update .

`ai-team install . --profile <SELECTED_PROFILE>`

If it is already installed:

`ai-team update .`

Then run:
ai-team status .
ai-team doctor .

`ai-team status .`
`ai-team doctor .`

Do not ignore `doctor` failures.

PHASE 5 — CUSTOMIZE PROJECT_CONTEXT.md
Populate `PROJECT_CONTEXT.md` based on verified facts from the repository:
- Project Purpose
- Tech Stack
- Main Verified Commands (install, dev, run, lint, format, typecheck, unit tests, integration tests, build, migrations)
- Architecture Overview
- Critical Areas & Failure Points
- Areas Requiring Explicit Approval
- Definition of Done

This is the most important part of the task.
PHASE 6 — PROJECT-SPECIFIC SKILLS
Determine whether this project needs repository-specific Skills under:
.agents/skills/project/
Create them only for knowledge unique to this repository. Do not duplicate generic language rules already provided by standard profiles.

Populate `PROJECT_CONTEXT.md` based on verified facts from the repository.
PHASE 7 — REVIEW ai-team.config.json
Ensure default safety policies remain active:
- requireCleanWorkingTree: true
- createBranchForEachRun: true
- antigravity.sandbox: true
- antigravity.fullAuto: false
- No automatic push, merge, or deployment.

It should contain at least:
PHASE 8 — VALIDATION
Run:
ai-team doctor .
ai-team status .
git status
git diff

### Project purpose
Briefly describe what the project does.
If safe and fast tests exist, run them to verify the commands recorded in PROJECT_CONTEXT.md.

### Stack
List the languages, frameworks, runtime, database, tools, and important libraries actually used.
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

### Main commands
Determine the real commands for:
### Polish Bootstrap Prompt

- install
- dev
- run
- lint
- format
- typecheck
- unit tests
- integration tests
- e2e tests
- build
- database migrations
- docker start
- docker stop
```text
Zainstaluj i skonfiguruj w tym repozytorium framework AI Engineering Team z publicznego repozytorium:

If a category is not applicable, write `N/A`.
Do not record a command unless you can verify it from the repository.
https://github.com/tomaasz/ai-engineering-team

### Architecture
Briefly describe:
- major modules,
- data flow,
- main entry points,
- important dependencies between components.
Twoim celem jest nie tylko zainstalowanie frameworka, ale przede wszystkim dopasowanie go do tego konkretnego projektu, tak aby później polecenie `ai-team run . "<prompt>"` mogło bezpiecznie analizować, implementować, testować i reviewować zmiany.

### Critical areas
Identify, where applicable:
- user data,
- migrations,
- authentication,
- authorization,
- database schema,
- external integrations,
- scraping,
- filesystem operations,
- deployment,
- areas where data loss is possible.
ZASADY:
- Najpierw dokładnie przeanalizuj repozytorium.
- Nie zmieniaj kodu biznesowego aplikacji podczas tej konfiguracji.
- Nie wykonuj git push, merge, deployment, force push, git reset --hard ani git clean.
- Nie usuwaj istniejącej konfiguracji projektu.
- Jeżeli AI Engineering Team jest już zainstalowany, nie instaluj go ponownie w ciemno — sprawdź `ai-team status .` i w razie potrzeby użyj `ai-team update .`.
- Nie zgaduj komend testowych, buildów ani technologii. Ustal je z istniejących plików projektu.
- Zachowaj istniejące lokalne Skills i konfigurację AI, jeśli już istnieją.
- Jeżeli jakaś informacja jest niepewna, oznacz ją jako niezweryfikowaną zamiast wymyślać wartość.

### Areas requiring explicit approval
List operations agents should not perform automatically, for example:
- deleting data,
- modifying a production database,
- deployment,
- changing secrets,
- force pushing,
- destructive migrations,
- infrastructure modifications.
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

### Definition of Done
Adapt it to the project. At minimum:
- lint passes;
- type checking passes if used;
- unit tests pass;
- relevant integration tests pass;
- build passes if applicable;
- no unintended changes in the diff;
- migrations have a rollback strategy when relevant;
- MEDIUM/HIGH changes receive independent review.
ETAP 2 — SPRAWDZENIE AI ENGINEERING TEAM
Sprawdź:
ai-team --help
ai-team status .

PHASE 6 — PROJECT-SPECIFIC SKILLS
Jeżeli `ai-team` nie jest dostępny, zainstaluj go:
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"

Determine whether this project needs its own Skills under:
ETAP 3 — DOBÓR PROFILU
Wybierz optymalny profil AI Engineering Team dla projektu:
- core
- python
- web
- postgres
- ocr
- geneteka
- full

`.agents/skills/project/`
Wybierz najmniejszy profil, który sensownie pokrywa projekt. Brakujące specyficzne kompetencje dodaj jako project-specific Skills zamiast instalować niepotrzebne komponenty.

Create them only for knowledge specific to this repository that should not live in the general framework.
ETAP 4 — INSTALACJA LUB AKTUALIZACJA
Jeżeli framework nie jest zainstalowany:
ai-team install . --profile <WYBRANY_PROFIL>

Examples:
- project-specific data model;
- rules for a particular API;
- imported file formats;
- repository conventions;
- unusual ETL pipeline;
- parser rules;
- domain data structure;
- project-specific migration workflow;
- special testing requirements.
Jeżeli jest już zainstalowany:
ai-team update .

Do not duplicate generic Python, Git, PostgreSQL, or similar guidance if the framework already provides it.
Następnie sprawdź:
ai-team status .
ai-team doctor .

Each project Skill should be short, concrete, and based on verified repository facts.
ETAP 5 — DOSTOSOWANIE PROJECT_CONTEXT.md
Uzupełnij `PROJECT_CONTEXT.md` na podstawie faktycznej analizy repozytorium:
- Cel projektu
- Stack technologiczny
- Rzeczywiste, zweryfikowane komendy (install, dev, run, lint, format, typecheck, testy, build, migracje)
- Architektura
- Krytyczne obszary
- Obszary wymagające jawnej zgody
- Definition of Done

PHASE 7 — REVIEW ai-team.config.json
ETAP 6 — PROJEKTOWE SKILLS
Oceń, czy projekt wymaga własnych Skills w `.agents/skills/project/`. Twórz je tylko dla wiedzy specyficznej dla tego repozytorium.

Review `ai-team.config.json`.
ETAP 7 — KONFIGURACJA ai-team.config.json
Zachowaj domyślne reguły bezpieczeństwa:
- requireCleanWorkingTree: true
- createBranchForEachRun: true
- antigravity.sandbox: true
- antigravity.fullAuto: false
- Brak automatycznego push, merge i deployment.

Change it only when there is a concrete project-specific reason.
ETAP 8 — WALIDACJA
Uruchom:
ai-team doctor .
ai-team status .
git status
git diff

By default preserve this policy:
Jeżeli istnieją bezpieczne, szybkie testy projektu, uruchom je w celu potwierdzenia komend z PROJECT_CONTEXT.md.

LOW → Gemini/Antigravity
MEDIUM → Gemini/Antigravity + Codex review
HIGH → Gemini/Antigravity + Claude review + Codex review
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

Do not enable unrestricted `fullAuto` automatically.
---

Do not enable automatic:
- push,
- merge,
- deployment.
## Development

PHASE 8 — VALIDATION
Clone and install in editable mode:
```bash
git clone https://github.com/tomaasz/ai-engineering-team.git
cd ai-engineering-team
python -m pip install -e ".[dev]"
```

After configuration, run again:
Run test suite:
```bash
pytest -v
```

`ai-team doctor .`
`ai-team status .`
`git status`
`git diff`
Build package distributions:
```bash
python -m build
```

If safe and fast project tests exist, run them to verify that the commands recorded in `PROJECT_CONTEXT.md` are correct.
---

Do not run tests that:
- modify production data,
- deploy anything,
- use paid services unnecessarily,
- have destructive side effects.
## Contributing

PHASE 9 — FINAL REPORT
Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, testing requirements, and the pull request submission process.

Provide a concise final report:
---

### Detected project
- stack
- main components
## License

### AI Engineering Team
- version
- selected profile
- `doctor` status

### Customized configuration
- detected commands
- critical areas recorded
- safety restrictions configured

### Skills
- project-specific Skills created
- why they were created

### Changed files
List every file created or modified.

### Problems / TODO
List anything that could not be determined confidently.

### Readiness
End with exactly:

`AI_TEAM_READY: YES`

if `ai-team doctor .` reports no blocking problems and the project configuration is complete.

Otherwise use:

`AI_TEAM_READY: NO`

and list the specific missing items.

Do not commit or push any changes unless I explicitly instruct you to do so.
```
This project is licensed under the [MIT License](LICENSE).
