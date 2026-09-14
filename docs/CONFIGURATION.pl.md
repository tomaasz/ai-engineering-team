# Dokumentacja konfiguracji

[English](CONFIGURATION.md) · **Polski**

`ai-team.config.json` jest walidowany przed `doctor` i `run`. Komendy nigdy nie są zgadywane na podstawie zawartości repozytorium. Nieznane klucze w `antigravity` są odrzucane, więc klucz, którego runner nie czyta, zawodzi głośno zamiast po cichu się rozjeżdżać.

```json
{
  "language": "pl",
  "primaryProvider": "agy",
  "models": {"agy": "model-id", "claude": {"default": "opus", "triage": "haiku"}},
  "providerArgs": {"codex": {"reviewer": ["--reasoning-effort", "medium"]}},
  "roleProviders": {"integrator": "codex"},
  "requireCleanWorkingTree": true,
  "createBranchForEachRun": true,
  "reuseBranchForFollowUp": false,
  "branchPrefix": "ai/",
  "reviewPolicy": {
    "LOW": ["codex"],
    "MEDIUM": ["codex"],
    "HIGH": ["claude", "codex"]
  },
  "allowUnreviewedLowRisk": false,
  "skipFinalVerificationAtLow": true,
  "agentTimeoutSeconds": 3600,
  "runTimeoutSeconds": 14400,
  "maxReviewRounds": 2,
  "verification": {
    "commands": [
      {"argv": ["python", "-m", "pytest"], "cwd": ".", "timeoutSeconds": 600}
    ]
  },
  "riskPaths": {
    "HIGH": ["infra/**", "src/security/**"],
    "MEDIUM": ["src/api/**"]
  },
  "passthroughEnv": [],
  "protectedIgnoredPaths": [".env", ".env.*", "*.pem", "*.key"]
}
```

## Dostawcy i polityka recenzji

`primaryProvider` przyjmuje `agy`, `codex` albo `claude`.

`reviewPolicy` musi definiować dokładnie `LOW`, `MEDIUM` i `HIGH`. Recenzenci muszą być obsługiwanymi dostawcami, unikalnymi w obrębie poziomu i różnymi od `primaryProvider`. `MEDIUM` wymaga co najmniej jednego recenzenta, a `HIGH` co najmniej dwóch. `LOW` również wymaga jednego: model, który napisał zmianę, nie powinien być jej jedynym sędzią. Ustaw `allowUnreviewedLowRisk` na `true`, aby przyjąć `"LOW": []`, i zapisz dlaczego.

Ponieważ ryzyko eskaluje na podstawie rzeczywistego diffu po implementacji, **każdy** recenzent wymieniony na dowolnym poziomie musi być zainstalowany przed startem przebiegu. Brak któregokolwiek przerywa przebieg od razu, a nie dopiero po opłaceniu etapu implementacji. Brakujący lub zawodzący wymagany recenzent nie daje fallbacku do sukcesu. `availabilityFallback` może pozostać w starszej konfiguracji dla zgodności, ale runner nigdy go nie czyta.

`roleProviders.integrator` kieruje etap rozstrzygania findingów do dostawcy innego niż główny — przydatne, gdy jeden model lepiej recenzuje, niż pisze, albo odwrotnie. Integrator nie może być *jedynym* recenzentem na żadnym poziomie, bo jego własna poprawka nigdy nie dostałaby niezależnego werdyktu.

Uwierzytelnianie u dostawcy, istnienie modelu i dostęp nie są weryfikowane statycznie. `doctor --probe` testuje wyłącznie wywołanie pomocy.

## Modele, effort i argumenty per rola

Role to `triage`, `orchestrator`, `reviewer`, `integrator` i `verifier`.

`models` mapuje dostawcę na jeden identyfikator (obowiązuje wszędzie) albo na obiekt kluczowany rolą plus `default`. Tanie etapy read-only mogą dzięki temu używać mniejszego modelu niż etap implementacji.

`antigravity.triageEffort`, `antigravity.implementationEffort` i `antigravity.verificationEffort` ustawiają `--effort` dla `agy`. Domyślnie: `low` dla triage, `high` dla ról piszących (`orchestrator`, `integrator`) i `medium` dla ról wydających werdykt w trybie read-only (`reviewer`, `verifier`).

`providerArgs` to odpowiednik tej dźwigni dla `codex` i `claude`, które nie mają flagi `--effort`: dokleja surowe argumenty CLI per dostawca i rola, z rolą `default` jako zapasową. Argumenty stąd nadpisują domyślne ustawienia runnera dla tej samej flagi, więc `{"claude": {"reviewer": ["--max-turns", "12"]}}` zastępuje wbudowane `--max-turns 30`, a nie dubluje je. Runner nie sprawdza, czy dana flaga istnieje w używanym CLI.

## Weryfikacja

`verification.commands` to tablica obiektów:

- `argv` jest wymagane: niepusta tablica niepustych stringów. Wykonywana bezpośrednio, bez powłoki.
- `cwd` jest opcjonalne i domyślnie `.`. Musi wskazywać istniejący katalog wewnątrz projektu.
- `timeoutSeconds` jest opcjonalne, domyślnie 300, musi być dodatnią liczbą całkowitą.
- `allowShellWrapper` jest opcjonalne. Bez niego `argv[0]` w rodzaju `bash`, `sh`, `pwsh`, `env` czy `xargs` jest odrzucane, bo przywraca semantykę powłoki, której unika kontrakt bezpośredniego wykonania. Ustawienie na `true` przyjmuje to ryzyko świadomie. Ta kontrola zatrzymuje przypadkowe `bash -c "… | sh"`; nie jest sandboxem, bo `python -c` potrafi to samo.

Używaj komend potwierdzonych przez pliki lub dokumentację projektu.

Gdy nie istnieje bezpieczna komenda automatyczna, użyj pustej listy komend i konkretnego, niepustego `verification.noChecksReason`. Pozwala to wyłącznie na `PASS_WITH_NOTES`. Pominięcie zarówno komend, jak i powodu jest niepoprawne dla gotowości i dla wykonania.

Kontrole uruchamiają się po weryfikacji przez model. Niezerowy kod wyjścia albo nieudany `git diff --check` daje `CHANGES_REQUIRED`; zmiana plików projektu przerywa przebieg jako `FAILED`.

## Limity, Git i rundy recenzji

- `agentTimeoutSeconds`: dodatnia liczba całkowita; limit czasu jednego wywołania dostawcy. Po jego przekroczeniu zabijane jest całe drzewo procesów.
- `runTimeoutSeconds`: dodatnia liczba całkowita; termin całego przebiegu.
- `maxReviewRounds`: liczba całkowita od 1 do 5. Wyczerpanie kończy przebieg jako `CHANGES_REQUIRED` (kod 2), a nie awarią; praca zostaje na branchu. Kontynuuj przez `ai-team resume <run-id> --extra-rounds N`, co odrzuca zapisane werdykty ostatniej rundy i uruchamia ją ponownie.
- `requireCleanWorkingTree`: gdy `true`, blokuje przebieg przy zmianach śledzonych lub nieśledzonych.
- `createBranchForEachRun`: tworzy unikalny branch `branchPrefix + run-id`.
- `useWorktree`: gdy `true`, wykonuje przebiegi w odizolowanym git worktree (`.ai/worktrees/<run_id>`) bez przełączania gałęzi w głównym katalogu roboczym.
- `reuseBranchForFollowUp`: gdy `true`, a bieżący branch zaczyna się od `branchPrefix`, kontynuuje na nim zamiast tworzyć kolejny. Przydatne przy iterowaniu nad jedną zmianą; zostaw wyłączone, gdy każdy przebieg ma być izolowany.
- `skipFinalVerificationAtLow`: gdy `true` (domyślnie), ryzyko to `LOW`, a niezależny recenzent już wydał werdykt, własna weryfikacja końcowa głównego dostawcy jest pomijana. Skonfigurowane kontrole i `git diff --check` nadal się wykonują. Utrzymuje to trywialną zmianę na trzech wywołaniach modelu, zastępując samoocenę oceną niezależną.
- `branchPrefix`: musi zaczynać się od `ai/` i nie może zawierać `..`.

To limity czasu i iteracji. Nie śledzą tokenów ani kosztu. Przerwany przebieg nie wznawia się automatycznie, ale `ai-team resume <run-id>|latest` kontynuuje go ręcznie, pomijając etapy ukończone — etap przerwany w połowie odpowiedzi jest powtarzany, a nie przyjmowany.

## Ścieżki i treść ryzyka

`riskPaths` mapuje `LOW`, `MEDIUM` albo `HIGH` na tablice globów. Dopasowane zmienione ścieżki mogą tylko podnieść bieżący poziom ryzyka. Wzorce wbudowane eskalują ścieżki uwierzytelniania, sesji, tokenów, uprawnień, sekretów, migracji, schematów, płatności, infrastruktury i CI, w tym `*.tfvars`, `Containerfile`, `.gitlab-ci.yml` i `Jenkinsfile`. Lista wbudowana jest celowo szeroka; projekt z niepowiązanym plikiem `tokenizer.py` zobaczy jego eskalację.

Poza nazwami plików skanowane są dodane linie pod kątem destrukcyjnego SQL, wyłączonej weryfikacji TLS i niebezpiecznej deserializacji, które same z siebie eskalują do `HIGH`. Jest to celowo wąskie: łapie to, czego nazwa pliku nie wyrazi, a nie wszystko co niebezpieczne.

Pliki guardrail zawsze eskalują do `HIGH`, niezależnie od konfiguracji: `ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` oraz wszystko w `.agents/agents/`, `.claude/agents/`, `.agents/skills/` i `.claude/skills/`. Agent nie może osłabić własnej polityki recenzji w nierecenzowanej zmianie jednego pliku. Zmiana `ai-team.config.json` w trakcie przebiegu przerywa ten przebieg.

Część profili zasiewa `riskPaths` przy tworzeniu świeżego `ai-team.config.json` — `postgres` i `geneteka` dodają ścieżki migracji, wersji i `*.sql`, `ocr` dodaje ścieżki pipeline'u. Istniejąca konfiguracja nigdy nie jest modyfikowana.

## Sekrety w środowisku

Podprocesy dostają przefiltrowane środowisko. Usuwane jest wszystko, co pasuje do key, token, secret, password, cookie, credential, auth, private, cert, salt, signing, session, `_DSN`, `_URI`, `_URL` albo segmentu `PAT`/`JWT`/`SK`/`API`, plus stałe nazwy `KUBECONFIG`, `AWS_PROFILE`, `AWS_CONFIG_FILE`, `DOCKER_CONFIG`, `GIT_ASKPASS`, `SSH_ASKPASS`, `NETRC`, `PGSERVICEFILE`, `PGPASSFILE`. Kotwice zaufania TLS (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, ...) oraz `PATH` są zawsze zachowywane.

Usuwa to również `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` i `GOOGLE_APPLICATION_CREDENTIALS`. Jeżeli Twoje CLI uwierzytelniają się przez zmienne środowiskowe, a nie zapisane logowanie, wypisz je w `passthroughEnv`:

```json
{"passthroughEnv": ["ANTHROPIC_API_KEY"]}
```

Filtrowanie środowiska to nie izolacja. Agenci działają z Twoimi uprawnieniami i mogą odczytać `~/.aws/credentials`, `~/.ssh/` i `.env` z dysku. Gdy to istotne, uruchamiaj ich w maszynie wirtualnej lub kontenerze.

`protectedIgnoredPaths` wymienia pliki ignorowane przez Git, których etap read-only mimo to nie może zmodyfikować. Domyślne wartości obejmują `.env`, `.env.*`, `*.pem` i `*.key`.

## Język

`language` to `en` (domyślnie) albo `pl`. Zapisuje go `ai-team install --lang <en|pl>` i decyduje on o tym, jak runner formułuje własne prompty etapów: preambułę roli, instrukcje triage i implementacji, treść recenzji i weryfikacji oraz rubrykę jakości w promptcie werdyktu.

Instalator zapisuje do projektu odpowiadającą wersję językową każdej instrukcji agenta i każdego skilla, więc na dysku istnieje tylko jeden język i żaden przebieg nie płaci za drugą kopię. Utrzymuj `language` zgodne z tym, co umieścił `ai-team install --lang`: polski projekt z `"language": "en"` podawałby modelowi angielskie instrukcje etapów na tle polskich skilli, czyli dokładnie ten mieszany językowo prompt, któremu ten podział ma zapobiegać. `ai-team update --lang <en|pl>` przełącza oba naraz.

## Opcje Antigravity

Opcjonalny obiekt `antigravity` konfiguruje `agy`: `model`, `sandbox`, `fullAuto`, `printTimeout` oraz trzy klucze effort powyżej. Żaden inny klucz nie jest akceptowany. Włączenie szerokiego trybu automatyzacji zmienia uprawnienia dostawcy; utrzymuj politykę projektu i dostawcy spójnie. Etapy read-only wymuszają ograniczony tryb dostawcy tam, gdzie jest wspierany, a runner dodatkowo wykrywa zmiany plików w repozytorium.
