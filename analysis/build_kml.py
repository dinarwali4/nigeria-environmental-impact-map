import json
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, MultiLineString, Point, GeometryCollection
from xml.sax.saxutils import escape
STY={ # kind: (line aabbggrr, width, fill aabbggrr or None)
 'observed_scour':('ffffff00',2,'26ffff00'),'flood_path_observed':('ffff6a00',5,None),'flood_path_inferred':('ffffb27f',4,None),
 'exposure':('ff00ffff',2,'3300ffff'),'exposed_builtup':('ff0080ff',1,'8c0080ff'),'sar_water':('ffffff00',2,'ccffff00'),
 'gully_candidate':('99ff80ff',1,None),'verified_gully':('ffff00ff',3,'33ff00ff'),'gully_axis':('ff0000ff',4,None),'gully_axis_unverified':('99ff80ff',1,None),'railway':('ff333333',3,None),'new_road':('ff00a5ff',6,None),'new_clearance':('ff00a5ff',4,'4000a5ff'),'cleared_woodland':('ff4aaa2e',3,'334aaa2e'),
 'reserve':('ff00ff55',4,'00000000'),'national_park':('ff00aa00',3,'00000000'),'inner_edge_0_2km':('9900ffaa',2,'1a00ffaa'),'outside_ring_0_5km':('99aaffff',2,'1aaaffff'),
 'canopy_loss_hotspot':('ff0000ff',2,'260000ff')}
PIN={'centre':'http://maps.google.com/mapfiles/kml/paddle/wht-stars.png','groundsource':'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png','breach':'http://maps.google.com/mapfiles/kml/paddle/red-diamond.png','clearing':'http://maps.google.com/mapfiles/kml/paddle/grn-diamond.png','gully_head':'http://maps.google.com/mapfiles/kml/paddle/red-circle.png','sediment_fan':'http://maps.google.com/mapfiles/kml/paddle/orange-circle.png','excavation_pit':'http://maps.google.com/mapfiles/kml/paddle/orange-square.png','rejected_shoreline':'http://maps.google.com/mapfiles/kml/shapes/forbidden.png','unverified_candidate':'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'}
def coords(cs): return ' '.join(f'{x:.6f},{y:.6f},0' for x,y in cs)
def geom_kml(g):
    if isinstance(g,Polygon):
        s='<Polygon><tessellate>1</tessellate><altitudeMode>clampToGround</altitudeMode><outerBoundaryIs><LinearRing><coordinates>'+coords(g.exterior.coords)+'</coordinates></LinearRing></outerBoundaryIs>'
        for i in g.interiors: s+='<innerBoundaryIs><LinearRing><coordinates>'+coords(i.coords)+'</coordinates></LinearRing></innerBoundaryIs>'
        return s+'</Polygon>'
    if isinstance(g,LineString): return '<LineString><tessellate>1</tessellate><altitudeMode>clampToGround</altitudeMode><coordinates>'+coords(g.coords)+'</coordinates></LineString>'
    if isinstance(g,Point): return f'<Point><coordinates>{g.x:.6f},{g.y:.6f},0</coordinates></Point>'
    if isinstance(g,(MultiPolygon,MultiLineString,GeometryCollection)): return '<MultiGeometry>'+''.join(geom_kml(x) for x in g.geoms)+'</MultiGeometry>'
    return ''
def styles():
    s=''
    for k,(lc,w,fc) in STY.items():
        s+=f'<Style id="{k}"><LineStyle><color>{lc}</color><width>{w}</width></LineStyle><PolyStyle><color>{fc or "00000000"}</color><fill>{1 if fc else 0}</fill><outline>1</outline></PolyStyle><LabelStyle><scale>0</scale></LabelStyle></Style>'
    for k,h in PIN.items(): s+=f'<Style id="{k}"><IconStyle><scale>{1.3 if k=="centre" else 0.9}</scale><Icon><href>{h}</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle><LineStyle><color>ff00ffff</color><width>2</width></LineStyle><PolyStyle><fill>0</fill><outline>1</outline></PolyStyle></Style>'
    return s
def desc(p): return escape('<br>'.join(f'<b>{k}</b>: {v}' for k,v in p.items() if k not in('layer',)))
def folder(name,feats,filt=lambda p:True):
    out=f'<Folder><name>{escape(name)}</name>'
    for f in feats:
        p=f['properties']
        if not filt(p): continue
        k=p['kind']; nm=p.get('name') or f"{k} {p.get('id','')}".strip()
        if k=='canopy_loss_hotspot': nm=f"Canopy-loss hotspot: {p['ha']} ha lost (Hansen 2023–25 + RADD 2025–26)"
        
        out+=f'<Placemark><name>{escape(nm)}</name><description><![CDATA[{desc(p)}]]></description><styleUrl>#{k}</styleUrl>{geom_kml(shape(f["geometry"]))}</Placemark>'
    return out+'</Folder>'
L1=json.load(open('layers/L1_hydromet.geojson'))['features']; L2=json.load(open('layers/L2_gully.geojson'))['features']; L3=json.load(open('layers/L3_forest.geojson'))['features']
author='<description><![CDATA[Nigeria Regional Environmental Impact Map – designed by Mr. Dinar Wali, Geospatial Computational Researcher (RegenX.eco). dinar.wali@regenx.eco · linkedin.com/in/dinar-wali-621954102]]></description>'
doc=f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Nigeria Environmental Impact Map – 3 risk layers (D. Wali, Oct 2026)</name>{author}{styles()}'
doc+='<Folder><name>Layer 1 – Hydro-meteorological risk (flash floods)</name>'+folder('Mokwa, Niger State – 28–29 May 2025',L1,lambda p:p['site']=='Mokwa')+folder('Osogbo, Osun State – 29 Sep 2026',L1,lambda p:p['site']=='Osogbo')+'</Folder>'
doc+='<Folder><name>Layer 2 – Land degradation (gully erosion, Imo)</name>'+folder('VHR-verified active gullies (Okigwe escarpment; Obodo, Ideato North)',L2,lambda p:p['kind'] in ('verified_gully','gully_axis','gully_head','sediment_fan'))+folder('Excavation pits (gully-initiation risk)',L2,lambda p:p['kind']=='excavation_pit')+folder('Brief point & rejected/unverified screen hits',L2,lambda p:p['kind'] in ('centre','rejected_shoreline','unverified_candidate','gully_candidate','gully_axis_unverified'))+'</Folder>'
doc+='<Folder><name>Layer 3 – Vegetation dynamics (canopy loss / logging pressure)</name>'
for s in ['Oban / Cross River','Omo','Okomu']:
    doc+=folder(s,L3,lambda p,s=s:p['site']==s or (p['kind']=='centre' and s.split()[0] in p['site']))
doc+='</Folder></Document></kml>'
open('out/Nigeria_Environmental_Impact_Map.kml','w').write(doc)
print(len(doc)/1e6,'MB')
