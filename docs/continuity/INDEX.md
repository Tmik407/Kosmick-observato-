# X-5 CONTINUITY SYSTEM — centrální rozcestník

Aktualizováno: 23. 11. 2026

Tento systém slouží k předávání dlouhodobých projektů mezi chaty bez opakovaného vysvětlování historie.

## Aktivní projektové záznamy

| Projekt | Umístění dokumentace | Stav |
|---|---|---|
| POLAR VORTEX 3D X-5 | [Projektová karta](PROJECT_MASTER.md) | Založeno; funkčnost PWA potvrzena uživatelem |
| Kosmická observatoř X-5 | [Projektová karta observatoře](../observatory-x5/PROJECT_MASTER.md) | Dokumentace založena; další úkoly a testy evidovány |
| OPERATION X-5 | [Projektová karta](../operation-x5/PROJECT_MASTER.md) | Dokumentace založena zde; vlastní GitHub repozitář zatím neexistuje; pokračování od etapy 114 po kontrole zdrojů |

## Povinná sada souborů pro každý projekt
1. `PROJECT_MASTER.md` — účel, architektura, odkazy a pravidla.
2. `SESSION_STATE.md` — poslední potvrzený stav a přesné místo pokračování.
3. `CHANGELOG.md` — historie skutečně provedených změn.
4. `NEXT_TASKS.md` — otevřené úkoly a priority.
5. `TESTS.md` — testy, výsledky a neověřené oblasti.

Šablona: [CONTINUITY_TEMPLATE.md](CONTINUITY_TEMPLATE.md)

## Pracovní protokol
- Na začátku nového chatu načíst projektovou kartu a stav předání.
- Před změnou ověřit aktuální zdrojové soubory.
- Po každém významném balíčku aktualizovat stav, changelog a testy.
- Před přechodem do nového chatu zapsat poslední dokončený krok a jediný nejbližší další krok.
- Nikdy nezaměňovat úspěšné nasazení za funkčnost potvrzenou testem.

## Text pro zahájení nového chatu
„Pokračujeme v projektu [NÁZEV]. Načti dokumentaci X-5 CONTINUITY SYSTEM z repozitáře, ověř aktuální stav souborů a navazuj od posledního otevřeného úkolu. Neopakuj již dokončenou práci.“
