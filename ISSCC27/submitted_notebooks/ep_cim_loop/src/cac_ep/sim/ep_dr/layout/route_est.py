"""가견적판 배치·연결 그림 (10/27, 사용자 "내가 옛날에 가견적으로 만들어두려고 한 게 있긴 해. 그것을 활용해봐"). route_v2.py 를 가견적 배치용으로 옮김 —
좌표는 모두 블록 사각형에서 계산. DRC·LVS 없음, 블록 수준 연결만 (v3 칩 덱 real_circuit/gen_chip_deck2.py 기준).
floorplan_est.json → route_est.json. Olympus 에서 route_gds.py 로 GDS·PNG (out/chip_est_pr.*) 를 만든 뒤 다시 python route_est.py 하면
TikZ 이름표를 얹어 ../../../deck/figs/real_circuit/fig_rc_chip_est.{tex,pdf,png}.
쓰임: python route_est.py
"""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIG = HERE.parents[2] / 'deck' / 'figs' / 'real_circuit'
F = json.load(open(HERE / 'floorplan_est.json'))
W, H = F['die']['w'], F['die']['h']
OX, OY = F['core']['offset_in_die']
CW, CH = F['core']['w'], F['core']['h']
BL = {b['name']: dict(kind=b['kind'], cell=b['cell'], mirror=b.get('mirror', False), rect=[OX + b['rect'][0], OY + b['rect'][1], OX + b['rect'][2], OY + b['rect'][3]])
      for b in F['blocks']}
X0 = lambda n: BL[n]['rect'][0]
Y0 = lambda n: BL[n]['rect'][1]
X1 = lambda n: BL[n]['rect'][2]
Y1 = lambda n: BL[n]['rect'][3]
XC = lambda n: (X0(n) + X1(n)) / 2
YC = lambda n: (Y0(n) + Y1(n)) / 2
RING = {r['net']: r['offset'] + r['width'] / 2 for r in F['core_rings']}
P2R = {'VDD': 'VDD', 'VSS': 'VSS', 'VCM': 'VCM', 'VDDL': 'VCCD', 'VSSL': 'VSS'}      # VSSD = VSS
WID = dict(ana=5.0, dig=5.0, bus=8.0, pwr=10.0)
NBUS = {'free bus': 4, 'nudge bus': 4, 'V_W': 2, 'ctl': 4, 'wu ctl': 4, 'D': 6, 'row select': 3, 'bias': 3, 'beta': 2, 'nudge inj': 3}   # 가닥 수 (금속 그림)
IN_EDGE = F['die']['margin'] + 197.965                             # 패드 core 쪽 가장자리 (die 가장자리에서)
R = []


def route(net, cls, *pts, w=None):
    R.append(dict(net=net, cls=cls, w=w or WID[cls], n=NBUS.get(net, 1), pts=[[round(x, 2), round(y, 2)] for x, y in pts]))


def pin(p):
    x0, y0, x1, y1 = p['rect']
    return dict(top=((x0 + x1) / 2, y0), bottom=((x0 + x1) / 2, y1), left=(x1, (y0 + y1) / 2), right=(x0, (y0 + y1) / 2))[p['side']]


def pads(name, side):
    return [q for q in F['pads'] if q['name'] == name and q['side'] == side]


def path(side, p, a, t, dep, d):
    """변 좌표 a → t, 통로 깊이 d (die 가장자리에서), 끝 = 블록 가장자리 dep (die 좌표). d 가 None 이면 곧게."""
    if d is None:
        return [p, (dep, a)] if side in ('left', 'right') else [p, (a, dep)]
    if side == 'left':
        return [p, (d, a), (d, t), (dep, t)]
    if side == 'right':
        return [p, (W - d, a), (W - d, t), (dep, t)]
    if side == 'bottom':
        return [p, (a, d), (t, d), (t, dep)]
    return [p, (a, H - d), (t, H - d), (t, dep)]


def river(side, nets, cls='dig'):
    """한 변의 패드 → 블록 가장자리. nets = [(이름, 목표 = 변 방향 좌표, 목표 깊이 = 블록 가장자리 die 좌표)].
    옆으로 비키는 선은 ring 띠 안 통로로: 같은 방향으로 비키는 선 중 진행 방향 앞쪽 패드가 바깥 통로, 뒤쪽 패드일수록 안쪽 (교차 없음)."""
    lo, hi = IN_EDGE + 6, (OX if side in ('left', 'right') else OY) - 6
    items = []
    for nm, t, dep in nets:
        p = pin(pads(nm, side)[0])
        items.append((nm, p[1] if side in ('left', 'right') else p[0], t, dep, p))
    for sgn in (+1, -1):
        mv = sorted((it for it in items if (it[2] - it[1]) * sgn > 0.5), key=lambda it: it[1] * sgn, reverse=True)
        for k, (nm, a, t, dep, p) in enumerate(mv):
            route(nm, cls, *path(side, p, a, t, dep, lo + (hi - lo) * (k + 0.5) / len(mv)))
    for nm, a, t, dep, p in items:
        if abs(t - a) <= 0.5:
            route(nm, cls, *path(side, p, a, a, dep, None))


# ── 전원 패드 → core 전원 ring
for p in F['pads']:
    if p['name'] in P2R:
        (x, y), d = pin(p), RING[P2R[p['name']]]
        route(p['name'], 'pwr', (x, y), dict(top=(x, H - d), bottom=(x, d), left=(d, y), right=(W - d, y))[p['side']])

# ── 위 변: VRAILP·VRAILM → 입력 구동 + 입력 구동 옆 틈으로 열 띠 (clamp 다이오드)
for blk, arr, sgn in (('input drive (free)', 'free', +1), ('input drive (nudge)', 'nudge', -1)):
    for nm in ('VRAILP', 'VRAILM'):
        q = min(pads(nm, 'top'), key=lambda q: abs(pin(q)[0] - XC(blk)))
        x, y = pin(q); route(nm, 'ana', (x, y), (x, Y1(blk)))
    gx = X1(blk) if sgn > 0 else X0(blk)
    cm = f'column MUX ({arr})'; ax = X0(cm) if sgn > 0 else X1(cm)
    route('VRAILP', 'ana', (gx, Y1(blk) - 12), (gx + sgn * 12, Y1(blk) - 12), (gx + sgn * 12, YC(cm) - 8), (ax, YC(cm) - 8), w=4)
    route('VRAILM', 'ana', (gx, Y1(blk) - 5), (gx + sgn * 19, Y1(blk) - 5), (gx + sgn * 19, YC(cm) + 8), (ax, YC(cm) + 8), w=4)

# ── 오른쪽 변: bias 패드 → bias 오른쪽 가장자리
yb = [Y0('bias') + 6 + k * 10 for k in range(3)]
river('right', [('IBIAS', yb[2], X1('bias')), ('VBNC', yb[1], X1('bias')), ('VBPC', yb[0], X1('bias'))], cls='ana')

# ── 아래 변: 쓰기 전압 → write buffer, VBUS ← 판독 TG, gpio 5 → 합성 디지털 (5 V 블록 아래)
xw = [XC('write buffer') + k * 24 for k in (1, 0, -1)]
river('bottom', [('VWH', xw[0], Y0('write buffer')), ('VWLO', xw[1], Y0('write buffer')), ('VWL', xw[2], Y0('write buffer'))], cls='ana')
for nm, tg in (('VBUS_F', 'readout TG (free)'), ('VBUS_N', 'readout TG (nudge)')):
    x, y = pin(pads(nm, 'bottom')[0]); route(nm, 'ana', (x, y), (x, Y0(tg)))
gd = 'global digital (5 V)'
xg = [X0(gd) + 16 + k * 20 for k in range(5)][::-1]                # LAT, CK3, CK, LQ2, LQ1 (오른 → 왼)
river('bottom', [(nm, xg[k], Y0(gd)) for k, nm in enumerate(['LAT', 'CK3', 'CK', 'LQ2', 'LQ1'])])

# ── 왼쪽 변: gpio 6 → 합성 디지털 왼쪽 가장자리
GDT = Y1('global digital (1.8 V)')
river('left', [(nm, Y0(gd) + 5 + k * (GDT - Y0(gd) - 10) / 5, X0(gd)) for k, nm in enumerate(['SCK', 'SDI', 'SLD', 'RST', 'SEL_EN', 'WP'])])

# ── core 안 (블록 수준 버스)
YB0, YB1 = max(Y1('WU1'), GDT), Y0('COL1/COL2 token (free)')       # 버스 통로
C_DIG, C_FREE, C_NUD, C_CLK, C_BIAS = (YB1 - 8 - 10 * k for k in range(5))
A0, A1 = Y0('free crossbar'), Y1('free crossbar')
XS = XC('ROW1/ROW2 token')
YSP = min(Y0('ROW1/ROW2 token'), Y0('row decoder (shared)'), Y0('DATA + latch + gate')) - 12
GX, GX2 = X1('global digital (1.8 V)') - 12, X1('global digital (1.8 V)') - 30
# 합성 디지털 → 레지스터·decoder (SDI, 레지스터 클록, 동작 신호, SEL_EN)
route('ctl', 'dig', (GX, GDT), (GX, C_DIG), (XC('COL1/COL2 token (nudge)'), C_DIG), (XC('COL1/COL2 token (nudge)'), Y0('COL1/COL2 token (nudge)')))
route('ctl', 'dig', (XC('COL1/COL2 token (free)'), C_DIG), (XC('COL1/COL2 token (free)'), Y0('COL1/COL2 token (free)')))
route('ctl', 'dig', (XS, C_DIG), (XS, YSP), (XC('DATA + latch + gate'), YSP), (XC('DATA + latch + gate'), Y0('DATA + latch + gate')))
route('ctl', 'dig', (XS, YSP), (XS, Y0('ROW1/ROW2 token')))
route('ctl', 'dig', (XC('row decoder (shared)'), YSP), (XC('row decoder (shared)'), Y0('row decoder (shared)')))
# 합성 디지털 ↔ WU1·WU2·write buffer (CK, CK3, LAT/LATB, LQ, WP, POL)
route('wu ctl', 'dig', (GX2, GDT), (GX2, C_CLK), (X1('WU2') - 15, C_CLK), (X1('WU2') - 15, Y1('WU2')))
route('wu ctl', 'dig', (X0('WU1') + 15, C_CLK), (X0('WU1') + 15, Y1('WU1')))
route('wu ctl', 'dig', (X1('write buffer') - 10, C_CLK), (X1('write buffer') - 10, Y1('write buffer')))
# free / nudge 버스: row MUX (R1, R2) + 열 MUX (C1, C2) → WU1 (R1, C1) · WU2 (R2, C2), R2 → 판독 TG
for p, xt, cy, d1, d2, tg in (('free', X0('row MUX + WL (free)') + 8, C_FREE, X0('WU1') + 35, X0('WU2') + 20, 'readout TG (free)'),
                              ('nudge', X1('row MUX + WL (nudge)') - 8, C_NUD, X0('WU1') + 60, X0('WU2') + 45, 'readout TG (nudge)')):
    cm = f'column MUX ({p})'
    route(f'{p} bus', 'bus', (xt, Y0(f'row MUX + WL ({p})')), (xt, cy))
    route(f'{p} bus', 'bus', (X1(cm) if p == 'free' else X0(cm), YC(cm)), (xt, YC(cm)))
    route(f'{p} bus', 'bus', (d1, Y1('WU1')), (d1, cy), (d2, cy), (d2, Y1('WU2')))
    route(f'{p} bus', 'bus', (xt, YC(tg)), (X0(tg) if p == 'free' else X1(tg), YC(tg)))
# write buffer → V_W (+ V_WL) 버스 → row MUX·열 MUX (두 배열)
YVW = Y0('row MUX + WL (free)') - 12
route('V_W', 'ana', (XC('write buffer'), Y1('write buffer')), (XC('write buffer'), YVW))
route('V_W', 'ana', (X0('row MUX + WL (free)') + 25, Y0('row MUX + WL (free)')), (X0('row MUX + WL (free)') + 25, YVW),
      (X1('row MUX + WL (nudge)') - 25, YVW), (X1('row MUX + WL (nudge)') - 25, Y0('row MUX + WL (nudge)')))
route('V_W', 'ana', (X1('column MUX (free)'), YC('column MUX (free)') + 14), (X0('column MUX (nudge)'), YC('column MUX (nudge)') + 14))
# 행 decoder → row MUX + WL (행 pitch 로 token·DATA 위를 지남)
YRS = [Y0('row decoder (shared)') + f * (A1 - Y0('row decoder (shared)')) for f in (0.3, 0.75)]
for yy in YRS:
    route('row select', 'dig', (X0('row decoder (shared)'), yy), (X1('row MUX + WL (free)'), yy))
    route('row select', 'dig', (X1('row decoder (shared)'), yy), (X0('row MUX + WL (nudge)'), yy))
# DATA → 입력 구동 (두 배열), 배열 위 통로
YD = A1 + 7.5
xdf, xdn = X1('input drive (free)') - 60, X0('input drive (nudge)') + 60
route('D', 'dig', (xdf, Y1('input drive (free)')), (xdf, YD), (xdn, YD), (xdn, Y1('input drive (nudge)')))
route('D', 'dig', (XC('DATA + latch + gate'), Y1('DATA + latch + gate')), (XC('DATA + latch + gate'), YD))
# bias → WU1·WU2 (vbn, vbp, VBNC, VBPC), β 미러 → nudge 주입기 → nudge 출력 행 (행 22–27 근처)
route('bias', 'ana', (X0('bias') + 8, Y1('bias')), (X0('bias') + 8, C_BIAS), (X1('WU1') - 12, C_BIAS), (X1('WU1') - 12, Y1('WU1')))
route('bias', 'ana', (X1('WU2') - 30, C_BIAS), (X1('WU2') - 30, Y1('WU2')))
XBM = X0('bias') + 24
route('beta', 'ana', (XBM, Y1('bias')), (XBM, Y0('nudge injector')))
yo = A0 + 25 * (A1 - A0) / 128
xi = X0('input drive (nudge)') - 6
route('nudge inj', 'ana', (X0('nudge injector') + 10, Y1('nudge injector')), (X0('nudge injector') + 10, Y1('nudge injector') + 7),
      (xi, Y1('nudge injector') + 7), (xi, yo), (X1('nudge crossbar'), yo), w=4)

LABEL = dict(
    blocks={'free crossbar': 'Free 1T1R crossbar\\\\128 $\\times$ 64', 'nudge crossbar': 'Nudge 1T1R crossbar\\\\128 $\\times$ 64',
            'input drive (free)': 'Input drive (READ)\\\\NMOS 2:1, W 1,000 $\\times$ 198', 'input drive (nudge)': 'Input drive (READ)\\\\NMOS 2:1, W 1,000 $\\times$ 198',
            'column MUX (free)': 'Column MUX + diodes', 'column MUX (nudge)': 'Column MUX + diodes',
            'COL1/COL2 token (free)': 'Column decoder +\\\\COL1/COL2 shift reg.', 'COL1/COL2 token (nudge)': 'Column decoder +\\\\COL1/COL2 shift reg.',
            'WU1': 'WU1', 'WU2': 'WU2', 'write buffer': 'Write buf.', 'bias': 'Bias'},
    beside={'global digital (5 V)': 'Clock buffers + level shifters (5 V)', 'global digital (1.8 V)': 'Config reg. + mode decoder (1.8 V)',
            'nudge injector': 'Nudge injector'},
    rot={'row MUX + WL (free)': 'Row MUX + WL', 'row MUX + WL (nudge)': 'Row MUX + WL', 'ROW1/ROW2 token': 'ROW1/ROW2 shift reg.',
         'row decoder (shared)': 'Row decoder', 'DATA + latch + gate': 'DATA reg. + latch'},
    callouts=[
        (1, 'Free bus: R1, C1 $\\rightarrow$ WU1; R2, C2 $\\rightarrow$ WU2', (X0('row MUX + WL (free)') + 8, (YVW + C_FREE) / 2 + 20)),
        (2, 'Nudge bus: R1, C1 $\\rightarrow$ WU1; R2, C2 $\\rightarrow$ WU2', (X1('row MUX + WL (nudge)') - 8, (YVW + C_NUD) / 2 + 20)),
        (3, 'V$_\\mathrm{W}$, V$_\\mathrm{WL}$: write buffer $\\rightarrow$ row / column MUX', (XC('write buffer'), (YVW + C_DIG) / 2)),
        (4, 'SDI, register clocks (SCK$\\cdot$TSEL), mode, SEL\\_EN', (XS, (YSP + C_DIG) / 2 + 25)),
        (5, 'CK, CK3, LAT, LQ1/2, WP, POL', (X0('WU1') - 60, C_CLK)),
        (6, 'vbn, vbp: bias $\\rightarrow$ WU1, WU2', (X0('bias') - 60, C_BIAS)),
        (7, '$\\beta$ mirror: bias $\\rightarrow$ nudge injector', (XBM, (Y1('bias') + Y0('nudge injector')) / 2)),
        (8, 'D: DATA latch $\\rightarrow$ input drive gates', (X0('free crossbar') + 60, YD)),
        (9, 'Row select: row decoder $\\rightarrow$ row MUX + WL', (X1('DATA + latch + gate') + 5, YRS[1])),
        (10, 'Readout TG: R2 bus $\\rightarrow$ VBUS pad', (XC('readout TG (free)') + 16, YC('readout TG (free)'))),
        (10, '', (XC('readout TG (nudge)') - 16, YC('readout TG (nudge)'))),
        (11, 'Nudge current $\\rightarrow$ nudge output rows', (xi, (Y1('nudge injector') + yo) / 2)),
        (12, 'VRAILP / VRAILM $\\rightarrow$ clamp diodes', (X1('input drive (free)') + 15, (A0 + A1) / 2)),
        (12, '', (X0('input drive (nudge)') - 15, (A0 + A1) / 2))])
json.dump(dict(note='가견적판 배치·연결 (DRC·LVS 없음). 좌표 µm, die 좌표.', die=dict(w=W, h=H), core=[OX, OY, OX + CW, OY + CH],
               blocks=BL, routes=R, labels=LABEL), open(HERE / 'route_est.json', 'w'), indent=1, ensure_ascii=False)
print('blocks', len(BL), 'routes', len(R))

# ── TikZ (Olympus 의 KLayout 그림이 있을 때)
PNG = HERE / 'out' / 'chip_est_pr.png'
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
  bl/.style={font=\fontsize{5.2}{6}\selectfont\bfseries, align=center, text=black, fill=white, fill opacity=0.8, text opacity=1, inner sep=0.8pt, rounded corners=0.5pt},
  pl/.style={font=\fontsize{4.4}{5}\selectfont\bfseries, fill=white, fill opacity=0.85, text opacity=1, inner sep=0.6pt, rounded corners=0.5pt},
  bu/.style={font=\fontsize{4.4}{5}\selectfont, fill=white, fill opacity=0.85, text opacity=1, inner sep=0.8pt},
  co/.style={circle, draw=black, line width=0.3pt, fill=white, inner sep=0.3pt, minimum size=0.22cm, font=\fontsize{4.4}{5}\selectfont\bfseries}]
""", f"\\node[anchor=south west, inner sep=0] at (0,0) {{\\includegraphics[width={WCM}cm]{{{PNG}}}}};"]
    for n, t in LABEL['blocks'].items():
        L.append(f"\\node[bl] at {P(XC(n), YC(n))} {{{t}}};")
    for n, t in LABEL['rot'].items():
        L.append(f"\\node[bl, rotate=90] at {P(XC(n), YC(n))} {{{t}}};")
    for n, t in LABEL['beside'].items():                           # 작은 블록: 이름표를 오른쪽 옆에
        L.append(f"\\node[bl, anchor=west] at {P(X1(n) + 6, YC(n))} {{{t}}};")
    for p in F['pads']:
        x0, y0, x1, y1 = p['rect']
        nm = 'spare' if p['name'].startswith('SPARE') else p['name'].replace('_', '\\_')
        L.append(f"\\node[pl, rotate={90 if p['side'] in ('top', 'bottom') else 0}] at {P((x0 + x1) / 2, (y0 + y1) / 2)} {{{nm}}};")
    for k, t, (x, y) in LABEL['callouts']:
        L.append(f"\\node[co] at {P(x, y)} {{{k}}};")
    for k, (net, d) in enumerate(RING.items()):
        L.append(f"\\node[bu] at {P(X0('free crossbar') + 70 * k, H - d)} {{{net}}};")
    yl = -0.35
    L.append(f"\\node[anchor=west, font=\\fontsize{{6}}{{7}}\\selectfont] at (0.2,{yl:.2f}) "
             "{Block-level wiring: met3 (horizontal) and met4 (vertical), buses drawn as parallel lines; power straps: met5.};")
    seen = sorted({(k, t) for k, t, _ in LABEL['callouts'] if t})
    for j, (k, t) in enumerate(seen):
        cx, cy = 0.35 + 5.7 * (j // 4), yl - 0.38 - 0.27 * (j % 4)
        L.append(f"\\node[co] at ({cx:.2f},{cy:.2f}) {{{k}}}; \\node[anchor=west, font=\\fontsize{{5.5}}{{6.5}}\\selectfont] at ({cx + 0.18:.2f},{cy:.2f}) {{{t}}};")
    L += ['\\end{tikzpicture}', '\\end{document}']
    tex = FIG / 'fig_rc_chip_est.tex'
    tex.write_text('\n'.join(L) + '\n')
    TB = os.path.expanduser('~/texlive/2026/bin/aarch64-linux')
    subprocess.run([f'{TB}/pdflatex', '-interaction=nonstopmode', tex.name], cwd=FIG, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['pdftoppm', '-r', '600', '-png', '-singlefile', 'fig_rc_chip_est.pdf', 'fig_rc_chip_est'], cwd=FIG, check=True)
    for ext in ('aux', 'log'):
        (FIG / f'fig_rc_chip_est.{ext}').unlink(missing_ok=True)
    print(FIG / 'fig_rc_chip_est.pdf')
