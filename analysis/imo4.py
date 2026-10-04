import rasterio, numpy as np, json
from scipy import ndimage as ndi
from skimage.measure import regionprops, label
R={b:rasterio.open(f'out/imo_{b}.tif') for b in ['incis','slope','bsi26','ndvi26','bsi18','ndvi18','wc']}
A={b:r.read(1) for b,r in R.items()}
shp={b:a.shape for b,a in A.items()}; print(shp)
H=min(a.shape[0] for a in A.values()); W=min(a.shape[1] for a in A.values())
A={b:a[:H,:W] for b,a in A.items()}
T=R['bsi26'].transform
notbuilt=(A['wc']!=50)&(A['wc']!=80)
bare26=(A['bsi26']>0.05)&(A['ndvi26']<0.35)&notbuilt
bare18=(A['bsi18']>0.05)&(A['ndvi18']<0.35)&notbuilt
inc=(A['incis']<-3)&(A['slope']>6)
cand=ndi.binary_closing(bare26&ndi.binary_dilation(inc,iterations=2),iterations=1)
lab=label(cand,connectivity=2)
rows=[]
for rp in regionprops(lab):
    if rp.area<20: continue
    elong=rp.major_axis_length/max(rp.minor_axis_length,1)
    rr,cc=rp.coords[:,0],rp.coords[:,1]
    lon,lat=T*(rp.centroid[1]+0.5,rp.centroid[0]+0.5)
    rows.append(dict(id=rp.label,ha=rp.area*0.01*(1.0),lat=round(lat,5),lon=round(lon,5),elong=round(elong,1),
        incis=round(float(A['incis'][rr,cc].mean()),1),slope=round(float(A['slope'][rr,cc].mean()),1),
        bare18_frac=round(float(bare18[rr,cc].mean()),2)))
# pixel size in m: deg->m
print('pix deg',T.a, 'm',T.a*111320*np.cos(np.radians(5.64)))
rows.sort(key=lambda r:-r['ha'])
for r in rows[:40]: print(r)
print('n',len(rows))
np.save('out/imo_lab.npy',lab)
json.dump(rows,open('out/imo_cand_rows.json','w'))
