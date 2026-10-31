"""실제 크기 배치 (10/28, 칩 core 조립 `place/` 담당). (d3) floorplan (`../../floorplan_opt_D3.json`, `../../floorplan_opt.py` build_stacked) 의 위상을 그대로 두고
블록을 실제 GDS 크기로 다시 놓는다. 사용자 지시 (10/28): "각 블럭 길이 연결하는 것과 lvs 통과와 DRC 통과가 되면은 CaC 제출 기준에 만족".

위상 (d3 와 같음):
  위 반쪽 (free, R0)  : DATA | input drive | 배열 | row_blk, 배열 아래 col_blk.
  아래 반쪽 (nudge, R180): 위 반쪽을 180° 돌린 것 (col_blk 이 배열 위). 두 col_blk 이 가운데 띠에 나란히, 사이 = 가운데 버스 통로.
  가운데 띠 왼쪽 = test | 판독 TG | write buffer | WU1 → nudge col_blk, 오른쪽 = free col_blk → WU2 | write buffer | 판독 TG | test.
  위 왼쪽 모서리 = glob_dig + test, 아래 오른쪽 모서리 = bias + nudge 주입기 + test. core 둘레 배선 띠.
핀 맞춤 (곧은 strap 으로 잇기 위함):
  배열 row_i ↔ input_drive row_i (같은 y), 배열 wl_i ↔ row_blk wl[i] (같은 y, row 는 블록 안 간격 차이로 0.01 µm 남음 → 보고),
  배열 col_c ↔ col_blk col[c] (같은 x). DATA ga·gb ↔ input drive ga·gb 는 두 블록 핀 간격이 달라 맞출 수 없음 → 보고 + 맞출 y 표.
쓰임: python mk_lef.py && python place_real.py → place_real.json, place_real.tcl, chip_core_placed.gds, pin_check.txt, data_blk_pin_targets.txt, place_real.png
"""
import json
import os
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
L = H.parents[1]
D3 = json.loads((L / 'floorplan_opt_D3.json').read_text())
P = json.loads((H / 'lef' / 'pins_all.json').read_text())
HVL = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl'
INV = 'sky130_fd_sc_hvl__inv_2'                                     # net/DEVIATIONS.md D7: LAT → latb inverter, WU 마다 하나 (ilatb1·ilatb2)
P[INV] = dict(size=[2.40, 4.07], gds=str(HVL / 'gds/sky130_fd_sc_hvl.gds'), pins={})
SITE_W, SITE_H = 0.48, 4.07                                         # hvl unithv site (표준 셀 줄 격자)
NETV = H.parent / 'net' / 'chip_core.v'
LEF = lambda c: str(HVL / 'lef/sky130_fd_sc_hvl.lef') if c == INV else str(H / 'lef' / f'{c}.lef')

# ── 틈 (µm). d3 값은 floorplan_opt.py 의 G, g, GB, ring, ch
RING, CH, MID = 30.0, 30.0, 15.0        # core 둘레 배선 띠, 가운데 띠 버스 통로 (가로 두 곳), 두 col_blk 사이 통로 (d3 = G 15)
G, g, GB = 15.0, 5.0, 20.0              # d3 의 블록 사이 틈, 좁은 틈, WU ↔ col_blk 버스 틈
GS = 5.0                                # 곧은 strap 구간 (배열 ↔ input drive / row_blk / col_blk, DATA ↔ input drive)
DRC_MIN = 1.27                          # 블록 경계 사이 최소 (HV nwell 간격 hvnwell.8.hv 1.27 µm 가 가장 큼, 아래 README)
ARR = os.environ.get('ARR_CELL', 'arr_w3s_128x64')                  # 칩 정본 = 덧댄 판 (조정 세션 10/28). 원본 = ARR_CELL=arr_w3_128x64 (크기·핀 자리 같음)
TEST_D3 = {b['cell']: b['rect'] for b in D3['blocks'] if b['kind'] == 'test'}
snap = lambda v: round(round(v / 0.005) * 0.005, 3)
W = lambda c: P[c]['size'][0]
Hh = lambda c: P[c]['size'][1]


def pin_rects(cell, pin):
    return [s[1:] for s in P[cell]['pins'][pin]['shapes']]


def pc(cell, pin, side=None):
    """핀 사각형 가운데 (cell 좌표). side = 'W'·'E'·'S'·'N' 이면 그 변에 닿는 조각."""
    rs = pin_rects(cell, pin)
    if side:
        w, h = P[cell]['size']
        f = {'W': lambda r: r[0] <= 0.5, 'E': lambda r: r[2] >= w - 0.5, 'S': lambda r: r[1] <= 0.5, 'N': lambda r: r[3] >= h - 0.5}[side]
        rs = [r for r in rs if f(r)]
    assert rs, (cell, pin, side)
    r = rs[0]
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), r


def consistent(vals, what):
    assert max(vals) - min(vals) < 1e-6, (what, min(vals), max(vals))
    return vals[0]


# ── 블록끼리 상대 위치 (핀에서 계산, 배열 왼쪽 아래 기준, R0)
NR_ID = 100; NR_RB = 106; NC = 64
dy_id = consistent([pc(ARR, f'row_{i}', 'W')[0][1] - pc('input_drive', f'row_{i}', 'E')[0][1] for i in range(NR_ID)], 'idrv row')
dy_rb = consistent([pc(ARR, f'wl_{i}', 'E')[0][1] - pc('row_blk', f'wl[{i}]', 'W')[0][1] for i in range(NR_RB)], 'row_blk wl')
dx_cb = consistent([pc(ARR, f'col_{c}', 'S')[0][0] - pc('col_blk', f'col[{c}]', 'N')[0][0] for c in range(NC)], 'col_blk col')
dy_rb, dy_id, dx_cb = snap(dy_rb), snap(dy_id), snap(dx_cb)
REL = {   # 위 반쪽 (free) 블록: 배열 왼쪽 아래 기준 (x, y)
    'arr': (0.0, 0.0),
    'idrv': (-GS - W('input_drive'), dy_id),
    'rowb': (W(ARR) + GS, dy_rb),
    'colb': (dx_cb, -GS - Hh('col_blk')),
}
REL['data'] = (REL['idrv'][0] - g - W('data_blk'), Hh(ARR) - Hh('data_blk'))     # DATA 위 = 배열 위 (d3 처럼 위로 맞춤)
CELL = dict(arr=ARR, idrv='input_drive', rowb='row_blk', colb='col_blk', data='data_blk')   # 인스턴스 = <키>_f / <키>_n (README §2)

# ── core 좌표
XAn, YAn = RING + GS + W('row_blk'), RING                           # nudge 배열 (R180) 왼쪽 아래: row_blk 이 core 왼쪽 띠에 붙음
TX, TY = XAn + W(ARR), YAn + Hh(ARR)                                 # R180 이동: free 상대 (rx, ry, w, h) → (TX − rx − w, TY − ry − h)
nud = lambda k: (TX - REL[k][0] - W(CELL[k]), TY - REL[k][1] - Hh(CELL[k]))
ncolb_right = nud('colb')[0] + W('col_blk')
XAf = ncolb_right + MID - REL['colb'][0]                             # free col_blk 왼 끝 = nudge col_blk 오른 끝 + 가운데 통로
ncolb_top = nud('colb')[1] + Hh('col_blk')
YAf = ncolb_top + CH                                                 # free 배열 아래 = nudge col_blk 위 + 버스 통로 (nudge 쪽)
assert abs((YAf + REL['colb'][1]) - (YAn + Hh(ARR) + CH)) < 1e-6     # free col_blk 아래 = nudge 배열 위 + 버스 통로 (free 쪽) — 대칭
fre = lambda k: (XAf + REL[k][0], YAf + REL[k][1])
CORE_W = snap(fre('rowb')[0] + W('row_blk') + RING)
CORE_H = snap(YAf + Hh(ARR) + RING)
INST = {}


def put(inst, cell, x, y, orient, group):
    INST[inst] = dict(cell=cell, x=snap(x), y=snap(y), w=W(cell), h=Hh(cell), orient=orient, group=group)


for k, cell in CELL.items():
    put(f'{k}_f', cell, *fre(k), 'R0', 'free half')
    put(f'{k}_n', cell, *nud(k), 'R180', 'nudge half')
band0, band1 = YAn + Hh(ARR), YAf                                    # 가운데 띠 (nudge 배열 위 … free 배열 아래)
yb = (band0 + band1) / 2 - Hh('wu') / 2                              # d3: WU 를 띠 가운데 높이에
# 왼쪽 띠: test | 판독 TG | write buffer | WU1 | (GB) | nudge col_blk
x = INST['colb_n']['x'] - GB - W('wu');                              put('wu1', 'wu', x, yb, 'MY', 'band')        # 핀 (왼 변) 이 col_blk 쪽을 보게
x -= G + W('wbuf');                                                  put('wbuf_n', 'wbuf', x, yb, 'R0', 'band')    # out·vwh·vwl (오른 변) → WU1·col_blk 쪽
x -= G + W('tg_n2');                                                 put('rotg_n', 'tg_n2', x, yb, 'R0', 'band')
# 오른쪽 띠: free col_blk | (GB) | WU2 | write buffer | 판독 TG | test
x = INST['colb_f']['x'] + W('col_blk') + GB;                         put('wu2', 'wu', x, yb, 'R0', 'band')
x += W('wu') + G;                                                    put('wbuf_f', 'wbuf', x, yb, 'MY', 'band')    # out 이 col_blk 쪽 (왼) 을 보게
x += W('wbuf') + G;                                                  put('rotg_f', 'tg_n2', x, yb, 'R0', 'band')
# 위 왼쪽 모서리: glob_dig (위에 붙임)
put('glob', 'glob_dig', RING, CORE_H - RING - Hh('glob_dig'), 'R0', 'corner')
# 아래 오른쪽 모서리: bias, 그 위 nudge 주입기 (d3 와 같은 쌓음)
half_r = max(INST[i]['x'] + INST[i]['w'] for i in INST if INST[i]['group'] == 'nudge half')
put('bias', 'bias_beta', half_r + G, RING, 'R0', 'corner')
put('ninj', 'nudge_inj', half_r + G, RING + Hh('bias_beta') + G, 'R0', 'corner')
# latb inverter: WU 아래, lat·latb 핀이 있는 변 쪽 모서리. site 격자 (x 0.48, y 4.07 짝수 줄 → R0), WU 와 틈 ≥ 5 µm
import math                                                                  # noqa: E402
yi = (math.floor((yb - g - SITE_H) / SITE_H) // 2 * 2) * SITE_H
put('ilatb1', INV, math.floor((INST['wu1']['x'] + W('wu') - W(INV)) / SITE_W) * SITE_W, yi, 'R0', 'glue')   # wu1 = MY → 핀이 오른 변
put('ilatb2', INV, math.ceil(INST['wu2']['x'] / SITE_W) * SITE_W, yi, 'R0', 'glue')                         # wu2 = R0 → 핀이 왼 변

# ── test 자리 (d3 사각형 크기 그대로, d3 와 같은 모서리·변에 붙임). 실제 블록은 testpat/ 에이전트.
dw = lambda c: TEST_D3[c][2] - TEST_D3[c][0]
dh = lambda c: TEST_D3[c][3] - TEST_D3[c][1]
TEST = {}
TEST['tp_tl'] = [RING, YAf, RING + dw('B_tp_tl'), YAf + dh('B_tp_tl')]                                    # d3: 왼 띠, 아래 = free 배열 아래
rb_n_top = INST['rowb_n']['y'] + INST['rowb_n']['h']
y0 = max(band0 + g, rb_n_top + g)                                                                         # d3: 띠 아래 + 5 (nudge row_blk 위가 띠 안으로 4.5 µm 들어옴)
TEST['tp_bandl'] = [RING, y0, RING + dw('B_tp_bandl'), y0 + dh('B_tp_bandl')]
TEST['tp_bandr'] = [CORE_W - RING - dw('B_tp_bandr'), band0 + G, CORE_W - RING, band0 + G + dh('B_tp_bandr')]  # d3: 오른 띠, 아래 = 띠 아래 + 15
y0 = INST['ninj']['y'] + INST['ninj']['h'] + G
TEST['tp_br'] = [half_r + G, y0, half_r + G + dw('B_tp_br'), y0 + dh('B_tp_br')]                         # d3: bias 열, nudge 주입기 위 + 15
TEST = {k: [snap(v) for v in r] for k, r in TEST.items()}
for k, r in TEST.items():                                                  # 실제 test 블록 (testpat/, 10/28): d3 사각형 왼쪽 아래에, 크기는 조금 작음
    if k in P:
        assert W(k) <= r[2] - r[0] + 1e-6 and Hh(k) <= r[3] - r[1] + 1e-6, (k, P[k]['size'], r)
        put(k, k, r[0], r[1], 'R0', 'test')
ROUTE = {
    'routing ring (bottom)': [0, 0, CORE_W, RING], 'routing ring (top)': [0, CORE_H - RING, CORE_W, CORE_H],
    'routing ring (left)': [0, RING, RING, CORE_H - RING], 'routing ring (right)': [CORE_W - RING, RING, CORE_W, CORE_H - RING],
    'bus channel (nudge side)': [INST['colb_n']['x'], INST['colb_n']['y'] + Hh('col_blk'), INST['colb_n']['x'] + W('col_blk'), YAf],
    'bus channel (middle)': [INST['colb_n']['x'] + W('col_blk'), band0, INST['colb_f']['x'], band1],
    'bus channel (free side)': [INST['colb_f']['x'], band0, INST['colb_f']['x'] + W('col_blk'), INST['colb_f']['y']],
}
ROUTE = {k: [snap(v) for v in r] for k, r in ROUTE.items()}


# ── 변환: cell 좌표 (u, v) → core 좌표
def xf(inst, u, v):
    I = INST[inst]; w, h = I['w'], I['h']
    return {'R0': (I['x'] + u, I['y'] + v), 'R180': (I['x'] + w - u, I['y'] + h - v), 'MY': (I['x'] + w - u, I['y'] + v),
            'MX': (I['x'] + u, I['y'] + h - v)}[I['orient']]


def xr(inst, r):
    (a, b), (c, d) = xf(inst, r[0], r[1]), xf(inst, r[2], r[3])
    return [round(min(a, c), 4), round(min(b, d), 4), round(max(a, c), 4), round(max(b, d), 4)]


def bbox(inst):
    I = INST[inst]
    return [I['x'], I['y'], I['x'] + I['w'], I['y'] + I['h']]


# ── 핀 맞춤 검사
def pin_abs(inst, pin, side):
    (cx, cy), r = pc(INST[inst]['cell'], pin, side)
    R = xr(inst, r)
    return ((R[0] + R[2]) / 2, (R[1] + R[3]) / 2), R


CHECK, LINES = {}, []


def check(name, pairs, axis):
    """pairs = [(라벨, (inst, pin, side), (inst, pin, side))]. axis = 1 (y 맞춤) / 0 (x 맞춤). 결과: 최대 |차|, 어긋난 쌍, strap 길이."""
    d, bad, gap = [], [], []
    for lab, A, B in pairs:
        (ca, ra), (cb, rb) = pin_abs(*A), pin_abs(*B)
        dd = cb[axis] - ca[axis]
        d.append(dd)
        o = 1 - axis                                                        # strap 방향
        gap.append(max(rb[o] - ra[o + 2], ra[o] - rb[o + 2]))              # 두 핀 사각형 사이 곧은 구간
        if abs(dd) > 0.0005:
            bad.append((lab, round(dd, 4)))
    CHECK[name] = dict(pairs=len(pairs), max_abs_diff_um=round(max(abs(v) for v in d), 4), mismatched=len(bad),
                       mismatched_list=bad[:200], strap_len_um=[round(min(gap), 3), round(max(gap), 3)])
    LINES.append(f'{name}: 쌍 {len(pairs)}, 최대 |차| {max(abs(v) for v in d):.4f} µm, 어긋난 쌍 {len(bad)}, 곧은 구간 {min(gap):.3f}–{max(gap):.3f} µm')
    if bad:
        LINES.append('   어긋난 쌍 (차 µm): ' + ', '.join(f'{a} {b:+.3f}' for a, b in bad[:12]) + (' …' if len(bad) > 12 else ''))


for h in 'fn':
    a = f'arr_{h}'
    check(f'[{h}] 배열 row_i (서쪽 끝) ↔ input_drive row_i', [(f'row_{i}', (a, f'row_{i}', 'W'), (f'idrv_{h}', f'row_{i}', 'E')) for i in range(NR_ID)], 1)
    check(f'[{h}] 배열 row_i (동쪽 끝) ↔ row_blk row[i]', [(f'row_{i}', (a, f'row_{i}', 'E'), (f'rowb_{h}', f'row[{i}]', 'W')) for i in range(NR_RB)], 1)
    check(f'[{h}] 배열 wl_i (동쪽 끝) ↔ row_blk wl[i]', [(f'wl_{i}', (a, f'wl_{i}', 'E'), (f'rowb_{h}', f'wl[{i}]', 'W')) for i in range(NR_RB)], 1)
    check(f'[{h}] 배열 col_c (남쪽 끝) ↔ col_blk col[c]', [(f'col_{c}', (a, f'col_{c}', 'S'), (f'colb_{h}', f'col[{c}]', 'N')) for c in range(NC)], 0)
    check(f'[{h}] data_blk ga·gb ↔ input_drive ga·gb', [(f'{s}{k}', (f'data_{h}', f'{s}[{k}]', 'E'), (f'idrv_{h}', f'{s}{k}', 'W'))
                                                       for k in range(49) for s in ('ga', 'gb')], 1)

# ── netlist 대조 (net/chip_core.v 가 있으면): 맞춘 핀 쌍이 정말 같은 넷인지, 배열 행·열 넷이 다른 번호와 엮이지 않는지
NETCHK = []
if NETV.exists():
    import sys                                                               # noqa: E402
    sys.path.insert(0, str(H.parent / 'route'))
    import routelib                                                          # noqa: E402  (route/ 의 Verilog 읽기, 읽기만)
    macros = {}
    for c in sorted({I['cell'] for I in INST.values()} - {INV}) + ['arr_w3_128x64']:
        routelib.parse_lef(LEF(c), macros)
    routelib.parse_lef(LEF(INV), macros)                                     # hvl 표준 셀 (inv_2)
    for c in ('tp_tl', 'tp_br', 'tp_bandl', 'tp_bandr'):                     # test 자리 = netlist 의 빈 모듈 (LEF 없음)
        macros.setdefault(c, routelib.Macro(c))
    _, _, NI = routelib.parse_verilog(str(NETV), macros, top='chip_core')
    net = lambda inst, pin: NI[inst][1].get(pin)
    miss_inst = sorted(set(NI) - set(INST))
    extra_inst = sorted(set(INST) - set(NI))
    for h in 'fn':
        groups = [('배열 row ↔ input_drive row', [(f'arr_{h}', f'row_{i}', f'idrv_{h}', f'row_{i}') for i in range(NR_ID)]),
                  ('배열 row ↔ row_blk row', [(f'arr_{h}', f'row_{i}', f'rowb_{h}', f'row[{i}]') for i in range(NR_RB)]),
                  ('배열 wl ↔ row_blk wl', [(f'arr_{h}', f'wl_{i}', f'rowb_{h}', f'wl[{i}]') for i in range(NR_RB)]),
                  ('배열 col ↔ col_blk col', [(f'arr_{h}', f'col_{c}', f'colb_{h}', f'col[{c}]') for c in range(NC)]),
                  ('data ga·gb ↔ input_drive ga·gb', [(f'data_{h}', f'{s}[{k}]', f'idrv_{h}', f'{s}{k}') for k in range(49) for s in ('ga', 'gb')])]
        for nm, prs in groups:
            bad = [(a, pa, b, pb, net(a, pa), net(b, pb)) for a, pa, b, pb in prs if not net(a, pa) or net(a, pa) != net(b, pb)]
            NETCHK.append(f'[{h}] {nm}: 쌍 {len(prs)}, 같은 넷 {len(prs) - len(bad)}' + (f', 다름 {len(bad)}: {bad[:3]}' if bad else ''))
    NETCHK.append(f'netlist 인스턴스 중 배치 안 한 것: {miss_inst or "없음"}, 배치했는데 netlist 에 없는 것: {extra_inst or "없음"}')
    for i in ('ilatb1', 'ilatb2'):
        if i in NI:
            NETCHK.append(f'{i}: A = {NI[i][1].get("A")}, Y = {NI[i][1].get("Y")}')
    print('\n'.join(NETCHK))

# ── 블록 사이 간격 (모든 쌍, 경계 사각형 기준). 겹침·DRC_MIN 미만 = 문제
def gap_of(r, s):
    dx = max(s[0] - r[2], r[0] - s[2], 0.0); dy = max(s[1] - r[3], r[1] - s[3], 0.0)
    if dx == 0 and dy == 0:
        ox = min(r[2], s[2]) - max(r[0], s[0]); oy = min(r[3], s[3]) - max(r[1], s[1])
        return -min(ox, oy) if ox > 0 and oy > 0 else 0.0
    return (dx * dx + dy * dy) ** 0.5


RECTS = {i: bbox(i) for i in INST} | {k: v for k, v in TEST.items() if k not in INST}
GAPS = []
names = sorted(RECTS)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        gv = gap_of(RECTS[a], RECTS[b])
        if gv < 10.0:
            GAPS.append((round(gv, 3), a, b))
GAPS.sort()
inside = all(0 <= r[0] and r[2] <= CORE_W and 0 <= r[1] and r[3] <= CORE_H for r in RECTS.values())
ring_ok = all(RING - 1e-6 <= r[0] and r[2] <= CORE_W - RING + 1e-6 and RING - 1e-6 <= r[1] and r[3] <= CORE_H - RING + 1e-6 for r in RECTS.values())

# ── die 크기 영향 (floorplan_opt.py 와 같은 식: die = 10 µm 올림 (core + 2 × (IO ring 30+204+10 + core 전원 ring 80 + 10)))
RING_OUT = 30 + 204 + 10 + 4 * 20
up10 = lambda v: -(-v // 10) * 10
DIE = (up10(CORE_W + 2 * (RING_OUT + 10)), up10(CORE_H + 2 * (RING_OUT + 10)))

# ── 파일
GDSF = lambda c: P[c]['gds']
ORI_DEF = {'R0': 'N', 'R180': 'S', 'MY': 'FN', 'MX': 'FS'}
OUTJ = dict(
    version='실제 크기 배치 첫 판 (10/28) — (d3) 위상, 블록 = 실제 GDS·LEF',
    units='µm, core 좌표 (원점 = core 왼쪽 아래). x·y = 놓은 블록 경계의 왼쪽 아래 (Innovus placeInstance / DEF COMPONENTS 와 같은 뜻)',
    lef_origin='LEF ORIGIN 0 0 = 블록 경계 왼쪽 아래. GDS 는 같은 원점으로 맞춘 파일 (instances.*.gds) 을 쓴다',
    core=dict(w=CORE_W, h=CORE_H, d3=[D3['core']['w'], D3['core']['h']], over_d3=[round(CORE_W - D3['core']['w'], 2), round(CORE_H - D3['core']['h'], 2)]),
    die_estimate=dict(w=DIE[0], h=DIE[1], d3=[D3['die']['w'], D3['die']['h']], rule='floorplan_opt.py: up10(core + 2 × 334)'),
    gaps_um=dict(ring=RING, bus_channel=CH, middle_channel=MID, strap=GS, G=G, g=g, wu_bus=GB, drc_min=DRC_MIN),
    pin_offsets_um=dict(idrv_y_from_arr=dy_id, rowb_y_from_arr=dy_rb, colb_x_from_arr=dx_cb),
    instances={i: dict(cell=I['cell'], x=I['x'], y=I['y'], w=I['w'], h=I['h'], orient=I['orient'], def_orient=ORI_DEF[I['orient']],
                       group=I['group'], lef=LEF(I['cell']), gds=GDSF(I['cell'])) for i, I in INST.items()},
    test_areas={k: dict(rect=v, d3_rect=TEST_D3['B_' + k], note='자리만 (testpat/ 에이전트가 이 크기로 만듦)') for k, v in TEST.items()},
    route_areas=ROUTE,
    checks=CHECK, netlist_check=NETCHK,
    min_gaps=[dict(gap=a, between=[b, c]) for a, b, c in GAPS[:25]],
    inside_core=inside, inside_ring=ring_ok,
)
(H / 'place_real.json').write_text(json.dumps(OUTJ, indent=1, ensure_ascii=False))

ORI_ST = {'R0': 'r0', 'R180': 'r180', 'MY': 'my', 'MX': 'mx'}
T = ['# place_real.tcl — Innovus (stylus) 블록 고정 배치. place_real.py 가 씀 (손으로 고치지 않음).',
     f'# core {CORE_W} x {CORE_H} um, 원점 = core 왼쪽 아래. location = 방향 적용 뒤 bbox 왼쪽 아래 (DEF COMPONENTS 와 같은 뜻).',
     '# LEF: place/lef/<cell>.lef (ORIGIN 0 0). GDS merge: place_real.json 의 instances.<inst>.gds (원점을 LEF 원점에 맞춘 파일).',
     f'# floorplan 예: create_floorplan -box_size {{0 0 {CORE_W} {CORE_H} 0 0 {CORE_W} {CORE_H} 0 0 {CORE_W} {CORE_H}}}',
     '# 옛 명령 (legacy UI): placeInstance <inst> <x> <y> <R0|R180|MY> -fixed', '',
     'set PLACE_REAL {']
T += [f'  {{{i} {I["cell"]} {I["x"]:.3f} {I["y"]:.3f} {ORI_ST[I["orient"]]}}}' for i, I in INST.items()]
T += ['}', 'foreach m $PLACE_REAL {', '    lassign $m inst cell x y o', '    place_inst $inst [list $x $y] $o -fixed', '}',
      'set nbad 0', 'foreach m $PLACE_REAL {', '    lassign $m inst cell x y o', '    set ib [get_db inst:$inst]',
      '    lassign [lindex [get_db $ib .bbox] 0] bx1 by1 bx2 by2',
      '    if {abs($bx1 - $x) > 0.001 || abs($by1 - $y) > 0.001 || [string tolower [get_db $ib .orient]] ne $o || [get_db $ib .place_status] ne "fixed"} {',
      '        incr nbad; puts "PLACE_REAL MISPLACED $inst plan {$x $y $o} got {$bx1 $by1 [get_db $ib .orient] [get_db $ib .place_status]}"', '    }', '}',
      'puts "PLACE_REAL placed [llength $PLACE_REAL], mismatched $nbad"', 'if {$nbad > 0} { error "placement != place_real" }', '',
      '# test 자리 (블록 아직 없음, 배치만 비워 둠): ' + ', '.join(f'{k} {{{" ".join(f"{v:.3f}" for v in r)}}}' for k, r in TEST.items()),
      '# 배선 자리 (route_areas): ' + ', '.join(f'{k} {{{" ".join(f"{v:.3f}" for v in r)}}}' for k, r in ROUTE.items()), '']
(H / 'place_real.tcl').write_text('\n'.join(T))

# ── 핀 맞춤 결과 + DATA 핀 맞출 자리
PC = ['# 핀 맞춤 검사 (place_real.py). 차 = 둘째 블록 핀 가운데 − 첫째 블록 핀 가운데 (µm). 곧은 구간 = 마주 보는 두 핀 사각형 사이 거리.', '']
PC += LINES + ([''] + ['# netlist 대조 (net/chip_core.v)'] + NETCHK if NETCHK else []) + ['', f'core {CORE_W} × {CORE_H} µm (d3 {D3["core"]["w"]} × {D3["core"]["h"]}), die 어림 {DIE[0]} × {DIE[1]} µm (d3 {D3["die"]["w"]} × {D3["die"]["h"]})',
               f'core 안: {inside}, 배선 띠 안쪽: {ring_ok}', '', '# 블록 경계 사이 간격이 10 µm 미만인 쌍 (작은 것부터, 대각은 유클리드 거리)']
PC += [f'  {a:8.3f}  {b} ↔ {c}' for a, b, c in GAPS]
(H / 'pin_check.txt').write_text('\n'.join(PC) + '\n')
DT = ['# data_blk 핀을 input_drive ga·gb 와 같은 y 로 다시 놓을 때의 자리 (data_blk 셀 좌표, µm). place_real.json 의 data_f 자리 기준.',
      '# 지금 data_blk 핀: 3.41 µm 간격 고른 줄 (ga[k]·gb[k] 번갈아), input_drive: 0.64 µm 간격 묶음 (tier 20 개) → 차 최대 98 µm.',
      '# pin  지금_y  맞출_y  (met3, 동쪽 변 x = 40.8; input_drive 핀은 met2 0.34 µm 높이)']
for k in range(49):
    for s in ('ga', 'gb'):
        (_, cy_i), _ = pin_abs('idrv_f', f'{s}{k}', 'W')
        (_, cy_d), _ = pin_abs('data_f', f'{s}[{k}]', 'E')
        DT.append(f'{s}[{k}]  {cy_d - INST["data_f"]["y"]:.3f}  {cy_i - INST["data_f"]["y"]:.3f}')
(_, cy_r), _ = pin_abs('idrv_f', 'READ', 'W')
DT.append(f'# 참고: input_drive READ 핀 (서쪽 met2) y = {cy_r - INST["data_f"]["y"]:.3f} (data_blk 좌표)')
(H / 'data_blk_pin_targets.txt').write_text('\n'.join(DT) + '\n')

# ── chip_core_placed.gds (배선 없음, test 자리 비움)
ly = db.Layout(); ly.dbu = 0.001
opt = db.LoadLayoutOptions(); opt.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell    # 같은 이름 하위 셀은 내용이 같음 (mk 전 확인)
for c in sorted({I['cell'] for I in INST.values()}):
    ly.read(GDSF(c), opt)
top = ly.create_cell('chip_core')
um = lambda v: int(round(v * 1000))
gchk = []
for i, I in INST.items():
    ci = ly.cell(I['cell']).cell_index()
    x, y, w, h = um(I['x']), um(I['y']), um(I['w']), um(I['h'])
    t = {'R0': db.Trans(0, False, x, y), 'R180': db.Trans(2, False, x + w, y + h), 'MY': db.Trans(db.Trans.M90, x + w, y),
         'MX': db.Trans(db.Trans.M0, x, y + h)}[I['orient']]
    bb = top.insert(db.CellInstArray(ci, t)).bbox()                    # GDS 도형이 배치 사각형 안에 있는지 (hvl 표준 셀은 hvi·nwell 이 LEF 밖으로 0.33·0.265·0.415 µm 나옴)
    m = 420 if I['cell'] == INV else 0
    gchk.append(bb.left >= x - m and bb.bottom >= y - m and bb.right <= x + w + m and bb.top <= y + h + m)
so = db.SaveLayoutOptions(); so.add_cell(top.cell_index())
ly.write(str(H / 'chip_core_placed.gds'), so)
print('GDS 블록 bbox ⊂ 배치 사각형:', all(gchk), len(gchk))

# ── 그림
import matplotlib                                                            # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                              # noqa: E402
from matplotlib.patches import Rectangle                                     # noqa: E402

NAME = {'arr': ('{} crossbar\n128 × 64 1T1R', 'array'), 'idrv': ('input drive\n({})', 'pitch'), 'rowb': ('row MUX + decoder\n+ shift reg.\n({})', 'pitch'),
        'colb': ('column MUX + diodes + decoder + shift reg. ({})', 'pitch'), 'data': ('DATA ({})', 'digital')}
FILLC = dict(array='#DCE3F0', pitch='#E4E6EE', analog='#E6DDF0', digital='#D3DCEA')
fig, ax = plt.subplots(figsize=(10, 10 * CORE_H / CORE_W + 0.6))
ax.add_patch(Rectangle((0, 0), CORE_W, CORE_H, fc='white', ec='black', lw=1.0))
for nm, r in ROUTE.items():
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='white', ec='#7A8494', lw=0.4, hatch='////'))
for i, I in INST.items():
    x0, y0, x1, y1 = bbox(i)
    key, half = i.split('_')[0], {'f': 'free', 'n': 'nudge'}.get(i.split('_')[-1], '')
    if key == 'tp':                                                    # test 블록 (실제)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#F2E6E6', ec='#500000', lw=0.7))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, 'test structures', rotation=90, ha='center', va='center', fontsize=5, color='#500000')
        continue
    if key.startswith('ilatb'):                                        # LAT → latb inverter (hvl 표준 셀)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#D3DCEA', ec='#333333', lw=0.4))
        ax.annotate('LAT inverter', xy=((x0 + x1) / 2, y0), xytext=((x0 + x1) / 2, y0 - 14), ha='center', va='top', fontsize=4.2,
                    arrowprops=dict(arrowstyle='-', lw=0.4, color='#333333'))
        continue
    if key in NAME:
        txt, kind = NAME[key]; txt = txt.format(half)
    else:
        txt, kind = {'wu1': ('WU1', 'analog'), 'wu2': ('WU2', 'analog'), 'wbuf': ('write\nbuffer', 'analog'), 'rotg': ('', 'analog'),
                     'glob': ('global\ndigital', 'digital'), 'bias': ('bias', 'analog'), 'ninj': ('nudge\ninjector', 'analog')}[key]
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=FILLC[kind], ec='#333333', lw=0.6))
    fs = 7 if key == 'arr' else 5.2
    if key == 'rotg':
        ax.annotate('readout TG', xy=((x0 + x1) / 2, y1), xytext=((x0 + x1) / 2, y1 + 40), ha='center', va='bottom', fontsize=4.6,
                    arrowprops=dict(arrowstyle='-', lw=0.4, color='#333333'))
    elif key == 'data':
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, 'DATA', rotation=90, ha='center', va='center', fontsize=fs)
    elif key in ('bias', 'ninj', 'wbuf'):
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, txt, ha='center', va='center', fontsize=4.2)
    else:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, txt, ha='center', va='center', fontsize=fs,
                weight='bold' if key in ('arr', 'wu1', 'wu2') else 'normal')
    if I['orient'] == 'R180' and key == 'arr':
        ax.text((x0 + x1) / 2, y0 + 25, '(rotated 180°)', ha='center', fontsize=5, color='#500000')
for k, r in TEST.items():
    if k in INST:
        continue
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='white', ec='#500000', lw=0.8, ls='--'))
    ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 'test area', rotation=90, ha='center', va='center', fontsize=5, color='#500000')
d3w, d3h = D3['core']['w'], D3['core']['h']
ax.add_patch(Rectangle((0, 0), d3w, d3h, fc='none', ec='#500000', lw=0.9, ls=(0, (6, 3))))
ax.text(d3w - 4, d3h - 6, 'floorplan estimate core', ha='right', va='top', fontsize=5, color='#500000')
ax.set_title(f'Core placement with real block sizes: core {CORE_W / 1000:.3f} × {CORE_H / 1000:.3f} mm '
             f'(estimate {d3w / 1000:.3f} × {d3h / 1000:.3f} mm), die ≈ {DIE[0] / 1000:.2f} × {DIE[1] / 1000:.2f} mm', fontsize=8, loc='left')
ax.text(0, -18, 'Hatched = routing ring and bus channels (no blocks). Maroon = test-structure blocks; dashed maroon = the floorplan-estimate core outline.',
        fontsize=5.5, va='top')
ax.set_xlim(-10, CORE_W + 10); ax.set_ylim(-40, CORE_H + 10); ax.set_aspect('equal'); ax.axis('off')
fig.tight_layout()
fig.savefig(H / 'place_real.png', dpi=300)

print(f'core {CORE_W} × {CORE_H} (d3 {d3w} × {d3h}), die ≈ {DIE}, inside {inside}, ring {ring_ok}')
print('\n'.join(LINES))
print('min gaps:', GAPS[:8])
