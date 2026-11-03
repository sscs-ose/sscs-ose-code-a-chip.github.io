"""Magic hvntm.1 위반 상자가 어느 셀 (방향 포함) 안에 있는지 + 그려진 hvntm (125/20) 을 펴서 잰 폭·간격 위반 수.
waive 근거 (README 「정한 것」): 모두 위아래로 뒤집힌 (MX) dfrtp_1 안이고, 그려진 층으로는 0.7 µm 미만이 없음.
쓰임: python hvntm_where.py <gds> <top> <Magic drc 보고서 (LibreLane drc.magic.rpt, µm 좌표)>"""
import re
import sys
from collections import Counter

import klayout.db as db

ly = db.Layout(); ly.read(sys.argv[1]); t = ly.cell(sys.argv[2])
txt = open(sys.argv[3]).read()
sec = txt.split('(hvntm.1)', 1)[1] if '(hvntm.1)' in txt else ''
boxes = [tuple(float(v) for v in m) for m in re.findall(r'^\s*([-0-9.]+)um ([-0-9.]+)um ([-0-9.]+)um ([-0-9.]+)um', sec, re.M)]
c = Counter()
for x0, y0, x1, y1 in boxes:
    b = db.DBox(x0, y0, x1, y1).to_itype(ly.dbu)
    hit = [ly.cell(i.cell_index).name.replace('sky130_fd_sc_hvl__', '') + ('/MX' if i.trans.is_mirror() else '/R0')
           for i in t.each_overlapping_inst(b)]
    c[','.join(sorted(hit)) or '(top)'] += 1
hv = db.Region(t.begin_shapes_rec(ly.layer(125, 20))).merged()
print(f"Magic hvntm.1 상자 {len(boxes)}: {dict(c)}")
print(f"그려진 hvntm: 다각형 {hv.count()}, 폭 < 0.7 µm {hv.width_check(700).count()}, 간격 < 0.7 µm {hv.space_check(700).count()}")
