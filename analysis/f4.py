from eeinit import ee
from dl import download
import json
H=ee.Image('UMD/hansen/global_forest_change_2025_v1_13')
nf=ee.ImageCollection('projects/nature-trace/assets/forest_typology/natural_forest_2020_v1_0_collection').mosaic().select('B0')
op=ee.ImageCollection('BIOPAMA/GlobalOilPalm/v1').mosaic().select('classification')
R=ee.ImageCollection('projects/radar-wur/raddalert/v1').filter(ee.Filter.eq('system:index','africa_20260923')).first()
radd=R.select('Date').updateMask(R.select('Alert').gte(2)).updateMask(R.select('Date').gte(25001))  # YYDOY, 2025-01-01 onward
raddhi=R.select('Date').updateMask(R.select('Alert').eq(3)).updateMask(R.select('Date').gte(25001))
w=ee.FeatureCollection('WCMC/WDPA/current/polygons').filter(ee.Filter.eq('ISO3','NGA'))
sites={'oban':(8.5721,5.3214,22000),'omo':(4.3542,6.8125,22000),'okomu':(5.2184,6.4136,22000)}
pa={}
for k,(lon,lat,r) in sites.items():
    p=ee.Geometry.Point(lon,lat); box=p.buffer(r).bounds()
    print(k,'natprob range',nf.reduceRegion(ee.Reducer.minMax(),box,300).getInfo())
    img=ee.Image.cat(H.select('lossyear').unmask(0).rename('lossyear'),H.select('treecover2000').rename('tc2000'),nf.unmask(0).multiply(100).rename('nat'),op.unmask(0).rename('palm'),
        radd.unmask(0).reduceResolution(ee.Reducer.max(),maxPixels=64).rename('radd'),raddhi.unmask(0).reduceResolution(ee.Reducer.max(),maxPixels=64).rename('raddhi')).toInt32()
    img=img.reproject('EPSG:4326',None,H.projection().nominalScale().getInfo())
    for b in ['lossyear','tc2000','nat','palm','radd','raddhi']:
        download(img.select(b),box,30,f'out/{k}_{b}.tif')
    pas=w.filterBounds(box)
    json.dump(pas.getInfo(),open(f'out/{k}_wdpa.geojson','w'))
