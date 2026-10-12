# Procedura Odwrócenia Zmian (Rollback Procedure) — Próba Zeroshot R204

## 1. Cel i Zakres
Niniejsza procedura definiuje bezpieczne i bezstratne wycofanie wszystkich artefaktów gałęzi próbnej `trial/zeroshot-verification-loop` w repozytorium `ai-engineering-team`.

Środowisko próby zostało w 100% odizolowane od gałęzi produkcyjnej `main` przy użyciu mechanizmu Git Worktree w katalogu `.worktrees/trial-zeroshot-verification-loop`. Główna gałąź produkcyjna `main` nie zawiera żadnych zmian, co gwarantuje natychmiastowy i bezpieczny rollback w razie decyzji użytkownika lub niespełnienia kryteriów GO/NO-GO.

---

## 2. Izolacja Środowiska
- **Gałąź produkcyjna:** `main` (stan nienaruszony, czyste drzewo robocze).
- **Gałąź próbna:** `trial/zeroshot-verification-loop`.
- **Lokalizacja worktree próby:** `/home/tomaasz/projekty/ai-engineering-team/.worktrees/trial-zeroshot-verification-loop`.
- **Komponenty Zeroshot:** Zainstalowane w dedykowanym katalogu `zeroshot/` oraz w pamięci podręcznej narzędzi npm (`~/.cache/npm/_npx/`).

---

## 3. Instrukcja Krok po Kroku (Manual Rollback)

W przypadku podjęcia decyzji o wycofaniu próby, wykonaj poniższe kroki z poziomu głównego katalogu repozytorium (`/home/tomaasz/projekty/ai-engineering-team`):

### Krok 1: Przejście do głównego repozytorium
```bash
cd /home/tomaasz/projekty/ai-engineering-team
```

### Krok 2: Usunięcie i wyrejestrowanie worktree próby
```bash
git worktree remove --force .worktrees/trial-zeroshot-verification-loop
```

### Krok 3: Usunięcie gałęzi próbnej Git
```bash
git branch -D trial/zeroshot-verification-loop
```

### Krok 4: Weryfikacja czystości repozytorium
```bash
git worktree list
git status
```
Oczekiwany wynik: tylko gałąź `main` z czystym stanem roboczym.

### Krok 5 (Opcjonalny): Usunięcie pamięci podręcznej Zeroshot
```bash
rm -rf ~/.cache/npm/_npx/*/node_modules/@the-open-engine-company/zeroshot
```

---

## 4. Automatyczny Skrypt Rollbacku
Dla wygody i minimalizacji ryzyka błędu przygotowano zautomatyzowany skrypt:
```bash
# Tryb podglądu (suchy przebieg):
./zeroshot/rollback.sh --dry-run

# Wykonanie rollbacku:
./zeroshot/rollback.sh --force
```
