"""WeatherNext 3 precipitation forecasts for the Nigeria EWS sites (Earth Engine)."""
import datetime as dt, json, sys
from pathlib import Path; HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent))
from eeinit import ee
EE_10 = 'projects/gcp-public-data-weathernext/assets/weathernext_3_0_0_0p1deg'
PCT = ('mean', 'p10', 'p25', 'p50', 'p75', 'p90')
BANDS = [f'total_precipitation_1hr_{p}' for p in PCT] + ['imerg_tp_1hr_mean']
# Areal sites: rainfall that matters for a flash flood falls on the catchment, not on the town pixel.
SITES = {
 'mokwa':   dict(name='Mokwa (town + upstream 15 km)', lon=5.0539, lat=9.2931, r=15000),
 'osogbo':  dict(name='Osogbo / upper Osun (25 km)',    lon=4.5624, lat=7.7827, r=25000),
 'okigwe':  dict(name='Okigwe escarpment gullies',      lon=7.3820, lat=5.8270, r=8000),
 'ideato':  dict(name='Obodo, Ideato North gully',      lon=7.0588, lat=5.8708, r=8000),
 'obolo':   dict(name='Obolo, Isiala Mbano (brief pt)', lon=7.1955, lat=5.6412, r=8000),
 'oban':    dict(name='Oban / Cross River',             lon=8.5360, lat=5.3000, r=15000),
}
def runs(lookback_h=36):
    now = dt.datetime.now(dt.UTC)
    c = ee.ImageCollection(EE_10).filterDate((now - dt.timedelta(hours=lookback_h)).isoformat()[:19], (now + dt.timedelta(hours=2)).isoformat()[:19])
    from collections import Counter
    n = Counter(c.aggregate_array('start_time').getInfo())
    long = {k: v for k, v in n.items() if v >= 240}
    return max(long) if long else max(n), n
def fetch(init, max_h=360, chunk=60):
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point(s['lon'], s['lat']).buffer(s['r']), {'k': k}) for k, s in SITES.items()])
    out = {k: {} for k in SITES}
    leads = list(range(1, max_h + 1))
    for i in range(0, len(leads), chunk):
        coll = (ee.ImageCollection(EE_10).filter(ee.Filter.eq('start_time', init))
                .filter(ee.Filter.inList('forecast_hour', leads[i:i + chunk])).select(BANDS))
        def samp(img):
            return img.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=11132).map(
                lambda f: f.set('fh', img.get('forecast_hour'), 'vt', img.get('end_time')))
        for f in coll.map(samp).flatten().getInfo()['features']:
            p = f['properties']
            out[p['k']][p['vt']] = {('imerg_mean' if b.startswith('imerg') else b.split('_')[-1]): (p.get(b) or 0) * 1000 for b in BANDS}  # m -> mm per hour
    return out
def daily(series):
    """Daily totals (UTC days). mean: exact sum of hourly means. hi_env: sum of hourly p90 = conservative UPPER ENVELOPE, not a daily p90."""
    d = {}
    for vt, r in sorted(series.items()):
        day = vt[:10]
        a = d.setdefault(day, {'mean': 0.0, 'imerg_mean': 0.0, 'p50': 0.0, 'hi_env': 0.0, 'lo_env': 0.0, 'hours': 0})
        a['imerg_mean'] += r.get('imerg_mean', 0.0); a['mean'] += r['mean']; a['p50'] += r['p50']; a['hi_env'] += r['p90']; a['lo_env'] += r['p10']; a['hours'] += 1
    return {k: {kk: round(vv, 1) if kk != 'hours' else vv for kk, vv in v.items()} for k, v in d.items()}
if __name__ == '__main__':
    init, counts = runs()
    print('synoptic init', init, 'steps', counts[init])
    s = fetch(init)
    res = {'init': init, 'fetched_utc': dt.datetime.now(dt.UTC).isoformat()[:19], 'sites': {}}
    for k, ser in s.items():
        res['sites'][k] = {'name': SITES[k]['name'], 'daily': daily(ser)}
        dd = res['sites'][k]['daily']
        full = {d: v for d, v in dd.items() if v['hours'] == 24}
        print(k, 'days', len(full), 'max daily mean', max((v['mean'], d) for d, v in full.items()), 'max hi_env', max((v['hi_env'], d) for d, v in full.items()))
    json.dump(res, open(str(HERE / 'wn3_latest.json'), 'w'), indent=1)
