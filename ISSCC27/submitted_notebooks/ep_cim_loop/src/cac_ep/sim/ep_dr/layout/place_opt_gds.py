"""재배치 후보 (d) 배치 GDS + ISSCC 식 그림 (10/27, 사용자 "1000으로 유지하고 (d) 배치를 보여줘봐"). DRC·LVS·블록 사이 배선 없음 — 배치만.
floorplan_opt_D.json (floorplan_opt.py) → 실제 SKY130 IO 셀 (로컬 volare) + 가견적 블록 셀 B_* (out/chip_est_pr.gds.gz 안의 것, est_blocks.py 가 만든 셀)
+ core 전원 ring (met5 자리표시) + 빈 곳 decap 타일 (B_decap_tile).
블록 방향: nudge 반쪽 = free 반쪽을 180° 돌림 (R180), 합성 디지털 = 세워서 (R90), 나머지 R0. 셀 크기와 블록 자리 크기가 1 µm 넘게 다르면 멈춤.
낸다: out/chip_optD.gds (top ep_chip_optD), out/chip_optD_dark.png, ../../../deck/figs/real_circuit/fig_rc_chip_optD_isscc_dark.{tex,pdf,png}
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python place_opt_gds.py [floorplan_opt_D.json] [chip_optD]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import klayout.db as db
import klayout.lay as lay

HERE = Path(__file__).resolve().parent
FIG = HERE.parents[2] / 'deck' / 'figs' / 'real_circuit'
FP, NAME = (sys.argv[1:] + ['floorplan_opt_D.json', 'chip_optD'][len(sys.argv) - 1:])[:2]
F = json.load(open(HERE / FP))
W, H = F['die']['w'], F['die']['h']
OX, OY = F['core']['offset_in_die']
IO = Path('/home/dave/pdk/volare/sky130A/libs.ref/sky130_fd_io/gds')      # padframe_gds.py 의 iolib/ 과 같은 volare c6d73a35 원본
LYP = '/home/dave/pdk/volare/sky130A/libs.tech/klayout/tech/sky130A.lyp'
um = lambda v: int(round(v * 1000))

ly = db.Layout(); ly.dbu = 0.001
ly.read(str(IO / 'sky130_fd_io.gds'))
opt = db.LoadLayoutOptions(); opt.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
for f in ('sky130_ef_io.gds', 'sky130_ef_io__analog.gds', 'sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um.gds'):
    ly.read(str(IO / f), opt)
ly.read(str(HERE / 'out' / 'chip_est_pr.gds.gz'), opt)            # B_* 블록 셀 (IO 셀은 이미 있어 건너뜀)
for f in ('est_blocks_d2.gds', 'est_tests.gds'):                  # (d2) 세운 디지털 줄 블록 B_*_t, test 구조 B_tp_* (est_tests.py)
    if (HERE / 'out' / f).exists():
        ly.read(str(HERE / 'out' / f), opt)
T = ly.create_cell('ep_' + NAME)
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
assert not missing, missing
for cell in ly.each_cell():                                        # prBoundary 235/4 지움 (padframe_gds.py 와 같음)
    cell.shapes(ly.layer(235, 4)).clear()
M5, LO = ly.layer(72, 20), ly.layer(250, 9)
for rg in F['core_rings']:
    o, w = rg['offset'], rg['width']
    T.shapes(M5).insert(db.Region(db.Box(um(o), um(o), um(W - o), um(H - o))) - db.Region(db.Box(um(o + w), um(o + w), um(W - o - w), um(H - o - w))))
NUDGE_HALF = {'nudge crossbar', 'column MUX (nudge)', 'COL1/COL2 token (nudge)', 'input drive (nudge)', 'row MUX + WL (nudge)',
              'ROW1/ROW2 token (nudge)', 'row decoder (nudge)', 'DATA + latch + gate (nudge)'}
B, used = {}, db.Region()
for b in F['blocks']:
    x0, y0, x1, y1 = b['rect']; x0, x1, y0, y1 = x0 + OX, x1 + OX, y0 + OY, y1 + OY
    B[b['name']] = [x0, y0, x1, y1]
    if b['kind'] in ('route', 'test'):                             # 버스 통로·test 영역: decap 안 채움. test 셀 (est_tests.py) 이 있으면 영역 가운데에
        used.insert(db.Box(um(x0), um(y0), um(x1), um(y1)))
        c = ly.cell(b['cell']) if b['kind'] == 'test' else None
        if c is not None:
            bb = c.dbbox()
            assert bb.width() <= x1 - x0 + 0.01 and bb.height() <= y1 - y0 + 0.01, (b['name'], bb)
            T.insert(db.DCellInstArray(c.cell_index(), db.DTrans(x0 + (x1 - x0 - bb.width()) / 2 - bb.left, y0 + (y1 - y0 - bb.height()) / 2 - bb.bottom)))
        continue
    c = ly.cell(b['cell'])
    assert c is not None, b['cell']
    cb = c.dbbox()
    if b['name'] in NUDGE_HALF:
        t0 = db.DTrans.R180
    elif abs(cb.width() - (x1 - x0)) > 1 and abs(cb.width() - (y1 - y0)) < 1:
        t0 = db.DTrans.R90                                         # 세운 블록 (합성 디지털)
    else:
        t0 = db.DTrans.R0
    bb = cb.transformed(db.DTrans(t0))
    assert abs(bb.width() - (x1 - x0)) < 1 and abs(bb.height() - (y1 - y0)) < 1, (b['name'], bb, (x1 - x0, y1 - y0))
    T.insert(db.DCellInstArray(c.cell_index(), db.DTrans(x0 - bb.left, y0 - bb.bottom) * db.DTrans(t0)))
    T.shapes(LO).insert(db.Box(um(x0), um(y0), um(x1), um(y1)))
    used.insert(db.Box(um(x0 - 4), um(y0 - 4), um(x1 + 4), um(y1 + 4)))
c = ly.cell('B_decap_tile'); bb = c.dbbox(); px, py = bb.width() + 1.0, bb.height() + 1.0     # core 빈 곳 = decap 타일 (route_gds.py 와 같음)
cx0, cy0, cx1, cy1 = OX, OY, OX + F['core']['w'], OY + F['core']['h']
free = db.Region(db.Box(um(cx0), um(cy0), um(cx1), um(cy1))) - used
n_dc = 0
for i in range(int((cx1 - cx0) // px)):
    for j in range(int((cy1 - cy0) // py)):
        x, y = cx0 + i * px, cy0 + j * py
        if (db.Region(db.Box(um(x), um(y), um(x + bb.width()), um(y + bb.height()))) - free).is_empty():
            T.insert(db.DCellInstArray(c.cell_index(), db.DTrans(x - bb.left, y - bb.bottom))); n_dc += 1
if F.get('metal_plan'):                                            # (d3) 금속층 배정 그림 — 자리표시이고 실제 배선이 아님
    M4L = ly.layer(71, 20)
    for b in F['blocks']:                                          # met4 = 배선 띠·버스 통로 트랙 (간격 2 µm, 폭 0.9 µm, 긴 쪽 방향)
        if b['kind'] != 'route':
            continue
        x0, y0, x1, y1 = b['rect'][0] + OX, b['rect'][1] + OY, b['rect'][2] + OX, b['rect'][3] + OY
        horiz = (x1 - x0) >= (y1 - y0)
        lo = y0 if horiz else x0
        for k in range(int(((y1 - y0 if horiz else x1 - x0) - 2.0) // 2.0)):
            c0 = lo + 1.5 + k * 2.0
            T.shapes(M4L).insert(db.DBox(x0, c0, x1, c0 + 0.9) if horiz else db.DBox(c0, y0, c0 + 0.9, y1))
    PITCH5, W5 = 150.0, 6.0                                        # met5 = 전원 줄 (core 안 세로, VDD·VSS 번갈아, ring 이음은 배선 때)
    for k in range(int((cx1 - cx0 - 60) // PITCH5) + 1):
        x = cx0 + 30 + k * PITCH5
        T.shapes(M5).insert(db.DBox(x, cy0, x + W5, cy1))
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
gds = HERE / 'out' / f'{NAME}.gds'
ly.write(str(gds), so)
print(gds, 'blocks', len(F['blocks']), 'pads', len(F['pads']), 'decap tiles', n_dc)

# ── 검은 바탕 렌더 (fig_isscc_est.py 와 같은 방식)
M0, PX = 30.0, 6000
DARK = HERE / 'out' / f'{NAME}_dark.png'
lv = lay.LayoutView()
for k, v in (('background-color', '#000000'), ('grid-visible', 'false'), ('text-visible', 'false'), ('cell-box-visible', 'false')):
    lv.set_config(k, v)
lv.load_layout(str(gds), True); lv.load_layer_props(LYP); lv.add_missing_layers()
for lp in lv.each_layer():
    if (lp.source_layer, lp.source_datatype) in ((235, 0), (235, 4), (240, 0), (241, 0), (250, 9)):
        lp.visible = False
lv.active_cellview().cell_name = 'ep_' + NAME; lv.max_hier()
lv.zoom_box(db.DBox(-M0, -M0, W + M0, H + M0))
lv.save_image(str(DARK), PX, int(round(PX * (H + 2 * M0) / (W + 2 * M0))))


def U(*names):
    xs = [B[n] for n in names]
    return [min(r[0] for r in xs), min(r[1] for r in xs), max(r[2] for r in xs), max(r[3] for r in xs)]


ID = 'Input drive\\\\NMOS 2:1\\\\W 1,000 $\\times$ 198'
BOXES = [(U('free crossbar'), 'Free\\\\1T1R crossbar\\\\128 $\\times$ 64', 'in'),
         (U('nudge crossbar'), 'Nudge\\\\1T1R crossbar\\\\128 $\\times$ 64\\\\(rotated 180$^\\circ$)', 'in'),
         (U('input drive (free)'), ID, 'in'), (U('input drive (nudge)'), ID, 'in'),
         (U('row MUX + WL (free)'), 'Row MUX + WL driver', 'in90'), (U('row MUX + WL (nudge)'), 'Row MUX + WL driver', 'in90'),
         (U('ROW1/ROW2 token (free)', 'row decoder (free)'), 'Row shift reg. + decoder', 'in90'),
         (U('ROW1/ROW2 token (nudge)', 'row decoder (nudge)'), 'Row shift reg. + decoder', 'in90'),
         (U('DATA + latch + gate (free)'), 'DATA', 'in90'), (U('DATA + latch + gate (nudge)'), 'DATA', 'in90'),
         (U('column MUX (free)', 'COL1/COL2 token (free)'), 'Column MUX\\\\+ col. decoder', 'in'),
         (U('column MUX (nudge)', 'COL1/COL2 token (nudge)'), 'Column MUX\\\\+ col. decoder', 'in'),
         (U('WU1'), 'WU1', 'in'), (U('WU2'), 'WU2', 'in'),
         (U('global digital (1.8 V)', 'global digital (5 V)'), 'Digital control', ('out', 0, 100)),
         (U('bias'), 'Bias', ('out', 110, 0)),
         (U('nudge injector'), 'Nudge injector', ('out', 110, 0))]
BOXES += [(U(n), 'Write\\\\buffer', ('out', 0, 85)) for n in ('write buffer', 'write buffer (nudge)', 'write buffer (free)') if n in B]   # 10/27 배열마다 하나
BOXES += [(U(n), 'Test patterns', 'in90') for n in ('test area (top-left)', 'test area (bottom-right)') if n in B]
BOXES += [(U(n), '', 'in') for n in ('test area (band left)', 'test area (band right)') if n in B]   # 좁아서 네모만 (이름은 큰 두 곳에)
if 'routing ring (bottom)' in B:                                  # (d3) 배선 띠
    BOXES.append((U('routing ring (bottom)'), 'Routing ring 30 \\textmu m (met4)', 'in'))
WCM = 14.0
S = WCM / (W + 2 * M0)
P = lambda x, y: f'({(x + M0) * S:.3f},{(y + M0) * S:.3f})'
sgn = lambda v: (v > 0) - (v < 0)
L = [r"""\documentclass[border=4pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[helvet]{sfmath}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{arrows.meta}
\begin{document}
\begin{tikzpicture}[x=1cm,y=1cm,""",
     "  bx/.style={draw=white, line width=1.1pt},",
     "  lb/.style={font=\\fontsize{6.2}{7.2}\\selectfont\\bfseries, text=white, align=center, fill=black, fill opacity=0.55, text opacity=1, inner sep=1.2pt},",
     "  dm/.style={draw=black, line width=0.5pt, {Latex[length=1.6mm]}-{Latex[length=1.6mm]}}]",
     f"\\node[anchor=south west, inner sep=0] at (0,0) {{\\includegraphics[width={WCM}cm]{{{DARK}}}}};",
     f"\\fill[black, opacity=0.38] (0,0) rectangle {P(W + M0, H + M0)};"]
for (x0, y0, x1, y1), t, pos in BOXES:
    L.append(f"\\draw[bx] {P(x0, y0)} rectangle {P(x1, y1)};")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if not t:
        continue
    if pos == 'in':
        L.append(f"\\node[lb] at {P(cx, cy)} {{{t}}};")
    elif pos == 'in90':
        L.append(f"\\node[lb, rotate=90] at {P(cx, cy)} {{{t}}};")
    else:
        _, dx, dy = pos
        ex, ey = cx + dx, cy + dy
        sx, sy = cx + (x1 - x0) / 2 * sgn(dx), cy + (y1 - y0) / 2 * sgn(dy)
        anc = 'west' if dx > 0 else 'east' if dx < 0 else ('north' if dy < 0 else 'south')
        L.append(f"\\draw[white, line width=0.6pt] {P(sx, sy)} -- {P(ex, ey)};")
        L.append(f"\\node[lb, anchor={anc}] at {P(ex, ey)} {{{t}}};")
L.append(f"\\node[lb] at {P(W / 2, H - 120)} {{SKY130 I/O ring ({len(F['pads'])} pads)}};")
L.append(f"\\draw[dm] ({M0 * S:.3f},-0.25) -- ({(W + M0) * S:.3f},-0.25) node[midway, below=0.5pt, font=\\fontsize{{7}}{{8}}\\selectfont] {{{W / 1000:.2f} mm}};")
L.append(f"\\draw[dm] (-0.25,{M0 * S:.3f}) -- (-0.25,{(H + M0) * S:.3f}) node[midway, above=0.5pt, rotate=90, font=\\fontsize{{7}}{{8}}\\selectfont] {{{H / 1000:.2f} mm}};")
if F.get('metal_plan'):
    L.append(f"\\node[anchor=north west, font=\\fontsize{{6.5}}{{7.5}}\\selectfont, text width={WCM}cm] at (0,-0.75) "
             f"{{Metal plan: blocks met1--met3; global signals (control, register clocks, sense buses, V\\_W, bias) on met4 in the routing ring and bus channels; "
             f"power grid on met5 over the blocks. Tracks and straps are placeholders, not routed nets.}};")
L += ['\\end{tikzpicture}', '\\end{document}']
name = f'fig_rc_{NAME}_isscc_dark'
f = FIG / f'{name}.tex'
f.write_text('\n'.join(L) + '\n')
TB = os.path.expanduser('~/texlive/2026/bin/aarch64-linux')
subprocess.run([f'{TB}/pdflatex', '-interaction=nonstopmode', f.name], cwd=FIG, check=True, stdout=subprocess.DEVNULL)
subprocess.run(['pdftoppm', '-r', '600', '-png', '-singlefile', f'{name}.pdf', name], cwd=FIG, check=True)
for ext in ('aux', 'log'):
    (FIG / f'{name}.{ext}').unlink(missing_ok=True)
print(FIG / f'{name}.png')
