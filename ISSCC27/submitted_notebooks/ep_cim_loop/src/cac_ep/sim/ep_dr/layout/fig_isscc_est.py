"""가견적판 ISSCC 식 칩 그림 (10/27, 사용자 "보통 좀 어두운 GDS칼라에 흰색 굵은 네모박스 또는 검은색 굵은 네모박스하고 라벨 정보를 넣거든").
out/chip_est_pr.gds 를 검은 바탕으로 렌더 (KLayout) → TikZ: 반투명 검은 막으로 어둡게 + 기능 블록 흰 굵은 네모 + 흰 굵은 이름 + die 크기 화살표 (dark).
같은 네모·이름을 흰 바탕 그림 (out/chip_est_pr.png) 위에 검은색으로 (light). 버스 번호·패드 이름은 넣지 않는다.
읽음: route_est.json (블록 사각형, die 좌표 µm). 낸다: out/chip_est_dark.png, ../../../deck/figs/real_circuit/fig_rc_chip_est_isscc_{dark,light}.{tex,pdf,png}.
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python fig_isscc_est.py
"""
import json
import os
import subprocess
from pathlib import Path

import klayout.db as db
import klayout.lay as lay

HERE = Path(__file__).resolve().parent
FIG = HERE.parents[2] / 'deck' / 'figs' / 'real_circuit'
J = json.load(open(HERE / 'route_est.json'))
W, H = J['die']['w'], J['die']['h']
B = {k: v['rect'] for k, v in J['blocks'].items()}
M0, PX = 30.0, 6000
LYP = '/home/dave/pdk/volare/sky130A/libs.tech/klayout/tech/sky130A.lyp'

# ── 검은 바탕 렌더
DARK = HERE / 'out' / 'chip_est_dark.png'
lv = lay.LayoutView()
for k, v in (('background-color', '#000000'), ('grid-visible', 'false'), ('text-visible', 'false'), ('cell-box-visible', 'false')):
    lv.set_config(k, v)
lv.load_layout(str(HERE / 'out' / 'chip_est_pr.gds'), True); lv.load_layer_props(LYP); lv.add_missing_layers()
for lp in lv.each_layer():
    if (lp.source_layer, lp.source_datatype) in ((235, 0), (235, 4), (240, 0), (241, 0), (250, 9)):
        lp.visible = False
lv.active_cellview().cell_name = 'ep_chip_est_pr'; lv.max_hier()
lv.zoom_box(db.DBox(-M0, -M0, W + M0, H + M0))
lv.save_image(str(DARK), PX, int(round(PX * (H + 2 * M0) / (W + 2 * M0))))


def U(*names):
    xs = [B[n] for n in names]
    return [min(r[0] for r in xs), min(r[1] for r in xs), max(r[2] for r in xs), max(r[3] for r in xs)]


# (네모 사각형, 이름, 이름 자리: 'in' 가운데 / 'in90' 가운데 세로 / ('out', dx, dy) 네모 밖 + 짧은 선)
BOXES = [(U('free crossbar'), 'Free\\\\1T1R crossbar\\\\128 $\\times$ 64', 'in'),
         (U('nudge crossbar'), 'Nudge\\\\1T1R crossbar\\\\128 $\\times$ 64', 'in'),
         (U('input drive (free)'), 'Input drive\\\\NMOS 2:1\\\\W 1,000 $\\times$ 198', 'in'),
         (U('input drive (nudge)'), 'Input drive\\\\NMOS 2:1\\\\W 1,000 $\\times$ 198', 'in'),
         (U('row MUX + WL (free)'), 'Row MUX + WL driver', 'in90'),
         (U('row MUX + WL (nudge)'), 'Row MUX + WL driver', 'in90'),
         (U('ROW1/ROW2 token', 'row decoder (shared)', 'DATA + latch + gate'), 'Row shift reg.\\\\+ decoder + DATA', 'in90'),
         (U('column MUX (free)', 'COL1/COL2 token (free)'), 'Column MUX + diodes\\\\Col. decoder + shift reg.', 'in'),
         (U('column MUX (nudge)', 'COL1/COL2 token (nudge)'), 'Column MUX + diodes\\\\Col. decoder + shift reg.', 'in'),
         (U('WU1'), 'WU1', 'in'), (U('WU2'), 'WU2', 'in'),
         (U('write buffer'), 'Write buffer', ('out', 0, -95)),
         (U('global digital (1.8 V)', 'global digital (5 V)'), 'Digital control\\\\(config, clock buf., level shift)', ('out', 300, 30)),
         (U('bias'), 'Bias', ('out', -110, 40)),
         (U('nudge injector'), 'Nudge injector', ('out', 230, 0))]
DECAP = [((B['input drive (free)'][0] + B['input drive (free)'][2]) / 2 + 60, (B['global digital (5 V)'][3] + B['input drive (free)'][1]) / 2 + 30),
         ((B['input drive (nudge)'][0] + B['input drive (nudge)'][2]) / 2 + 40, (B['bias'][3] + B['nudge injector'][1]) / 2 + 10)]
WCM = 17.0
S = WCM / (W + 2 * M0)
P = lambda x, y: f'({(x + M0) * S:.3f},{(y + M0) * S:.3f})'
sgn = lambda v: (v > 0) - (v < 0)


def tex(name, png, dark):
    fg, bgc, op = ('white', 'black', 0.55) if dark else ('black', 'white', 0.75)
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
         f"  bx/.style={{draw={fg}, line width=1.1pt}},",
         f"  lb/.style={{font=\\fontsize{{6.2}}{{7.2}}\\selectfont\\bfseries, text={fg}, align=center, fill={bgc}, fill opacity={op}, text opacity=1, inner sep=1.2pt}},",
         "  dm/.style={draw=black, line width=0.5pt, {Latex[length=1.6mm]}-{Latex[length=1.6mm]}}]",
         f"\\node[anchor=south west, inner sep=0] at (0,0) {{\\includegraphics[width={WCM}cm]{{{png}}}}};"]
    if dark:                                                       # 전체를 어둡게
        L.append(f"\\fill[black, opacity=0.38] (0,0) rectangle {P(W + M0, H + M0)};")
    for (x0, y0, x1, y1), t, pos in BOXES:
        L.append(f"\\draw[bx] {P(x0, y0)} rectangle {P(x1, y1)};")
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if pos == 'in':
            L.append(f"\\node[lb] at {P(cx, cy)} {{{t}}};")
        elif pos == 'in90':
            L.append(f"\\node[lb, rotate=90] at {P(cx, cy)} {{{t}}};")
        else:
            _, dx, dy = pos
            ex, ey = cx + dx, cy + dy
            sx, sy = cx + (x1 - x0) / 2 * sgn(dx), cy + (y1 - y0) / 2 * sgn(dy)   # 네모 가장자리에서 선 시작
            anc = 'west' if dx > 0 else 'east' if dx < 0 else ('north' if dy < 0 else 'south')
            L.append(f"\\draw[{fg}, line width=0.6pt] {P(sx, sy)} -- {P(ex, ey)};")
            L.append(f"\\node[lb, anchor={anc}] at {P(ex, ey)} {{{t}}};")
    for x, y in DECAP:
        L.append(f"\\node[lb] at {P(x, y)} {{Decap}};")
    L.append(f"\\node[lb] at {P(W / 2, H - 120)} {{SKY130 I/O ring (42 pads)}};")
    y = -0.25                                                     # die 크기 화살표
    L.append(f"\\draw[dm] ({M0 * S:.3f},{y:.2f}) -- ({(W + M0) * S:.3f},{y:.2f}) node[midway, below=0.5pt, font=\\fontsize{{7}}{{8}}\\selectfont] {{{W / 1000:.2f} mm}};")
    x = -0.25
    L.append(f"\\draw[dm] ({x:.2f},{M0 * S:.3f}) -- ({x:.2f},{(H + M0) * S:.3f}) node[midway, above=0.5pt, rotate=90, font=\\fontsize{{7}}{{8}}\\selectfont] {{{H / 1000:.2f} mm}};")
    L += ['\\end{tikzpicture}', '\\end{document}']
    f = FIG / f'{name}.tex'
    f.write_text('\n'.join(L) + '\n')
    TB = os.path.expanduser('~/texlive/2026/bin/aarch64-linux')
    subprocess.run([f'{TB}/pdflatex', '-interaction=nonstopmode', f.name], cwd=FIG, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['pdftoppm', '-r', '600', '-png', '-singlefile', f'{name}.pdf', name], cwd=FIG, check=True)
    for ext in ('aux', 'log'):
        (FIG / f'{name}.{ext}').unlink(missing_ok=True)
    print(FIG / f'{name}.pdf')


tex('fig_rc_chip_est_isscc_dark', DARK, True)
tex('fig_rc_chip_est_isscc_light', HERE / 'out' / 'chip_est_pr.png', False)
