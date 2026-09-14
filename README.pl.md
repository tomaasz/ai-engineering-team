# AI Engineering Team

[English](README.md) | [Polski](README.pl.md)

[![CI](https://github.com/tomaasz/ai-engineering-team/actions/workflows/ci.yml/badge.svg)](https://github.com/tomaasz/ai-engineering-team/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/tomaasz/ai-engineering-team?include_prereleases)](https://github.com/tomaasz/ai-engineering-team/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Wieloplatformowy orkiestrator zespołu inżynierii oprogramowania multi-agent dla Gemini / Google Antigravity, Codex i Claude Code.

---

## Czym jest projekt

**AI Engineering Team** to framework orkiestracji wieloagentowej dla programistów, zaprojektowany w celu osadzenia autonomicznego, wyspecjalizowanego w rolach zespołu inżynierii oprogramowania bezpośrednio w dowolnym repozytorium Git.

Zamiast polegać na pojedynczym prompcie lub jednym modelu działającym jako asystent do wszystkiego, AI Engineering Team koordynuje wyspecjalizowane role agentów — Architekta, Badacza (Researcher), Implementera, Inżyniera Testów (Test Engineer) oraz Recenzenta (Reviewer) — w połączeniu z automatyczną klasyfikacją ryzyka i **niezależną weryfikacją krzyżową przez odrębne modele**.

## Jaki problem rozwiązuje

- **Halucynacje weryfikacyjne**: Pojedyncze agenty często twierdzą, że testy przeszły pomyślnie bez ich faktycznego uruchomienia, lub nie dostrzegają regresji we własnych rozwiązaniach.
- **Efekt bańki poznawczej (echo-chamber)**: Model dokonujący przeglądu własnego kodu powiela swoje pierwotne założenia, pomijając luki w bezpieczeństwie i degradację architektury.
- **Zanieczyszczenie repozytorium i wysokie ryzyko awarii**: Niekontrolowane agenty mogą nadpisywać niescommitowaną pracę użytkownika, zmieniać pliki konfiguracyjne, wymuszać push (force-push) lub inicjować niekontrolowane wdrożenia produkcyjne.
- **Problemy z wieloplatformowością**: Konfiguracje agentów oparte na skryptach systemowych często zawodzą przy przełączaniu się między Windowsem, serwerami Linux a sesjami Remote SSH.

AI Engineering Team rozwiązuje te problemy poprzez:
1. Wymuszoną izolację na dedykowanych branchach Git (`ai/...`) i wymóg czystego working tree.
2. Kierowanie zadań przez zautomatyzowaną **bramkę oceny ryzyka (Triage & Risk Gate)**: LOW, MEDIUM, HIGH.
3. Wykorzystanie **zewnętrznych, niezależnych modeli** (Claude Code i OpenAI Codex) do przeprowadzania audytów w trybie tylko do odczytu przed zatwierdzeniem kodu.
4. Ochronę plików dostosowanych przez użytkownika dzięki śledzeniu sum kontrolnych i automatycznemu wykrywaniu konfliktów podczas aktualizacji frameworka.

---

## Architektura

### Przepływ orkiestracji (Pipeline)

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

### Role modeli

| Model / CLI | Główna rola | Charakterystyka wykonania |
| ----------- | ----------- | ------------------------- |
| **Google Antigravity / Gemini (`agy`)** | Zespół główny i orkiestracja | Główny silnik implementacyjny: Architekt, Badacz, Implementer, Inżynier Testów oraz Integrator. Działa w bezpiecznym sandboxie. |
| **OpenAI Codex (`codex`)** | Niezależny recenzent (MEDIUM & HIGH) | Działa w efemerycznym trybie inspekcji tylko do odczytu. Analizuje poprawność, przypadki brzegowe i regresje bez wglądu w inne recenzje. |
| **Anthropic Claude Code (`claude`)** | Niezależny recenzent (HIGH) | Działa w rygorystycznym trybie plan/read-only przy zadaniach krytycznych (bezpieczeństwo, migracje bazy, auth). Generuje raporty dowodowe bez modyfikowania plików. |

### Dlaczego niezależny review przez różne modele?

Różne architektury modeli posiadają odmienne ograniczenia, specyfikę danych treningowych i martwe pola. Gdy model implementuje złożony refaktor, podczas autorecenzji ma tendencję do racjonalizowania własnych błędów. Wprowadzenie modeli Codex i Claude jako niezależnych recenzentów tworzy weryfikację kontradyktoryjną (adversarial verification). Recenzenci nie widzą wzajemnie swoich raportów, co gwarantuje w pełni autonomiczną ocenę. Następnie Integrator weryfikuje każdy zarzut bezpośrednio w kodzie.

### Klasyfikacja ryzyka

- **LOW**: Drobne, w pełni odwracalne zmiany (np. poprawki literówek, lokalne funkcje pomocnicze, formatowanie). Realizowane w całości przez główny zespół Gemini/Antigravity bez narzutu zewnętrznych recenzji.
- **MEDIUM**: Zmiany wieloplikowe, nowe funkcje, zmiany publicznego API lub istotny refaktoring. Automatycznie uruchamia niezależny review przez Codex.
- **HIGH**: Zmiany w obszarach krytycznych: uwierzytelnianie, autoryzacja, kryptografia, zarządzanie sekretami, migracje schematu baz danych, infrastruktura lub kluczowa logika biznesowa. Wymaga podwójnego, niezależnego przeglądu przez Claude Code i Codex.

---

## Funkcje (Features)

- **Specjalizacja ról**: Dedykowane persony agentów dla architektury, researchu, implementacji, testów, integracji i końcowej weryfikacji.
- **Izolacja Git Worktree**: Wykonywanie zadań w odizolowanym drzewie roboczym (`--worktree`) bez przełączania gałęzi użytkownika i bez przerywania lokalnej pracy w edytorze.
- **Interaktywne CLI recenzji**: Narzędzie `ai-team review` umożliwia podgląd werdyktów, diffa zmian (`--diff`), czyste scalenie (`--merge`) lub odrzucenie (`--discard`) gałęzi przebiegu.
- **Mapa repozytorium AST**: Wbudowane, wolne od zewnętrznych zależności mapowanie struktury klas i funkcji repozytorium zapewnia agentom orientację w architekturze projektu bez marnowania tokenów.
- **Żywa pamięć zespołu**: Wnioski, nierozwiązane uwagi i notatki z weryfikacji są automatycznie zapisywane w `.ai/LEARNINGS.md` i przekazywane do kolejnych przebiegów.
- **Deterministyczne śledzenie stanu**: Sumy SHA-256 w `.ai-team/state.json`. Aktualizacje nigdy nie nadpisują zmodyfikowanych lokalnie plików — konflikty trafiają do `.ai-team/conflicts/`.
- **Zachowanie kontekstu projektu**: Pliki `PROJECT_CONTEXT.md`, `ai-team.config.json` oraz `.agents/skills/project/` są chronione i nienaruszane podczas aktualizacji.
- **Pełne wsparcie wieloplatformowe**: Natywna obsługa Windows 11 (PowerShell) i Linux (bash/zsh), w tym wsparcie dla VS Code Remote SSH.
- **Integracja z VS Code**: Automatyczne generowanie i bezkonfliktowy merge zadań w `.vscode/tasks.json` (uruchamianie promptów, diagnostyka, aktualizacja).
- **Rygorystyczne zasady bezpieczeństwa**: Brak automatycznego push, merge i deploymentu. Wszystkie zmiany powstają na dedykowanych branchach `ai/...`.

---

## Wymagania

- **Python**: 3.10 lub nowszy
- **Git**: Zainstalowany i dostępny w `$PATH`
- **Narzędzia CLI agentów**:
  - `agy` (Google Antigravity CLI) — **Wymagane** (główny wykonawca)
  - `codex` (OpenAI Codex CLI) — Opcjonalne (rekomendowane dla review MEDIUM/HIGH)
  - `claude` (Anthropic Claude Code CLI) — Opcjonalne (rekomendowane dla review HIGH)

> [!NOTE]
> Zaloguj narzędzia `agy`, `claude` oraz `codex` interaktywnie w terminalu co najmniej raz przed uruchomieniem zadań nienadzorowanych.

---

## Instalacja

Rekomendowaną metodą instalacji na wszystkich platformach jest [`pipx`](https://pypa.github.io/pipx/):

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"
```

### Instalacja konkretnej wersji

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.2.0"
```

### Aktualizacja

```bash
pipx upgrade ai-engineering-team
```

### Opcjonalnie: Instalacja deweloperska przez SSH

```bash
pipx install "git+ssh://git@github.com/tomaasz/ai-engineering-team.git"
```

### Instalacja z lokalnego repozytorium

**Windows (PowerShell):**
```powershell
.\install-local.ps1
```

**Linux (Bash):**
```bash
./install-local.sh
```

---

## Szybki start (Quick Start)

1. Przejdź do katalogu docelowego projektu:
   ```bash
   cd /sciezka/do/twojego-projektu
   ```

2. Zainstaluj AI Engineering Team z wybranym profilem:
   ```bash
   ai-team install . --profile python
   ```

3. Sprawdź poprawność konfiguracji:
   ```bash
   ai-team doctor .
   ```

4. Uruchom zadanie (opcjonalnie w odizolowanym worktree):
   ```bash
   ai-team run . "Dodaj eksport do pliku CSV wraz z pełnym zestawem testów" --worktree
   ```
   *W trybie `--worktree` agenci pracują w odizolowanym katalogu roboczym. Po zakończeniu zadania CLI automatycznie pyta:*
   ```text
   Czy wdrożyć zmiany na gałąź główną 'main'?
     [t]ak       - scal (merge) zmiany na 'main' i usuń gałąź roboczą
     [p]odgląd   - zobacz pełny diff zmian
     [o]drzuć    - odrzuć zmiany i usuń gałąź roboczą
     [n]ie       - pozostaw gałąź do późniejszego wglądu
   Wybór [t/p/o/n]:
   ```
   *Wybór **[t]ak** natychmiast scala zmiany do gałęzi głównej i usuwa tymczasową gałąź roboczą, zapewniając idealny porządek w repozytorium bez namnażania niepotrzebnych gałęzi.*

5. Przejrzyj przebieg i scal lub odrzuć później (jeśli wybrano [n]ie):
   ```bash
   ai-team review            # Podsumowanie werdyktów i kontroli
   ai-team review --diff     # Podgląd pełnego patcha
   ai-team review --merge    # Scalenie gałęzi do bieżącej gałęzi (z automatycznym usunięciem gałęzi)
   ai-team review --discard  # Usunięcie gałęzi przebiegu
   ```

---

## Profile instalacyjne

Profile determinują zestaw instalowanych modułów umiejętności (Skills) oraz szablonów konfiguracyjnych:

| Profil | Przeznaczenie | Kluczowe komponenty |
| ------ | ------------- | ------------------- |
| `core` | Uniwersalna baza | Podstawowe agenty, review kodu, planowanie zadań, testy ogólne. |
| `python` | Aplikacje w Pythonie | Umiejętności bazowe + jakość Pythona, type hints, standardy pytest. |
| `web` | Web & Frontend | Umiejętności bazowe + automatyzacja przeglądarki, inspekcja DOM, testy UI. |
| `postgres` | Projekty bazodanowe | Umiejętności bazowe + bezpieczeństwo PostgreSQL, migracje, blokady. |
| `ocr` | Przetwarzanie dokumentów | Umiejętności bazowe + pipeline OCR, parsowanie layoutu, ekstrakcja tekstu. |
| `geneteka` | Rekordy genealogiczne | Umiejętności bazowe + specjalistyczny pipeline ETL dla zbiorów danych. |
| `full` | Projekty wielodziedzinowe | Pełny zestaw wszystkich dostępnych umiejętności i ról. |

---

## Integracja z VS Code

Podczas instalacji `ai-team` sprawdza plik `.vscode/tasks.json`. Jeśli istnieje, bezkonfliktowo dołącza zadania AI Team bez modyfikowania ani dublowania zadań użytkownika.

### Dostępne zadania:
- **`AI Team: Run prompt`**: Otwiera okno dialogowe w VS Code pytające o prompt, po czym wykonuje `ai-team run`.
- **`AI Team: Doctor`**: Uruchamia diagnostykę środowiska w zintegrowanym terminalu VS Code.
- **`AI Team: Update`**: Synchronizuje szablony i skille frameworka z zainstalowaną wersją.

Uruchamianie: `Ctrl+Shift+P` (lub `Cmd+Shift+P` na macOS) → `Tasks: Run Task` → Wybierz zadanie.

---

## Windows

- Pełne wsparcie pod Windows 10/11 z użyciem PowerShell 7 lub Windows PowerShell 5.1.
- Upewnij się, że Python i Git znajdują się w zmiennej środowiskowej `PATH`.
- Ścieżki plikowe są obsługiwane w sposób w pełni wieloplatformowy z automatyczną normalizacją ukośników.

## Linux

- Pełne wsparcie na dystrybucjach Ubuntu, Debian, Fedora, Arch, Alpine.
- Działa bez problemu w środowiskach `bash` oraz `zsh`.

## VS Code Remote SSH

W przypadku pracy na zdalnym serwerze VPS lub w kontenerze:
- Zainstaluj `ai-team` oraz CLI agentów (`agy`, `claude`, `codex`) **na maszynie zdalnej**.
- Zadania VS Code są uruchamiane bezpośrednio w środowisku zdalnym, zapewniając dostęp do zdalnych plików, kontenerów i usług dev.

---

## Aktualizacja frameworka w projekcie

Aby zaktualizować szablony frameworka w projekcie:
```bash
cd /sciezka/do/projektu
ai-team update .
```

- **Pliki chronione**: `PROJECT_CONTEXT.md`, `ai-team.config.json` oraz `.agents/skills/project/` nigdy nie są nadpisywane.
- **Obsługa konfliktów**: Jeśli zmodyfikowałeś plik szablonu lokalnie, `ai-team update` zachowuje Twoją wersję, a wersję nadrzędną zapisuje w `.ai-team/conflicts/<sciezka>`, zapobiegając utracie zmian.

---

## Model bezpieczeństwa (Security Model)

> [!WARNING]
> **Lokalne wykonywanie kodu**: AI Engineering Team uruchamia modele AI, które mogą generować i wykonywać polecenia powłoki, instalować pakiety i modyfikować pliki w Twoim systemie.

W celu ochrony repozytoriów i środowiska pracy framework wymusza następujące ograniczenia:
1. **Brak automatycznego push i merge**: `ai-team` **nigdy** nie wykonuje `git push` ani nie scala kodu do głównych gałęzi.
2. **Brak automatycznego deploymentu**: Runner nie wykonuje poleceń wdrażania ani modyfikacji infrastruktury produkcyjnej.
3. **Izolacja gałęzi**: Wszystkie zmiany są wprowadzane wyłącznie na dedykowanych branchach z prefiksem `ai/`.
4. **Domyślnie włączony sandbox**: Antigravity działa z domyślnym ustawieniem `"sandbox": true`.
5. **Domyślnie wyłączony Full Auto**: `"fullAuto": false` chroni przed pomijaniem uprawnień (`--dangerously-skip-permissions`). Włączaj ten tryb wyłącznie w odizolowanych kontenerach.
6. **Tylko do odczytu dla zewnętrznych recenzentów**: Agenty recenzujące (`claude`, `codex`) są uruchamiane w rygorystycznym trybie read-only / plan-only i nie mają prawa modyfikować kodu.

Szczegółowe zasady zgłaszania luk bezpieczeństwa znajdują się w [SECURITY.md](SECURITY.md).

---

## Project Bootstrap (Prompty inicjalizujące)

Jeżeli chcesz, aby autonomiczny agent skonfigurował AI Engineering Team w nowym lub istniejącym repozytorium, wklej jeden z poniższych promptów do jego interfejsu.

### Prompt angielski (EN)

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

### Prompt polski (PL)

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

## Rozwój projektu (Development)

Sklonuj repozytorium i zainstaluj w trybie edytowalnym wraz z zależnościami deweloperskimi:
```bash
git clone https://github.com/tomaasz/ai-engineering-team.git
cd ai-engineering-team
python -m pip install -e ".[dev]"
```

Uruchomienie testów jednostkowych:
```bash
pytest -v
```

Budowanie pakietu:
```bash
python -m build
```

---

## Współpraca (Contributing)

Zapraszamy do współtworzenia projektu! Zapoznaj się z plikiem [CONTRIBUTING.md](CONTRIBUTING.md), aby poznać standardy kodu, wymagania testowe i procedurę zgłaszania Pull Requestów.

---

## Licencja

Projekt jest objęty [Licencją MIT](LICENSE).
