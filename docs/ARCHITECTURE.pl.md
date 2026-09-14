# Architektura

[English](ARCHITECTURE.md) · **Polski**

Pakiet zawiera dispatcher, adaptery dostawców, instalator, profile, instrukcje agentów, skille i szablony IDE. Instalacja kopiuje wybrany profil do repozytorium Git i zapisuje sumy kontrolne zarządzanych plików oraz nierozwiązane konflikty w `.ai-team/state.json`.

## Przebieg runu

```text
prompt
  -> kontrola gotowości (główny dostawca + każde CLI recenzenta z dowolnego poziomu polityki)
  -> read-only triage (ryzyko w JSON)
  -> implementacja przez głównego dostawcę
  -> eskalacja ryzyka ze zmienionych ścieżek, zmienionej treści i plików guardrail
  -> niezależne recenzje (werdykty JSON) na podstawie wygenerowanego diff.patch
  -> integracja gdy potrzebna (główny dostawca albo roleProviders.integrator)
  -> ograniczona liczba rund recenzji
  -> read-only verifier końcowy (werdykt JSON), pomijany przy LOW gdy recenzent już zatwierdził
  -> skonfigurowane kontrole argv + git diff --check
  -> result.json
```

Głównym dostawcą może być `agy`, `codex` albo `claude`. Polityka recenzji musi używać różnych dostawców i nie może zawierać głównego. `LOW` wymaga jednego recenzenta, chyba że ustawiono `allowUnreviewedLowRisk`, `MEDIUM` co najmniej jednego, a `HIGH` co najmniej dwóch. Brakujące CLI oraz nieudane lub niepoprawne recenzje zatrzymują przebieg; runner nie czyta `availabilityFallback` i nie pozwala on na sukces. Ponieważ ryzyko eskaluje na podstawie rzeczywistego diffu, każde CLI recenzenta wymienione gdziekolwiek w polityce musi być zainstalowane przed startem, nie tylko te wynikające z poziomu ustalonego w triage.

Triage zwraca `{"risk":"LOW|MEDIUM|HIGH"}`. Recenzje i weryfikacja końcowa zwracają `verdict`, `unresolved` i `summary`. Werdykt zaliczający nie może zawierać nierozwiązanych findingów. Dispatcher parsuje JSON, zamiast szukać słowa `PASS` w prozie. Niepoprawna odpowiedź wskazuje dostawcę, plik etapu i pierwsze 200 znaków tego, co wróciło.

Prompty recenzji niosą jawną rubrykę jakości (najpierw poprawność, potem czy zmiana jest minimalna, wolna od przedwczesnej abstrakcji i spójna z otaczającym kodem) oraz treść każdego `.agents/skills/*/*/SKILL.md`, więc kryteria recenzji nie zależą od tego, czy dane CLI samo odnajdzie skille.

Ryzyko jest przeliczane na podstawie klasyfikacji początkowej, liczby zmienionych plików, wbudowanych globów wrażliwych nazw, `riskPaths`, treści dodanych linii oraz stałej listy guardrail. Pliki definiujące sposób, w jaki zespół recenzuje sam siebie — `ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, pliki instrukcji AI oraz wszystko w `.agents/agents/`, `.claude/agents/`, `.agents/skills/` i `.claude/skills/` — zawsze eskalują do `HIGH`. Runner przerywa też przebieg, jeśli `ai-team.config.json` zmieni się w jego trakcie. Dopasowanie po nazwie pozostaje heurystyką i nie rozumie semantyki kodu; dopasowanie po treści obejmuje wyłącznie destrukcyjny SQL, wyłączoną weryfikację TLS i niebezpieczną deserializację.

Każdy przebieg zapisuje swój base ref, branch, prompt, wyjście etapów, stderr, logi kontroli i kanoniczny `.ai/runs/<run-id>/result.json`. W trybie `--worktree` (lub `"useWorktree": true`) całe wykonanie jest izolowane w `.ai/worktrees/<run_id>`, pozostawiając aktywną gałąź w pełni nienaruszoną. Po zakończeniu zadania zmiany są czysto utrwalane w gałęzi `ai/<run_id>`, a CLI pyta użytkownika o decyzję o wdrożeniu (merge) wraz z automatycznym usunięciem gałęzi roboczej. W trybie bezpośrednim używany jest dedykowany branch bez automatycznego pusha ani deploymentu.

Komendy weryfikacji uruchamiają się bezpośrednio z `argv`, bez powłoki. `argv[0]` przywracające powłokę (`bash`, `sh`, `pwsh`, `env`, `xargs`, ...) jest odrzucane, chyba że polecenie ustawi `allowShellWrapper`. Zatrzymuje to przypadkowe `bash -c`; nie jest to sandbox, bo każdy interpreter może wykonać dowolny kod. Nieudana komenda, zmiana plików w trakcie weryfikacji, nieudany `git diff --check`, `CHANGES_REQUIRED` albo wyczerpane rundy recenzji uniemożliwiają sukces. Jawny `noChecksReason` jest dozwolony, ale daje najwyżej `PASS_WITH_NOTES`.

## Trwałość

- Odpowiedzi etapów zapisywane są atomowo. Komenda przerwana timeoutem lub zakończona błędem zostawia `<etap>.failed` do diagnozy i nie zostawia pliku `<etap>`, a etap liczy się jako ukończony dopiero po powstaniu znacznika `<etap>.done`. Dzięki temu `resume` powtarza przerwany etap, zamiast uznać obciętą odpowiedź za gotową pracę.
- Timeout zabija całe drzewo procesów (`taskkill /T /F` na Windows, `killpg` gdzie indziej), więc agent po timeoucie przestaje pisać do repozytorium.
- Wyczerpane rundy recenzji kończą przebieg jako `CHANGES_REQUIRED` z kodem 2, a nie wyjątkiem. Praca zostaje na branchu, a `ai-team resume <run-id> --extra-rounds N` otwiera ostatnią rundę ponownie.

## Granice

- `agentTimeoutSeconds` ogranicza jedno bezpośrednio uruchomione wywołanie agenta; `runTimeoutSeconds` ogranicza cały przebieg; `maxReviewRounds` ogranicza cykle recenzja/integracja.
- Nie ma rozliczania tokenów ani kosztu. `ai-team resume <run-id>|latest` wchodzi ponownie w przerwany przebieg po sprawdzeniu, że branch nadal się zgadza, ale resume jest ręczny, nie automatyczny.
- Środowiska podprocesów tracą zmienne wyglądające na poświadczenia, connection stringi lub gniazda agentów, plus stałą listę odrzuceń (`KUBECONFIG`, `AWS_PROFILE`, ...). Usuwa to również klucze API dostawców: wypisz je w `passthroughEnv`, jeśli CLI uwierzytelnia się w ten sposób. Filtrowanie środowiska nie powstrzymuje agenta przed odczytaniem poświadczeń z dysku; działa on z uprawnieniami użytkownika, który go uruchomił.
- Recenzenci używają trybów read-only dostawcy oraz snapshotów systemu plików obejmujących pliki śledzone, nieśledzone, `protectedIgnoredPaths` i sam katalog przebiegu, ale dzielą jedno repozytorium. Niezależność od innych raportów jest też wymuszana promptem, więc nie jest to izolacja kontenera ani hosta.
- Konflikty instalacji pozostają do czasu `resolve`. Zmniejszenie profilu może zostawić wycofane szablony śledzone aż do odinstalowania.
- Scalanie JSONC VS Code tworzy kopię zapasową, normalizuje JSON i zgłasza usunięcie komentarzy.
