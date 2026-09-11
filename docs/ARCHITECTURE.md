# Architektura
# Architektura AI Engineering Team

Centralne prywatne repo zawiera program `ai-team`, agentów, skille, profile i szablony VS Code.
Centralne repozytorium zawiera program CLI `ai-team`, definicje agentów, zestawy umiejętności (Skills), profile instalacyjne oraz integracje ze środowiskiem IDE (VS Code tasks).

Po `ai-team install` projekt dostaje m.in.:
## Struktura po instalacji w projekcie

Po wykonaniu polecenia `ai-team install . --profile <profil>` docelowy projekt otrzymuje m.in.:

```text
.agents/
.claude/
.vscode/tasks.json
.ai-team/state.json
.ai/runs/
AI_TEAM.md
AGENTS.md
CLAUDE.md
GEMINI.md
PROJECT_CONTEXT.md
ai-team.config.json
.agents/                  # Definicje agentów i umiejętności dla Google Antigravity
  agents/                 # Role: architect, implementer, integrator, orchestrator, researcher, reviewer, test-engineer, triage, verifier
  skills/                 # Moduły wiedzy (core, python, web, postgres, ocr itp.)
.claude/                  # Konfiguracja i agenci dla Claude Code
  agents/                 # Independent reviewer, debugger
  skills/                 # Moduły wiedzy odpowiadające profilowi
.vscode/tasks.json        # Zadania VS Code (Run prompt, Doctor, Update)
.ai-team/                 # Stan wewnętrzny instalatora
  state.json              # Sumy kontrolne SHA-256 zainstalowanych plików
  conflicts/              # Miejsce odkładania konfliktów przy aktualizacjach
.ai/                      # Środowisko uruchomieniowe (automatycznie dodane do .gitignore)
  runs/                   # Historia wykonanych runów, logi i raporty
  latest.txt              # Identyfikator ostatniego uruchomienia
AI_TEAM.md                # Główne zasady zespołu, role, matryca ryzyka, DoD
AGENTS.md                 # Konfiguracja i instrukcje dla OpenAI Codex
CLAUDE.md                 # Konfiguracja dla Claude Code (niezależny reviewer)
GEMINI.md                 # Konfiguracja dla Gemini / Antigravity (główny wykonawca)
PROJECT_CONTEXT.md        # Kontekst projektu uzupełniany przez dewelopera / prompt bootstrap
ai-team.config.json       # Konfiguracja działania zespołu, reguły review i sandbox
```

`state.json` zapisuje hash każdego zarządzanego pliku. Podczas update plik jest nadpisywany tylko wtedy, gdy od poprzedniej instalacji nie został ręcznie zmieniony.
## Zarządzanie stanem i aktualizacje

Plik `.ai-team/state.json` przechowuje sumę kontrolną SHA-256 każdego zarządzanego pliku z chwili instalacji lub ostatniej aktualizacji:
- Podczas `ai-team update .` plik zarządzany jest nadpisywany nową wersją z frameworka **tylko wtedy**, gdy jego lokalna suma kontrolna nie uległa zmianie (plik nie był ręcznie modyfikowany).
- Jeśli plik został lokalnie zmieniony przez użytkownika, aktualizator **nie nadpisuje** wersji lokalnej, lecz zapisuje nową wersję w katalogu `.ai-team/conflicts/`, umożliwiając manualny przegląd różnic.
- Pliki lokalne (`PROJECT_CONTEXT.md`, `ai-team.config.json` oraz `.agents/skills/project/`) są zawsze zachowywane.

## Przepływ orkiestracji (Run Pipeline)

```text
User prompt
    ↓
Triage (analiza zakresu i wyznaczenie poziomu ryzyka)
    ↓
Gemini / Antigravity Team (implementacja i testy)
    ├── Architect
    ├── Researcher
    ├── Implementer
    ├── Test Engineer
    └── Reviewer
    ↓
Risk Gate (niezależna weryfikacja zewnętrzna)
    ├── LOW    → Gemini
    ├── MEDIUM → + Codex
    └── HIGH   → + Claude + Codex
    ↓
Integrator (samodzielne rozstrzyganie findingów dowodem)
    ↓
Final Verifier (ostateczna walidacja testów i diffu bez modyfikacji kodu)
    ↓
Git branch (ai/...) + szczegółowy raport w .ai/runs/
```
