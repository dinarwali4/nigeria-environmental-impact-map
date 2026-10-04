from eeinit import ee
from dl import download
P=ee.Geometry.Point(7.1955,5.6412)
dem=ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(P.buffer(40000)).select('DEM').mosaic().setDefaultProjection('EPSG:4326',None,30)
incis=dem.subtract(dem.focal_mean(240,'circle','meters'))
slope=ee.Terrain.slope(dem)
S2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
CP=ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
def comp(a,b,g):
    col=ee.ImageCollection(ee.Join.saveFirst('cp').apply(S2.filterBounds(g).filterDate(a,b).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',60)),CP.filterBounds(g).filterDate(a,b),ee.Filter.equals(leftField='system:index',rightField='system:index')))
    return col.map(lambda i: i.select(['B2','B4','B8','B11']).updateMask(ee.Image(i.get('cp')).lt(30)).divide(10000)).median()
wc=ee.ImageCollection('ESA/WorldCover/v200').first()
water=ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('max_extent').unmask(0).Or(wc.eq(80))
wdist=water.selfMask().fastDistanceTransform(20).sqrt().multiply(ee.Image.pixelArea().sqrt()).unmask(9999)
for i,(dx,dy) in enumerate([(-1,-1),(1,-1),(-1,1),(1,1)]):
    c=ee.Geometry.Point(7.1955+dx*0.135,5.6412+dy*0.135); box=c.buffer(15000).bounds()
    s=comp('2025-11-01','2026-03-15',box)
    bsi=s.expression('((S+R)-(N+B))/((S+R)+(N+B))',{'S':s.select('B11'),'R':s.select('B4'),'N':s.select('B8'),'B':s.select('B2')})
    nd=s.normalizedDifference(['B8','B4'])
    img=ee.Image.cat(incis.multiply(10),slope.multiply(10),bsi.multiply(1000),nd.multiply(1000),wc,wdist.min(5000)).rename(['incis','slope','bsi','ndvi','wc','wdist']).toInt16()
    download(img,box,20,f'imo_wide/t{i}.tif')
