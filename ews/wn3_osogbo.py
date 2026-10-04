import sys, json
from pathlib import Path; HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE.parent)); sys.path.insert(0,str(HERE))
from eeinit import ee
from wn3 import EE_10, SITES
s=SITES['osogbo']; g=ee.Geometry.Point(s['lon'],s['lat']).buffer(s['r'])
day0=ee.Date('2026-09-28T00:00:00'); day1=day0.advance(1,'day')
IM=ee.ImageCollection('NASA/GPM_L3/IMERG_V07').select('precipitation')
obs=IM.filterDate(day0,day1).sum().multiply(0.5).reduceRegion(ee.Reducer.mean(),g,11132).get('precipitation').getInfo()
print('IMERG 28 Sep (25 km areal mean):',round(obs,1),'mm')
out=[]
for init in ['2026-09-21T00:00:00Z','2026-09-22T00:00:00Z','2026-09-23T00:00:00Z','2026-09-24T00:00:00Z','2026-09-25T00:00:00Z','2026-09-26T00:00:00Z','2026-09-27T00:00:00Z','2026-09-27T12:00:00Z']:
    c=(ee.ImageCollection(EE_10).filter(ee.Filter.eq('start_time',init)).filterDate(day0,day1.advance(1,'second'))
       .filter(ee.Filter.gt('system:time_start',0)))
    c=ee.ImageCollection(EE_10).filter(ee.Filter.eq('start_time',init)).filter(ee.Filter.rangeContains('forecast_hour',
        int((ee.Date('2026-09-28').millis().getInfo()-ee.Date(init).millis().getInfo())/3.6e6)+1,
        int((ee.Date('2026-09-29').millis().getInfo()-ee.Date(init).millis().getInfo())/3.6e6)))
    n=c.size().getInfo()
    v=c.select(['total_precipitation_1hr_mean','total_precipitation_1hr_p90','imerg_tp_1hr_mean']).sum().multiply(1000).reduceRegion(ee.Reducer.mean(),g,11132).getInfo()
    lead=round((ee.Date('2026-09-28').millis().getInfo()-ee.Date(init).millis().getInfo())/8.64e7,1)
    out.append(dict(init=init,lead_days=lead,hours=n,mean=round(v['total_precipitation_1hr_mean'],1),hi_env=round(v['total_precipitation_1hr_p90'],1),imerg_flavour=round(v['imerg_tp_1hr_mean'],1)))
    print(out[-1])
json.dump({'obs_imerg_mm':round(obs,1),'forecasts':out},open(str(HERE / 'wn3_osogbo_test.json'),'w'),indent=1)
# baselines over the verification set
rows=json.load(open(str(HERE / 'wn3_verification.json')))
import statistics as st
from collections import defaultdict
bys=defaultdict(list)
for r in rows: bys[r['site']].append(r['obs'])
clim={k:st.mean(v) for k,v in bys.items()}
for L in [1,2,3]:
    R=[r for r in rows if r['lead']==L]
    print('lead',L,'MAE WN3',round(st.mean(abs(r['fc']-r['obs']) for r in R),1),' WN3-imerg',round(st.mean(abs(r['fc_imerg']-r['obs']) for r in R),1),' climatology(site mean, in-sample)',round(st.mean(abs(clim[r['site']]-r['obs']) for r in R),1))
# heavy-day detection: obs >= 20 mm
for L in [1,2,3]:
    R=[r for r in rows if r['lead']==L]; ev=[r for r in R if r['obs']>=20]; non=[r for r in R if r['obs']<20]
    for th in [10,15,20]:
        hit=sum(r['fc_imerg']>=th for r in ev); fa=sum(r['fc_imerg']>=th for r in non)
        print(f' lead {L} obs>=20mm days={len(ev)}  fc_imerg>={th}: hits {hit}/{len(ev)}  false alarms {fa}/{len(non)}')
