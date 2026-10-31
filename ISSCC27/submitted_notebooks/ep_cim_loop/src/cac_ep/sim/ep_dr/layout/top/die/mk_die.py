"""die: pad frame (place/die_real.gds) + r6 chip core (route/chip_core.gds) + 패드 ↔ core 배선.
사용자 (10/28): "하는 김에 패드까지 연결하면 작업을 하고", "패드끼리 자리를 바꿔 가지고 조금 더 레이아웃 편하게 해도 돼".
규칙: r6 core 는 그대로 (core 변의 핀·전원 토막 자리 고정). pad frame 의 셀 종류·자리 그대로, 같은 셀 종류끼리만 넷을 바꿈.
낸다 (die/): chip_die.gds (top chip_die, DRC 용 = 실제 IO 셀), pad_map.json·pad_map.md, wire_report.txt
       (OUT2/): chip_frame.gds (frame 만, 자리표시 ring 뺀 판 = DRC 비교용), chip_die_lvs.gds (LVS 용: IO 셀 대신 LEF 핀 도형 + 이름표)
쓰임: <klayout python> mk_die.py [OUT2 폴더]
"""
import json
import sys
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent                      # layout/top/die
TOP = H.parent
sys.path.insert(0, str(TOP / 'route'))
import routelib as R  # noqa: E402  (읽기만: LEF 읽개)

OUT2 = Path(sys.argv[1]) if len(sys.argv) > 1 else H
DJ = json.load(open(TOP / 'place' / 'die_real.json'))
OX, OY = DJ['core']['offset_in_die']; CW, CH = DJ['core']['w'], DJ['core']['h']
IOLEF = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_io/lef/sky130_ef_io.lef'
M = R.parse_lef(str(IOLEF))
DBU = 0.001
LAY = {'met1': (68, 20), 'met2': (69, 20), 'met3': (70, 20), 'met4': (71, 20), 'met5': (72, 20),
       'via1': (68, 44), 'via2': (69, 44), 'via3': (70, 44), 'via4': (71, 44)}
LBL = {'met1': (68, 5), 'met2': (69, 5), 'met3': (70, 5), 'met4': (71, 5), 'met5': (72, 5)}
# via: 크기, 간격 (규칙보다 조금 넉넉히), 배열을 넣을 때 금속 상자에서 안쪽으로 줄이는 값
VIA = {'via1': (0.15, 0.25, 0.10), 'via2': (0.20, 0.30, 0.10), 'via3': (0.20, 0.30, 0.10), 'via4': (0.80, 1.00, 0.35)}


def sn(x):                                               # 0.005 µm 격자
    return round(round(x / 0.005) * 0.005, 3)


# ── 변 좌표: u = 변을 따라 (die x 또는 y), v = 패드 core 쪽 끝에서 core 쪽으로 잰 거리
EDGE = {'N': 1580.0, 'S': 230.0, 'W': 230.0, 'E': 1790.0}
CORE_EDGE = {'N': OY + CH, 'S': OY, 'W': OX, 'E': OX + CW}
G = {s: abs(EDGE[s] - CORE_EDGE[s]) for s in EDGE}       # 패드 ↔ core 틈


def box(s, u1, v1, u2, v2):
    u1, u2 = sorted((u1, u2)); v1, v2 = sorted((v1, v2))
    if s == 'N':
        b = (u1, EDGE[s] - v2, u2, EDGE[s] - v1)
    elif s == 'S':
        b = (u1, EDGE[s] + v1, u2, EDGE[s] + v2)
    elif s == 'W':
        b = (EDGE[s] + v1, u1, EDGE[s] + v2, u2)
    else:
        b = (EDGE[s] - v2, u1, EDGE[s] - v1, u2)
    return db.DBox(*[sn(x) for x in b])


def touv(s, b):                                          # die DBox → (u1, v1, u2, v2)
    if s == 'N':
        return (b.left, EDGE[s] - b.top, b.right, EDGE[s] - b.bottom)
    if s == 'S':
        return (b.left, b.bottom - EDGE[s], b.right, b.top - EDGE[s])
    if s == 'W':
        return (b.bottom, b.left - EDGE[s], b.top, b.right - EDGE[s])
    return (b.bottom, EDGE[s] - b.right, b.top, EDGE[s] - b.left)


SH = {k: db.Region() for k in LAY}                       # 배선 도형 (die 좌표, dbu)
LABELS = []                                              # (layer, text, x, y) — LVS 판 이름표
ABSTRACT = {k: db.Region() for k in LAY if k.startswith('met')}   # LVS 판 패드 핀 도형
REPORT = []


def add(layer, s, u1, v1, u2, v2):
    SH[layer].insert(box(s, u1, v1, u2, v2).to_itype(DBU))


def via_arr(cut, s, u1, v1, u2, v2):
    a, sp, sh = VIA[cut]
    b = box(s, u1, v1, u2, v2)
    x1, y1, x2, y2 = b.left + sh, b.bottom + sh, b.right - sh, b.top - sh
    nx = int((x2 - x1 + sp) // (a + sp)); ny = int((y2 - y1 + sp) // (a + sp))
    if nx < 1 or ny < 1:
        raise SystemExit(f'via {cut} 자리 없음 {s} {u1, v1, u2, v2}')
    ox = x1 + ((x2 - x1) - (nx * a + (nx - 1) * sp)) / 2; oy = y1 + ((y2 - y1) - (ny * a + (ny - 1) * sp)) / 2
    n = 0
    for i in range(nx):
        for j in range(ny):
            x = sn(ox + i * (a + sp)); y = sn(oy + j * (a + sp))
            SH[cut].insert(db.DBox(x, y, sn(x + a), sn(y + a)).to_itype(DBU)); n += 1
    return n


def via1(s, uc, vc):                                     # via1 하나 + met2·met1 덧대기 (0.32 µm 정사각)
    uc, vc = sn(uc), sn(vc)
    add('via1', s, uc - 0.075, vc - 0.075, uc + 0.075, vc + 0.075)
    add('met2', s, uc - 0.16, vc - 0.16, uc + 0.16, vc + 0.16)
    add('met1', s, uc - 0.16, vc - 0.16, uc + 0.16, vc + 0.16)


def via2(s, uc, vc, w2):                                 # via2 하나: met2 (폭 w2) 위 met3 0.4 µm pad
    uc, vc = sn(uc), sn(vc)
    add('via2', s, uc - 0.1, vc - 0.1, uc + 0.1, vc + 0.1)
    add('met3', s, uc - 0.2, vc - 0.2, uc + 0.2, vc + 0.2)
    add('met2', s, uc - w2 / 2, vc - 0.2, uc + w2 / 2, vc + 0.2)


# ── 패드 자리: die_real.gds 의 실제 인스턴스 변환 (mk_padmap 과 같은 짝짓기)
fr = db.Layout(); fr.read(str(TOP / 'place' / 'die_real.gds'))
FT = fr.top_cells()[0]
TR = []
for inst in FT.each_inst():
    c = fr.cell(inst.cell_index).name
    if c.startswith('sky130_ef_io__') and '_pad' in c and 'corner' not in c:
        TR.append((c, inst.dcplx_trans))
SIDE = {'top': 'N', 'bottom': 'S', 'left': 'W', 'right': 'E'}


def pin_uv(slot, pin, layers=('met1', 'met2', 'met3')):
    m = M[slot['cell']]; t = slot['t']; out = []
    for l, r in m.pins[pin]:
        if l not in layers:
            continue
        b = t * db.DBox(r[0] / 1000, r[1] / 1000, r[2] / 1000, r[3] / 1000)
        out.append((l, b, touv(slot['side'], b)))
    return out


def edge_pin(slot, pin, layers=('met1', 'met2', 'met3')):   # core 쪽 끝 조각 (v 가 가장 큰 것)
    return max(pin_uv(slot, pin, layers), key=lambda q: q[2][3])


slots = []
for k, p in enumerate(DJ['pads']):
    rr = p['rect']; t = None
    for c, tt in TR:
        if c != p['cell']:
            continue
        b = tt * db.DBox(0, 0, M[c].size[0] / 1000, M[c].size[1] / 1000)
        if abs(b.left - rr[0]) < 0.5 and abs(b.bottom - rr[1]) < 0.5 and abs(b.right - rr[2]) < 0.5 and abs(b.top - rr[3]) < 0.5:
            t = tt
    assert t is not None, (k, p)
    slots.append(dict(idx=k, old=p['name'], net=p['name'], cell=p['cell'], side=SIDE[p['side']], t=t, rect=rr))

# ── 새 배정. r6 core 의 변 핀·전원 토막은 지금 패드 자리 위에 그려져 있어 그대로 두는 것이 가장 짧다.
#    바꾼 것: IBIASP (core 아래 변 x 1157.65 = die 1494.35) 를 가장 가까운 예비 아날로그 패드 slot 32 (SPARE18, 12 µm) 에.
#    (d3 때 SPARE17 에서 이름을 바꾼 넷이지만 die_real 에는 IBIASP 패드가 없었음 → 지금 SPARE17 은 120 µm 떨어짐)
MOVE = {32: 'IBIASP'}
for s in slots:
    if s['idx'] in MOVE:
        s['net'] = MOVE[s['idx']]
    if s['net'].startswith('SPARE'):
        s['net'] = ''

# ── core 변 핀 (r6 DEF PINS, core 좌표 → die)
DEFP = {}
txt = open(TOP / 'route' / 'chip_core_routed.def').read()
blk = txt[txt.index('\nPINS'):txt.index('END PINS')]
for ent in blk.split(';'):
    tk = ent.split()
    if '-' in tk and 'LAYER' in tk and 'SPECIAL' not in tk:
        nm = tk[tk.index('-') + 1]; i = tk.index('LAYER')
        lay = tk[i + 1]; x1, y1, x2, y2 = (int(tk[i + 3]) / 1000, int(tk[i + 4]) / 1000, int(tk[i + 7]) / 1000, int(tk[i + 8]) / 1000)
        DEFP[nm] = (lay, db.DBox(x1 + OX, y1 + OY, x2 + OX, y2 + OY))
# 전원·넓은 넷 토막 (core 변에 닿은 met4/met5, r6 GDS 에서 읽은 것 — README §표). core 좌표 (변, 층, lo, hi)
STUB = {
    'VDD': [('N', 'met4', 860.65, 868.65), ('N', 'met4', 1130.65, 1138.65), ('S', 'met4', 286.65, 294.65), ('S', 'met4', 750.65, 758.65),
            ('W', 'met5', 36.0, 44.0), ('W', 'met5', 164.94, 172.94), ('E', 'met5', 324.94, 332.94), ('E', 'met5', 923.94, 931.94)],
    'VSS': [('N', 'met4', 950.65, 958.65), ('N', 'met4', 1232.65, 1240.65), ('S', 'met4', 376.65, 384.65), ('S', 'met4', 655.65, 663.65),
            ('W', 'met5', 74.94, 82.94), ('E', 'met5', 232.94, 240.94), ('E', 'met5', 833.94, 841.94)],
    'VCM': [('N', 'met4', 1043.0, 1047.0), ('S', 'met4', 327.0, 331.0)],
    'VRAILP': [('N', 'met5', 678.15, 691.15), ('S', 'met5', 838.15, 851.15)],
    'VRAILM': [('N', 'met5', 768.15, 781.15), ('S', 'met5', 928.15, 941.15)],
    'VWLO': [('W', 'met5', 428.94, 509.825)], 'VWH': [('W', 'met5', 518.94, 699.315)],
}
SHIFT = {'N': OX, 'S': OX, 'W': OY, 'E': OY}


def stubs(net, side):
    return [(l, a + SHIFT[s], b + SHIFT[s]) for s, l, a, b in STUB.get(net, []) if s == side]


RAIL = {'sky130_ef_io__vdda_hvc_clamped_pad': 'VDDA', 'sky130_ef_io__vddio_hvc_clamped_pad': 'VDDIO',
        'sky130_ef_io__vssa_hvc_clamped_pad': 'VSSA', 'sky130_ef_io__vssio_hvc_clamped_pad': 'VSSIO',
        'sky130_ef_io__vccd_lvc_clamped_pad': 'VCCD', 'sky130_ef_io__vssd_lvc_clamped_pad': 'VSSD'}


def fingers(s):
    return [(l, b, uv) for l, b, uv in pin_uv(s, RAIL[s['cell']], ('met3',)) if uv[3] > -3]


# ═════ 1. 전원 패드 → core 전원 토막 (met3 손가락 → met4·met5 판 → 20 µm 목 → core 토막 8 µm)
NECK = 6.0
for s in slots:
    if s['cell'] not in RAIL or s['net'] not in ('VDD', 'VSS'):
        continue
    sd = s['side']; g = G[sd]
    F = fingers(s); fu = [(uv[0], uv[2]) for _, _, uv in F]; vf = min(uv[3] for _, _, uv in F)
    st = stubs(s['net'], sd)
    hl, hh = min(a for a, _ in fu), max(b for _, b in fu)
    cen = (hl + hh) / 2
    lay, sl, shh = min(st, key=lambda q: abs((q[1] + q[2]) / 2 - cen))
    for a, b in fu:
        add('met3', sd, a, vf - 0.5, b, 12.0); via_arr('via3', sd, a, 2.5, b, 11.5)
    jl, jh = min(hl, sl - NECK), max(hh, shh + NECK)
    for L, v0 in (('met4', 2.0), ('met5', 4.0)):
        add(L, sd, hl, v0, hh, 30.0)
        add(L, sd, jl, 10.0, jh, 30.0)
        add(L, sd, sl - NECK, 10.0, shh + NECK, g - 4.0)
    via_arr('via4', sd, hl, 12.0, hh, 28.0)
    via_arr('via4', sd, sl - NECK, 32.0, shh + NECK, g - 6.0)
    add(lay, sd, sl, g - 4.5, shh, g + 0.5)
    s['route'] = f'{lay} 토막 {sl:.2f}–{shh:.2f} (목 {2 * NECK + shh - sl:.0f} µm, met4∥met5)'
    for _, b, _ in F:
        ABSTRACT['met3'].insert(b.to_itype(DBU)); LABELS.append(('met3', s['net'], b.center().x, b.center().y))

# ═════ 2. 넓은 아날로그 (VRAILP·VRAILM·VWH·VWLO·VCM): P_CORE (met3 25 µm) → met4·met5 → core 토막
for s in slots:
    n = s['net']; sd = s['side']
    if 'analog_esd' not in s['cell'] or n not in ('VRAILP', 'VRAILM', 'VWH', 'VWLO', 'VCM'):
        continue
    g = G[sd]
    _, pb, (pl, _, ph, pv) = edge_pin(s, 'P_CORE', ('met3',))
    ABSTRACT['met3'].insert(pb.to_itype(DBU)); LABELS.append(('met3', n, pb.center().x, pb.center().y))
    st = stubs(n, sd)
    lay, sl, shh = min(st, key=lambda q: abs((q[1] + q[2]) / 2 - (pl + ph) / 2))
    if n == 'VCM' and sd == 'S':
        # 아래 VCM: core 토막 (die x 663.7–667.7) 이 패드에서 서쪽 145 µm, 사이에 VSS 패드 (slot 40) 가 있음
        # → met3 10 µm 가로 줄 (v 55–65, VSS 목 met4·met5 아래로 지남) → via3 → met4 4 µm 세로 → core 토막
        add('met3', sd, pl, -0.5, ph, 65.0)
        add('met3', sd, sl - 1.0, 55.0, ph, 65.0)
        add('met4', sd, sl, 55.0, shh, g + 0.5); via_arr('via3', sd, sl, 55.0, shh, 65.0)
        s['route'] = f'met3 10 µm 가로 (VSS 목 아래) → met4 {sl:.2f}–{shh:.2f}'
        continue
    add('met3', sd, pl, -0.5, ph, 12.0); via_arr('via3', sd, pl, 2.5, ph, 11.5)
    if lay == 'met4':                                     # 위 VCM: met4 25 µm 판 → core 토막 4 µm
        add('met4', sd, pl, 2.0, ph, g - 4.0); add('met4', sd, sl, g - 4.5, shh, g + 0.5)
        s['route'] = f'met4 25 µm → 토막 {sl:.2f}–{shh:.2f}'
        continue
    ul, uh = min(pl, sl), max(ph, shh)
    if n in ('VWH', 'VWLO'):                              # 왼쪽 변: core met5 띠 전체 폭으로 넓힘
        add('met4', sd, pl, 2.0, ph, 40.0)
        add('met5', sd, pl, 4.0, ph, 40.0); add('met5', sd, sl, 20.0, shh, g - 4.0)
        via_arr('via4', sd, pl, 12.0, ph, 38.0)
    else:                                                 # VRAIL: met4 ∥ met5 25 µm 그대로 core 앞까지
        add('met4', sd, pl, 2.0, ph, g - 4.0)
        add('met5', sd, ul, 4.0, uh, g - 4.0)
        via_arr('via4', sd, pl, 12.0, ph, g - 8.0)
    add('met5', sd, sl, g - 4.5, shh, g + 0.5)
    s['route'] = f'met3→met4∥met5 → met5 토막 {sl:.2f}–{shh:.2f}'

# ═════ 3. 신호 (met3 L 자): 패드 핀 → 꺾는 줄 v_j → core 핀 (마지막 2 µm 는 핀 폭, met2 핀이면 via2)
JOG = {'SCK': 30, 'SDI': 30, 'SLD': 30, 'RST': 30, 'SEL_EN': 30, 'WP': 30,
       'LQ1': 25, 'LQ2': 25, 'CK': 25, 'CK3': 25, 'LAT': 25, 'VBUS_N': 20, 'VWL': 20,
       'VBPC': 40, 'VBNC': 15, 'IBIAS': 15, 'VBUS_F': 20, 'IBIASP': 20}
OUTS = {'LQ1', 'LQ2'}


def sig(s, net, u_p, v0, w, start_w=None):
    sd = s['side']; g = G[sd]; lay, pb = DEFP[net]
    pu = touv(sd, pb); uc = sn((pu[0] + pu[2]) / 2); pw = pu[2] - pu[0]; vj = JOG[net]
    u_p = sn(u_p)
    add('met3', sd, u_p - w / 2, v0, u_p + w / 2, vj + w / 2)              # 패드 쪽 세로
    add('met3', sd, min(u_p, uc) - w / 2, vj - w / 2, max(u_p, uc) + w / 2, vj + w / 2)  # 꺾는 줄
    if lay == 'met3':
        add('met3', sd, uc - w / 2, vj - w / 2, uc + w / 2, g - 2.0)
        add('met3', sd, pu[0], g - 2.2, pu[2], g + 0.4)
    else:                                                                    # met2 핀 (위 변 디지털, IBIASP)
        add('met3', sd, uc - w / 2, vj - w / 2, uc + w / 2, g - 3.0)
        via2(sd, uc, g - 3.2, pw)
        add('met2', sd, pu[0], g - 3.4, pu[2], g + 0.4)
    LABEL_CORE.append((net, uc))
    return f'met3 {w} µm, 꺾는 줄 v={vj} µm, core 핀 {lay} {uc:.2f}, 꺾임 {abs(uc - u_p):.1f} µm'


LABEL_CORE = []
for s in slots:
    n = s['net']
    if n not in JOG:
        continue
    sd = s['side']
    if 'analog_esd' in s['cell']:
        _, pb, (pl, _, ph, _) = edge_pin(s, 'P_CORE', ('met3',))
        ABSTRACT['met3'].insert(pb.to_itype(DBU)); LABELS.append(('met3', n, pb.center().x, pb.center().y))
        lay, cb = DEFP[n]; cu = touv(sd, cb); uc = (cu[0] + cu[2]) / 2
        add('met3', sd, pl, -0.5, ph, 4.0)
        u_p = min(max(uc, pl + 1.0), ph - 1.0)
        s['route'] = sig(s, n, u_p, 0.0, 2.0)
    elif 'gpiov2' in s['cell']:
        if n in OUTS:                                     # PAD_A_ESD_0_H (met2 0.64) → via2 → met3
            l, pb, (a, _, b, _) = edge_pin(s, 'PAD_A_ESD_0_H')
            ABSTRACT['met2'].insert(pb.to_itype(DBU)); LABELS.append(('met2', n, pb.center().x, pb.center().y))
            uc = sn((a + b) / 2)
            add('met2', sd, a, -0.2, b, 17.0)
            for vv in (16.2, 16.7):
                add('via2', sd, uc - 0.1, vv - 0.1, uc + 0.1, vv + 0.1)
            add('met3', sd, a - 0.05, 15.8, b + 0.05, 17.2)
            s['route'] = 'PAD_A_ESD_0_H → ' + sig(s, n, uc, 16.0, 0.5)
        else:                                             # IN_H (met3 0.62)
            l, pb, (a, _, b, _) = edge_pin(s, 'IN_H')
            ABSTRACT['met3'].insert(pb.to_itype(DBU)); LABELS.append(('met3', n, pb.center().x, pb.center().y))
            add('met3', sd, a, -0.2, b, 1.0)
            s['route'] = 'IN_H → ' + sig(s, n, (a + b) / 2, 0.0, 0.5)

# ═════ 4. gpiov2 설정 핀 묶음 (패드 앞 met1 줄 4 개, 각 핀 met2 세로 → via1)
#   v=4 THI (그 패드 TIE_HI_ESD = VDDIO 쪽), v=7 TLO (그 패드 TIE_LO_ESD = VSSIO 쪽), v=10 VSSD 버스, v=13 VCCD 버스 (변마다 VSSL·VDDL 패드에서)
ROWV = {'THI': 4.0, 'TLO': 7.0, 'VSSD': 10.0, 'VCCD': 13.0}
TIE_IN = {'OE_N': 'VCCD', 'DM[0]': 'VCCD', 'DM[1]': 'VSSD', 'DM[2]': 'VSSD', 'INP_DIS': 'VSSD', 'IB_MODE_SEL': 'VSSD',
          'VTRIP_SEL': 'VSSD', 'SLOW': 'VSSD', 'HLD_OVR': 'VSSD', 'ANALOG_EN': 'VSSD', 'ANALOG_SEL': 'VSSD',
          'ANALOG_POL': 'VSSD', 'OUT': 'VSSD', 'ENABLE_VDDIO': 'VCCD', 'HLD_H_N': 'THI', 'ENABLE_H': 'THI',
          'ENABLE_INP_H': 'TLO', 'ENABLE_VDDA_H': 'TLO', 'ENABLE_VSWITCH_H': 'TLO', 'TIE_HI_ESD': 'THI', 'TIE_LO_ESD': 'TLO'}
TIE_OUT = dict(TIE_IN, **{'DM[0]': 'VSSD', 'INP_DIS': 'VCCD'})   # 출력 패드: DM=000 (드라이버 끔), 입력 버퍼 끔
GPIO_TIE = {}
bus_span = {}                                             # (변, 버스) → [u_lo, u_hi]
for s in slots:
    if 'gpiov2' not in s['cell']:
        continue
    sd = s['side']; tie = TIE_OUT if s['net'] in OUTS else TIE_IN
    GPIO_TIE[s['net']] = tie
    rows = {}
    for pin, row in tie.items():
        l, pb, (a, _, b, _) = edge_pin(s, pin)
        ABSTRACT[l].insert(pb.to_itype(DBU))
        uc = sn((a + b) / 2); vr = ROWV[row]
        rows.setdefault(row, []).append(uc)
        if l == 'met1':                                   # ANALOG_EN: 패드 밖 1.2 µm 에서 met1 → met2
            add('met1', sd, a, -0.2, b, 1.5); via1(sd, uc, 1.1); add('met2', sd, a, 0.94, b, vr + 0.16)
        elif l == 'met3':                                 # ANALOG_POL·ENABLE_VDDIO: met3 → via2 → met2
            vv = 2.0 if pin == 'ANALOG_POL' else vr
            add('met3', sd, a, -0.2, b, vv + 0.25)
            add('via2', sd, uc - 0.1, vv - 0.1, uc + 0.1, vv + 0.1)
            add('met2', sd, a, vv - 0.2, b, max(vv + 0.2, vr + 0.16))
        else:
            add('met2', sd, a, -0.2, b, vr + 0.16)
        via1(sd, uc, vr)
    for row in ('THI', 'TLO'):
        us = rows[row]; add('met1', sd, min(us) - 0.3, ROWV[row] - 0.5, max(us) + 0.3, ROWV[row] + 0.5)
    for row in ('VSSD', 'VCCD'):
        sp = bus_span.setdefault((sd, row), [1e9, -1e9]); sp[0] = min(sp[0], min(rows[row]) - 0.3); sp[1] = max(sp[1], max(rows[row]) + 0.3)
    s['route'] = s.get('route', '') + ' · 설정 핀 묶음'
# VSSL·VDDL 패드 손가락 → VSSD·VCCD 버스 (met3 → via2·via1 배열 → met1)
for s in slots:
    if s['cell'] not in ('sky130_ef_io__vssd_lvc_clamped_pad', 'sky130_ef_io__vccd_lvc_clamped_pad'):
        continue
    sd = s['side']; row = 'VSSD' if 'vssd' in s['cell'] else 'VCCD'; vr = ROWV[row]
    # 모서리 가까운 손가락은 쓰지 않음 (위 변 VSSL 첫 손가락 die x 242–266 = 왼쪽 변 LAT 설정 핀 (x ≤ 243.5) 과 겹침)
    F = [f for f in fingers(s) if 250.0 < f[2][0] and f[2][2] < (1560.0 if sd in 'WE' else 1770.0)]
    sp = bus_span[(sd, row)]
    for _, b, (a, v1, c, v2) in F:
        ABSTRACT['met3'].insert(b.to_itype(DBU))
        add('met3', sd, a, v2 - 0.5, c, vr + 0.5)
        add('met2', sd, a, vr - 0.5, c, vr + 0.5)
        via_arr('via2', sd, a, vr - 0.5, c, vr + 0.5); via_arr('via1', sd, a, vr - 0.5, c, vr + 0.5)
        sp[0] = min(sp[0], a); sp[1] = max(sp[1], c)
    s['route'] = f'{RAIL[s["cell"]]} → {row} 버스 (met1 1 µm, v={vr:.0f}) — core 에 안 감'
for (sd, row), (a, b) in bus_span.items():
    add('met1', sd, a, ROWV[row] - 0.5, b, ROWV[row] + 0.5)

for k in SH:
    SH[k].merge()

# ═════ GDS 쓰기
# (1) DRC 판: frame (자리표시 met5 ring 지움) + chip_core + die_wire
ly = fr
li5 = ly.find_layer(72, 20)
nring = FT.shapes(li5).size(); FT.shapes(li5).clear()
lo = db.LoadLayoutOptions(); lo.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
ly.read(str(TOP / 'route' / 'chip_core.gds'), lo)
C = ly.cell('chip_core')
li_bnd = ly.find_layer(235, 4)
if li_bnd is not None:                                    # IO 셀 prBoundary 지움 (mk_die_from_frame 과 같음)
    core_cells = set(C.called_cells()) | {C.cell_index()}
    for c in ly.each_cell():
        if c.cell_index() not in core_cells and c.cell_index() != FT.cell_index():
            c.shapes(li_bnd).clear()
W = ly.create_cell('die_wire')
for k, (l, d) in LAY.items():
    W.shapes(ly.layer(l, d)).insert(SH[k])
FT.name = 'chip_frame'
so = db.SaveLayoutOptions(); so.add_cell(FT.cell_index())
ly.write(str(OUT2 / 'chip_frame.gds'), so)               # frame 만 (core·배선 없음)
FT.insert(db.DCellInstArray(C.cell_index(), db.DTrans(OX, OY)))
FT.insert(db.DCellInstArray(W.cell_index(), db.DTrans()))
FT.name = 'chip_die'
so = db.SaveLayoutOptions(); so.add_cell(FT.cell_index())
ly.write(str(H / 'chip_die.gds'), so)

# (2) LVS 판: chip_core + die_wire + 패드 핀 도형 (LEF) + 이름표 (core 넷 이름)
lv = db.Layout(); lv.read(str(TOP / 'route' / 'chip_core.gds'))
LT = lv.create_cell('chip_die'); LC = lv.cell('chip_core')
LT.insert(db.DCellInstArray(LC.cell_index(), db.DTrans(OX, OY)))
LW = lv.create_cell('die_wire')
for k, (l, d) in LAY.items():
    LW.shapes(lv.layer(l, d)).insert(SH[k])
LT.insert(db.DCellInstArray(LW.cell_index(), db.DTrans()))
PA = lv.create_cell('pad_pins')
for k, r in ABSTRACT.items():
    r.merge(); PA.shapes(lv.layer(*LAY[k])).insert(r)
LT.insert(db.DCellInstArray(PA.cell_index(), db.DTrans()))
for l, t, x, y in LABELS:
    LT.shapes(lv.layer(*LBL[l])).insert(db.DText(t, db.DTrans(x, y)))
so = db.SaveLayoutOptions(); so.add_cell(LT.cell_index())
lv.write(str(OUT2 / 'chip_die_lvs.gds'), so)

# ═════ 배정 표
SN = {'N': '위', 'S': '아래', 'W': '왼쪽', 'E': '오른쪽'}
for s in slots:
    s.pop('t')
json.dump(dict(note='die pad 배정 (r6 core). 좌표 die µm. net "" = 예비 (연결 없음)', offset=[OX, OY], gap=G, slots=slots,
               gpio_tie=GPIO_TIE, tie_rows_v=ROWV), open(H / 'pad_map.json', 'w'), indent=1, ensure_ascii=False)
L = ['# die 패드 배정 (r6 core) — `mk_die.py` 가 씀', '',
     '| # | 변 | 셀 | 이전 | 새 | 연결 |', '|---|---|---|---|---|---|']
for s in slots:
    old = s['old']; new = s['net'] or '(예비)'
    ch = ' **←**' if (s['idx'] in MOVE) else ''
    L.append(f"| {s['idx']} | {SN[s['side']]} | {s['cell'].replace('sky130_ef_io__', '')} | {old} | {new}{ch} | {s.get('route', '')} |")
(H / 'pad_map.md').write_text('\n'.join(L) + '\n')
REPORT.append(f'gap (패드 끝 ↔ core 변) µm: {G}')
REPORT.append(f'지운 자리표시 met5 ring 도형 (frame top): {nring}')
for k in SH:
    REPORT.append(f'{k}: 도형 {SH[k].count()}')
(H / 'wire_report.txt').write_text('\n'.join(REPORT) + '\n')
print('\n'.join(REPORT))
print('labels', len(LABELS), 'core-signal', len(LABEL_CORE))
