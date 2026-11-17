"""Reproduce the README figures from the local HydroSHEDS tiles and the delineated catchment.

Usage (from the repo root, after setup_env.bat and tiling):
    python scripts/make_figures.py

Independently re-traces the catchment from the raw D8 tile, compares it with the
OpenHydroNet polygon, and writes three PNGs to figures/.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); os.makedirs('figures', exist_ok=True)
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.colors import LinearSegmentedColormap
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; MUTED='#898781'; GRID='#e1e0d9'; AXIS='#c3c2b7'; BLUE='#2a78d6'; ORANGE='#eb6834'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.edgecolor':AXIS,'axes.labelcolor':INK2,'xtick.color':MUTED,'ytick.color':MUTED,'text.color':INK,'figure.facecolor':SURF,'axes.facecolor':SURF,'savefig.facecolor':SURF})
res=1/1200
T=np.load('data/tiles_5deg/n45e010.npy',mmap_mode='r')
r0,r1=int((45-44.60)*1200), int((45-43.90)*1200); c0,c1=int((10.70-10)*1200), int((11.45-10)*1200)
D=np.array(T[r0:r1,c0:c1]); H,W=D.shape
off={1:(0,1),2:(1,1),4:(1,0),8:(1,-1),16:(0,-1),32:(-1,-1),64:(-1,0),128:(-1,1)}
dr=np.zeros(D.shape,int);dc=np.zeros(D.shape,int);valid=np.zeros(D.shape,bool)
for k,(a,b) in off.items(): m=D==k; dr[m]=a; dc[m]=b; valid|=m
R,C=np.indices(D.shape); tr=R+dr; tc=C+dc
inb=valid&(tr>=0)&(tr<H)&(tc>=0)&(tc<W)
down=np.full(D.size,-1); down[inb.ravel()]=(tr*W+tc)[inb]
lat=45-(r0+R+0.5)*res; lon=10+(c0+C+0.5)*res
area=(res*111.32)*(res*111.32*np.cos(np.radians(lat)))
indeg=np.bincount(down[down>=0],minlength=D.size); acc=area.ravel().copy(); order=[]
q=np.where(indeg==0)[0]
while q.size:
    order.append(q); d=down[q]; m=d>=0
    np.add.at(acc,d[m],acc[q[m]]); np.subtract.at(indeg,d[m],1)
    cand=np.unique(d[m]); q=cand[indeg[cand]==0]
acc=acc.reshape(D.shape)
glat,glon=44.4825,11.28417
gr=int((45-glat)*1200)-r0; gc=int((glon-10)*1200)-c0
w=acc[gr-2:gr+3,gc-2:gc+3]; i,j=np.unravel_index(w.argmax(),w.shape); orr,occ=gr-2+i,gc-2+j
o=orr*W+occ
dy=res*111.32; dx=res*111.32*np.cos(np.radians(lat.ravel()))
steplen=np.sqrt((dr.ravel()*dy)**2+(dc.ravel()*dx)**2)
inside=np.zeros(D.size,bool); inside[o]=True; dist=np.full(D.size,np.nan); dist[o]=0
for q in order[::-1]:
    d=down[q]; m=(d>=0)&(q!=o); qq=q[m]; dd=d[m]; inside[qq]=inside[dd]; dist[qq]=dist[dd]+steplen[qq]
inside=inside.reshape(D.shape); dist=dist.reshape(D.shape)
myarea=area[inside].sum()
# google polygon raster
g=json.load(open('data/casalecchio/casalecchio_425.geojson'))
poly=np.array(g['features'][0]['geometry']['coordinates'][0])
pin=Path(poly).contains_points(np.c_[lon.ravel(),lat.ravel()]).reshape(D.shape)
inter=(pin&inside).sum(); uni=(pin|inside).sum()
L=np.nanmax(dist[inside])
stats=dict(my_area=myarea,poly_area_cells=area[pin].sum(),iou=inter/uni,maxlen=L,cells=int(inside.sum()))
print({k: round(float(v), 4) for k, v in stats.items()})


# ---- Fig 1: catchment map
ext=[10+c0*res,10+c1*res,45-r1*res,45-r0*res]
fig,ax=plt.subplots(figsize=(7.2,6.6),dpi=160)
shade=np.where(inside,1.0,np.nan)
ax.imshow(shade,extent=ext,cmap=LinearSegmentedColormap.from_list('s',['#eef4fc','#eef4fc']),vmin=0,vmax=1,interpolation='nearest')
from scipy.ndimage import grey_dilation
la0=np.where((acc>=5)&inside,np.log10(np.maximum(acc,1e-9)),-1)
la=grey_dilation(la0,size=(3,3)); la=np.where(la>0,la,np.nan)
cm=LinearSegmentedColormap.from_list('b',['#86b6ef','#2a78d6','#104281'])
im=ax.imshow(la,extent=ext,cmap=cm,vmin=np.log10(5),vmax=np.log10(1100),interpolation='nearest')
ax.plot(poly[:,0],poly[:,1],color=INK,lw=1.4,label='Delineated catchment (OpenHydroNet tool)')
ax.plot([glon],[glat],marker='o',ms=9,mfc=ORANGE,mec=SURF,mew=2,ls='none',label='Outlet: Reno at Casalecchio di Reno')
ax.annotate('Outlet\n44.483 N, 11.284 E',(glon,glat),xytext=(14,4),textcoords='offset points',fontsize=9,color=INK2,va='center')
ax.set_aspect(1/np.cos(np.radians(44.2)))
ax.set_xlim(10.74,11.40); ax.set_ylim(43.94,44.55)
ax.set_xlabel('Longitude (°E)'); ax.set_ylabel('Latitude (°N)')
ax.grid(color=GRID,lw=0.6); ax.set_axisbelow(True)
for s in ['top','right']: ax.spines[s].set_visible(False)
ax.legend(loc='lower right',frameon=True,facecolor=SURF,edgecolor=GRID,fontsize=8.5)
cb=fig.colorbar(im,ax=ax,shrink=0.6,pad=0.02); cb.set_label('Upstream area (km², log scale)',color=INK2)
t=[5,10,50,100,500,1000]; cb.set_ticks(np.log10(t)); cb.set_ticklabels([str(x) for x in t]); cb.outline.set_edgecolor(AXIS); cb.ax.tick_params(colors=MUTED)
fig.text(0.03,0.975,'Reno catchment above Casalecchio — 1,050 km²',fontsize=12,color=INK,fontweight='bold',va='top')
fig.text(0.03,0.94,'River network from HydroSHEDS 3″ D8 flow directions (cells draining ≥ 5 km²)',fontsize=8.5,color=INK2,va='top')
fig.tight_layout(rect=(0,0,1,0.92)); fig.savefig('figures/catchment_map.png'); plt.close()

# ---- Fig 2: width function
dd=dist[inside]; aa=area[inside]
bins=np.arange(0,np.ceil(L/2)*2+2,2)
h,_=np.histogram(dd,bins=bins,weights=aa)
fig,ax=plt.subplots(figsize=(7.2,3.6),dpi=160)
ax.bar(bins[:-1]+1,h,width=2*0.85,color=BLUE,edgecolor=SURF,lw=0)
ax.set_xlabel('Flow distance to outlet (km)'); ax.set_ylabel('Contributing area (km² per 2 km)')
ax.grid(axis='y',color=GRID,lw=0.6); ax.set_axisbelow(True)
for s in ['top','right','left']: ax.spines[s].set_visible(False)
ax.tick_params(axis='y',length=0)
pk=bins[np.argmax(h)]+1
ax.annotate(f'Peak ≈ {pk:.0f} km',(pk,h.max()),xytext=(8,0),textcoords='offset points',fontsize=9,color=INK2,va='center')
ax.axvline(L,color=MUTED,lw=1,ls=(0,(3,3)))
ax.text(L,h.max()*0.95,f' Longest flow path\n {L:.0f} km',fontsize=9,color=INK2,va='top',ha='right')
ax.set_title('Width function: how much of the basin drains from each distance',loc='left',fontsize=12,fontweight='bold')
fig.tight_layout(); fig.savefig('figures/width_function.png'); plt.close()

# ---- Fig 3: tile coverage
import re
names=sorted(f[:-4] for f in os.listdir('data/tiles_5deg') if f.endswith('.npy'))
fig,ax=plt.subplots(figsize=(7.2,4.4),dpi=160)
from matplotlib.patches import Rectangle
for n in names:
    mm=re.match(r'n(\d+)([ew])(\d+)',n); top=int(mm.group(1)); lf=int(mm.group(3))*(1 if mm.group(2)=='e' else -1)
    used=(n=='n45e010')
    ax.add_patch(Rectangle((lf,top-5),5,5,facecolor=BLUE if used else '#e1e0d9',edgecolor=SURF,lw=2))
ax.plot([glon],[glat],marker='o',ms=6,mfc=ORANGE,mec=SURF,mew=1.5)
ax.annotate('Casalecchio basin lies in a single tile\n(n45e010, 36 MB)',(10,40.5),xytext=(-15,22),textcoords='data',fontsize=9,color=INK2,arrowprops=dict(arrowstyle='-',color=MUTED,lw=0.8))
ax.set_xlim(-16,71); ax.set_ylim(9,61); ax.set_aspect(1.25)
ax.set_xlabel('Longitude (°)'); ax.set_ylabel('Latitude (°N)')
for s in ['top','right']: ax.spines[s].set_visible(False)
ax.set_title('108 HydroSHEDS tiles prepared (3.9 GB) — 1 needed',loc='left',fontsize=12,fontweight='bold')
fig.tight_layout(); fig.savefig('figures/tile_coverage.png'); plt.close()
