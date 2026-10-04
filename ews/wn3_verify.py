import sys, json, datetime as dt
from pathlib import Path; HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE.parent)); sys.path.insert(0,str(HERE))
from eeinit import ee
from wn3 import EE_10, SITES
from collections import Counter
c=ee.ImageCollection(EE_10).filterDate('2026-09-20','2026-10-05')
n=Counter(c.aggregate_array('start_time').getInfo())
syn=sorted(k for k,v in n.items() if v>=240)
print('retained long runs:',len(syn),syn[0] if syn else None,'->',syn[-1] if syn else None)
IM=ee.ImageCollection('NASA/GPM_L3/IMERG_V07').select('precipitation')
last_im=ee.Date(IM.filterDate('2026-09-25','2026-10-05').aggregate_max('system:time_start')).format("YYYY-MM-dd'T'HH:mm").getInfo()
print('IMERG last:',last_im)
fc=ee.FeatureCollection([ee.Feature(ee.Geometry.Point(s['lon'],s['lat']).buffer(s['r']),{'k':k}) for k,s in SITES.items()])
rows=[]
LIM=ee.Date(last_im).millis().getInfo()
syn=[x for x in syn if x[11:13] in ('00','12')]
for init in syn:
    t0=ee.Date(init)
    for lead_day in [1,2,3]:
        a=t0.advance((lead_day-1)*24,'hour'); b=a.advance(24,'hour')
        import datetime as _d
        if (_d.datetime.fromisoformat(init.replace('Z','+00:00'))+_d.timedelta(hours=lead_day*24)).timestamp()*1000>LIM: continue
        f=(ee.ImageCollection(EE_10).filter(ee.Filter.eq('start_time',init)).filter(ee.Filter.rangeContains('forecast_hour',(lead_day-1)*24+1,lead_day*24))
           .select(['total_precipitation_1hr_mean','imerg_tp_1hr_mean','total_precipitation_1hr_p90']).sum().multiply(1000))
        o=IM.filterDate(a,b).sum().multiply(0.5).rename('obs')
        r=f.addBands(o).reduceRegions(fc,ee.Reducer.mean(),11132).getInfo()
        for x in r['features']:
            p=x['properties']; rows.append(dict(init=init,lead=lead_day,site=p['k'],fc=round(p['total_precipitation_1hr_mean'],1),fc_imerg=round(p['imerg_tp_1hr_mean'],1),hi_env=round(p['total_precipitation_1hr_p90'],1),obs=round(p['obs'],1)))
json.dump(rows,open(str(HERE / 'wn3_verification.json'),'w'),indent=1)
import statistics as st
for L in [1,2,3]:
    R=[r for r in rows if r['lead']==L]
    if not R: continue
    for key in ['fc','fc_imerg']:
        e=[r[key]-r['obs'] for r in R]
        print(f'lead day {L} {key:9s} n={len(R)} bias={st.mean(e):+.1f} mm  MAE={st.mean(abs(x) for x in e):.1f} mm  obs mean={st.mean(r["obs"] for r in R):.1f}')
