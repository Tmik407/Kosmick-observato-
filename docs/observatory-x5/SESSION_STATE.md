# SESSION STATE — Kosmická observatoř X-5

Aktualizováno: 23. 11. 2026

## Poslední známý stav
- Hlavní web je publikován na GitHub Pages.
- Uživatel v předchozích etapách potvrdil funkčnost na tabletu po opravách a úspěšném nasazení.
- Hlavní stránka obsahuje živé panely pro sluneční vítr, IMF, Kp, GOES, Dst, geomagnetické riziko a analytické diagnostiky.
- Veřejný status JSON poskytuje metadata o stáří a dostupnosti datových zdrojů.
- PWA má manifest, service worker, offline stránku a cache.
- Samostatný model polárního víru je na `polarni-vir.html`.

## Poslední konkrétní kontrola statusu dat
Při načtení `space-weather-status.json` dne 23. 11. 2026 byl uveden čas vytvoření 11:52:52 UTC:
- sluneční vítr: poslední měření 11:47 UTC, status fresh;
- magnetické pole: poslední měření 11:48 UTC, status fresh;
- Kp: poslední měření 06:00 UTC, status stale_or_missing (limit čerstvosti 240 minut).
Jde o konkrétní snapshot při kontrole souboru, nikoli o trvalý stav ani současný živý odečet. Při další práci načíst aktuální JSON znovu.

## Známé / dříve řešené technické oblasti
- Neplatné ACE vzorky: kontrolovat příznak kvality `S` a sentinel hodnoty typu `-999.x`.
- Časové párování magnetometru a slunečního větru: dříve stanovený maximální rozdíl 90 sekund.
- Izolované skoky rychlosti větru: filtrovat / označit, neinterpretovat automaticky jako fyzikální událost.
- Kp a JavaScript: v minulosti byla řešena chyba výpočtu / zpracování.
- GitHub Pages 404: dříve opravováno; po změně ověřit aktuální deployment.
- Polární mapový panel: v dřívější etapě zůstával prázdný; následovaly opravy CSV čtení a JavaScriptu. Nutno znovu ověřit aktuální stav, než se označí za vyřešený.
- Některé starší skripty byly dočasně vypnuty, což mohlo zanechat neaktualizované datové panely. Před opravou ověřit současnou architekturu.

## Bezpečný bod pokračování
Neprovádět plošný refaktor. Nejdříve znovu načíst aktuální statusy, workflow a dotčené části kódu. Prioritně ověřit čerstvost Kp a funkčnost mapového panelu.

## Pokyn pro nový chat
„Pokračujeme v projektu Kosmická observatoř X-5. Načti docs/observatory-x5/PROJECT_MASTER.md, SESSION_STATE.md, CHANGELOG.md, NEXT_TASKS.md a TESTS.md. Ověř aktuální stav dat a GitHub Actions. Zachovej funkční části, neprováděj plošný refaktor a pokračuj od nejbližšího otevřeného úkolu.“
