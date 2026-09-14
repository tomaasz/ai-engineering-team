# Project Context

## Cel projektu
TODO

## Stack
TODO

## Główne komendy
Przy każdej komendzie zapisz katalog roboczy, wymagania, źródło w repo i status:
potwierdzona w konfiguracji / uruchomiona / niezweryfikowana.
Bezpieczne komendy kontroli skonfiguruj też w ai-team.config.json:
verification.commands = [{"argv":["program","argument"],"cwd":".","timeoutSeconds":300}].
Nie wpisuj migracji ani wdrożeń jako automatycznych kontroli.
Jeśli projekt nie ma kontroli automatycznych, uzasadnij verification.noChecksReason.
- install: TODO
- lint: TODO
- typecheck: TODO
- unit tests: TODO
- integration tests: TODO
- build: TODO

## Krytyczne obszary
TODO

## Obszary wymagające jawnej zgody przed zmianą
TODO

## Konwencje
TODO

## Wzorce do naśladowania
Wskaż 2-3 istniejące pliki, które najlepiej reprezentują docelowy styl projektu
(np. moduł domenowy, test, warstwa API). Model kopiuje styl z przykładów skuteczniej
niż z reguł opisowych. Dla każdego napisz, co dokładnie ma z niego przejąć.
- TODO: ścieżka — co naśladować
- TODO: ścieżka — co naśladować

## Czego nie naśladować
Wymień pliki lub obszary uznane za dług techniczny, których wzorca nie należy powielać.
TODO

## Komponenty monorepo
Wymień komponenty, katalogi, stacki i powiązane komendy; dla pojedynczego projektu: nie dotyczy.

## Definition of Done
Wymaganie spełnione, wymagane recenzje zakończone, kontrole mają kod 0,
brak nierozwiązanych BLOCKER/HIGH. Brak testów musi być jawnie uzasadniony.
