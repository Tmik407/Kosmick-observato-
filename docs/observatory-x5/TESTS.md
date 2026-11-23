# TESTS — Kosmická observatoř X-5

Aktualizováno: 23. 11. 2026

| Oblast | Stav | Poznámka |
|---|---|---|
| Hlavní GitHub Pages web | DŘÍVE NASAZENO | Produkční adresa je známá; před další změnou znovu ověřit poslední deployment. |
| Základní ovládání na tabletu | POTVRZENO UŽIVATELEM V PŘEDCHOZÍ ETAPĚ | Po opravách uživatel uvedl, že funguje. |
| PWA / offline | IMPLEMENTOVÁNO, ČÁSTEČNĚ OVĚŘENO | Manifest, service worker a offline stránka jsou v repozitáři; úplný offline test není v této etapě doložen. |
| NOAA vítr | STATUS SNAPSHOT FRESH | Ve status JSON 23. 11. 2026 11:52 UTC; při další práci načíst znovu. |
| ACE MAG | STATUS SNAPSHOT FRESH | Ve status JSON 23. 11. 2026 11:52 UTC; při další práci načíst znovu. |
| Kp | VAROVÁNÍ — ZASTARALÝ SNAPSHOT | Ve status JSON poslední měření 06:00 UTC, stav stale_or_missing. Nutno ověřit aktuálně. |
| Dst | NEOVĚŘENO V TÉTO ETAPĚ | Nutná kontrola aktuálního zdroje a časové značky. |
| Mapový panel | NEOVĚŘENO | Historicky hlášena prázdná mapa; po dřívějších opravách vyžaduje nový test. |
| Polární vír — stránka a animace | NEOVĚŘENO V TÉTO ETAPĚ | Kód i stránka existují; živý test vykreslení nebyl v této etapě proveden. |
| Automatizace / GitHub Actions | NEOVĚŘENO V TÉTO ETAPĚ | Před další změnou zkontrolovat poslední běhy. |

## Kvalita dat — povinné kontroly
- Ověřit časovou značku a věk každého zdroje.
- Odmítnout neplatné ACE řádky (`S ≠ 0`) a sentinel hodnoty `-999.x`.
- Zachovat časový limit párování 90 sekund, pokud aktuální implementace a datový kontext nepotvrdí jinou specifikaci.
- Odlišit aktuální měření, historický archiv, reanalýzu a předpověď.
- Při chybě zdroje zobrazit stav nedostupnosti / zastaralosti, ne starou hodnotu jako aktuální.

## Evidence
Před každým testem zapsat datum, zdroj, poslední čas měření, postup a výsledek.
