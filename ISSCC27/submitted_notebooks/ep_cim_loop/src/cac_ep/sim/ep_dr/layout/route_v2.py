"""보고용 배치·연결 그림 (10/27, 사용자 "1T1R 으로 된 우리의 신경망에 대해서 각 회로에 대해서 배치만 해볼래? DRC를 하지 말고,
PAD Frame안에 배치만하고, 그냥 연결만 해놓아봐봐"). DRC·LVS 안 함 — 블록 수준 연결만.
floorplan_v2.json (PAD frame v2 + core 블록) → route_v2.json (블록 + 판독 TG, 배선 꺾은선). 연결은 v3 칩 덱 (real_circuit/gen_chip_deck2.py) 기준:
  패드 → 블록 (gpio 는 레벨 변환이 있는 합성 디지털로), 전원 패드 → core 전원 ring,
  DATA → 입력 구동, 행 decoder → row MUX, 합성 디지털 → 레지스터·decoder·WU·write buffer, row·열 MUX → free / nudge 버스 → WU1·WU2,
  R2 버스 → 판독 TG → VBUS 패드, write buffer → V_W 버스 → row·열 MUX, bias → WU·β 미러 → nudge 주입기 → nudge 출력 행.
GDS·그림: Olympus 에서 route_gds.py (→ out/chip_v2_pr.gds, out/chip_v2_pr.png), 그 PNG 를 가져온 뒤 다시 python route_v2.py 하면
TikZ 이름표를 얹어 ../../../deck/figs/real_circuit/fig_rc_chip_v2_pr.{tex,pdf,png} 를 만든다.
쓰임: python route_v2.py
"""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIG = HERE.parents[2] / 'deck' / 'figs' / 'real_circuit'
F = json.load(open(HERE / 'floorplan_v2.json'))
W, H = F['die']['w'], F['die']['h']
ox, oy = F['core']['offset_in_die']
BL = {b['name']: dict(kind=b['kind'], rect=[ox + b['rect'][0], oy + b['rect'][1], ox + b['rect'][2], oy + b['rect'][3]]) for b in F['blocks']}
BL['readout TG (free)'] = dict(kind='analog', rect=[1106.0, 650.0, 1130.0, 690.0])   # 가운데 빈 곳 (두 열 쌓음 사이), R2 버스 옆
BL['readout TG (nudge)'] = dict(kind='analog', rect=[1330.0, 650.0, 1354.0, 690.0])
X0 = lambda n: BL[n]['rect'][0]
Y0 = lambda n: BL[n]['rect'][1]
X1 = lambda n: BL[n]['rect'][2]
Y1 = lambda n: BL[n]['rect'][3]
XC = lambda n: (X0(n) + X1(n)) / 2
YC = lambda n: (Y0(n) + Y1(n)) / 2
RING = {r['net']: r['offset'] + r['width'] / 2 for r in F['core_rings']}           # die 가장자리에서 ring 가운데까지
P2R = {'VDD': 'VDD', 'VSS': 'VSS', 'VCM': 'VCM', 'VDDL': 'VCCD', 'VSSL': 'VSS'}      # VSSD = VSS
WID = dict(ana=5.0, dig=5.0, bus=8.0, pwr=10.0)
R = []


def route(net, cls, *pts, w=None):
    R.append(dict(net=net, cls=cls, w=w or WID[cls], pts=[[round(x, 2), round(y, 2)] for x, y in pts]))


def pin(p):
    """패드의 core 쪽 가장자리 가운데."""
    x0, y0, x1, y1 = p['rect']
    return dict(top=((x0 + x1) / 2, y0), bottom=((x0 + x1) / 2, y1), left=(x1, (y0 + y1) / 2), right=(x0, (y0 + y1) / 2))[p['side']]


pad = lambda name, side: pin([q for q in F['pads'] if q['name'] == name and q['side'] == side][0])

# ── 전원 패드 → core 전원 ring
for p in F['pads']:
    if p['name'] in P2R:
        (x, y), d = pin(p), RING[P2R[p['name']]]
        route(p['name'], 'pwr', (x, y), dict(top=(x, H - d), bottom=(x, d), left=(d, y), right=(W - d, y))[p['side']])

# ── 위 변: VRAILP·VRAILM → 입력 구동 (+ 입력 구동 옆 틈으로 clamp 다이오드: 위 = VRAILM, 아래 = VRAILP)
for blk, arr, sgn, gx in (('input drive (free)', 'free', +1, X1('input drive (free)')), ('input drive (nudge)', 'nudge', -1, X0('input drive (nudge)'))):
    for nm in ('VRAILP', 'VRAILM'):
        q = min((q for q in F['pads'] if q['name'] == nm and q['side'] == 'top'), key=lambda q: abs(pin(q)[0] - XC(blk)))
        x, y = pin(q); route(nm, 'ana', (x, y), (x, Y1(blk)))
    up, dn = f'clamp diode up ({arr})', f'clamp diode down ({arr})'
    ax = X0(up) if sgn > 0 else X1(up)
    route('VRAILP', 'ana', (gx, 1420), (gx + sgn * 4.5, 1420), (gx + sgn * 4.5, YC(dn)), (ax, YC(dn)))
    route('VRAILM', 'ana', (gx, 1425), (gx + sgn * 10.5, 1425), (gx + sgn * 10.5, YC(up)), (ax, YC(up)))

# ── 오른쪽 변: bias 패드 → bias
for nm in ('IBIAS', 'VBNC', 'VBPC'):
    x, y = pad(nm, 'right'); route(nm, 'ana', (x, y), (X1('bias'), y))

# ── 아래 변: 쓰기 전압 → write buffer (V_WL 은 V_W 버스와 같이 row MUX 로), 판독 VBUS ← 판독 TG, gpio → 합성 디지털
for nm in ('VWH', 'VWLO', 'VWL'):
    x, y = pad(nm, 'bottom'); route(nm, 'ana', (x, y), (x, Y0('write buffer')))
TRK_B = 326.0                                                      # 아래 변 가로 통로 (VCCD ring 과 core 사이)
for nm, tg, gx in (('VBUS_F', 'readout TG (free)', (X1('WU1') + X0('write buffer')) / 2 + 2.5),
                   ('VBUS_N', 'readout TG (nudge)', (X1('write buffer') + X0('WU2')) / 2 - 0.5)):
    x, y = pad(nm, 'bottom'); route(nm, 'ana', (x, y), (x, TRK_B), (gx, TRK_B), (gx, Y0(tg)))
for nm in ('LQ1', 'LQ2', 'CK', 'CK3', 'LAT'):
    x, y = pad(nm, 'bottom')
    tx = min(x, X1('global digital') - 15)
    route(nm, 'dig', *([(x, y), (x, Y0('global digital'))] if tx == x else [(x, y), (x, TRK_B), (tx, TRK_B), (tx, Y0('global digital'))]))

# ── 왼쪽 변: gpio 6 → 합성 디지털 왼쪽 (아래로 몰기: 위에 있는 패드일수록 안쪽 세로 통로)
for k, nm in enumerate(['SCK', 'SDI', 'SLD', 'RST', 'SEL_EN', 'WP']):
    x, y = pad(nm, 'left')
    ty, tx = Y0('global digital') + 40 + k * 48, 290.0 + k * 8
    route(nm, 'dig', (x, y), (tx, y), (tx, ty), (X0('global digital'), ty))

# ── core 안 (블록 수준 버스)
C_DIG, C_FREE, C_NUD, C_CLK, C_BIAS = 614.0, 600.0, 586.0, 572.0, 556.0      # 버스 통로 (아래 줄 위 ~ 열 token 아래)
GDx = X1('global digital')
XF, XN = X0('row MUX + WL (free)') + 5, X1('row MUX + WL (nudge)') - 5          # free / nudge 버스 세로 줄기
XV, XS = XC('write buffer'), XC('ROW1/ROW2 token')                           # V_W 줄기, spine 제어 줄기
# 합성 디지털 → 레지스터·decoder (SDI, 레지스터 클록, 동작 신호, SEL_EN)
route('ctl', 'dig', (GDx, C_DIG), (XC('COL1/COL2 token (nudge)'), C_DIG), (XC('COL1/COL2 token (nudge)'), Y0('COL1/COL2 token (nudge)')))
route('ctl', 'dig', (XC('COL1/COL2 token (free)'), C_DIG), (XC('COL1/COL2 token (free)'), Y0('COL1/COL2 token (free)')))
route('ctl', 'dig', (XS, C_DIG), (XS, 940), (XC('DATA + latch + gate'), 940), (XC('DATA + latch + gate'), Y0('DATA + latch + gate')))
route('ctl', 'dig', (XS, 940), (XS, Y0('ROW1/ROW2 token')))
route('ctl', 'dig', (XC('row decoder (shared)'), 940), (XC('row decoder (shared)'), Y0('row decoder (shared)')))
# 합성 디지털 ↔ WU1·WU2·write buffer (CK, CK3, LAT/LATB, LQ, WP, POL)
DWU1, DWB, DWU2 = X0('WU1') + 40, X1('write buffer') - 45, X1('WU2') - 60
route('wu ctl', 'dig', (GDx, C_CLK), (DWU2, C_CLK), (DWU2, Y1('WU2')))
for x in (DWU1, DWB):
    route('wu ctl', 'dig', (x, C_CLK), (x, Y1('WU1')))
# free / nudge 버스: row MUX (R1, R2) + 열 MUX (C1, C2) → WU1 (R1, C1) · WU2 (R2, C2), R2 → 판독 TG
for p, xt, cy, d1, d2, cm, tg in (('free', XF, C_FREE, X0('WU1') + 120, X0('WU2') + 60, X1('column MUX (free)'), 'readout TG (free)'),
                                  ('nudge', XN, C_NUD, X0('WU1') + 200, X0('WU2') + 140, X0('column MUX (nudge)'), 'readout TG (nudge)')):
    route(f'{p} bus', 'bus', (xt, Y0(f'row MUX + WL ({p})')), (xt, cy))
    route(f'{p} bus', 'bus', (cm, YC(f'column MUX ({p})')), (xt, YC(f'column MUX ({p})')))
    route(f'{p} bus', 'bus', (d1, Y1('WU1')), (d1, cy), (d2, cy), (d2, Y1('WU2')))
    route(f'{p} bus', 'bus', (xt, YC(tg)), (X0(tg) if p == 'free' else X1(tg), YC(tg)))
# write buffer → V_W (+ V_WL) 버스 → row MUX·열 MUX (두 배열)
route('V_W', 'ana', (XV, Y1('write buffer')), (XV, 905))
route('V_W', 'ana', (X0('row MUX + WL (free)') + 25, Y0('row MUX + WL (free)')), (X0('row MUX + WL (free)') + 25, 905),
      (X1('row MUX + WL (nudge)') - 25, 905), (X1('row MUX + WL (nudge)') - 25, Y0('row MUX + WL (nudge)')))
route('V_W', 'ana', (X1('column MUX (free)'), YC('column MUX (free)') + 14), (X0('column MUX (nudge)'), YC('column MUX (nudge)') + 14))
# 행 decoder (spine) → row MUX + WL (행 pitch 로 token·DATA 위를 지남)
for yy in (1100, 1300):
    route('row select', 'dig', (X0('row decoder (shared)'), yy), (X1('row MUX + WL (free)'), yy))
    route('row select', 'dig', (X1('row decoder (shared)'), yy), (X0('row MUX + WL (nudge)'), yy))
# DATA (+ latch + gate) → 입력 구동 (두 배열), 배열 위 통로
YD = Y1('clamp diode up (free)') + 7.5
route('D', 'dig', (XC('input drive (free)') + 110, Y1('input drive (free)')), (XC('input drive (free)') + 110, YD),
      (XC('input drive (nudge)') - 110, YD), (XC('input drive (nudge)') - 110, Y1('input drive (nudge)')))
route('D', 'dig', (XC('DATA + latch + gate'), Y1('DATA + latch + gate')), (XC('DATA + latch + gate'), YD))
# bias → WU1·WU2 (vbn, vbp, VBNC, VBPC), β 미러 → nudge 주입기 → nudge 출력 행
route('bias', 'ana', (X0('bias') + 40, Y1('bias')), (X0('bias') + 40, C_BIAS), (X1('WU1') - 30, C_BIAS), (X1('WU1') - 30, Y1('WU1')))
route('bias', 'ana', (X1('WU2') - 20, C_BIAS), (X1('WU2') - 20, Y1('WU2')))
XB = X0('nudge injector') + 70                                     # Decap 이름표를 피함
route('beta', 'ana', (XB, Y1('bias')), (XB, Y0('nudge injector')))
yo = (Y0('row MUX + WL (nudge)') + Y0('input drive (nudge)')) / 2
route('nudge inj', 'ana', (X0('nudge injector'), yo), (X1('nudge crossbar'), yo))

LABEL = dict(  # 블록 이름표 (그림)
    blocks={'free crossbar': 'Free 1T1R crossbar\\\\128 $\\times$ 64', 'nudge crossbar': 'Nudge 1T1R crossbar\\\\128 $\\times$ 64',
            'input drive (free)': 'Input drive (READ)\\\\NMOS 2:1 $\\times$ 100', 'input drive (nudge)': 'Input drive (READ)\\\\NMOS 2:1 $\\times$ 100',
            'column MUX (free)': 'Column MUX', 'column MUX (nudge)': 'Column MUX', 'column decoder (free)': 'Column decoder',
            'column decoder (nudge)': 'Column decoder', 'COL1/COL2 token (free)': 'COL1 / COL2 shift reg.', 'COL1/COL2 token (nudge)': 'COL1 / COL2 shift reg.',
            'clamp diode up (free)': 'Clamp diode', 'clamp diode down (free)': 'Clamp diode', 'clamp diode up (nudge)': 'Clamp diode',
            'clamp diode down (nudge)': 'Clamp diode', 'WU1': 'WU1\\\\(first stage)', 'WU2': 'WU2\\\\(last stage)', 'write buffer': 'Write\\\\buffer',
            'global digital': 'Global digital (1.8 V)\\\\config reg., mode decoder,\\\\clock buffers, level shifters',
            'bias': 'Bias\\\\HOG bias, $\\beta$ mirror', 'nudge injector': 'Nudge\\\\injector $\\times$3', 'decap (left)': 'Decap',
            'decap (right, lower)': 'Decap', 'decap (right, upper)': 'Decap'},
    rot={'row MUX + WL (free)': 'Row MUX + WL', 'row MUX + WL (nudge)': 'Row MUX + WL', 'ROW1/ROW2 token': 'ROW1 / ROW2 shift reg.',
         'row decoder (shared)': 'Row decoder', 'DATA + latch + gate': 'DATA reg. + latch'},
    callouts=[  # (번호, 범례 문구, 선 위 자리) — 버스 이름은 번호로, 뜻은 그림 아래 범례에
        (1, 'Free bus: R1, C1 $\\rightarrow$ WU1; R2, C2 $\\rightarrow$ WU2', (XF, 820)),
        (2, 'Nudge bus: R1, C1 $\\rightarrow$ WU1; R2, C2 $\\rightarrow$ WU2', (XN, 820)),
        (3, 'V$_\\mathrm{W}$, V$_\\mathrm{WL}$: write buffer $\\rightarrow$ row / column MUX', (XV, 700)),
        (4, 'SDI, register clocks (SCK$\\cdot$TSEL), mode, SEL\\_EN', (XS, 720)),
        (5, 'CK, CK3, LAT, LQ1/2, WP, POL', (1600, C_CLK)),
        (6, 'vbn, vbp: bias $\\rightarrow$ WU1, WU2', (1710.7, C_BIAS)),
        (7, '$\\beta$ mirror: bias $\\rightarrow$ nudge injector', (XB, 700)),
        (8, 'D: DATA latch $\\rightarrow$ input drive gates', (1200, YD)),
        (9, 'Row select: row decoder $\\rightarrow$ row MUX + WL', (X1('DATA + latch + gate') + 15, 1100)),
        (10, 'Readout TG: R2 bus $\\rightarrow$ VBUS pad', (XC('readout TG (free)'), Y1('readout TG (free)') + 14)),
        (10, '', (XC('readout TG (nudge)'), Y1('readout TG (nudge)') + 14)),
        (11, 'Nudge current $\\rightarrow$ nudge output rows', (X0('nudge injector') - 8, yo + 30)),
        (12, 'VRAILP / VRAILM $\\rightarrow$ clamp diodes', (X1('input drive (free)') + 7.5, 1150)),
        (12, '', (X0('input drive (nudge)') - 7.5, 1150))])
json.dump(dict(note='보고용 배치·연결 (DRC·LVS 없음). 좌표 µm, die 좌표.', die=dict(w=W, h=H), blocks=BL, routes=R, labels=LABEL),
          open(HERE / 'route_v2.json', 'w'), indent=1, ensure_ascii=False)
print('blocks', len(BL), 'routes', len(R))

# ── TikZ (Olympus 의 KLayout 그림이 있을 때)
PNG = HERE / 'out' / 'chip_v2_pr.png'
if PNG.exists():
    M0, WCM = 30.0, 17.0                                            # M0 = route_gds.py 의 zoom 여백 (µm)
    S = WCM / (W + 2 * M0)
    P = lambda x, y: f'({(x + M0) * S:.3f},{(y + M0) * S:.3f})'
    L = [r"""\documentclass[border=4pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[helvet]{sfmath}
\usepackage{graphicx}
\usepackage{tikz}
\definecolor{maroon}{HTML}{500000}
\definecolor{navy}{HTML}{001C54}
\definecolor{purp}{HTML}{4B3B7A}
\definecolor{grayp}{HTML}{7F7F7F}
\begin{document}
\begin{tikzpicture}[x=1cm,y=1cm,
  bl/.style={font=\fontsize{5.5}{6.2}\selectfont, align=center, text=black},
  pl/.style={font=\fontsize{4.6}{5}\selectfont\bfseries, fill=white, fill opacity=0.85, text opacity=1, inner sep=0.6pt, rounded corners=0.5pt},
  bu/.style={font=\fontsize{4.6}{5}\selectfont, fill=white, fill opacity=0.85, text opacity=1, inner sep=0.8pt},
  co/.style={circle, draw=black, line width=0.3pt, fill=white, inner sep=0.3pt, minimum size=0.24cm, font=\fontsize{4.6}{5}\selectfont\bfseries}]
""", f"\\node[anchor=south west, inner sep=0] at (0,0) {{\\includegraphics[width={WCM}cm]{{{PNG}}}}};"]
    for n, t in LABEL['blocks'].items():
        L.append(f"\\node[bl] at {P(XC(n), YC(n))} {{{t}}};")
    for n, t in LABEL['rot'].items():
        L.append(f"\\node[bl, rotate=90] at {P(XC(n), YC(n))} {{{t}}};")
    for p in F['pads']:
        x0, y0, x1, y1 = p['rect']
        nm = 'spare' if p['name'].startswith('SPARE') else p['name'].replace('_', '\\_')
        L.append(f"\\node[pl, rotate={90 if p['side'] in ('top', 'bottom') else 0}] at {P((x0 + x1) / 2, (y0 + y1) / 2)} {{{nm}}};")
    for k, t, (x, y) in LABEL['callouts']:
        L.append(f"\\node[co] at {P(x, y)} {{{k}}};")
    for k, (net, d) in enumerate(RING.items()):                     # core 전원 ring 이름
        L.append(f"\\node[bu] at {P(900 + 70 * k, H - d)} {{{net}}};")
    yl = -0.35
    for k, (col, t) in enumerate((('maroon', 'analog signal / bus'), ('navy', 'digital / control'), ('purp', 'free \\& nudge bus'),
                                  ('grayp', 'power (pad $\\rightarrow$ core ring)'))):
        L.append(f"\\fill[{col}] ({0.2 + 4.2 * k:.2f},{yl - 0.06:.2f}) rectangle ({0.7 + 4.2 * k:.2f},{yl + 0.06:.2f}); "
                 f"\\node[anchor=west, font=\\fontsize{{6}}{{7}}\\selectfont] at ({0.75 + 4.2 * k:.2f},{yl:.2f}) {{{t}}};")
    seen = sorted({(k, t) for k, t, _ in LABEL['callouts'] if t})
    for j, (k, t) in enumerate(seen):                               # 번호 범례: 3 단
        cx, cy = 0.35 + 5.7 * (j // 4), yl - 0.38 - 0.27 * (j % 4)
        L.append(f"\\node[co] at ({cx:.2f},{cy:.2f}) {{{k}}}; \\node[anchor=west, font=\\fontsize{{5.5}}{{6.5}}\\selectfont] at ({cx + 0.18:.2f},{cy:.2f}) {{{t}}};")
    L += ['\\end{tikzpicture}', '\\end{document}']
    tex = FIG / 'fig_rc_chip_v2_pr.tex'
    tex.write_text('\n'.join(L) + '\n')
    TB = os.path.expanduser('~/texlive/2026/bin/aarch64-linux')
    subprocess.run([f'{TB}/pdflatex', '-interaction=nonstopmode', tex.name], cwd=FIG, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['pdftoppm', '-r', '600', '-png', '-singlefile', 'fig_rc_chip_v2_pr.pdf', 'fig_rc_chip_v2_pr'], cwd=FIG, check=True)
    print(FIG / 'fig_rc_chip_v2_pr.pdf')
