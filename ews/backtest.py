import sys, json, random
from pathlib import Path; HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE.parent))
from eeinit import ee
ng=ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017').filter(ee.Filter.eq('country_na','Nigeria')).geometry()
gs=(ee.FeatureCollection('projects/sat-io/open-datasets/groundsource_2026').filterBounds(ng)
    .filter(ee.Filter.lt('area_km2',50)).filter(ee.Filter.gte('start_date','2001-01-02')))
n=gs.size().getInfo(); print('Nigerian Groundsource events <50 km2 since 2001:',n)
yrs=gs.aggregate_array('start_date').getInfo()
from collections import Counter
print('by year',sorted(Counter(y[:4] for y in yrs).items()))
# dedupe: one record per ~10 km cell per date
gs=gs.map(lambda f: f.set('cx',f.geometry().centroid(100).coordinates().get(0),'cy',f.geometry().centroid(100).coordinates().get(1)))
rows=gs.reduceColumns(ee.Reducer.toList(4),['start_date','cx','cy','area_km2']).get('list').getInfo()
seen=set(); ev=[]
for d,x,y,a in rows:
    k=(d,round(x,1),round(y,1))
    if k in seen: continue
    seen.add(k); ev.append((d,x,y,a))
print('deduplicated events:',len(ev))
random.seed(7); sample=random.sample(ev,min(700,len(ev)))
IM=ee.ImageCollection('NASA/GPM_L3/IMERG_V07').select('precipitation')
def feats(evs,label):
    out=[]
    for d,x,y,a in evs:
        out.append(ee.Feature(ee.Geometry.Point(x,y),{'date':d,'label':label}))
    return out
# controls: same location & day-of-year, 3 different years (2001-2025), skipping years with a record at that cell within +-5 days
evset={}
for d,x,y,a in ev: evset.setdefault((round(x,1),round(y,1)),[]).append(d)
import datetime as dt
ctrl=[]
for d,x,y,a in sample:
    D=dt.date.fromisoformat(d); cell=(round(x,1),round(y,1))
    cands=[yy for yy in range(2001,2026) if yy!=D.year]
    random.shuffle(cands); k=0
    for yy in cands:
        try: C=D.replace(year=yy)
        except ValueError: continue
        if any(abs((dt.date.fromisoformat(e)-C).days)<=5 for e in evset[cell]): continue
        ctrl.append((C.isoformat(),x,y,a)); k+=1
        if k==3: break
fc=ee.FeatureCollection(feats(sample,1)+feats(ctrl,0))
def rain(f):
    d=ee.Date(f.get('date'))
    def day(k):
        a=d.advance(k,'day'); return IM.filterDate(a,a.advance(1,'day')).sum().multiply(0.5)
    mx=ee.ImageCollection([day(-1),day(0),day(1)]).max().rename('r1')
    s3=day(-2).add(day(-1)).add(day(0)).rename('r3')
    v=mx.addBands(s3).reduceRegion(ee.Reducer.mean(),f.geometry().buffer(5000),11132)
    return f.set('r1',v.get('r1'),'r3',v.get('r3'))
res=[]
lst=fc.toList(fc.size()); N=fc.size().getInfo()
for i in range(0,N,250):
    part=ee.FeatureCollection(lst.slice(i,i+250)).map(rain).getInfo()['features']
    res+= [dict(label=p['properties']['label'],date=p['properties']['date'],lon=p['geometry']['coordinates'][0],lat=p['geometry']['coordinates'][1],r1=p['properties'].get('r1'),r3=p['properties'].get('r3')) for p in part]
    print('done',min(i+250,N),'/',N)
json.dump(res,open(str(HERE / 'backtest_rows.json'),'w'))
