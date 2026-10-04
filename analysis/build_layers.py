import json, numpy as np, rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping, LineString, Point
from shapely.ops import unary_union
from skimage.measure import regionprops
def fc(feats): return dict(type='FeatureCollection',features=feats)
def F(g,**p): return dict(type='Feature',geometry=mapping(g) if not isinstance(g,dict) else g,properties=p)
# ---------- Layer 1: Mokwa
x0,x1,y0,y1=4.990591188080409,5.117412372334194,9.356092061660393,9.230132141350124
px=lambda x,y:(x0+x*(x1-x0)/1400, y0+y*(y1-y0)/1391)
main_obs=LineString([px(*p) for p in [(620,0),(628,120),(632,200),(640,260),(668,330),(690,395),(680,470),(668,540),(657,610)]])
main_inf=LineString([px(*p) for p in [(657,610),(650,700),(648,820)]])
ne=LineString([px(*p) for p in [(1280,70),(1200,130),(1130,175),(1060,215),(960,290),(860,355),(770,385),(690,400)]])
corr=unary_union([main_obs.buffer(0.00135),ne.buffer(0.00135)])  # ~150 m
obs=json.load(open('out/mokwa_obs_scour.geojson'))
keep=[f for f in obs['features'] if shape(f['geometry']).intersects(corr)]
sc=unary_union([shape(f['geometry']) for f in keep]).simplify(0.00005)
import pyproj
from shapely.ops import transform
utm=pyproj.Transformer.from_crs(4326,32631,always_xy=True).transform
print('Mokwa scour kept ha',round(transform(utm,sc).area/1e4,1),'from',len(keep),'polys; dropped',len(obs['features'])-len(keep))
vf=unary_union([shape(f['geometry']) for f in json.load(open('out/mokwa_valley_floor.geojson'))['features']]).simplify(0.0002)
L1=[F(sc,layer='L1',site='Mokwa',kind='observed_scour',name='Observed flood scour / fresh sediment (S2 21→31 May 2025, haze-normalised)',ha=round(transform(utm,sc).area/1e4,1)),
    F(main_obs,layer='L1',site='Mokwa',kind='flood_path_observed',name='Flash-flood path – observed (main channel N of town)'),
    F(main_inf,layer='L1',site='Mokwa',kind='flood_path_inferred',name='Flash-flood path – inferred through built-up core (scour hidden by buildings)'),
    F(ne,layer='L1',site='Mokwa',kind='flood_path_observed',name='NE tributary – observed scour streak'),
    F(Point(5.0539,9.2931),layer='L1',site='Mokwa',kind='centre',name='Mokwa flash flood, 28–29 May 2025 (brief point)',date='2025-05-29')]
gs=json.load(open('out/groundsource_mokwa_may2025.geojson'))
for f in gs['features']:
    p=f['properties']
    if p['area_km2']<100:
        g=shape(f['geometry']); 
        L1.append(F(g.centroid if p['area_km2']<1 else g,layer='L1',site='Mokwa',kind='groundsource',name=f"Google Groundsource record {p['start_date']}→{p['end_date']} ({p['area_km2']:.3g} km²)",uuid=p['uuid']))
# Osogbo
ex=unary_union([shape(f['geometry']) for f in json.load(open('out/osogbo_exposure.geojson'))['features']]).simplify(0.0002)
eb=unary_union([shape(f['geometry']) for f in json.load(open('out/osogbo_exposed_builtup.geojson'))['features']]).simplify(0.0001)
wt=unary_union([shape(f['geometry']) for f in json.load(open('out/osogbo_s1_water_20260928.geojson'))['features']])
L1+=[F(ex,layer='L1',site='Osogbo',kind='exposure',name='Osun floodplain ≤3 m above river (MERIT HAND), 1,534 ha'),
     F(eb,layer='L1',site='Osogbo',kind='exposed_builtup',name='Built-up land inside that floodplain (ESA WorldCover), 186 ha'),
     F(wt,layer='L1',site='Osogbo',kind='sar_water',name='New open water, Sentinel-1C 28 Sep 2026 05:28 UTC (day before reported flood)'),
     F(Point(4.5624,7.7827),layer='L1',site='Osogbo',kind='centre',name='Osogbo riverine/flash flood, 29 Sep 2026 (brief point)',date='2026-09-29')]
for f in json.load(open('out/groundsource_osogbo.geojson'))['features']:
    p=f['properties']; g=shape(f['geometry'])
    L1.append(F(g.centroid,layer='L1',site='Osogbo',kind='groundsource',name=f"Google Groundsource record {p['start_date']} ({p['area_km2']:.3g} km²)"))
for rf in json.load(open('out/mokwa_rail.geojson'))['features']:
    L1.append(F(shape(rf['geometry']),layer='L1',site='Mokwa',kind='railway',name='Lagos–Kano railway embankment (OpenStreetMap)'))
L1+=[F(Point(5.05009,9.30069),layer='L1',site='Mokwa',kind='breach',name='Channel crosses railway embankment – observed scour ends 13 m upstream (reported embankment failure)'),
     F(Point(5.09392,9.34086),layer='L1',site='Mokwa',kind='breach',name='NE tributary crosses railway embankment'),
     F(Point(5.0488,9.3060),layer='L1',site='Mokwa',kind='clearing',name='Riparian woodland cleared Mar 2025, 2 months BEFORE flood (S2 NDVI 0.39→0.20)')]
for cf in json.load(open('out/mokwa_cleared_mar2025.geojson'))['features']:
    L1.append(F(shape(cf['geometry']),layer='L1',site='Mokwa',kind='cleared_woodland',ha=round(cf['properties']['ha'],1),name='Riparian woodland cleared Mar 2025 (S2 NDVI drop, pre-flood)'))
json.dump(fc(L1),open('layers/L1_hydromet.geojson','w'))
# ---------- Layer 2: Imo gullies (verified in Google Earth Pro VHR, Oct 2026)
L2=[]
def cls_small(lat,lon):
    if 5.598<=lat<=5.612 and 7.155<=lon<=7.168: return 'rejected_shoreline'
    if 5.686<=lat<=5.708 and 7.205<=lon<=7.245: return 'excavation_pit'
    return 'unverified_candidate'
for r in json.load(open('out/imo_cand_rows.json')):
    c=cls_small(r['lat'],r['lon'])
    if c=='unverified_candidate' and r['ha']<0.4: continue
    L2.append(F(Point(r['lon'],r['lat']),layer='L2',site='Imo',kind=c,ha=r['ha'],incision_m=r['incis'],
        name={'rejected_shoreline':'Rejected – lake shoreline (water-level change, not a gully)','excavation_pit':'Open-cast sand/laterite excavation pit (VHR 15 Mar 2024) – gully-initiation risk','unverified_candidate':'Unverified bare/incised candidate'}[c]))
for w in json.load(open('out/imo_wide_polys.json')):
    g=shape(w['poly']); c=g.centroid
    okigwe=5.79<=c.y<=5.85 and 7.36<=c.x<=7.40
    ideato=abs(c.y-5.8708)<0.01 and abs(c.x-7.0588)<0.012
    kind='verified_gully' if (okigwe or ideato) else 'gully_candidate'
    site='Okigwe escarpment' if okigwe else ('Obodo, Ideato North' if ideato else 'Imo (wide screen)')
    L2.append(F(g,layer='L2',site=site,kind=kind,len_m=w['len_m'],incision_m=w['incision_m'],slope_deg=w['slope_deg'],
        name=(f"Active gully – {site} (VHR-verified)" if kind=='verified_gully' else f"Gully candidate (unverified) – {w['len_m']} m, incised {w['incision_m']} m")))
    L2.append(F(shape(w['axis']),layer='L2',site=site,kind='gully_axis' if kind=='verified_gully' else 'gully_axis_unverified',name='Gully axis'))
L2+=[F(LineString([(7.06225, 5.87143), (7.06052, 5.87094), (7.05843, 5.87074), (7.0567, 5.8705), (7.05566, 5.86998), (7.05514, 5.86912), (7.05393, 5.86887), (7.05219, 5.86877), (7.05046, 5.86867), (7.049, 5.86856)]),layer='L2',site='Obodo, Ideato North',kind='gully_axis',name='Mega-gully axis, head→mouth (~1.5 km), traced on Airbus 12 Mar 2024'),
     F(Point(7.06225,5.87143),layer='L2',site='Obodo, Ideato North',kind='gully_head',name='Gully head at settlement edge (5.87143 N, 7.06225 E)'),
     F(Point(7.0490,5.8685),layer='L2',site='Obodo, Ideato North',kind='sediment_fan',name='Sediment fan into valley (5.8685 N, 7.0490 E)'),
     F(Point(7.3826,5.8320),layer='L2',site='Okigwe escarpment',kind='gully_head',name='Active gully head, bare sandstone headwall (Airbus 13 Feb 2025)'),
     F(Point(7.3862,5.8232),layer='L2',site='Okigwe escarpment',kind='gully_head',name='Active gully head, bare headwall beside built-up area (Airbus 13 Feb 2025)'),
     F(Point(7.1955,5.6412),layer='L2',site='Imo',kind='centre',name='Brief point – Obolo, Isiala Mbano: no gully visible in Airbus 15 Mar 2024 within ~2 km')]
json.dump(fc(L2),open('layers/L2_gully.geojson','w'))
from collections import Counter
print('L2',Counter(f['properties']['kind'] for f in L2))
# ---------- Layer 3
L3=[]
for k,lab_ in [('oban','Oban / Cross River'),('omo','Omo'),('okomu','Okomu')]:
    for f in json.load(open(f'out/{k}_zones.geojson'))['features']:
        g=shape(f['geometry']).simplify(0.0005); L3.append(F(g,layer='L3',site=lab_,kind=f['properties']['kind'],name=f['properties'].get('name',f['properties']['kind'])))
    for f in json.load(open(f'out/{k}_wdpa.geojson'))['features']:
        p=f['properties']
        if p['DESIG_ENG'] in ('National Park',) : L3.append(F(shape(f['geometry']).simplify(0.0005),layer='L3',site=lab_,kind='national_park',name=p['NAME']+' National Park'))
    for f in json.load(open(f'out/{k}_hotspots.geojson'))['features']:
        p=f['properties']
        if p['ha']>=5: L3.append(F(shape(f['geometry']),layer='L3',site=lab_,kind='canopy_loss_hotspot',**{kk:p[kk] for kk in ['ha','envelope_ha','loss_hansen_2023_25_ha','radd_2025_26_ha']}))
for nm,(lon,lat) in {'Cross River / Oban sector':(8.5721,5.3214),'Omo Forest Reserve':(4.3542,6.8125),'Okomu protected zone':(5.2184,6.4136)}.items():
    L3.append(F(Point(lon,lat),layer='L3',site=nm,kind='centre',name=nm+' (brief point)'))
rd=json.load(open('out/oban_new_road.geojson'))
L3.append(F(shape(rd['geometry']),layer='L3',site='Oban / Cross River',kind='new_road',name='New access/logging road, first seen in 2025–26 S2 composite – 4,233 m inside Oban Group Forest Reserve (4,740 m traced; continues beyond analysis box)',length_m=rd['properties']['length_m']))
ob=json.load(open('out/okomu_new_block.geojson'))['features'][0]
L3.append(F(shape(ob['geometry']),layer='L3',site='Okomu',kind='new_clearance',ha=163.0,name='New 163 ha clearance with planting rows inside Okomu Forest Reserve – radar-dated Apr–Dec 2025 (RADD); 10.5 km from National Park'))
for f in L3:
    p=f['properties']
    if p['kind']=='canopy_loss_hotspot' and p['site']=='Omo': p['confidence']='low – plantation/farm mosaic; may be rotation harvest'
    elif p['kind']=='canopy_loss_hotspot': p['confidence']='moderate–high (frontier advance visible in S2 2020→2026)'
json.dump(fc(L3),open('layers/L3_forest.geojson','w'))
print('L3 features',len(L3),'hotspots',sum(1 for f in L3 if f['properties']['kind']=='canopy_loss_hotspot'))
import os; print({f:round(os.path.getsize('layers/'+f)/1e6,2) for f in os.listdir('layers')})
