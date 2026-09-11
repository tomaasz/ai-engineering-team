#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v pipx >/dev/null 2>&1; then
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
fi
pipx install --force "$REPO"
echo "Zainstalowano ai-team. Otwórz nowy terminal i uruchom: ai-team --help"
