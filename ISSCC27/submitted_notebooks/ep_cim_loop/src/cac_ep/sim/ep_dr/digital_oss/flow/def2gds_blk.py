"""OpenROAD 블록 DEF → GDS (KLayout LEF/DEF 읽기 + hvl 셀 GDS). route_oss/kl/def2gds.py 의 블록 판.
- 셀 도형은 LEF 가 아니라 hvl GDS 에서 (macro_resolution_mode 2: 이름만 있는 빈 cell 을 GDS 로 채움). 상용 판 GDS 와 같은 셀 GDS.
- 핀 = met*/16 (+ 같은 도형을 met*/20 으로, 상용 판 add_pg_labels_hvl.py 와 같음) + 이름표 met*/5. VDD·VSS 이름표는 met1 띠 위 (68/5) 에 하나씩.
쓰임: [FILL=fill.json] python3 def2gds_blk.py <def> <out.gds> <map> <hvl.gds[,macro.gds…]> <lef>...
"""
import os
import re
import sys
import klayout.db as db

dfn, out, mp, cgds, *lefs = sys.argv[1:]
ly = db.Layout()
opt = db.LoadLayoutOptions()
lo = opt.lefdef_config
lo.dbu = 0.001
lo.lef_files = [os.path.abspath(f) for f in lefs]
lo.read_lef_with_def = False
lo.map_file = os.path.abspath(mp)
lo.macro_resolution_mode = 2
for k in ('produce_cell_outlines', 'produce_placement_blockages', 'produce_regions', 'produce_routing_blockages',
          'produce_obstructions', 'produce_blockages'):
    if hasattr(lo, k):
        setattr(lo, k, False)
opt.lefdef_config = lo
ly.read(dfn, opt)
top = ly.top_cells()[0]
# DEF 에서 만들어진 via cell (M1M2_PR_1 …) 이름에 블록 이름을 붙인다: 블록마다 같은 이름이 다른 모양일 수 있어
# (col_blk·row_blk 의 M1M2_PR_2 등) 칩 GDS 에 블록을 합칠 때 같은 이름 cell 끼리 도형이 합쳐지면 단락 (10/30 칩 시험)
nren = 0
for c in list(ly.each_cell()):
    if c.cell_index() != top.cell_index() and not c.is_empty():
        c.name = f'{top.name}_{c.name}'; nren += 1
for g in cgds.split(','):
    ly.read(g)
for c in list(ly.top_cells()):
    if c.name != top.name:
        c.prune_cell()
npd = 0
for lay in (68, 69, 70):
    pi = ly.find_layer(lay, 16)
    if pi is None:
        continue
    di = ly.layer(lay, 20)
    for s in top.shapes(pi).each():
        if s.is_box() or s.is_polygon():
            top.shapes(di).insert(s.polygon); npd += 1
# VDD·VSS 이름표: DEF SPECIALNETS 의 첫 met1 띠 가운데
t = open(dfn).read()
ss = t[t.index('\nSPECIALNETS'):t.index('END SPECIALNETS')]
lab = ly.layer(68, 5)
nl = 0
for ent in re.split(r'\n\s*- ', ss)[1:]:
    nm = ent.split()[0]
    if nm not in ('VDD', 'VSS'):
        continue
    m = re.search(r'RECT met1 \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent)
    if m is None:
        m2 = re.search(r'met1 ([1-9]\d*) \+ SHAPE \w+ \( (-?\d+) (-?\d+) \) \( (-?\d+|\*) (-?\d+|\*) \)', ent)
        x1, y1 = int(m2.group(2)), int(m2.group(3)); x2 = x1 if m2.group(4) == '*' else int(m2.group(4))
        cx, cy = (x1 + x2) // 2, y1
    else:
        x1, y1, x2, y2 = map(int, m.groups()); cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    if nm in ('VDD', 'VSS'):
        top.shapes(lab).insert(db.Text(nm, db.Trans(cx, cy))); nl += 1
# 배선 막기 (DEF BLOCKAGES 의 LAYER 사각형) → <층>/10 (상용 판 GDS 와 같은 층: 칩 배선 mk_route.py 가 이 층을 읽어 막기로 씀, row_blk 서쪽 met2)
nblk = 0
if '\nBLOCKAGES' in t:
    bs = t[t.index('\nBLOCKAGES'):t.index('END BLOCKAGES')]
    for m in re.finditer(r'- LAYER (met\d) RECT \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', bs):
        top.shapes(ly.layer(67 + int(m.group(1)[3]), 10)).insert(db.Box(*map(int, m.groups()[1:]))); nblk += 1
# 매크로 줄 메움 (col_blk·row_blk): 환경 FILL = json 의 rects [층, dt, x1, y1, x2, y2] µm
nfill = 0
if os.environ.get('FILL'):
    import json
    for l, d, x1, y1, x2, y2 in json.load(open(os.environ['FILL']))['rects']:
        top.shapes(ly.layer(l, d)).insert(db.DBox(x1, y1, x2, y2).to_itype(ly.dbu)); nfill += 1
empty = [c.name for c in ly.each_cell() if c.is_empty() and c.name != top.name]
assert not empty, f'빈 cell (GDS 에 없는 셀): {empty}'
ly.write(out)
print('wrote', out, 'top', top.name, 'cells', ly.cells(), 'pin->drawing', npd, 'pg labels', nl, 'fill', nfill, 'route blockages', nblk, 'via cells renamed', nren)
