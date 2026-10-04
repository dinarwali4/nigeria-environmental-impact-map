from eeinit import ee
import json, urllib.request
O=ee.Geometry.Point(4.5624,7.7827); aoi=O.buffer(9000).bounds()
mh=ee.Image('MERIT/Hydro/v1_0_1'); hand=mh.select('hnd'); upa=mh.select('upa')
built=ee.ImageCollection('ESA/WorldCover/v200').first().eq(50)
chan=upa.gt(50)  # Osun River main stem
near=chan.selfMask().fastDistanceTransform(30).sqrt().multiply(ee.Image.pixelArea().sqrt()).lt(600)
expo=hand.lte(3).And(near)
area=lambda m: ee.Number(m.multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(),aoi,10,maxPixels=1e9).values().get(0)).divide(1e4)
print('Osun floodplain HAND<=3m within 600 m of channel (ha):',area(expo.selfMask()).getInfo(),' of which built-up:',area(expo.And(built).selfMask()).getInfo())
json.dump(expo.selfMask().reduceToVectors(geometry=aoi,scale=30,eightConnected=True,maxPixels=1e9).getInfo(),open('out/osogbo_exposure.geojson','w'))
json.dump(expo.And(built).selfMask().reduceToVectors(geometry=aoi,scale=10,eightConnected=True,maxPixels=1e9).getInfo(),open('out/osogbo_exposed_builtup.geojson','w'))
# SAR open-water within floodplain per date
S1=ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi).filter(ee.Filter.eq('instrumentMode','IW')).filter(ee.Filter.eq('relativeOrbitNumber_start',95))
fp=hand.lte(5).And(near)
def w(i):
    vv=i.select('VV').focal_median(30,'circle','meters')
    return ee.Feature(None,{'d':i.date().format('YYYY-MM-dd'),'ha':vv.lt(-18).And(fp).multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(),aoi,10,maxPixels=1e9).get('VV')})
r=S1.filterDate('2025-12-01','2026-10-05').map(w).getInfo()
print('S1 rel95 desc open-water ha in floodplain:',[(f['properties']['d'],round(f['properties']['ha']/1e4,1)) for f in r['features']])
gs=ee.FeatureCollection("projects/sat-io/open-datasets/groundsource_2026").filterBounds(O.buffer(8000))
small=gs.filter(ee.Filter.lt('area_km2',50))
yrs=small.aggregate_array('start_date').getInfo()
from collections import Counter
print('Groundsource local (<50 km2) records by year:',sorted(Counter(y[:4] for y in yrs).items()))
json.dump(small.filter(ee.Filter.gte('start_date','2015-01-01')).getInfo(),open('out/groundsource_osogbo.geojson','w'))
