from eeinit import ee
import json
aoi=ee.Geometry.Point(5.0505,9.3050).buffer(2500)
S2=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi)
def med(a,b):
    c=S2.filterDate(a,b).map(lambda i:i.updateMask(i.select('SCL').eq(4).Or(i.select('SCL').eq(5))).normalizedDifference(['B8','B4']))
    return c.median()
feb=med('2025-01-15','2025-03-01'); apr=med('2025-03-28','2025-04-25')
feb24=med('2024-01-15','2024-03-01'); apr24=med('2024-03-28','2024-04-25')
# woodland = dry-season NDVI>0.40 in both early-2024 and early-2025 (evergreen riparian), then dropped to <0.28 in Apr 2025
wood=feb.gt(0.40).And(feb24.gt(0.40))
cleared=wood.And(apr.lt(0.28)).And(apr24.gt(0.35))
hand=ee.Image('MERIT/Hydro/v1_0_1').select('hnd')
a=lambda m: ee.Number(m.selfMask().multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(),aoi,10,maxPixels=1e9).values().get(0)).divide(1e4)
print('woodland ha (Feb 2024 & Feb 2025):',a(wood).getInfo())
print('cleared Mar 2025 ha:',a(cleared).getInfo(),' of which valley floor HAND<=6m:',a(cleared.And(hand.lte(6))).getInfo())
v=cleared.selfMask().focal_mode(1).reduceToVectors(geometry=aoi,scale=10,eightConnected=True,maxPixels=1e9).map(lambda f:f.set('ha',f.geometry().area(1).divide(1e4))).filter(ee.Filter.gte('ha',1))
json.dump(v.getInfo(),open('out/mokwa_cleared_mar2025.geojson','w'))
