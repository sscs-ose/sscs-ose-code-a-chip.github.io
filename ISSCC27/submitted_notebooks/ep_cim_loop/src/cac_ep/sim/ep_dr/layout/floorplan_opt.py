"""floorplan 재배치 후보 (10/27, 사용자 "지금 구조도 살짝 수정하거나 최적화 할 수 있을 것 같거든", "일단은 사진을 만들어봐. 그것 보면서 피드백할게")
— floorplan_est.py (가견적, est_blocks.json 실제 셀 크기) 사본을 고침. DRC·LVS 없음, 논의용 그림.
후보:
  now = 지금 가견적 (floorplan_est.json 을 그대로 읽어 같은 축척으로 그림)
  A   = 맨 아래 띠의 작은 블록 (WU1·WU2·write buffer·판독 TG 둘) 을 spine 아래 가운데 (두 열 쌓음 사이) 로 → 맨 아래 띠 없앰.
        합성 디지털 = 왼쪽 입력 구동 아래, bias·nudge 주입기 = 오른쪽 입력 구동 아래. 입력 스위치 W 1,000 µm.
  B   = A + 입력 스위치 W 300 µm. 입력 구동 블록 폭은 어림: est 는 nf 50 (핑거 20 µm) × 열 11 개 → nf 15 로 열마다 35 핑거 × 0.79 µm 줄임.
패드: 42 개 그대로, 원하는 중심 = 이어지는 블록 자리 (floorplan_est.py 와 같은 식). die 높이가 줄어 왼쪽 변에 10 개가 안 들어가서
      SEL_EN·WP 를 아래 변 (합성 디지털 앞) 으로 옮김.
낸다: floorplan_opt_A.json, floorplan_opt_B.json (floorplan_est.json 과 같은 꼴), out/floorplan_opt_compare.png
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python floorplan_opt.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import Rectangle                          # noqa: E402

HERE = Path(__file__).resolve().parent
E = json.load(open(HERE / 'est_blocks.json'))
WH = lambda k: (E[k]['w'], E[k]['h'])
G, g, GS, TOPM, H_BUS = 15.0, 5.0, 25.0, 15.0, 60.0                # floorplan_est.py 와 같은 틈
M = 30.0
RING_OUT = M + 204 + 10 + 4 * 20
up10 = lambda v: float(-(-v // 10) * 10)
CELL = {
    'gpio': ('sky130_ef_io__gpiov2_pad', 80.0, 197.965), 'analog': ('sky130_ef_io__analog_esd_pad', 75.0, 200.0),
    'vdda': ('sky130_ef_io__vdda_hvc_clamped_pad', 75.0, 197.965), 'vssa': ('sky130_ef_io__vssa_hvc_clamped_pad', 75.0, 197.965),
    'vddio': ('sky130_ef_io__vddio_hvc_clamped_pad', 75.0, 197.965), 'vssio': ('sky130_ef_io__vssio_hvc_clamped_pad', 75.0, 197.965),
    'vccd': ('sky130_ef_io__vccd_lvc_clamped_pad', 75.0, 197.965), 'vssd': ('sky130_ef_io__vssd_lvc_clamped_pad', 75.0, 197.965),
    'connect': ('sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um', 20.0, 197.965)}
SLICE = {w: f'sky130_ef_io__com_bus_slice_{w}um' for w in (20, 10, 5, 1)}
CORNER = 'sky130_ef_io__corner_pad'
PAD_GAP = 15
G_, A_ = 'gpio', 'analog'
ptype = lambda n, c: 'spare' if n.startswith('SPARE') else 'power' if c not in (G_, A_) or n == 'VCM' else 'digital' if c == G_ else 'analog'
ROT = {'top': 0, 'left': 1, 'bottom': 2, 'right': 3}


def insw_w(w_sw):
    """입력 구동 블록 폭 (µm). est_blocks: W 1,000 = nf 50 × 핑거 20 µm, 소자 열 11 개. 핑거 피치 L + 0.29 = 0.79 µm."""
    return WH('input_drive')[0] - 11 * (50 - round(w_sw / 20)) * 0.79


def build(tag, w_sw):
    W_INSW, H_INSW = insw_w(w_sw), WH('input_drive')[1]
    AW, AH = max(WH('crossbar')[0], WH('col_strip')[0]), WH('crossbar')[1]
    W_ROWM, H_ROWM = WH('row_mux')
    W_TOK, W_DEC, W_DAT = WH('row_tok')[0], WH('row_dec')[0], WH('data')[0]
    H_CS, H_CD = WH('col_strip')[1], WH('col_dec')[1]
    x, X = 0.0, {}
    for k, w, gap in (('insw_f', W_INSW, 0), ('arr_f', AW, GS), ('rowm_f', W_ROWM, G), ('spine', W_TOK + W_DEC + W_DAT + 2 * g, 10),
                      ('rowm_n', W_ROWM, 10), ('arr_n', AW, G), ('insw_n', W_INSW, GS)):
        x += gap; X[k] = (x, x + w); x += w
    CORE_W = x
    XC = CORE_W / 2
    # 세로: spine 아래 가운데 = WU 줄 (y 0 … H_WU) + 버스 통로 (H_BUS) + 틈 → row MUX 아래 끝. 배열은 row MUX 와 위를 맞춤
    H_WU = WH('wu1')[1]
    A1 = H_WU + H_BUS + G + H_ROWM
    A0 = A1 - AH
    Y = {'cols': (A0 - G - H_CS, A0 - G)}
    Y['cold'] = (Y['cols'][0] - g - H_CD, Y['cols'][0] - g)
    assert Y['cold'][0] >= 0, ('열 쌓음이 core 아래로 나감', Y)
    CORE_H = A1 + TOPM
    B = []

    def blk(name, kind, cell, x0, y0, w, h, moved=False):
        B.append(dict(name=name, kind=kind, cell='B_' + cell, rect=[round(v, 2) for v in (x0, y0, x0 + w, y0 + h)], moved=moved))

    for p, side in (('f', 'free'), ('n', 'nudge')):
        ax0 = X[f'arr_{p}'][0]
        blk(f'{side} crossbar', 'array', 'crossbar', ax0, A0, *WH('crossbar'))
        blk(f'column MUX ({side})', 'pitch_col', 'col_strip', ax0, Y['cols'][0], *WH('col_strip'))
        blk(f'COL1/COL2 token ({side})', 'pitch_col', 'col_dec', ax0, Y['cold'][0], *WH('col_dec'))
        blk(f'row MUX + WL ({side})', 'pitch_row', 'row_mux', X[f'rowm_{p}'][0], A1 - H_ROWM, W_ROWM, H_ROWM)
        blk(f'input drive ({side})', 'pitch_row', 'input_drive' if w_sw == 1000 else f'input_drive_w{w_sw}',
            X[f'insw_{p}'][0], A1 - H_INSW, W_INSW, H_INSW, moved=(w_sw != 1000))
    s0 = X['spine'][0]
    blk('ROW1/ROW2 token', 'pitch_row', 'row_tok', s0, A1 - WH('row_tok')[1], *WH('row_tok'))
    blk('row decoder (shared)', 'pitch_row', 'row_dec', s0 + W_TOK + g, A1 - WH('row_dec')[1], *WH('row_dec'))
    blk('DATA + latch + gate', 'pitch_row', 'data', s0 + W_TOK + W_DEC + 2 * g, A1 - WH('data')[1], *WH('data'))
    # spine 아래 가운데: WU1 · write buffer · WU2, 양옆에 판독 TG (R2 버스 → VBUS 패드)
    wb_w, wu_w = WH('write_buffer')[0], WH('wu1')[0]
    blk('write buffer', 'analog', 'write_buffer', XC - wb_w / 2, 0, *WH('write_buffer'), moved=True)
    blk('WU1', 'analog', 'wu1', XC - wb_w / 2 - G - wu_w, 0, *WH('wu1'), moved=True)
    blk('WU2', 'analog', 'wu2', XC + wb_w / 2 + G, 0, *WH('wu2'), moved=True)
    tw = WH('readout_tg_f')[0]
    blk('readout TG (free)', 'analog', 'readout_tg_f', XC - wb_w / 2 - G - wu_w - G - tw, 0, *WH('readout_tg_f'), moved=True)
    blk('readout TG (nudge)', 'analog', 'readout_tg_n', XC + wb_w / 2 + G + wu_w + G, 0, *WH('readout_tg_n'), moved=True)
    assert B[-1]['rect'][2] <= X['rowm_n'][1] and B[-2]['rect'][0] >= X['rowm_f'][0], '가운데 블록이 열 쌓음과 겹침'
    # 입력 구동 아래 모서리: 왼쪽 = 합성 디지털 (gpio 패드 앞), 오른쪽 = bias·nudge 주입기
    fx0, nx0 = X['insw_f'][0], X['insw_n'][0]
    assert W_INSW >= WH('global_digital_5v')[0], '입력 구동 아래에 디지털이 안 들어감'
    blk('global digital (5 V)', 'digital', 'global_digital_5v', fx0, 0, *WH('global_digital_5v'), moved=True)
    blk('global digital (1.8 V)', 'digital', 'global_digital_1v8', fx0, WH('global_digital_5v')[1] + g, *WH('global_digital_1v8'), moved=True)
    blk('bias', 'analog', 'bias', nx0, 0, *WH('bias'), moved=True)
    blk('nudge injector', 'analog', 'nudge_injector', nx0, A1 - H_INSW - G - WH('nudge_injector')[1], *WH('nudge_injector'))
    assert A1 - H_INSW - G - WH('nudge_injector')[1] >= WH('bias')[1] + G, '오른쪽 아래 모서리가 모자람'

    # ── die + IO ring (floorplan_est.py 와 같은 규칙)
    DIE_W, DIE_H = up10(CORE_W + 2 * (RING_OUT + 10)), up10(CORE_H + 2 * (RING_OUT + 10))
    OX, OY = (DIE_W - CORE_W) / 2, (DIE_H - CORE_H) / 2
    BD = {b['name']: [OX + b['rect'][0], OY + b['rect'][1], OX + b['rect'][2], OY + b['rect'][3]] for b in B}
    cx = lambda n: (BD[n][0] + BD[n][2]) / 2
    cy = lambda n: (BD[n][1] + BD[n][3]) / 2
    xf, xn, xs = cx('input drive (free)'), cx('input drive (nudge)'), (BD['ROW1/ROW2 token'][0] + BD['DATA + latch + gate'][2]) / 2
    xg = cx('global digital (5 V)')
    P_SIDES = {
        'top': [('VRAILP', A_, xf - 45), ('VRAILM', A_, xf + 45), ('VDD', 'vdda', xs - 120), ('VSS', 'vssa', xs - 40), ('VCM', A_, xs + 40),
                ('SPARE1', A_, xs + 120), ('SPARE2', A_, xs + 200), ('SPARE3', A_, xs + 280), ('VRAILM', A_, xn - 45), ('VRAILP', A_, xn + 45)],
        'right': [('VDD', 'vddio', BD['input drive (nudge)'][3] - 60), ('VSS', 'vssio', BD['input drive (nudge)'][3] - 150),
                  ('SPARE4', A_, cy('input drive (nudge)')), ('SPARE5', A_, cy('input drive (nudge)') - 90),
                  ('IBIAS', A_, cy('bias') + 100), ('VBNC', A_, cy('bias') + 20), ('VBPC', A_, cy('bias') - 60)],
        'bottom': [('VSS', 'vssa', xn + 120), ('VDD', 'vdda', xn + 40), ('VCM', A_, xn - 40), ('VBUS_N', A_, cx('readout TG (nudge)')),
                   ('VWH', A_, cx('write buffer') + 80), ('VWLO', A_, cx('write buffer')), ('VWL', A_, cx('write buffer') - 80),
                   ('VBUS_F', A_, cx('readout TG (free)')), ('SEL_EN', G_, xg + 320), ('WP', G_, xg + 240), ('LAT', G_, xg + 160),
                   ('CK3', G_, xg + 80), ('CK', G_, xg), ('LQ2', G_, xg - 80), ('LQ1', G_, xg - 160), ('VDDL', 'vccd', xg - 240), ('VSSL', 'vssd', xg - 320)],
        'left': [('VSSL', 'vssd', OY + 10), ('VDDL', 'vccd', OY + 90), ('SCK', G_, OY + 180), ('SDI', G_, OY + 260), ('SLD', G_, OY + 340),
                 ('RST', G_, OY + 420), ('VDD', 'vddio', cy('input drive (free)') + 40), ('VSS', 'vssio', cy('input drive (free)') + 130)]}
    SPAN = {'top': (M + 204, DIE_W - M - 200), 'bottom': (DIE_W - M - 204, M + 200), 'right': (DIE_H - M - 204, M + 200), 'left': (M + 204, DIE_H - M - 200)}

    def place(side, s, w, h):
        if side == 'top':
            return (s, DIE_H - M - h), [s, DIE_H - M - h, s + w, DIE_H - M]
        if side == 'bottom':
            return (s, M + h), [s - w, M, s, M + h]
        if side == 'left':
            return (M + h, s), [M, s, M + h, s + w]
        return (DIE_W - M - h, s), [DIE_W - M - h, s - w, DIE_W - M, s]

    PADS, FILL = [], []
    for side, items in P_SIDES.items():
        a, b = SPAN[side]; L = abs(b - a); d = 1 if b > a else -1
        widths = [CELL[c][1] for _, c, _ in items]
        conn = side == 'bottom'
        u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]
        for i in range(1, len(u)):
            u[i] = max(u[i], u[i - 1] + widths[i - 1] + PAD_GAP)
        u[-1] = min(u[-1], int(L) - widths[-1])
        for i in range(len(u) - 2, -1, -1):
            u[i] = min(u[i], u[i + 1] - widths[i] - PAD_GAP)
        assert u[0] >= 0, (tag, side, '패드가 변에 안 들어감', u)
        ends = [0] + [ui + w for ui, w in zip(u, widths)]
        gaps = [ui - e for ui, e in zip(u + [int(L)], ends)]
        n = len(items) + 1
        i_conn = max(range(n), key=lambda i: gaps[i]) if conn else -1
        assert not conn or gaps[i_conn] >= CELL['connect'][1]
        if conn:
            gaps[i_conn] -= CELL['connect'][1]
        s = a
        for i in range(n):
            gg = gaps[i]
            if i == i_conn:
                o, r = place(side, s, CELL['connect'][1], CELL['connect'][2]); FILL.append(dict(cell=CELL['connect'][0], side=side, origin=o, rot=ROT[side], rect=r))
                s += d * CELL['connect'][1]
            for w in (20, 10, 5, 1):
                while gg >= w:
                    o, r = place(side, s, w, 197.965); FILL.append(dict(cell=SLICE[w], side=side, origin=o, rot=ROT[side], rect=r))
                    s += d * w; gg -= w
            if i < len(items):
                nm, c, _ = items[i]; cn, w, h = CELL[c]
                o, r = place(side, s, w, h)
                PADS.append(dict(name=nm, type=ptype(nm, c), io=c, cell=cn, side=side, origin=[round(v, 3) for v in o], rot=ROT[side], rect=[round(v, 3) for v in r]))
                s += d * w
        assert abs(s - b) < 1e-6, (side, s, b)
    CORNERS = [dict(cell=CORNER, at='TR', rot=0, origin=[DIE_W - M - 200, DIE_H - M - 204]), dict(cell=CORNER, at='TL', rot=1, origin=[M + 204, DIE_H - M - 200]),
               dict(cell=CORNER, at='BL', rot=2, origin=[M + 200, M + 204]), dict(cell=CORNER, at='BR', rot=3, origin=[DIE_W - M - 204, M + 200])]
    n_by = {t: sum(p['type'] == t for p in PADS) for t in ('digital', 'analog', 'power', 'spare')}
    assert len(PADS) == 42 and n_by == dict(digital=11, analog=12, power=14, spare=5), n_by
    RING_IN = M + 204 + 10
    RINGS = [dict(net=nn, offset=round(RING_IN + k * 20, 2), width=15.0) for k, nn in enumerate(('VSS', 'VDD', 'VCM', 'VCCD'))]
    fill_ratio = {sd: round(sum(CELL[c][1] for _, c, _ in it) / abs(SPAN[sd][1] - SPAN[sd][0]), 3) for sd, it in P_SIDES.items()}
    J = dict(version=f'재배치 후보 {tag} (10/27, est_blocks 실제 셀 크기, 입력 스위치 W {w_sw} µm, v3 핀)',
             note='블록 크기 = est_blocks.json (실제 셀, DRC·LVS 없음). W 300 입력 구동은 폭 어림 (셀 없음). 좌표 µm. core 원점 = core 왼쪽 아래, 패드·filler 는 die 좌표.',
             iolib='sky130_ef_io / sky130_fd_io (volare sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b), 크기 = LEF',
             rails=dict(VSSA='VSS', VSSIO='VSS', VSSD='VSS', VDDA='VDD', VDDIO='VDD', VCCD='VSS+1.8V', VCCHIB='VCCD', VSWITCH='VDDIO'),
             core=dict(w=round(CORE_W, 2), h=round(CORE_H, 2), offset_in_die=[round(OX, 2), round(OY, 2)]),
             die=dict(w=DIE_W, h=DIE_H, margin=M), corners=CORNERS, pads=PADS, fillers=FILL, core_rings=RINGS, blocks=B,
             pad_count=n_by, side_fill=fill_ratio)
    json.dump(J, open(HERE / f'floorplan_opt_{tag}.json', 'w'), indent=1, ensure_ascii=False)
    return J


def fill_spares(P_SIDES, SPAN):
    """(사용자 10/27 "PAD frame에서 비어있는 패드가 많지 않아? 그냥 다 넣어놔") 변마다 원하는 자리대로 놓은 뒤 남는 틈에 예비 아날로그 패드
    (analog_esd_pad 75 µm) 를 들어가는 만큼 넣는다. 틈 규칙: 패드·모서리 사이 PAD_GAP 15 µm. 아래 변은 이음 slice (20 µm) 자리를 가장 큰 틈에 남김."""
    sw, k_sp, out = CELL[A_][1], 6, {}
    for side, items in P_SIDES.items():
        a, b = SPAN[side]; L = abs(b - a); d = 1 if b > a else -1
        widths = [CELL[c][1] for _, c, _ in items]
        u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]
        for i in range(1, len(u)):
            u[i] = max(u[i], u[i - 1] + widths[i - 1] + PAD_GAP)
        u[-1] = min(u[-1], int(L) - widths[-1])
        for i in range(len(u) - 2, -1, -1):
            u[i] = min(u[i], u[i + 1] - widths[i] - PAD_GAP)
        starts = [0.0] + [ui + w for ui, w in zip(u, widths)]           # 틈 i = starts[i] … ends[i]
        ends = list(u) + [float(L)]
        gaps = [e - s for s, e in zip(starts, ends)]
        if side == 'bottom':                                              # 이음 slice 자리
            j = max(range(len(gaps)), key=lambda i: gaps[i]); gaps[j] -= CELL['connect'][1] + PAD_GAP
        new = []
        for i in range(len(gaps)):
            k = max(0, int((gaps[i] - PAD_GAP) // (sw + PAD_GAP)))
            for q in range(k):                                            # 틈 안에 고르게
                pitch = (gaps[i] - PAD_GAP) / k
                dist = starts[i] + PAD_GAP + q * pitch + sw / 2
                new.append((f'SPARE{k_sp}', A_, a + d * dist)); k_sp += 1
            if i < len(items):
                new.append(items[i])
        # (사용자 10/27 "ESD가 들어가야하는 PAD는 없나? 여유분 생긴만큼 몇개 넣어줘봐") 변마다 새 예비 패드 둘을 VDD·VSS clamp 패드로:
        # 신호 패드 ESD 다이오드 전류가 빠지는 전원 clamp 를 변 가운데에 한 쌍 더 (긴 변의 방전 경로를 반으로). 위·아래 = VDDIO 계열, 좌·우 = VDDA 계열
        # 고르는 기준: 신호 패드 → 가장 가까운 clamp 패드 거리의 최댓값이 가장 작아지게 (새 예비 패드 중 이웃 둘, 없으면 하나)
        vdd, vss = ('vddio', 'vssio') if side in ('top', 'bottom') else ('vdda', 'vssa')
        sig = [cc for nm, c, cc in new if c in (G_, A_) and not nm.startswith('SPARE') and nm != 'VCM']
        clp = [cc for nm, c, cc in new if c not in (G_, A_)]
        sp = [k for k, (nm, _, _) in enumerate(new) if nm.startswith('SPARE') and int(nm[5:]) >= 6]
        worst = lambda extra: max((min(abs(x - y) for y in clp + extra) for x in sig), default=0.0)
        pairs = [(k, k2) for k in sp for k2 in sp if k2 == k + 1]
        if pairs:
            k1, k2 = min(pairs, key=lambda kk: worst([new[kk[0]][2], new[kk[1]][2]]))
            new[k1] = ('VDD', vdd, new[k1][2]); new[k2] = ('VSS', vss, new[k2][2])
        elif sp:
            k1 = min(sp, key=lambda k: worst([new[k][2]]))
            new[k1] = ('VDD', vdd, new[k1][2])
        out[side] = new
    return out


def place_pads(tag, P_SIDES, DIE_W, DIE_H, fill=False):
    """패드 배치 (build 와 같은 규칙). → PADS, FILL, CORNERS, n_by, RINGS, fill_ratio. fill = 남는 틈에 예비 패드"""
    SPAN = {'top': (M + 204, DIE_W - M - 200), 'bottom': (DIE_W - M - 204, M + 200), 'right': (DIE_H - M - 204, M + 200), 'left': (M + 204, DIE_H - M - 200)}
    if fill:
        P_SIDES = fill_spares(P_SIDES, SPAN)

    def place(side, s, w, h):
        if side == 'top':
            return (s, DIE_H - M - h), [s, DIE_H - M - h, s + w, DIE_H - M]
        if side == 'bottom':
            return (s, M + h), [s - w, M, s, M + h]
        if side == 'left':
            return (M + h, s), [M, s, M + h, s + w]
        return (DIE_W - M - h, s), [DIE_W - M - h, s - w, DIE_W - M, s]

    PADS, FILL = [], []
    for side, items in P_SIDES.items():
        a, b = SPAN[side]; L = abs(b - a); d = 1 if b > a else -1
        widths = [CELL[c][1] for _, c, _ in items]
        conn = side == 'bottom'
        u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]
        for i in range(1, len(u)):
            u[i] = max(u[i], u[i - 1] + widths[i - 1] + PAD_GAP)
        u[-1] = min(u[-1], int(L) - widths[-1])
        for i in range(len(u) - 2, -1, -1):
            u[i] = min(u[i], u[i + 1] - widths[i] - PAD_GAP)
        assert u[0] >= 0, (tag, side, '패드가 변에 안 들어감', u)
        ends = [0] + [ui + w for ui, w in zip(u, widths)]
        gaps = [ui - e for ui, e in zip(u + [int(L)], ends)]
        n = len(items) + 1
        i_conn = max(range(n), key=lambda i: gaps[i]) if conn else -1
        assert not conn or gaps[i_conn] >= CELL['connect'][1]
        if conn:
            gaps[i_conn] -= CELL['connect'][1]
        s = a
        for i in range(n):
            gg = gaps[i]
            if i == i_conn:
                o, r = place(side, s, CELL['connect'][1], CELL['connect'][2]); FILL.append(dict(cell=CELL['connect'][0], side=side, origin=o, rot=ROT[side], rect=r))
                s += d * CELL['connect'][1]
            for w in (20, 10, 5, 1):
                while gg >= w:
                    o, r = place(side, s, w, 197.965); FILL.append(dict(cell=SLICE[w], side=side, origin=o, rot=ROT[side], rect=r))
                    s += d * w; gg -= w
            if i < len(items):
                nm, c, _ = items[i]; cn, w, h = CELL[c]
                o, r = place(side, s, w, h)
                PADS.append(dict(name=nm, type=ptype(nm, c), io=c, cell=cn, side=side, origin=[round(v, 3) for v in o], rot=ROT[side], rect=[round(v, 3) for v in r]))
                s += d * w
        assert abs(s - b) < 1e-6, (side, s, b)
    CORNERS = [dict(cell=CORNER, at='TR', rot=0, origin=[DIE_W - M - 200, DIE_H - M - 204]), dict(cell=CORNER, at='TL', rot=1, origin=[M + 204, DIE_H - M - 200]),
               dict(cell=CORNER, at='BL', rot=2, origin=[M + 200, M + 204]), dict(cell=CORNER, at='BR', rot=3, origin=[DIE_W - M - 204, M + 200])]
    n_by = {t: sum(p['type'] == t for p in PADS) for t in ('digital', 'analog', 'power', 'spare')}
    assert n_by['digital'] == 11 and n_by['analog'] == 12 and ((n_by['power'], n_by['spare']) == (14, 5) if not fill else n_by['power'] >= 14), (tag, n_by)
    RING_IN = M + 204 + 10
    RINGS = [dict(net=nn, offset=round(RING_IN + k * 20, 2), width=15.0) for k, nn in enumerate(('VSS', 'VDD', 'VCM', 'VCCD'))]
    fill_ratio = {sd: round(sum(CELL[c][1] for _, c, _ in it) / abs(SPAN[sd][1] - SPAN[sd][0]), 3) for sd, it in P_SIDES.items()}
    return PADS, FILL, CORNERS, n_by, RINGS, fill_ratio


METAL_PLAN = dict(blocks='met1–met3 (블록 안, 생성기는 met4·met5 를 쓰지 않음)',
                  global_signals='met4 (core 둘레 배선 띠·가운데 버스 통로: 동작 decode·레지스터 클록·SDI·감지 버스·V_W·bias)',
                  power='met5 (VDD·VSS 줄을 블록 위로, core 전원 ring 에 이음)')


def build_stacked(tag, w_sw, reshape=False, ch=0.0, wu_inner=False, test=False, ring=0.0, wb2=False, fill_pads=False):
    """사용자 스케치 (10/27 21:54, "decap이 너무 많이 들어가게 되는 구조야. 그러면 이것은 어때"): 두 배열을 위·아래로 쌓고 nudge 반쪽을 180° 돌림.
    위 반쪽 (free, 왼→오) = DATA | 입력 구동 | 배열 | row MUX | row reg. | row decoder, 열 쌓음은 배열 아래.
    아래 반쪽 (nudge) = 위 반쪽을 180° 돌린 것, 열 쌓음은 배열 위 → 두 열 쌓음이 가운데 띠에 나란히 (x 로 안 겹치게 위 반쪽을 오른쪽으로 SH 만큼).
    spine 을 같이 쓸 수 없어 row reg.·decoder·DATA 를 반쪽마다 한 벌 (DATA 는 입력 구동 바로 바깥 = 게이트선이 짧음).
    SH 로 생긴 두 모서리: 위 왼쪽 = 합성 디지털 (세워서), 아래 오른쪽 = bias·nudge 주입기. 가운데 띠 양끝 = WU1 + write buffer + 판독 TG (nudge) / WU2 + 판독 TG (free).
    (d2) 사용자 10/27 "Weight update circuit을 조금 더 중앙 쪽으로 넣고. shift register와 decoder는 어차피 digital이니까 … 상하로 더 길쭉하게 …
         decap이 없도록 최대한 꽉꽉 … 단 metal line이 이어지는 것은 margin을 두긴 해야해":
      reshape  = row reg.·row decoder·DATA 를 면적 그대로 배열 높이 (AH) 로 세움, 순서 row MUX | decoder | reg. (decoder 가 MUX 옆)
      ch       = 가운데 띠 버스 통로 (µm): nudge 열 쌓음 위 + free 열 쌓음 아래 (두 WU 가 두 배열 버스를 다 받음)
      wu_inner = WU1 은 nudge 열 쌓음 바로 왼쪽, WU2 는 free 열 쌓음 바로 오른쪽 (버스 들어올 틈 20 µm)"""
    IDW, IDH = insw_w(w_sw), WH('input_drive')[1]
    AW, AH = max(WH('crossbar')[0], WH('col_strip')[0]), WH('crossbar')[1]
    W_ROWM, H_ROWM = WH('row_mux')
    area = lambda k: WH(k)[0] * WH(k)[1]
    if reshape:                                                    # 디지털 줄 블록: 세운 셀 (est_blocks_d2.py, 채움률 1.0, 높이 ≤ 배열 높이)
        E2 = json.load(open(HERE / 'est_blocks_d2.json'))
        TOK, DEC, DAT = ((E2[k]['w'], E2[k]['h']) for k in ('row_tok_t', 'row_dec_t', 'data_t'))
        CT = ('row_tok_t', 'row_dec_t', 'data_t')
    else:
        TOK, DEC, DAT = WH('row_tok'), WH('row_dec'), WH('data')
        CT = ('row_tok', 'row_dec', 'data')
    W_TOK, W_DEC, W_DAT = TOK[0], DEC[0], DAT[0]
    H_CS, H_CD = WH('col_strip')[1], WH('col_dec')[1]
    H_STK = G + H_CS + g + H_CD                                    # 배열 ↔ 열 MUX 틈 + 열 MUX + 틈 + 열 decoder
    x, XS = 0.0, {}
    spine = (('dec', W_DEC, 10), ('tok', W_TOK, g)) if reshape else (('tok', W_TOK, 10), ('dec', W_DEC, g))
    for k, w, gap in (('data', W_DAT, 0), ('insw', IDW, g), ('arr', AW, GS), ('rowm', W_ROWM, G)) + spine:
        x += gap; XS[k] = (x, x + w); x += w
    HALF_W = x
    SH = max(0.0, HALF_W - 2 * XS['arr'][0] + G)                    # nudge 배열 오른 끝 + G ≤ free 배열 왼 끝
    CORE_W = SH + HALF_W
    A0n = G; A1n = A0n + AH; A0f = A1n + H_STK + ch; A1f = A0f + AH
    CORE_H = A1f + TOPM
    B = []

    def blk(name, kind, cell, x0, y0, w, h, moved=False):
        B.append(dict(name=name, kind=kind, cell='B_' + cell, rect=[round(v, 2) for v in (x0, y0, x0 + w, y0 + h)], moved=moved))

    fx = lambda k: SH + XS[k][0]                                    # 위 반쪽 x (왼 끝)
    nx = lambda k: HALF_W - XS[k][1]                                # 아래 반쪽 x (180° 돌림, 왼 끝)
    idc = 'input_drive' if w_sw == 1000 else f'input_drive_w{w_sw}'
    # 위 반쪽 (free): 위를 A1f 에 맞춤
    blk('free crossbar', 'array', 'crossbar', fx('arr'), A0f, *WH('crossbar'))
    blk('column MUX (free)', 'pitch_col', 'col_strip', fx('arr'), A0f - G - H_CS, *WH('col_strip'))
    blk('COL1/COL2 token (free)', 'pitch_col', 'col_dec', fx('arr'), A0f - G - H_CS - g - H_CD, *WH('col_dec'))
    blk('input drive (free)', 'pitch_row', idc, fx('insw'), A1f - IDH, IDW, IDH, moved=True)
    blk('row MUX + WL (free)', 'pitch_row', 'row_mux', fx('rowm'), A1f - H_ROWM, W_ROWM, H_ROWM, moved=True)
    blk('ROW1/ROW2 token (free)', 'pitch_row', CT[0], fx('tok'), A1f - TOK[1], *TOK, moved=True)
    blk('row decoder (free)', 'pitch_row', CT[1], fx('dec'), A1f - DEC[1], *DEC, moved=True)
    blk('DATA + latch + gate (free)', 'pitch_row', CT[2], fx('data'), A1f - DAT[1], *DAT, moved=True)
    # 아래 반쪽 (nudge, 180° 돌림): 아래를 A0n 에 맞춤, 열 쌓음은 배열 위
    blk('nudge crossbar', 'array', 'crossbar', nx('arr'), A0n, *WH('crossbar'), moved=True)
    blk('column MUX (nudge)', 'pitch_col', 'col_strip', nx('arr'), A1n + G, *WH('col_strip'), moved=True)
    blk('COL1/COL2 token (nudge)', 'pitch_col', 'col_dec', nx('arr'), A1n + G + H_CS + g, *WH('col_dec'), moved=True)
    blk('input drive (nudge)', 'pitch_row', idc, nx('insw'), A0n, IDW, IDH, moved=True)
    blk('row MUX + WL (nudge)', 'pitch_row', 'row_mux', nx('rowm'), A0n, W_ROWM, H_ROWM, moved=True)
    blk('ROW1/ROW2 token (nudge)', 'pitch_row', CT[0], nx('tok'), A0n, *TOK, moved=True)
    blk('row decoder (nudge)', 'pitch_row', CT[1], nx('dec'), A0n, *DEC, moved=True)
    blk('DATA + latch + gate (nudge)', 'pitch_row', CT[2], nx('data'), A0n, *DAT, moved=True)
    if ch:                                                         # 버스 통로 (계단꼴): nudge 열 쌓음 위 + 두 쌓음 사이 틈 + free 열 쌓음 아래
        blk('bus channel (nudge side)', 'route', 'none', nx('arr'), A1n + H_STK, AW, ch)
        blk('bus channel (middle)', 'route', 'none', nx('arr') + AW, A1n, fx('arr') - nx('arr') - AW, H_STK + ch)
        blk('bus channel (free side)', 'route', 'none', fx('arr'), A1n, AW, ch)
    # 가운데 띠 (y A1n … A0f)
    yb = A1n + (H_STK + ch - WH('wu1')[1]) / 2
    if wu_inner:                                                   # WU 를 열 쌓음 바로 옆으로 (버스 들어올 틈 20 µm), 판독 TG 는 띠 끝 (row MUX 쪽)
        GB = 20.0
        xr1 = nx('arr') - GB
        blk('WU1', 'analog', 'wu1', xr1 - WH('wu1')[0], yb, *WH('wu1'), moved=True)
        blk('write buffer (nudge)' if wb2 else 'write buffer', 'analog', 'write_buffer', xr1 - WH('wu1')[0] - G - WH('write_buffer')[0], yb,
            *WH('write_buffer'), moved=True)                         # wb2: 배열마다 하나 (nudge 쪽 = nudge row MUX 가까이)
        x_wb = xr1 - WH('wu1')[0] - G - WH('write_buffer')[0]
        x_tgn = x_wb - G - WH('readout_tg_n')[0] if test else 0.0  # test 영역이 있으면 판독 TG 를 write buffer 옆으로 (띠 끝을 test 영역에)
        blk('readout TG (nudge)', 'analog', 'readout_tg_n', x_tgn, yb, *WH('readout_tg_n'), moved=True)
        assert WH('readout_tg_n')[0] + G <= x_wb, '가운데 띠 왼쪽이 모자람'
        xl2 = fx('arr') + AW + GB
        blk('WU2', 'analog', 'wu2', xl2, yb, *WH('wu2'), moved=True)
        x_after = xl2 + WH('wu2')[0] + G
        if wb2:                                                    # free 쪽 write buffer = WU2 옆 (free row MUX 바로 아래)
            blk('write buffer (free)', 'analog', 'write_buffer', x_after, yb, *WH('write_buffer'), moved=True)
            x_after += WH('write_buffer')[0] + G
        x_tgf = x_after if test else CORE_W - WH('readout_tg_f')[0]
        blk('readout TG (free)', 'analog', 'readout_tg_f', x_tgf, yb, *WH('readout_tg_f'), moved=True)
        assert xl2 + WH('wu2')[0] + G <= CORE_W - WH('readout_tg_f')[0], '가운데 띠 오른쪽이 모자람'
        if test:                                                   # 띠 양 끝 test 영역 (사용자 10/27 "test pattern 넣어서 decap이 최대한 없게")
            blk('test area (band left)', 'test', 'tp_bandl', 0.0, A1n + g, x_tgn - G, H_STK + ch - g - G)
            blk('test area (band right)', 'test', 'tp_bandr', x_tgf + WH('readout_tg_f')[0] + G, A1n + G,
                CORE_W - x_tgf - WH('readout_tg_f')[0] - G, H_STK + ch - g - G)
    else:                                                          # (d): 왼쪽 끝 = 판독 TG (nudge) + WU1 + write buffer, 오른쪽 끝 = WU2 + 판독 TG (free)
        xl = 0.0
        blk('readout TG (nudge)', 'analog', 'readout_tg_n', xl, yb, *WH('readout_tg_n'), moved=True); xl += WH('readout_tg_n')[0] + G
        blk('WU1', 'analog', 'wu1', xl, yb, *WH('wu1'), moved=True); xl += WH('wu1')[0] + G
        blk('write buffer', 'analog', 'write_buffer', xl, yb, *WH('write_buffer'), moved=True); xl += WH('write_buffer')[0]
        assert xl + G <= nx('arr'), ('가운데 띠 왼쪽이 모자람', xl, nx('arr'))
        xr = CORE_W
        xr -= WH('readout_tg_f')[0]; blk('readout TG (free)', 'analog', 'readout_tg_f', xr, yb, *WH('readout_tg_f'), moved=True)
        xr -= G + WH('wu2')[0]; blk('WU2', 'analog', 'wu2', xr, yb, *WH('wu2'), moved=True)
        assert xr - G >= fx('arr') + AW, ('가운데 띠 오른쪽이 모자람', xr)
    # 위 왼쪽 모서리 (x 0 … SH): 합성 디지털 (세움). 아래 오른쪽 모서리 (x HALF_W … CORE_W): bias·nudge 주입기
    d5w, d5h = WH('global_digital_5v'); d1w, d1h = WH('global_digital_1v8')
    if SH >= d5h + g + d1h:                                         # 세워서 (폭 ↔ 높이)
        blk('global digital (5 V)', 'digital', 'global_digital_5v', 0, A1f - d5w, d5h, d5w, moved=True)
        blk('global digital (1.8 V)', 'digital', 'global_digital_1v8', d5h + g, A1f - d1w, d1h, d1w, moved=True)
    else:
        raise AssertionError(('위 왼쪽 모서리에 디지털이 안 들어감', SH))
    blk('bias', 'analog', 'bias', HALF_W + G, A0n, *WH('bias'), moved=True)
    blk('nudge injector', 'analog', 'nudge_injector', HALF_W + G, A0n + WH('bias')[1] + G, *WH('nudge_injector'), moved=True)
    assert HALF_W + G + WH('nudge_injector')[0] <= CORE_W, ('아래 오른쪽 모서리가 모자람', CORE_W - HALF_W)
    if test:                                                       # 사용자 10/27 "test 영역이라고 그려놓고" — 패드 연결 없음, 자리만 (decap 안 채움)
        blk('test area (top-left)', 'test', 'tp_tl', 0.0, A0f, SH - G, A1f - d5w - G - A0f)
        y_t = A0n + WH('bias')[1] + G + WH('nudge_injector')[1] + G
        blk('test area (bottom-right)', 'test', 'tp_br', HALF_W + G, y_t, CORE_W - HALF_W - G, A1n - y_t)
    if ring:                                                       # (d3) 사용자 10/27 "1, 2번 반영해서 다시 그려봐": core 둘레 배선 띠 (met4 전역 신호)
        dx, dy = ring, ring - A0n                                  # 블록을 띠 안쪽으로 (아래 여백 A0n → ring, 위 여백 TOPM → ring)
        for b in B:
            r = b['rect']; b['rect'] = [round(r[0] + dx, 2), round(r[1] + dy, 2), round(r[2] + dx, 2), round(r[3] + dy, 2)]
        CORE_W = CORE_W + 2 * ring
        CORE_H = A1f + dy + ring
        for nm, r in (('routing ring (bottom)', (0, 0, CORE_W, ring)), ('routing ring (top)', (0, CORE_H - ring, CORE_W, CORE_H)),
                      ('routing ring (left)', (0, ring, ring, CORE_H - ring)), ('routing ring (right)', (CORE_W - ring, ring, CORE_W, CORE_H - ring))):
            B.append(dict(name=nm, kind='route', cell='B_none', rect=[round(v, 2) for v in r], moved=True))

    DIE_W, DIE_H = up10(CORE_W + 2 * (RING_OUT + 10)), up10(CORE_H + 2 * (RING_OUT + 10))
    OX, OY = (DIE_W - CORE_W) / 2, (DIE_H - CORE_H) / 2
    BD = {b['name']: [OX + b['rect'][0], OY + b['rect'][1], OX + b['rect'][2], OY + b['rect'][3]] for b in B}
    cx = lambda n: (BD[n][0] + BD[n][2]) / 2
    cy = lambda n: (BD[n][1] + BD[n][3]) / 2
    xf, xnn = cx('input drive (free)'), cx('input drive (nudge)')
    yd, ybd = cy('global digital (5 V)'), cy('WU1')
    xd = cx('global digital (5 V)')
    P_SIDES = {   # 위 = 왼→오, 오른 = 위→아래, 아래 = 오른→왼, 왼 = 아래→위 (원하는 중심 = 이어지는 블록 자리)
        'top': [('VSSL', 'vssd', xd - 120), ('VDDL', 'vccd', xd - 40), ('SCK', G_, xd + 40), ('SDI', G_, xd + 120), ('SLD', G_, xd + 200),
                ('RST', G_, xd + 280), ('SEL_EN', G_, xd + 360), ('WP', G_, xd + 440), ('VRAILP', A_, xf + 120), ('VRAILM', A_, xf + 200),
                ('VDD', 'vdda', OX + CORE_W / 2 + 200), ('VSS', 'vssa', OX + CORE_W / 2 + 280), ('VCM', A_, OX + CORE_W / 2 + 360)],
        'right': [('VDD', 'vddio', cy('row decoder (free)') + 60), ('VSS', 'vssio', cy('row decoder (free)') - 30), ('SPARE4', A_, cy('row decoder (free)') - 120),
                  ('VBUS_F', A_, cy('readout TG (free)')), ('IBIAS', A_, cy('nudge injector') + 40), ('VBNC', A_, cy('bias')), ('VBPC', A_, cy('bias') - 80)],
        'bottom': [('VRAILM', A_, xnn + 40), ('VRAILP', A_, xnn - 40), ('VCM', A_, OX + CORE_W / 2 - 200), ('VSS', 'vssa', OX + CORE_W / 2 - 280),
                   ('VDD', 'vdda', OX + CORE_W / 2 - 360), ('SPARE1', A_, OX + 300), ('SPARE2', A_, OX + 220), ('SPARE3', A_, OX + 140), ('SPARE5', A_, OX + 60)],
        'left': [('VSS', 'vssio', cy('row decoder (nudge)') - 40), ('VDD', 'vddio', cy('row decoder (nudge)') + 40), ('VBUS_N', A_, ybd - 120),
                 ('VWL', A_, ybd - 40), ('VWLO', A_, ybd + 40), ('VWH', A_, ybd + 120), ('VSSL', 'vssd', yd - 200), ('VDDL', 'vccd', yd - 120),
                 ('LQ1', G_, yd - 40), ('LQ2', G_, yd + 40), ('CK', G_, yd + 120), ('CK3', G_, yd + 200), ('LAT', G_, yd + 280)]}
    PADS, FILL, CORNERS, n_by, RINGS, fill_ratio = place_pads(tag, P_SIDES, DIE_W, DIE_H, fill=fill_pads)
    J = dict(version=f'재배치 후보 {tag} (10/27, 사용자 스케치: 위·아래로 쌓고 nudge 180° 돌림, est_blocks 실제 셀 크기, 입력 스위치 W {w_sw} µm, v3 핀)',
             note='블록 크기 = est_blocks.json (실제 셀, DRC·LVS 없음). row reg.·decoder·DATA 는 반쪽마다 한 벌. 좌표 µm. core 원점 = core 왼쪽 아래, 패드·filler 는 die 좌표.',
             iolib='sky130_ef_io / sky130_fd_io (volare sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b), 크기 = LEF',
             rails=dict(VSSA='VSS', VSSIO='VSS', VSSD='VSS', VDDA='VDD', VDDIO='VDD', VCCD='VSS+1.8V', VCCHIB='VCCD', VSWITCH='VDDIO'),
             core=dict(w=round(CORE_W, 2), h=round(CORE_H, 2), offset_in_die=[round(OX, 2), round(OY, 2)]),
             die=dict(w=DIE_W, h=DIE_H, margin=M), corners=CORNERS, pads=PADS, fillers=FILL, core_rings=RINGS, blocks=B,
             pad_count=n_by, side_fill=fill_ratio, shift=round(SH, 2), routing_ring=ring, metal_plan=METAL_PLAN if ring else None)
    json.dump(J, open(HERE / f'floorplan_opt_{tag}.json', 'w'), indent=1, ensure_ascii=False)
    return J


# ── 그림: 지금 / A / B 를 같은 축척으로
FILLC = dict(array='#DCE3F0', pitch_row='#E4E6EE', pitch_col='#E4E6EE', analog='#E6DDF0', digital='#D3DCEA')
PADC = dict(power='#500000', digital='#1F3A68', analog='#5B4A8B', spare='#9AA0A6')
LABEL = {'free crossbar': 'free crossbar\n128 × 64 1T1R', 'nudge crossbar': 'nudge crossbar\n128 × 64 1T1R',
         'column MUX (free)': 'column MUX + diodes', 'column MUX (nudge)': 'column MUX + diodes',
         'COL1/COL2 token (free)': 'col. decoder + shift reg.', 'COL1/COL2 token (nudge)': 'col. decoder + shift reg.',
         'row MUX + WL (free)': 'row MUX + WL', 'row MUX + WL (nudge)': 'row MUX + WL', 'ROW1/ROW2 token': 'row reg.',
         'row decoder (shared)': 'row decoder', 'DATA + latch + gate': 'DATA', 'WU1': 'WU1', 'WU2': 'WU2',
         'row decoder': 'row decoder', 'ROW1/ROW2 token (free)': 'row reg.', 'ROW1/ROW2 token (nudge)': 'row reg.',
         'row decoder (free)': 'row decoder', 'row decoder (nudge)': 'row decoder',
         'DATA + latch + gate (free)': 'DATA', 'DATA + latch + gate (nudge)': 'DATA'}
SMALL = {'write buffer': 'write buffer', 'readout TG (free)': 'readout TG', 'readout TG (nudge)': 'readout TG', 'bias': 'bias',
         'nudge injector': 'nudge injector', 'global digital (5 V)': 'digital control', 'global digital (1.8 V)': None}


def draw(ax, J, title, w_sw, mark_moved):
    W, H = J['die']['w'], J['die']['h']
    ox, oy = J['core']['offset_in_die']
    cw, ch = J['core']['w'], J['core']['h']
    ax.add_patch(Rectangle((0, 0), W, H, fc='white', ec='black', lw=1.2))
    ax.add_patch(Rectangle((M, M), W - 2 * M, H - 2 * M, fc='#EDEDED', ec='none'))           # IO ring 띠
    ax.add_patch(Rectangle((M + 204, M + 204), W - 2 * (M + 204), H - 2 * (M + 204), fc='white', ec='none'))
    for c in J['corners']:
        x0, y0 = c['origin']
        r = {'TR': (x0, y0, 200, 204), 'TL': (x0 - 204, y0, 204, 200), 'BL': (x0 - 200, y0 - 204, 200, 204), 'BR': (x0, y0 - 200, 204, 200)}[c['at']]
        ax.add_patch(Rectangle(r[:2], r[2], r[3], fc='#C9C9C9', ec='#777777', lw=0.4))
    for p in J['pads']:
        x0, y0, x1, y1 = p['rect']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='white', ec=PADC[p['type']], lw=0.9))
        rot = 90 if p['side'] in ('top', 'bottom') else 0
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, p['name'], rotation=rot, ha='center', va='center', fontsize=3.6, color=PADC[p['type']])
    for rg in J['core_rings']:
        o = rg['offset']
        ax.add_patch(Rectangle((o, o), W - 2 * o, H - 2 * o, fc='none', ec='#B8B8B8', lw=0.3))
    ax.add_patch(Rectangle((ox, oy), cw, ch, fc='#EEF2E6', ec='#555555', lw=0.8, ls='--'))   # 빈 곳 = decap
    area, r_area = 0.0, 0.0
    for b in J['blocks']:
        x0, y0, x1, y1 = b['rect']; x0, x1, y0, y1 = x0 + ox, x1 + ox, y0 + oy, y1 + oy
        if b['kind'] == 'route':                                      # 버스 통로 (금속 선 자리) — decap 과 따로 셈
            r_area += (x1 - x0) * (y1 - y0)
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='white', ec='#7A8494', lw=0.4, hatch='////'))
            continue
        if b['kind'] == 'test':                                       # test 영역 (자리만)
            r_area += (x1 - x0) * (y1 - y0)
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='white', ec='#500000', lw=0.8, ls='--'))
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, 'test area', rotation=90, ha='center', va='center', fontsize=5, color='#500000')
            continue
        area += (x1 - x0) * (y1 - y0)
        moved = mark_moved and b.get('moved')
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=FILLC[b['kind']], ec='#500000' if moved else '#555555', lw=1.6 if moved else 0.6))
        nm = b['name']
        if nm.startswith('input drive'):
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, f'input\ndrive\nNMOS 2:1\nW {w_sw:,} µm', ha='center', va='center', fontsize=6.5 if x1 - x0 > 300 else 5, weight='bold')
        elif nm == 'nudge injector':                                  # bias 와 헷갈리지 않게 왼쪽에
            ax.annotate(SMALL[nm], xy=(x0, (y0 + y1) / 2), xytext=(x0 - 40, (y0 + y1) / 2), ha='right', va='center', fontsize=4.8,
                        arrowprops=dict(arrowstyle='-', lw=0.4, color='#333333'))
        elif nm in LABEL:
            rot = 90 if (b['kind'] == 'pitch_row' and 'crossbar' not in nm) else 0
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, LABEL[nm], ha='center', va='center', fontsize=6 if 'crossbar' in nm else 5, rotation=rot,
                    weight='bold' if 'crossbar' in nm or nm.startswith('WU') else 'normal')
        elif SMALL.get(nm):
            ax.annotate(SMALL[nm], xy=((x0 + x1) / 2, (y0 + y1) / 2), xytext=((x0 + x1) / 2, y0 - 150 if y0 - oy < 150 else y0 - 60),
                        ha='center', va='top', fontsize=4.8, arrowprops=dict(arrowstyle='-', lw=0.4, color='#333333'))
    decap = 1 - (area + r_area) / (cw * ch)
    rt = f', bus channel {r_area / (cw * ch) * 100:.0f} %' if r_area else ''
    ax.set_title(f'{title}\ndie {W / 1000:.2f} × {H / 1000:.2f} mm ({W * H / 1e6:.2f} mm²), core {cw / 1000:.2f} × {ch / 1000:.2f} mm, '
                 f'core left for decap {decap * 100:.0f} %{rt}', fontsize=8, loc='left')
    ax.set_xlim(-20, 2850); ax.set_ylim(-20, H + 20); ax.set_aspect('equal'); ax.axis('off')
    return dict(die=(W, H), core=(cw, ch), decap=decap)


if __name__ == '__main__':
    now = json.load(open(HERE / 'floorplan_est.json'))
    A = build('A', 1000)
    Bj = build('B', 300)
    hs = [now['die']['h'], A['die']['h'], Bj['die']['h']]
    fig, axs = plt.subplots(3, 1, figsize=(10, 10 * sum(hs) / 2850 + 1.2), gridspec_kw=dict(height_ratios=hs))
    st = [draw(axs[0], now, '(a) Now: estimate with real cells (input switch W 1,000 µm)', 1000, False),
          draw(axs[1], A, '(b) Small blocks moved under the row spine, bottom band removed (W 1,000 µm)', 1000, True),
          draw(axs[2], Bj, '(c) Same as (b) with input switch W 300 µm', 300, True)]
    fig.text(0.01, 0.005, 'Block sizes: est_blocks (real cells, no DRC / LVS). The W 300 µm input drive width is scaled from the W 1,000 µm block. '
             'Maroon outline = block moved or resized. Light green = core area left for decoupling capacitors.', fontsize=6)
    fig.tight_layout(rect=(0, 0.015, 1, 1))
    (HERE / 'out').mkdir(exist_ok=True)
    fig.savefig(HERE / 'out' / 'floorplan_opt_compare.png', dpi=300)
    for t, s in zip(('now', 'A', 'B'), st):
        print(t, f"die {s['die'][0]:.0f} × {s['die'][1]:.0f} ({s['die'][0] * s['die'][1] / 1e6:.2f} mm²), core {s['core'][0]:.0f} × {s['core'][1]:.0f}, decap {s['decap'] * 100:.0f} %")
    # 그림 2: 사용자 스케치 (위·아래로 쌓기) — 지금 / D (W 1,000) / E (W 300)
    D = build_stacked('D', 1000)
    Ej = build_stacked('E', 300)
    hs = [now['die']['h'], D['die']['h'], Ej['die']['h']]
    fig, axs = plt.subplots(3, 1, figsize=(10, 10 * sum(hs) / 2850 + 1.2), gridspec_kw=dict(height_ratios=hs))
    st = [draw(axs[0], now, '(a) Now: estimate with real cells (input switch W 1,000 µm)', 1000, False),
          draw(axs[1], D, '(d) Stacked: nudge half rotated 180° under the free half (W 1,000 µm)', 1000, True),
          draw(axs[2], Ej, '(e) Same as (d) with input switch W 300 µm', 300, True)]
    for ax, J in zip(axs[1:], (D, Ej)):                             # 아래 반쪽이 돌았다는 표시
        ox, oy = J['core']['offset_in_die']
        r = next(b['rect'] for b in J['blocks'] if b['name'] == 'nudge crossbar')
        ax.text(ox + (r[0] + r[2]) / 2, oy + r[1] + 60, '(rotated 180°)', ha='center', fontsize=5, color='#500000')
    fig.text(0.01, 0.005, 'Block sizes: est_blocks (real cells, no DRC / LVS). Row registers, row decoder and DATA are duplicated per half in (d) and (e). '
             'Maroon outline = block moved, duplicated or resized. Light green = core area left for decoupling capacitors.', fontsize=6)
    fig.tight_layout(rect=(0, 0.015, 1, 1))
    fig.savefig(HERE / 'out' / 'floorplan_opt_stacked.png', dpi=300)
    for t, s, J in zip(('now', 'D', 'E'), st, (now, D, Ej)):
        print(t, f"die {s['die'][0]:.0f} × {s['die'][1]:.0f} ({s['die'][0] * s['die'][1] / 1e6:.2f} mm²), core {s['core'][0]:.0f} × {s['core'][1]:.0f}, "
              f"decap {s['decap'] * 100:.0f} %, shift {J.get('shift', '-')}")
    # 그림 3: (d) 와 (d2) — 사용자 10/27 피드백 (WU 를 가운데 쪽으로, 디지털 줄 블록 세움, 버스 통로, 빈 곳 최소)
    D2 = build_stacked('D2', 1000, reshape=True, ch=30.0, wu_inner=True, test=True)
    D3 = build_stacked('D3', 1000, reshape=True, ch=30.0, wu_inner=True, test=True, ring=30.0, wb2=True, fill_pads=True)   # 10/27 write buffer 배열마다
    print('D3 pads', len(D3['pads']), D3['pad_count'], D3['side_fill'])
    print('D3', f"die {D3['die']['w']:.0f} × {D3['die']['h']:.0f} ({D3['die']['w'] * D3['die']['h'] / 1e6:.2f} mm²), core {D3['core']['w']:.0f} × {D3['core']['h']:.0f}")
    for b in D2['blocks']:
        if b['kind'] == 'test':
            r = b['rect']; print(b['name'], f'{r[2] - r[0]:.1f} × {r[3] - r[1]:.1f} µm')
    hs = [D['die']['h'], D2['die']['h']]
    fig, axs = plt.subplots(1, 2, figsize=(16, 16 * max(hs) / (2 * 2000) + 1.0))
    st = [draw(axs[0], D, '(d) Stacked, as shown before', 1000, False),
          draw(axs[1], D2, '(d2) WU next to the column blocks, row reg. / decoder / DATA\nreshaped to the array height, 30 µm bus channel', 1000, True)]
    for ax in axs:
        ax.set_xlim(-20, 2000)
    fig.text(0.01, 0.005, 'Block sizes: est_blocks (real cells). Reshaped digital blocks keep their area. Hatched = bus channel (metal lines from both arrays to WU1 and WU2). '
             'Light green = core area left for decoupling capacitors. Gaps where lines connect (array to MUX, array to column blocks) are kept.', fontsize=6)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(HERE / 'out' / 'floorplan_opt_d2.png', dpi=300)
    for t, s, J in zip(('D', 'D2'), st, (D, D2)):
        print(t, f"die {s['die'][0]:.0f} × {s['die'][1]:.0f} ({s['die'][0] * s['die'][1] / 1e6:.2f} mm²), core {s['core'][0]:.0f} × {s['core'][1]:.0f}, "
              f"decap {s['decap'] * 100:.0f} %, shift {J.get('shift', '-')}")
