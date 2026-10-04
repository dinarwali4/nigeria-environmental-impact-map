import rasterio, numpy as np, glob, json, zipfile, os
from scipy import ndimage as ndi
from skimage.measure import regionprops, label
rows=[]
for f in sorted(glob.glob('imo_wide/t*.tif')):
    src=rasterio.open(f); A=src.read().astype(np.float32); T=src.transform
    incis,slope,bsi,ndvi,wc,wd=A[0]/10,A[1]/10,A[2]/1000,A[3]/1000,A[4],A[5]
    bare=(bsi>0.03)&(ndvi<0.40)&(wc!=50)&(wc!=80)&(wd>150)
    m=bare&(incis<-3)&(slope>5)
    m=ndi.binary_closing(m,iterations=1)
    lab=label(m,connectivity=2)
    for rp in regionprops(lab):
        if rp.area<6: continue
        el=rp.axis_major_length/max(rp.axis_minor_length,1)
        rr,cc=rp.coords[:,0],rp.coords[:,1]
        inc=float(incis[rr,cc].mean())
        if el<4 or inc>-5: continue
        lon,lat=T*(rp.centroid[1]+.5,rp.centroid[0]+.5)
        rows.append(dict(lat=round(lat,5),lon=round(lon,5),ha=round(rp.area*0.04,2),len_m=round(rp.axis_major_length*20),elong=round(el,1),incis=round(inc,1),slope=round(float(slope[rr,cc].mean()),1),wdist=int(wd[rr,cc].min())))
# dedupe overlaps between tiles
uniq=[]
for r in sorted(rows,key=lambda r:(-r['len_m'])):
    if all(abs(r['lat']-u['lat'])>0.002 or abs(r['lon']-u['lon'])>0.002 for u in uniq): uniq.append(r)
for r in uniq: r['dist_km']=round(((r['lat']-5.6412)**2+((r['lon']-7.1955)*0.995)**2)**.5*111,1)
uniq.sort(key=lambda r:-(r['len_m']*-r['incis']))
print(len(uniq))
for r in uniq[:25]: print(r)
json.dump(uniq,open('out/imo_wide_candidates.json','w'),indent=1)
# ---- export polygons for wide candidates
from rasterio.features import shapes
from shapely.geometry import shape, mapping, LineString
from shapely.ops import unary_union
feats=[]
for f in sorted(glob.glob('imo_wide/t*.tif')):
    src=rasterio.open(f); A=src.read().astype(np.float32); T=src.transform
    incis,slope,bsi,ndvi,wc,wd=A[0]/10,A[1]/10,A[2]/1000,A[3]/1000,A[4],A[5]
    m=(bsi>0.03)&(ndvi<0.40)&(wc!=50)&(wc!=80)&(wd>150)&(incis<-3)&(slope>5)
    m=ndi.binary_closing(m,iterations=1); lab=label(m,connectivity=2)
    for rp in regionprops(lab):
        if rp.area<6: continue
        el=rp.axis_major_length/max(rp.axis_minor_length,1); rr,cc=rp.coords[:,0],rp.coords[:,1]; inc=float(incis[rr,cc].mean())
        if el<4 or inc>-5: continue
        mm=lab==rp.label; g=unary_union([shape(x) for x,v in shapes(mm.astype(np.uint8),mask=mm,transform=T)])
        cy,cx=rp.centroid; o=rp.orientation; Lh=rp.axis_major_length/2
        ax=LineString([T*(cx-np.sin(o)*Lh+.5,cy-np.cos(o)*Lh+.5),T*(cx+np.sin(o)*Lh+.5,cy+np.cos(o)*Lh+.5)])
        feats.append((g,ax,dict(len_m=round(rp.axis_major_length*20),incision_m=round(inc,1),slope_deg=round(float(slope[rr,cc].mean()),1),elong=round(el,1))))
json.dump([dict(poly=mapping(g),axis=mapping(a),**p) for g,a,p in feats],open('out/imo_wide_polys.json','w'))
print('polys',len(feats))
