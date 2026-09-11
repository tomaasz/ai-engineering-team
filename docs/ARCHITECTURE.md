# Architektura

Centralne prywatne repo zawiera program `ai-team`, agentów, skille, profile i szablony VS Code.

Po `ai-team install` projekt dostaje m.in.:
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
```

`state.json` zapisuje hash każdego zarządzanego pliku. Podczas update plik jest nadpisywany tylko wtedy, gdy od poprzedniej instalacji nie został ręcznie zmieniony.
