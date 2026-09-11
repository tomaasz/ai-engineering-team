# Instalacja — Windows i Linux

## Wymagania
- Git
- Python 3.10+
- Antigravity CLI (`agy`)
- opcjonalnie Claude Code (`claude`)
- opcjonalnie Codex CLI (`codex`)

Antigravity działa natywnie na Windows i Linux. Zaloguj `agy` interaktywnie co najmniej raz przed użyciem trybu automatycznego.

## Instalacja centralnego CLI

Najwygodniej przez `pipx`.
Najwygodniejszą metodą instalacji jest narzędzie `pipx`.

### Prywatne repo przez SSH
### Instalacja przez HTTPS (rekomendowana)
```bash
pipx install "git+ssh://git@github.com/OWNER/ai-engineering-team.git"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"
```

Instalacja konkretnej wersji (np. `v3.0.1`):
```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v3.0.1"
```

Aktualizacja centralnego programu:
```bash
pipx upgrade ai-engineering-team
```

### Ze sklonowanego repo
### Opcjonalnie: Instalacja przez SSH (dla deweloperów)
```bash
pipx install "git+ssh://git@github.com/tomaasz/ai-engineering-team.git"
```

### Ze sklonowanego repozytorium (tryb lokalny)
Windows:
```powershell
.\install-local.ps1
```

Linux:
```bash
./install-local.sh
```

---

## Instalacja do projektu

Przejdź do katalogu dowolnego projektu i zainstaluj wybrany profil:
```bash
cd /path/to/project
ai-team install . --profile python
```

Profile:
- `core`
- `python`
- `web`
- `postgres`
- `ocr`
- `geneteka`
- `full`
Dostępne profile:
- `core` — bazowy zespół i uniwersalne szablony
- `python` — zestaw dla projektów Python (jakość, testy, typowanie)
- `web` — technologie frontendowe i automatyzacja przeglądarki
- `postgres` — bezpieczne operacje bazodanowe i migracje
- `ocr` — pipeline OCR i przetwarzanie dokumentów
- `geneteka` — pipeline ETL dla danych genealogicznych
- `full` — pełny zestaw wszystkich profili i kompetencji

## Test
## Weryfikacja środowiska
```bash
ai-team doctor .
```

## Uruchomienie
## Uruchomienie zadania
```bash
ai-team run . "Dodaj eksport CSV i testy"
```

VS Code:
`Ctrl+Shift+P` → `Tasks: Run Task` → `AI Team: Run prompt`.

## Aktualizacja frameworka w projekcie
```bash
ai-team update .
```

`PROJECT_CONTEXT.md`, `ai-team.config.json` oraz `.agents/skills/project/` są lokalne i nie są nadpisywane.
Jeśli zmienisz ręcznie plik zarządzany przez framework, aktualizator zachowa lokalną wersję, a nową zapisze do `.ai-team/conflicts/`.
- Pliki lokalne (`PROJECT_CONTEXT.md`, `ai-team.config.json` oraz `.agents/skills/project/`) są chronione i nigdy nie są nadpisywane.
- Jeżeli ręcznie zmienisz plik zarządzany przez framework, aktualizator zachowa Twoją wersję, a wersję nadrzędną zapisze w katalogu `.ai-team/conflicts/`.

## Linux / serwer VPS
Na serwerze workflow jest taki sam:
## Linux / serwer VPS / VS Code Remote SSH
Na serwerze Linux proces wygląda identycznie:
```bash
cd ~/projects/my-project
ai-team doctor .
ai-team run . "Napraw failing integration tests"
```

Przy VS Code Remote SSH `ai-team` oraz `agy` muszą być zainstalowane po stronie zdalnego Linuxa, bo task jest wykonywany w zdalnym workspace.
W przypadku korzystania z **VS Code Remote SSH**, programy `ai-team` oraz `agy` muszą być zainstalowane w środowisku zdalnym maszyny Linux, ponieważ zadania VS Code są wykonywane w zdalnym workspace.
