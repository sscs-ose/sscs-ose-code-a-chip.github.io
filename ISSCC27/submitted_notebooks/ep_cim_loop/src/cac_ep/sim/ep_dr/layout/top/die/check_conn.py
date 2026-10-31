"""die 배선 연결 검사 (KLayout, 금속·via 만): chip_die_lvs.gds 에서
 ① 패드 이름표 (core 넷 이름) 마다 같은 이름의 core 핀 이름표와 한 넷인지, ② 서로 다른 이름이 한 넷에 붙지 않았는지 (단락),
 ③ gpiov2 설정 핀 묶음 (THI·TLO = 패드마다, VSSD·VCCD = 변마다) 이 뜻한 핀만 묶고 core 넷·다른 묶음과 떨어져 있는지.
쓰임: <klayout python> check_conn.py <chip_die_lvs.gds> [pad_map.json]  → 끝 줄 'CONN OK' / 'CONN FAIL n'
"""
import json
import sys
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent / 'route'))
import routelib as R  # noqa: E402

gds = sys.argv[1]
PM = json.load(open(sys.argv[2] if len(sys.argv) > 2 else H / 'pad_map.json'))
OX, OY = PM['offset']
ly = db.Layout(); ly.read(gds); top = ly.cell('chip_die')
l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
L = {}
for n, (l, d) in {'m1': (68, 20), 'v1': (68, 44), 'm2': (69, 20), 'v2': (69, 44), 'm3': (70, 20), 'v3': (70, 44),
                  'm4': (71, 20), 'v4': (71, 44), 'm5': (72, 20)}.items():
    L[n] = l2n.make_layer(ly.layer(l, d), n)
seq = ['m1', 'v1', 'm2', 'v2', 'm3', 'v3', 'm4', 'v4', 'm5']
for a in seq:
    l2n.connect(L[a])
for a, b in zip(seq, seq[1:]):
    l2n.connect(L[a], L[b])
l2n.extract_netlist()
LM = {(68, 5): 'm1', (69, 5): 'm2', (70, 5): 'm3', (71, 5): 'm4', (72, 5): 'm5'}


def probe(layer, x, y):
    n = l2n.probe_net(L[layer], db.DPoint(x, y))
    return None if n is None else (n.circuit().name, n.cluster_id)


def labels(cell, dx, dy):
    out = []
    for (l, d), nm in LM.items():
        li = ly.find_layer(l, d)
        if li is None:
            continue
        for s in cell.shapes(li).each():
            if s.is_text():
                out.append((s.text.string, nm, s.dtext.x + dx, s.dtext.y + dy))
    return out


core = labels(ly.cell('chip_core'), OX, OY)
pads = labels(top, 0, 0)
net_names = {}
bad = 0
cnet = {}
for nm, l, x, y in core:
    k = probe(l, x, y); cnet[nm] = k
    net_names.setdefault(k, set()).add('core:' + nm)
for nm, l, x, y in pads:
    k = probe(l, x, y)
    net_names.setdefault(k, set()).add('pad:' + nm)
    if k is None or k != cnet.get(nm):
        print(f'OPEN/잘못: 패드 이름표 {nm} @({x:.2f},{y:.2f}) net={k} core net={cnet.get(nm)}'); bad += 1
for k, ns in net_names.items():
    base = {n.split(':')[1] for n in ns}
    if len(base) > 1:
        print('SHORT:', sorted(ns)); bad += 1
missing = sorted(set(cnet) - {nm for nm, *_ in pads})
print('core pin labels', len(core), 'pad labels', len(pads), 'core pins without pad', missing)
if missing:
    bad += len(missing)

# ③ gpiov2 설정 핀
M = R.parse_lef(str(Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_io/lef/sky130_ef_io.lef'))
fr = db.Layout(); fr.read(str(H.parent / 'place' / 'die_real.gds')); FT = fr.top_cells()[0]
TRS = [(fr.cell(i.cell_index).name, i.dcplx_trans) for i in FT.each_inst() if 'gpiov2_pad' in fr.cell(i.cell_index).name]
LYN = {'met1': 'm1', 'met2': 'm2', 'met3': 'm3'}
group = {}
core_nets = set(cnet.values())
for s in PM['slots']:
    if 'gpiov2' not in s['cell']:
        continue
    t = None
    for c, tt in TRS:
        b = tt * db.DBox(0, 0, M[c].size[0] / 1000, M[c].size[1] / 1000)
        if abs(b.left - s['rect'][0]) < 0.5 and abs(b.bottom - s['rect'][1]) < 0.5:
            t = tt
    tie = PM['gpio_tie'][s['net']]
    for pin, row in tie.items():
        l, r = max([(l, r) for l, r in M[s['cell']].pins[pin] if l in LYN],
                   key=lambda q: 0)                       # 핀은 조각 하나
        b = t * db.DBox(r[0] / 1000, r[1] / 1000, r[2] / 1000, r[3] / 1000)
        k = probe(LYN[l], b.center().x, b.center().y)
        key = (s['side'], row) if row in ('VSSD', 'VCCD') else (s['net'], row)
        group.setdefault(key, set()).add(k)
        if k is None or k in core_nets:
            print(f'설정 핀 {s["net"]}.{pin} → {row}: net={k} (끊김 또는 core 넷)'); bad += 1
allk = {}
for key, ks in group.items():
    if len(ks) != 1:
        print('묶음이 여러 넷:', key, len(ks)); bad += 1
    for k in ks:
        allk.setdefault(k, set()).add(key)
for k, keys in allk.items():
    if len(keys) > 1:
        print('묶음끼리 단락:', sorted(keys)); bad += 1
print('tie groups', len(group), '(per THI/TLO pad + per VSSD/VCCD side)')
print('CONN OK' if bad == 0 else f'CONN FAIL {bad}')
