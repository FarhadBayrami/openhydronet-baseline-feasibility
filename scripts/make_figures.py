"""Catchment analysis and README figures for the Reno at Casalecchio.

Run from the repo root after setup_env.bat and tiling:
    python scripts/make_figures.py

Inputs : data/tiles_5deg/n45e010.npy  (HydroSHEDS 3" D8 tile, git-ignored)
         data/casalecchio/casalecchio_425.geojson
Outputs: figures/*.png and results/catchment_metrics.json

Everything is computed independently of the OpenHydroNet delineator:
flow accumulation, upstream trace, flow distances, Strahler orders,
main stem, tributaries and outlet sensitivity.
"""
import json, os, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from scipy.ndimage import grey_dilation
try:
    from pyproj import Geod
except ImportError:
    Geod = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
os.makedirs('figures', exist_ok=True); os.makedirs('results', exist_ok=True)

# ------------------------------------------------------------------ style
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; MUTED='#898781'; GRID='#e1e0d9'; AXIS='#c3c2b7'
BLUE='#2a78d6'; ORANGE='#eb6834'
CAT=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#6250d6']
RAMP=['#86b6ef','#5598e7','#2a78d6','#1c5cab','#104281','#0d366b']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.edgecolor':AXIS,
    'axes.labelcolor':INK2,'xtick.color':MUTED,'ytick.color':MUTED,'text.color':INK,
    'figure.facecolor':SURF,'axes.facecolor':SURF,'savefig.facecolor':SURF})

def style(ax, grid='both'):
    for s in ['top','right']: ax.spines[s].set_visible(False)
    if grid: ax.grid(axis=grid if grid!='both' else 'both', color=GRID, lw=0.6)
    ax.set_axisbelow(True)

def title(fig, t, sub=None):
    fig.text(0.02,0.98,t,fontsize=12,fontweight='bold',va='top')
    if sub: fig.text(0.02,0.935,sub,fontsize=8.5,color=INK2,va='top')

# ------------------------------------------------------------------ data
RES = 1/1200; R_AUTH = 6371.0072      # 3 arc-second cells; authalic Earth radius (km)
TILE_TOP, TILE_LEFT = 45, 10
GAUGE = (44.4825, 11.28417)
TOOL_AREA = 1050.1; REF_AREA = 1053.0
tile = np.load('data/tiles_5deg/n45e010.npy', mmap_mode='r')
r0, r1 = int((TILE_TOP-44.60)/RES), int((TILE_TOP-43.90)/RES)
c0, c1 = int((10.70-TILE_LEFT)/RES), int((11.45-TILE_LEFT)/RES)
D = np.array(tile[r0:r1, c0:c1]); H, W = D.shape; N = D.size
geo = json.load(open('data/casalecchio/casalecchio_425.geojson'))
poly = np.array(geo['features'][0]['geometry']['coordinates'][0])

OFF = {1:(0,1),2:(1,1),4:(1,0),8:(1,-1),16:(0,-1),32:(-1,-1),64:(-1,0),128:(-1,1)}
dr = np.zeros(D.shape,int); dc = np.zeros(D.shape,int); valid = np.zeros(D.shape,bool)
for k,(a,b) in OFF.items():
    m = D==k; dr[m]=a; dc[m]=b; valid |= m
R, C = np.indices(D.shape); tr, tc = R+dr, C+dc
inb = valid & (tr>=0)&(tr<H)&(tc>=0)&(tc<W)
down = np.full(N,-1); down[inb.ravel()] = (tr*W+tc)[inb]
lat = TILE_TOP-(r0+R+0.5)*RES; lon = TILE_LEFT+(c0+C+0.5)*RES
# exact cell area on the authalic sphere
lat_n, lat_s = np.radians(lat+RES/2), np.radians(lat-RES/2)
area = (R_AUTH**2*np.radians(RES)*(np.sin(lat_n)-np.sin(lat_s))).ravel()
dy = R_AUTH*np.radians(RES); dx = dy*np.cos(np.radians(lat.ravel()))
step = np.sqrt((dr.ravel()*dy)**2+(dc.ravel()*dx)**2)

# topological order (sources first) + flow accumulation
indeg = np.bincount(down[down>=0], minlength=N); levels=[]; acc=area.copy()
q = np.where(indeg==0)[0]
while q.size:
    levels.append(q); d=down[q]; m=d>=0
    np.add.at(acc,d[m],acc[q[m]]); np.subtract.at(indeg,d[m],1)
    cand=np.unique(d[m]); q=cand[indeg[cand]==0]

# upstream neighbour lists (CSR)
src = np.where(down>=0)[0]; srt = np.argsort(down[src],kind='stable'); up_src = src[srt]
up_ptr = np.searchsorted(down[src][srt], np.arange(N+1))
def ups(i): return up_src[up_ptr[i]:up_ptr[i+1]]

def rc(la,lo): return int((TILE_TOP-la)/RES)-r0, int((lo-TILE_LEFT)/RES)-c0
gr, gc = rc(*GAUGE)
win = acc.reshape(D.shape)[gr-2:gr+3, gc-2:gc+3]
i, j = np.unravel_index(win.argmax(), win.shape); OUT = (gr-2+i)*W+(gc-2+j)

def trace(o):
    ins = np.zeros(N,bool); ins[o]=True; dist=np.full(N,np.nan); dist[o]=0
    for q in levels[::-1]:
        d=down[q]; m=(d>=0)&(q!=o); qq=q[m]; dd=d[m]
        ins[qq]=ins[dd]; dist[qq]=dist[dd]+step[qq]
    return ins, dist
inside, dist = trace(OUT)
A_cells = area[inside].sum()
pin = Path(poly).contains_points(np.c_[lon.ravel(), lat.ravel()])
iou = (pin&inside).sum()/(pin|inside).sum()
L = np.nanmax(dist[inside])

# ------------------------------------------------------------------ shape metrics
if Geod:
    a_geo, p_geo = Geod(ellps='WGS84').polygon_area_perimeter(poly[:,0], poly[:,1])
    A_geo, P_geo = abs(a_geo)/1e6, p_geo/1e3
else:
    A_geo, P_geo = A_cells, np.nan
olat, olon = lat.ravel()[OUT], lon.ravel()[OUT]
ddy = (lat.ravel()-olat)*111.2; ddx = (lon.ravel()-olon)*111.2*np.cos(np.radians(olat))
Lb = np.sqrt(ddx**2+ddy**2)[inside].max()
shape = dict(
    gravelius_Kc = P_geo/(2*np.sqrt(np.pi*A_geo)),
    circularity_Rc = 4*np.pi*A_geo/P_geo**2,
    elongation_Re = 2*np.sqrt(A_geo/np.pi)/Lb,
    form_factor_Rf = A_geo/Lb**2,
)

# ------------------------------------------------------------------ Strahler orders
def strahler(thr):
    stream = (acc>=thr)&inside
    order = np.zeros(N,np.int16); maxin=np.zeros(N,np.int16); nmax=np.zeros(N,np.int16)
    for q in levels:
        q = q[stream[q]]
        if not q.size: continue
        o = np.where(nmax[q]>=2, maxin[q]+1, np.maximum(maxin[q],1)).astype(np.int16)
        order[q]=o
        d=down[q]; m=(d>=0)
        d=d[m]; o=o[m]; m2=stream[d]; d=d[m2]; o=o[m2]
        for dd_, oo in zip(d.tolist(), o.tolist()):
            if oo>maxin[dd_]: maxin[dd_]=oo; nmax[dd_]=1
            elif oo==maxin[dd_]: nmax[dd_]+=1
    starts = stream & (order>maxin)
    return stream, order, starts
THR = 1.0
stream, order, starts = strahler(THR)
omax = int(order.max())
N_u = np.array([starts[order==u].sum() for u in range(1,omax+1)])
L_u = np.array([step[(order==u)&stream].sum() for u in range(1,omax+1)])
Rb = np.mean(N_u[:-1]/N_u[1:]); Dd = L_u.sum()/A_cells
thr_list = np.array([0.1,0.25,0.5,1,2,5,10,25,50])
Dd_list = np.array([step[(acc>=t)&inside].sum()/A_cells for t in thr_list])

# ------------------------------------------------------------------ main stem + tributaries
main=[OUT]; cur=OUT
while True:
    u = ups(cur); u = u[inside[u]] if u.size else u
    if not u.size: break
    cur = u[np.argmax(acc[u])]; main.append(cur)
main = np.array(main); main_set=set(main.tolist())
tribs=[]
for k,mc in enumerate(main):
    for u in ups(mc):
        if u in main_set: continue
        if acc[u]>=20: tribs.append(dict(cell=int(u), area=float(acc[u]), dist=float(dist[mc]),
                                         lat=float(lat.ravel()[mc]), lon=float(lon.ravel()[mc])))
tribs.sort(key=lambda t:-t['area'])
TOP = tribs[:6]
label = np.full(N,-1,np.int8)
for k,t in enumerate(TOP): label[t['cell']]=k
for q in levels[::-1]:
    d=down[q]; m=(d>=0)&(label[q]<0)&inside[q]; label[q[m]]=label[d[m]]
# outlet sensitivity along main stem (upstream) and downstream of the gauge
dn=[]; cur=OUT
while down[cur]>=0 and len(dn)<400: cur=down[cur]; dn.append(cur)
dn=np.array(dn)
sens_x = np.r_[-np.cumsum(step[np.r_[OUT,dn[:-1]]])[::-1], dist[main]]
sens_y = np.r_[acc[dn][::-1], acc[main]]

def area_at(km): return float(np.interp(km, sens_x, sens_y))
metrics = dict(
    outlet_sensitivity_km2={str(k):round(area_at(k),1) for k in (-2,-1,0,1,2,5,14,15)},
    tool_area_km2=TOOL_AREA, reference_area_km2=REF_AREA,
    geodesic_area_km2=round(A_geo,1), geodesic_perimeter_km=round(P_geo,1),
    retrace_area_km2=round(float(A_cells),1), iou_retrace_vs_polygon=round(float(iou),4),
    cells=int(inside.sum()), longest_flow_path_km=round(float(L),1),
    main_stem_length_km=round(float(dist[main[-1]]),1), basin_length_km=round(float(Lb),1),
    mean_flow_distance_km=round(float(np.average(dist[inside],weights=area[inside])),1),
    **{k:round(float(v),3) for k,v in shape.items()},
    stream_threshold_km2=THR, max_strahler_order=omax,
    streams_per_order=N_u.tolist(), length_per_order_km=[round(float(x),1) for x in L_u],
    bifurcation_ratio=round(float(Rb),2), drainage_density_km_per_km2=round(float(Dd),3),
    drainage_density_vs_threshold={str(t):round(float(v),3) for t,v in zip(thr_list,Dd_list)},
    tributaries_ge_20km2=[{k:(round(v,4) if isinstance(v,float) else v) for k,v in t.items() if k!='cell'} for t in tribs],
)
json.dump(metrics, open('results/catchment_metrics.json','w'), indent=2)
print(json.dumps({k:v for k,v in metrics.items() if k!='tributaries_ge_20km2'}, indent=1))
for t in tribs[:10]: print(t)

# ------------------------------------------------------------------ figures
ext=[TILE_LEFT+c0*RES, TILE_LEFT+c1*RES, TILE_TOP-r1*RES, TILE_TOP-r0*RES]
ASPECT = 1/np.cos(np.radians(44.2))
def basemap(ax):
    ax.plot(poly[:,0],poly[:,1],color=INK,lw=1.2)
    ax.plot([GAUGE[1]],[GAUGE[0]],marker='o',ms=8,mfc=ORANGE,mec=SURF,mew=1.8,ls='none',zorder=5)
    ax.set_aspect(ASPECT); ax.set_xlim(10.76,11.36); ax.set_ylim(43.96,44.52)
    ax.set_xlabel('Longitude (°E)'); ax.set_ylabel('Latitude (°N)'); style(ax)
grid2 = lambda v: v.reshape(D.shape)

# 1 catchment map
la0=np.where((acc>=5)&inside,np.log10(np.maximum(acc,1e-9)),-1)
la=grey_dilation(grid2(la0),size=(3,3)); la=np.where(la>0,la,np.nan)
fig,ax=plt.subplots(figsize=(7.2,6.6),dpi=160)
ax.imshow(np.where(grid2(inside),1.0,np.nan),extent=ext,cmap=ListedColormap(['#eef4fc']),interpolation='nearest')
im=ax.imshow(la,extent=ext,cmap=LinearSegmentedColormap.from_list('b',RAMP[:1]+[BLUE,'#104281']),vmin=np.log10(5),vmax=np.log10(1100),interpolation='nearest')
basemap(ax)
ax.plot([],[],color=INK,lw=1.2,label='Delineated catchment (OpenHydroNet tool)')
ax.plot([],[],marker='o',ms=8,mfc=ORANGE,mec=SURF,ls='none',label='Outlet: Reno at Casalecchio di Reno')
ax.legend(loc='lower right',facecolor=SURF,edgecolor=GRID,fontsize=8.5)
ax.annotate('Outlet\n44.483 N, 11.284 E',(GAUGE[1],GAUGE[0]),xytext=(12,0),textcoords='offset points',fontsize=9,color=INK2,va='center')
cb=fig.colorbar(im,ax=ax,shrink=0.6,pad=0.02); cb.set_label('Upstream area (km², log scale)',color=INK2)
t=[5,10,50,100,500,1000]; cb.set_ticks(np.log10(t)); cb.set_ticklabels([str(x) for x in t]); cb.outline.set_edgecolor(AXIS); cb.ax.tick_params(colors=MUTED)
title(fig,'Reno catchment above Casalecchio — 1,050 km²','River network from HydroSHEDS 3″ D8 flow directions (cells draining ≥ 5 km²)')
fig.tight_layout(rect=(0,0,1,0.92)); fig.savefig('figures/catchment_map.png'); plt.close()

# 2 sub-basins
fig,(ax,bx)=plt.subplots(1,2,figsize=(10,5.4),dpi=160,gridspec_kw=dict(width_ratios=[1.15,1]))
lab=grid2(label).astype(float); lab[~grid2(inside)]=np.nan
cm=ListedColormap(['#e1e0d9']+CAT[:len(TOP)])
ax.imshow(np.where(np.isnan(lab),np.nan,lab+1),extent=ext,cmap=cm,vmin=-0.5,vmax=len(TOP)+0.5,interpolation='nearest')
ms=np.zeros(N,bool); ms[main]=True
ax.imshow(np.where(grey_dilation(grid2(ms),size=(3,3)),1.0,np.nan),extent=ext,cmap=ListedColormap([INK]),interpolation='nearest')
basemap(ax)
for k,t in enumerate(TOP):
    ax.plot(t['lon'],t['lat'],marker='o',ms=5,mfc=SURF,mec=INK,mew=1,zorder=6)
    ax.annotate(f'T{k+1}',(t['lon'],t['lat']),xytext=(-14,2),textcoords='offset points',fontsize=8.5,fontweight='bold',color=INK)
names=[f'T{k+1}' for k in range(len(TOP))]+['Rest (main-stem\nhillslopes + small\ntributaries)']
vals=[t['area'] for t in TOP]+[float(area[inside&(label<0)].sum())]
y=np.arange(len(vals))[::-1]
bx.barh(y,vals,height=0.62,color=CAT[:len(TOP)]+['#c3c2b7'],edgecolor=SURF,lw=2)
for yy,v,t in zip(y,vals,TOP+[None]):
    s=f'{v:,.0f} km² ({100*v/A_cells:.0f}%)' + (f' · joins {t["dist"]:.0f} km upstream' if t else '')
    bx.text(v+8,yy,s,va='center',fontsize=8.5,color=INK2)
bx.set_yticks(y); bx.set_yticklabels(names,fontsize=9); bx.set_xlim(0,max(vals)*1.9)
bx.set_xlabel('Drainage area (km²)'); style(bx,'x'); bx.tick_params(axis='y',length=0); bx.spines['left'].set_visible(False)
title(fig,'Six largest tributaries account for most of the basin','Tributaries ≥ 20 km² joining the main stem (black), ranked by area; T1 = largest. Dots mark confluences.')
fig.tight_layout(rect=(0,0,1,0.91)); fig.savefig('figures/subbasins.png'); plt.close()

# 3 Strahler
fig,(ax,bx)=plt.subplots(1,2,figsize=(10,5.4),dpi=160,gridspec_kw=dict(width_ratios=[1.15,1]))
basemap(ax)
for u in range(1,omax+1):
    g=grey_dilation(grid2(((order==u)&stream)),size=(1+ (u>=3) + (u>=5),)*2) if u>=3 else grid2((order==u)&stream)
    ax.imshow(np.where(g,1.0,np.nan),extent=ext,cmap=ListedColormap([RAMP[min(u-1,5)]]),interpolation='nearest')
    ax.plot([],[],color=RAMP[min(u-1,5)],lw=0.8+0.5*u,label=f'Order {u}')
ax.legend(loc='upper left',facecolor=SURF,edgecolor=GRID,fontsize=8,title='Strahler',title_fontsize=8)
uu=np.arange(1,omax+1)
bx.semilogy(uu,N_u,marker='o',ms=8,color=BLUE,lw=2,mec=SURF,mew=1.5)
for x,v in zip(uu,N_u): bx.annotate(f'{v:,}',(x,v),xytext=(8,4),textcoords='offset points',fontsize=8.5,color=INK2)
fit=np.polyfit(uu,np.log10(N_u),1)
bx.semilogy(uu,10**np.polyval(fit,uu),color=MUTED,lw=1,ls=(0,(3,3)))
bx.text(0.97,0.95,f'Bifurcation ratio Rb = {Rb:.2f}\n(slope fit: {10**-fit[0]:.2f})',transform=bx.transAxes,ha='right',va='top',fontsize=9,color=INK2)
from matplotlib.ticker import FixedLocator as FL, FixedFormatter as FF, NullLocator as NL
bx.yaxis.set_major_locator(FL([1,3,10,30,100,300])); bx.yaxis.set_major_formatter(FF(['1','3','10','30','100','300'])); bx.yaxis.set_minor_locator(NL())
bx.set_xticks(uu); bx.set_xlabel('Strahler order'); bx.set_ylabel('Number of stream segments (log)'); style(bx,'y')
title(fig,f'Stream network: order {omax}, bifurcation ratio {Rb:.1f}',f'Streams defined as cells draining ≥ {THR:g} km². Right: Horton\'s law of stream numbers.')
fig.tight_layout(rect=(0,0,1,0.91)); fig.savefig('figures/strahler.png'); plt.close()

# 4 width function
dd=dist[inside]; aa=area[inside]; bins=np.arange(0,np.ceil(L/2)*2+2,2)
h,_=np.histogram(dd,bins=bins,weights=aa)
fig,ax=plt.subplots(figsize=(7.2,3.8),dpi=160)
ax.bar(bins[:-1]+1,h,width=1.7,color=BLUE,lw=0)
ax.set_xlabel('Flow distance to outlet (km)'); ax.set_ylabel('Contributing area (km² per 2 km)')
style(ax,'y'); ax.spines['left'].set_visible(False); ax.tick_params(axis='y',length=0)
pk=bins[np.argmax(h)]+1; md=metrics['mean_flow_distance_km']
ax.annotate(f'Peak ≈ {pk:.0f} km',(pk,h.max()),xytext=(8,0),textcoords='offset points',fontsize=9,color=INK2,va='center')
ax.axvline(L,color=MUTED,lw=1,ls=(0,(3,3))); ax.text(L,h.max()*0.95,f'Longest flow path\n{L:.0f} km ',fontsize=9,color=INK2,va='top',ha='right')
ax.axvline(md,color=INK2,lw=1); ax.text(md-0.8,h.max()*0.97,f'Area-weighted\nmean {md:.0f} km',fontsize=9,color=INK2,va='top',ha='right')
title(fig,'Width function: how much of the basin drains from each distance')
fig.tight_layout(rect=(0,0,1,0.93)); fig.savefig('figures/width_function.png'); plt.close()

# 5 outlet sensitivity
fig,ax=plt.subplots(figsize=(7.2,3.8),dpi=160)
mask=(sens_x>=-6)&(sens_x<=40)
ax.step(sens_x[mask],sens_y[mask],where='post',color=BLUE,lw=2)
ax.axvline(0,color=ORANGE,lw=1.5); ax.text(0.6,sens_y[mask].max()*1.0,'Gauge',color=INK2,fontsize=9,va='top')
for k,t in enumerate(TOP):
    if t['dist']<=40: ax.annotate(f'T{k+1} joins\n−{t["area"]:.0f} km²',(t['dist'],np.interp(t['dist'],dist[main],acc[main])),xytext=(6,10),textcoords='offset points',fontsize=8,color=INK2)
ax.set_xlabel('Outlet position along the Reno (km upstream of gauge; negative = downstream)'); ax.set_ylabel('Catchment area (km²)')
ax.set_ylim(0,None); style(ax,'y')
title(fig,'How much the catchment changes if the outlet is misplaced','Area draining to each cell of the main stem. Steps are tributary confluences.')
fig.tight_layout(rect=(0,0,1,0.86)); fig.savefig('figures/outlet_sensitivity.png'); plt.close()

# 6 drainage density vs threshold
fig,ax=plt.subplots(figsize=(7.2,3.6),dpi=160)
ax.loglog(thr_list,Dd_list,marker='o',ms=8,color=BLUE,lw=2,mec=SURF,mew=1.5)
for x,v in zip(thr_list,Dd_list):
    if x in (0.1,1,10,50): ax.annotate(f'{v:.2f}',(x,v),xytext=(6,6),textcoords='offset points',fontsize=8.5,color=INK2)
ax.set_xlabel('Stream-definition threshold (km² upstream)'); ax.set_ylabel('Drainage density (km / km²)'); style(ax)
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
ax.xaxis.set_major_locator(FixedLocator([0.1,0.25,0.5,1,2,5,10,25,50])); ax.xaxis.set_major_formatter(FixedFormatter(['0.1','0.25','0.5','1','2','5','10','25','50'])); ax.xaxis.set_minor_locator(NullLocator())
ax.yaxis.set_major_locator(FixedLocator([0.15,0.25,0.5,1,2])); ax.yaxis.set_major_formatter(FixedFormatter(['0.15','0.25','0.5','1','2'])); ax.yaxis.set_minor_locator(NullLocator())
title(fig,'Drainage density depends on how a "stream" is defined','Same basin, same flow directions — only the accumulation threshold changes.')
fig.tight_layout(rect=(0,0,1,0.86)); fig.savefig('figures/drainage_density_threshold.png'); plt.close()

# 7 tile coverage
names=sorted(f[:-4] for f in os.listdir('data/tiles_5deg') if f.endswith('.npy'))
fig,ax=plt.subplots(figsize=(7.2,4.4),dpi=160)
for n in names:
    mm=re.match(r'n(\d+)([ew])(\d+)',n); top=int(mm.group(1)); lf=int(mm.group(3))*(1 if mm.group(2)=='e' else -1)
    ax.add_patch(Rectangle((lf,top-5),5,5,facecolor=BLUE if n=='n45e010' else '#e1e0d9',edgecolor=SURF,lw=2))
ax.plot([GAUGE[1]],[GAUGE[0]],marker='o',ms=6,mfc=ORANGE,mec=SURF,mew=1.5)
ax.annotate('Casalecchio basin lies in a single tile\n(n45e010, 36 MB)',(10,40.5),xytext=(-15,22),textcoords='data',fontsize=9,color=INK2,arrowprops=dict(arrowstyle='-',color=MUTED,lw=0.8))
ax.set_xlim(-16,71); ax.set_ylim(9,61); ax.set_aspect(1.25); style(ax,None)
ax.set_xlabel('Longitude (°)'); ax.set_ylabel('Latitude (°N)')
title(fig,f'{len(names)} HydroSHEDS tiles prepared (3.9 GB) — 1 needed')
fig.tight_layout(rect=(0,0,1,0.93)); fig.savefig('figures/tile_coverage.png'); plt.close()
