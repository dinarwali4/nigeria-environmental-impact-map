from eeinit import ee
import json, urllib.request
M=ee.Geometry.Point(5.0539,9.2931); aoi=M.buffer(7000).bounds()
mh=ee.Image('MERIT/Hydro/v1_0_1')
upa,hand=mh.select('upa'),mh.select('hnd')
print('upa at sample pts (km2):',{k:upa.reduceRegion(ee.Reducer.max(),ee.Geometry.Point(*v).buffer(200),90).get('upa').getInfo() for k,v in {'town_centre':(5.0565,9.2955),'north':(5.0350,9.3530),'NE_trib':(5.0880,9.3350),'south':(5.0330,9.2460)}.items()})
S2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
def s2(d):
    a=ee.Date(d); return S2.filterBounds(aoi).filterDate(a,a.advance(1,'day')).mosaic().divide(10000)
pre,post=s2('2025-05-21'),s2('2025-05-31')
bands=['B8','B11']
def norm(i):
    med=i.select(bands).reduceRegion(ee.Reducer.median(),aoi,20,maxPixels=1e9)
    return i.select(bands).divide(ee.Image.constant(med.values(bands))).rename(bands)
r=norm(post).subtract(norm(pre))
dark=r.select('B11').lt(-0.2).And(r.select('B8').lt(-0.1))
chan=upa.gt(5)
near=chan.selfMask().fastDistanceTransform(30).sqrt().multiply(ee.Image.pixelArea().sqrt()).lt(350)
valley=hand.lte(4).And(near)
# exclude cloud/shadow on post via SCL
scl=post.multiply(10000).select('SCL'); clear=scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
obs=dark.And(valley).And(clear).selfMask()
obs=obs.updateMask(obs.connectedPixelCount(200).gte(8))
area=lambda m: m.multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(),aoi,10,maxPixels=1e9).values().get(0)
print('observed scour/sediment in valley floor (ha):',ee.Number(area(obs)).divide(1e4).getInfo())
print('modelled valley floor (ha):',ee.Number(area(valley.selfMask())).divide(1e4).getInfo())
v=obs.reduceToVectors(geometry=aoi,scale=10,eightConnected=True,maxPixels=1e9).map(lambda f:f.set('ha',f.geometry().area(1).divide(1e4)))
json.dump(v.getInfo(),open('out/mokwa_obs_scour.geojson','w'))
vz=valley.selfMask().reduceToVectors(geometry=aoi,scale=30,eightConnected=True,maxPixels=1e9)
json.dump(vz.getInfo(),open('out/mokwa_valley_floor.geojson','w'))
# S1 dVV inside obs
S1=ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi).filter(ee.Filter.eq('relativeOrbitNumber_start',103))
d1=S1.filterDate('2025-06-04','2025-06-05').mosaic().select('VV').subtract(S1.filterDate('2025-05-23','2025-05-24').mosaic().select('VV'))
built=ee.ImageCollection('ESA/WorldCover/v200').first().eq(50)
print('S1 dVV median in obs:',d1.updateMask(obs).reduceRegion(ee.Reducer.median(),aoi,10,maxPixels=1e9).getInfo(),' in built valley:',d1.updateMask(built.And(valley)).reduceRegion(ee.Reducer.median(),aoi,10,maxPixels=1e9).getInfo(),' built outside valley:',d1.updateMask(built.And(valley.Not())).reduceRegion(ee.Reducer.median(),aoi,10,maxPixels=1e9).getInfo())
print('built-up ha in valley floor (WorldCover):',ee.Number(area(built.And(valley).selfMask())).divide(1e4).getInfo())
vis=post.visualize(bands=['B4','B3','B2'],min=0.02,max=0.22,gamma=1.2)
ov=vis.blend(valley.selfMask().visualize(palette=['ffff00'],opacity=0.25)).blend(obs.visualize(palette=['00e5ff'],opacity=0.9))
urllib.request.urlretrieve(ov.getThumbURL({'region':aoi,'dimensions':1400,'format':'png'}),'out/mokwa_obs_overlay.png')
# Groundsource event records
gs=ee.FeatureCollection("projects/sat-io/open-datasets/groundsource_2026").filterBounds(M.buffer(30000)).filter(ee.Filter.rangeContains('start_date','2025-05-27','2025-06-02'))
json.dump(gs.getInfo(),open('out/groundsource_mokwa_may2025.geojson','w'))
print('GS records',gs.aggregate_array('area_km2').getInfo(), gs.map(lambda f:f.set('c',f.geometry().centroid(10).coordinates())).aggregate_array('c').getInfo())
