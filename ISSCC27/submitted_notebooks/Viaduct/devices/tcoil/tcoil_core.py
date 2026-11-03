"""Viaduct T-coil device: configurable parallel T-coil. Units: um.

Geometry follows tcoil_config_pcell_generator.il (2026-09-14), ported from the
sky130_tcoil package. Layer numbers and rules come from a PDK profile
(pdk/<name>.json, default sky130A; override with VIADUCT_PDK) instead of code.
build() is the layout; em_model() is the same coil as conductor centerlines for
quasi-static EM. This is NOT a foundry DRC signoff.
"""
import json
import math
import os
from dataclasses import dataclass, asdict

PDK_DIR = os.environ.get("VIADUCT_PDK_DIR",
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pdk"))
PDK_NAME = os.environ.get("VIADUCT_PDK", "sky130A")


def load_profile(name=PDK_NAME):
    with open(os.path.join(PDK_DIR, name + ".json")) as f:
        return json.load(f)


PROFILE = load_profile()
GRID = PROFILE["grid_um"]
METALS = {n: tuple(m["gds"]) for n, m in PROFILE["metals"].items()}
VIAS = {n: tuple(v["gds"]) for n, v in PROFILE["vias"].items()}
# via index (lower metal index) -> (cut size, edge spacing, all-side enclosure)
VIA_RULES = {v["between"][0]: (v["cut_um"], v["space_um"], v["enclosure_um"]) for v in PROFILE["vias"].values()}
MIN_WIDTH = {m["index"]: m["min_width_um"] for m in PROFILE["metals"].values()}
PIN_DATATYPE = PROFILE["pin_datatype"]
LABEL_DATATYPE = PROFILE["label_datatype"]

@dataclass(frozen=True)
class Parameters:
    metalWidth: float = 4.0
    area: float = 6400.0
    turnSpacing: float = 0.0
    upperMetal: str = 'met5'
    lowerMetal: str = 'met4'
    upperCrossover: str = 'met1+met2+met3'
    lowerCrossover: str = 'met1+met2+met3'
    upperViaChain: str = 'Auto'
    lowerViaChain: str = 'Auto'
    parallelViaChain: str = 'Auto'

def snap(x):
    # SKILL-style symmetric nearest grid, not Python banker's rounding.
    return math.copysign(math.floor(abs(x)/GRID + .5 + 1e-9)*GRID, x)

def metal_index(name):
    if name not in METALS:
        raise ValueError('SKY130 metal must be met1..met5: '+str(name))
    return int(name[-1])

def bridges(value):
    names = value.split('+')
    if not names or len(names) != len(set(names)):
        raise ValueError('Empty or repeated crossover metal')
    for name in names:
        metal_index(name)
    return names

def connection(main, layers, selection):
    ids = [metal_index(n) for n in [main]+layers]
    lo, hi = min(ids), max(ids)
    expected = '+'.join(f'via{i}' for i in range(lo, hi))
    if selection not in ('Auto', expected):
        raise ValueError(f'Via chain {selection!r} must be Auto or {expected!r}')
    return lo, hi, expected

def dimensions(p):
    w, a, gap = p.metalWidth, p.area, p.turnSpacing
    if not all(math.isfinite(v) for v in (w,a,gap)) or w<=0 or a<=0 or gap<0:
        raise ValueError('Width/area must be positive; spacing must be nonnegative')
    if abs(w/.01-round(w/.01))>1e-6 or abs(gap/GRID-round(gap/GRID))>1e-6:
        raise ValueError('Width grid=0.01 um; spacing grid=0.005 um')
    ui, li = metal_index(p.upperMetal), metal_index(p.lowerMetal)
    if ui<=li:
        raise ValueError('Upper metal must be strictly above lower metal')
    ups, lows = bridges(p.upperCrossover), bridges(p.lowerCrossover)
    for name in ups+lows:
        if name in (p.upperMetal, p.lowerMetal):
            raise ValueError('A crossover cannot use either main winding metal')
    used = {ui, li, *[metal_index(n) for n in ups+lows]}
    if w < max(MIN_WIDTH[i] for i in used):
        raise ValueError('Metal width below selected SKY130 layer minimum')
    chains = [connection(p.upperMetal, ups, p.upperViaChain),
              connection(p.lowerMetal, lows, p.lowerViaChain),
              connection(p.upperMetal, [p.lowerMetal], p.parallelViaChain)]
    side = math.floor(math.sqrt(a)/.01+1e-9)*.01
    s = (side-w/2-.01)/171.16
    if not .2<=s<=3 or not 2*s+.8<=w<=12*s:
        raise ValueError('Width/area outside reference geometry limits')
    ro, ri, co, ci = [snap(k*s) for k in (73.08,60.05,30.27,24.875)]
    if gap>0:
        ri=snap(ro-w-gap)
        ci=snap(co-(w+gap)*(math.sqrt(2)-1))
    effective = ro-ri-w
    required_gap=max(.5, max(MIN_WIDTH[i] for i in (ui,li)))
    if effective+1e-8<required_gap:
        raise ValueError(f'Turn gap {effective:.3f} below {required_gap:.3f} um for selected metals')
    bend=snap((ro-ri)/2)
    g=max(snap(7.775*s),bend+GRID)
    if not(ci>g+8*s+.5 and ri>ci+w):
        raise ValueError('Inner turn too small for crossover/via landing')
    landing=math.floor(min(w,8*s)/.01+1e-9)*.01
    for lo,hi,_ in chains:
        for i in range(lo,hi):
            cut,_,enc=VIA_RULES[i]
            if landing+1e-8<cut+2*enc:
                raise ValueError(f'via{i} needs landing >= {cut+2*enc:.3f} um')
    return dict(w=w,s=s,ro=ro,ri=ri,co=co,ci=ci,g=g,bend=bend,
                lead=snap(-98.08*s),portx=snap(20*s),landing=landing,
                effective=effective,chains=chains,bridge_layers=sorted(set(ups+lows)))

def path_polygon(points, width):
    """Flush-ended, miter-joined path matching the reference dbCreatePath."""
    directions=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        if length<1e-12: raise ValueError('Zero-length path segment')
        directions.append((dx/length,dy/length))
    def edge(sign):
        out=[]
        for i,(x,y) in enumerate(points):
            d=directions[min(i,len(directions)-1)]
            if i==0 or i==len(points)-1:
                ox,oy=-d[1]*width/2*sign,d[0]*width/2*sign
            else:
                prev=directions[i-1]
                nx,ny=-prev[1]-d[1],prev[0]+d[0]
                den=1+prev[0]*d[0]+prev[1]*d[1]
                ox,oy=nx*width/2*sign/den,ny*width/2*sign/den
            out.append((snap(x+ox),snap(y+oy)))
        return out
    return edge(1)+edge(-1)[::-1]

def build(p=Parameters()):
    d=dimensions(p)
    w,s,ro,ri,co,ci,g,bend,lead,portx,landing=[d[k] for k in
        ('w','s','ro','ri','co','ci','g','bend','lead','portx','landing')]
    polygons=[]
    def poly(layer,pts,datatype=None):
        pair=METALS.get(layer,VIAS.get(layer))
        if datatype is not None: pair=(pair[0],datatype)
        polygons.append((pair,[(snap(x),snap(y)) for x,y in pts]))
    def rect(layer,x0,y0,x1,y1,datatype=None):
        poly(layer,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)],datatype)
    inner=[(-g,ri),(-ci,ri),(-ri,ci),(-ri,-ci),(-ci,-ri),(ci,-ri),(ri,-ci),(ri,ci),(ci,ri),(g,ri)]
    left=[(-portx,lead),(-portx,-ro),(-co,-ro),(-ro,-co),(-ro,co),(-co,ro),(-g,ro)]
    right=[(portx,lead),(portx,-ro),(co,-ro),(ro,-co),(ro,co),(co,ro),(g,ro)]
    high=[(g,ri-w/2),(g,ri+w/2),(bend,ri+w/2),(-bend,ro+w/2),(-g,ro+w/2),(-g,ro-w/2),(-bend,ro-w/2),(bend,ri-w/2)]
    low=[(-g,ri-w/2),(-g,ri+w/2),(-bend,ri+w/2),(bend,ro+w/2),(g,ro+w/2),(g,ro-w/2),(bend,ro-w/2),(-bend,ri-w/2)]
    for layer in (p.upperMetal,p.lowerMetal):
        for path in (inner,left,right): poly(layer,path_polygon(path,w))
        poly(layer,high)
    # Preserve legacy union-of-crossover-layers semantics: these are parallel conductors.
    for layer in d['bridge_layers']:
        poly(layer,low)
        rect(layer,-g-snap(8*s),ri-w/2,-g,ri+w/2)
        rect(layer,g,ro-w/2,g+snap(8*s),ro+w/2)
    seen=set()
    arrays=[]
    def stack(conn,cx,cy):
        lo,hi,_=conn
        for i in range(lo,hi+1):
            key=('metal',i,cx,cy)
            if key not in seen:
                rect(f'met{i}',cx-landing/2,cy-landing/2,cx+landing/2,cy+landing/2)
                seen.add(key)
        for i in range(lo,hi):
            key=('via',i,cx,cy)
            if key in seen: continue
            seen.add(key)
            cut,space,enc=VIA_RULES[i]
            pitch=cut+space
            span=min(8*s,w-2*s,landing-2*enc)
            n=math.floor((span-cut+1e-8)/pitch)+1
            if n<1: raise ValueError(f'via{i} cannot fit reference via window')
            arrays.append(dict(via=f'via{i}',center=[cx,cy],n=n,cut=cut,pitch=pitch,landing=landing,enclosure=enc))
            for ix in range(n):
                for iy in range(n):
                    x=snap(cx+(ix-(n-1)/2)*pitch); y=snap(cy+(iy-(n-1)/2)*pitch)
                    rect(f'via{i}',x-cut/2,y-cut/2,x+cut/2,y+cut/2)
    ends=[(-g-snap(4*s),ri),(g+snap(4*s),ro)]
    for conn in d['chains'][:2]:
        for x,y in ends: stack(conn,x,y)
    sites=ends+[(ro,0),(ri,0),(-ro,0),(-ri,0),(g+snap(4*s),ri),(-g-snap(4*s),ro),(0,-ri),(portx,lead+snap(4*s)),(-portx,lead+snap(4*s))]
    for x,y in sites: stack(d['chains'][2],x,y)
    # Keep the tap location; widen its short lead if required by SKY130 metal.
    tapx=snap(-ri+w/2+snap(.405*w))
    py=max(GRID,snap(.16*w),MIN_WIDTH[metal_index(p.upperMetal)]/2)
    rect(p.upperMetal,-ri+w/2-GRID,-py,tapx,py)
    ports=[dict(name='P1',center=[-portx,lead],width=w,orientation=270),
           dict(name='P2',center=[portx,lead],width=w,orientation=270),
           dict(name='P3',center=[tapx,0],width=2*py,orientation=0)]
    labels=[]
    for port in ports:
        x,y=port['center']
        box=(x-min(.2*w,1),-py,x,py) if port['name']=='P3' else (x-w/2,y,x+w/2,y+min(w/2,4*s))
        rect(p.upperMetal,*box)
        rect(p.upperMetal,*box,datatype=PIN_DATATYPE)
        labels.append(((METALS[p.upperMetal][0],LABEL_DATATYPE),port['name'],(x,y)))
    pts=[v for pair,points in polygons if pair[1]==20 for v in points]
    bbox=[[min(x for x,y in pts),min(y for x,y in pts)],[max(x for x,y in pts),max(y for x,y in pts)]]
    return dict(polygons=polygons,labels=labels,ports=ports,parameters=asdict(p),
                bbox=bbox,actualTurnSpacing=round(d['effective'],6),parallelSites=sites,
                viaArrays=arrays,resolvedViaChains=[c[2] for c in d['chains']],
                resultStatus='NOT_RUN',DRC='NOT_SIGNED_OFF')


def em_model(p=Parameters()):
    """The coil as conductor centerlines for quasi-static EM (FastHenry). Units: um.

    Returns paths (polyline, width, metal), vertical vias (x, y, from-metal,
    to-metal, size) and the three port points, all taken from the same
    dimensions as build(). Signal path, P1 to P2:
      P1 -> outer left half -> 'high' crossover (winding metals) -> inner turn,
      traversed right side / bottom / left side -> 'low' crossover (bridge
      metals, under the windings) -> outer right half -> P2.
    The tap P3 sits on the left side of the inner turn, so P1-P3 spans about
    3/4 of the inner turn and P2-P3 about 1/4: L1 > L2 by construction.
    """
    d=dimensions(p)
    w,s,ro,ri,co,ci,g,bend,lead,portx,landing=[d[k] for k in
        ('w','s','ro','ri','co','ci','g','bend','lead','portx','landing')]
    e=snap(4*s)
    planes=[p.upperMetal,p.lowerMetal]
    paths,vias=[],[]
    # Windings on both parallel planes. The bridge via landings sit on the winding
    # just inside its end (centre 4s from the end), so the 'low' crossover joins
    # the inner turn at (-g-4s, ri) and the outer right half at (g+4s, ro); the
    # last 4s of those two ends carry no current and are left out. Via sites that
    # fall mid-path are inserted as nodes by the EM builder.
    left=[(-portx,lead),(-portx,-ro),(-co,-ro),(-ro,-co),(-ro,co),(-co,ro),(-g,ro)]
    right=[(portx,lead),(portx,-ro),(co,-ro),(ro,-co),(ro,co),(co,ro),(g+e,ro)]
    inner=[(-g-e,ri),(-ci,ri),(-ri,ci),(-ri,-ci),(-ci,-ri),(ci,-ri),(ri,-ci),(ri,ci),(ci,ri),(g,ri)]
    high=[(g,ri),(bend,ri),(-bend,ro),(-g,ro)]
    for m in planes:
        for name,pts in (('left',left),('right',right),('inner',inner),('high',high)):
            paths.append(dict(name=f'{name}.{m}',metal=m,width=w,points=pts))
    # 'low' crossover on every bridge metal (parallel conductors), with its via stacks
    lowpts=[(-g-e,ri),(-g,ri),(-bend,ri),(bend,ro),(g,ro),(g+e,ro)]
    for m in d['bridge_layers']:
        paths.append(dict(name=f'low.{m}',metal=m,width=w,points=lowpts))
    for x,y in ((-g-e,ri),(g+e,ro)):
        for m in planes:
            for b in d['bridge_layers']:
                vias.append(dict(x=x,y=y,top=m,bottom=b,size=landing))
    # inter-plane parallel connection sites
    sites=[(-g-e,ri),(g+e,ro),(ro,0),(ri,0),(-ro,0),(-ri,0),(g+e,ri),(-g-e,ro),(0,-ri),(portx,lead+e),(-portx,lead+e)]
    for x,y in sites:
        vias.append(dict(x=x,y=y,top=planes[0],bottom=planes[1],size=landing))
    # tap stub on the upper metal
    tapx=snap(-ri+w/2+snap(.405*w))
    py=max(GRID,snap(.16*w),MIN_WIDTH[metal_index(p.upperMetal)]/2)
    paths.append(dict(name='tap',metal=p.upperMetal,width=2*py,points=[(-ri,0),(tapx,0)]))
    ports={'P1':(-portx,lead,p.upperMetal),'P2':(portx,lead,p.upperMetal),'P3':(tapx,0,p.upperMetal)}
    return dict(paths=paths,vias=vias,ports=ports,sites=sites,parameters=asdict(p),
                bbox=build(p)['bbox'],actualTurnSpacing=round(d['effective'],6))
