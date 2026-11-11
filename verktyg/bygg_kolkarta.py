"""Bygger kartlager och förberäknad data till kartsidan (index.html).

Läser SLU:s kollager (soc, dom) och biomassalagret direkt som Cloud Optimized GeoTIFF över HTTP och hämtar bara
Malmöutsnittet. Skriver:
  lager/<namn>.png        färgsatta rasterlager i Web Mercator (EPSG:3857) för Leaflet
  lager/lager.json        lagrens gränser, enheter och färgskalor
  data/omraden.geojson    ÖP 2023:s utbyggnadsområden med pixelstatistik som sidan räknar markposten ur
  data/deso.geojson       DeSO med ohårdgjord andel och hushåll per ha (referensunderlaget)

Kör:  python -I verktyg/bygg_kolkarta.py        (kräver rasterio, shapely, matplotlib, numpy)
"""
import ast, json, os, sys, numpy as np, rasterio
from rasterio.warp import transform_geom, reproject, calculate_default_transform, Resampling, transform_bounds
from rasterio.features import geometry_mask, rasterize
from rasterio.windows import from_bounds
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid
import matplotlib; matplotlib.use("Agg")
from matplotlib import cm, colors
from PIL import Image

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "/vsicurl/https://carbonaracarbon.blob.core.windows.net/carbon/{}.tif"
MIN_LANDDEL_M2 = 5000  # landbitar under 0,5 ha tas bort (Öresundsbrons pelare räknas som land i OSM)
BBOX = (360000, 6148000, 392000, 6172000)  # SWEREF 99 TM, täcker Malmö kommun
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

# OSM-taggar (samma regler som analysen 2026-11-11)
VEG = {('landuse','forest'),('natural','wood'),('natural','scrub'),('natural','shrubbery'),('leisure','park'),('landuse','grass'),
       ('landuse','meadow'),('natural','tree_row'),('landuse','allotments'),('surface','grass'),('landuse','flowerbed'),
       ('leisure','dog_park'),('natural','grassland'),('natural','heath'),('landuse','cemetery'),('leisure','garden')}
TRAD = {('landuse','forest'),('natural','wood'),('natural','tree_row')}
SEAL = {('amenity','parking'),('amenity','parking_space'),('surface','asphalt'),('surface','concrete'),('surface','paving_stones'),
        ('leisure','swimming_pool'),('surface','tartan'),('surface','artificial_turf'),('landuse','construction'),('highway','pedestrian'),
        ('landuse','industrial'),('landuse','retail'),('landuse','commercial'),('landuse','railway')}


def las(namn):
    with rasterio.open(URL.format(namn)) as s:
        w = from_bounds(*BBOX, transform=s.transform).round_offsets().round_lengths()
        return s.read(1, window=w, boundless=True, fill_value=s.nodata).astype(float), s.window_transform(w), s.nodata


def osm_geom(f):
    g = f['g']
    try:
        if isinstance(g[0][0], (int, float)):
            s = Polygon(g) if (g[0] == g[-1] and len(g) >= 4) else LineString(g).buffer(0.00006)  # trädrad ~ 4–7 m bred
        else:
            s = Polygon(g[0], g[1:])
        return transform_geom('EPSG:4326', 'EPSG:3006', mapping(s.buffer(0)))
    except Exception:
        return None


def png(arr, tr, namn, vmax, cmap, enhet, titel, lager):
    """Projicera till EPSG:3857 och spara som PNG med genomskinlig nodata."""
    h, w = arr.shape
    dst_tr, dw, dh = calculate_default_transform('EPSG:3006', 'EPSG:3857', w, h, *rasterio.transform.array_bounds(h, w, tr))
    ut = np.full((dh, dw), np.nan)
    reproject(arr, ut, src_transform=tr, src_crs='EPSG:3006', dst_transform=dst_tr, dst_crs='EPSG:3857',
              resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    rgba = (matplotlib.colormaps[cmap](colors.Normalize(0, vmax, clip=True)(np.nan_to_num(ut))) * 255).astype(np.uint8)
    rgba[..., 3] = np.where(np.isnan(ut), 0, 220)
    # palettbild: en tredjedel av storleken, genomskinligheten behålls
    Image.fromarray(rgba).quantize(colors=128, method=Image.Quantize.FASTOCTREE).save(os.path.join(ROT, 'lager', namn + '.png'), optimize=True)
    b = transform_bounds('EPSG:3857', 'EPSG:4326', *rasterio.transform.array_bounds(dh, dw, dst_tr))
    stopp = [colors.to_hex(matplotlib.colormaps[cmap](i / 4)) for i in range(5)]
    lager.append(dict(id=namn, titel=titel, fil=f'lager/{namn}.png', bounds=[[b[1], b[0]], [b[3], b[2]]],
                      vmax=vmax, enhet=enhet, farger=stopp))


def main():
    soc, tr, nd = las('soc'); dom, _, _ = las('dom'); bio, trb, ndb = las('biomass')
    # biomassan har ett annat rutnät: läs om den på SLU-rutnätet
    if bio.shape != soc.shape or trb != tr:
        b2 = np.full(soc.shape, np.nan)
        reproject(bio, b2, src_transform=trb, src_crs='EPSG:3006', dst_transform=tr, dst_crs='EPSG:3006', resampling=Resampling.nearest)
        bio = b2
    bio[(bio < 0) | np.isnan(bio)] = 0
    oforseglad = soc > 0
    markkol = np.where(oforseglad, (soc + np.where(dom > 0, dom, 0)) / 1000, np.nan)   # t C/ha, kg C/ha i källan

    lager = []
    png(np.where(soc > 0, soc / 1000, np.nan), tr, 'soc', 200, 'YlOrBr', 't C/ha', 'SOC – markkol 0–0,5 m (SLU)', lager)
    png(np.where(dom > 0, dom / 1000, np.nan), tr, 'dom', 40, 'BuPu', 't C/ha', 'DOM – dött organiskt material (SLU)', lager)
    png(np.where(bio > 0, bio, np.nan), tr, 'biomassa', 200, 'Greens', 't C/ha', 'Biomassa – original (ej korrigerad)', lager)
    png(np.where(oforseglad & (bio > 0), bio, np.nan), tr, 'biomassa_korr', 200, 'Greens', 't C/ha',
        'Biomassa – korrigerad (bara där SLU har markkol)', lager)
    png(markkol, tr, 'kol_summa', 200, 'viridis', 't C/ha', 'Markkol + DOM (SLU, ohårdgjord mark)', lager)
    json.dump(lager, open(os.path.join(ROT, 'lager', 'lager.json'), 'w'), ensure_ascii=False, indent=1)

    # OSM-masker
    osm = json.load(open(os.path.join(ROT, 'data/kalla/osm_markanvandning_utbyggnad.json')))['features']
    def mask(tags, utan=None):
        gs = [g for f in osm if any(t in tags for t in f['t'].items()) and not (utan and any(t in utan for t in f['t'].items()))
              for g in [osm_geom(f)] if g]
        return rasterize([(g, 1) for g in gs], out_shape=soc.shape, transform=tr, fill=0).astype(bool)
    m_veg, m_trad, m_seal = mask(VEG), mask(TRAD), mask(SEAL, utan=VEG)

    # Utbyggnadsområden
    exp = json.load(open(os.path.join(ROT, 'data/kalla/exploatering_op2023.json')))
    feats = []
    for o in exp['omraden']:
        g = o['geometry']; g = json.loads(g.replace("'", '"')) if isinstance(g, str) else g
        inne = ~geometry_mask([transform_geom('EPSG:4326', 'EPSG:3006', g)], soc.shape, tr)
        u = inne & oforseglad
        bio_ok = u & ~m_seal                      # biomassa på ohårdgjord mark, inte på OSM-hårdgjort utan vegetation
        trad_hardgjord = inne & ~oforseglad & m_trad
        varden, antal = np.unique(np.round(markkol[u]).astype(int), return_counts=True)
        bv, ba = np.unique((np.round(bio[trad_hardgjord] / 5) * 5).astype(int), return_counts=True)
        feats.append(dict(type='Feature', geometry=g, properties=dict(
            id=o['id'], namn=o['namn'], kategori=o['kategori'], bostader=o['bostader'], arbetsplatser=o['arbetsplatser'],
            ha=round(inne.sum() / 100, 2), ohardgjord_ha=round(u.sum() / 100, 2),
            markkol_hist=[[int(a), int(b)] for a, b in zip(varden, antal)],       # [t C/ha, antal 10 m-rutor]
            biomassa_ohardgjord_tC=round(float(bio[bio_ok].sum()) * 0.01, 1),
            trad_hardgjord_hist=[[int(a), int(b)] for a, b in zip(bv, ba) if a > 0],
            typ='blandad')))
    json.dump(dict(type='FeatureCollection', kalla=exp['kalla'], features=feats),
              open(os.path.join(ROT, 'data/omraden.geojson'), 'w'), ensure_ascii=False)

    # DeSO: referensunderlaget, klippt mot OSM:s landpolygoner så att havet inte räknas som hårdgjord yta
    deso = json.load(open(os.path.join(ROT, 'data/kalla/deso_2025_malmo.geojson')))
    land = unary_union([make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROT, 'data/kalla/land_malmo_osm.json')))['features']])
    hh = json.load(open(os.path.join(ROT, 'data/kalla/deso_hushall_2024.json')))
    for f in deso['features']:
        p = f['properties']
        klipp = make_valid(shape(f['geometry'])).intersection(land)
        delar = [d for d in getattr(klipp, 'geoms', [klipp]) if d.geom_type == 'Polygon'
                 and shape(transform_geom('EPSG:4326', 'EPSG:3006', mapping(d))).area >= MIN_LANDDEL_M2]
        f['geometry'] = mapping(MultiPolygon(delar).simplify(2e-5, preserve_topology=True))
        m = ~geometry_mask([transform_geom('EPSG:4326', 'EPSG:3006', f['geometry'])], soc.shape, tr)
        p['ohardgjord'] = round(float(oforseglad[m].mean()), 3) if m.any() else None
        p['hushall_per_ha'] = round(hh[p['id']]['hushall'] / p['land_ha'], 1)
        p['inv_per_ha'] = round(hh[p['id']]['bef'] / p['land_ha'], 1)
    json.dump(deso, open(os.path.join(ROT, 'data/deso.geojson'), 'w'), ensure_ascii=False)
    print('klart:', len(lager), 'lager,', len(feats), 'områden,', len(deso['features']), 'DeSO')


if __name__ == '__main__':
    main()
