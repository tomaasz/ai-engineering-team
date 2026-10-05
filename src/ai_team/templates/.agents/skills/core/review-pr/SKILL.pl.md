---
name: review-pr
description: Dowodowy, dwufazowy audyt PR i weryfikacja krzyżowa w czystym oknie kontekstowym.
---
# review-pr

Dwufazowy, bezstronny audyt PR i weryfikacja krzyżowa przez niezależny model.

## Procedura
1. **Izolacja kontekstu**: Wyczyść pamięć sesji (`/clear` w sesji interaktywnej lub uruchomienie w trybie izolowanym `--bare`/`--ephemeral`). Nigdy nie weryfikuj kodu z uprzedzeniami twórcy (antywzorzec „grading own homework”).
2. **Pobranie diffu**: Pobierz diff zmian z PR lub gałęzi względem bazy za pomocą `gh pr diff` lub `git diff base...HEAD`.
3. **Krzyżowy audyt adwersarialny**: Uruchom niezależny model recenzencki (Codex, Claude lub agenta independent-reviewer), aby zbadać:
   - Poprawność, regresje i ciche błędy logiczne
   - Bezpieczeństwo, wycieki sekretów i podatności OWASP
   - Przypadki brzegowe, wyścigi współbieżności i wycieki zasobów
   - Luki w testach i brakujące asercje
4. **Struktura znalezisk**: Każda uwaga musi zawierać: Poziom (CRITICAL, HIGH, MEDIUM, LOW), Lokalizację (plik:linia), Problem, Wpływ, Minimalną poprawkę.
5. **Pętla Self-Healing**: Identyfikuj powtarzające się wzorce błędów i zgłaszaj aktualizacje do reguł projektu (`CLAUDE.md`, skilli, linterów).
