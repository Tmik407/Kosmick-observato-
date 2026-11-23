# OPERATION X-5 — projektová karta

Aktualizováno: 23. 11. 2026

## Účel projektu
OPERATION X-5 je dlouhodobý projekt taktické real-time strategické hry pro PC/Windows. Zaměření zahrnuje velení pěchotě a obrněným jednotkám, dělostřelectvo, balistiku, poškození a destrukci prostředí, AI a kampaňové mise.

## Technologie a směr
- Zvolený technologický směr: Unreal Engine 5.
- Zamýšlená implementace: C++ a Blueprint.
- Cíl: postupně rozvíjený, škálovatelný herní prototyp.
- Inspirace: taktické real-time strategie ve stylu Men of War; nejde o tvrzení o oficiální návaznosti.

## Evidovaný stav projektu
- Archiv etap 1–113 byl nyní dodán a zkontrolován.
- Archiv obsahuje 718 souborů; ZIP CRC kontrola je úspěšná.
- Etapa 113: centralizované statistiky ztrát armády a logistiky.
- Etapa 114 byla připravena jako zdrojová etapa: automatické obnovení statistik posádek a logistiky.
- Aktuální pracovní balíček po etapě 114 obsahuje 720 souborů.
- Není potvrzena kompilace, spuštění ani runtime funkčnost v Unreal Engine 5.

## Umístění a správa
- Projekt zatím nemá vlastní GitHub repozitář.
- Tato dokumentace je vedena v centrálním repozitáři X-5 CONTINUITY SYSTEM v cestě `docs/operation-x5/`.
- Pracovní ZIP po etapě 114 je předán jako příloha této konverzace; není zatím uložen do samostatného GitHub repozitáře.

## Zásady
1. Nepřepisovat ani neopakovat dokončené etapy bez důvodu.
2. Navazovat od etapy 115.
3. Oddělovat hotové zdrojové soubory od funkcí ověřených v běžící hře.
4. Každou etapu evidovat v changelogu a odpovídajících testech.
5. Neoznačovat projekt za hratelný nebo sestavitelný bez skutečného testu.

## Struktura
Archiv obsahuje modul `Source/OPERATION_X5`, konfiguraci `Config`, soubor `OPERATION_X5.uproject`, dokumentaci a další pracovní soubory. Unreal Engine verze není v projektu pevně nastavena (`EngineAssociation` je prázdné).
