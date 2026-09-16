#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v uv >/dev/null 2>&1; then
  echo "Instalacja za pomocą uv tool..."
  uv tool install --editable "$REPO" --force
elif command -v pipx >/dev/null 2>&1; then
  echo "Instalacja za pomocą pipx..."
  pipx install --force "$REPO"
else
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
  pipx install --force "$REPO"
fi
echo "Zainstalowano ai-team. Otwórz nowy terminal i uruchom: ai-team --help"
