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
