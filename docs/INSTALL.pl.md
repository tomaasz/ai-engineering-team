# Instalacja

[English](INSTALL.md) · **Polski**

## Centralne CLI

Zainstaluj Pythona 3.10+, Git i `pipx`, a potem wersję, którą sprawdziłeś:

```bash
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@<sprawdzony-commit-lub-wydanie>"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.3.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.4.0"
pipx install "git+https://github.com/tomaasz/ai-engineering-team.git@v4.5.0"
ai-team --version
```

Nie przedstawiaj istniejącego taga jako zawierającego niewydane zmiany z bieżącej gałęzi. Przypnij zrecenzowany commit albo wydanie z niego utworzone. Aktualizacja CLI i aktualizacja szablonów projektu to osobne czynności:

```bash
pipx upgrade ai-engineering-team
ai-team update /sciezka/do/projektu
```

Do pracy lokalnej użyj `./install-local.sh` na Linuksie albo `.\install-local.ps1` na Windows.

## Konfiguracja projektu

```bash
ai-team profiles
ai-team install . --auto --lang pl
# lub z jawnym profilem:
ai-team install . --profile core --lang pl
```

Dostępne profile to `core`, `python`, `web`, `postgres`, `ocr`, `geneteka` i `full`. Profil wybiera szablony i skille; nie wykrywa stacku ani nie dowodzi poprawności komend.
Dostępne profile to `core`, `python`, `web`, `postgres`, `ocr`, `geneteka` i `full`. Flaga `--auto` automatycznie analizuje sygnatury repozytorium i dobiera zalecany profil.

`--lang` wybiera język instalowanych instrukcji agentów i skilli (`en` domyślnie albo `pl`). Do projektu trafia tylko jedna wersja językowa, a runner formułuje własne prompty etapów w tym samym języku, więc żaden przebieg nie niesie dwóch wersji naraz. Wybrany język zapisuje się w `.ai-team/state.json` oraz jako `language` w `ai-team.config.json`; `ai-team update . --lang en` przełącza oba naraz.

Instalacja zachowuje istniejące pliki. Przy kolizji zostawia kopię projektu, odkłada przychodzący szablon w `.ai-team/conflicts/<ścieżka>` i zapisuje konflikt. Konfiguracja lokalna (`PROJECT_CONTEXT.md`, `ai-team.config.json` oraz `.agents/skills/project/` i `.claude/skills/project/`) jest zachowywana przy aktualizacjach.

```bash
ai-team status .
ai-team resolve . AGENTS.md --strategy keep
# albo
ai-team resolve . AGENTS.md --strategy upstream
```

`keep` przyjmuje plik projektu. `upstream` instaluje odłożony szablon. Żadna opcja nie wykonuje scalenia semantycznego; najpierw porównaj obie kopie.

Zadania VS Code scalane są po identyfikatorach. Komentarze JSONC i przecinki końcowe są odczytywane, ale udane scalenie tworzy kopię zapasową i zapisuje znormalizowany JSON, więc formatowanie i komentarze mogą zniknąć — instalator to zgłasza.

Profil zmienisz przy aktualizacji: `ai-team update . --profile web`. Pliki wycofane przez mniejszy profil mogą pozostać śledzone aż do `uninstall`; przejrzyj je przy zmianie profilu.

## Automatyzacja aktualizacji i higiena Git

Aby zautomatyzować aktualizacje szablonów w pipeline CI, zainstaluj workflow GitHub Actions:
```bash
ai-team workflow .
```
Polecenie to tworzy plik `.github/workflows/ai-team-update.yml`, który automatycznie tworzy cotygodniowe Pull Requesty z aktualizacjami.

Aby skonfigurować reguły ignorowania Git:
```bash
# Ignorowanie logów uruchomień i konfliktów w .gitignore:
ai-team gitignore .

# Lub tryb prywatny (tylko w .git/info/exclude):
ai-team gitignore . --private
```

## Gotowość

Uzupełnij `PROJECT_CONTEXT.md` — `doctor` zgłasza pozostawione `TODO` jako problem — i skonfiguruj realne komendy weryfikacji albo jawny `noChecksReason`. Jeżeli CLI dostawców uwierzytelniają się zmiennymi środowiskowymi, wypisz te zmienne w `passthroughEnv`; runner domyślnie usuwa ze środowiska podprocesów zmienne wyglądające na poświadczenia. Przejrzyj i zatwierdź zmiany instalacyjne. Przy ustawieniach domyślnych `run` wymaga czystego drzewa roboczego, pierwszego commita i braku nierozwiązanych konfliktów.

```bash
ai-team doctor . --probe
```

`doctor` sprawdza konfigurację, stan Git, ścieżki programów, konflikty, obecność weryfikacji i nieuzupełnione `TODO` w `PROJECT_CONTEXT.md`. `--probe` uruchamia tylko `--help` CLI. Nie potwierdza logowania, poświadczeń, dostępności modelu, limitu, dostępu do sieci ani uprawnień. Zanim uznasz gotowość, wykonaj nieszkodliwe prawdziwe żądanie u każdego skonfigurowanego dostawcy.

Instalacje przez Remote SSH wymagają `ai-team` i CLI dostawców zainstalowanych na zdalnym hoście.
