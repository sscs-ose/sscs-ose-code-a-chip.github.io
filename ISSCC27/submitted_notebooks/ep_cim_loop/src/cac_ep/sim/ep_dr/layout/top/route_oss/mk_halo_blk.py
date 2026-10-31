"""넓은 금속 (폭 ≥ 3 µm) 둘레 배선 막기 — Pegasus CDRW.m3.3d ("huge_met3 ↔ met3 ≥ 0.40 µm") 대책 (o4 → o5).
TritonRoute 는 tech LEF 의 SPACINGTABLE (폭 3 µm → 0.4) 을 알지만, 블록 안 넓은 금속은 LEF 에서 가는 핀·OBS 조각으로만 보여
0.3 µm 간격으로 다가간다 (o4: WP met3 via2 pad ↔ wbuf_n out 핀 + 블록 met3 덩어리 0.335 µm, 1 곳).
블록 + 미리 그린 도형만 든 GDS (t0/pre.gds = chip_pre.def + 블록 merge) 에서 층마다 폭 ≥ 3 µm 부분을 찾아
(간격 + 0.02) 만큼 둘레 띠를 만들고, 금속 자체와 이을 넷의 블록 핀 둘레 0.6 µm 는 뺀 뒤 BLOCKAGES 로 낸다.
쓰임: <klayout python> mk_halo_blk.py <pre.gds> → chip/halo_blk.txt
"""
import sys
from pathlib import Path

import klayout.db as db

import routelib as R

H = Path(__file__).resolve().parent
TOPD = H.parent
SP = {'met2': (69, 0.28), 'met3': (70, 0.40), 'met4': (71, 0.40)}    # tech LEF SPACINGTABLE WIDTH 3 (met1 은 넓은 부분 0)

# 이을 넷의 블록 핀 (LEF, core 좌표) — 막지 않게
M = {}
for f in sorted((TOPD / 'place' / 'lef').glob('*.lef')):
    R.parse_lef(str(f), M)
for f in sorted((H / 'lef_fix').glob('*.lef')):
    R.parse_lef(str(f), M)
R.parse_lef(str(TOPD.parents[1] / 'digital' / 'pdk' / 'sky130_fd_sc_hvl.lef'), M)
import json  # noqa: E402
P = json.load(open(TOPD / 'place' / 'place_real.json'))
route = set((H / 'chip' / 'route_nets.txt').read_text().split())
TOP, PORTS, CONN = R.parse_verilog(str(H / 'chip' / 'chip_core_route.v'), M, top='chip_core')
pinreg = {l: db.Region() for l in SP}
for iname, (cell, pmap) in CONN.items():
    v = P['instances'][iname]
    I = R.Inst(iname, M[cell], (R.g(v['x']), R.g(v['y'])), v['def_orient'])
    for p, n in pmap.items():
        if n in route:
            for l, r in I.pin_shapes(p):
                if l in pinreg:
                    pinreg[l].insert(db.Box(*r))

ly = db.Layout(); ly.read(sys.argv[1]); t = ly.cell('chip_core')
assert abs(ly.dbu - 0.001) < 1e-9
out = []
for nm, (gl, sp) in SP.items():
    m = db.Region(t.begin_shapes_rec(ly.layer(gl, 20))).merged()
    wide = m.sized(-1499).sized(1499) & m
    ring = (wide.sized(int(sp * 1000) + 20) - m - pinreg[nm].sized(600)).merged()
    rects = [p.bbox() for p in ring.decompose_trapezoids_to_region().each()]
    out += [f'- LAYER {nm} RECT ( {b.left} {b.bottom} ) ( {b.right} {b.top} ) ;' for b in rects if b.width() > 0 and b.height() > 0]
    print(f'{nm}: wide {wide.count()}, ring rects {len(rects)}, area {ring.area() / 1e6:.0f} um2')
(H / 'chip' / 'halo_blk.txt').write_text('\n'.join(out) + '\n')
print('wrote', H / 'chip' / 'halo_blk.txt', len(out))
