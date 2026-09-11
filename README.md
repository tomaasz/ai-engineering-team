# AI Engineering Team v3

Prywatny, wieloplatformowy framework do instalowania zespołu agentów AI w dowolnym repozytorium.

```bash
ai-team install . --profile python
ai-team doctor .
ai-team run . "Dodaj import CSV wraz z testami"
ai-team update .
```

## Platformy
- Windows 11 / PowerShell / VS Code
- Linux / bash lub zsh / VS Code lub VS Code Remote SSH

## Role modeli
- Antigravity / Gemini — główny orkiestrator i wykonawca.
- Codex — domyślnie niezależny reviewer dla MEDIUM.
- Claude + Codex — niezależne review dla HIGH.

## Bezpieczeństwo
Każdy run pracuje na branchu `ai/...`. V3 nie wykonuje automatycznie `git push`, merge ani deployment.

## Prywatne repo
Po wrzuceniu tego katalogu do prywatnego GitHub repo instaluj menedżer przez `pipx`:

```bash
pipx install "git+ssh://git@github.com/OWNER/ai-engineering-team.git"
```

Następnie w dowolnym repo:

```bash
ai-team install . --profile core
```

Pełna instrukcja: `docs/INSTALL.md`.

---

# Bootstrap prompt for a project agent

Poniższe prompty służą do uruchomienia agenta już działającego **wewnątrz konkretnego projektu**. Agent ma przeanalizować repozytorium, dobrać profil AI Engineering Team, zainstalować lub zaktualizować framework oraz dostosować konfigurację do faktycznego stacku i workflow projektu.

## PL — prompt instalacyjno-konfiguracyjny

```text
Zainstaluj i skonfiguruj w tym repozytorium mój framework AI Engineering Team z prywatnego repozytorium:

https://github.com/tomaasz/ai-engineering-team

Twoim celem jest nie tylko zainstalowanie frameworka, ale przede wszystkim dopasowanie go do tego konkretnego projektu, tak aby później polecenie `ai-team run . "<prompt>"` mogło bezpiecznie analizować, implementować, testować i reviewować zmiany.

ZASADY

- Najpierw dokładnie przeanalizuj repozytorium.
- Nie zmieniaj kodu biznesowego aplikacji podczas tej konfiguracji.
- Nie wykonuj `git push`, merge, deployment, force push, `git reset --hard` ani `git clean`.
- Nie usuwaj istniejącej konfiguracji projektu.
- Jeżeli AI Engineering Team jest już zainstalowany, nie instaluj go ponownie w ciemno — sprawdź `ai-team status .` i w razie potrzeby użyj `ai-team update .`.
- Nie zgaduj komend testowych, buildów ani technologii. Ustal je z istniejących plików projektu.
- Zachowaj istniejące lokalne Skills i konfigurację AI, jeśli już istnieją.
- Jeżeli jakaś informacja jest niepewna, oznacz ją jako niezweryfikowaną zamiast wymyślać wartość.

ETAP 1 — ROZPOZNANIE PROJEKTU

Przeanalizuj repozytorium i ustal:

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

Sprawdź odpowiednio do projektu m.in.:

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

ETAP 2 — SPRAWDZENIE AI ENGINEERING TEAM

Sprawdź:

`ai-team --help`
`ai-team status .`

Jeżeli `ai-team` nie jest dostępny, spróbuj zainstalować go z prywatnego repozytorium:

`git+https://github.com/tomaasz/ai-engineering-team.git`

Preferuj `pipx`.

Jeżeli uwierzytelnienie do prywatnego GitHuba nie działa, nie próbuj obchodzić zabezpieczeń. Zatrzymaj ten etap i dokładnie podaj, czego brakuje.

ETAP 3 — DOBÓR PROFILU

Na podstawie rzeczywistej zawartości projektu wybierz najlepszy dostępny profil AI Engineering Team.

Dostępne profile mogą obejmować:

- `core`
- `python`
- `web`
- `postgres`
- `ocr`
- `geneteka`
- `full`

Nie wybieraj `full` automatycznie tylko dlatego, że zawiera najwięcej komponentów.

Wybierz najmniejszy profil, który sensownie pokrywa projekt.

Jeżeli projekt wymaga kompetencji z kilku profili, wybierz najbliższy profil bazowy, a brakujące kompetencje dodaj jako project-specific Skills zamiast instalować niepotrzebne elementy.

Napisz krótko, jaki profil wybierasz i dlaczego.

ETAP 4 — INSTALACJA LUB AKTUALIZACJA

Jeżeli framework nie jest zainstalowany:

`ai-team install . --profile <WYBRANY_PROFIL>`

Jeżeli jest już zainstalowany:

`ai-team update .`

Po operacji uruchom:

`ai-team status .`
`ai-team doctor .`

Nie ignoruj błędów `doctor`.

ETAP 5 — DOSTOSOWANIE PROJECT_CONTEXT.md

To najważniejsza część zadania.

Uzupełnij `PROJECT_CONTEXT.md` na podstawie faktycznej analizy repozytorium.

Powinien zawierać co najmniej:

### Cel projektu
Krótko i konkretnie opisz, do czego służy projekt.

### Stack
Wymień faktycznie używane języki, frameworki, runtime, bazę danych, narzędzia i ważne biblioteki.

### Główne komendy
Ustal rzeczywiste komendy:

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

Jeżeli dana kategoria nie występuje, wpisz `N/A`.
Nie wpisuj komendy, której nie potrafisz potwierdzić z repozytorium.

### Architektura
Krótko opisz:
- najważniejsze moduły,
- przepływ danych,
- główne entry points,
- istotne zależności pomiędzy komponentami.

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

### Obszary wymagające jawnej zgody
Wskaż operacje, których agent nie powinien wykonywać automatycznie, np.:
- usuwanie danych,
- zmiana produkcyjnej bazy,
- deployment,
- zmiana sekretów,
- force push,
- destructive migrations,
- modyfikacja infrastruktury.

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

ETAP 6 — PROJEKTOWE SKILLS

Oceń, czy projekt wymaga własnych Skills w:

`.agents/skills/project/`

Twórz je tylko wtedy, gdy dotyczą wiedzy charakterystycznej dla tego repo, której nie powinno się trzymać w ogólnym frameworku.

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

Nie kopiuj do project Skills ogólnych zasad Pythona, Git, PostgreSQL itd., jeśli framework już je posiada.

Każdy utworzony Skill powinien być krótki, konkretny i oparty na faktach z repozytorium.

ETAP 7 — KONFIGURACJA ai-team.config.json

Przejrzyj `ai-team.config.json`.

Dostosuj go tylko wtedy, gdy masz konkretny powód wynikający z projektu.

Domyślnie zachowaj model działania:

LOW → Gemini/Antigravity
MEDIUM → Gemini/Antigravity + Codex review
HIGH → Gemini/Antigravity + Claude review + Codex review

Nie włączaj automatycznie nieograniczonego `fullAuto`.

Nie włączaj automatycznego:
- push,
- merge,
- deployment.

ETAP 8 — WALIDACJA

Po zakończeniu konfiguracji uruchom ponownie:

`ai-team doctor .`
`ai-team status .`
`git status`
`git diff`

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

https://github.com/tomaasz/ai-engineering-team

Your goal is not only to install the framework, but to adapt it to this specific project so that later `ai-team run . "<prompt>"` can safely analyze, implement, test, and review changes.

RULES

- First, thoroughly inspect the repository.
- Do not modify application/business code during this setup task.
- Do not run `git push`, merge, deployment, force push, `git reset --hard`, or `git clean`.
- Do not delete existing project configuration.
- If AI Engineering Team is already installed, do not reinstall it blindly — check `ai-team status .` and use `ai-team update .` when appropriate.
- Do not guess test, build, or technology commands. Derive them from existing project files.
- Preserve existing local Skills and AI configuration if present.
- If any information is uncertain, mark it as unverified instead of inventing a value.

PHASE 1 — PROJECT DISCOVERY

Inspect the repository and determine:

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

`ai-team --help`
`ai-team status .`

If `ai-team` is unavailable, try to install it from the private repository:

`git+https://github.com/tomaasz/ai-engineering-team.git`

Prefer `pipx`.

If private GitHub authentication fails, do not bypass security controls. Stop this phase and report exactly what is missing.

PHASE 3 — SELECT A PROFILE

Based on the actual repository contents, choose the most appropriate available AI Engineering Team profile.

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

If the framework is not installed:

`ai-team install . --profile <SELECTED_PROFILE>`

If it is already installed:

`ai-team update .`

Then run:

`ai-team status .`
`ai-team doctor .`

Do not ignore `doctor` failures.

PHASE 5 — CUSTOMIZE PROJECT_CONTEXT.md

This is the most important part of the task.

Populate `PROJECT_CONTEXT.md` based on verified facts from the repository.

It should contain at least:

### Project purpose
Briefly describe what the project does.

### Stack
List the languages, frameworks, runtime, database, tools, and important libraries actually used.

### Main commands
Determine the real commands for:

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

If a category is not applicable, write `N/A`.
Do not record a command unless you can verify it from the repository.

### Architecture
Briefly describe:
- major modules,
- data flow,
- main entry points,
- important dependencies between components.

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

### Areas requiring explicit approval
List operations agents should not perform automatically, for example:
- deleting data,
- modifying a production database,
- deployment,
- changing secrets,
- force pushing,
- destructive migrations,
- infrastructure modifications.

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

PHASE 6 — PROJECT-SPECIFIC SKILLS

Determine whether this project needs its own Skills under:

`.agents/skills/project/`

Create them only for knowledge specific to this repository that should not live in the general framework.

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

Do not duplicate generic Python, Git, PostgreSQL, or similar guidance if the framework already provides it.

Each project Skill should be short, concrete, and based on verified repository facts.

PHASE 7 — REVIEW ai-team.config.json

Review `ai-team.config.json`.

Change it only when there is a concrete project-specific reason.

By default preserve this policy:

LOW → Gemini/Antigravity
MEDIUM → Gemini/Antigravity + Codex review
HIGH → Gemini/Antigravity + Claude review + Codex review

Do not enable unrestricted `fullAuto` automatically.

Do not enable automatic:
- push,
- merge,
- deployment.

PHASE 8 — VALIDATION

After configuration, run again:

`ai-team doctor .`
`ai-team status .`
`git status`
`git diff`

If safe and fast project tests exist, run them to verify that the commands recorded in `PROJECT_CONTEXT.md` are correct.

Do not run tests that:
- modify production data,
- deploy anything,
- use paid services unnecessarily,
- have destructive side effects.

PHASE 9 — FINAL REPORT

Provide a concise final report:

### Detected project
- stack
- main components

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
