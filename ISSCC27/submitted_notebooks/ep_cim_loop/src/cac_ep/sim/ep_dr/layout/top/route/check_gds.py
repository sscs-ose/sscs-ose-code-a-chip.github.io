"""chip_core.gds 확인 (KLayout): top cell, 블록 SREF 자리 = place_real.json, 블록 cell 이 비지 않음 (merge 됨), core 핀 이름표.
쓰임: <klayout python> check_gds.py <gds> [place_real.json]
"""
import json
import sys
from pathlib import Path

import klayout.db as db

g = sys.argv[1]
pj = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parents[1] / 'place' / 'place_real.json')
P = json.load(open(pj))
ly = db.Layout(); ly.read(g)
tops = [c.name for c in ly.top_cells()]
print('top cells', tops)
top = ly.cell('chip_core')
bad = 0
seen = {}
for inst in top.each_inst():
    c = ly.cell(inst.cell_index)
    if c.name.startswith(('chip_core_VIA', 'M1M2', 'M2M3', 'M3M4', 'M4M5', 'L1M1')) or 'VIA' in c.name:
        continue
    bb = inst.dbbox()
    seen.setdefault(c.name, []).append(bb)
for n, v in P['instances'].items():
    want = (v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h'])
    cands = seen.get(v['cell'], [])
    # 블록 GDS bbox 는 LEF 경계보다 작거나 (빈 가장자리) 조금 클 수 있음 → 가장 가까운 것, 2 µm 안이면 OK
    best = min(cands, key=lambda b: abs(b.left - want[0]) + abs(b.bottom - want[1]), default=None)
    if best is None:
        print('MISSING', n, v['cell']); bad += 1; continue
    d = max(abs(best.left - want[0]), abs(best.bottom - want[1]), abs(best.right - want[2]), abs(best.top - want[3]))
    # GDS 도형이 LEF 경계 안쪽에 있으면 됨 (블록 가장자리가 비어 있을 수 있음). 밖으로 0.5 µm 넘게 나오면 OFF (hvl 셀의 nwell·hvi 는 0.42 µm 까지)
    out = max(want[0] - best.left, want[1] - best.bottom, best.right - want[2], best.top - want[3])
    tag = 'OK ' if out < 0.5 and d < 5.0 else 'OFF'
    if tag == 'OFF':
        bad += 1
    print(f'{tag} {n:8s} {v["cell"]:24s} gds bbox ({best.left:.3f},{best.bottom:.3f};{best.right:.3f},{best.top:.3f}) place {want} max|d| {d:.3f}')
empty = [c.name for c in ly.each_cell() if c.is_empty() and c.name != 'chip_core']
print('empty cells', empty[:20])
bad += len(empty)
labels = {}
for li in ly.layer_indexes():
    info = ly.get_info(li)
    for s in top.shapes(li).each():
        if s.is_text():
            labels.setdefault(s.text_string, []).append(f'{info.layer}/{info.datatype}')
print('top labels', len(labels), sorted(labels)[:40])
print('CHECK_GDS', 'PASS' if bad == 0 else f'FAIL {bad}')
