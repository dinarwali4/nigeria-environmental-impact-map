import rasterio, numpy as np, json
from rasterio.features import rasterize, shapes
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from pyproj import Transformer
from scipy import ndimage as ndi
SITES={'oban':['Oban Group'],'omo':['Omo'],'okomu':['Okomu']}
summary={}
for k,names in SITES.items():
    L={b:rasterio.open(f'out/{k}_{b}.tif') for b in ['lossyear','tc2000','nat','palm','radd','raddhi']}
    A={b:r.read(1) for b,r in L.items()}
    h=min(a.shape[0] for a in A.values()); w=min(a.shape[1] for a in A.values()); A={b:a[:h,:w] for b,a in A.items()}
    T=L['lossyear'].transform
    lat0=T.f+T.e*h/2; pxa=(T.a*111320*np.cos(np.radians(lat0)))*(-T.e*110574)/1e4  # ha per pixel
    gj=json.load(open(f'out/{k}_wdpa.geojson'))
    feats=[f for f in gj['features'] if any(n==f['properties']['NAME'] for n in names) and f['properties']['DESIG_ENG']!='UNESCO-MAB Biosphere Reserve']
    if k=='okomu': feats=[f for f in gj['features'] if f['properties']['NAME']=='Okomu']
    geom=unary_union([shape(f['geometry']) for f in feats])
    utm=Transformer.from_crs(4326,32631 if k!='oban' else 32632,always_xy=True); inv=Transformer.from_crs(32631 if k!='oban' else 32632,4326,always_xy=True)
    gu=transform(utm.transform,geom)
    ring_in=transform(inv.transform,gu.difference(gu.buffer(-2000)))
    ring_out=transform(inv.transform,gu.buffer(5000).difference(gu))
    def m(g): return rasterize([mapping(g)],out_shape=(h,w),transform=T,fill=0,default_value=1).astype(bool)
    inside,rin,rout=m(geom),m(ring_in),m(ring_out)
    ispalm=(A['palm']==1)|(A['palm']==2); natural=(A['nat']>=13000)&(~ispalm)          # natural-forest prob>=0.52, not oil palm
    forest00=A['tc2000']>=30
    nat_forest=natural&forest00
    res={}
    np_names={'oban':'Cross River','okomu':'Okomu'}
    extra=[]
    if k in np_names:
        npf=[f for f in gj['features'] if f['properties']['NAME'].startswith(np_names[k]) and f['properties']['DESIG_ENG']=='National Park']
        if npf: extra=[('national_park_part',m(unary_union([shape(f['geometry']) for f in npf])))]
    for zn,z in [('inside_reserve',inside),('inner_edge_0_2km',rin),('outside_ring_0_5km',rout)]+extra:
        ly=A['lossyear']
        byyr={2000+y:round(float(((ly==y)&z&nat_forest).sum()*pxa),1) for y in range(1,26)}
        allyr={2000+y:round(float(((ly==y)&z&forest00).sum()*pxa),1) for y in range(1,26)}
        res[zn]=dict(natural_forest_2020_ha=round(float((natural&z).sum()*pxa),1),
            natloss_by_year=byyr,anyloss_by_year=allyr,
            natloss_2011_15=round(sum(byyr[y] for y in range(2011,2016)),1),natloss_2016_20=round(sum(byyr[y] for y in range(2016,2021)),1),natloss_2021_25=round(sum(byyr[y] for y in range(2021,2026)),1),
            radd_2025_26_ha=round(float(((A['radd']>0)&z).sum()*pxa),1),radd_nat_2025_26_ha=round(float(((A['radd']>0)&z&natural).sum()*pxa),1),
            radd_nat_2026_ha=round(float(((A['radd']>=26001)&z&natural).sum()*pxa),1),
            palm_ha=round(float((ispalm&z).sum()*pxa),1))
    summary[k]=res
    print('=====',k,'reserve km2',round(gu.area/1e6,1))
    for zn,r in res.items(): print(zn,{kk:v for kk,v in r.items() if 'by_year' not in kk}); print('   nat loss by yr 2016-25',[r['natloss_by_year'][y] for y in range(2016,2026)])
    # hotspot polygons: recent (Hansen 2023-25 natural-forest loss OR RADD 2025-26) clusters >= 3 ha
    raw=(((A['lossyear']>=23)&nat_forest)|((A['radd']>0)&natural))
    recent=ndi.binary_closing(raw,iterations=1)
    lab,n=ndi.label(recent,structure=np.ones((3,3)))
    sizes=ndi.sum(recent,lab,range(1,n+1))*pxa
    keep=np.isin(lab,np.where(sizes>=3)[0]+1)
    polys=[]
    for g,v in shapes(keep.astype(np.uint8),mask=keep,transform=T,connectivity=8):
        s=shape(g).simplify(0.0002)
        su=transform(utm.transform,s)
        pm=rasterize([g],out_shape=(h,w),transform=T,fill=0,default_value=1).astype(bool)
        polys.append(dict(type='Feature',geometry=mapping(s),properties=dict(site=k,envelope_ha=round(su.area/1e4,1),ha=round(float((pm&raw).sum()*pxa),1),loss_hansen_2023_25_ha=round(float((pm&(A['lossyear']>=23)&nat_forest).sum()*pxa),1),radd_2025_26_ha=round(float((pm&(A['radd']>0)&natural).sum()*pxa),1),inside=bool(s.representative_point().within(geom)))))
    polys.sort(key=lambda f:-f['properties']['ha'])
    json.dump(dict(type='FeatureCollection',features=polys),open(f'out/{k}_hotspots.geojson','w'))
    json.dump(dict(type='FeatureCollection',features=[dict(type='Feature',geometry=mapping(geom),properties=dict(name=names[0],kind='reserve')),dict(type='Feature',geometry=mapping(ring_in),properties=dict(kind='inner_edge_0_2km')),dict(type='Feature',geometry=mapping(ring_out),properties=dict(kind='outside_ring_0_5km'))]),open(f'out/{k}_zones.geojson','w'))
    print('hotspots',len(polys),'total ha',round(sum(p['properties']['ha'] for p in polys),1),'top',[(p['properties']['ha'],p['properties']['inside'],[round(c,4) for c in shape(p['geometry']).centroid.coords[0]]) for p in polys[:6]])
json.dump(summary,open('out/forest_summary.json','w'),indent=1)
