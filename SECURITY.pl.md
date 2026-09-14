# Polityka bezpieczeństwa

[English](SECURITY.md) · **Polski**

## Wspierane wersje

| Wersja  | Wspierana          |
| ------- | ------------------ |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

---

## Zgłaszanie podatności

Traktujemy bezpieczeństwo AI Engineering Team poważnie. Jeżeli znajdziesz podatność, **nie ujawniaj jej w publicznym issue, dyskusji ani pull requeście.**

Aby zgłosić ją odpowiedzialnie:

1. **GitHub Security Advisories (zalecane)**: przejdź do zakładki [Security Advisories](https://github.com/tomaasz/ai-engineering-team/security/advisories) repozytorium i kliknij **„Report a vulnerability"**, aby złożyć zgłoszenie prywatne.
2. Jeżeli GitHub Security Advisories są niedostępne, skontaktuj się z opiekunami repozytorium prywatnym kanałem na GitHubie.

W zgłoszeniu podaj:
- opis podatności i jej potencjalny wpływ,
- kroki odtworzenia albo minimalny proof-of-concept,
- objęte komponenty oraz szczegóły systemu i środowiska.

Potwierdzenie otrzymasz w ciągu 48 godzin, a następnie informacje o postępach analizy i naprawy.

---

## Model bezpieczeństwa i obszary wrażliwe

AI Engineering Team jest orkiestratorem, który współpracuje z zewnętrznymi CLI modeli AI (Antigravity/Gemini CLI `agy`, Claude Code CLI `claude`, OpenAI Codex CLI `codex`) i zarządza lokalnymi katalogami roboczymi repozytorium.

### Lokalne wykonywanie poleceń
- Framework uruchamia agentów AI, którzy mogą generować, modyfikować i testować kod aplikacji na Twoim systemie.
- Agenci działają z uprawnieniami użytkownika lokalnego uruchamiającego CLI `ai-team`.

### Sandbox i uprawnienia
- Domyślnie Antigravity działa z `sandbox: true` i `fullAuto: false`.
- **Nie** włączaj `--dangerously-skip-permissions` ani `"fullAuto": true`, chyba że pracujesz w izolowanym kontenerze lub maszynie wirtualnej.
- Niezależni recenzenci (`claude`, `codex`) są wywoływani wyłącznie w trybach **read-only / plan-only** i nie mogą modyfikować plików źródłowych ani wykonywać operacji zmieniających stan.

### Bezpieczne domyślne ustawienia
- Framework **nigdy** nie wykonuje automatycznie `git push`, `git merge` ani wdrożenia.
- Praca jest izolowana na branchach przebiegu (`ai/...`), `main` pozostaje nietknięty.
- Przed zadaniem wymuszane jest czyste drzewo robocze (`requireCleanWorkingTree: true`).

### Informacje wrażliwe i sekrety
- Nigdy nie przekazuj prywatnych tokenów API, haseł, plików `.env` ani poświadczeń produkcyjnych do promptów agentów ani do commitów.
- Zadbaj, aby pliki `.gitignore` projektu wykluczały wszystkie formaty poświadczeń (`.env`, `*.pem`, `*.key`, `.ai/runs/`).
- Środowiska podprocesów są filtrowane: zmienne pasujące do wzorców poświadczeń, connection stringi (`_URL`, `_URI`, `_DSN`), gniazda agentów oraz stała lista odrzuceń (`KUBECONFIG`, `AWS_PROFILE`, ...) są usuwane. Usuwa to również klucze API dostawców; te, których potrzebują Twoje CLI, wypisz w `passthroughEnv`.
- **Filtrowanie środowiska to nie izolacja.** Agenci działają z uprawnieniami uruchamiającego użytkownika i mogą odczytać `~/.aws/credentials`, `~/.ssh/` oraz `.env` wprost z dysku. Gdy to istotne, użyj kontenera lub maszyny wirtualnej.

### Guardraile
- Pliki definiujące sposób recenzji zespołu (`ai-team.config.json`, `AI_TEAM.md`, `PROJECT_CONTEXT.md`, `.agents/**`, `.claude/**`) zawsze eskalują do ryzyka HIGH i nie mogą przejść bez recenzji.
- Zmiana `ai-team.config.json` w trakcie przebiegu przerywa ten przebieg.
- `verification.commands` wykonują się z uprawnieniami użytkownika. `argv[0]` przywracające powłokę jest odrzucane bez `allowShellWrapper`, ale dowolny interpreter w `argv[0]` nadal może wykonać dowolny kod: traktuj `ai-team.config.json` jako zaufaną, zrecenzowaną konfigurację.
