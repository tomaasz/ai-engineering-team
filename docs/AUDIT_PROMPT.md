# Framework audit prompt

Paste the prompt below to a fresh coding agent (Claude Code, Codex, or Antigravity) run at the root of this repository to get a critical, evidence-based audit of whether this framework actually delivers on its goals: efficient vibecoding, security, cost/performance optimality, code ergonomics, and sensible task distribution across LLM models.

```text
Przeprowadź krytyczny, dowodowy audyt frameworka "AI Engineering Team" (to repozytorium: src/ai_team/, docs/, README.md, templates/, profiles/). Celem frameworka jest orkiestracja wielu CLI modeli LLM (agy/Antigravity, codex, claude) do samodzielnego implementowania i recenzowania zmian w kodzie ("vibecoding" — rozwój aplikacji sterowany promptami, z minimalnym ręcznym nadzorem).

ZASADA NACZELNA: Nie ufaj opisom w README.md / docs/*.md na słowo. Dla każdego twierdzenia w dokumentacji znajdź odpowiadający mu kod i sprawdź, czy faktycznie tak działa (dokumentacja i kod już raz się rozjechały w tym repo po nieudanym merge — nie zakładaj, że są zsynchronizowane). Cytuj plik:linia jako dowód dla każdego ustalenia.

Zbadaj kod źródłowy w szczególności: src/ai_team/runner.py (pipeline uruchomienia), src/ai_team/installer.py, src/ai_team/config.py, src/ai_team/cli.py, profiles/*.json, templates/ai-team.config.json, templates/AI_TEAM.md, templates/AGENTS.md, templates/PROJECT_CONTEXT.md oraz zawartość .agents/skills/**/SKILL.md.

Oceń framework w pięciu wymiarach. Dla każdego: werdykt (mocne/słabe/krytyczne), konkretne dowody z kodu, i **wykonalna rekomendacja** (nie ogólnik typu "dodać testy" — podaj co dokładnie zmienić i gdzie).

1. WYDAJNOŚĆ DLA VIBECODINGU (szybka, iteracyjna praca)
   - Ile realnych "przystanków"/tarcia wprowadza pipeline (triage -> implementacja -> risk escalation -> recenzje -> integracja -> weryfikacja finalna -> checks) dla trywialnej zmiany (LOW risk, 1 plik)? Czy LOW naprawdę omija recenzje, czy nadal przechodzi przez wszystkie etapy triage/finalnej weryfikacji niezależnie od rozmiaru zadania?
   - `requireCleanWorkingTree` + branch-per-run (`ai/<run-id>`) - czy to ułatwia, czy utrudnia szybkie iterowanie w typowym flow "vibecodingowym" (częste małe commity, eksperymenty)?
   - `ai-team resume` jest manualny, nie automatyczny (potwierdzone w ARCHITECTURE.md) - jak duże jest ryzyko utraty kontekstu/pracy przy przerwaniu długiego runu (agentTimeoutSeconds do 3600s, runTimeoutSeconds do 14400s)?
   - Czy błąd w jednym z etapów (np. malformed JSON od reviewera, brakujący CLI) daje developerowi jasną, actionable informację, czy tylko surowy wyjątek?

2. BEZPIECZEŃSTWO
   - `_sanitized_env()` w runner.py filtruje zmienne env po regexie `KEY|TOKEN|SECRET|PASSWORD|PASS|COOKIE|CREDENTIAL` - znajdź realne przykłady nazw zmiennych środowiskowych (AWS, GCP, DB connection stringi, niestandardowe nazwy sekretów), które ten regex by przepuścił.
   - Recenzje są "read-only" i mają być niezależne, ale ARCHITECTURE.md samo przyznaje: "share one repository... not container or host isolation" - jak realnie reviewer mógłby ominąć read-only mode i wpłynąć na wynik (np. przez pliki tymczasowe, race condition, wspólny working tree)?
   - Weryfikacja komend (`verification.commands`) odpala argv bez shella (dobre - brak injection przez shell), ale sprawdź: czy da się przekazać niebezpieczny argv (np. rm, curl | sh) bez żadnej walidacji semantycznej - czy framework w ogóle próbuje to ograniczać, czy pełne zaufanie do configu?
   - Risk escalation (`_risk()` w runner.py) opiera się na dopasowaniu nazw plików do glob-ów (`*auth*`, `*secret*`, itd.) - podaj min. 5 konkretnych, realistycznych ścieżek plików z wrażliwą logiką (np. middleware autoryzacji bez słowa "auth" w nazwie, endpoint płatności w generycznie nazwanym pliku), które nie zostałyby wykryte jako HIGH/MEDIUM.
   - `availabilityFallback: false` blokuje "fałszywy sukces" gdy brakuje reviewera - sprawdź czy w kodzie faktycznie nie ma żadnej ścieżki, która mogłaby to obejść.
   - Timeout „targetuje bezpośredni proces" i nie gwarantuje sprzątania procesów potomnych na każdej platformie (przyznane w ARCHITECTURE.md) - jakie jest realne ryzyko (zombie procesy, agent nadal piszący do repo po timeout runnera)?

3. OPTYMALNOŚĆ / KOSZT / WYDAJNOŚĆ
   - Framework jawnie nie ma żadnego liczenia tokenów/kosztów (ARCHITECTURE.md: "There is no token or cost accounting"). Oszacuj: dla zadania HIGH risk, ile pełnych wywołań modeli LLM minimum się odpala (triage + implementacja + 2 recenzentów + ewentualna integracja + finalna weryfikacja) i co to oznacza kosztowo/czasowo względem bezpośredniej pracy z jednym agentem bez frameworka.
   - `primaryProvider` robi WSZYSTKO: triage, implementację, integrację po recenzjach, finalną weryfikację (widoczne w `_execute()` w runner.py). Czy nie warto rozdzielić tanich/szybkich etapów (triage, finalna weryfikacja - oba "read-only") na tańszy/szybszy model niż ten używany do właściwej implementacji? Sprawdź czy `config.models`/`effort` w ogóle na to pozwala per-etap, czy tylko per-provider globalnie.
   - `antigravity.triageEffort/implementationEffort/verificationEffort` istnieje tylko dla providera `agy` (zobacz `_agy()` w runner.py) - czy `codex`/`claude` mają analogiczną kontrolę kosztu/jakości, czy nie (sprawdź `_command()`)? Jeśli nie - to luka w konfigurowalności dla 2 z 3 providerów.
   - `maxReviewRounds` (domyślnie 2) - czy przy jego wyczerpaniu framework marnuje całą dotychczasową pracę (przerywa z błędem), czy da się to bezpiecznie kontynuować/dociągnąć ręcznie?

4. ERGONOMIA I JAKOŚĆ GENEROWANEGO KODU
   - Przeczytaj VERDICT_PROMPT i prompty recenzenckie w runner.py - recenzent ma zwrócić tylko `verdict/unresolved/summary`. Czy prompt w ogóle instruuje model, PO CZYM ma oceniać jakość (prostota, czytelność, brak nadmiarowej abstrakcji, spójność ze stylem projektu), czy tylko "czy działa"? Sprawdź `.agents/skills/core/code-review/SKILL.md` i `python-quality/SKILL.md` - czy te skille faktycznie są ładowane/wskazywane recenzentowi w trakcie runu, czy istnieją tylko jako pliki nigdy nieodwoływane przez runner.py.
   - `AI_TEAM.md`/`AGENTS.md`/`PROJECT_CONTEXT.md` (krótkie pliki, odpowiednio ~40/4/37 linii) - czy dają wystarczający kontekst architektoniczny/stylistyczny, żeby model pisał kod spójny z resztą projektu, czy są zbyt ogólne?
   - VS Code JSONC merge "może usuwać komentarze" (przyznane w ARCHITECTURE.md) - jak duże praktyczne ryzyko utraty user-owned konfiguracji to niesie przy `ai-team update`?

5. PODZIAŁ ZADAŃ MIĘDZY MODELE LLM
   - Obecny podział to: jeden "primary" robi całą pracę merytoryczną (triage+implementacja+integracja+weryfikacja), a "reviewery" tylko czytają i wydają werdykt. Czy to sensowny podział ról między modelami o różnych mocnych stronach (np. jeden model lepszy w kodowaniu, inny w wychwytywaniu błędów), czy tylko "jeden robi, dwóch sprawdza" bez realnego wykorzystania różnic w możliwościach modeli?
   - `reviewPolicy` wymusza, że primary nie może recenzować własnej pracy (dobre), ale nic nie broni użycia tego samego dostawcy/modelu dla LOW co dla samodzielnej pracy bez żadnej drugiej opinii - jak duże jest ryzyko "ślepych plamek" jednego modelu przy zadaniach LOW/MEDIUM z jednym reviewerem?
   - Czy framework w ogóle różnicuje, JAKI model/provider nadaje się do jakiego RODZAJU zadania (np. refaktoryzacja vs. nowa funkcjonalność vs. bugfix vs. praca z bazą danych/OCR/genealogią - profile w profiles/*.json), czy dobór modelu jest statyczny niezależnie od typu pracy?

FORMAT RAPORTU:
Dla każdego z 5 wymiarów: 2-5 ustaleń, każde z: [WERDYKT: mocne/słabe/krytyczne] opis (1-2 zdania) -> dowód (plik:linia lub cytat z configu) -> rekomendacja (konkretna zmiana kodu/configu). Na końcu: 3 najważniejsze rzeczy do naprawienia PRZED użyciem tego frameworka produkcyjnie do realnego rozwoju aplikacji, posortowane wg ryzyka.
```
