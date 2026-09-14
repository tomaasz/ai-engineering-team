# Agent bootstrap prompts

Use one prompt below from the root of the target Git repository. The source is fixed to `https://github.com/tomaasz/ai-engineering-team` (`main` branch) — `main` is maintained to always be in an installable state, so no edits are needed before pasting the prompt. Record the exact commit SHA that was actually fetched in your report.

## English

```text
Install and configure AI Engineering Team in this repository.

1. Inspect the repository before editing: find the Git root, current branch and status, project components, languages, package managers, documented build/test/lint/typecheck commands, existing AI instruction files, VS Code configuration, and sensitive paths. Do not guess commands and do not run migrations, deployment, production, or destructive operations.
2. Obtain AI Engineering Team from `https://github.com/tomaasz/ai-engineering-team` (`main` branch). Pin the exact commit SHA you fetched. Distinguish installation/upgrading of the central CLI from `ai-team update`, which manages project templates. Record the selected commit and version in your report.
3. Run `ai-team profiles`, choose the smallest suitable profile based on repository evidence, and run `ai-team install . --profile <profile> --lang en` at the Git root. `--lang` decides which language the installed agent instructions and skills use; keep it matching the language of this prompt, because the runner then phrases its own stage prompts the same way. Preserve all existing content. Inspect `.ai-team/conflicts/`; compare each project file with its staged template and resolve it explicitly with `ai-team resolve . <file> --strategy keep|upstream`. Use `keep` unless replacing the file is clearly justified; manually combine useful instructions before accepting the resulting project copy when needed. Note any `[SEED]` line (a profile seeded `riskPaths`) and any VS Code merge that reported removed comments.
4. Complete `PROJECT_CONTEXT.md` from repository evidence. Leave no `TODO` placeholder: name the concrete files that best represent the project's target style and what to imitate from each, and the areas whose pattern must not be copied. `doctor` reports remaining `TODO` markers as a problem.
5. Configure `ai-team.config.json`:
   - choose `primaryProvider` from agy, codex, or claude;
   - use only distinct non-primary reviewers;
   - require at least one reviewer for LOW and MEDIUM, and two for HIGH. `"LOW": []` is rejected unless you also set `allowUnreviewedLowRisk: true`, which you may do only with a stated reason;
   - install every reviewer CLI named at any level, not only the ones you expect to use: risk escalates from the real diff after implementation, and a missing reviewer aborts the run before it starts;
   - configure verified `verification.commands` as argv arrays with cwd and timeoutSeconds. An `argv[0]` such as `bash`, `sh`, `pwsh`, `env` or `xargs` is rejected unless the command sets `allowShellWrapper: true`; prefer a direct program invocation over a shell wrapper;
   - if no safe check exists, set a precise `verification.noChecksReason` and report that runs can only be PASS_WITH_NOTES;
   - add conservative project-specific `riskPaths` on top of anything the profile seeded, and reasonable agentTimeoutSeconds, runTimeoutSeconds, and maxReviewRounds;
   - if the provider CLIs authenticate through environment variables rather than a stored login, list those variable names in `passthroughEnv`; the runner strips credential-looking variables from subprocess environments, provider API keys included. Do not put secret values in the configuration file.
6. Check `ai-team --version`, `ai-team status .`, and `ai-team doctor . --probe`. Treat doctor and help probes as static checks only. Separately execute a harmless real request through every configured provider/model to verify authentication, model access, quota, and permissions. Never expose or store secrets.
7. Review generated and modified files. Do not commit, stash, push, merge, deploy, or discard user changes unless already explicitly authorized. The default run requires an initial commit and clean tree, so state that setup changes must be reviewed and committed before the first run.
8. Report: Git root and components; installed source/version/profile; files created, preserved, backed up, normalized, or conflicted; conflict decisions; primary provider and reviewers, including which reviewer CLIs are installed; verification commands and whether each was actually executed; doctor results; real provider/model checks; remaining limitations or blockers.

End with exactly one line:
AI_TEAM_READY: YES
or
AI_TEAM_READY: NO - <specific blockers>

YES is allowed only when there are no unresolved installation conflicts, configuration validates, `ai-team doctor .` exits 0, every reviewer CLI named in the review policy exists, each configured provider/model has passed a real authentication/access request, verification is configured, an initial commit exists, and the working tree is ready for the configured clean-tree policy. `doctor --probe` alone is insufficient.
```

## Polski

```text
Zainstaluj i skonfiguruj AI Engineering Team w tym repozytorium. Źródło jest stałe: `https://github.com/tomaasz/ai-engineering-team` (branch `main`) — `main` jest utrzymywany zawsze w stanie nadającym się do instalacji, więc nie trzeba niczego edytować przed wklejeniem promptu. Podaj w raporcie dokładny commit SHA, który faktycznie pobrałeś.

1. Przed edycją przeanalizuj repozytorium: znajdź główny katalog Git, branch i status, komponenty projektu, języki, menedżery pakietów, udokumentowane polecenia build/test/lint/typecheck, istniejące instrukcje AI, konfigurację VS Code i wrażliwe ścieżki. Nie zgaduj poleceń. Nie uruchamiaj migracji, wdrożeń, operacji produkcyjnych ani destrukcyjnych.
2. Pobierz AI Engineering Team z `https://github.com/tomaasz/ai-engineering-team` (branch `main`). Przypnij dokładny pobrany commit SHA. Rozróżnij instalację lub aktualizację centralnego CLI od `ai-team update`, które zarządza szablonami projektu. Podaj commit i wersję w raporcie.
3. Uruchom `ai-team profiles`, wybierz najmniejszy profil uzasadniony zawartością repozytorium i wykonaj `ai-team install . --profile <profil> --lang pl` w głównym katalogu Git. `--lang` decyduje, w jakim języku instalowane są instrukcje agentów i skille; zostaw zgodnie z językiem tego promptu, bo runner formułuje wtedy własne prompty etapów tak samo. Zachowaj istniejącą treść. Przejrzyj `.ai-team/conflicts/`; porównaj każdy plik projektu z odłożonym szablonem i rozwiąż konflikt jawnie przez `ai-team resolve . <plik> --strategy keep|upstream`. Wybierz `keep`, jeśli zastąpienie nie jest wyraźnie uzasadnione; w razie potrzeby najpierw połącz ręcznie użyteczne instrukcje w kopii projektu. Odnotuj każdą linię `[SEED]` (profil zasiał `riskPaths`) oraz scalenie VS Code, które zgłosiło usunięcie komentarzy.
4. Uzupełnij `PROJECT_CONTEXT.md` wyłącznie na podstawie dowodów w repozytorium. Nie zostawiaj żadnego `TODO`: wskaż konkretne pliki najlepiej reprezentujące docelowy styl projektu i to, co z każdego przejąć, oraz obszary, których wzorca nie wolno powielać. `doctor` zgłasza pozostawione `TODO` jako problem.
5. Skonfiguruj `ai-team.config.json`:
   - wybierz `primaryProvider`: agy, codex albo claude;
   - użyj wyłącznie różnych recenzentów innych niż główny dostawca;
   - wymagaj co najmniej jednego recenzenta dla LOW i MEDIUM oraz dwóch dla HIGH. `"LOW": []` jest odrzucane, chyba że ustawisz też `allowUnreviewedLowRisk: true` — zrób to wyłącznie z podanym uzasadnieniem;
   - zainstaluj każde CLI recenzenta wymienione na dowolnym poziomie, nie tylko te, których się spodziewasz: ryzyko eskaluje na podstawie rzeczywistego diffu po implementacji, a brak recenzenta przerywa przebieg jeszcze przed startem;
   - zapisz potwierdzone `verification.commands` jako tablice argv z cwd i timeoutSeconds. `argv[0]` w rodzaju `bash`, `sh`, `pwsh`, `env` czy `xargs` jest odrzucane, chyba że polecenie ustawi `allowShellWrapper: true`; preferuj bezpośrednie wywołanie programu zamiast powłoki;
   - jeżeli nie ma bezpiecznego testu, podaj precyzyjne `verification.noChecksReason` i zaznacz, że wynik może być najwyżej PASS_WITH_NOTES;
   - dodaj konserwatywne `riskPaths` projektu ponad to, co zasiał profil, oraz rozsądne agentTimeoutSeconds, runTimeoutSeconds i maxReviewRounds;
   - jeżeli CLI dostawców uwierzytelniają się zmiennymi środowiskowymi, a nie zapisanym logowaniem, wypisz nazwy tych zmiennych w `passthroughEnv`; runner usuwa ze środowiska podprocesów zmienne wyglądające na poświadczenia, w tym klucze API dostawców. Nie wpisuj wartości sekretów do pliku konfiguracyjnego.
6. Sprawdź `ai-team --version`, `ai-team status .` oraz `ai-team doctor . --probe`. Traktuj doctor i wywołania help tylko jako kontrolę statyczną. Osobno wykonaj nieszkodliwe prawdziwe żądanie u każdego skonfigurowanego dostawcy/modelu, aby sprawdzić logowanie, dostęp do modelu, limit i uprawnienia. Nie ujawniaj ani nie zapisuj sekretów.
7. Przejrzyj utworzone i zmienione pliki. Nie wykonuj commit, stash, push, merge, deploy ani usuwania zmian użytkownika bez wcześniejszej wyraźnej zgody. Domyślny run wymaga pierwszego commita i czystego drzewa, więc zaznacz, że konfigurację trzeba przejrzeć i zatwierdzić przed pierwszym zadaniem.
8. Zaraportuj: katalog Git i komponenty; źródło, wersję i profil; pliki utworzone, zachowane, objęte kopią, znormalizowane lub konfliktowe; decyzje konfliktów; głównego dostawcę i recenzentów wraz z informacją, które CLI recenzentów są zainstalowane; komendy weryfikacji i informację, które rzeczywiście wykonano; wynik doctor; prawdziwe testy dostawców/modeli; ograniczenia i blokady.

Zakończ dokładnie jednym wierszem:
AI_TEAM_READY: YES
albo
AI_TEAM_READY: NO - <konkretne blokady>

YES jest dozwolone tylko wtedy, gdy nie ma nierozwiązanych konfliktów instalacji, konfiguracja jest poprawna, `ai-team doctor .` kończy się kodem 0, istnieje każde CLI recenzenta wymienione w polityce recenzji, każdy dostawca/model przeszedł prawdziwe żądanie sprawdzające logowanie i dostęp, weryfikacja jest skonfigurowana, istnieje pierwszy commit, a drzewo robocze spełnia skonfigurowaną politykę czystości. Sam `doctor --probe` nie wystarcza.
```
