# road2zero-kolkarta

Kolförråd i Malmö: originallagren ur SLU:s kolkartor och biomassalagret, och markposten för ÖP 2023:s 36
utbyggnadsområden, med de kritiska parametrarna justerbara i webbläsaren. Underlag till uppdraget Klimatkartor i
översiktlig planering (Malmö stad, december 2026) och till markposten i Road2Zero-OP (`Mulmen65/road2zero`, `op/`).

## Öppna kartan

Sidan läser sina data med `fetch`, så den måste visas via en webbserver:

```
python -m http.server 8000      # i repots rot, öppna sedan http://localhost:8000
```

Streamlit Community Cloud: välj repot, gren `main` och main file path `streamlit_app.py`. Appen visar samma
sida med data och lager inbäddade.

Eller slå på GitHub Pages (Settings > Pages > Deploy from branch, `main`, rot). Pages för privata repon kräver ett
betalt GitHub-konto.

## Innehåll

| Sökväg | Innehåll |
|---|---|
| `streamlit_app.py` | Samma karta i Streamlit (bäddar in data och lager) |
| `index.html` | Kartan: originallager, resultatlager, DeSO, parametrar och tabell (Leaflet 1.9.4) |
| `lager/*.png`, `lager/lager.json` | Rasterlagren över Malmö i Web Mercator, 10 m, med färgskala |
| `data/omraden.geojson` | Utbyggnadsområdena med förberäknad pixelstatistik (histogram över markkol, biomassa) |
| `data/deso.geojson` | DeSO 2025 med ohårdgjord andel (SLU) och hushåll per ha 2024 |
| `data/kalla/` | Indata kopierade ur Road2Zero-OP: ÖP 2023, OSM-markanvändning, DeSO, hushåll (Vägvis 2.3.1) |
| `verktyg/bygg_kolkarta.py` | Bygger `lager/` och `data/` direkt ur tiff-filerna (läser bara Malmöutsnittet över HTTP) |
| `test/test_rakning.js` | Kontroll att sidans räkning ger analysens resultat med standardvärdena |

Bygg om: `pip install -r verktyg/requirements.txt`, sedan `python -I verktyg/bygg_kolkarta.py`.
Testa: `node test/test_rakning.js`.

## Originallagren

| Lager | Källa | Enhet i filen | Anmärkning |
|---|---|---|---|
| `soc.tif` | SLU, *Carbon stock and carbon stock change in Swedish soils* | kg C/ha, 0–0,5 m | Bebyggd mark saknar värde, också gårdar och gaturum i tät stad |
| `dom.tif` | Samma (död ved, förna, humus) | kg C/ha | Samma rutnät som SOC |
| `biomass.tif` | Biomassalagret (källa att bekräfta) | t C/ha | Läser byggnader som vegetation på hårdgjord mark (Varvsstaden 120 t C/ha i medel) |

Filerna är Cloud Optimized GeoTIFF över hela Sverige, 10 m, SWEREF 99 TM, och ligger på
`https://carbonaracarbon.blob.core.windows.net/carbon/`.

## Metod för markposten

```
tagen yta  = min(områdets ohårdgjorda yta, bostadsekvivalenter / bostäder per ha)
förlust    = tagen yta × (1 − ohårdgjord andel i slutläget) × kol per ha × 44/12
kol per ha = medel över ohårdgjorda rutor av max(0, SOC + DOM − kvarvarande kol) + biomassa
```

- Ohårdgjord = rutor där SLU har markkol. Biomassa räknas bara där, och inte på ytor som OpenStreetMap anger som
  hårdgjorda utan vegetation.
- Verksamhetsområden tar hela den ohårdgjorda ytan.
- Träd på hårdgjord mark (torg, gator) räknas inte som standard: de antas sparas, och lagret är opålitligt där.

| Parameter | Standard | Status och underlag |
|---|---|---|
| Bostäder per ha, tät blandad stad | 64 | Mätt: Västra hamnen och Hyllievång syd (C1272), hushåll per ha brutto 2024 |
| Ohårdgjord andel i slutläget, tät blandad stad | 0,05 | Mätt i samma DeSO ur SLU-lagret (spann 0,01–0,14) |
| Bostäder per ha, småhus | 11 | Mätt: Bunkeflostrand öst och väst |
| Ohårdgjord andel, småhus | 0,71 | Mätt i samma DeSO; trädgårdar räknas som gräsmark av SLU |
| Arbetsplats i bostadsekvivalenter | 0,278 | Modellval: 25 / 90 m² BTA (Road2Zero-OP) |
| Kol kvar under bebyggd mark | 22 t C/ha | Länsstyrelsen i Uppsala län (2025), som i Road2Zero-OP |
| Andel av träd på hårdgjord mark som tas bort | 0 | Beslut 2026-11-11 |
| Tak för träd på hårdgjord mark | 50 t C/ha | Antagande; används bara om andelen ovan är större än 0 |

Typologin per område väljs i tabellen. ÖP 2023 anger bara kategori, så alla bostadsområden är tät blandad stad
tills samrådsförslagets lager finns.

Standardresultat: 153,8 kt CO₂ för alla 36 områden (Road2Zero-OP med Uppsalavärden: 99,7 kt).

## Licenser och data

OpenStreetMap-data © OpenStreetMap-bidragsgivare, ODbL. ÖP 2023: Malmö stad. DeSO: SCB. SLU-lagrens
användarvillkor anges inte i katalogen och bör bekräftas innan repot görs publikt.
