"""배선된 DEF → GDS (KLayout LEF/DEF 읽기 + 블록 GDS merge). Innovus `write_stream -merge` 대신.
쓰임: klayout -zz -rd cfg=<cfg_chip.tcl> -rd def=<routed.def> -rd out=<out.gds> -rd map=<sky130_kl.map> -r def2gds.py
  (또는 python3 def2gds.py cfg def out map — LibreLane 이미지의 python3 에는 klayout 모듈이 있다)
- LEF = cfg 의 LEFS (tech LEF + 블록 LEF + hvl 셀 LEF). 블록 도형은 LEF 가 아니라 cfg 의 GDS_MERGE (블록 GDS) 에서.
- macro_resolution_mode 2 = LEF 도형을 만들지 않고 이름만 있는 빈 cell → 블록 GDS 를 같은 layout 에 읽어 같은 이름 cell 에 채움.
"""
import os
import re
import sys

if len(sys.argv) >= 5:                       # python3 def2gds.py cfg def out map
    import klayout.db as db
    A = dict(zip(('cfg', 'def', 'out', 'map'), sys.argv[1:5]))
else:                                        # klayout -zz -rd ... -r def2gds.py
    import pya as db
    A = {k: globals()[k] for k in ('cfg', 'def', 'out', 'map')}

def tcl_list(txt, name):
    m = re.search(r'set ' + name + r' \[list ([^\]]*)\]', txt)
    return m.group(1).split()


cfg = open(A['cfg']).read()
lefs = tcl_list(cfg, 'LEFS')
gdss = tcl_list(cfg, 'GDS_MERGE')

ly = db.Layout()
opt = db.LoadLayoutOptions()
lo = opt.lefdef_config
lo.dbu = 0.001
lo.lef_files = lefs
lo.read_lef_with_def = False
lo.map_file = os.path.abspath(A['map'])
lo.macro_resolution_mode = 2
for k in ('produce_cell_outlines', 'produce_placement_blockages', 'produce_regions', 'produce_routing_blockages',
          'produce_obstructions', 'produce_blockages'):
    if hasattr(lo, k):
        setattr(lo, k, False)
opt.lefdef_config = lo
ly.read(A['def'], opt)
top = ly.top_cells()[0]
print('def top', top.name, 'cells', ly.cells())
for g in gdss:
    ly.read(g)                      # 같은 이름 cell 에 블록 도형이 들어감 (기본 AddToCell)
tops = [c.name for c in ly.top_cells()]
print('top cells after merge', tops)
# 블록 GDS 의 맨 위 cell 이 DEF 에서 쓰이지 않은 것 (예: hvl 라이브러리 전체) 은 지움
for c in list(ly.top_cells()):
    if c.name != top.name:
        c.prune_cell() if hasattr(c, 'prune_cell') else ly.delete_cell(c.cell_index())
if top.name != 'chip_core':
    top.name = 'chip_core'
npd = 0
for lay in (67, 68, 69, 70, 71, 72):
    pi = ly.find_layer(lay, 16)
    if pi is None:
        continue
    di = ly.layer(lay, 20)
    for s in top.shapes(pi).each():
        if s.is_box() or s.is_polygon():
            top.shapes(di).insert(s.polygon); npd += 1
print('pin shapes copied to drawing', npd)
empty = [c.name for c in ly.each_cell() if c.is_empty() and c.name != 'chip_core']
print('empty cells', empty)
ly.write(A['out'])
print('wrote', A['out'], 'top', [c.name for c in ly.top_cells()])
