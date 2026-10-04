from eeinit import ee
from dl import download
P=ee.Geometry.Point(7.1955,5.6412); aoi=P.buffer(8000).bounds()
dem=ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(aoi).select('DEM').mosaic().setDefaultProjection('EPSG:4326',None,30)
incis=dem.subtract(dem.focal_mean(240,'circle','meters'))
slope=ee.Terrain.slope(dem)
S2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi)
CP=ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY').filterBounds(aoi)
def comp(a,b):
    col=ee.ImageCollection(ee.Join.saveFirst('cp').apply(S2.filterDate(a,b).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',60)),CP.filterDate(a,b),ee.Filter.equals(leftField='system:index',rightField='system:index')))
    return col.map(lambda i: i.select(['B2','B4','B8','B11']).updateMask(ee.Image(i.get('cp')).lt(30)).divide(10000)).median()
c26=comp('2025-11-01','2026-03-15'); c18=comp('2017-11-01','2018-03-15')
bsi=lambda c: c.expression('((S+R)-(N+B))/((S+R)+(N+B))',{'S':c.select('B11'),'R':c.select('B4'),'N':c.select('B8'),'B':c.select('B2')})
nd=lambda c: c.normalizedDifference(['B8','B4'])
wc=ee.ImageCollection('ESA/WorldCover/v200').first()
img=ee.Image.cat(incis.rename('incis'),slope.rename('slope'),bsi(c26).rename('bsi26'),nd(c26).rename('ndvi26'),bsi(c18).rename('bsi18'),nd(c18).rename('ndvi18'),wc.rename('wc')).toFloat()
for i,b in enumerate(['incis','slope','bsi26','ndvi26','bsi18','ndvi18','wc']):
    download(img.select(b),aoi,10,f'out/imo_{b}.tif')
