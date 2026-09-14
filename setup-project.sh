#!/usr/bin/env bash
# ==============================================================================
# AI Engineering Team - One-Command Project Setup & Onboarding Script
# Automatyczny skrypt instalacji, konfiguracji i weryfikacji projektów
# ==============================================================================
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

if ! command -v ai-team >/dev/null 2>&1; then
  echo "==> ai-team CLI nie jest zainstalowane. Rozpoczynam instalację..."
  if command -v pipx >/dev/null 2>&1; then
    pipx install --upgrade "git+https://github.com/tomaasz/ai-engineering-team.git" || \
    pipx install "git+https://github.com/tomaasz/ai-engineering-team.git"
  else
    python3 -m pip install --user --upgrade "git+https://github.com/tomaasz/ai-engineering-team.git" --break-system-packages 2>/dev/null || \
    python3 -m pip install --user --upgrade "git+https://github.com/tomaasz/ai-engineering-team.git"
  fi
  export PATH="$HOME/.local/bin:$PATH"
fi

exec ai-team onboard "$@"

