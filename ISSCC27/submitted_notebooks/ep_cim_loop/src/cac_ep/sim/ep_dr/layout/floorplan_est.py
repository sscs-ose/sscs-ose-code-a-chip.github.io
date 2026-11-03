"""가견적 배치 (10/27, 사용자 "내가 옛날에 가견적으로 만들어두려고 한 게 있긴 해. 그것을 활용해봐") — floorplan_v2.py 사본을 고침.
v2 에서 바꾼 것: core 블록 크기 = est_blocks.py 가 실제 셀로 채운 블록 크기 (est_blocks.json), 블록마다 채울 셀 (cell = B_*).
  열 쪽은 두 블록: 'column MUX (..)' = colrow (열 MUX TG + clamp 다이오드 둘 다), 'COL1/COL2 token (..)' = 열 decoder + COL shift reg.
  → 배열 위 다이오드 줄 없음. 블록 배치 순서는 v2 와 같음. 패드 원하는 자리는 블록 자리에서 계산.
  빈 곳은 조립 때 decap (B_decap_tile) 으로 채운다 (route_gds.py).
낸다: floorplan_est.json. GDS = padframe_gds.py floorplan_est.json chip_est, 블록·배선 = route_est.py → route_gds.py.
쓰임: python floorplan_est.py   (먼저 est_blocks.py)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── core (µm): 실제 셀로 채운 블록 크기 (est_blocks.json)
E = json.load(open(HERE / 'est_blocks.json'))
WH = lambda k: (E[k]['w'], E[k]['h'])
G, g, GS = 15.0, 5.0, 25.0                                       # GS = 배열 ↔ 입력 구동 틈 (VRAIL·nudge 주입 선 자리)
AW, AH = max(WH('crossbar')[0], WH('col_strip')[0]), WH('crossbar')[1]
W_INSW, H_INSW = WH('input_drive'); W_ROWM, H_ROWM = WH('row_mux')
W_TOK, W_DEC, W_DAT = WH('row_tok')[0], WH('row_dec')[0], WH('data')[0]
H_CS, H_CD = WH('col_strip')[1], WH('col_dec')[1]
H_BOT = max(WH('wu1')[1], WH('global_digital_5v')[1] + g + WH('global_digital_1v8')[1])
H_BUS, TOPM = 60.0, 15.0                                         # 버스 통로, 배열 위 (D 버스 자리)
x, X = 0.0, {}
for k, w, gap in (('insw_f', W_INSW, 0), ('arr_f', AW, GS), ('rowm_f', W_ROWM, G), ('spine', W_TOK + W_DEC + W_DAT + 2 * g, 10),
                  ('rowm_n', W_ROWM, 10), ('arr_n', AW, G), ('insw_n', W_INSW, GS)):
    x += gap; X[k] = (x, x + w); x += w
CORE_W = x
XC = CORE_W / 2
Y = {'bot': (0.0, H_BOT), 'bus': (H_BOT, H_BOT + H_BUS)}
y = H_BOT + H_BUS
for k, h, gap in (('cold', H_CD, 0), ('cols', H_CS, g), ('arr', AH, G)):
    y += gap; Y[k] = (y, y + h); y += h
CORE_H = y + TOPM
A0, A1 = Y['arr']
B = []


def blk(name, kind, cell, x0, y0, w, h, mirror=False):
    B.append(dict(name=name, kind=kind, cell='B_' + cell, rect=[round(v, 2) for v in (x0, y0, x0 + w, y0 + h)], mirror=mirror))


for p, side in (('f', 'free'), ('n', 'nudge')):
    ax0 = X[f'arr_{p}'][0]
    blk(f'{side} crossbar', 'array', 'crossbar', ax0, A0, *WH('crossbar'))
    blk(f'column MUX ({side})', 'pitch_col', 'col_strip', ax0, Y['cols'][0], *WH('col_strip'))
    blk(f'COL1/COL2 token ({side})', 'pitch_col', 'col_dec', ax0, Y['cold'][0], *WH('col_dec'))
    blk(f'row MUX + WL ({side})', 'pitch_row', 'row_mux', X[f'rowm_{p}'][0], A1 - H_ROWM, W_ROWM, H_ROWM)
    blk(f'input drive ({side})', 'pitch_row', 'input_drive', X[f'insw_{p}'][0], A1 - H_INSW, W_INSW, H_INSW, mirror=(p == 'n'))   # 행 출력선이 배열 쪽
s0 = X['spine'][0]
blk('ROW1/ROW2 token', 'pitch_row', 'row_tok', s0, A1 - WH('row_tok')[1], *WH('row_tok'))
blk('row decoder (shared)', 'pitch_row', 'row_dec', s0 + W_TOK + g, A1 - WH('row_dec')[1], *WH('row_dec'))
blk('DATA + latch + gate', 'pitch_row', 'data', s0 + W_TOK + W_DEC + 2 * g, A1 - WH('data')[1], *WH('data'))
wb_w = WH('write_buffer')[0]
blk('write buffer', 'analog', 'write_buffer', XC - wb_w / 2, 0, *WH('write_buffer'))
blk('WU1', 'analog', 'wu1', XC - wb_w / 2 - G - WH('wu1')[0], 0, *WH('wu1'))
blk('WU2', 'analog', 'wu2', XC + wb_w / 2 + G, 0, *WH('wu2'))
blk('global digital (5 V)', 'digital', 'global_digital_5v', X['insw_f'][0], 0, *WH('global_digital_5v'))   # 왼쪽 아래 = gpio 패드 앞
blk('global digital (1.8 V)', 'digital', 'global_digital_1v8', X['insw_f'][0], WH('global_digital_5v')[1] + g,
    *WH('global_digital_1v8'))
blk('bias', 'analog', 'bias', X['insw_n'][0], 0, *WH('bias'))
blk('nudge injector', 'analog', 'nudge_injector', X['insw_n'][0], A1 - H_INSW - G - WH('nudge_injector')[1], *WH('nudge_injector'))
ych = Y['bus'][1] + 20                                           # 가운데 빈 곳 (두 열 쌓음 사이, spine 아래)
blk('readout TG (free)', 'analog', 'readout_tg_f', X['rowm_f'][0] + 30, ych, *WH('readout_tg_f'))
blk('readout TG (nudge)', 'analog', 'readout_tg_n', X['rowm_n'][1] - 30 - WH('readout_tg_n')[0], ych, *WH('readout_tg_n'))

# ── die + IO ring (실제 SKY130 IO 셀, LEF 크기)
M = 30.0                                                          # die 가장자리 ~ IO 셀 바깥 (seal ring 자리)
RING_OUT = M + 204 + 10 + 4 * 20                                  # IO ring (204) + 틈 10 + core 전원 ring 4 개 (15 µm + 5 µm)
up10 = lambda v: float(-(-v // 10) * 10)
DIE_W, DIE_H = up10(CORE_W + 2 * (RING_OUT + 10)), up10(CORE_H + 2 * (RING_OUT + 10))   # 최소를 10 µm 로 올림
OX, OY = (DIE_W - CORE_W) / 2, (DIE_H - CORE_H) / 2              # core 원점 (die 좌표)
BD = {b['name']: [OX + b['rect'][0], OY + b['rect'][1], OX + b['rect'][2], OY + b['rect'][3]] for b in B}
cx = lambda n: (BD[n][0] + BD[n][2]) / 2
cy = lambda n: (BD[n][1] + BD[n][3]) / 2
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
# (이름, IO 셀, 원하는 패드 중심 = die 좌표, 위·아래 변은 x, 왼·오른 변은 y) — 이어지는 블록 자리에서 계산 (가견적판)
xf, xn, xs = cx('input drive (free)'), cx('input drive (nudge)'), (BD['ROW1/ROW2 token'][0] + BD['DATA + latch + gate'][2]) / 2
xg, xb = cx('global digital (5 V)'), BD['bias'][0] + 100
P_SIDES = {
    'top': [('VRAILP', A_, xf - 45), ('VRAILM', A_, xf + 45), ('VDD', 'vdda', xs - 120), ('VSS', 'vssa', xs - 40), ('VCM', A_, xs + 40),
            ('SPARE1', A_, xs + 120), ('SPARE2', A_, xs + 200), ('SPARE3', A_, xs + 280), ('VRAILM', A_, xn - 45), ('VRAILP', A_, xn + 45)],
    'right': [('VDD', 'vddio', BD['input drive (nudge)'][3] - 60), ('VSS', 'vssio', BD['input drive (nudge)'][3] - 150),
              ('SPARE4', A_, cy('input drive (nudge)')), ('SPARE5', A_, cy('input drive (nudge)') - 90),
              ('IBIAS', A_, cy('bias') + 100), ('VBNC', A_, cy('bias') + 20), ('VBPC', A_, cy('bias') - 60)],
    'bottom': [('VSS', 'vssa', xn + 120), ('VDD', 'vdda', xn + 40), ('VCM', A_, xn - 40), ('VBUS_N', A_, cx('readout TG (nudge)')),
               ('VWH', A_, cx('write buffer') + 80), ('VWLO', A_, cx('write buffer')), ('VWL', A_, cx('write buffer') - 80),
               ('VBUS_F', A_, cx('readout TG (free)')), ('LAT', G_, xg + 160), ('CK3', G_, xg + 80), ('CK', G_, xg), ('LQ2', G_, xg - 80),
               ('LQ1', G_, xg - 160), ('VDDL', 'vccd', xg - 240), ('VSSL', 'vssd', xg - 320)],
    'left': [('VSSL', 'vssd', OY + 10), ('VDDL', 'vccd', OY + 90), ('SCK', G_, OY + 180), ('SDI', G_, OY + 260), ('SLD', G_, OY + 340),
             ('RST', G_, OY + 420), ('SEL_EN', G_, OY + 500), ('WP', G_, OY + 580), ('VDD', 'vddio', cy('input drive (free)') + 40),
             ('VSS', 'vssio', cy('input drive (free)') + 130)]}
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


PAD_GAP = 15                                                      # 패드 사이 최소 틈 (floorplan_v2.py 와 같음: IO 셀 도형이 LEF 폭 밖으로 나옴)
PADS, FILL, n_conn = [], [], 0
for side, items in P_SIDES.items():
    a, b = SPAN[side]; L = abs(b - a); d = 1 if b > a else -1
    widths = [CELL[c][1] for _, c, _ in items]
    conn = side == 'bottom'                                       # VCCHIB=VCCD, VSWITCH=VDDIO 이음 slice 하나 (아래 변, 가장 큰 틈)
    u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]   # 원하는 시작 (변 시작에서 잰 거리)
    for i in range(1, len(u)):                                    # 겹치지 않게 앞으로 밀고
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
CORE_OFF = (OX, OY)
assert min(CORE_OFF) >= RING_OUT + 10, ('core 가 전원 ring 과 겹침', CORE_OFF, RING_OUT)
fill_ratio = {sd: round(sum(CELL[c][1] for _, c, _ in it) / abs(SPAN[sd][1] - SPAN[sd][0]), 3) for sd, it in P_SIDES.items()}

json.dump(dict(version='가견적 (10/27, est_blocks 실제 셀 크기, v3 핀)', note='블록 크기 = est_blocks.json (실제 셀, DRC·LVS 없음). 좌표 µm. core 원점 = core 왼쪽 아래, 패드·filler 는 die 좌표.',
               iolib='sky130_ef_io / sky130_fd_io (volare sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b), 크기 = LEF',
               rails=dict(VSSA='VSS', VSSIO='VSS', VSSD='VSS', VDDA='VDD', VDDIO='VDD', VCCD='VSS+1.8V', VCCHIB='VCCD', VSWITCH='VDDIO'),
               core=dict(w=round(CORE_W, 2), h=round(CORE_H, 2), offset_in_die=[round(v, 2) for v in CORE_OFF]),
               die=dict(w=DIE_W, h=DIE_H, margin=M), corners=CORNERS, pads=PADS, fillers=FILL, core_rings=RINGS, blocks=B,
               pad_count=n_by, side_fill=fill_ratio), open(HERE / 'floorplan_est.json', 'w'), indent=1, ensure_ascii=False)
print(f"core {CORE_W:.0f} × {CORE_H:.0f} µm, die {DIE_W:.0f} × {DIE_H:.0f} µm ({DIE_W * DIE_H / 1e6:.2f} mm²), 패드 {len(PADS)} {n_by}, "
      f"filler {len(FILL)} (이음 {n_conn}), 변 채움 {fill_ratio}")
