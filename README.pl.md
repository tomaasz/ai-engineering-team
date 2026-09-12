# AI Engineering Team

AI Engineering Team instaluje w istniejącym repozytorium Git workflow agentów niezależny od dostawcy. Jedno CLI implementuje zmiany, a inne CLI recenzują pracę średniego i wysokiego ryzyka. Runner zapisuje odpowiedzi modeli, wykonane testy i końcowy status w `.ai/runs/<run-id>/`.

Głównym dostawcą (`primaryProvider`) może być `agy`, `codex` albo `claude`. Nie może on recenzować własnej pracy. `MEDIUM` wymaga co najmniej jednego innego dostawcy, a `HIGH` co najmniej dwóch.

## Szybki start

Wymagane są Python 3.10+, Git, CLI głównego dostawcy i wszystkie skonfigurowane CLI recenzentów.

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@<sprawdzony-commit-lub-wydanie>"
cd /sciezka/do/projektu
ai-team install . --profile python
```

Nie zakładaj, że istniejący tag `v3.0.1` zawiera zachowanie opisane dla bieżącej gałęzi. Przypnij commit albo wydaną wersję po sprawdzeniu jej źródeł.

Uzupełnij `PROJECT_CONTEXT.md` i `ai-team.config.json`, rozwiąż konflikty instalacji, a potem zatwierdź konfigurację w Git. Typowy przebieg wymaga pierwszego commita i czystego drzewa roboczego.

```bash
ai-team doctor . --probe
ai-team run . "Dodaj eksport CSV i testy"
```

`doctor` sprawdza konfigurację statyczną i obecność programów. `--probe` uruchamia ich `--help`; nie potwierdza logowania, dostępu do modelu, limitu ani możliwości wykonania prawdziwego żądania. Sprawdź je bezpośrednio u każdego dostawcy.

## Polecenia

```text
ai-team --version
ai-team profiles
ai-team install <projekt> --profile <nazwa>
ai-team update <projekt> [--profile <nazwa>]
ai-team resolve <projekt> <plik> --strategy keep|upstream
ai-team status <projekt>
ai-team doctor <projekt> [--probe]
ai-team run <projekt> "<zadanie>"
ai-team resume <run-id>|latest <projekt>
ai-team uninstall <projekt> [--dry-run]
```

`update --profile` zmienia profil. Szablony wyłączone z mniejszego profilu mogą pozostać śledzone aż do `uninstall`; przejrzyj je ręcznie.

Instalator zachowuje istniejące pliki. Nowe szablony trafiają do `.ai-team/conflicts/` do czasu jawnego rozwiązania:

```bash
ai-team resolve . AGENTS.md --strategy keep
ai-team resolve . AGENTS.md --strategy upstream
```

`keep` akceptuje kopię projektu, a `upstream` instaluje odłożony szablon. Najpierw sprawdź różnice. JSONC VS Code jest odczytywany, lecz scalanie zapisuje znormalizowany JSON i kopię zapasową, więc komentarze i formatowanie mogą się zmienić.

## Weryfikacja i wyniki

Rzeczywiste testy zapisuj jako tablice argumentów z katalogiem roboczym i limitem czasu. Runner nie zgaduje poleceń powłoki.

```json
{"verification":{"commands":[{"argv":["python","-m","pytest"],"cwd":".","timeoutSeconds":600}]}}
```

Gdy nie istnieje bezpieczny test automatyczny, ustaw niepuste `verification.noChecksReason`. Taki przebieg może zakończyć się tylko jako `PASS_WITH_NOTES`. Brak recenzenta, błąd recenzji, niepoprawny JSON, nieudany test, nierozwiązane uwagi lub błąd kontroli diffu nie mogą stać się sukcesem przez fallback.

Etapy decyzyjne zwracają ustrukturyzowany JSON. `.ai/runs/<run-id>/result.json` jest głównym podsumowaniem; pozostałe pliki zawierają prompty, odpowiedzi, stdout i stderr.

Runner wymusza `agentTimeoutSeconds`, `runTimeoutSeconds` i `maxReviewRounds`. Obecnie nie mierzy tokenów ani kosztu i nie wznawia automatycznie przebiegu. Timeout dotyczy bezpośredniego procesu i na części platform może nie zakończyć wszystkich procesów potomnych.

## Bootstrap i dokumentacja

Krótka instrukcja dla agenta:

```text
Zainstaluj i skonfiguruj AI Engineering Team w tym repozytorium zgodnie z docs/BOOTSTRAP.md. Najpierw przeanalizuj repozytorium, zachowaj istniejące pliki, wybierz profil i polecenia weryfikacji potwierdzone przez projekt oraz podaj AI_TEAM_READY dokładnie według definicji z dokumentu.
```

- [Prompty bootstrap](docs/BOOTSTRAP.md)
- [Instalacja](docs/INSTALL.md)
- [Konfiguracja](docs/CONFIGURATION.md)
- [Architektura](docs/ARCHITECTURE.md)

Recenzenci używają trybów tylko do odczytu i kontroli zmian plików, ale wszyscy pracują na tym samym repozytorium. Ich izolacja częściowo zależy od promptów i nie jest oddzielną granicą systemową. Eskalacja ryzyka korzysta z nazw plików i globów; jest heurystyką i wymaga konserwatywnych reguł w projektach wrażliwych.
