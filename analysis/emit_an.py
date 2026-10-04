import numpy as np, json, rasterio
z=np.load('out/emit_imo_20241222.npz'); C=z['cube'].astype(np.float32); wl=z['wl']; gt=z['gt']
b=lambda w: np.argmin(abs(wl-w))
def band(w,hw=10):
    i=[j for j in range(len(wl)) if abs(wl[j]-w)<=hw]; return np.nanmean(C[...,i],axis=-1)
def bd(c,l,r):
    Rc,Rl,Rr=band(c),band(l),band(r); f=(c-l)/(r-l); cont=Rl+(Rr-Rl)*f; return 1-Rc/cont
ndvi=(band(860)-band(660))/(band(860)+band(660))
fe=bd(900,760,1050); kao=bd(2205,2120,2250); 
H,W=ndvi.shape
def rc(lon,lat): return int((lat-gt[3])/gt[5]), int((lon-gt[0])/gt[1])
rows=json.load(open('out/imo_cand_rows.json'))
def stat(arrs,mask): return {k:round(float(np.nanmedian(a[mask])),4) for k,a in arrs.items()}
A={'ndvi':ndvi,'fe900':fe,'kao2205':kao}
cand=np.zeros((H,W),bool)
for r in rows:
    y,x=rc(r['lon'],r['lat'])
    if 0<=y<H and 0<=x<W: cand[y,x]=True
# background classes via WorldCover sampled at EMIT pixel centres
wc=rasterio.open('out/imo_wc.tif'); W0=wc.read(1)
cls=np.zeros((H,W),int)
for y in range(H):
    for x in range(W):
        lon=gt[0]+(x+0.5)*gt[1]; lat=gt[3]+(y+0.5)*gt[5]
        try:
            rr,cc=wc.index(lon,lat); cls[y,x]=W0[rr,cc] if 0<=rr<W0.shape[0] and 0<=cc<W0.shape[1] else 0
        except: pass
print('candidate px',cand.sum())
print('candidates      ',stat(A,cand))
print('tree cover (10) ',stat(A,cls==10)); print('built-up (50)   ',stat(A,cls==50)); print('crop/grass(30/40)',stat(A,(cls==30)|(cls==40)))
# bare-soil pixels (NDVI<0.3) outside built
bare=(ndvi<0.3)&(cls!=50)
print('bare non-built  ',stat(A,bare),'n',bare.sum())
# per-candidate top 10
out=[]
for r in sorted(rows,key=lambda r:-r['ha'])[:12]:
    y,x=rc(r['lon'],r['lat'])
    out.append((r['lat'],r['lon'],r['ha'],round(float(ndvi[y,x]),2),round(float(fe[y,x]),3),round(float(kao[y,x]),3)))
for o in out: print(o)
np.savez('out/emit_imo_indices.npz',ndvi=ndvi,fe=fe,kao=kao,gt=gt)
