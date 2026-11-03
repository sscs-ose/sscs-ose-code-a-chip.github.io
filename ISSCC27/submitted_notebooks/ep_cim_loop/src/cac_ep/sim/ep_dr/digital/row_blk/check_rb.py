#!/usr/bin/env python3
"""row_blk 배치·배선 뒤 검사 (LVS 가 못 보는 것): 계획 (row_blk_fp.json) · chip_lib ROWM 과 Innovus 결과를 맞대 봄.
  1. row_blk_pnr.v 의 매크로 636 개: a·b 넷이 ROWM 대로인지 (vw / vzero / R1·R2 / vwl / row[r] / wl[r]), ctl·ctlb 가 서로 다른 넷인지
  2. row_blk_pins.txt: 핀 층·자리 (서쪽 row[r]·wl[r] 은 배열 띠 자리) 가 계획대로인지
  3. row_blk_pnr.def: 매크로 위치·방향 (r0 = N, my = FN), 줄 (ROW) 이 channel 안에만 있는지
끝에 CHECK_RB: PASS / FAIL n
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mk_netlist import NR, actual, rowm_instances   # noqa: E402

p = json.loads((HERE / 'row_blk_fp.json').read_text())
fails = []


def bad(msg):
    fails.append(msg)
    if len(fails) <= 30:
        print('FAIL', msg)


def clean(n):
    n = n.strip()
    return re.sub(r'\s+', '', n[1:]) if n.startswith('\\') else n


# ── 1. 매크로 연결
_, insts = rowm_instances()
want = {}
for r in range(NR):
    for name, cell, pins in insts:
        want[f'rm{r}_{name}'] = (cell, {k: actual(f, r) for k, f in pins.items() if k in ('a', 'b')})
v = re.sub(r'//.*', '', (HERE / 'row_blk_pnr.v').read_text())
seen = {}
for m in re.finditer(r'\b(rb_\w+)\s+(\\?\S+)\s*\((.*?)\)\s*;', v, re.S):
    cell, iname, body = m.group(1), clean(m.group(2)), m.group(3)
    conns = {k: clean(n) for k, n in re.findall(r'\.(\w+)\s*\(\s*([^()]*?)\s*\)', body)}
    seen[iname] = (cell, conns)
for iname, (cell, ab) in want.items():
    if iname not in seen:
        bad(f'macro {iname} missing in pnr netlist')
        continue
    gcell, conns = seen[iname]
    if gcell != cell:
        bad(f'{iname} cell {gcell} != {cell}')
    for k, n in ab.items():
        if conns.get(k) != n:
            bad(f'{iname}.{k} = {conns.get(k)} (want {n})')
    c, cb = conns.get('ctl', ''), conns.get('ctlb', '')
    if not c or not cb or c == cb or "1'b" in c + cb:
        bad(f'{iname} ctl/ctlb = {c}/{cb}')
if len(seen) != len(want):
    bad(f'pnr netlist has {len(seen)} macros, want {len(want)}')
print(f'macros checked {len(want)} (a/b nets per ROWM, ctl != ctlb)')

# ── 2. 핀
got = {}
for ln in (HERE / 'row_blk_pins.txt').read_text().splitlines():
    t = [x.strip() for x in ln.split('|')]
    if len(t) >= 3:
        xy = [float(x) for x in re.findall(r'-?\d+\.?\d*', t[1])[:2]]
        got[t[0]] = (xy, t[2], t[3] if len(t) > 3 else '')
_d = (HERE / 'row_blk_pnr.def').read_text()
_m = re.search(r'DIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)', _d)
_u = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', _d).group(1))
W, H = int(_m.group(3)) / _u, int(_m.group(4)) / _u
npin = 0
for name, layer, side, pos, w, d in p['pins']:
    if name not in got:
        bad(f'pin {name} missing')
        continue
    (x, y), gl, rect = got[name]
    npin += 1
    if gl != layer:
        bad(f'pin {name} layer {gl} != {layer}')
    along, edge = {'W': (y, x), 'E': (y, x), 'N': (x, y), 'S': (x, y)}[side]
    e_want = {'W': 0.0, 'E': W, 'N': H, 'S': 0.0}[side]
    if abs(along - pos) > 0.002 or abs(edge - e_want) > 0.01:
        bad(f'pin {name} at ({x}, {y}) want {side} {pos}')
print(f'pins checked {npin} of {len(p["pins"])} (example row[1]: {got.get("row[1]")})')

# ── 3. DEF: 매크로 위치·방향, 줄
d = (HERE / 'row_blk_pnr.def').read_text()
dbu = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', d).group(1))
omap = {'r0': 'N', 'my': 'FN'}
comp = {m.group(1): (int(m.group(2)) / dbu, int(m.group(3)) / dbu, m.group(4))
        for m in re.finditer(r'-\s+(rm\d+_X\w+)\s+rb_\w+\s+\+\s+FIXED\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)', d)}
for mc in p['macros']:
    g = comp.get(mc['inst'])
    if g is None:
        bad(f'DEF: {mc["inst"]} not FIXED / missing')
    elif abs(g[0] - mc['x']) > 0.001 or abs(g[1] - mc['y']) > 0.001 or g[2] != omap[mc['orient']]:
        bad(f'DEF: {mc["inst"]} at {g} want ({mc["x"]}, {mc["y"]}, {omap[mc["orient"]]})')
rows = re.findall(r'^ROW\s+\S+\s+\S+\s+(-?\d+)\s+(-?\d+)\s+\w+\s+DO\s+(\d+)\s+BY\s+(\d+)\s+STEP\s+(\d+)', d, re.M)
for x, y, nx, ny, st in rows:
    x1, x2 = int(x) / dbu, (int(x) + int(nx) * int(st)) / dbu
    if not any(x1 > a - 0.001 and x2 < b + 0.001 for a, b in p['channels']):
        bad(f'DEF ROW at x {x1}..{x2} outside channels')
print(f'DEF: macros {len(comp)}, rows {len(rows)}')
print('CHECK_RB: PASS' if not fails else f'CHECK_RB: FAIL {len(fails)}')
