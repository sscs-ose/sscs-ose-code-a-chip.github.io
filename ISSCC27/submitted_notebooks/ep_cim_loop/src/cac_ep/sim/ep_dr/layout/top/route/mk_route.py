#!/usr/bin/env python3
"""칩 core 최상위 배선 준비 (Innovus 전): 배치·핀·미리 그린 선·전원·넓은 넷을 DEF 하나로 → innovus_top.tcl 이 읽고 나머지를 NanoRoute.
사용자 지시 (10/28): "각 블럭 길이 연결하는 것과 lvs 통과와 DRC 통과가 되면은 CaC 제출 기준에 만족", "에이전트는 최대한 많이 써서 작업을 해 보게".

입력 (읽기만): ../place/place_real.json · ../place/lef/*.lef (+ lef_fix/ 덮어쓰기) · ../net/chip_core_top.v · ../net/pins.json
내는 것 (chip/): chip_core_route.v (test pattern 뺀 netlist) · chip_pre.def · cfg_chip.tcl · mk_route_report.txt · special_paths.json
단계
  1. 곧은 선 (배열 ↔ input_drive row · row_blk row/wl · col_blk col), 배열 wl_106–127 (1'b0) → VSS 세로 met3 줄
  2. 전원 고리: 왼·오른 띠 met4 VSS·VDD 세로, 위·아래 띠 met5 VSS·VDD 가로 + 패드 자리 (core 핀) 잇기
  3. 넓은 넷 (VWH VWLO vw_f vw_n VRAILP VRAILM VCM): met4 (세로)·met5 (가로) 격자 미로 배선 (1 µm 격자, 폭·간격만큼 장애물 부풀림)
  4. met5 VDD·VSS 가로 줄 (넓은 넷 자리 비움) + 블록 전원 핀 → via stack + met4 세로 drop
  5. 신호 core 핀 (NanoRoute 가 잇는 넷): 위·아래 변 met4, 왼·오른 변 met3
좌표 nm (core 왼쪽 아래 원점).
"""
import heapq
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import routelib as R  # noqa: E402

TOPD = H.parent
OUT = Path(os.environ.get('ROUTE_OUT', str(H / 'chip')))          # die 판 core = ROUTE_OUT=die/core PAD_MAP=die/pad_map.json
PAD_MAP = os.environ.get('PAD_MAP')
OUT.mkdir(exist_ok=True)
LOC = '/home/dave/work/projects/isscc_cac/sim/ep_dr'
OLY = '/home/grads/s/seokjindaveoh/work/ep_dr'
HVL_LEF = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl/lef/sky130_fd_sc_hvl.lef'
HVL_GDS_OLY = '/home/grads/s/seokjindaveoh/work/ep_dr/digital/pdk/sky130_fd_sc_hvl.gds'
HVL_LEF_OLY = '/home/grads/s/seokjindaveoh/work/ep_dr/digital/pdk/sky130_fd_sc_hvl.lef'
TECH_LEF_OLY = '/home/grads/s/seokjindaveoh/work/ep_dr/digital/pdk/sky130_fd_sc_hvl__nom.tlef'
SKIP_CELLS_ALL = ('tp_tl', 'tp_br', 'tp_bandl', 'tp_bandr')   # test pattern: LEF·배치가 있으면 넣고, 없으면 netlist·LVS source 에서 뺀다
REP = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    REP.append(s)


def oly(p):
    p = str(p)
    if p.startswith(str(Path.home() / 'pdk/volare')) and p.endswith('sky130_fd_sc_hvl.gds'):
        return HVL_GDS_OLY
    return p.replace(LOC, OLY)


def um(n):
    return n / 1000.0


# ───────────────────────── 1. 입력 ─────────────────────────
P = json.load(open(TOPD / 'place' / 'place_real.json'))
M = {}
for f in sorted((TOPD / 'place' / 'lef').glob('*.lef')):
    R.parse_lef(str(f), M)
LEF_FIX = {}
if (H / 'lef_fix').is_dir():
    for f in sorted((H / 'lef_fix').glob('*.lef')):
        R.parse_lef(str(f), M); LEF_FIX[f.stem] = f
R.parse_lef(str(HVL_LEF), M)
W, Hc = R.g(P['core']['w']), R.g(P['core']['h'])
INST = {}
for n, v in P['instances'].items():
    INST[n] = R.Inst(n, M[v['cell']], (R.g(v['x']), R.g(v['y'])), v['def_orient'])
    INST[n].gds = v['gds']; INST[n].cell = v['cell']

SKIP_CELLS = tuple(c for c in SKIP_CELLS_ALL if c not in M or not any(I.cell == c for I in INST.values()))
say(f'test pattern cells left out (no LEF or not placed): {list(SKIP_CELLS)}')
# netlist: test pattern (LEF 없음) 인스턴스를 뺀 사본
src = (TOPD / 'net' / 'chip_core_top.v').read_text()
for c in SKIP_CELLS:
    src = re.sub(r'\n\s*' + c + r'\s+\S+\s*\((?:[^;]*?)\)\s*;', '\n', src, flags=re.S)
(OUT / 'chip_core_route.v').write_text(src)
TOP, PORTS, CONN = R.parse_verilog(str(OUT / 'chip_core_route.v'), M, top='chip_core')
miss = [i for i in CONN if i not in INST]
if miss:
    raise SystemExit(f'netlist 인스턴스가 배치에 없음: {miss}')
NETS = R.nets_of(CONN)
PORTD = dict(PORTS)
say(f'core {um(W)} x {um(Hc)} um, insts {len(INST)} (netlist {len(CONN)}), nets {len(NETS)}, ports {len(PORTS)}')

PG_NAME = {'VDD': 'VDD', 'vdd': 'VDD', 'VPWR': 'VDD', 'VPB': 'VDD', 'VSS': 'VSS', 'vss': 'VSS', 'VGND': 'VSS', 'VNB': 'VSS'}


def pin_net(inst, pin):
    m = INST[inst].m
    if m.use.get(pin) in ('POWER', 'GROUND') and pin in PG_NAME:
        return PG_NAME[pin]
    n = CONN.get(inst, (None, {}))[1].get(pin)
    if n == "1'b0":
        return 'VSS'
    return n


# ───────────────────────── 2. 도형 모음 ─────────────────────────
DB = R.ShapeDB()
DW_BLOCKAGES_PENDING = []
PINS_BY_NET = defaultdict(lambda: defaultdict(list))     # net → layer → [rect]
for n, I in INST.items():
    for l, r in I.obs_shapes():
        if l in R.MINS:
            DB.add(l, r, None)
    for p in I.m.pins:
        net = pin_net(n, p) or f'__nc_{n}_{p}'
        for l, r in I.pin_shapes(p):
            if l in R.MINS:
                DB.add(l, r, net); PINS_BY_NET[net][l].append(r)
say('shape DB built')
import klayout.db as kdb
CUT_LD = {'via': (68, 44), 'via2': (69, 44), 'via3': (70, 44), 'via4': (71, 44)}
BLK_LD = {'met1': (68, 10), 'met2': (69, 10), 'met3': (70, 10), 'met4': (71, 10)}
BLK_CUTS = {}       # cell → {vname: [rect]} (LEF 좌표)
BLK_BLKG = {}       # cell → {layer: [rect]}
for c in sorted({I.cell for I in INST.values()}):
    if c.startswith('arr_') or c.startswith('sky130_fd_sc_hvl__'):
        continue                                   # 배열 안에는 via 를 놓지 않음 (틈만), hvl 셀은 위에 stack 없음
    g0 = [I.gds for I in INST.values() if I.cell == c][0]
    ly = kdb.Layout(); ly.read(g0); tc = [t for t in ly.top_cells() if t.name == c] or ly.top_cells()
    tc = tc[0]
    BLK_CUTS[c] = {}; BLK_BLKG[c] = {}
    for vn, (l, d) in CUT_LD.items():
        li = ly.find_layer(l, d)
        if li is None:
            continue
        BLK_CUTS[c][vn] = [(R.g(b.left), R.g(b.bottom), R.g(b.right), R.g(b.top)) for b in
                           (p_.bbox().to_dtype(ly.dbu) for p_ in kdb.Region(tc.begin_shapes_rec(li)).each())]
    for ml, (l, d) in BLK_LD.items():
        li = ly.find_layer(l, d)
        if li is None:
            continue
        BLK_BLKG[c][ml] = [(R.g(b.left), R.g(b.bottom), R.g(b.right), R.g(b.top)) for b in
                           (p_.bbox().to_dtype(ly.dbu) for p_ in kdb.Region(tc.begin_shapes_rec(li)).merged().each())]
ncut = 0; nblk = 0
CUT_OBS = R.ShapeDB()
for n, I in INST.items():
    for vn, L in BLK_CUTS.get(I.cell, {}).items():
        for r in L:
            CUT_OBS.add(vn, R.xform_rect(r, I.m, I.orient, I.loc), None); ncut += 1
    for ml, L in BLK_BLKG.get(I.cell, {}).items():
        for r in L:
            rc = R.xform_rect(r, I.m, I.orient, I.loc)
            DB.add(ml, rc, None); nblk += 1
            DW_BLOCKAGES_PENDING.append((ml, rc))
say(f'block cuts {ncut}, block routing blockages {nblk}')

DW = R.DefWriter('chip_core', (0, 0, W, Hc), style='rect')
DW.blockages += DW_BLOCKAGES_PENDING           # 블록 GDS 의 met2 blockage (row_blk 서쪽 1.5 µm) → NanoRoute 도 피함
for n, I in INST.items():
    DW.comps.append((n, I.cell, I.loc[0], I.loc[1], I.orient))
SKIP = set()                 # NanoRoute 가 건드리지 않을 넷 (모든 핀이 미리 그린 선으로 이어짐)
PREWIRED = defaultdict(set)  # net → {(inst, pin)} 미리 그린 선이 닿은 핀
OWN = defaultdict(list)      # net → [(layer, rect)] 이 스크립트가 그린 것 (검사용)
BAD = []
EXPECTED = []   # 배열 row met3 가 덧대기 met3 (OBS, 같은 넷) 와 겹침 — 의도


def inside_pin(net, layer, r):
    return any(a[0] <= r[0] and a[1] <= r[1] and a[2] >= r[2] and a[3] >= r[3] for a in PINS_BY_NET[net][layer])


def ok_rect(net, layer, r, allow_in_pin=True):
    if allow_in_pin and inside_pin(net, layer, r):
        return True
    return not DB.conflicts(layer, r, net)


def put(net, layer, r, check=True, tag='', same_ok=False):
    r = tuple(R.snap(v) for v in r)
    if check and not ok_rect(net, layer, r) and (not same_ok or any(x[0] != net for x in DB.conflicts(layer, r, net))):
        c = DB.conflicts(layer, r, net)[:3]
        if tag.endswith('-E3') and layer == 'met3' and all(x[0] is None for x in c):
            EXPECTED.append(tag)
        else:
            BAD.append((tag, net, layer, r, [(x[0], x[1]) for x in c]))
    DW.add_rect(net, layer, r); DB.add(layer, r, net); OWN[net].append((layer, r))
    return r


CUTDB = R.ShapeDB()
CUTSP = {'via': 170, 'via2': 200, 'via3': 200, 'via4': 800}
NSKIPV = defaultdict(int)


def put_via(net, vname, cx, cy, nx=1, ny=1, big_lo='x', big_hi='x', check=True, tag=''):
    pre = R.via_rects(vname, R.snap(cx), R.snap(cy), nx, ny, big_lo, big_hi)
    clash = []
    for c in pre['cuts'][1]:
        for n2, r2 in CUTDB.near(vname, c, CUTSP[vname] + 1000):
            d, dx, dy = R.rect_dist(c, r2)
            if R.overlaps(c, r2) or d < CUTSP[vname] - 0.5:
                clash.append(n2)
    for c in pre['cuts'][1]:
        for n2, r2 in CUT_OBS.near(vname, c, CUTSP[vname] + 1000):
            d, dx, dy = R.rect_dist(c, r2)
            if R.overlaps(c, r2) or d < CUTSP[vname] - 0.5:
                clash.append('__block_cut__')
    if clash:
        if all(n2 == net for n2 in clash):
            NSKIPV[vname] += 1
            return pre
        BAD.append((tag + ':cut', net, vname, (cx, cy), sorted(set(clash))))
    for c in pre['cuts'][1]:
        CUTDB.add(vname, c, net)
    rr = DW.add_via(net, vname, cx, cy, nx, ny, big_lo, big_hi)
    v = R.VIA[vname]
    for l in (v['lo'], v['hi']):
        r = rr[l]
        if check and not ok_rect(net, l, r):
            BAD.append((tag + ':' + vname, net, l, r, [(x[0], x[1]) for x in DB.conflicts(l, r, net)[:3]]))
        DB.add(l, r, net); OWN[net].append((l, r))
    return rr


def to_local(I, r):
    """core 좌표 사각형 → 인스턴스 LEF 좌표 (N·S·FN·FS 는 변환이 자기 역)."""
    rr = (r[0] - I.loc[0], r[1] - I.loc[1], r[2] - I.loc[0], r[3] - I.loc[1])
    return R.xform_rect(rr, I.m, I.orient, (0, 0))


def to_core(I, r):
    return R.xform_rect(r, I.m, I.orient, I.loc)


def pt_core(I, x, y):
    r = to_core(I, (x, y, x, y))
    return r[0], r[1]


# ───────────────────────── 3. 곧은 선 (배열 ↔ 블록) ─────────────────────────
def arr_prewire(aname):
    A = INST[aname]; m = A.m
    AW, AH = m.size
    cnt = defaultdict(int)
    tie_rows = []
    pins = CONN[aname][1]
    for p, net in sorted(pins.items()):
        mm = re.match(r'(row|wl|col)_(\d+)$', p)
        if not mm:
            continue
        kind, k = mm.group(1), int(mm.group(2))
        loc_sh = [(l, r) for l, r in m.pins[p]]           # LEF (= 배열 국소) 좌표
        if net == "1'b0":
            if kind == 'wl':
                tie_rows.append((k, loc_sh))
            continue
        for (pi, pp) in NETS[net]:
            if pi == aname:
                continue
            B = INST[pi]
            bsh = [(l, to_local(A, r)) for l, r in B.pin_shapes(pp)]
            if not bsh:
                continue
            bl, br = bsh[0]
            if kind == 'row' and br[2] <= 0 and B.cell == 'input_drive':        # 서쪽: input_drive (met2 ↔ met2)
                west = [r for l, r in loc_sh if r[0] == 0]
                if not west:
                    continue
                a = west[0]
                y1, y2 = max(a[1], br[1]), min(a[3], br[3])
                if y2 - y1 < 140 or bl != 'met2':
                    BAD.append(('row-west', net, bl, br, 'no overlap')); continue
                rr = (br[0] + (br[2] - br[0]) // 2, y1, a[0] + 700, y2)
                put(net, 'met2', to_core(A, rr), tag=f'{aname}.{p}-W')
                PREWIRED[net] |= {(aname, p), (pi, pp)}; cnt['row-W'] += 1
            elif kind == 'row' and br[0] >= AW and B.cell == 'row_blk':        # 동쪽: row_blk (met2 → via2 → met3)
                east = [r for l, r in loc_sh if r[2] == AW]
                a = east[0]
                put(net, 'met2', to_core(A, (AW - 700, a[1], AW + 1400, a[3])), tag=f'{aname}.{p}-E2')
                cx, cy = AW + 1000, br[1] + 165
                if not (a[1] + 40 <= cy - 100 and cy + 100 <= a[3] - 40):
                    BAD.append(('row-E via', net, 'via2', (cy, a), 'enclosure'))
                c = pt_core(A, cx, cy)
                put_via(net, 'via2', c[0], c[1], big_lo='x', tag=f'{aname}.{p}-E')
                put(net, 'met3', to_core(A, (AW - 500, br[1], br[0] + 700, br[3])), tag=f'{aname}.{p}-E3')
                PREWIRED[net] |= {(aname, p), (pi, pp)}; cnt['row-E'] += 1
            elif kind == 'wl' and br[0] >= AW and B.cell == 'row_blk':         # wl: landing met2 → via2 → met3
                east = [r for l, r in loc_sh if r[2] == AW]
                ly1, ly2 = min(r[1] for r in east), max(r[3] for r in east)
                if ly2 - ly1 < 400:                                             # 덧대기 전 판: landing 을 틈에 만듦
                    ly1 = ly2 - 420
                put(net, 'met2', to_core(A, (AW - 700, ly1, AW + 2400, ly2)), tag=f'{aname}.{p}-L')
                cx, cy = AW + 2000, (ly1 + ly2) // 2
                c = pt_core(A, cx, cy)
                put_via(net, 'via2', c[0], c[1], big_lo='x', tag=f'{aname}.{p}-WLv')
                put(net, 'met3', to_core(A, (cx - 165, br[1], br[0] + 700, br[3])), tag=f'{aname}.{p}-WL3')
                PREWIRED[net] |= {(aname, p), (pi, pp)}; cnt['wl-E'] += 1
            elif kind == 'col' and br[3] <= 0 and B.cell == 'col_blk':         # 남쪽: col_blk (met2)
                m2 = [r for l, r in loc_sh if l == 'met2']
                if m2:
                    lnd = m2[0]
                    if not (lnd[0] <= br[0] and br[2] <= lnd[2]):
                        BAD.append(('col', net, 'met2', br, 'colb pin outside landing')); continue
                    put(net, 'met2', to_core(A, (br[0], br[1] + (br[3] - br[1]) // 2, br[2], lnd[1] + 700)), tag=f'{aname}.{p}-S')
                else:                                                           # 덧대기 전 판: met1 → via1 → met2
                    s = [r for l, r in loc_sh if l == 'met1' and r[1] == 0][0]
                    put(net, 'met1', to_core(A, (s[0], -1000, s[2], 300)), tag=f'{aname}.{p}-S1')
                    c = pt_core(A, (s[0] + s[2]) // 2, -600)
                    put_via(net, 'via', c[0], c[1], big_lo='y', big_hi='y', tag=f'{aname}.{p}-Sv')
                    put(net, 'met2', to_core(A, (br[0], br[1] + (br[3] - br[1]) // 2, br[2], -440)), tag=f'{aname}.{p}-S2')
                PREWIRED[net] |= {(aname, p), (pi, pp)}; cnt['col-S'] += 1
    # wl 1'b0 → 틈에 met2 landing + via2 + 세로 met3 줄 (VSS)
    spine = None
    if tie_rows:
        ys = []
        for k, sh in tie_rows:
            east = [r for l, r in sh if r[2] == AW]
            ly1, ly2 = min(r[1] for r in east), max(r[3] for r in east)
            if ly2 - ly1 < 400:
                ly1 = ly2 - 420
            put('VSS', 'met2', to_core(A, (AW - 700, ly1, AW + 2400, ly2)), tag=f'{aname}.wl_{k}-tie')
            cy = (ly1 + ly2) // 2
            c = pt_core(A, AW + 2000, cy)
            put_via('VSS', 'via2', c[0], c[1], big_lo='x', tag=f'{aname}.wl_{k}-tiev')
            ys.append(cy)
        spine = to_core(A, (AW + 1750, min(ys) - 300, AW + 2250, AH + 300))
        put('VSS', 'met3', spine, tag=f'{aname}.tie-spine')
        cnt['wl-tie'] = len(tie_rows)
    say(f'{aname} prewire', dict(cnt))
    return spine


SPINES = [s for s in (arr_prewire(a) for a in ('arr_f', 'arr_n')) if s]


def facing_same_layer(cell_a, cell_b, maxgap=12000):
    """cell_a 핀 ↔ cell_b 핀 이 같은 층·같은 높이로 가로 마주 보면 곧은 선 (data_blk ga·gb ↔ input_drive ga·gb)."""
    n_ok = 0
    for net, pins in NETS.items():
        pa = [(i, p) for i, p in pins if INST[i].cell == cell_a]
        pb = [(i, p) for i, p in pins if INST[i].cell == cell_b]
        for ia, pa_ in pa:
            for ib, pb_ in pb:
                for la, ra in INST[ia].pin_shapes(pa_):
                    for lb, rb in INST[ib].pin_shapes(pb_):
                        if la != lb:
                            continue
                        L, Rr = (ra, rb) if ra[2] <= rb[0] else (rb, ra)
                        gap = Rr[0] - L[2]
                        y1, y2 = max(L[1], Rr[1]), min(L[3], Rr[3])
                        if 0 <= gap <= maxgap and y2 - y1 >= 140:
                            put(net, la, (L[0] + (L[2] - L[0]) // 2, y1, Rr[0] + (Rr[2] - Rr[0]) // 2, y2), tag=f'{ia}.{pa_}-{ib}')
                            PREWIRED[net] |= {(ia, pa_), (ib, pb_)}; n_ok += 1
    say(f'facing {cell_a} <-> {cell_b}: {n_ok} straight wires')


facing_same_layer('data_blk', 'input_drive')
for net, pins in NETS.items():
    if net in ("1'b0",):
        continue
    if len(pins) >= 2 and all(p in PREWIRED[net] for p in pins):
        SKIP.add(net)
say(f'prewired nets {len(PREWIRED)}, fully prewired (skip NanoRoute) {len(SKIP)}')
partial = sorted(n for n in PREWIRED if n not in SKIP)
say(f'partly prewired (NanoRoute finishes) {len(partial)}: {partial[:12]}')

# ───────────────────────── 4. 전원 고리 + 패드 자리 ─────────────────────────
PJ = json.load(open(TOPD / 'net' / 'pins.json'))['pins']


PMAP = json.load(open(PAD_MAP))['core_pins'] if PAD_MAP else None
if PMAP:
    for k_ in ('VDDL', 'VSSL'):                     # 1.8 V 패드는 IO ring 안에서만 (core 와 안 섞음)
        PMAP.pop(k_, None)
    PJ = {k_: v for k_, v in PMAP.items()}
    say(f'pad map: {PAD_MAP} ({len(PMAP)} core nets)')


def pad_points(pn):
    """core 핀 → [(변, x, y)] (nm). pins.json 의 label_core (d3 core 기준) 를 지금 core 변에 맞춤.
    PAD_MAP 이 있으면 die 패드 핀을 core 변에 내린 자리 (전원은 core 변 밖이면 뺌 = die 고리로만 이음)."""
    out = []
    if PMAP is not None:
        for q in PMAP.get(pn, []):
            v = R.g(q['pos']); side = q['side']
            if q['kind'] == 'power':
                if not (12000 <= v <= (W if side in 'NS' else Hc) - 12000):
                    continue
            else:
                v = min(max(v, 5000), (W if side in 'NS' else Hc) - 5000)
            out.append({'N': ('N', v, Hc), 'S': ('S', v, 0), 'W': ('W', 0, v), 'E': ('E', W, v)}[side])
        return out
    for pad in PJ[pn]['pads']:
        side = pad['side']; x, y = pad['label_core']
        x, y = R.g(x), R.g(y)
        if side == 'top':
            out.append(('N', min(max(x, 40000), W - 40000), Hc))
        elif side == 'bottom':
            out.append(('S', min(max(x, 40000), W - 40000), 0))
        elif side == 'left':
            out.append(('W', 0, min(max(y, 40000), Hc - 40000)))
        else:
            out.append(('E', W, min(max(y, 40000), Hc - 40000)))
    return out


# ── 입력 rail (VRAILP·VRAILM) 은 반쪽마다 가까운 패드에서 따로 먹임 (조정 세션 10/28: 패드 → input_drive rail 핀 ≤ 1 Ω, 30 µm 띠 써도 됨)
#    free 반쪽 = 위 패드 → 위 띠·input_drive 위쪽 rail 핀, nudge 반쪽 = 아래 패드 → 아래 띠·input_drive (R180) 아래쪽 rail 핀
def rail_pin(inst, pin, top):
    sh = [r for l, r in INST[inst].pin_shapes(pin) if l == 'met3' and (r[2] - r[0]) >= 5000]
    return max(sh, key=lambda r: r[1]) if top else min(sh, key=lambda r: r[1])


RAIL = dict(
    top=dict(P=rail_pin('idrv_f', 'vrailp', True), M=rail_pin('idrv_f', 'vrailm', True),
             xP=[x for sd, x, y in pad_points('VRAILP') if sd == 'N'][0], xM=[x for sd, x, y in pad_points('VRAILM') if sd == 'N'][0]),
    bot=dict(P=rail_pin('idrv_n', 'vrailp', False), M=rail_pin('idrv_n', 'vrailm', False),
             xP=[x for sd, x, y in pad_points('VRAILP') if sd == 'S'][0], xM=[x for sd, x, y in pad_points('VRAILM') if sd == 'S'][0]))
RW_FEED = 20000 if PAD_MAP else 13000             # 패드에서 띠까지 세로 met5 폭 (die 판: 패드 P_CORE 25 µm 에 맞춰 20)
TOP_CUT = max(RAIL['top']['xP'], RAIL['top']['xM']) + RW_FEED // 2 + 4000     # 위 고리 met5 는 이 x 오른쪽만
BOT_CUT = (min(RAIL['bot']['xP'], RAIL['bot']['xM'], RAIL['bot']['P'][0], RAIL['bot']['M'][0]) - RW_FEED // 2 - 4000,
           max(RAIL['bot']['P'][2], RAIL['bot']['M'][2], RAIL['bot']['xP'] + RW_FEED // 2, RAIL['bot']['xM'] + RW_FEED // 2) + 4000)
say(f"rail plan: top pads P {um(RAIL['top']['xP'])} M {um(RAIL['top']['xM'])}, bottom pads P {um(RAIL['bot']['xP'])} M {um(RAIL['bot']['xM'])}; "
    f"top ring met5 from x {um(TOP_CUT)}, bottom ring met5 gap {um(BOT_CUT[0])}–{um(BOT_CUT[1])}")
RING = {'VSS': dict(m4=(4000, 12000), m5=(4000, 12000)), 'VDD': dict(m4=(16000, 24000), m5=(16000, 24000))}
PG_PINS = defaultdict(list)       # net → [(layer, rect)]
TRUNK = defaultdict(list)          # net → [met4 rect]  (왼·오른 띠)
RINGS5 = defaultdict(list)         # net → [met5 rect]  (위·아래 띠)
for net, d in RING.items():
    a, b = d['m4']
    for x1, x2 in ((a, b), (W - b, W - a)):
        TRUNK[net].append(put(net, 'met4', (x1, 4000, x2, Hc - 4000), tag='ring4'))
    a, b = d['m5']
    RINGS5[net].append(put(net, 'met5', (4000, a, BOT_CUT[0], b), tag='ring5'))           # 아래: rail 자리 비움
    RINGS5[net].append(put(net, 'met5', (BOT_CUT[1], a, W - 4000, b), tag='ring5'))
    RINGS5[net].append(put(net, 'met5', (TOP_CUT, Hc - b, W - 4000, Hc - a), tag='ring5'))  # 위: rail 자리 (왼쪽) 비움
    DW.snet_use[net] = 'POWER' if net == 'VDD' else 'GROUND'


def via4_array(net, r, tag=''):
    """met4·met5 이 겹치는 사각형 r 에 via4 배열 (cut 0.8, 간격 0.8, 둘러쌈 0.31)."""
    w, h = r[2] - r[0], r[3] - r[1]
    nx = max(1, int((w - 620 + 800) // 1600)); ny = max(1, int((h - 620 + 800) // 1600))
    if w < 1420 or h < 1420:
        return 0
    put_via(net, 'via4', (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, nx, ny, check=False, tag=tag)
    return nx * ny


for net in RING:
    for t in TRUNK[net]:
        for s in RINGS5[net]:
            ov = (max(t[0], s[0]), max(t[1], s[1]), min(t[2], s[2]), min(t[3], s[3]))
            via4_array(net, ov, tag='ringcorner')
# 전원 패드: 왼·오른 변 = met5 토막 (변 → 같은 넷 met4 세로 줄), 위·아래 변 = met4 토막 (변 → 같은 넷 met5 가로 줄)
for net in ('VDD', 'VSS'):
    for side, x, y in pad_points(net):
        if side in 'WE':
            t = [r for r in TRUNK[net] if (r[0] < 40000) == (side == 'W')][0]
            r5 = (0, y - 4000, t[2], y + 4000) if side == 'W' else (t[0], y - 4000, W, y + 4000)
            put(net, 'met5', r5, tag=f'pad5-{net}')
            via4_array(net, (t[0], y - 4000, t[2], y + 4000), tag='padvia')
            pr = (0, y - 4000, 2000, y + 4000) if side == 'W' else (W - 2000, y - 4000, W, y + 4000)
            PG_PINS[net].append(('met5', pr))
        else:
            s = [r for r in RINGS5[net] if (r[1] < 40000) == (side == 'S') and r[0] + 4000 <= x <= r[2] - 4000][0]
            r4 = (x - 4000, 0, x + 4000, s[3]) if side == 'S' else (x - 4000, s[1], x + 4000, Hc)
            put(net, 'met4', r4, tag=f'pad4-{net}')
            via4_array(net, (x - 4000, s[1], x + 4000, s[3]), tag='padvia')
            pr = (x - 4000, 0, x + 4000, 2000) if side == 'S' else (x - 4000, Hc - 2000, x + 4000, Hc)
            PG_PINS[net].append(('met4', pr))
say('rings + PG pads', {n: len(v) for n, v in PG_PINS.items()})

SPECIAL_PORT_PINS = defaultdict(list)     # 넓은 넷 core 핀 도형
RAIL_SEEDS = defaultdict(lambda: defaultdict(list))     # net → 'top'/'bot' → [(layer, rect)]  (미로가 이어 붙일 자리)
RAIL_RES = {}


def via3_on_pin(net, pr):
    """met3 rail 핀 위 via3 배열 (cut 0.2, 간격 0.2, met3 둘러쌈 0.09/0.06 안쪽)."""
    nx = max(1, (pr[2] - pr[0] - 180 + 200) // 400); ny = max(1, (pr[3] - pr[1] - 120 + 200) // 400)
    put_via(net, 'via3', (pr[0] + pr[2]) // 2, (pr[1] + pr[3]) // 2, nx, ny, check=True, tag=f'{net}-railvia3')
    return nx * ny


def stack45(net, r, tag):
    """met4·met5 를 같은 자리에 겹치고 via4 배열 (20 µm 마다 끊어 놓음)."""
    n = 0
    x = r[0]
    while x < r[2] - 1500:
        x2 = min(r[2], x + 20000)
        n += via4_array(net, (x, r[1], x2, r[3]), tag=tag)
        x = x2
    return n


def rail_feed(half):
    d = RAIL[half]
    top = half == 'top'
    out = {}
    if top:
        # P = 위 띠 (y Hc-28 … Hc-2), M = input_drive 위쪽 (띠 아래) 에 같은 폭. P 패드 (서쪽) ↔ M 패드 (동쪽), 핀은 M 이 서쪽 → P 는 띠에서 바로 핀으로 내려가고 M 은 띠 아래 줄로
        pP, pM = d['P'], d['M']
        yb1, yb2 = Hc - 28000, Hc - 2000
        bandP = (pP[0] - 1000, yb1, d['xP'] + RW_FEED // 2, yb2)
        for l in ('met5', 'met4'):
            put('VRAILP', l, bandP, tag='railP-top'); RAIL_SEEDS['VRAILP']['top'].append((l, bandP))
        nv = stack45('VRAILP', bandP, 'railP-top-v4')
        put('VRAILP', 'met4', (pP[0], pP[1], pP[2], yb1 + 2000), tag='railP-top-drop')
        nc = via3_on_pin('VRAILP', pP)
        SPECIAL_PORT_PINS['VRAILP'].append(('met5', (d['xP'] - RW_FEED // 2, Hc - 2000, d['xP'] + RW_FEED // 2, Hc)))
        put('VRAILP', 'met5', (d['xP'] - RW_FEED // 2, yb2 - 1000, d['xP'] + RW_FEED // 2, Hc), tag='railP-top-pad')
        L = bandP[2] - pP[2]
        out['VRAILP'] = (L, bandP[3] - bandP[1], bandP[3] - bandP[1], nv, nc, 0)
        # M: 띠 아래 줄 (input_drive 위) met5 + met4 (배열 위는 met5 만), 패드에서 세로 met5
        ym2 = pM[1] - 1200; ym1 = ym2 - 26000
        arr = INST['arr_f'].bbox
        rowM5 = (pM[0] - 1000, ym1, d['xM'] + RW_FEED // 2, ym2)
        rowM4 = (pM[0] - 1000, ym1, arr[0] - 1000, ym2)
        put('VRAILM', 'met5', rowM5, tag='railM-top5'); put('VRAILM', 'met4', rowM4, tag='railM-top4')
        RAIL_SEEDS['VRAILM']['top'] += [('met5', rowM5), ('met4', rowM4)]
        nv = stack45('VRAILM', rowM4, 'railM-top-v4')
        feedM = (d['xM'] - RW_FEED // 2, ym1, d['xM'] + RW_FEED // 2, Hc)
        put('VRAILM', 'met5', feedM, tag='railM-top-feed')
        put('VRAILM', 'met4', (pM[0], ym2 - 2000, pM[2], pM[3]), tag='railM-top-rise')
        nc = via3_on_pin('VRAILM', pM)
        SPECIAL_PORT_PINS['VRAILM'].append(('met5', (feedM[0], Hc - 2000, feedM[2], Hc)))
        out['VRAILM'] = (rowM4[2] - pM[2], 26000, 26000, nv, nc, (rowM5[2] - rowM4[2]) + (Hc - ym2))
    else:
        # 아래 띠: M = 아래 줄 (y 1.5 … 13.5), P = 위 줄 (y 15.5 … 28.5). P 패드 서쪽 → 핀 서쪽 (엇갈림 없음). M 은 met4 로 P 줄을 가로질러 핀에
        pP, pM = d['P'], d['M']
        # 줄 x 범위 = 패드 세로 토막과 핀을 모두 덮게 (패드가 핀 서쪽·동쪽 어느 쪽이어도)
        rowP = (min(d['xP'] - RW_FEED // 2, pP[0]), 15500, max(d['xP'] + RW_FEED // 2, pP[2]), 28500)
        rowM = (min(d['xM'] - RW_FEED // 2, pM[0]), 1500, max(d['xM'] + RW_FEED // 2, pM[2]), 13500)
        if rowP[2] > pM[0] - 1600 and rowP[0] < pM[2]:          # P 줄이 M 의 세로 (met4) 와 겹치면 met4 만 끊음 (met5 는 M 이 met4 로 지나감)
            pass
        for net, r in (('VRAILP', rowP), ('VRAILM', rowM)):
            for l in ('met5', 'met4'):
                put(net, l, r, tag=f'{net}-bot'); RAIL_SEEDS[net]['bot'].append((l, r))
        nvP = stack45('VRAILP', rowP, 'railP-bot-v4'); nvM = stack45('VRAILM', rowM, 'railM-bot-v4')
        put('VRAILP', 'met5', (d['xP'] - RW_FEED // 2, 0, d['xP'] + RW_FEED // 2, rowP[3]), tag='railP-bot-pad')
        put('VRAILM', 'met5', (d['xM'] - RW_FEED // 2, 0, d['xM'] + RW_FEED // 2, rowM[3]), tag='railM-bot-pad')
        put('VRAILP', 'met4', (pP[0], rowP[1] + 1000, pP[2], pP[3]), tag='railP-bot-rise')
        put('VRAILM', 'met4', (pM[0], rowM[1] + 1000, pM[2], pM[3]), tag='railM-bot-rise')
        ncP = via3_on_pin('VRAILP', pP); ncM = via3_on_pin('VRAILM', pM)
        out['VRAILP'] = (abs((pP[0] + pP[2]) // 2 - d['xP']), 13000, 13000, nvP, ncP, rowP[1])
        out['VRAILM'] = (abs((pM[0] + pM[2]) // 2 - d['xM']), 12000, 12000, nvM, ncM, rowM[1])
    return out


for half in ('top', 'bot'):
    for net, (L, w5, w4, nv4, nv3, extra) in rail_feed(half).items():
        # 저항 어림 (nom): 겹친 met5·met4 줄 = 병렬, via3 배열 = 3.41 / n, 패드 세로 토막 met5
        r_band = (L / 1000) / (w5 / 1000 / 0.0285 + w4 / 1000 / 0.047)
        r_v3 = 3.41 / max(nv3, 1)
        r_feed = 0.0285 * (extra / 1000) / (RW_FEED / 1000)
        r_tot = r_band + r_v3 + r_feed
        RAIL_RES[(net, half)] = dict(len_um=um(L), w_m5_um=um(w5), w_m4_um=um(w4), via4=nv4, via3=nv3, R_band=round(r_band, 3), R_via3=round(r_v3, 3),
                                     R_feed=round(r_feed, 3), R_total=round(r_tot, 3), I_dc_m5_mA=round(10.17 * w5 / 1000), I_dc_via3_mA=round(0.48 * nv3, 1))
        say(f'rail feed {net} {half}: 줄 {um(L):.0f} um (met5 {um(w5)} ∥ met4 {um(w4)} um) {r_band:.3f} Ω + via3 {nv3} 개 {r_v3:.3f} Ω + 패드 토막 {r_feed:.3f} Ω = {r_tot:.3f} Ω;'
            f' EM DC: met5 {10.17 * w5 / 1000:.0f} mA, via3 {0.48 * nv3:.1f} mA')

# ── 쓰기 전원 VWH·VWLO (순간 106–122 mA): 왼쪽 변 패드 → 왼쪽 띠 세로 met5 → WU 줄 위 (VWH)·아래 (VWLO) 가로 met5 띠 → wbuf 핀.
#    met5 만 쓴다 (다른 넓은 넷·신호가 met4 로 가로지르게). wbuf 핀 셋 (vwl·out·vwh 0.45 µm 간격) 에서는 met4 4 µm 짧은 토막으로만 빠짐
WB_RES = {}


def wbuf_feeds():
    wus = [INST[n].bbox for n in INST if INST[n].cell == 'wu']
    wb = {n: INST[n] for n in INST if INST[n].cell == 'wbuf'}
    wu_y1, wu_y2 = min(b[1] for b in wus), max(b[3] for b in wus)
    xmax = max(I.bbox[2] for I in wb.values()) - 40000           # 띠 동쪽 끝 = 먼 wbuf 핀 너머
    pins = {n: {p: [r for l, r in I.pin_shapes(p) if l == 'met3'][0] for p in ('vwh', 'vwl', 'out')} for n, I in wb.items()}
    xe = max(max(pins[n]['vwh'][2] for n in pins) + 18000, 0)
    yH1, yH2 = wu_y2 + 1800, wu_y2 + 1800 + 76000                # VWH 띠 (WU 위)
    yL2 = wu_y1 - 1800; yL1 = yL2 - 70000                         # VWLO 띠 (WU 아래, 배열 위 met5 까지 내려감)
    padH = [y for sd, x, y in pad_points('VWH') if sd == 'W'][0]
    padL = [y for sd, x, y in pad_points('VWLO') if sd == 'W'][0]
    padHE = [y for sd, x, y in pad_points('VWH') if sd == 'E']        # die 판: 오른쪽 변에 하나 더 (wbuf_f 쪽)
    padLE = [y for sd, x, y in pad_points('VWLO') if sd == 'E']
    xeH = W if padHE else xe; xeL = W if padLE else xe
    out = {}
    # 띠 + 왼쪽 세로 (+ 오른쪽 세로)
    put('VWH', 'met5', (0, yH1, xeH, yH2), tag='VWH-band'); put('VWH', 'met5', (0, min(padH - 10000, yH1), 28000, max(padH + 10000, yH2)), tag='VWH-left')
    put('VWLO', 'met5', (0, yL1, xeL, yL2), tag='VWLO-band'); put('VWLO', 'met5', (0, min(padL - 10000, yL1), 28000, max(padL + 10000, yL2)), tag='VWLO-left')
    SPECIAL_PORT_PINS['VWH'].append(('met5', (0, padH - 10000, 2000, padH + 10000)))
    SPECIAL_PORT_PINS['VWLO'].append(('met5', (0, padL - 10000, 2000, padL + 10000)))
    for yy in padHE:
        put('VWH', 'met5', (W - 28000, min(yy - 10000, yH1), W, max(yy + 10000, yH2)), tag='VWH-right')
    for yy in padLE:
        put('VWLO', 'met5', (W - 28000, min(yy - 10000, yL1), W, max(yy + 10000, yL2)), tag='VWLO-right')
    for n, I in wb.items():
        ph, pl = pins[n]['vwh'], pins[n]['vwl']
        cx = (ph[0] + ph[2]) // 2
        # VWH: 핀 위 (북쪽) 기둥 met5. 기둥 폭 = WU 와 1.8 µm 띄운 자리까지
        near = [b for b in wus if abs((b[0] + b[2]) / 2 - cx) < 150000]
        if ph[0] > (near[0][0] + near[0][2]) / 2:                   # wbuf 가 WU 동쪽
            c1, c2 = near[0][2] + 1800, cx + 18000
        else:
            c1, c2 = cx - 22000, near[0][0] - 1800
        col = (c1, I.bbox[3] + 500, c2, yH2)
        put('VWH', 'met5', col, tag=f'VWH-col-{n}')
        esc = (cx - 2000, ph[1], cx + 2000, I.bbox[3] + 8000)
        put('VWH', 'met4', esc, tag=f'VWH-esc-{n}')
        nv4 = via4_array('VWH', (esc[0], col[1], esc[2], esc[3]), tag='VWH-esc-v4')
        nv3 = via3_on_pin('VWH', ph)
        # VWLO: 핀 아래 (남쪽) met4 토막 → 띠
        cxl = (pl[0] + pl[2]) // 2
        escl = (cxl - 2000, yL2 - 6500, cxl + 2000, pl[3])
        put('VWLO', 'met4', escl, tag=f'VWLO-esc-{n}')
        nv4l = via4_array('VWLO', (escl[0], escl[1], escl[2], yL2), tag='VWLO-esc-v4')
        nv3l = via3_on_pin('VWLO', pl)
        # 저항 어림 (nom): 왼쪽 세로 + 띠 (패드 쪽 끝 → 기둥) + 기둥 + via4 + 토막 met4 + via3
        yHc = (yH1 + yH2) / 2; yLc = (yL1 + yL2) / 2
        dxH = min((c1 + c2) / 2, (W - (c1 + c2) / 2) if padHE else 1e18)
        dyH = abs(yHc - padH) if dxH == (c1 + c2) / 2 else abs(yHc - padHE[0])
        rH = (0.0285 * dyH / 28000 + 0.0285 * dxH / (yH2 - yH1) + 0.0285 * (yHc - col[1]) / (c2 - c1)
              + 0.38 / max(nv4, 1) + 0.047 * (esc[3] - esc[1]) / 4000)
        dxL = min(cxl, (W - cxl) if padLE else 1e18)
        dyL = abs(yLc - padL) if dxL == cxl else abs(yLc - padLE[0])
        rL = (0.0285 * dyL / 28000 + 0.0285 * dxL / (yL2 - yL1) + 0.38 / max(nv4l, 1) + 0.047 * (escl[3] - escl[1]) / 4000)
        WB_RES[('VWH', n)] = dict(R_wire=round(rH, 3), via3=nv3, R_via3=round(3.41 / nv3, 3), R_total=round(rH + 3.41 / nv3, 3),
                                  band_um=(um(yH2 - yH1)), col_um=um(c2 - c1), via4=nv4)
        WB_RES[('VWLO', n)] = dict(R_wire=round(rL, 3), via3=nv3l, R_via3=round(3.41 / nv3l, 3), R_total=round(rL + 3.41 / nv3l, 3),
                                   band_um=um(yL2 - yL1), via4=nv4l)
    for k, v in WB_RES.items():
        say(f'write feed {k[0]} → {k[1]}: 선 {v["R_wire"]} Ω + 핀 via3 {v["via3"]} 개 {v["R_via3"]} Ω = {v["R_total"]} Ω (met5 띠 {v["band_um"]} µm)')
    SKIP.update({'VWH', 'VWLO'})


wbuf_feeds()

# ───────────────────────── 5. 넓은 넷: met4/met5 격자 미로 ─────────────────────────
G = 1000
NX, NY = W // G + 1, Hc // G + 1
# 폭 (nm). 근거 = SkyWater tech LEF EM DC 평균 Jmax (Tj 90 °C): met5 10.17 mA/µm, met4 6.8 mA/µm (README §EM)
SPECIAL = {
    'vw_f': dict(w4=8000, w5=12000, I=122),     # wbuf out 은 핀 위에서 바로 met5 로 올라감 → met4 (row_blk 위 세로) 를 넓게
    'vw_n': dict(w4=8000, w5=12000, I=122),
    'VRAILP': dict(w4=4000, w5=6000, I=1, seeded=True),    # input_drive 는 rail_feed 가 이음. 여기서는 col_blk clamp (작은 전류) + 두 반쪽 묶음 (LVS 한 넷)
    'VRAILM': dict(w4=4000, w5=6000, I=1, seeded=True),
    'VCM': dict(w4=4000, w5=6000, I=20),
}
WU_BOX = [INST[n].bbox for n in INST if INST[n].cell == 'wu']
ARR_BOX = [INST[n].bbox for n in INST if INST[n].cell.startswith('arr_')]


def stack_at(net, layer, x, y, pin_rect, check_only=False):
    """pin 층 → met4 via stack 을 (x, y) 에. 각 층 도형이 pin 안이거나 다른 넷과 간격을 지키면 OK. → met4 pad rect 또는 None."""
    order = ['met1', 'met2', 'met3', 'met4']
    a = order.index(layer)
    rects = []
    for k in range(a, 3):
        vname = R.CUTS[(order[k], order[k + 1])]
        rr = R.via_rects(vname, x, y)
        rects.append((order[k], rr[order[k]])); rects.append((order[k + 1], rr[order[k + 1]]))
    for k in range(a + 1, 3):                                       # 중간층 최소 면적 pad
        l = order[k]
        half = R.snap((R.MINAREA[l] ** 0.5) / 2 + 3)
        rects.append((l, (R.snap(x) - half, R.snap(y) - half, R.snap(x) + half, R.snap(y) + half)))
    for l, r in rects:
        if l == layer:
            if not (pin_rect[0] <= r[0] and pin_rect[1] <= r[1] and pin_rect[2] >= r[2] and pin_rect[3] >= r[3]):
                return None
        elif not ok_rect(net, l, r):
            return None
    for k in range(a, 3):                                           # cut 이 블록 via·이미 놓은 via 와 간격을 지키는지
        vname = R.CUTS[(order[k], order[k + 1])]
        for c in R.via_rects(vname, x, y)['cuts'][1]:
            for dbx in (CUT_OBS, CUTDB):
                for n2, r2 in dbx.near(vname, c, CUTSP[vname] + 1000):
                    d, dx, dy = R.rect_dist(c, r2)
                    if R.overlaps(c, r2) or d < CUTSP[vname] - 0.5:
                        return None
    if check_only:
        return [r for l, r in rects if l == 'met4'][0]
    for k in range(a, 3):
        put_via(net, R.CUTS[(order[k], order[k + 1])], x, y, check=False)
    for l, r in rects[2 * (3 - a):]:
        put(net, l, r, check=False)
    return [r for l, r in rects if l == 'met4'][0]


def pin_sites(net, shapes, step=1000):
    """pin 도형 위 후보 점 (가운데 줄을 따라)."""
    out = []
    for l, r in shapes:
        w, h = r[2] - r[0], r[3] - r[1]
        if w >= h:
            yc = R.snap((r[1] + r[3]) / 2)
            xs = range(r[0] + 400, r[2] - 399, step) if w > 800 else [R.snap((r[0] + r[2]) / 2)]
            out += [(l, r, R.snap(x), yc) for x in xs]
        else:
            xc = R.snap((r[0] + r[2]) / 2)
            ys = range(r[1] + 400, r[3] - 399, step) if h > 800 else [R.snap((r[1] + r[3]) / 2)]
            out += [(l, r, xc, R.snap(y)) for y in ys]
    return out


# 작은 전원 핀 (input_drive vss, col_blk lo, …) 의 drop 자리를 넓은 넷 미로가 먼저 차지하지 않게 met4 세로 띠를 비워 둠
RESERVE4 = []
for n_, I_ in INST.items():
    if I_.cell.startswith('arr_'):
        continue
    for p_ in I_.m.pins:
        if pin_net(n_, p_) in ('VDD', 'VSS'):
            sh_ = [r for l, r in I_.pin_shapes(p_) if l in ('met1', 'met2', 'met3')]
            if sh_ and sum((r[2] - r[0]) * (r[3] - r[1]) for r in sh_) < 5 * 10 ** 6:
                r = sh_[0]; cx, cy = (r[0] + r[2]) // 2, (r[1] + r[3]) // 2
                RESERVE4.append((cx - 3500, cy - 25000, cx + 3500, cy + 25000))


def raster(net, l, w):
    """넷 net (폭 w) 의 중심선이 못 가는 격자 (True = 막힘)."""
    B = np.zeros((NY, NX), bool)
    if l == 'met4':
        for r in RESERVE4:
            d = w // 2 + 400
            i1, i2 = max(0, math.ceil((r[0] - d) / G)), min(NX - 1, math.floor((r[2] + d) / G))
            j1, j2 = max(0, math.ceil((r[1] - d) / G)), min(NY - 1, math.floor((r[3] + d) / G))
            B[j1:j2 + 1, i1:i2 + 1] = True
    sp = 1600 if l == 'met5' else 400
    d = w // 2 + sp + 200
    for b in DB.d[l].values():
        for n2, r in b:
            if n2 == net:
                continue
            i1, i2 = max(0, math.ceil((r[0] - d) / G)), min(NX - 1, math.floor((r[2] + d) / G))
            j1, j2 = max(0, math.ceil((r[1] - d) / G)), min(NY - 1, math.floor((r[3] + d) / G))
            if i1 <= i2 and j1 <= j2:
                B[j1:j2 + 1, i1:i2 + 1] = True
    for bx in WU_BOX:                                               # WU (MIM) 위로는 넓은 넷이 지나지 않음
        i1, i2 = max(0, math.ceil((bx[0] - d) / G)), min(NX - 1, math.floor((bx[2] + d) / G))
        j1, j2 = max(0, math.ceil((bx[1] - d) / G)), min(NY - 1, math.floor((bx[3] + d) / G))
        B[j1:j2 + 1, i1:i2 + 1] = True
    m = math.ceil((w // 2 + 1000) / G)                              # core 가장자리
    B[:m, :] = True; B[-m:, :] = True; B[:, :m] = True; B[:, -m:] = True
    return B


def astar(Bl, starts, targets, tbox):
    """Bl = [B4, B5]. starts = [(l, j, i)], targets = set((l, j, i)). met4 = 세로만, met5 = 가로만, via 값 8."""
    INF = 1 << 30
    gbest = np.full((2, NY, NX), INF, np.int32)
    par = np.full((2, NY, NX), -1, np.int64)
    ti1, tj1, ti2, tj2 = tbox

    def hfun(j, i):
        return max(0, ti1 - i, i - ti2) + max(0, tj1 - j, j - tj2)
    pq = []
    for l, j, i in starts:
        if Bl[l][j, i]:
            continue
        gbest[l, j, i] = 0
        heapq.heappush(pq, (hfun(j, i), 0, l, j, i))
    while pq:
        f, gc, l, j, i = heapq.heappop(pq)
        if gc > gbest[l, j, i]:
            continue
        if (l, j, i) in targets:
            path = [(l, j, i)]
            k = par[l, j, i]
            while k >= 0:
                ll, rem = divmod(int(k), NY * NX); jj, ii = divmod(rem, NX)
                path.append((ll, jj, ii)); k = par[ll, jj, ii]
            return path[::-1]
        nb = [((1 - l, j, i), 8)]
        if l == 0:
            nb += [((0, j + 1, i), 1), ((0, j - 1, i), 1)]
        else:
            nb += [((1, j, i + 1), 1), ((1, j, i - 1), 1)]
        for (l2, j2, i2), c in nb:
            if not (0 <= j2 < NY and 0 <= i2 < NX) or Bl[l2][j2, i2]:
                continue
            g2 = gc + c
            if g2 < gbest[l2, j2, i2]:
                gbest[l2, j2, i2] = g2; par[l2, j2, i2] = (l * NY + j) * NX + i
                heapq.heappush(pq, (g2 + hfun(j2, i2), g2, l2, j2, i2))
    return None


SP_REPORT = {}


def path_rects(net, path, w4, w5):
    """격자 경로 → 금속 사각형 + via4."""
    runs = []
    cur = [path[0]]
    for p in path[1:]:
        if p[0] == cur[-1][0]:
            cur.append(p)
        else:
            runs.append(cur); cur = [p]
    runs.append(cur)
    length = {'met4': 0, 'met5': 0}
    for run in runs:
        l = run[0][0]
        xs = [p[2] * G for p in run]; ys = [p[1] * G for p in run]
        if l == 0:
            r = (xs[0] - w4 // 2, min(ys) - w4 // 2, xs[0] + w4 // 2, max(ys) + w4 // 2); put(net, 'met4', r, check=False)
            length['met4'] += max(ys) - min(ys)
        else:
            r = (min(xs) - w5 // 2, ys[0] - w5 // 2, max(xs) + w5 // 2, ys[0] + w5 // 2); put(net, 'met5', r, check=False)
            length['met5'] += max(xs) - min(xs)
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            x, y = a[2] * G, a[1] * G
            s = min(w4, w5) // 2
            via4_array(net, (x - s, y - s, x + s, y + s), tag='sp-via4')
    return length


def special_terminals(net, w4, w5):
    """→ [(이름, starts[(l,j,i)], 연결 도형 함수)] : 블록 핀은 stack 을 놓을 자리만 고르고 (아직 그리지 않음), core 핀은 변 자리."""
    terms = []
    seeded = SPECIAL.get(net, {}).get('seeded')
    for (inst, pin) in NETS.get(net, []):
        I = INST[inst]
        if seeded and I.cell == 'input_drive':
            continue
        shapes = I.pin_shapes(pin)
        terms.append(('blk', f'{inst}.{pin}', shapes))
    if net in PORTD and net in PJ and not seeded:
        for side, x, y in pad_points(net):
            terms.append(('pad', f'{net}@{side}', (side, x, y)))
    return terms


STACK_PTS = []    # (net, x, y) 이미 놓은 넓은 넷 stack


def clearance(net, x, y):
    """자리 점수 (nm): 다른 넓은 넷 블록 핀까지 거리 (20 µm 까지) + 이미 놓은 다른 넷 stack 까지 거리 / 3 (60 µm 까지)."""
    bp = 10 ** 9; bs = 10 ** 9
    for n2, sx, sy in STACK_PTS:
        if n2 != net:
            bs = min(bs, abs(sx - x) + abs(sy - y))
    for n2 in SPECIAL:
        if n2 == net:
            continue
        for (inst, pin) in NETS.get(n2, []):
            for l, r in INST[inst].pin_shapes(pin):
                dx = max(0, r[0] - x, x - r[2]); dy = max(0, r[1] - y, y - r[3])
                bp = min(bp, dx + dy)
    return min(bp, 20000) + min(bs, 180000) // 3


def place_block_stack(net, shapes, w4):
    """블록 핀 stack: 다른 넓은 넷 핀과 가장 먼 자리 (긴 rail 이면 가운데 쪽). → (x, y, met4 pad, ncut) 또는 None."""
    cands = pin_sites(net, shapes, step=2000)
    def mid(c):
        r = c[1]
        return abs(c[2] - (r[0] + r[2]) // 2) + abs(c[3] - (r[1] + r[3]) // 2)
    cands.sort(key=lambda c: (-clearance(net, c[2], c[3]) // 5000, mid(c)))
    for l, r, x, y in cands:
        if l not in ('met1', 'met2', 'met3'):
            continue
        pad = stack_at(net, l, x, y, r, check_only=True)
        if pad:
            # pin 이 넓으면 via3 를 여럿 (met3 pin 안쪽에 들어가는 만큼)
            if l == 'met3' and (r[2] - r[0]) >= 900 and (r[3] - r[1]) >= 900:
                ix = r[0] + 130, r[2] - 130; iy = r[1] + 130, r[3] - 130
                nx = max(1, (ix[1] - ix[0] + 200) // 400); ny = max(1, (iy[1] - iy[0] + 200) // 400)
                nx, ny = min(nx, 12), min(ny, 40)
                cx, cy = R.snap((r[0] + r[2]) / 2), R.snap((r[1] + r[3]) / 2)
                rr = R.via_rects('via3', cx, cy, nx, ny)
                if all(ok_rect(net, 'met4', rr['met4']) for _ in [0]) and rr['met3'][0] >= r[0] - 60 and rr['met3'][2] <= r[2] + 60 \
                        and rr['met3'][1] >= r[1] - 60 and rr['met3'][3] <= r[3] + 60:
                    put_via(net, 'via3', cx, cy, nx, ny, check=False)
                    m4 = (min(rr['met4'][0], r[0]), min(rr['met4'][1], r[1]), max(rr['met4'][2], r[2]), max(rr['met4'][3], r[3]))
                    put(net, 'met4', m4, check=True, tag=f'{net}-pinm4')
                    return cx, cy, m4, nx * ny
            pad = stack_at(net, l, x, y, r)
            return x, y, pad, 1
    return None


def jog_to_node(net, x, y, pad, B4, maxr=25, dirn=None):
    """met4 pad (x, y) → 가까운 막히지 않은 met4 격자점까지 1.2 µm L 자 met4. dirn = 'N'/'S' 면 그 쪽 점만. → (j, i) 또는 None."""
    ci, cj = round(x / G), round(y / G)
    cand = []
    for dj in range(-maxr, maxr + 1):
        if dirn == 'S' and (cj + dj) * G > pad[1] - 1000:
            continue
        if dirn == 'N' and (cj + dj) * G < pad[3] + 1000:
            continue
        for di in range(-maxr, maxr + 1):
            i, j = ci + di, cj + dj
            if 0 <= i < NX and 0 <= j < NY and not B4[j, i]:
                cand.append((abs(di) + abs(dj), j, i))
    cand.sort()
    hw = 600
    for _, j, i in cand[:400]:
        nxp, nyp = i * G, j * G
        for order in ('vh', 'hv'):
            if order == 'vh':
                r1 = (x - hw, min(y, nyp) - hw, x + hw, max(y, nyp) + hw); r2 = (min(x, nxp) - hw, nyp - hw, max(x, nxp) + hw, nyp + hw)
            else:
                r1 = (min(x, nxp) - hw, y - hw, max(x, nxp) + hw, y + hw); r2 = (nxp - hw, min(y, nyp) - hw, nxp + hw, max(y, nyp) + hw)
            if ok_rect(net, 'met4', r1, False) and ok_rect(net, 'met4', r2, False):
                put(net, 'met4', r1, check=False); put(net, 'met4', r2, check=False)
                return j, i
    return None


SP_STATE = {}
# (a) 모든 넓은 넷의 블록 핀 stack 을 먼저 놓는다 (서로 장애물이 되게)
for net, d in SPECIAL.items():
    if net not in NETS:
        say(f'special {net}: not in netlist'); continue
    st = []
    for kind, name, info in special_terminals(net, d['w4'], d['w5']):
        if kind == 'blk':
            s = place_block_stack(net, info, d['w4'])
            if s is None:
                BAD.append(('special-stack', net, '-', name, 'no site')); say(f'  {net} {name}: NO STACK SITE')
                continue
            st.append(('blk', name, s)); STACK_PTS.append((net, s[0], s[1]))
        else:
            st.append(('pad', name, info))
    SP_STATE[net] = st
# (b) 넷마다 미로 (VWH → … 순서)
for net, d in SPECIAL.items():
    if net not in SP_STATE:
        continue
    w4, w5 = d['w4'], d['w5']
    B4, B5 = raster(net, 'met4', w4), raster(net, 'met5', w5)
    for bx in ARR_BOX:                                                # 배열 위 met5 도 넓은 넷은 피함 (덧대기 위 결합)
        pass
    nodes = []                                                        # 단자마다 시작 격자점
    M5START = {}
    for kind, name, s in SP_STATE[net]:
        if kind == 'blk':
            x, y, pad, ncut = s
            st = []
            j5, i5 = round(y / G), round(x / G)
            if not B5[j5, i5] and (pad[2] - pad[0]) >= 1180 - 400:
                st.append((1, j5, i5)); M5START[(1, j5, i5)] = (x, y, pad)
            inst, pin = name.split('.', 1)
            dirn = {'vwl': 'S', 'vwh': 'N'}.get(pin) if INST[inst].cell == 'wbuf' else None
            ji = jog_to_node(net, x, y, pad, B4, dirn=dirn)
            if ji is not None:
                st.append((0, ji[0], ji[1]))
            if not st:
                BAD.append(('special-jog', net, 'met4', name, 'no node')); say(f'  {net} {name}: NO NODE'); continue
            nodes.append((name, st))
        else:
            side, x, y = s
            # 변에서 안쪽으로: 위·아래 = met4, 왼·오른 = met5. 막히면 변을 따라 ±60 µm 안에서 옮김
            found = None
            for off in sorted(range(-300, 301, 1), key=abs):
                if side in 'NS':
                    i = round(x / G) + off
                    j = (math.ceil((w4 // 2 + 1500) / G) if side == 'S' else NY - 1 - math.ceil((w4 // 2 + 1500) / G))
                    col = B4[j:j + 60, i] if side == 'S' else B4[j - 59:j + 1, i]
                    if 0 < i < NX - 1 and not col.any():
                        xr = i * G
                        r = (xr - w4 // 2, 0, xr + w4 // 2, j * G + w4 // 2) if side == 'S' else (xr - w4 // 2, j * G - w4 // 2, xr + w4 // 2, Hc)
                        if ok_rect(net, 'met4', r, False):
                            found = ((0, j, i), r, 'met4'); break
                else:
                    j = round(y / G) + off
                    i = (math.ceil((w5 // 2 + 1500) / G) if side == 'W' else NX - 1 - math.ceil((w5 // 2 + 1500) / G))
                    row = B5[j, i:i + 60] if side == 'W' else B5[j, i - 59:i + 1]
                    if 0 < j < NY - 1 and not row.any():
                        yr = j * G
                        r = (0, yr - w5 // 2, i * G + w5 // 2, yr + w5 // 2) if side == 'W' else (i * G - w5 // 2, yr - w5 // 2, W, yr + w5 // 2)
                        if ok_rect(net, 'met5', r, False):
                            found = ((1, j, i), r, 'met5'); break
            if not found:
                BAD.append(('special-pad', net, '-', name, 'no edge node')); say(f'  {net} {name}: NO EDGE NODE'); continue
            node, r, l = found
            put(net, l, r, check=False)
            if l == 'met4':
                pr = (r[0], 0, r[2], 2000) if side == 'S' else (r[0], Hc - 2000, r[2], Hc)
            else:
                pr = (0, r[1], 2000, r[3]) if side == 'W' else (W - 2000, r[1], W, r[3])
            SPECIAL_PORT_PINS[net].append((l, pr))
            nodes.append((name, [node]))
    seed_cells = {}
    if d.get('seeded'):
        for half in ('top', 'bot'):
            cs = set()
            for l, r in RAIL_SEEDS[net][half]:
                li = 0 if l == 'met4' else 1
                ww = (w4 if li == 0 else w5) // 2 + 200
                for j in range(math.ceil((r[1] + ww) / G), math.floor((r[3] - ww) / G) + 1):
                    for i in range(math.ceil((r[0] + ww) / G), math.floor((r[2] - ww) / G) + 1):
                        if not [B4, B5][li][j, i]:
                            cs.add((li, j, i))
            seed_cells[half] = cs
        nodes = [(f'{net}-top-feed', sorted(seed_cells['top']))] + nodes + [(f'{net}-bot-feed', sorted(seed_cells['bot'])[::3])]
    if len(nodes) < 2:
        say(f'special {net}: terminals {len(nodes)} — skip'); continue
    # 트리: 첫 단자에서 시작, 가까운 것부터
    n0 = [t for t in nodes[0][1] if t[0] == 0] or nodes[0][1]
    tree = set(n0[:1]) if not d.get('seeded') else set(seed_cells['top']); done = [nodes[0][0]]; rest = nodes[1:]
    TNODE = {nodes[0][0]: n0[0]}
    if not d.get('seeded') and next(iter(tree)) in M5START:
        x, y, pad = M5START[next(iter(tree))]
        put(net, 'met4', (min(pad[0], x - 600), min(pad[1], y - 600), max(pad[2], x + 600), max(pad[3], y + 600)), check=True, tag=f'{net}-m5start0')
        put_via(net, 'via4', x, y, check=False)
    tot = {'met4': 0, 'met5': 0}
    ok = True
    while rest:
        tj = [t[1] for t in tree]; ti = [t[2] for t in tree]
        tbox = (min(ti), min(tj), max(ti), max(tj))
        rest.sort(key=lambda t: min(abs(t[1][0][2] - tbox[0]) + abs(t[1][0][1] - tbox[1]), abs(t[1][0][2] - tbox[2]) + abs(t[1][0][1] - tbox[3])))
        name, st = rest.pop(0)
        path = astar([B4, B5], st, tree, tbox)
        if path is not None and name.endswith('-feed'):
            tree |= seed_cells['bot']
        if path is None:
            l0, j0, i0 = st[0]
            # 막힌 까닭을 보려고: 시작점에서 닿는 격자 수 (BFS, 최대 20000)
            seen = {(l0, j0, i0)}; q = [(l0, j0, i0)]
            while q and len(seen) < 20000:
                l, j, i = q.pop()
                nb = [(1 - l, j, i)] + ([(0, j + 1, i), (0, j - 1, i)] if l == 0 else [(1, j, i + 1), (1, j, i - 1)])
                for t in nb:
                    if 0 <= t[1] < NY and 0 <= t[2] < NX and not [B4, B5][t[0]][t[1], t[2]] and t not in seen:
                        seen.add(t); q.append(t)
            BAD.append(('special-route', net, '-', name, 'no path')); ok = False
            say(f'  {net}: NO PATH to {name} start ({l0},{um(i0*G)},{um(j0*G)}) reach {len(seen)} B4[start]={B4[j0,i0]} B5[start]={B5[j0,i0]}')
            continue
        if path[0] in M5START:                                        # 핀 위에서 바로 met5: met4 pad 를 via4 크기로 넓히고 via4
            x, y, pad = M5START[path[0]]
            m4 = (min(pad[0], x - 600), min(pad[1], y - 600), max(pad[2], x + 600), max(pad[3], y + 600))
            put(net, 'met4', m4, check=True, tag=f'{net}-m5start')
            put_via(net, 'via4', x, y, check=False)
        if len(tree) == 1 and next(iter(tree)) in M5START:
            pass
        TNODE[name] = path[0]
        ln = path_rects(net, path, w4, w5)
        for k in tot:
            tot[k] += ln[k]
        tree |= set(path); done.append(name)
    SKIP.add(net)
    # 단자마다 저항: 트리 격자 위 최단 저항 (met4 0.047·met5 0.0285 Ω/□, via4 배열 ≈ 0.38 / cut 수). 패드 → 블록 핀
    import heapq as _hq
    r4, r5 = 0.047 * G / w4, 0.0285 * G / w5
    nv = max(1, int((min(w4, w5) - 620 + 800) // 1600)) ** 2
    rv = 0.38 / nv

    def dij(src):
        dist = {src: 0.0}; pq = [(0.0, src)]
        while pq:
            d0, u = _hq.heappop(pq)
            if d0 > dist.get(u, 1e18):
                continue
            l, j, i = u
            nb = [((1 - l, j, i), rv)] + ([((0, j + 1, i), r4), ((0, j - 1, i), r4)] if l == 0 else [((1, j, i + 1), r5), ((1, j, i - 1), r5)])
            for v, c in nb:
                if v in tree and d0 + c < dist.get(v, 1e18):
                    dist[v] = d0 + c; _hq.heappush(pq, (d0 + c, v))
        return dist
    pads = [n for n in TNODE if '@' in n] or [n for n in TNODE if '.out' in n]     # 패드가 없는 vw 는 wbuf out 에서
    Rpin = {}
    if pads:
        dists = [dij(TNODE[p_]) for p_ in pads]
        for n_, t_ in TNODE.items():
            if n_ not in pads:
                Rpin[n_] = round(min(d.get(t_, 1e9) for d in dists), 3)
    SP_REPORT[net] = dict(R_pad_to_pin_ohm=Rpin, terminals=done, len_m4_um=um(tot['met4']), len_m5_um=um(tot['met5']), w4_um=um(w4), w5_um=um(w5), ok=ok,
                          R_est_ohm=round(0.047 * tot['met4'] / w4 + 0.0285 * tot['met5'] / w5, 3))
    say(f'special {net}: {len(done)} terminals, met4 {um(tot["met4"]):.0f} um, met5 {um(tot["met5"]):.0f} um, R(전체 길이 합) ≈ {SP_REPORT[net]["R_est_ohm"]} ohm, 패드→핀 {Rpin}')

# ───────────────────────── 6. met5 VDD·VSS 가로 줄 + drop ─────────────────────────
STRIPES = defaultdict(list)          # net → [rect]
SW, SP_ = 4000, 20000
y = 40000; k = 0
while y + SW // 2 < Hc - 32000:
    net = 'VSS' if k % 2 == 0 else 'VDD'
    cand = (4000, y - SW // 2, W - 4000, y + SW // 2)
    # 다른 넷 met5 와 겹치거나 1.6 µm 안이면 그 x 구간을 뺀다
    cuts = []
    for n2, r in DB.near('met5', cand, 2000):
        if n2 == net:
            continue
        if r[1] - 1600 < cand[3] and r[3] + 1600 > cand[1]:
            cuts.append((r[0] - 1700, r[2] + 1700))
    cuts.sort()
    segs = []; x0 = cand[0]
    for a, b in cuts:
        if a > x0:
            segs.append((x0, a))
        x0 = max(x0, b)
    if x0 < cand[2]:
        segs.append((x0, cand[2]))
    for a, b in segs:
        if b - a >= 10000:
            r = put(net, 'met5', (R.snap(a), cand[1], R.snap(b), cand[3]), check=False)
            STRIPES[net].append(r)
            for t in TRUNK[net]:
                ov = (max(t[0], r[0]), r[1], min(t[2], r[2]), r[3])
                if ov[2] - ov[0] >= 1420:
                    via4_array(net, ov, tag='stripe-trunk')
    y += SP_; k += 1
say('met5 stripes', {n: len(v) for n, v in STRIPES.items()})


def drop(net, l, pr, x, y):
    """pin (layer l, rect pr) 의 (x, y) 에 stack + met4 세로 줄 → 가장 가까운 같은 넷 met5 줄 (위·아래). 성공하면 True."""
    pad = stack_at(net, l, x, y, pr, check_only=True)
    if not pad:
        return False
    best = None
    for s in STRIPES[net] + RINGS5[net]:
        if s[0] + 800 <= x <= s[2] - 800:
            yc = (s[1] + s[3]) // 2
            d = abs(yc - y)
            if best is None or d < best[0]:
                best = (d, s, yc)
    if best is None:
        return False
    for s in sorted([s for s in STRIPES[net] + RINGS5[net] if s[0] + 800 <= x <= s[2] - 800], key=lambda s: abs((s[1] + s[3]) // 2 - y))[:3]:
        yc = (s[1] + s[3]) // 2
        r4 = (x - 800, min(y, yc) - 800, x + 800, max(y, yc) + 800)
        if ok_rect(net, 'met4', r4, False):
            stack_at(net, l, x, y, pr)
            put(net, 'met4', r4, check=False)
            put_via(net, 'via4', x, yc, check=False)
            return True
    return False


DROPS = defaultdict(int)
DROP_FAIL = []
pg_targets = []   # (inst, net, [(l, r)])
for n, I in INST.items():
    if I.cell.startswith('arr_'):
        continue                                        # 배열 vss = 기판 (p-tap), 배선 없이 칩 기판으로 VSS
    for p in I.m.pins:
        net = pin_net(n, p)
        if net in ('VDD', 'VSS'):
            sh = [(l, r) for l, r in I.pin_shapes(p) if l in ('met1', 'met2', 'met3')]
            if sh:
                pg_targets.append((n, p, net, sh))
for sp in SPINES:
    pg_targets.append(('tie-spine', 'met3', 'VSS', [('met3', sp)]))
# hvl inverter: tap rail 을 전원 rail 에 met1 로 묶음 (place/README §5-4)
for n, I in INST.items():
    if I.cell.startswith('sky130_fd_sc_hvl__'):
        x0, y0 = I.loc
        wcell = I.m.size[0]
        bs = put('VSS', 'met1', (x0 - 4000, y0 - 115, x0 + wcell, y0 + 625), check=True, tag='hvl-vnb')
        bd = put('VDD', 'met1', (x0, y0 + 3445, x0 + wcell + 4000, y0 + 4185), check=True, tag='hvl-vpb')
        PINS_BY_NET['VSS']['met1'].append(bs); PINS_BY_NET['VDD']['met1'].append(bd)
        pg_targets[:] = [t for t in pg_targets if t[0] != n]
        pg_targets.append((n, 'tapVSS', 'VSS', [('met1', (x0 - 4000, y0 - 115, x0 - 200, y0 + 625))]))
        pg_targets.append((n, 'tapVDD', 'VDD', [('met1', (x0 + wcell + 200, y0 + 3445, x0 + wcell + 4000, y0 + 4185))]))
def ext_sites(n, net, sh):
    """블록 경계 3 µm 안의 핀 도형 → 경계 밖 2.5 µm 까지 핀 층 연장 (같은 높이/폭). → [(l, ext_rect, x, y)] (아직 그리지 않음)."""
    I = INST.get(n)
    out = []
    if I is None:
        return out
    bx = I.bbox
    for l, r in sh:
        cx, cy = (r[0] + r[2]) // 2, (r[1] + r[3]) // 2
        for side, d in (('W', r[0] - bx[0]), ('E', bx[2] - r[2]), ('S', r[1] - bx[1]), ('N', bx[3] - r[3])):
            if d > 3000:
                continue
            if side in 'WE':
                h = max(r[3] - r[1], 400); y1 = R.snap(cy - h / 2)
                e = (bx[0] - 2500, y1, r[0] + 200, y1 + h) if side == 'W' else (r[2] - 200, y1, bx[2] + 2500, y1 + h)
                out.append((l, e, R.snap((e[0] + 1000) if side == 'W' else (e[2] - 1000)), R.snap(cy)))
            else:
                w = max(r[2] - r[0], 400); x1 = R.snap(cx - w / 2)
                e = (x1, bx[1] - 2500, x1 + w, r[1] + 200) if side == 'S' else (x1, r[3] - 200, x1 + w, bx[3] + 2500)
                out.append((l, e, R.snap(cx), R.snap((e[1] + 1000) if side == 'S' else (e[3] - 1000))))
    return out


for n, p, net, sh in pg_targets:
    I = INST.get(n)
    area = (I.bbox[2] - I.bbox[0]) * (I.bbox[3] - I.bbox[1]) if I else 10 ** 10
    quota = max(2, min(40, int(area / (80000 ** 2)) + 1))
    acc = []
    sites = pin_sites(net, sh, step=2000)
    # 고르게: 큰 도형부터, 받아들인 자리와 30 µm 떨어지게
    sites.sort(key=lambda s: -((s[1][2] - s[1][0]) * (s[1][3] - s[1][1])))
    for l, r, x, y in sites:
        if len(acc) >= quota:
            break
        if any(abs(x - a) + abs(y - b) < 30000 for a, b in acc):
            continue
        if drop(net, l, r, x, y):
            acc.append((x, y))
    if not acc:                                        # 경계 밖으로 늘여서
        for l, e, x, y in ext_sites(n, net, sh):
            if not ok_rect(net, l, e):
                continue
            PINS_BY_NET[net][l].append(e)
            if drop(net, l, e, x, y):
                put(net, l, e, check=False); acc.append((x, y)); break
            PINS_BY_NET[net][l].remove(e)
    DROPS[(n, net)] += len(acc)
    if not acc:
        DROP_FAIL.append((n, p, net))
say(f'PG drops: {sum(DROPS.values())} on {len(DROPS)} (inst,net); failed pins {len(DROP_FAIL)}')
for f in DROP_FAIL[:30]:
    say('  DROP FAIL', f)
nod = defaultdict(int)
for (n, net), c in DROPS.items():
    nod[(n, net)] += c
missing = sorted({(n, net) for n, p, net, sh in pg_targets if nod[(n, net)] == 0})
say(f'(inst, net) with no PG drop: {missing}')

# 전원 연결 검사: met4·met5 도형 + via4 로 묶은 덩어리. 고리 (ring) 에 닿지 않는 덩어리 = 블록 안을 거쳐야만 이어짐
def pg_islands(net):
    sh = [(l, r) for l, r in OWN[net] if l in ('met4', 'met5')]
    vias = [(it[2], it[3]) for it in DW.snets[net] if it[0] == 'via' and it[1].startswith('via4')]
    par = list(range(len(sh)))

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    idx = defaultdict(list)
    for k, (l, r) in enumerate(sh):
        for bx in range(r[0] // 50000, r[2] // 50000 + 1):
            for by in range(r[1] // 50000, r[3] // 50000 + 1):
                idx[(bx, by)].append(k)
    for k, (l, r) in enumerate(sh):
        for bx in range(r[0] // 50000, r[2] // 50000 + 1):
            for by in range(r[1] // 50000, r[3] // 50000 + 1):
                for k2 in idx[(bx, by)]:
                    l2, r2 = sh[k2]
                    if k2 > k and l2 == l and r[0] <= r2[2] and r2[0] <= r[2] and r[1] <= r2[3] and r2[1] <= r[3]:
                        par[f(k)] = f(k2)
    for x, y in vias:
        hit = [k for k in idx[(x // 50000, y // 50000)] if sh[k][1][0] <= x <= sh[k][1][2] and sh[k][1][1] <= y <= sh[k][1][3]]
        for k in hit[1:]:
            par[f(k)] = f(hit[0])
    ring = {f(k) for k, (l, r) in enumerate(sh) if r in TRUNK[net] or r in RINGS5[net]}
    comps = defaultdict(list)
    for k in range(len(sh)):
        comps[f(k)].append(k)
    isl = [c for c in comps if c not in ring]
    return len(comps), len(ring), isl, comps, sh


def link_islands(net):
    """고리에 닿지 않는 met5 줄 덩어리마다: 그 줄에서 met4 세로로 고리에 닿은 같은 넷 met5 줄까지 (via4 두 곳)."""
    nc, nr, isl, comps, sh = pg_islands(net)
    nlink = 0
    for c in isl:
        mine = [sh[k][1] for k in comps[c] if sh[k][0] == 'met5' and sh[k][1][3] - sh[k][1][1] >= 3000]
        others = [sh[k][1] for k in range(len(sh)) if sh[k][0] == 'met5' and sh[k][1][3] - sh[k][1][1] >= 3000 and k not in set(comps[c])]
        done = False
        for a in mine:
            for x in range(a[0] + 2000, a[2] - 1999, 2000):
                tg = sorted([o for o in others if o[0] + 1000 <= x <= o[2] - 1000], key=lambda o: abs((o[1] + o[3]) // 2 - (a[1] + a[3]) // 2))
                for o in tg[:4]:
                    ya, yo = (a[1] + a[3]) // 2, (o[1] + o[3]) // 2
                    r4 = (x - 800, min(ya, yo) - 800, x + 800, max(ya, yo) + 800)
                    if ok_rect(net, 'met4', r4, False):
                        put(net, 'met4', r4, check=False); put_via(net, 'via4', x, ya, check=False); put_via(net, 'via4', x, yo, check=False)
                        nlink += 1; done = True; break
                if done:
                    break
            if done:
                break
    return nlink


for net in ('VDD', 'VSS'):
    for it in range(4):
        nc, nr, isl, comps, sh = pg_islands(net)
        if not isl:
            break
        nl = link_islands(net)
        if nl == 0:
            break
    nc, nr, isl, comps, sh = pg_islands(net)
    big = [c for c in isl if any(sh[k][0] == 'met5' for k in comps[c])]
    say(f'PG {net}: pieces {nc}, ring pieces {nr}, pieces not on ring {len(isl)} (with met5 stripe {len(big)})')


def fill_same_net_gaps():
    """같은 넷 (이 스크립트가 그린) 도형 둘이 같은 층에서 최소 간격보다 가깝게 마주 보면 그 틈을 메움 (notch)."""
    nf = 0
    for net, L in list(OWN.items()):
        for layer in ('met2', 'met3', 'met4', 'met5'):
            rs = [r for l, r in L if l == layer]
            if len(rs) < 2:
                continue
            sp = R.MINS[layer] if layer != 'met5' else 1600
            idx = defaultdict(list)
            for k, r in enumerate(rs):
                for bx in range(r[0] // 20000, r[2] // 20000 + 1):
                    for by in range(r[1] // 20000, r[3] // 20000 + 1):
                        idx[(bx, by)].append(k)
            seen = set()
            for k, a in enumerate(rs):
                for bx in range(a[0] // 20000, a[2] // 20000 + 1):
                    for by in range(a[1] // 20000, a[3] // 20000 + 1):
                        for k2 in idx[(bx, by)]:
                            if k2 <= k or (k, k2) in seen:
                                continue
                            seen.add((k, k2)); b = rs[k2]
                            gx = max(a[0], b[0]) - min(a[2], b[2]); gy = max(a[1], b[1]) - min(a[3], b[3])
                            if 0 < gx < sp and gy < 0:          # 가로로 떨어짐, 세로로 겹침
                                y1, y2 = max(a[1], b[1]), min(a[3], b[3])
                                put(net, layer, (min(a[2], b[2]), y1, max(a[0], b[0]), y2), check=True, tag='gapfill', same_ok=True); nf += 1
                            elif 0 < gy < sp and gx < 0:
                                x1, x2 = max(a[0], b[0]), min(a[2], b[2])
                                put(net, layer, (x1, min(a[3], b[3]), x2, max(a[1], b[1])), check=True, tag='gapfill', same_ok=True); nf += 1
    return nf


say(f'same-net gap fills: {fill_same_net_gaps()}')
say(f'vias skipped (same-net cut already there): {dict(NSKIPV)}')

# ───────────────────────── 7. 핀 ─────────────────────────
PRE = ["# mk_route.py 가 씀: read_def 뒤에 innovus_top.tcl 이 source", "catch { connect_global_net VSS -type tie_lo -all }"]
for net in ('VDD', 'VSS'):
    l, r = PG_PINS[net][0]
    PRE.append(f"if {{[catch {{create_pg_pin -name {net} -net {net} -geom {l} {um(r[0]):.3f} {um(r[1]):.3f} {um(r[2]):.3f} {um(r[3]):.3f}}} m]}} {{ puts \"TOPR: PGPIN {net} FAIL $m\" }} else {{ puts \"TOPR: PGPIN {net}\" }}")
(OUT / 'chip_pre.tcl').write_text('\n'.join(PRE) + '\n')
for pn, kind in PORTS:
    if pn in SPECIAL_PORT_PINS:
        DW.pins.append(dict(name=pn, net=pn, dir=kind.upper(), x=0, y=0, shapes=SPECIAL_PORT_PINS[pn][:1]))
        continue
    if pn not in PJ:
        say(f'port {pn}: no pad info'); continue
    shapes = []
    for side, x, y in pad_points(pn):
        if side in 'NS':
            for off in sorted(range(-40, 41), key=abs):
                xx = R.snap(x + off * 480)
                r = (xx - 150, 0, xx + 150, 1400) if side == 'S' else (xx - 150, Hc - 1400, xx + 150, Hc)
                if ok_rect(pn, 'met2', r, False):
                    shapes.append(('met2', r)); break
        else:
            for off in sorted(range(-40, 41), key=abs):
                yy = R.snap(y + off * 740)
                r = (0, yy - 150, 1400, yy + 150) if side == 'W' else (W - 1400, yy - 150, W, yy + 150)
                if ok_rect(pn, 'met3', r, False):
                    shapes.append(('met3', r)); break
    shapes = shapes[:1]
    for l, r in shapes:
        put(pn, l, r, check=False)                   # pin 도형을 drawing 으로도 (x.5 규칙)
    if not shapes:
        BAD.append(('port', pn, '-', '-', 'no pin site'))
    DW.pins.append(dict(name=pn, net=pn, dir=kind.upper(), x=0, y=0, shapes=shapes))
# SPECIALNETS 의 연결 목록 (블록 핀) — 미리 그린 넷
for net in set(DW.snets):
    if net in NETS:
        DW.nets[net] = NETS[net]

# ───────────────────────── 8. 쓰기 ─────────────────────────
DW.write(str(OUT / 'chip_pre.def'))
# 입력 사본 (Olympus 경로가 로컬과 달라서): chip/lef/·chip/gds/ 로 모아 같이 올린다
import shutil
(OUT / 'lef').mkdir(exist_ok=True); (OUT / 'gds').mkdir(exist_ok=True)
used_cells = sorted({I.cell for I in INST.values()})
lefs = [TECH_LEF_OLY]
for c in used_cells:
    if c.startswith('sky130_fd_sc_hvl__'):
        continue
    src_l = LEF_FIX.get(c, TOPD / 'place' / 'lef' / f'{c}.lef')
    shutil.copy(src_l, OUT / 'lef' / f'{c}.lef'); lefs.append(oly(OUT / 'lef' / f'{c}.lef'))
lefs.append(HVL_LEF_OLY)
gds = []
for c in used_cells:
    if c.startswith('sky130_fd_sc_hvl__'):
        continue
    g0 = [I.gds for I in INST.values() if I.cell == c][0]
    shutil.copy(g0, OUT / 'gds' / f'{c}.gds'); gds.append(oly(OUT / 'gds' / f'{c}.gds'))
    say(f'  merge {c}: {g0}')
gds.append(HVL_GDS_OLY)
skip_list = sorted(SKIP)
ndr = []
cfg = f"""# mk_route.py 가 씀 — 손으로 고치지 않음
set TOP chip_core
set LEFS [list {' '.join(lefs)}]
set NETLIST {oly(OUT / 'chip_core_route.v')}
set DIE_W {um(W):.3f}
set DIE_H {um(Hc):.3f}
set PREDEF {oly(OUT / 'chip_pre.def')}
set SKIP_NETS {{{' '.join(skip_list)}}}
set PG_NETS {{VDD VSS}}
set NDR_RULES {{}}
set NDR_NETS {{}}
set GDS_MERGE [list {' '.join(gds)}]
set MAP /home/grads/s/seokjindaveoh/work/ep_dr/digital/pdk/sky130_hvl_stream.map
set OUT {oly(OUT / 'run' / 'chip_core')}
set PRE_TCL {oly(OUT / 'chip_pre.tcl')}
set POST_TCL {oly(OUT / 'post_patch.tcl')}
"""
(OUT / 'cfg_chip.tcl').write_text(cfg)
# NanoRoute 뒤 손질: 블록 LEF OBS 에서 빠진 (핀 둘레 halo) 블록 금속과 NanoRoute via 사이 같은 넷 notch 를 메움.
PATCHES = [
    ('col1_clk_n', 'met3', (664.60, 626.00, 664.98, 626.30), 'CDR.m3.2 notch: NanoRoute via2 pad ↔ col_blk 안 met3 (같은 넷), 잡 721323'),
]
PT = ['# mk_route.py 가 씀: route_design 뒤에 source']
for n_, l_, r_, why in PATCHES:
    PT.append(f'# {why}')
    PT.append(f'if {{[catch {{create_shape -net {n_} -layer {l_} -rect {{{r_[0]:.3f} {r_[1]:.3f} {r_[2]:.3f} {r_[3]:.3f}}} -status fixed -shape stripe}} m]}} {{ puts "TOPR: PATCH FAIL {n_} $m" }} else {{ puts "TOPR: PATCH {n_} {l_}" }}')
(OUT / 'post_patch.tcl').write_text('\n'.join(PT) + '\n')
json.dump(SP_REPORT, open(OUT / 'special_paths.json', 'w'), indent=1, ensure_ascii=False)
say(f'expected overlaps (row met3 ↔ array strap, same net) {len(EXPECTED)}')
say(f'BAD (규칙 검사에 걸린 그린 도형) {len(BAD)}')
for b in BAD[:40]:
    say('  BAD', b)
(OUT / 'mk_route_report.txt').write_text('\n'.join(REP) + '\n')
say('wrote', OUT / 'chip_pre.def', OUT / 'cfg_chip.tcl')

# LVS 용 CDL: test pattern 인스턴스를 뺀 사본 (layout 에 아직 없으므로). 블록 CDL 은 net/ 의 것을 그대로 include
cdl = (TOPD / 'net' / 'chip_core.cdl').read_text().splitlines()
outl, skip = [], False
for ln in cdl:
    if ln.startswith('X'):
        skip = any(ln.startswith(f'X{c} ') for c in SKIP_CELLS)
    elif not ln.startswith('+'):
        skip = False
    if not skip:
        outl.append(ln)
(OUT / 'chip_core_notp.cdl').write_text('\n'.join(outl) + '\n')
say(f'LVS CDL without test patterns: {OUT / "chip_core_notp.cdl"} ({len(cdl) - len(outl)} lines removed)')
