"""Magic hvntm.1 (HVNTM 폭 < 0.7 µm) 표시가 거짓 양성인지 본다 (opensrc/scripts/hvntm_where.py 의 블록 판).
- 그려진 hvntm (125/20) 을 펴서 (merge) 폭·간격 < 0.7 µm 를 KLayout 으로 잼 → 0 이면 Magic 이 셀 경계에서 만든 조각 (거짓 양성).
- Magic 표시 상자 (internal unit = 0.005 µm) 가 걸친 셀 이름·방향.
쓰임: python3 hvntm_check.py <gds> <top> <magic .sum.boxes> <out.json>"""
import json
import sys
from collections import Counter

import klayout.db as db

g, top, bf, out = sys.argv[1:5]
ly = db.Layout(); ly.read(g); t = ly.cell(top)
c = Counter(); n = 0
for l in open(bf):
    if 'hvntm.1' not in l:
        continue
    n += 1
    x0, y0, x1, y1 = [float(v) * 0.005 for v in l.split('\t')[0].split()[:4]]
    b = db.DBox(x0 - 0.01, y0 - 0.01, x1 + 0.01, y1 + 0.01).to_itype(ly.dbu)
    hit = sorted({ly.cell(i.cell_index).name.replace('sky130_fd_sc_hvl__', '') + ('/MX' if i.trans.is_mirror() else '/R0')
                  for i in t.each_overlapping_inst(b)})
    c[','.join(hit) or '(top)'] += 1
hv = db.Region(t.begin_shapes_rec(ly.layer(125, 20))).merged()
r = dict(magic_hvntm1=n, cells=dict(c), drawn_polygons=hv.count(), drawn_width_lt_0p7=hv.width_check(700).count(),
         drawn_space_lt_0p7=hv.space_check(700).count())
r['false_positive'] = n == 0 or (r['drawn_width_lt_0p7'] == 0 and r['drawn_space_lt_0p7'] == 0)
json.dump(r, open(out, 'w'), indent=1)
print('HVNTM', r)
