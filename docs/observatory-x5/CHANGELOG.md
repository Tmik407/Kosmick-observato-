# CHANGELOG — Kosmická observatoř X-5

## 2026-11-23 — Zavedení kontinuity projektu
- Přidána samostatná dokumentace observatoře X-5.
- Zaznamenána architektura hlavní stránky, PWA, stavových metadat a stránky polárního víru.
- Zaznamenány dříve řešené problémy a opatrnost při jejich opětovném ověřování.
- Při kontrole souboru `space-weather-status.json` byl ve snapshotu Kp označen jako stale_or_missing; vítr a magnetické pole jako fresh.

## Dřívější vývoj — souhrn z projektových záznamů
- Přidány / rozvíjeny NOAA SWPC RTSW, ACE MAG, IRTAM, OVATION, CH1411, GIRO a SUVI datové toky a archivy.
- Přidána diagnostika `space-weather-status.json`, integrita archivů a ochrana proti zastaralým datům.
- Rozvíjen samostatný stratosférický model polárního víru včetně NOAA GFS / NASA datových výstupů a animace.
- PWA rozšířena o cache a offline stránku.
- V minulých etapách opravovány panely a skripty včetně chování `activeOnly`; uživatel následně potvrdil funkčnost na tabletu.

## Pravidla zápisu
Každá další položka musí obsahovat datum, soubory, důvod, výsledek testu a stav nasazení. Historické shrnutí není náhradou úplné Git historie.
