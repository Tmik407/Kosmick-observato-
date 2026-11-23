# KOSMICKÁ OBSERVATOŘ X-5 — hlavní karta projektu

Aktualizováno: 23. 11. 2026

## Identifikace
- Název: Kosmická observatoř X-5
- Repozitář: https://github.com/Tmik407/Kosmick-observato-
- Produkční web: https://tmik407.github.io/Kosmick-observato-/
- Hlavní stránka: `index.html`
- Jazyk: čeština
- Typ: webová observatoř a instalovatelná PWA

## Účel
Sledování kosmického počasí, slunečního větru, meziplanetárního magnetického pole, geomagnetické aktivity, sluneční rentgenové aktivity, polární záře a souvisejících atmosférických jevů.

## Hlavní moduly doložené v projektu a předchozí práci
- NOAA SWPC RTSW / ACE: rychlost a hustota slunečního větru, Bx/By/Bz/Bt a dynamický tlak.
- Geomagnetické indexy Kp a Dst, G1–G5 monitorovací panel.
- GOES rentgenové záření a diagnostika slunečních erupcí.
- Grafy, historické archivy a automatická upozornění.
- Kontrola kvality, čerstvosti a časového párování dat.
- Archiv a vizualizace polární záře / OVATION.
- GIRO, IRTAM a ionosférická data.
- SUVI a další solární datové zdroje.
- Samostatná stránka `polarni-vir.html` pro stratosférický polární vír.
- NOAA GFS a Open-Meteo mapové / modelové výstupy; hladiny 10, 30 a 50 hPa.
- PWA manifest, service worker, offline stránka a cache.

## Důležité soubory
- `index.html` — hlavní rozhraní observatoře.
- `manifest.webmanifest` — manifest hlavní PWA.
- `sw.js` — service worker a cache.
- `space-weather-status.json` — stav a aktuálnost zdrojů kosmického počasí.
- `polarni-vir.html` — samostatný model stratosférického polárního víru.
- `polarni-vir.webmanifest` — manifest stránky polárního víru.
- `gfs-polarni-3d.js`, `gfs-polarni-animace.js`, `gfs-vortex-comparison.js` — části modelování a vizualizace polárního víru.
- `data/` — datové archivy a výstupy modelů.
- `.github/workflows/` — automatizace a publikace dat / webu.

## Pravidla vývoje
1. Zachovat funkční části hlavní observatoře a samostatného modelu polárního víru.
2. Před úpravou vždy načíst aktuální verzi souboru a ověřit SHA.
3. Rozlišovat živé měření, archiv, reanalýzu a modelovou předpověď.
4. Neplatné hodnoty, sentinel hodnoty a zastaralé vzorky nikdy nevydávat za aktuální data.
5. Při časovém párování zachovat limity a pravidla kvality zavedená v kódu.
6. Po změně ověřit commit, běh workflow a dostupnost nasazení; zařízení testovat zvlášť.
7. Aktualizovat dokumentaci před předáním práce do nového chatu.

## Související dokumentace
- [Aktuální stav](SESSION_STATE.md)
- [Historie změn](CHANGELOG.md)
- [Další úkoly](NEXT_TASKS.md)
- [Testy a omezení](TESTS.md)
- [Centrální rozcestník X-5](../continuity/INDEX.md)
