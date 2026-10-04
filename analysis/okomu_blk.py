from eeinit import ee
import json
aoi=ee.Geometry.Point(5.0696,6.2996).buffer(2500).bounds()
S2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED'); CP=ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
def comp(a,b):
    col=ee.ImageCollection(ee.Join.saveFirst('cp').apply(S2.filterBounds(aoi).filterDate(a,b).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',80)),CP.filterBounds(aoi).filterDate(a,b),ee.Filter.equals(leftField='system:index',rightField='system:index')))
    return col.map(lambda i:i.updateMask(ee.Image(i.get('cp')).lt(25)).divide(10000)).median()
a,b=comp('2023-11-15','2024-03-15'),comp('2025-11-15','2026-03-15')
nbr=lambda i:i.normalizedDifference(['B8','B12'])
blk=nbr(a).gt(0.45).And(nbr(b).lt(0.25))
blk=blk.selfMask().focal_mode(2).selfMask()
v=blk.reduceToVectors(geometry=aoi,scale=10,eightConnected=True,maxPixels=1e9).map(lambda f:f.set('ha',f.geometry().area(1).divide(1e4))).filter(ee.Filter.gte('ha',5))
g=v.getInfo(); print([round(f['properties']['ha'],1) for f in g['features']])
json.dump(g,open('out/okomu_new_block.geojson','w'))
# radd dates inside biggest block
R=ee.ImageCollection('projects/radar-wur/raddalert/v1').filter(ee.Filter.eq('system:index','africa_20260923')).first()
big=ee.Feature(v.sort('ha',False).first()).geometry()
h=R.select('Date').updateMask(R.select('Alert').gte(2)).reduceRegion(ee.Reducer.frequencyHistogram(),big,10,maxPixels=1e9).getInfo()
from collections import Counter
c=Counter()
for k,n in h['Date'].items():
    k=int(float(k)); 
    if k>0: c[f"20{k//1000:02d}-Q{min(4,(k%1000-1)//92+1)}"]+=n
print('RADD alert pixels by quarter in largest block:',sorted(c.items()))
