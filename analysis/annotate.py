from PIL import Image, ImageDraw, ImageFont
import math, sys, json
Image.MAX_IMAGE_PIXELS=None
FB='/System/Library/Fonts/Avenir Next.ttc'
def font(sz,bold=False): return ImageFont.truetype(FB,sz,index=(2 if bold else 5))
CREDIT='Designed by Mr. Dinar Wali — Geospatial Computational Researcher, RegenX.eco  ·  dinar.wali@regenx.eco  ·  linkedin.com/in/dinar-wali-621954102'
def annotate(src,out,centre,rng,title,subtitle,date_label,source,labels=[],legend=[],outw=3200,crop=None):
    im=Image.open(src).convert('RGB'); W,H=im.size
    mpp=1.1632*rng/W   # metres per native pixel (validated on Mokwa railway crossing)
    lon0,lat0=centre
    def px(lon,lat):
        dx=(lon-lon0)*111320*math.cos(math.radians(lat0)); dy=(lat-lat0)*110574
        return W/2+dx/mpp, H/2-dy/mpp
    s=outw/W; im=im.resize((outw,int(H*s)),Image.LANCZOS); W2,H2=im.size
    d=ImageDraw.Draw(im,'RGBA')
    # labels with leader lines
    for lb in labels:
        lon,lat,text=lb[:3]; dxo,dyo=(lb[3] if len(lb)>3 else (80,-80)); col=lb[4] if len(lb)>4 else (220,40,40,255)
        x,y=px(lon,lat); x*=s; y*=s
        tx,ty=x+dxo,y+dyo
        f=font(30,True); bb=d.textbbox((0,0),text,font=f)
        w,h=bb[2]-bb[0],bb[3]-bb[1]
        bx=tx if dxo>=0 else tx-w-24
        bx=min(max(bx,24),W2-w-60); ty=min(max(ty,170),H2-h-130)
        d.line([(x,y),(tx,ty+h/2+8)],fill=(255,255,255,255),width=4)
        d.ellipse([x-9,y-9,x+9,y+9],outline=(255,255,255,255),width=4,fill=col)
        d.rounded_rectangle([bx,ty,bx+w+24,ty+h+18],radius=8,fill=(10,20,30,215))
        d.text((bx+12,ty+4),text,font=f,fill=(255,255,255,255))
    # title bar
    d.rectangle([0,0,W2,150],fill=(8,18,28,225))
    d.text((40,18),title,font=font(54,True),fill=(255,255,255,255))
    d.text((40,92),subtitle,font=font(30),fill=(190,215,230,255))
    # date badge
    f=font(46,True); bb=d.textbbox((0,0),date_label,font=f)
    d.rounded_rectangle([W2-bb[2]-90,30,W2-30,124],radius=14,fill=(200,60,30,235))
    d.text((W2-bb[2]-60,44),date_label,font=f,fill=(255,255,255,255))
    # legend
    if legend:
        f=font(28); lh=46; lw=max(d.textbbox((0,0),t,font=f)[2] for _,t in legend)+110
        x0,y0=40,H2-130-lh*len(legend)-30
        d.rounded_rectangle([x0,y0,x0+lw,y0+lh*len(legend)+30],radius=12,fill=(8,18,28,215))
        for i,(c,t) in enumerate(legend):
            yy=y0+18+i*lh
            if c.startswith('line:'): d.line([(x0+20,yy+16),(x0+70,yy+16)],fill=c[5:],width=7)
            elif c.startswith('pin:'): d.ellipse([x0+33,yy+4,x0+57,yy+28],fill=c[4:],outline='white',width=3)
            else: d.rectangle([x0+20,yy+2,x0+70,yy+30],outline=c,width=5)
            d.text((x0+88,yy),t,font=f,fill=(255,255,255,255))
    # scale bar (nice length)
    mpp2=mpp/s; target=W2*0.18*mpp2
    nice=[50,100,200,250,500,1000,2000,5000]; L=min(nice,key=lambda n:abs(n-target)); Lpx=L/mpp2
    x1,y1=W2-80-Lpx,H2-170
    d.rectangle([x1-20,y1-50,x1+Lpx+20,y1+30],fill=(8,18,28,200))
    d.rectangle([x1,y1,x1+Lpx/2,y1+14],fill='white'); d.rectangle([x1+Lpx/2,y1,x1+Lpx,y1+14],fill=(30,30,30),outline='white',width=2)
    d.text((x1,y1-44),f"{L if L<1000 else L//1000} {'m' if L<1000 else 'km'}",font=font(30,True),fill='white')
    # north arrow
    nx,ny=W2-110,220
    d.polygon([(nx,ny-55),(nx-26,ny+25),(nx,ny+8),(nx+26,ny+25)],fill='white',outline=(20,20,20))
    d.text((nx-12,ny+30),'N',font=font(36,True),fill='white')
    # footer
    d.rectangle([0,H2-90,W2,H2],fill=(8,18,28,230))
    d.text((40,H2-80),source,font=font(24),fill=(200,220,230,255))
    d.text((40,H2-46),CREDIT,font=font(24,True),fill=(255,255,255,255))
    im.save(out,quality=90); print('saved',out,im.size)
    return im
if __name__=='__main__':
    for i in range(6):
        try: print(i,ImageFont.truetype(FB,20,index=i).getname())
        except Exception as e: print(i,e); break
