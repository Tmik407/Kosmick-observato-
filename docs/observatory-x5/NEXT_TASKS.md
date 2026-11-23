# NEXT TASKS — Kosmická observatoř X-5

Aktualizováno: 23. 11. 2026

## Priorita 1 — ověřit aktuální data
- [ ] Znovu načíst `space-weather-status.json` a zjistit, zda se Kp aktualizuje a jaký je jeho poslední platný čas.
- [ ] Porovnat Kp s oficiálním zdrojem NOAA SWPC; neprezentovat starý Kp jako aktuální.
- [ ] Prověřit poslední čas měření ACE/RTSW a ACE MAG a jejich časové párování.

## Priorita 2 — ověřit mapy a polární model
- [ ] Otestovat, zda mapový panel na hlavní observatoři skutečně vykresluje body / vrstvy.
- [ ] Prověřit NOAA GFS / Open-Meteo výstupy a archivní mapy.
- [ ] Ověřit, že samostatná stránka polárního víru načítá data a animace bez chyb.

## Priorita 3 — stabilita
- [ ] Projít poslední GitHub Actions běhy pro datové workflow a Pages deployment.
- [ ] Ověřit PWA manifest, service worker a offline fallback po posledních změnách.
- [ ] Zkontrolovat, že dočasně vypnuté starší skripty nezpůsobují neaktualizované panely.

## Pravidlo
Neoznačovat žádný úkol za hotový, dokud neexistuje odpovídající technický nebo uživatelský důkaz.
