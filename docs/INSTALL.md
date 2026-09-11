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

### Prywatne repo przez SSH
```bash
pipx install "git+ssh://git@github.com/OWNER/ai-engineering-team.git"
```

Aktualizacja centralnego programu:
```bash
pipx upgrade ai-engineering-team
```

### Ze sklonowanego repo
Windows:
```powershell
.\install-local.ps1
```

Linux:
```bash
./install-local.sh
```

## Instalacja do projektu
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

## Test
```bash
ai-team doctor .
```

## Uruchomienie
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

## Linux / serwer VPS
Na serwerze workflow jest taki sam:
```bash
cd ~/projects/my-project
ai-team doctor .
ai-team run . "Napraw failing integration tests"
```

Przy VS Code Remote SSH `ai-team` oraz `agy` muszą być zainstalowane po stronie zdalnego Linuxa, bo task jest wykonywany w zdalnym workspace.
