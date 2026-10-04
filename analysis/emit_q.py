import json, urllib.request, sys
sites={'imo_gully':(7.1610,5.6050),'imo_pt':(7.1955,5.6412),'mokwa':(5.0500,9.3000),'oban':(8.5302,5.2890),'omo':(4.2802,6.9616),'okomu':(5.0696,6.2996),'osogbo':(4.5624,7.7827)}
res={}
for k,(lon,lat) in sites.items():
    url=f"https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=EMITL2ARFL&version=001&point={lon},{lat}&page_size=200"
    d=json.load(urllib.request.urlopen(url))
    rows=[]
    for it in d['items']:
        u=it['umm']; t=u['TemporalExtent']['RangeDateTime']['BeginningDateTime'][:16]
        cc=u.get('CloudCover'); rows.append((t,cc,u['GranuleUR']))
    rows.sort(); res[k]=rows
    print(k,d['hits'],'hits; low-cloud (<30%):',[(r[0],r[1]) for r in rows if r[1] is not None and r[1]<30])
json.dump(res,open('out/emit_granules.json','w'),indent=1)
