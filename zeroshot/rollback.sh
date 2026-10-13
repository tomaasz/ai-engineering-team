#!/usr/bin/env bash
set -euo pipefail

# Rollback script for Zeroshot trial branch in ai-engineering-team

DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: $0 [--dry-run] [--force]" >&2
            exit 1
            ;;
    esac
done

MAIN_REPO="/home/tomaasz/projekty/ai-engineering-team"
WORKTREE_PATH="${MAIN_REPO}/.worktrees/trial-zeroshot-verification-loop"
BRANCH_NAME="trial/zeroshot-verification-loop"

echo "=== Procedura Rollbacku: Próba Zeroshot R204 ==="
echo "Repozytorium: ${MAIN_REPO}"
echo "Worktree:     ${WORKTREE_PATH}"
echo "Gałąź:        ${BRANCH_NAME}"

if [ "${DRY_RUN}" = true ]; then
    echo "[DRY-RUN] Sprawdzanie stanu..."
    git -C "${MAIN_REPO}" worktree list
    echo "[DRY-RUN] W trybie wykonania zostanie uruchomione:"
    echo "  git -C '${MAIN_REPO}' worktree remove --force '${WORKTREE_PATH}'"
    echo "  git -C '${MAIN_REPO}' branch -D '${BRANCH_NAME}'"
    exit 0
fi

if [ "${FORCE}" != true ]; then
    echo "BŁĄD: Wymagane potwierdzenie flagą --force, aby usunąć gałąź próbną i worktree." >&2
    echo "Uruchom: $0 --force" >&2
    exit 1
fi

echo "1. Usuwanie worktree..."
if [ -d "${WORKTREE_PATH}" ] || git -C "${MAIN_REPO}" worktree list | grep -q "${WORKTREE_PATH}"; then
    git -C "${MAIN_REPO}" worktree remove --force "${WORKTREE_PATH}" || rm -rf "${WORKTREE_PATH}"
    git -C "${MAIN_REPO}" worktree prune
    echo "   -> Worktree pomyślnie usunięte."
else
    echo "   -> Worktree już nie istnieje."
fi

echo "2. Usuwanie gałęzi próbnej ${BRANCH_NAME}..."
if git -C "${MAIN_REPO}" show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
    git -C "${MAIN_REPO}" branch -D "${BRANCH_NAME}"
    echo "   -> Gałąź pomyślnie usunięta."
else
    echo "   -> Gałąź już nie istnieje."
fi

echo "3. Weryfikacja czystości repozytorium głównego..."
git -C "${MAIN_REPO}" status

echo "=== Rollback zakończony pomyślnie. Kod produkcyjny main pozostał nienaruszony. ==="
