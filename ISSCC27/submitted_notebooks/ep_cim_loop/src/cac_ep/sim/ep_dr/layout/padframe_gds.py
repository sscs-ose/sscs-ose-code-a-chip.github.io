"""die + SKY130 IO ring GDS (v1, 10/26, 사용자 "PAD Frame에는 SKY130에서 제공해주었던 것처럼 powerrail과 ESD등을 참고해서 넣어봐").
floorplan.json (floorplan.py v1) 을 읽어 실제 sky130_ef_io 셀 (corner·gpiov2·analog_esd·전원 clamp 패드·com_bus_slice·이음 slice) 을 놓고,
core 전원 ring (met5 자리표시, VSS·VDD·VCM·VCCD) 과 core 블록 외곽 (241/0, 이름 글자) 을 더한다. v0 (자리표시 패드) = scratchpad 사본.
IO 라이브러리: iolib/ (volare sky130 c6d73a35 의 libs.ref/sky130_fd_io/gds 사본: sky130_fd_io.gds, sky130_ef_io.gds,
  sky130_ef_io__analog.gds, sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um.gds), 색 = libs.tech/klayout/tech/sky130A.lyp.
쓰임 (Olympus): QT_QPA_PLATFORM=offscreen ~/opt/kl312/bin/python padframe_gds.py [floorplan.json] [chip_v1] → out/<이름>.gds (top ep_<이름>, top + 쓰인 셀만), out/<이름>.png
  v2 (tape-out 준비, v3 핀) = padframe_gds.py floorplan_v2.json chip_v2
"""
import json
import os
import sys

import klayout.db as db
import klayout.lay as lay

H = os.path.dirname(os.path.abspath(__file__))
IO, OUT = os.path.join(H, 'iolib'), os.path.join(H, 'out')
os.makedirs(OUT, exist_ok=True)
FP, NAME = (sys.argv[1:] + ['floorplan.json', 'chip_v1'][len(sys.argv) - 1:])[:2]
F = json.load(open(os.path.join(H, FP)))
ly = db.Layout(); ly.dbu = 0.001
ly.read(os.path.join(IO, 'sky130_fd_io.gds'))                     # fd_io 먼저 (ef_io 의 빈 참조 셀을 채움)
opt = db.LoadLayoutOptions(); opt.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
for f in ('sky130_ef_io.gds', 'sky130_ef_io__analog.gds', 'sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um.gds'):
    ly.read(os.path.join(IO, f), opt)
T = ly.create_cell('ep_' + NAME)
um = lambda v: int(round(v * 1000))
missing = set()


def inst(name, ox, oy, rot):
    c = ly.cell(name)
    if c is None or c.bbox().empty():
        missing.add(name); return
    T.insert(db.CellInstArray(c.cell_index(), db.Trans(rot, False, um(ox), um(oy))))


for c in F['corners']:
    inst(c['cell'], *c['origin'], c['rot'])
for p in F['pads']:
    inst(p['cell'], *p['origin'], p['rot'])
for f in F['fillers']:
    inst(f['cell'], *f['origin'], f['rot'])
LY = {k: ly.layer(*v) for k, v in dict(bnd=(235, 4), m5=(72, 20), m5t=(72, 5), core=(240, 0), blk=(241, 0)).items()}
D = F['die']; W, Hh = D['w'], D['h']
for p in F['pads']:                                               # 패드 이름 (bond pad 가운데)
    x0, y0, x1, y1 = p['rect']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    M = D['margin']; dpt = 64.0
    bx, by = {'top': (cx, Hh - M - dpt), 'bottom': (cx, M + dpt), 'left': (M + dpt, cy), 'right': (W - M - dpt, cy)}[p['side']]
    T.shapes(LY['m5t']).insert(db.Text(p['name'], db.Trans(um(bx), um(by))))
for rg in F['core_rings']:                                        # core 전원 ring (met5 자리표시)
    o, w = rg['offset'], rg['width']
    outer = db.Region(db.Box(um(o), um(o), um(W - o), um(Hh - o)))
    inner = db.Region(db.Box(um(o + w), um(o + w), um(W - o - w), um(Hh - o - w)))
    T.shapes(LY['m5']).insert(outer - inner)
    T.shapes(LY['m5t']).insert(db.Text(rg['net'], db.Trans(um(W / 2), um(o + w / 2))))
ox, oy = F['core']['offset_in_die']
T.shapes(LY['core']).insert(db.Box(um(ox), um(oy), um(ox + F['core']['w']), um(oy + F['core']['h'])))
for b in F['blocks']:
    x0, y0, x1, y1 = b['rect']
    T.shapes(LY['blk']).insert(db.Box(um(ox + x0), um(oy + y0), um(ox + x1), um(oy + y1)))
    T.shapes(LY['blk']).insert(db.Text(b['name'], db.Trans(um(ox + (x0 + x1) / 2), um(oy + (y0 + y1) / 2))))
ly.clear_layer(LY['bnd'])                                         # prBoundary 235/4 는 DRC x.prBndry 위반 (IO 셀 안 포함) → 전부 지운다 (10/26)
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())          # top 과 그 아래 셀만
gds = os.path.join(OUT, NAME + '.gds')
ly.write(gds, so)

lv = lay.LayoutView()
lv.set_config('background-color', '#ffffff'); lv.set_config('grid-visible', 'false')
lv.set_config('text-visible', 'false'); lv.set_config('cell-box-visible', 'false')
lv.load_layout(gds, True)
lyp = os.path.join(IO, 'sky130A.lyp')
if os.path.exists(lyp):
    lv.load_layer_props(lyp)
lv.add_missing_layers()
for lp in lv.each_layer():                                        # 자리표시 층 (core·블록) 은 외곽선만
    if (lp.source_layer, lp.source_datatype) in ((240, 0), (241, 0)):
        lp.dither_pattern = 1; lp.fill_color = lp.frame_color = 0x4b5d80; lp.width = 2
cv = lv.active_cellview(); cv.cell_name = 'ep_' + NAME
lv.max_hier()
lv.zoom_box(db.DBox(-30, -30, W + 30, Hh + 30))
px = 2400
lv.save_image(os.path.join(OUT, NAME + '.png'), px, int(px * (Hh + 60) / (W + 60)))
print(gds, 'pads', len(F['pads']), 'fillers', len(F['fillers']), 'missing', sorted(missing))
