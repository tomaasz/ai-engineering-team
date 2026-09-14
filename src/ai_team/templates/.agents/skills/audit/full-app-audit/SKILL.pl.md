---
name: full-app-audit
description: Kompleksowy audyt aplikacji 360° obejmujący architekturę, bezpieczeństwo OWASP, jakość kodu, testy, wydajność i gotowość DevOps.
---
# full-app-audit

Przeprowadź rygorystyczny, całościowy audyt 360° aplikacji w 6 kluczowych wymiarach inżynieryjnych.

## Wymiary audytu

### 1. Architektura i struktura kodu
- **Wzorce i granice domenowe**: Weryfikacja separacji odpowiedzialności (SoC), warstw architektonicznych i spójności modułów.
- **Dług technologiczny i antywzorce**: Identyfikacja klas/modułów typu „God object”, zależności cyklicznych, logiki spaghetti i duplikacji kodu.
- **Martwy i osierocony kod**: Wyszukiwanie nieużywanych exportów, przestarzałych funkcji pomocniczych, martwych endpointów i nieużywanych pakietów.

### 2. Bezpieczeństwo i podatności (OWASP Top 10 & CWE)
- **Sekrety i poświadczenia**: Skanowanie kodu pod kątem zaszytych kluczy API, tokenów, haseł, kluczy prywatnych lub plików `.env`.
- **Wstrzyknięcia (Injection)**: Weryfikacja parametryzacji zapytań SQL/NoSQL, wywołań powłoki (shell injection), podatności na SSTI i ReDoS.
- **Autentykacja i autoryzacja**: Weryfikacja cyklu życia tokenów, haszowania haseł (bcrypt/argon2), walidacji JWT, podatności IDOR/BOLA oraz kontroli ról (RBAC).
- **Ochrona danych i nagłówki HTTP**: Sprawdzenie sanityzacji wejścia/wyjścia, reguł CORS (zakaz `*` z poświadczeniami), CSP i nagłówków bezpieczeństwa.
- **Zależności i łańcuch dostaw**: Sprawdzenie znanych podatności CVE w zewnętrznych bibliotekach i integralności plików lock.

### 3. Niezawodność, obsługa błędów i przypadki brzegowe
- **Bezpieczeństwo wyjątków**: Wykrywanie wyciszanych błędów (`catch {}`, `except: pass`), nieobsłużonych odrzuceń obietnic (unhandled rejections) i braku propagacji błędów.
- **Współbieżność i wyścigi (Race conditions)**: Analiza współdzielonego stanu modyfikowalnego, pułapek w operacjach asynchronicznych i atomowości operacji.
- **Zarządzanie zasobami**: Wykrywanie niezamkniętych połączeń bazodanowych, otwartych deskryptorów plików, nieobsłużonych sygnałów systemu (SIGTERM/SIGINT) i wycieków pamięci.

### 4. Wydajność i dostęp do danych
- **Wzorce zapytań bazodanowych**: Identyfikacja problemu N+1 zapytań, brakujących indeksów na kluczach obcych i filtrach oraz zapytań bez stronicowania (pagination).
- **Pętla zdarzeń i wątki**: Weryfikacja, czy operacje blokujące CPU nie zamrażają pętli zdarzeń w środowiskach asynchronicznych (Node.js/asyncio).
- **Buforowanie i transfer**: Sprawdzenie strategii cache'owania oraz kompresji przesyłanych danych.

### 5. Testy i zapewnienie jakości (QA)
- **Luki w pokryciu**: Zidentyfikowanie krytycznych ścieżek biznesowych i autoryzacyjnych pozbawionych testów automatycznych.
- **Jakość testów**: Wykrywanie testów testujących wyłącznie mocki zamiast rzeczywistego zachowania; testowanie ścieżek negatywnych i błędów.

### 6. DevOps, konteneryzacja i produkcja
- **Higiena kontenerów**: Wielostopniowe budowanie Dockerfile (multi-stage), uruchamianie jako użytkownik nieuprzywilejowany (non-root), przypięte wersje obrazów bazowych.
- **Obserwowalność**: Strukturyzowane logowanie JSON, identyfikatory korelacji (correlation ID), brak logowania danych wrażliwych (PII), endpointy `/health` i `/ready`.
- **Zarządzanie konfiguracją**: Rygorystyczna walidacja zmiennych środowiskowych podczas startu aplikacji (fail-fast).

## Format wyjściowy raportu

Zapisz kompletny raport audytowy w `docs/AUDIT.md` (lub wskazanej ścieżce wyjściowej) wg poniższej struktury:

```markdown
# Raport Kompleksowego Audytu Aplikacji 360°

**Data audytu**: [YYYY-MM-DD]  
**Ocena ogólna zdrowia systemu**: [A / B / C / D / F] (Wynik: 0–100%)  
**Podsumowanie wykonawcze (Executive Summary)**: [2-3 zwięzłe akapity podsumowujące stan aplikacji, kluczowe ryzyka i zalecenia]

---

## Matryca Znalezisk

| ID | Obszar | Poziom ryzyka | Plik:Linia | Tytuł znaleziska | Rekomendowane działanie |
|---|---|---|---|---|---|
| SEC-01 | Bezpieczeństwo | KRYTYCZNY | src/auth.js:42 | Zaszyty na stałe klucz JWT | Przeniesienie do zmiennych środowiskowych z walidacją startową |
| ARC-01 | Architektura | ŚREDNI | src/db/repo.js:105 | Pętla N+1 zapytań przy pobieraniu użytkowników | Zastosowanie SQL JOIN lub batchingu (Dataloader) |

---

## Szczegółowa Analiza Znalezisk

### [SEC-01] Tytuł znaleziska
- **Poziom ryzyka**: KRYTYCZNY / WYSOKI / ŚREDNI / NISKI
- **Lokalizacja**: `sciezka/do/pliku.ext:L123`
- **Wpływ**: Szczegółowe wyjaśnienie zagrożenia, podatności na atak i konsekwencji biznesowych.
- **Dowód / Fragment kodu**: Fragment kodu ilustrujący problem.
- **Sposób naprawy**: Konkretny, minimalny kod naprawczy usuwający podatność.

---

## Plan Działań Naprawczych (Action Plan)
- **Faza 1 (Natychmiastowa / P0)**: Poprawki krytycznych luk bezpieczeństwa i ryzyka utraty danych.
- **Faza 2 (Krótkoterminowa / P1)**: Błędy o wysokim priorytecie, obsługa wyjątków, uzupełnienie brakujących testów.
- **Faza 3 (Średnioterminowa / P2)**: Refaktoryzacja architektoniczna, optymalizacja wydajności i redukcja długu technicznego.
```

