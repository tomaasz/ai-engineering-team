# Historia zmian

[English](CHANGELOG.md) · **Polski**

Wszystkie istotne zmiany w tym projekcie są dokumentowane w tym pliku.

Format opiera się na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
a projekt stosuje [wersjonowanie semantyczne](https://semver.org/spec/v2.0.0.html).

---

## [4.8.0] - 2026-09-14

### Added
- **Komenda Kompleksowego Audytu Aplikacji 360° (`ai-team audit`)**:
  - Nowa wbudowana komenda CLI: `ai-team audit [project] [--output docs/AUDIT.md] [--lang pl|en] [--worktree] [--solo] [--auto-merge]`.
  - Przeprowadza rygorystyczną, wielowymiarową inspekcję aplikacji w 6 kluczowych obszarach:
    1. **Architektura i jakość kodu**: modularność, granice domenowe, dług technologiczny, martwy kod, zapachy kodu (code smells), duplikacja.
    2. **Bezpieczeństwo i podatności**: OWASP Top 10 (2025), CWE, wycieki sekretów i kluczy, SQLi/Command injection, XSS, CSRF, SSRF, IDOR, podatności zależności.
    3. **Niezawodność i obsługa błędów**: wyciszane wyjątki, unhandled rejections, wyścigi współbieżności, wycieki pamięci i otwartych deskryptorów.
    4. **Wydajność i bazy danych**: pętle zapytań N+1, brakujące indeksy, blokowanie pętli zdarzeń, optymalizacja pamięci podręcznej.
    5. **Testy i jakość QA**: luki w pokryciu krytycznych ścieżek i błędów, wiarygodność mocków.
    6. **DevOps i kontenery**: higiena Dockerfile (multi-stage, użytkownik non-root), logowanie strukturyzowane, healthchecki (`/health`), walidacja zmiennych środowiskowych (fail-fast).
  - Automatycznie generuje uporządkowany raport w `docs/AUDIT.md` zawierający:
    - Executive Summary z ogólną oceną stanu zdrowia systemu (A–F / 0–100%).
    - Matrycę Znalezisk z priorytetami (`[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]`), dokładną lokalizacją `plik:linia` i rekomendowaną naprawą.
    - Drobiazgową analizę każdego problemu z dowodem w kodzie, oceną wpływu i minimalnym kodem naprawczym.
    - Priorytetyzowany Plan Naprawczy podzielony na Fazy (Faza 1 P0, Faza 2 P1, Faza 3 P2).
- **Nowy Skill Audytowy (`audit/full-app-audit`)**:
  - Międzyplatformowe szablony skilli w języku angielskim (`SKILL.md`) i polskim (`SKILL.pl.md`) dla `.agents/skills/audit/full-app-audit/` oraz `.claude/skills/audit/full-app-audit/`.
  - Włączony do wszystkich profili projektowych (`core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, `full`).
- **Dedykowana Rola Agenta Audytora (`auditor`)**:
  - Specjalistyczna persona nastawiona na dogłębną inspekcję analityczną bez destrukcyjnych zmian w kodzie (`.agents/agents/auditor.md` i `.claude/agents/auditor.md`).
  - Automatycznie sugerowana przez `ai-team skills suggest` i automatycznie dostarczana do zadań audytowych.

## [4.7.0] - 2026-09-14

### Added
- **Jednokomendowy Onboarding Projektów (`ai-team onboard` / `ai-team quickstart` / `ai-team setup`)**:
  - Automatyczna inicjalizacja repozytorium Git (jeśli brak), instalacja lub aktualizacja `ai-team` z auto-detekcją stosu technologicznego.
  - Automatyczne rozwiązywanie konfliktów szablonów ze strategią `--strategy upstream`.
  - Automatyczna konfiguracja `ai-team.config.json` z bezpiecznymi domyślnymi wartościami (`allowUnreviewedLowRisk: true`, auto-detekcja poleceń testowych dla npm/pytest/cargo/go, reguły solo/multi provider).
  - Automatyczne oczyszczenie `PROJECT_CONTEXT.md` (usunięcie placeholderów `TODO` i wygenerowanie metadanych projektu).
  - Automatyczne zatwierdzenie konfiguracji w Git (`git commit`) oraz uruchomienie pełnej diagnostyki (`ai-team doctor`).
- **Skrypty automatyzujące onboarding (`setup-project.sh` i `setup-project.ps1`)**:
  - Uniwersalne skrypty Bash oraz PowerShell umożliwiające błyskawiczną konfigurację dowolnego repozytorium w kilka sekund jedną komendą.
- **Masowe rozwiązywanie konfliktów (`ai-team resolve <project> all --strategy <keep|upstream>`)**:
  - Możliwość rozwiązania wszystkich zaległych konfliktów szablonów jednym poleceniem.

### Added
- **Tryb pojedynczego dostawcy Solo (`--solo` / `--single-provider` / `"singleProvider": true`)**:
  - Umożliwia realizację pełnego cyklu inżynieryjnego przy użyciu wyłącznie jednego dostawcy (`agy` / Gemini 3.8 Flash High) bez wymogu posiadania zewnętrznych narzędzi CLI (`codex`, `claude`) ani zewnętrznych limitów API (quota).
  - Polityka recenzji automatycznie się dostosowuje: w trybie solo role recenzenta są wykonywane przez odizolowane, wyłącznie do odczytu procesy `primaryProvider` (`--mode plan`, `--sandbox`, brak uprawnień zapisu).
  - Działa bezpośrednio z flagą `ai-team run --solo` lub poprzez wpis `"singleProvider": true` w `ai-team.config.json`.
  - Dodano flagę `--solo` do komendy `ai-team doctor`, weryfikującą gotowość środowiska do pracy solo bez zgłaszania braków zewnętrznych CLI.
- **Odporność na limity i awarie recenzentów (`availabilityFallback`)**:
  - Domyślnie aktywny mechanizm zapobiegający przerwaniu pracy w przypadku wyczerpania quota, przekroczenia limitów zapytań (HTTP 429), błędów autoryzacji czy awarii sieci u zewnętrznych recenzentów.
  - W razie błędu zewnętrznego CLI recenzenta runner loguje komunikat `[FALLBACK]` i bez przerywania pracy płynnie deleguje wykonanie recenzji do odizolowanej instancji dostawcy głównego (`agy`).
  - Wyniki zapisywane są w dedykowanych plikach `review-<round>-<reviewer>-fallback.json` z oznaczeniem `fallbackFrom` w końcowym raporcie wykonania.
  - Możliwość konfiguracji w `ai-team.config.json` (`"availabilityFallback": true/false`) lub za pomocą flag CLI `--availability-fallback` / `--no-availability-fallback`.

## [4.5.0] - 2026-09-14

### Added
- **Automatyzacja aktualizacji via GitHub Actions (`ai-team workflow [project]`)**:
  - Instaluje gotowy workflow GitHub Actions (`.github/workflows/ai-team-update.yml`) w repozytorium docelowym.
  - Uruchamia się cyklicznie co tydzień (lub na żądanie), aktualizuje `ai-engineering-team`, wywołuje `ai-team update .` i automatycznie zakłada Pull Request (`chore/ai-team-update`) w przypadku wykrycia zmian w szablonach lub skillach.
- **Wzmocniona ochrona i higiena Git (`ai-team gitignore [project] [--private]`)**:
  - Automatycznie tworzy `.ai-team/.gitignore` podczas instalacji i aktualizacji, chroniąc przed przypadkowym commitowaniem tymczasowych kopii konfliktów i backupów.
  - `ai-team gitignore`: Dodaje standardowe reguły ignorowania artefaktów wykonawczych (`.ai/runs/`, `.ai-team/conflicts/` itp.) do głównego `.gitignore` projektu.
  - `ai-team gitignore --private`: Konfiguruje tryb prywatnego dewelopera w lokalnym `.git/info/exclude`, ukrywając wszystkie pliki frameworka przed zdalnym repozytorium zespołu.
- **Sprawdzanie dostępności nowej wersji (`ai-team update --check` oraz `ai-team status`)**:
  - Zapewnia pełną odporność na brak sieci, umożliwiając sprawdzenie czy na GitHubie pojawiło się nowsze wydanie oraz informując o krokach aktualizacji.

## [4.4.0] - 2026-09-14

### Added
- **Autonomiczny i proaktywny dobór skilli przez Agenta AI**:
  - Orkiestrator AI automatycznie i proaktywnie zarządza skillami bez konieczności ręcznego wywoływania komend CLI przez użytkownika.
  - **Etap przed implementacją**: Przed rozpoczęciem prac runner analizuje sygnatury stosu technologicznego oraz intencję promptu zadania, automatycznie doinstalowując brakujące skille z katalogu szablonów.
  - **Etap po implementacji**: Analizuje pliki zmienione lub dodane w wygenerowanym diffie (np. Dockerfile, schematy SQL, pliki migracji) i proaktywnie doinstalowuje pasujące skille przed przystąpieniem do niezależnego review.
  - **Autonomiczne skille projektowe**: Agenci w instrukcjach `AI_TEAM.md` i `AGENTS.md` zostali upoważnieni do samodzielnego formułowania i utrzymywania reguł projektowych w `.agents/skills/project/<nazwa>/SKILL.md`.
  - **Konfiguracja i wyłączanie**: Funkcja domyślnie włączona (`"autoSkills": true`), z możliwością wyłączenia flagą `--no-auto-skills` w `ai-team run` lub parametrem `"autoSkills": false` w `ai-team.config.json`.

## [4.3.0] - 2026-09-14

### Added
- **Inteligentne wykrywanie stosu i instalacja automatyczna (`ai-team install --auto`)**: Automatyczna analiza sygnatur repozytorium (`pyproject.toml`, `package.json`, `alembic`, `Dockerfile` itp.) pod kątem języków, baz danych i narzędzi, wraz z doborem optymalnego profilu.
- **Dedykowany interfejs CLI do zarządzania skillami (`ai-team skill` / `ai-team skills`)**:
  - `list`: Przegląd zainstalowanych skilli (ze statusami `MANAGED`, `LOCAL`, `CUSTOM`) oraz dostępnych w katalogu.
  - `suggest`: Analiza stosu repozytorium i prezentacja rekomendacji skilli wraz z uzasadnieniem.
  - `add <skill>`: Instalacja pojedynczego skilla z katalogu szablonów do `.agents/skills/` i `.claude/skills/` wraz z rejestracją w `.ai-team/state.json`.
  - `remove <skill>`: Bezpieczne odinstalowanie zarządzanego skilla i wyrejestrowanie ze śledzenia.
- **Dynamiczny dobór skilli pod zadanie**: Orkiestrator w `runner.py` inteligentnie dopasowuje skille domenowe do treści prompta i zmienionych plików, oszczędzając tokeny okna kontekstowego LLM.
- **Rozszerzenie katalogu skilli**: Dodano skille `devops/docker-quality` (bezpieczeństwo kontenerów, multi-stage, non-root) oraz `security/secure-coding` (ochrona OWASP, sanityzacja danych, zasada najmniejszych uprawnień) w wersjach EN i PL.

## [4.2.0] - 2026-09-14

### Added
- **Automatyczne pytanie o wdrożenie (merge) po izolacji w Git Worktree**: Po ukończeniu zadania w odizolowanym drzewie roboczym (`--worktree`) CLI natychmiast pyta użytkownika, czy wdrożyć zmiany na bieżącą gałąź główną (`main`).
  - `[t]ak`: Scala zmiany (`git merge --no-ff`) na gałąź główną i automatycznie usuwa gałąź roboczą (`git branch -D`), zapobiegając namnażaniu się starych gałęzi w repozytorium.
  - `[p]odgląd`: Wyświetla pełny diff zmian i ponawia zapytanie.
  - `[o]drzuć`: Odrzuca zmiany i natychmiast usuwa gałąź roboczą.
  - `[n]ie`: Pozostawia gałąź do późniejszego wglądu przez `ai-team review <run_id>`.
- **Automatyczne czyszczenie pustych przebiegów**: Jeśli agenci nie wprowadzili żadnych zmian w kodzie, tymczasowa gałąź jest automatycznie usuwana bez niepotrzebnych pytań.
- **Flagi automatyzacji dla skryptów i CI**: Dodano flagi `--auto-merge` (`--merge`), `--auto-discard` (`--discard`) oraz `--non-interactive` w poleceniu `ai-team run`, jak również klucz konfiguracji `"autoMerge": true` w `ai-team.config.json`.
- **Usuwanie gałęzi po scaleniu w CLI Review**: Polecenie `ai-team review <run_id> --merge` domyślnie usuwa scalaną gałąź roboczą (z możliwością jej zachowania za pomocą `--keep-branch`).

## [4.1.0] - 2026-09-14

Usprawnienia autonomicznego workflow i recenzji inspirowane nowoczesnymi architekturami agentowymi (izolacja git worktree, żywa pamięć zespołu, mapowanie repozytorium AST oraz dedykowane CLI do inspekcji).

### Added
- **Izolacja Git Worktree (`--worktree`)**: Wykonywanie przebiegów zespołu agentów w odizolowanym drzewie `.ai/worktrees/<run_id>` bez przełączania bieżącej gałęzi użytkownika i bez przerywania lokalnej pracy. Zmiany są czysto utrwalane w gałęzi `ai/<run_id>`. Opcję można włączyć na stałe przez `"useWorktree": true` w `ai-team.config.json`.
- **Interaktywne CLI recenzji (`ai-team review`)**: Przegląd statusu przebiegu, ocen ryzyka, werdyktów recenzentów i wyników kontroli. Wspiera `--diff` (pełny podgląd łatki względem bazy), `--merge` (czyste scalenie gałęzi przebiegu do bieżącej gałęzi) oraz `--discard` (usunięcie gałęzi przebiegu).
- **Mapa repozytorium AST (`src/ai_team/repomap.py`)**: Wbudowana, bez dodatkowych zależności mapa symboli (klasy, metody, funkcje) automatycznie dołączana do promptów triage i architekta/orkiestratora, zapewniająca kontekst całego projektu przy minimalnym narzucie tokenów.
- **Dynamiczna pamięć zespołu (`.ai/LEARNINGS.md`)**: Automatyczne utrwalanie uwag recenzentów, nierozwiązanych problemów i notatek weryfikacyjnych po każdym przebiegu oraz dołączanie ostatnich wniosków do kolejnych zadań, zapobiegając powtarzaniu tych samych błędów.

## [4.0.0] - 2026-09-12

Realizacja wniosków z audytu frameworka. Kilka domyślnych ustawień zmieniło się tak,
że odrzucają wcześniej poprawne konfiguracje — patrz Migracja.

### Security
- Pliki guardrail (`ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, pliki instrukcji dla
  AI, `.agents/**`, `.claude/**`) zawsze eskalują do `HIGH`, więc agent nie osłabi własnej polityki
  recenzji jedną niezrecenzowaną zmianą. Zmiana pliku konfiguracji w trakcie przebiegu go przerywa.
- Filtrowanie środowiska obejmuje teraz connection stringi, gniazda agentów i wskaźniki do plików
  z poświadczeniami (`DATABASE_URL`, `SENTRY_DSN`, `SSH_AUTH_SOCK`, `KUBECONFIG`,
  `DOCKER_AUTH_CONFIG`, …). Kotwice zaufania TLS są zachowywane jawnie, a klucze API dostawców —
  które filtr również usuwa — można przywrócić per projekt przez `passthroughEnv`.
- Snapshoty etapów read-only obejmują katalog przebiegu i `protectedIgnoredPaths`, co zamyka lukę,
  w której etap mógł pisać do plików ignorowanych przez gita albo do zapisanej odpowiedzi innego etapu.
- Nagłówki `argv` w weryfikacji, które ponownie wprowadzają powłokę (`bash -c`, `sh`, `pwsh`, `env`,
  `xargs`, …), są odrzucane, chyba że polecenie ustawia `allowShellWrapper`.
- Globy ryzyka pokrywają ścieżki pomijane przez starą listę (`session`, `jwt`, `rbac`, `sso`,
  `billing`, `checkout`, `*/versions/*`, `*.tfvars`, `Containerfile`, `.gitlab-ci.yml`,
  `Jenkinsfile`), a dodane linie są skanowane pod kątem destrukcyjnego SQL-a, wyłączonej weryfikacji
  TLS i niebezpiecznej deserializacji.
- `LOW` wymaga teraz jednego niezależnego recenzenta; przyjęcie niezrecenzowanego `LOW` wymaga
  jawnego `allowUnreviewedLowRisk`.

### Fixed
- Odpowiedzi etapów są zapisywane atomowo i oznaczane `.done` dopiero po sukcesie. Przebieg przerwany
  w trakcie etapu nie jest już wznawiany tak, jakby ten etap się zakończył — wcześniej pozwalało to
  `resume` pominąć etap implementacji i recenzować na wpół zapisaną pracę.
- Timeouty zabijają całe drzewo procesów agenta, a nie tylko bezpośredniego potomka, więc agent po
  timeoucie przestaje pisać do repozytorium.
- Każdy recenzent wymieniony gdziekolwiek w `reviewPolicy` jest sprawdzany przed startem przebiegu,
  zamiast powodować błąd po etapie implementacji, gdy ryzyko eskaluje.
- Wyczerpane rundy recenzji kończą przebieg jako `CHANGES_REQUIRED` (kod wyjścia 2) z podpowiedzią
  wznowienia, zamiast rzucać wyjątkiem ponad wciąż użyteczną pracą.
- Niepoprawne werdykty podają dostawcę, plik etapu i pierwsze 200 znaków odpowiedzi.
- `antigravity.triageEffort`, `implementationEffort` i `verificationEffort` są znów odczytywane;
  trafiały do domyślnego szablonu, ale runner ignorował je od czasu przepisania na wielu dostawców.
  Nieznane klucze w `antigravity` są teraz odrzucane, aby ten sam rozjazd ujawnił się głośno.
- Komunikat o brudnym drzewie roboczym nie jest już w połowie polski, w połowie angielski.

### Added
- `providerArgs` daje `codex` i `claude` kontrolę kosztu/jakości per rola, którą wcześniej miał tylko
  `agy`, i nadpisuje domyślne flagi runnera.
- `models` przyjmuje mapowanie per rola, więc etapy read-only mogą używać tańszego modelu niż etap
  implementacji.
- `roleProviders.integrator` kieruje rozwiązywanie uwag do dostawcy innego niż podstawowy.
- `skipFinalVerificationAtLow` (domyślnie true) zastępuje przy `LOW` autoweryfikację dostawcy
  podstawowego werdyktem niezależnego recenzenta, utrzymując trywialną zmianę na trzech wywołaniach modelu.
- `reuseBranchForFollowUp` kontynuuje pracę na bieżącym branchu `ai/` zamiast tworzyć kolejny.
- `ai-team resume <run-id> --extra-rounds N` otwiera ponownie ostatnią rundę recenzji.
- `ai-team runs` wypisuje każdy branch przebiegu ze statusem i informacją, czy nadal różni się od
  swojej bazy, oraz drukuje linię `git branch -d` dla tych, które się nie różnią. Runner nadal nigdy
  sam nie usuwa brancha.
- Prompty recenzji niosą jawne kryteria jakości i treść każdego projektowego SKILL.md, więc kryteria
  recenzji nie zależą już od tego, czy każde CLI samo odkryje skille.
- Recenzenci dostają wygenerowany `diff.patch` zamiast odtwarzać zmianę od zera.
- `.claude/skills/project/` jest instalowany i traktowany jako własność projektu, więc recenzenci
  Claude widzą skille projektowe, które wcześniej istniały tylko dla `agy`.
- Profile `postgres`, `geneteka` i `ocr` zasiewają `riskPaths` przy tworzeniu nowej konfiguracji.
- `doctor` zgłasza niewypełnione znaczniki TODO w `PROJECT_CONTEXT.md`; szablon prosi o konkretne
  pliki do naśladowania i do unikania.
- Scalanie zadań VS Code informuje, kiedy usunęło komentarze i gdzie jest kopia zapasowa.
- Oba prompty bootstrapu w `docs/BOOTSTRAP.md` zostały zaktualizowane pod nową powierzchnię
  konfiguracji; poprzednie brzmienie produkowało politykę `"LOW": []`, którą to wydanie odrzuca.
  Test sprawdza teraz, że obie wersje językowe pokrywają każde ustawienie krytyczne dla bootstrapu.
- `ai-team install . --lang pl` (oraz `update . --lang en`) instaluje polskie albo angielskie
  instrukcje agentów i skille. Każdy szablon ma teraz parę `.md`/`.pl.md`; projekt dostaje jeden
  język, nigdy oba. Wybór jest zapisywany w `.ai-team/state.json` i jako `language` w
  `ai-team.config.json`, a runner formułuje własne prompty etapów i kontrakt werdyktu w tym samym
  języku, więc przebieg nigdy nie miesza obu.
- Każdy dokument dla ludzi ma odpowiednik `.pl.md` z przełącznikami języka w obie strony. Test
  pilnuje istnienia odpowiednika, linków przełączających i zgodnej struktury nagłówków, więc
  tłumaczenie nie zostanie po cichu w tyle za oryginałem.

### Migration
- `reviewPolicy.LOW` musi wskazać recenzenta. `[]` zachowasz tylko dodając `"allowUnreviewedLowRisk": true`.
- Usuń `availabilityFallback` z `antigravity`, jeśli tam jest; nieznane klucze w tej sekcji są
  teraz odrzucane. Klucz najwyższego poziomu nadal jest przyjmowany i nadal ignorowany.
- Polecenia weryfikacji wywołujące wrapper powłoki wymagają `"allowShellWrapper": true`.
- Jeżeli Twoje CLI dostawców uwierzytelniają się przez zmienne środowiskowe, dopisz je do
  `passthroughEnv` — inaczej przebieg padnie na uwierzytelnianiu.
- Etapy weryfikatora i recenzenta `agy` domyślnie używają wysiłku `medium`, a nie `high`. Ustaw
  `antigravity.verificationEffort` na `high`, aby zachować poprzednie zachowanie.

---

## [Unreleased]

### Fixed
- Zachowanie istniejących instrukcji AI i lokalnych zmian przy powtórnych instalacjach i konfliktowych aktualizacjach.
- Utrzymanie wycofanych szablonów pod kontrolą wersji; normalizacja operacji projektowych do katalogu głównego Git.
- Scalanie zadań JSONC VS Code na bazie linii bazowych własności z zachowaniem wpisów użytkownika.
- Błędy wymaganych recenzentów, brakujący recenzenci, nieudane testy i niepoprawne werdykty nie pozwalają już zakończyć przebiegu sukcesem.
- Tworzenie unikalnego brancha dla każdego przebiegu, także gdy start następuje na istniejącym branchu `ai/`.

### Added
- Jawne rozwiązywanie konfliktów (`resolve --strategy keep|upstream`), migracja profili, lista profili i wersja CLI.
- Walidowany wybór dostawcy (`agy`, `codex`, `claude`), ustrukturyzowane wyniki, eskalacja ryzyka na podstawie zmienionych ścieżek i ograniczone rundy recenzji.
- Bezpośrednie polecenia weryfikacji z katalogami roboczymi i timeoutami, zapisane kody wyjścia i `result.json`.
- Rozszerzona diagnostyka gotowości, opcjonalne sondy CLI, testy regresji i dwujęzyczne prompty bootstrapu.
- `ai-team resume <run-id>|latest` kontynuuje przerwany przebieg, pomijając ukończone etapy agentów i recenzji, po sprawdzeniu, że branch nadal się zgadza.
- Filtrowane środowiska podprocesów (usunięte zmienne wyglądające na sekrety, znacznik `AI_TEAM_SUBPROCESS`) i izolacja grupy procesów dla każdego uruchamianego CLI i polecenia weryfikacji.

### Migration
- Istniejąca konfiguracja projektu jest zachowywana. Przed uruchomieniem dodaj `verification.commands` albo udokumentowane `verification.noChecksReason`.
- Polityki recenzji wymagają jednego niezależnego dostawcy dla MEDIUM i dwóch dla HIGH; fallback dostępności nie pozwala już zakończyć sukcesem.
- Etapy decyzyjne agentów muszą zwracać format JSON opisany w `docs/ARCHITECTURE.md`.

## [3.0.1] - 2026-09-11

### Added
- Trwałe manifesty przebiegów, bezpieczne wznawianie nieudanych i oczekujących etapów, zredagowane ślady JSONL i atomowe artefakty ewaluacji. Wznowienie odmawia działania przy zmienionym branchu/bazie albo brudnym drzewie i wymaga zapisanych danych wejściowych.
- Filtrowane środowiska podprocesów z jawnym znacznikiem `AI_TEAM_SUBPROCESS` i sprawdzaniem granicy CWD repozytorium.
- Standardowa licencja MIT (`LICENSE`).
- Pełna dwujęzyczna dokumentacja (`README.md` po angielsku i `README.pl.md` po polsku) z przełącznikami języka.
- Dokumenty projektowe: `CONTRIBUTING.md`, `SECURITY.md` i `CHANGELOG.md`.
- Workflow CI GitHub Actions (`.github/workflows/ci.yml`) dla Ubuntu i Windows na Pythonie 3.10, 3.11, 3.12 i 3.13.
- Rozszerzony zestaw testów obejmujący cykl życia instalatora, profile, scalanie zadań VS Code, obsługę ścieżek na różnych platformach, routing runnera i `doctor` oraz domyślne ustawienia bezpieczeństwa.
- Rozszerzony `.gitignore` obejmujący cache Pythona, środowiska wirtualne, IDE, artefakty systemowe, sekrety i artefakty przebiegów AI.
- Konfiguracja pakowania w `pyproject.toml` z pełnymi metadanymi, adresami projektu i dołączaniem plików ukrytych w szablonach (`.agents`, `.claude`, `.vscode`).

### Changed
- Zastąpienie odwołań do prywatnego repozytorium publicznymi adresami HTTPS.
- Aktualizacja promptów bootstrapu projektu (EN i PL) pod publiczną dystrybucję.
- Ujednolicenie wersji pakietu w `pyproject.toml`, `VERSION` i `src/ai_team/__init__.py`.

### Removed
- Wycofanie statycznego `MANIFEST.txt` na rzecz deklaratywnego `package-data` w `pyproject.toml`.

---

## [3.0.0] - 2026-09-11

### Added
- Pierwsze wydanie AI Engineering Team v3.
- Wieloplatformowy orkiestrator CLI (`ai-team`) z poleceniami `install`, `update`, `status`, `doctor`, `run` i `uninstall`.
- Orkiestracja wieluagentowa integrująca Google Antigravity / Gemini CLI (`agy`), Anthropic Claude Code CLI (`claude`) i OpenAI Codex CLI (`codex`).
- Automatyczna klasyfikacja ryzyka (LOW / MEDIUM / HIGH) z niezależnymi ścieżkami recenzji między modelami.
- System instalacji oparty na profilach (`core`, `python`, `web`, `postgres`, `ocr`, `geneteka`, `full`).
- Szablony automatyzacji zadań VS Code i niedestrukcyjne zarządzanie konfiguracją z wykrywaniem konfliktów.
- Wsparcie dla Windows (PowerShell) i Linux (bash/zsh, VS Code Remote SSH).
