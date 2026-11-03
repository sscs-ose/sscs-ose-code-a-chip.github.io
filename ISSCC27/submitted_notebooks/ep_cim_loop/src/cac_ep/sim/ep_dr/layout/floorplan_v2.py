"""PAD frame v2 (10/26, tape-out 준비) — floorplan.py (v1) 사본을 고침. 사용자 "나중에 tape-out 내는 것도 고려하고 있어. 그러니 최적화 해봐봐".
v1 에서 바꾼 것:
  - 핀 = v3 (핀 줄이기, real_circuit/gen_chip_deck2.py, chip_read2·chip_write2 검증): 디지털 입력 9 (SCK SDI SLD RST SEL_EN WP CK CK3 LAT)
    + 출력 2 (LQ1 LQ2) + 아날로그 10 (VRAILP VRAILM VWH VWLO VWL VBUS_F VBUS_N IBIAS VBNC VBPC). v1 은 v2b 핀 (신호 40).
  - VRAILP·VRAILM 은 패드 2 개씩 (위 변 양 끝 = free·nudge 입력 구동 가까이, 칩 안에서 한 net). 행 전류가 이 rail 로 흘러 IR 강하가 입력 오차가 됨.
  - 전원 rail 마다 패드 2 개 (마주 보는 변): VDDA·VSSA 위·아래, VDDIO·VSSIO 왼·오른, VCCD·VSSD 왼·아래 (합성 디지털 가까이). VCM 2 (위·아래), 여유 5.
  - 패드는 이어지는 블록 앞에 모은다 (10/27, 원하는 중심 위치 → 겹치지 않게 맞춤): gpio 11 = 합성 디지털 (레벨 변환) 앞, VRAIL = 입력 구동 위,
    쓰기 전압·판독 VBUS = WU·write buffer 아래, bias 3 = bias 옆. 같은 간격 판 (DRC·rail 검사한 것) = floorplan_v2_even.json, out/chip_v2_even.*
  - die = core + IO ring + core 전원 ring 이 들어가는 최소를 10 µm 로 올림 (v1 은 2.5 × 1.9 mm 고정).
  - core 블록은 v1 과 같음 (어림). 그림 (TikZ) 은 만들지 않는다 — GDS 그림 = padframe_gds.py.
낸다: floorplan_v2.json. GDS = padframe_gds.py floorplan_v2.json chip_v2 (Olympus KLayout).
쓰임: python floorplan_v2.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

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
M = 30.0                                                          # die 가장자리 ~ IO 셀 바깥 (seal ring 자리)
RING_OUT = M + 204 + 10 + 4 * 20                                  # IO ring (204) + 틈 10 + core 전원 ring 4 개 (15 µm + 5 µm)
up10 = lambda v: float(-(-v // 10) * 10)
DIE_W, DIE_H = up10(CORE_W + 2 * (RING_OUT + 10)), up10(CORE_H + 2 * (RING_OUT + 10))   # 최소를 10 µm 로 올림
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
# (이름, IO 셀, 원하는 패드 중심 = die 좌표, 위·아래 변은 x, 왼·오른 변은 y). 이어지는 블록 앞에 모은다 (10/27, 보고용 배치·연결 그림).
# gpio 11 개 = 레벨 변환이 있는 합성 디지털 (왼쪽 아래) 앞. VRAIL = 입력 구동 위, 쓰기 전압 = write buffer 아래, bias 3 개 = bias 옆.
P_SIDES = {
    'top': [('VRAILP', A_, 470), ('VRAILM', A_, 580), ('VDD', 'vdda', 1060), ('VSS', 'vssa', 1150), ('VCM', A_, 1240), ('SPARE1', A_, 1330),
            ('SPARE2', A_, 1420), ('SPARE3', A_, 1510), ('VRAILM', A_, 1860), ('VRAILP', A_, 1970)],
    'right': [('VDD', 'vddio', 1450), ('VSS', 'vssio', 1350), ('SPARE4', A_, 1150), ('SPARE5', A_, 1050), ('IBIAS', A_, 500),
              ('VBNC', A_, 420), ('VBPC', A_, 340)],
    'bottom': [('VSS', 'vssa', 2050), ('VDD', 'vdda', 1960), ('VCM', A_, 1870), ('VBUS_N', A_, 1500), ('VWH', A_, 1300), ('VWLO', A_, 1230),
               ('VWL', A_, 1160), ('VBUS_F', A_, 1000), ('LAT', G_, 780), ('CK3', G_, 700), ('CK', G_, 620), ('LQ2', G_, 540), ('LQ1', G_, 460),
               ('VDDL', 'vccd', 380), ('VSSL', 'vssd', 300)],
    'left': [('VSSL', 'vssd', 300), ('VDDL', 'vccd', 380), ('SCK', G_, 470), ('SDI', G_, 550), ('SLD', G_, 630), ('RST', G_, 710),
             ('SEL_EN', G_, 790), ('WP', G_, 870), ('VDD', 'vddio', 1250), ('VSS', 'vssio', 1350)]}
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


PAD_GAP = 15                                                      # 패드 사이 최소 틈 (µm, slice 로 채움). IO 셀 도형이 LEF 폭 밖으로 나옴:
                                                                  # vccd_lvc_clamped_pad 86.2 µm (LEF 75), gpiov2 −0.7…80.9 (LEF 80) — 맞붙이면 겹쳐 단락 (10/27 DRC·rail 검사)
PADS, FILL, n_conn = [], [], 0
for side, items in P_SIDES.items():
    a, b = SPAN[side]; L = abs(b - a); d = 1 if b > a else -1
    widths = [CELL[c][1] for _, c, _ in items]
    conn = side == 'bottom'                                       # VCCHIB=VCCD, VSWITCH=VDDIO 이음 slice 하나 (아래 변, 가장 큰 틈)
    u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]   # 원하는 시작 (변 시작에서 잰 거리)
    for i in range(1, len(u)):                                    # 겹치지 않게 앞으로 밀고 (패드 사이 PAD_GAP 이상)
        u[i] = max(u[i], u[i - 1] + widths[i - 1] + PAD_GAP)
    u[-1] = min(u[-1], int(L) - widths[-1])
    for i in range(len(u) - 2, -1, -1):                           # 끝을 넘으면 뒤에서 당김
        u[i] = min(u[i], u[i + 1] - widths[i] - PAD_GAP)
    assert u[0] >= 0, (side, u)
    ends = [0] + [ui + w for ui, w in zip(u, widths)]
    gaps = [ui - e for ui, e in zip(u + [int(L)], ends)]
    n = len(items) + 1
    i_conn = max(range(n), key=lambda i: gaps[i]) if conn else -1
    assert not conn or gaps[i_conn] >= CELL['connect'][1]
    if conn:
        gaps[i_conn] -= CELL['connect'][1]
    s = a
    for i in range(n):
        g = gaps[i]
        if i == i_conn:                                           # 이음 slice
            o, r = place(side, s, *CELL['connect'][:1], CELL['connect'][1], CELL['connect'][2]); FILL.append(dict(cell=CELL['connect'][0], side=side, origin=o, rot=ROT[side], rect=r))
            s += d * CELL['connect'][1]; n_conn += 1
        for w in (20, 10, 5, 1):                                  # 틈을 com_bus_slice 로 채움 (rail 이음)
            while g >= w:
                o, r = place(side, s, SLICE[w], w, 197.965); FILL.append(dict(cell=SLICE[w], side=side, origin=o, rot=ROT[side], rect=r))
                s += d * w; g -= w
        if i < len(items):
            nm, c, _ = items[i]; cn, w, h = CELL[c]
            o, r = place(side, s, cn, w, h)
            PADS.append(dict(name=nm, type=ptype(nm, c), io=c, cell=cn, side=side, origin=[round(v, 3) for v in o], rot=ROT[side], rect=[round(v, 3) for v in r]))
            s += d * w
    assert abs(s - b) < 1e-6, (side, s, b)
CORNERS = [dict(cell=CORNER, at='TR', rot=0, origin=[DIE_W - M - 200, DIE_H - M - 204]), dict(cell=CORNER, at='TL', rot=1, origin=[M + 204, DIE_H - M - 200]),
           dict(cell=CORNER, at='BL', rot=2, origin=[M + 200, M + 204]), dict(cell=CORNER, at='BR', rot=3, origin=[DIE_W - M - 204, M + 200])]
n_by = {t: sum(p['type'] == t for p in PADS) for t in ('digital', 'analog', 'power', 'spare')}
assert len(PADS) == 42 and n_by == dict(digital=11, analog=12, power=14, spare=5), n_by
# core 전원 ring (IO ring 안쪽): 바깥부터 VSS, VDD, VCM, VCCD — 각 15 µm, 사이 5 µm (met4·met5 겹침)
RING_IN = M + 204 + 10
RINGS = [dict(net=n, offset=round(RING_IN + k * 20, 2), width=15.0) for k, n in enumerate(('VSS', 'VDD', 'VCM', 'VCCD'))]
assert RING_OUT == RING_IN + 4 * 20
CORE_OFF = ((DIE_W - CORE_W) / 2, (DIE_H - CORE_H) / 2)
assert min(CORE_OFF) >= RING_OUT + 10, ('core 가 전원 ring 과 겹침', CORE_OFF, RING_OUT)
fill_ratio = {sd: round(sum(CELL[c][1] for _, c, _ in it) / abs(SPAN[sd][1] - SPAN[sd][0]), 3) for sd, it in P_SIDES.items()}

json.dump(dict(version='v2 (10/26, tape-out 준비, v3 핀)', note='어림 (가정): 행 pitch 4.5 µm, 열 pitch 5.1 µm, 블록 크기 어림. 좌표 µm. core 원점 = core 왼쪽 아래, 패드·filler 는 die 좌표.',
               iolib='sky130_ef_io / sky130_fd_io (volare sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b), 크기 = LEF',
               rails=dict(VSSA='VSS', VSSIO='VSS', VSSD='VSS', VDDA='VDD', VDDIO='VDD', VCCD='VSS+1.8V', VCCHIB='VCCD', VSWITCH='VDDIO'),
               pitch=dict(row=P_R, col=P_C), core=dict(w=round(CORE_W, 2), h=round(CORE_H, 2), offset_in_die=[round(v, 2) for v in CORE_OFF]),
               die=dict(w=DIE_W, h=DIE_H, margin=M), corners=CORNERS, pads=PADS, fillers=FILL, core_rings=RINGS, blocks=B,
               pad_count=n_by, side_fill=fill_ratio), open(HERE / 'floorplan_v2.json', 'w'), indent=1, ensure_ascii=False)
print(f"core {CORE_W:.0f} × {CORE_H:.0f} µm, die {DIE_W:.0f} × {DIE_H:.0f} µm ({DIE_W * DIE_H / 1e6:.2f} mm²), 패드 {len(PADS)} {n_by}, "
      f"filler {len(FILL)} (이음 {n_conn}), 변 채움 {fill_ratio}")
