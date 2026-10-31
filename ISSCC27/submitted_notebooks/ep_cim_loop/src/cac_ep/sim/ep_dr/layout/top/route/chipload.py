"""칩 입력 읽기: place/place_real.json + place/lef + net/chip_core.v + net/pins.json → Inst·넷·핀 좌표 (nm)."""
import json
import os
from pathlib import Path

import routelib as R

H = Path(__file__).resolve().parent            # layout/top/route
TOPD = H.parent
LOC = '/home/dave/work/projects/isscc_cac/sim/ep_dr'
OLY = '/home/grads/s/seokjindaveoh/work/ep_dr'
HVL_LEF = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl/lef/sky130_fd_sc_hvl.lef'
SKIP_CELLS = ('tp_tl', 'tp_br', 'tp_bandl', 'tp_bandr')


def oly(p):
    return str(p).replace(LOC, OLY)


def load(place=TOPD / 'place' / 'place_real.json', lefdir=TOPD / 'place' / 'lef', netv=TOPD / 'net' / 'chip_core.v',
         pins=TOPD / 'net' / 'pins.json', override=H / 'lef_fix'):
    P = json.load(open(place))
    M = {}
    lefs = sorted(Path(lefdir).glob('*.lef'))
    for f in lefs:
        R.parse_lef(str(f), M)
    if Path(override).is_dir():
        for f in sorted(Path(override).glob('*.lef')):
            R.parse_lef(str(f), M)
    if HVL_LEF.exists():
        R.parse_lef(str(HVL_LEF), M)
    insts = {}
    for n, v in P['instances'].items():
        m = M[v['cell']]
        insts[n] = R.Inst(n, m, (R.g(v['x']), R.g(v['y'])), v['def_orient'])
        insts[n].gds = v['gds']; insts[n].lef = v['lef']
    top, ports, conns = R.parse_verilog(str(netv), M if not SKIP_CELLS else dict(M, **{c: R.Macro(c) for c in SKIP_CELLS}), top='chip_core')
    core = (R.g(P['core']['w']), R.g(P['core']['h']))
    pj = json.load(open(pins))
    return dict(P=P, M=M, insts=insts, top=top, ports=ports, conns=conns, core=core, pins=pj, lefs=lefs)
