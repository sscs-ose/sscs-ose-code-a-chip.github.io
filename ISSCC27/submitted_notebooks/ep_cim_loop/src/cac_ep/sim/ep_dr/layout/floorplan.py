"""CaC core floorplan + PAD frame (v1, 10/26). v0 (5 × 5 mm, 자리표시 패드) 는 floorplan_v0.json·그림 fig_rc_floorplan / fig_rc_padframe.
v1 에서 바꾼 것 (사용자 10/26 "PAD Frame에는 SKY130에서 제공해주었던 것처럼 powerrail과 ESD등을 참고해서 … 직사각형 모양으로 pad frame을
결정할까? 그리고 core도 빈공간 없이 WU 회로 등을 배치 … 2.5mm by 2.5mm로"):
  - 패드 = 실제 SKY130 IO 셀 (sky130_ef_io, volare c6d73a35): 디지털 gpiov2_pad (80 µm, ESD·레벨 변환), 아날로그 analog_esd_pad (75 µm,
    VDDA·VSSA 로 ESD), 전원 *_hvc/lvc_clamped_pad (75 µm, clamp), 모서리 corner_pad (200 × 204 µm), 사이 = com_bus_slice (rail 12 개 이음).
    크기는 LEF 값. IO ring rail: VSSA = VSSIO = VSSD = VSS (−2.5 V, 기판), VDDA = VDDIO = VDD (+2.5 V), VCCD = VSS + 1.8 V (합성 디지털),
    VCCHIB = VCCD, VSWITCH = VDDIO (connect slice 하나). VCM (0 V) 은 아날로그 패드 4 개로.
  - die = 직사각형 2.5 × 1.9 mm (core + IO ring + core 전원 ring 이 들어가는 최소 ≈ 2.45 × 1.81 mm 에 여유). DIE_W·DIE_H 만 바꾸면 2.5 × 2.5.
  - core: 행 pitch·열 pitch 는 그대로 가정 (4.5 / 5.1 µm), 블록 사이 15 µm·버스 통로 30 / 90 µm 로 넓힘 (BEOL 배선 자리),
    입력 구동 띠 아래 빈 모서리에 합성 디지털·bias·nudge 주입기·decap 을 넣어 빈 곳 없앰.
낸다: floorplan.json (블록·패드·filler·모서리·core ring), ../../../deck/figs/real_circuit/fig_rc_floorplan_v1.tex, fig_rc_padframe_v1.tex.
padframe_gds.py 가 floorplan.json 으로 GDS 를 만든다 (Olympus KLayout).
쓰임: python floorplan.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIG = HERE.parents[2] / 'deck' / 'figs' / 'real_circuit'

# ── core (µm, 어림: pitch 는 가정)
P_R, P_C, NR, NC = 4.5, 5.1, 128, 64
N_IN_ROWS, N_OUT_ROWS, N_HID = 100, 6, 60
ARR_W, ARR_H = NC * P_C, NR * P_R
W_INSW, W_ROWM, W_CH, W_SUB = 400.0, 40.0, 30.0, 40.0
G = 15.0
H_DIO, H_COLM, H_COLL, H_COLR = 30.0, 55.0, 50.0, 55.0
H_BOT, H_BUS = 200.0, 90.0

x, X = 0.0, {}
for k, w, gap in (('insw_f', W_INSW, 0), ('arr_f', ARR_W, G), ('rowm_f', W_ROWM, G), ('ch_f', W_CH, 0), ('spine', 3 * W_SUB + 10, 0),
                  ('ch_n', W_CH, 0), ('rowm_n', W_ROWM, 0), ('arr_n', ARR_W, G), ('insw_n', W_INSW, G)):
    x += gap; X[k] = (x, x + w); x += w
CORE_W = x
XC = CORE_W / 2
Y = {'bot': (0.0, H_BOT), 'bus': (H_BOT, H_BOT + H_BUS)}
y = H_BOT + H_BUS
for k, h, gap in (('colr', H_COLR, 0), ('coll', H_COLL, 5), ('colm', H_COLM, 5), ('dio_b', H_DIO, G), ('arr', ARR_H, G), ('dio_t', H_DIO, G)):
    y += gap; Y[k] = (y, y + h); y += h
CORE_H = y
A0, A1 = Y['arr']
Y['in_rows'] = (A1 - N_IN_ROWS * P_R, A1)
Y['out_rows'] = (Y['in_rows'][0] - N_OUT_ROWS * P_R, Y['in_rows'][0])
Y['spare_rows'] = (A0, Y['out_rows'][0])

B = []


def blk(name, kind, x0, y0, x1, y1, label='', note=''):
    B.append(dict(name=name, kind=kind, rect=[round(v, 2) for v in (x0, y0, x1, y1)], label=label, note=note))


for p, side in (('f', 'free'), ('n', 'nudge')):
    ax0, ax1 = X[f'arr_{p}']
    blk(f'{side} crossbar', 'array', ax0, A0, ax1, A1)
    blk(f'clamp diode up ({side})', 'diode', ax0, Y['dio_t'][0], ax1, Y['dio_t'][1], 'clamp diode $\\uparrow$ $\\times$60')
    blk(f'clamp diode down ({side})', 'diode', ax0, Y['dio_b'][0], ax1, Y['dio_b'][1], 'clamp diode $\\downarrow$ $\\times$60')
    blk(f'column MUX ({side})', 'pitch_col', ax0, Y['colm'][0], ax1, Y['colm'][1], 'column MUX $\\times$64')
    blk(f'column decoder ({side})', 'pitch_col', ax0, Y['coll'][0], ax1, Y['coll'][1], 'column decoder $\\times$64')
    blk(f'COL1/COL2 token ({side})', 'pitch_col', ax0, Y['colr'][0], ax1, Y['colr'][1], 'COL1 / COL2 token $\\times$60', '배열마다 한 벌, 같은 SDI·클록')
    blk(f'row MUX + WL ({side})', 'pitch_row', X[f'rowm_{p}'][0], Y['out_rows'][0], X[f'rowm_{p}'][1], A1, 'row MUX + WL driver $\\times$106')
    blk(f'input drive ({side})', 'pitch_row', X[f'insw_{p}'][0], Y['in_rows'][0], X[f'insw_{p}'][1], A1,
        '\\textbf{input drive (READ)}\\\\NMOS 2:1 per row, $\\times$100\\\\W 1,000 \\textmu m $\\times$ 2 per row', 'W 1,000 µm × 2 / 행')
s0 = X['spine'][0]
blk('ROW1/ROW2 token', 'pitch_row', s0, Y['out_rows'][0], s0 + W_SUB, A1, 'ROW1 / ROW2 token $\\times$106')
blk('row decoder (shared)', 'pitch_row', s0 + W_SUB + 5, Y['out_rows'][0], s0 + 2 * W_SUB + 5, A1, 'row decoder $\\times$106')
blk('DATA + latch + gate', 'pitch_row', s0 + 2 * W_SUB + 10, Y['in_rows'][0], s0 + 3 * W_SUB + 10, A1, 'DATA + latch + gate $\\times$49')
# 맨 아래 줄 (가운데 = 두 배열 버스가 모이는 곳) + 입력 구동 띠 아래 모서리
blk('WU1', 'analog', XC - 470, 0, XC - 130, H_BOT, '\\textbf{WU1}\\\\first stage')
blk('write buffer', 'analog', XC - 115, 0, XC + 115, H_BOT, 'write buffer\\\\(V\\_W bus)')
blk('WU2', 'analog', XC + 130, 0, XC + 470, H_BOT, '\\textbf{WU2}\\\\last stage')
fx0, fx1 = X['insw_f']; nx0, nx1 = X['insw_n']
corner_top = Y['in_rows'][0] - G
blk('global digital', 'digital', fx0, 0, fx1, 300, '\\textbf{global digital}\\\\(synthesized, 1.8 V)\\\\mode decoder, clock buffers,\\\\level shifters')
blk('decap (left)', 'decap', fx0, 300 + G, fx1, corner_top, 'decap\\\\(VDD--VSS, VCM)')
blk('bias', 'analog', nx0, 0, nx1, H_BOT, '\\textbf{bias}\\\\$\\beta$ reference, HOG bias')
blk('nudge injector', 'analog', nx0, Y['out_rows'][1] - 140, nx0 + 200, Y['out_rows'][1], 'nudge\\\\injector $\\times$3')
blk('decap (right, lower)', 'decap', nx0, H_BOT + G, nx1, Y['out_rows'][1] - 140 - G, 'decap')
blk('decap (right, upper)', 'decap', nx0 + 200 + G, Y['out_rows'][1] - 140, nx1, corner_top, 'decap')

# ── die + IO ring (실제 SKY130 IO 셀, LEF 크기)
DIE_W, DIE_H, M = 2500.0, 1900.0, 30.0                          # M = die 가장자리 ~ IO 셀 바깥 (seal ring 자리)
CELL = {  # 이름 → (폭, 원점에서 바깥 (패드 쪽) 가장자리까지)
    'gpio': ('sky130_ef_io__gpiov2_pad', 80.0, 197.965), 'analog': ('sky130_ef_io__analog_esd_pad', 75.0, 200.0),
    'vdda': ('sky130_ef_io__vdda_hvc_clamped_pad', 75.0, 197.965), 'vssa': ('sky130_ef_io__vssa_hvc_clamped_pad', 75.0, 197.965),
    'vddio': ('sky130_ef_io__vddio_hvc_clamped_pad', 75.0, 197.965), 'vssio': ('sky130_ef_io__vssio_hvc_clamped_pad', 75.0, 197.965),
    'vccd': ('sky130_ef_io__vccd_lvc_clamped_pad', 75.0, 197.965), 'vssd': ('sky130_ef_io__vssd_lvc_clamped_pad', 75.0, 197.965),
    'connect': ('sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um', 20.0, 197.965)}
SLICE = {w: f'sky130_ef_io__com_bus_slice_{w}um' for w in (20, 10, 5, 1)}
CORNER = 'sky130_ef_io__corner_pad'                              # 200 × 204 (R0 = 오른쪽 위)
# 패드 (이름, IO 셀). 변마다 놓는 순서: 위 = 왼→오, 오른 = 위→아래, 아래 = 오른→왼, 왼 = 아래→위
G_, A_ = 'gpio', 'analog'
P_SIDES = {
    'top': [('VDD', 'vdda'), ('VSS', 'vssa'), ('VCM', A_), ('RAIP', A_), ('RAIM', A_), ('VRUP', A_), ('VRDN', A_), ('DATA_D', G_), ('DATA_CLK', G_),
            ('DATA_LD', G_), ('ROW1_D', G_), ('ROW1_CLK', G_), ('ROW2_D', G_), ('ROW2_CLK', G_), ('SEL_EN', G_), ('RST', G_), ('SPARE1', A_), ('SPARE2', A_)],
    'right': [('VDD', 'vddio'), ('VSS', 'vssio'), ('VCM', A_), ('IREF_P', A_), ('IREF_N', A_), ('VBUS_N', A_), ('PV', G_), ('POL', G_), ('WP', G_),
              ('WU_EN', G_), ('VWH', A_), ('VWLO', A_), ('SPARE3', A_)],
    'bottom': [('VDD', 'vdda'), ('VSS', 'vssa'), ('VCM', A_), ('IBN', A_), ('IBP', A_), ('VBNC', A_), ('VBPC', A_), ('LQ2', G_), ('LQ1', G_),
               ('LATB', G_), ('LAT', G_), ('CK3', G_), ('CK', G_), ('M1', G_), ('M0', G_), ('VDDL', 'vccd'), ('VSSL', 'vssd'), ('SPARE4', A_)],
    'left': [('VDD', 'vddio'), ('VSS', 'vssio'), ('VCM', A_), ('VDDL', 'vccd'), ('VSSL', 'vssd'), ('VBUS_F', A_), ('VWL', A_), ('COL1_D', G_),
             ('COL1_CLK', G_), ('COL2_D', G_), ('COL2_CLK', G_), ('SPARE5', A_)]}
ptype = lambda n, c: 'spare' if n.startswith('SPARE') else 'power' if c not in (G_, A_) or n == 'VCM' else 'digital' if c == G_ else 'analog'
# 변마다 시작·끝 (모서리 셀 크기: 위 오른쪽 R0 200 × 204, 왼쪽 위 R90 204 × 200, 왼쪽 아래 R180 200 × 204, 오른쪽 아래 R270 204 × 200)
SPAN = {'top': (M + 204, DIE_W - M - 200), 'bottom': (DIE_W - M - 204, M + 200), 'right': (DIE_H - M - 204, M + 200), 'left': (M + 204, DIE_H - M - 200)}
ROT = {'top': 0, 'left': 1, 'bottom': 2, 'right': 3}            # KLayout Trans 회전 (90° 단위)


def place(side, s, cell, w, h):
    """변 위치 s (변 시작에서 놓는 방향으로 잰 앞 끝) → 원점 (ox, oy), 회전, die 좌표 사각형."""
    if side == 'top':
        x0 = s; return (x0, DIE_H - M - h), [x0, DIE_H - M - h, x0 + w, DIE_H - M]
    if side == 'bottom':                                          # 오른→왼, R180
        x1 = s; return (x1, M + h), [x1 - w, M, x1, M + h]
    if side == 'left':                                            # 아래→위, R90
        y0 = s; return (M + h, y0), [M, y0, M + h, y0 + w]
    y1 = s; return (DIE_W - M - h, y1), [DIE_W - M - h, y1 - w, DIE_W - M, y1]   # right: 위→아래, R270


PADS, FILL, n_conn = [], [], 0
for side, items in P_SIDES.items():
    a, b = SPAN[side]; L = abs(b - a); d = 1 if b > a else -1
    widths = [CELL[c][1] for _, c in items]
    conn = side == 'bottom'                                       # VCCHIB=VCCD, VSWITCH=VDDIO 이음 slice 하나 (아래 변)
    free = L - sum(widths) - (CELL['connect'][1] if conn else 0)
    n = len(items) + 1
    gaps = [int(free // n)] * n
    for i in range(int(round(free - sum(gaps)))):
        gaps[i % n] += 1
    s = a
    for i in range(n):
        g = gaps[i]
        if conn and i == n // 2:                                  # 이음 slice 를 가운데 틈에
            o, r = place(side, s, *CELL['connect'][:1], CELL['connect'][1], CELL['connect'][2]); FILL.append(dict(cell=CELL['connect'][0], side=side, origin=o, rot=ROT[side], rect=r))
            s += d * CELL['connect'][1]; n_conn += 1
        for w in (20, 10, 5, 1):                                  # 틈을 com_bus_slice 로 채움 (rail 이음)
            while g >= w:
                o, r = place(side, s, SLICE[w], w, 197.965); FILL.append(dict(cell=SLICE[w], side=side, origin=o, rot=ROT[side], rect=r))
                s += d * w; g -= w
        if i < len(items):
            nm, c = items[i]; cn, w, h = CELL[c]
            o, r = place(side, s, cn, w, h)
            PADS.append(dict(name=nm, type=ptype(nm, c), io=c, cell=cn, side=side, origin=[round(v, 3) for v in o], rot=ROT[side], rect=[round(v, 3) for v in r]))
            s += d * w
    assert abs(s - b) < 1e-6, (side, s, b)
CORNERS = [dict(cell=CORNER, at='TR', rot=0, origin=[DIE_W - M - 200, DIE_H - M - 204]), dict(cell=CORNER, at='TL', rot=1, origin=[M + 204, DIE_H - M - 200]),
           dict(cell=CORNER, at='BL', rot=2, origin=[M + 200, M + 204]), dict(cell=CORNER, at='BR', rot=3, origin=[DIE_W - M - 204, M + 200])]
n_by = {t: sum(p['type'] == t for p in PADS) for t in ('digital', 'analog', 'power', 'spare')}
assert len(PADS) == 61 and n_by == dict(digital=25, analog=15, power=16, spare=5), n_by
# core 전원 ring (IO ring 안쪽): 바깥부터 VSS, VDD, VCM, VCCD — 각 15 µm, 사이 5 µm (met4·met5 겹침)
RING_IN = M + 204 + 10
RINGS = [dict(net=n, offset=round(RING_IN + k * 20, 2), width=15.0) for k, n in enumerate(('VSS', 'VDD', 'VCM', 'VCCD'))]
RING_OUT = RING_IN + 4 * 20
CORE_OFF = ((DIE_W - CORE_W) / 2, (DIE_H - CORE_H) / 2)
assert min(CORE_OFF) >= RING_OUT + 10, ('core 가 전원 ring 과 겹침', CORE_OFF, RING_OUT)
fill_ratio = {sd: round(sum(CELL[c][1] for _, c in it) / abs(SPAN[sd][1] - SPAN[sd][0]), 3) for sd, it in P_SIDES.items()}

json.dump(dict(version='v1 (10/26)', note='어림 (가정): 행 pitch 4.5 µm, 열 pitch 5.1 µm, 블록 크기 어림. 좌표 µm. core 원점 = core 왼쪽 아래, 패드·filler 는 die 좌표.',
               iolib='sky130_ef_io / sky130_fd_io (volare sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b), 크기 = LEF',
               rails=dict(VSSA='VSS', VSSIO='VSS', VSSD='VSS', VDDA='VDD', VDDIO='VDD', VCCD='VSS+1.8V', VCCHIB='VCCD', VSWITCH='VDDIO'),
               pitch=dict(row=P_R, col=P_C), core=dict(w=round(CORE_W, 2), h=round(CORE_H, 2), offset_in_die=[round(v, 2) for v in CORE_OFF]),
               die=dict(w=DIE_W, h=DIE_H, margin=M), corners=CORNERS, pads=PADS, fillers=FILL, core_rings=RINGS, blocks=B,
               pad_count=n_by, side_fill=fill_ratio), open(HERE / 'floorplan.json', 'w'), indent=1, ensure_ascii=False)

# ── TikZ
PRE = r"""\documentclass[border=8pt,12pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[helvet]{sfmath}
\usepackage{tikz}
\usetikzlibrary{calc,arrows.meta}
\definecolor{maroon}{HTML}{500000}
\definecolor{navy}{HTML}{001C54}
\definecolor{grayd}{HTML}{404040}
\definecolor{bluel}{HTML}{DBE5F1}
\definecolor{redl}{HTML}{EFD5D5}
\definecolor{tilec}{HTML}{E6E9EF}
\definecolor{anac}{HTML}{E4DDF0}
\definecolor{digc}{HTML}{D5DCEA}
\definecolor{dioc}{HTML}{F2F2F2}
\definecolor{decc}{HTML}{EEF2E6}
\definecolor{purp}{HTML}{4B3B7A}
\definecolor{padc}{HTML}{D9C27A}
\begin{document}
\begin{tikzpicture}[x=1cm,y=1cm,line cap=round]
"""
FILLC = dict(array='white', diode='dioc', pitch_row='tilec', pitch_col='tilec', analog='anac', digital='digc', decap='decc')
fmt = lambda v: f'{v:.3f}'


def core_tex(S, ox=0.0, oy=0.0, detail=True):
    L = []
    P = lambda xx, yy: f'({fmt(ox + xx * S)},{fmt(oy + yy * S)})'
    for b in B:
        x0, y0, x1, y1 = b['rect']
        L.append(f"\\draw[fill={FILLC[b['kind']]}, draw=grayd, line width=0.5pt] {P(x0, y0)} rectangle {P(x1, y1)};")
        if b['kind'] == 'array':
            free = 'free' in b['name']
            hx0, hx1 = (x0, x0 + N_HID * P_C) if free else (x1 - N_HID * P_C, x1)
            L.append(f"\\fill[bluel] {P(hx0, Y['in_rows'][0])} rectangle {P(hx1, Y['in_rows'][1])};")
            L.append(f"\\fill[redl] {P(hx0, Y['out_rows'][0])} rectangle {P(hx1, Y['out_rows'][1])};")
            if detail:
                for k in range(1, 16):
                    yy = y0 + k * (y1 - y0) / 16; L.append(f"\\draw[gray!55, line width=0.25pt] {P(x0, yy)} -- {P(x1, yy)};")
                for k in range(1, 8):
                    xx = x0 + k * (x1 - x0) / 8; L.append(f"\\draw[gray!55, line width=0.25pt] {P(xx, y0)} -- {P(xx, y1)};")
            L.append(f"\\draw[draw=grayd, line width=0.6pt] {P(x0, y0)} rectangle {P(x1, y1)};")
        elif detail and b['kind'] == 'pitch_row':
            yy = y1 - 10 * P_R
            while yy > y0 + 1e-6:
                L.append(f"\\draw[gray!70, line width=0.2pt] {P(x0, yy)} -- {P(x1, yy)};"); yy -= 10 * P_R
        elif detail and b['kind'] == 'pitch_col':
            xx = x0 + 8 * P_C
            while xx < x1 - 1e-6:
                L.append(f"\\draw[gray!70, line width=0.2pt] {P(xx, y0)} -- {P(xx, y1)};"); xx += 8 * P_C
    return L


# 그림 1: core (1 cm = 100 µm)
S = 0.01
L = [PRE, '% 생성: sim/ep_dr/layout/floorplan.py v1 (손으로 고치지 말 것). 크기는 어림 (가정).'] + core_tex(S)
lab = lambda xx, yy, t, rot=0, fs='\\scriptsize', col='black', w=None: (
    f"\\node[font={fs}, text={col}, align=center{', rotate=' + str(rot) if rot else ''}{', text width=' + fmt(w) + 'cm' if w else ''}] "
    f"at ({fmt(xx * S)},{fmt(yy * S)}) {{{t}}};")
for p, side in (('f', 'free'), ('n', 'nudge')):
    cx = sum(X[f'arr_{p}']) / 2
    L.append(lab(cx, sum(Y['in_rows']) / 2 + 30, f'\\textbf{{{side} crossbar}}\\\\128 $\\times$ 64, 1T1R', fs='\\small'))
    L.append(lab(cx, sum(Y['in_rows']) / 2 - 60, 'first-stage cells', col='navy'))
    L.append(lab(cx, sum(Y['out_rows']) / 2, 'last-stage cells', fs='\\tiny', col='maroon'))
    L.append(lab(cx, sum(Y['spare_rows']) / 2, 'unused rows (22)', col='gray'))
for b in B:
    x0, y0, x1, y1 = b['rect']
    if not b['label']:
        continue
    if b['kind'] == 'pitch_row' and 'input' not in b['name']:
        L.append(lab((x0 + x1) / 2, (y0 + y1) / 2, b['label'], rot=90))
    else:
        wide = b['kind'] in ('pitch_col', 'diode')                 # 가로로 긴 띠는 줄바꿈 없이
        L.append(lab((x0 + x1) / 2, (y0 + y1) / 2, b['label'], fs='\\footnotesize' if 'input' in b['name'] else '\\scriptsize', w=None if wide else (x1 - x0) * S * 0.95))
L.append(lab(XC, A1 + 40, 'shared row spine', col='grayd'))
# 버스 (통로 y = H_BOT … H_BOT + H_BUS): R1·C1 → WU1 (navy), R2·C2 → WU2 (maroon). 각 WU 는 두 배열의 버스를 받는다
yl = {k: H_BOT + v for k, v in dict(C1n=15, R1n=32, R2f=50, C2f=68).items()}
xr = dict(R1f=sum(X['ch_f']) / 2 - 6, R2f=sum(X['ch_f']) / 2 + 6, R1n=sum(X['ch_n']) / 2 - 6, R2n=sum(X['ch_n']) / 2 + 6)
w1x0, w1x1, w2x0, w2x1 = XC - 470, XC - 130, XC + 130, XC + 470
seg = lambda col, pts: L.append(f"\\draw[{col}, line width=0.9pt] " + ' -- '.join(f'({fmt(a * S)},{fmt(b * S)})' for a, b in pts) + ';')
seg('navy', [(xr['R1f'], A1 - 5), (xr['R1f'], yl['R1n'] + 8), (w1x1 - 25, yl['R1n'] + 8), (w1x1 - 25, H_BOT)])
seg('navy', [(xr['R1n'], A1 - 5), (xr['R1n'], yl['R1n']), (w1x1 - 45, yl['R1n']), (w1x1 - 45, H_BOT)])
seg('maroon', [(xr['R2f'], Y['out_rows'][1]), (xr['R2f'], yl['R2f']), (w2x0 + 45, yl['R2f']), (w2x0 + 45, H_BOT)])
seg('maroon', [(xr['R2n'], Y['out_rows'][1]), (xr['R2n'], yl['R2f'] + 8), (w2x0 + 25, yl['R2f'] + 8), (w2x0 + 25, H_BOT)])
seg('navy', [(w1x0 + 60, Y['colr'][0]), (w1x0 + 60, H_BOT)])
seg('navy', [(X['arr_n'][0] + 60, Y['colr'][0]), (X['arr_n'][0] + 60, yl['C1n']), (w1x0 + 90, yl['C1n']), (w1x0 + 90, H_BOT)])
seg('maroon', [(X['arr_f'][1] - 60, Y['colr'][0]), (X['arr_f'][1] - 60, yl['C2f']), (w2x1 - 90, yl['C2f']), (w2x1 - 90, H_BOT)])
seg('maroon', [(w2x1 - 60, Y['colr'][0]), (w2x1 - 60, H_BOT)])
L += [f"\\draw[{{Latex[length=1.6mm]}}-{{Latex[length=1.6mm]}}, grayd] ({fmt(X['arr_f'][0] * S)},{fmt((CORE_H + 25) * S)}) -- "
      f"({fmt(X['arr_f'][1] * S)},{fmt((CORE_H + 25) * S)}) node[midway, above, font=\\scriptsize] {{64 columns $\\times$ 5.1 \\textmu m $\\approx$ {ARR_W:.0f} \\textmu m}};",
      f"\\draw[{{Latex[length=1.6mm]}}-{{Latex[length=1.6mm]}}, grayd] ({fmt((CORE_W + 25) * S)},{fmt(A0 * S)}) -- ({fmt((CORE_W + 25) * S)},{fmt(A1 * S)}) "
      f"node[midway, right, font=\\scriptsize, align=left] {{128 rows\\\\$\\times$ 4.5 \\textmu m\\\\$\\approx$ {ARR_H:.0f} \\textmu m}};",
      f"\\draw[{{Latex[length=1.6mm]}}-{{Latex[length=1.6mm]}}, grayd] (0,{fmt(-25 * S)}) -- ({fmt(CORE_W * S)},{fmt(-25 * S)}) "
      f"node[midway, below, font=\\scriptsize] {{core $\\approx$ {CORE_W / 1000:.2f} mm $\\times$ {CORE_H / 1000:.2f} mm (estimate)}};",
      f"\\node[font=\\bfseries, anchor=south west] at (0,{fmt((CORE_H + 70) * S)}) {{Core floorplan (v1): two crossbars mirrored about a shared row spine}};"]
legend = [('tilec', 'pitch-matched line tiles'), ('dioc', 'clamp diodes at the column ends'), ('anac', 'analog blocks'),
          ('digc', 'synthesized digital'), ('decc', 'decoupling capacitors')]
for k, (cname, t) in enumerate(legend):
    xx = (k % 3) * 600; yy = -110 - (k // 3) * 30
    L.append(f"\\draw[fill={cname}, draw=grayd] ({fmt(xx * S)},{fmt(yy * S)}) rectangle ({fmt((xx + 40) * S)},{fmt((yy + 18) * S)});")
    L.append(f"\\node[font=\\scriptsize, anchor=west] at ({fmt((xx + 50) * S)},{fmt((yy + 9) * S)}) {{{t}}};")
L.append(f"\\node[font=\\scriptsize, anchor=north west, text width=17.5cm, align=left] at (0,{fmt(-160 * S)}) "
         f"{{Each row line has the READ drive at its outer end and the row MUX (write / verify / sense TGs, WL driver) at its inner end. "
         f"Row tokens and row decoders sit once in the spine and drive both arrays; column tiles repeat under each array. "
         f"WU1 and WU2 sit at the center so the free and nudge buses have the same length. The corners below the input drive hold the synthesized digital, "
         f"bias, nudge injector and decoupling capacitors. Gaps of 15 \\textmu m and bus channels of 30 / 90 \\textmu m are left for routing. "
         f"Bus channel: R1, C1 $\\to$ WU1 (navy), R2, C2 $\\to$ WU2 (maroon); the V\\_W bus is not drawn. Sizes are estimates (row pitch 4.5 \\textmu m, column pitch 5.1 \\textmu m assumed).}};")
L += ['\\end{tikzpicture}', '\\end{document}']
(FIG / 'fig_rc_floorplan_v1.tex').write_text('\n'.join(L) + '\n')

# 그림 2: die + IO ring (16 cm = 2.5 mm)
S2 = 16.0 / DIE_W
Q = lambda xx, yy: f'({fmt(xx * S2)},{fmt(yy * S2)})'
L = [PRE, '% 생성: sim/ep_dr/layout/floorplan.py v1 (손으로 고치지 말 것).',
     f"\\draw[line width=0.8pt] {Q(0, 0)} rectangle {Q(DIE_W, DIE_H)};", f"\\draw[gray!60, line width=0.4pt] {Q(M / 2, M / 2)} rectangle {Q(DIE_W - M / 2, DIE_H - M / 2)};"]
# IO ring rail 띠 (셀 원점 = core 쪽 끝에서 잰 높이, LEF 의 met5 rail): 네 변에 같은 깊이로
RAILS = [(6.95, 11.40, 'navy!55'), (13.0, 16.25, 'maroon!70'), (17.85, 22.30, 'maroon!40'), (23.90, 28.35, 'gray!60'),
         (45.70, 54.70, 'grayd!80'), (68.0, 92.95, 'maroon!40'), (173.75, 197.965, 'gray!60')]
D0 = 197.965
for sd in ('top', 'bottom', 'left', 'right'):
    r = {'top': (M, DIE_H - M - D0, DIE_W - M, DIE_H - M), 'bottom': (M, M, DIE_W - M, M + D0),
         'left': (M, M, M + D0, DIE_H - M), 'right': (DIE_W - M - D0, M, DIE_W - M, DIE_H - M)}[sd]
    L.append(f"\\fill[gray!10] {Q(r[0], r[1])} rectangle {Q(r[2], r[3])};")
for a, b, col in RAILS:
    for (x0, y0, x1, y1) in ((M, DIE_H - M - D0 + a, DIE_W - M, DIE_H - M - D0 + b), (M, M + D0 - b, DIE_W - M, M + D0 - a),
                             (M + D0 - b, M, M + D0 - a, DIE_H - M), (DIE_W - M - D0 + a, M, DIE_W - M - D0 + b, DIE_H - M)):
        L.append(f"\\fill[{col}, opacity=0.6] {Q(x0, y0)} rectangle {Q(x1, y1)};")
for c in CORNERS:
    ox, oy = c['origin']
    r = {'TR': (ox, oy, ox + 200, oy + 204), 'TL': (ox - 204, oy, ox, oy + 200), 'BL': (ox - 200, oy - 204, ox, oy), 'BR': (ox, oy - 200, ox + 204, oy)}[c['at']]
    L.append(f"\\draw[fill=gray!40, draw=grayd] {Q(r[0], r[1])} rectangle {Q(r[2], r[3])};")
PCOL = dict(power='maroon', digital='navy', analog='purp', spare='gray!70')
for p in PADS:
    x0, y0, x1, y1 = p['rect']
    L.append(f"\\draw[fill=white, fill opacity=0.35, draw={PCOL[p['type']]}, line width=0.9pt] {Q(x0, y0)} rectangle {Q(x1, y1)};")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dpt = 64.0                                                    # bond pad 중심 (바깥 가장자리에서 ≈ 64 µm)
    bc = {'top': (cx, DIE_H - M - dpt), 'bottom': (cx, M + dpt), 'left': (M + dpt, cy), 'right': (DIE_W - M - dpt, cy)}[p['side']]
    L.append(f"\\draw[fill=padc, draw=grayd, line width=0.2pt] {Q(bc[0] - 30, bc[1] - 30)} rectangle {Q(bc[0] + 30, bc[1] + 30)};")
    nm = p['name'].replace('_', '\\_')
    inner = {'top': (cx, DIE_H + 12), 'bottom': (cx, -12), 'left': (-12, cy), 'right': (DIE_W + 12, cy)}[p['side']]   # 글자는 die 바깥
    anc = {'top': 'west', 'bottom': 'east', 'left': 'east', 'right': 'west'}[p['side']]
    rot = ', rotate=90' if p['side'] in ('top', 'bottom') else ''
    L.append(f"\\node[font=\\tiny, text={PCOL[p['type']]}, anchor={anc}{rot}, inner sep=1pt] at {Q(*inner)} {{{nm}}};")
for rg in RINGS:                                                  # core 전원 ring 
    o, w = rg['offset'], rg['width']
    col = dict(VSS='grayd', VDD='maroon', VCM='purp', VCCD='navy')[rg['net']]
    L.append(f"\\draw[{col}, line width={w * S2 * 28.45:.2f}pt] {Q(o + w / 2, o + w / 2)} rectangle {Q(DIE_W - o - w / 2, DIE_H - o - w / 2)};")
L += core_tex(S2, CORE_OFF[0] * S2, CORE_OFF[1] * S2, detail=False)
L.append(f"\\node[font=\\bfseries, anchor=south west] at {Q(-150, DIE_H + 190)} {{{DIE_W / 1000:.1f} mm $\\times$ {DIE_H / 1000:.1f} mm die, SKY130 IO ring ({len(PADS)} pads)}};")
leg = [('maroon', f"power ({n_by['power']}): VDD, VSS (hvc clamp), VDDL, VSSL (lvc clamp), VCM"), ('navy', f"digital ({n_by['digital']}): gpiov2 (ESD, level shift)"),
       ('purp', f"analog ({n_by['analog']}): analog\\_esd (ESD to VDDA / VSSA)"), ('gray!70', f"spare ({n_by['spare']}): analog\\_esd")]
for k, (cname, t) in enumerate(leg):
    yy = -230 - k * 70
    L.append(f"\\draw[draw={cname}, line width=0.9pt] {Q(0, yy)} rectangle {Q(45, yy + 45)};")
    L.append(f"\\node[font=\\scriptsize, anchor=west] at {Q(65, yy + 22)} {{{t}}};")
L.append(f"\\node[font=\\scriptsize, anchor=north west, text width=16cm, align=left] at {Q(0, -230 - 4 * 70)} "
         f"{{IO ring = sky130\\_ef\\_io cells at their LEF sizes: corner 200 $\\times$ 204 \\textmu m, pad cells 75 / 80 \\textmu m wide, 198--200 \\textmu m deep, "
         f"bond pad $\\approx$ 60 \\textmu m (yellow). Gaps are filled with com\\_bus\\_slice so the IO rails run all the way round "
         f"(bands, inside to outside: VCCD, VDDA, VDDIO, VSSIO, VSSA, VDDIO, VSSIO). "
         f"VSSA = VSSIO = VSSD = VSS ($-$2.5 V, substrate), VDDA = VDDIO = VDD (+2.5 V), VCCD = VSS + 1.8 V. "
         f"Inside the IO ring: core power ring VSS, VDD, VCM, VCCD. Pads fill {min(fill_ratio.values()) * 100:.0f}--{max(fill_ratio.values()) * 100:.0f} \\% of each side.}};")
L += ['\\end{tikzpicture}', '\\end{document}']
(FIG / 'fig_rc_padframe_v1.tex').write_text('\n'.join(L) + '\n')
need_w = CORE_W + 2 * (RING_OUT + 10); need_h = CORE_H + 2 * (RING_OUT + 10)
print(f"core {CORE_W:.0f} × {CORE_H:.0f} µm, die {DIE_W:.0f} × {DIE_H:.0f} (최소 ≈ {need_w:.0f} × {need_h:.0f}), 패드 {len(PADS)} {n_by}, "
      f"filler {len(FILL)} (이음 {n_conn}), 변 채움 {fill_ratio}")
