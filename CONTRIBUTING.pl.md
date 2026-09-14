# Współtworzenie AI Engineering Team

[English](CONTRIBUTING.md) · **Polski**

Dziękujemy za zainteresowanie rozwojem AI Engineering Team. Ten dokument opisuje zasady i instrukcje współtworzenia projektu.

---

## Zasady i reguły

- **Bezpieczeństwo przede wszystkim**: AI Engineering Team orkiestruje autonomicznych agentów AI, którzy uruchamiają lokalne polecenia i edytują kod. Każdy wkład musi utrzymywać ścisłe granice bezpieczeństwa (sandbox, bramki uprawnień, zero automatycznego push/deploy).
- **Wieloplatformowość**: każda funkcja, operacja na ścieżkach i zadanie musi działać tak samo na Windows i Linux (w tym VS Code Remote SSH). Zawsze używaj `pathlib.Path` i unikaj założeń specyficznych dla powłoki.
- **Minimum zależności**: pakiet podstawowy dąży do zera zależności runtime poza biblioteką standardową Pythona.

---

## Przygotowanie środowiska

### Wymagania

- Python 3.10+
- Git
- `pip` albo `pipx`

### Kroki

1. Sforkuj i sklonuj repozytorium:
   ```bash
   git clone https://github.com/tomaasz/ai-engineering-team.git
   cd ai-engineering-team
   ```

2. Utwórz i aktywuj środowisko wirtualne:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. Zainstaluj pakiet w trybie edytowalnym z zależnościami deweloperskimi:
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

---

## Uruchamianie testów

Do testów używamy `pytest`. Wszystkie testy jednostkowe mockują wywołania zewnętrznych CLI (`agy`, `claude`, `codex`) i nie wymagają aktywnych subskrypcji ani poświadczeń do modeli.

Uruchomienie zestawu testów:
```bash
pytest -v
```

Przed wysłaniem pull requesta upewnij się, że:
1. Wszystkie testy przechodzą w Twoim środowisku.
2. Nowe funkcje i poprawki mają odpowiadające im testy jednostkowe.
3. Build pakietu się udaje:
   ```bash
   python -m build
   ```

### Dokumentacja jest częścią testów

Zestaw testów pilnuje spójności dokumentacji z kodem, bo raz już się rozjechały:

- każdy klucz w `templates/ai-team.config.json` i w `antigravity` musi być opisany w `docs/CONFIGURATION.md`,
- obie wersje promptu w `docs/BOOTSTRAP.md` muszą pokrywać ustawienia krytyczne dla bootstrapu,
- każdy dokument dla ludzi potrzebuje odpowiednika `.pl.md` o tej samej strukturze nagłówków i z linkiem w drugą stronę,
- każdy szablon w `templates/` potrzebuje wariantu `.pl.md`.

Dodając opcję konfiguracji albo dokument, zaktualizuj obie wersje językowe w tym samym PR-ze.

---

## Branche i commity

### Nazewnictwo branchy

- Funkcje: `feature/<krótki-opis>`
- Poprawki: `fix/<krótki-opis>`
- Dokumentacja: `docs/<krótki-opis>`
- Przygotowanie wydania: `public-prep/<wersja>`

### Komunikaty commitów

Pisz jasne, zwięzłe komunikaty zgodne ze standardową konwencją:
```text
<typ>(<zakres>): <podsumowanie>

[opcjonalny opis]
```
Przykłady:
- `feat(installer): add support for custom template manifests`
- `fix(paths): normalize backslashes on Windows`
- `docs(readme): update quick start guide`
- `test(runner): add mock tests for triage risk evaluation`

Nigdy nie commituj sekretów, kluczy API, prywatnych poświadczeń ani lokalnych ścieżek środowiskowych.

---

## Proces pull requesta

1. Wypchnij zmiany na swój branch w forku.
2. Otwórz pull request na branch `main` w `tomaasz/ai-engineering-team`.
3. Podaj jasne podsumowanie zmian, uzasadnienie, wyniki testów i ewentualne kwestie bezpieczeństwa.
4. Upewnij się, że CI przechodzi w macierzy Ubuntu i Windows.
5. Odnieś się do uwag z review.
