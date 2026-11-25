# WEATHER VORTEX 3D X-5 – Etapa 2

## Výchozí stav
Tato větev vychází z ověřené verze nasazené na GitHub Pages. Stabilní záloha je uložena ve větvi `stable/weather-vortex-3d-x5-v1.1`.

## Cíl etapy
Vylepšit meteorologickou čitelnost a prostorovou vizualizaci bez změny existujících zdrojů dat a ovládání.

## Plánované úkoly
1. **Teplotní pole:** zpřesnit barevnou škálu a interpolaci mezi meteorologickými body; zachovat jednotnou legendu a čitelnost na mobilu.
2. **Srážky:** jasně oddělit déšť a sněžení, zlepšit intenzitní škálu a popisky jednotek.
3. **Proudění větru:** zachovat lokální vektory Open-Meteo, zlepšit plynulost a čitelnost proudnic; nepřidávat falešnou rotaci.
4. **Mobil/tablet:** ověřit rozměry 3D plochy, ovládací prvky a posouvání stránky v portrait i landscape.
5. **Ověření:** syntaktická kontrola, test načítání dat a samostatný náhledový balíček. Do hlavní větve se změny dostanou až po uživatelském testu.

## Bezpečnostní pravidla
- Neměnit větev `main` během vývoje etapy 2.
- Neměnit stabilní zálohu `stable/weather-vortex-3d-x5-v1.1`.
- Neoznačovat schematický 3D terén ani interpolované pole za přímé měření.
- Při selhání jedné vrstvy zachovat funkčnost ostatních vrstev.
