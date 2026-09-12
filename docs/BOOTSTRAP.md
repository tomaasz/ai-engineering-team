# Agent bootstrap prompts

Use one prompt below from the root of the target Git repository. Replace `<SOURCE>` with an inspected repository URL plus commit, a released version, or a trusted local checkout. Do not claim the existing `v3.0.1` tag contains current unreleased changes.

## English

```text
Install and configure AI Engineering Team in this repository.

1. Inspect the repository before editing: find the Git root, current branch and status, project components, languages, package managers, documented build/test/lint/typecheck commands, existing AI instruction files, VS Code configuration, and sensitive paths. Do not guess commands and do not run migrations, deployment, production, or destructive operations.
2. Obtain AI Engineering Team from <SOURCE>. Pin the exact inspected commit or released version. Distinguish installation/upgrading of the central CLI from `ai-team update`, which manages project templates. Record the selected source and version in your report.
3. Run `ai-team profiles`, choose the smallest suitable profile based on repository evidence, and run `ai-team install . --profile <profile>` at the Git root. Preserve all existing content. Inspect `.ai-team/conflicts/`; compare each project file with its staged template and resolve it explicitly with `ai-team resolve . <file> --strategy keep|upstream`. Use `keep` unless replacing the file is clearly justified; manually combine useful instructions before accepting the resulting project copy when needed.
4. Complete `PROJECT_CONTEXT.md` from repository evidence. Configure `ai-team.config.json`:
   - choose `primaryProvider` from agy, codex, or claude;
   - use only distinct non-primary reviewers;
   - require at least one reviewer for MEDIUM and two for HIGH;
   - configure verified `verification.commands` as argv arrays with cwd and timeoutSeconds;
   - if no safe check exists, set a precise `verification.noChecksReason` and report that runs can only be PASS_WITH_NOTES;
   - add conservative project-specific `riskPaths` and reasonable agentTimeoutSeconds, runTimeoutSeconds, and maxReviewRounds.
5. Check `ai-team --version`, `ai-team status .`, and `ai-team doctor . --probe`. Treat doctor and help probes as static checks only. Separately execute a harmless real request through every configured provider/model to verify authentication, model access, quota, and permissions. Never expose or store secrets.
6. Review generated and modified files. Do not commit, stash, push, merge, deploy, or discard user changes unless already explicitly authorized. The default run requires an initial commit and clean tree, so state that setup changes must be reviewed and committed before the first run.
7. Report: Git root and components; installed source/version/profile; files created, preserved, backed up, normalized, or conflicted; conflict decisions; primary provider and reviewers; verification commands and whether each was actually executed; doctor results; real provider/model checks; remaining limitations or blockers.

End with exactly one line:
AI_TEAM_READY: YES
or
AI_TEAM_READY: NO - <specific blockers>

YES is allowed only when there are no unresolved installation conflicts, configuration validates, required CLIs exist, each configured provider/model has passed a real authentication/access request, verification is configured, an initial commit exists, and the working tree is ready for the configured clean-tree policy. `doctor --probe` alone is insufficient.
```

## Polski

```text
Zainstaluj i skonfiguruj AI Engineering Team w tym repozytorium.

1. Przed edycją przeanalizuj repozytorium: znajdź główny katalog Git, branch i status, komponenty projektu, języki, menedżery pakietów, udokumentowane polecenia build/test/lint/typecheck, istniejące instrukcje AI, konfigurację VS Code i wrażliwe ścieżki. Nie zgaduj poleceń. Nie uruchamiaj migracji, wdrożeń, operacji produkcyjnych ani destrukcyjnych.
2. Pobierz AI Engineering Team z <SOURCE>. Przypnij dokładnie sprawdzony commit albo wydaną wersję. Rozróżnij instalację lub aktualizację centralnego CLI od `ai-team update`, które zarządza szablonami projektu. Podaj źródło i wersję w raporcie.
3. Uruchom `ai-team profiles`, wybierz najmniejszy profil uzasadniony zawartością repozytorium i wykonaj `ai-team install . --profile <profil>` w głównym katalogu Git. Zachowaj istniejącą treść. Przejrzyj `.ai-team/conflicts/`; porównaj każdy plik projektu z odłożonym szablonem i rozwiąż konflikt jawnie przez `ai-team resolve . <plik> --strategy keep|upstream`. Wybierz `keep`, jeśli zastąpienie nie jest wyraźnie uzasadnione; w razie potrzeby najpierw połącz ręcznie użyteczne instrukcje w kopii projektu.
4. Uzupełnij `PROJECT_CONTEXT.md` wyłącznie na podstawie dowodów w repozytorium. Skonfiguruj `ai-team.config.json`:
   - wybierz `primaryProvider`: agy, codex albo claude;
   - użyj wyłącznie różnych recenzentów innych niż główny dostawca;
   - wymagaj co najmniej jednego recenzenta dla MEDIUM i dwóch dla HIGH;
   - zapisz potwierdzone `verification.commands` jako tablice argv z cwd i timeoutSeconds;
   - jeżeli nie ma bezpiecznego testu, podaj precyzyjne `verification.noChecksReason` i zaznacz, że wynik może być najwyżej PASS_WITH_NOTES;
   - dodaj konserwatywne `riskPaths` projektu oraz rozsądne agentTimeoutSeconds, runTimeoutSeconds i maxReviewRounds.
5. Sprawdź `ai-team --version`, `ai-team status .` oraz `ai-team doctor . --probe`. Traktuj doctor i wywołania help tylko jako kontrolę statyczną. Osobno wykonaj nieszkodliwe prawdziwe żądanie u każdego skonfigurowanego dostawcy/modelu, aby sprawdzić logowanie, dostęp do modelu, limit i uprawnienia. Nie ujawniaj ani nie zapisuj sekretów.
6. Przejrzyj utworzone i zmienione pliki. Nie wykonuj commit, stash, push, merge, deploy ani usuwania zmian użytkownika bez wcześniejszej wyraźnej zgody. Domyślny run wymaga pierwszego commita i czystego drzewa, więc zaznacz, że konfigurację trzeba przejrzeć i zatwierdzić przed pierwszym zadaniem.
7. Zaraportuj: katalog Git i komponenty; źródło, wersję i profil; pliki utworzone, zachowane, objęte kopią, znormalizowane lub konfliktowe; decyzje konfliktów; głównego dostawcę i recenzentów; komendy weryfikacji i informację, które rzeczywiście wykonano; wynik doctor; prawdziwe testy dostawców/modeli; ograniczenia i blokady.

Zakończ dokładnie jednym wierszem:
AI_TEAM_READY: YES
albo
AI_TEAM_READY: NO - <konkretne blokady>

YES jest dozwolone tylko wtedy, gdy nie ma nierozwiązanych konfliktów instalacji, konfiguracja jest poprawna, wymagane CLI istnieją, każdy dostawca/model przeszedł prawdziwe żądanie sprawdzające logowanie i dostęp, weryfikacja jest skonfigurowana, istnieje pierwszy commit, a drzewo robocze spełnia skonfigurowaną politykę czystości. Sam `doctor --probe` nie wystarcza.
```
