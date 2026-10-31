#!/usr/bin/env python3
"""col_blk 배치도 생성기 (10/28) — 열 MUX 매크로 (TGW 1 + TG 4 / 열, 남는 열은 TG 하나 더) 와 δ clamp (hidden 열마다) 의 자리,

열 pitch 5.115 µm 에 매크로 폭 5.52 µm (TG·TGW) 라 한 줄에 열마다 하나씩 못 놓는다 → 줄 (가로 띠) 로 나눔:
  위 (배열 쪽, 북) → 아래:
    clamp 줄  : clamp_d2r 60 개를 열 pitch 그대로 맞붙임 (폭 5.115, col 핀 = 매크로 col 띠, rail vrailp·vrailm·VSS 가 이어짐)
    TGW 2 줄  : 짝수 열 (아래 줄, r0) / 홀수 열 (위 줄, mx), 매크로 가운데 = 열 x. 두 줄이 가운데 VDD rail 을 같이 씀
    std 셀 N  : decoder·token DFF (place 가 자리를 정함)
    TG 5 줄   : 8 열 묶음마다 TG 7 개를 맞붙인 덩어리 (덩어리 사이 2.28 µm). 줄 1–4 = 종류별 (T2 vw / T4 vbus / T5 C1 / T6 C2),
                묶음마다 종류별로 빠지는 열을 서로 다르게 골라 (순열 전수) 줄 0 에 넘김 → 줄 0 = 넘친 32 개 + 남는 열 SP TG 4 개를
                1-D 합법화 (Abacus 식). 비용 = Σ(TG 의 col 핀 x − 열 x)².
                줄 방향 r0 / mx 번갈아 → 이웃 줄이 같은 rail (VDD 또는 VSS) 을 맞댐
    std 셀 S  : decoder·token DFF
  매크로 줄 rail 은 줄 경계마다 met1 띠 (VDD/VSS) 로 줄 끝까지 잇고, 블록 서·동 끝 PG 자리 (met2 stripe) 에서 std 셀 전원과 묶는다.
  매크로끼리 맞붙인 틈 (nwell 0.12 µm, psdm 0.12 µm) 은 후처리 (add_pg_labels_col.py) 가 줄마다 nwell·psdm·hvi 띠로 메움 (cb_rows.json).
      col_rows.json (후처리), tb/tb_col_blk.v (매크로 연결까지 보는 testbench), 화면에 요약
쓰임: python3 gen_colblk.py [--ns 7 --nn 7 --halo 2.5]   (기본 = 서명한 판, 잡 721186. 10+10·8+8 도 통과: 잡 721169·721178)
"""
import argparse
import json
import math
from pathlib import Path

H = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--ns', type=int, default=7, help='std 셀 줄 수 (남쪽 영역)')
ap.add_argument('--nn', type=int, default=7, help='std 셀 줄 수 (TG 와 TGW 사이 영역)')
ap.add_argument('--halo', type=float, default=2.5, help='std 셀 줄 경계 ↔ 매크로 bbox 간격 (µm)')
a = ap.parse_args()

PITCH, NC, NH = 5.115, 64, 60
TGW_, TGH, TGWH = 5.52, 9.165, 18.165            # TG·TGW 폭, TG 높이, TGW 높이
CLW, CLH = 5.115, 9.80                           # clamp
RH, SITE = 4.07, 0.48
PGZ = 2.4                                        # 서·동 끝 PG stripe 자리 (core 안)
MG = {'l': 1.5, 'b': 1.5, 'r': 1.5, 't': 2.0}
# 매크로 핀 x (매크로 왼쪽 기준, LEF): a 0.455–0.755, b (TG) 1.245–1.545, b (TGW) 4.405–4.705
PIN_A, PIN_B_TG, PIN_B_TGW = 0.605, 1.395, 4.555
r5 = lambda v: round(round(v / 0.005) * 0.005, 3)


def xc(c):                                       # 열 c 의 x (core 기준) = col 핀 가운데
    return PGZ + TGW_ / 2 + c * PITCH


Wc = math.ceil((PGZ + (NC - 1) * PITCH + TGW_ + PGZ) / SITE - 1e-9) * SITE

# ── 세로 배치 (core 기준, 아래 → 위)
yS1 = a.ns * RH
yT0 = r5(yS1 + a.halo)
NTG = 5
yT1 = r5(yT0 + NTG * TGH)
kN0 = math.ceil((yT1 + a.halo) / RH - 1e-9)
yN0, yN1 = r5(kN0 * RH), r5((kN0 + a.nn) * RH)
need = yN1 + a.halo + 2 * TGWH + CLH
nrow = math.ceil(need / RH - 1e-9)
Hc = r5(nrow * RH)
yC0 = r5(Hc - CLH)                               # clamp 줄 = core 위 끝에 붙임 (남는 높이는 std N ↔ TGW 사이 간격으로)
yW1 = yC0
yW0 = r5(yW1 - 2 * TGWH)
keep_rows = list(range(0, a.ns)) + list(range(kN0, kN0 + a.nn))

# ── 매크로 자리
inst = []                                        # (이름, 셀, x, y, 방향, 연결 dict)


def add(name, cell, x, y, orient, conn):
    inst.append(dict(name=name, cell=cell, x=r5(x), y=r5(y), orient=orient, conn=conn))


for c in range(NH):                              # clamp: col 띠 (1.74–2.06) 가운데 1.90 = 열 x
    add(f'XCL_c{c}', 'clamp_d2r', xc(c) - 1.90, yC0, 'r0', dict(col=f'col[{c}]', vrailp='vrailp', vrailm='vrailm'))
for c in range(NC):                              # TGW: 짝수 = 아래 줄 r0, 홀수 = 위 줄 mx
    y, o = (yW0, 'r0') if c % 2 == 0 else (r5(yW0 + TGWH), 'mx')
    add(f'XT1_c{c}', 'cb_tgw_n20', xc(c) - TGW_ / 2, y, o, dict(a='vzero', b=f'col[{c}]', ctl=f'wz[{c}]', ctlb=f'wzb[{c}]'))

# TG 줄: 8 열 묶음마다 7 칸 (가운데 맞춤), 칸 왼쪽 x
slots = []
for g in range(NC // 8):
    left = (xc(8 * g) + xc(8 * g + 7)) / 2 - 7 * TGW_ / 2
    slots += [r5(left + k * TGW_) for k in range(7)]
TYPES = {  # 종류 → (col 핀 x, 연결)
    'T2': (PIN_B_TG, lambda c: dict(a='vw', b=f'col[{c}]', ctl=f'wvw[{c}]', ctlb=f'wvwb[{c}]')),
    'T4': (PIN_A, lambda c: dict(a=f'col[{c}]', b='vbus', ctl=f'vfy[{c}]', ctlb=f'vfyb[{c}]')),
    'T5': (PIN_A, lambda c: dict(a=f'col[{c}]', b='C1', ctl=f'sns1[{c}]', ctlb=f'sns1b[{c}]')),
    'T6': (PIN_A, lambda c: dict(a=f'col[{c}]', b='C2', ctl=f'sns2[{c}]', ctlb=f'sns2b[{c}]')),
    'SP': (PIN_A, lambda c: dict(a=f'col[{c}]', b='vzero', ctl='READ', ctlb='READb')),
}
ROW_TYPE = {1: 'T6', 2: 'T5', 3: 'T4', 4: 'T2'}   # 줄 0 (맨 아래) = 넘친 것 + SP


# 종류 줄 (1–4) 은 8 열 묶음마다 7 칸 → 열 하나씩 빠진다. 빠지는 열을 종류마다 다르게 골라 (묶음 안 순열 전수),
#   (종류 줄 핀 x − 열 x)² + (줄 0 에서 빠진 열들의 핀 x − 열 x)² 합이 최소가 되게 한다 (줄 0 이 한 곳에 몰리지 않게)
from itertools import permutations
over = []
tg_rows = {r: [] for r in range(NTG)}            # 줄 → [(칸, 종류, 열)]
TROWS = [4, 3, 2, 1]


def grp_cost(g, t, j):                           # 묶음 g, 종류 t, 열 8g+j 를 뺐을 때 종류 줄 비용과 칸 배정
    off = TYPES[t][0]
    cols = [8 * g + k for k in range(8) if k != j]
    return sum((slots[7 * g + k] + off - xc(c)) ** 2 for k, c in enumerate(cols)), cols


XL, XR = PGZ, PGZ + (NC - 1) * PITCH + TGW_


def abacus(tgts, xl, xr):
    """1-D 합법화 (Abacus 식 덩어리 합치기): 목표 왼쪽 x (오름차순) 에서 시작해 겹치면 덩어리로 묶어 평균 자리로.
    순서 유지, Σ dx² 최소, [xl, xr] 안. 덩어리 = [왼쪽 x, 개수, Σ(목표 − 덩어리 안 앞 원소 폭)]."""
    clumps = []
    for tgt in tgts:
        clumps.append([tgt, 1, tgt])
        while True:
            cl = clumps[-1]
            cl[0] = min(max(cl[2] / cl[1], xl), xr - cl[1] * TGW_)
            if len(clumps) > 1 and clumps[-2][0] + clumps[-2][1] * TGW_ > cl[0] + 1e-9:
                pv = clumps.pop(-2)
                cl[2] = pv[2] + cl[2] - cl[1] * pv[1] * TGW_
                cl[1] += pv[1]
                continue
            break
    xs = [x0 + i * TGW_ for x0, n, _ in clumps for i in range(n)]
    return xs, sum((x - t) ** 2 for x, t in zip(xs, tgts))


for g in range(NC // 8):
    best = None
    sp = [('SP', c) for c in range(NH, NC) if 8 * g <= c < 8 * g + 8]
    gl, gr = max(XL, xc(8 * g) - PITCH / 2 - 3.0), min(XR, xc(8 * g + 7) + PITCH / 2 + 3.0)
    for js in permutations(range(8), len(TROWS)):
        cost = sum(grp_cost(g, ROW_TYPE[r], j)[0] for r, j in zip(TROWS, js))
        ov = sorted([(ROW_TYPE[r], 8 * g + j) for r, j in zip(TROWS, js)] + sp, key=lambda tc: xc(tc[1]) - TYPES[tc[0]][0])
        _, c0 = abacus([xc(c) - TYPES[t][0] for t, c in ov], gl, gr)
        if best is None or cost + c0 < best[0]:
            best = (cost + c0, js)
    for r, j in zip(TROWS, best[1]):
        t = ROW_TYPE[r]
        _, cols = grp_cost(g, t, j)
        tg_rows[r] += [(7 * g + k, t, c) for k, c in enumerate(cols)]
        over.append((t, 8 * g + j))
over += [('SP', c) for c in range(NH, NC)]
# 줄 0 (넘친 32 개 + SP 4 개) 은 칸 묶음을 쓰지 않고 위 abacus 로 블록 매크로 영역 안에 (핀 x 를 열 x 에 맞춘 자리에서 시작)
over.sort(key=lambda tc: (xc(tc[1]) - TYPES[tc[0]][0], tc[0]))
row0, _ = abacus([xc(c) - TYPES[t][0] for t, c in over], XL, XR)
for (t, c), x in zip(over, row0):
    tg_rows[0].append((r5(x), t, c))
ORIENT_TG = ['r0', 'mx', 'r0', 'mx', 'r0']
dx_all = []
for r in range(NTG):
    y = r5(yT0 + r * TGH)
    for s, t, c in sorted(tg_rows[r]):
        off = TYPES[t][0]
        x = s if r == 0 else slots[s]
        dx_all.append(abs(x + off - xc(c)))
        add(f'X{t}_c{c}' if t != 'SP' else f'XSP_c{c}', 'cb_tg_n2', x, y, ORIENT_TG[r], TYPES[t][1](c))
# 인스턴스 이름 = 덱 COLM 의 XT1 (TGW)·XT2·XT4·XT5·XT6 + 남는 열 XSP + clamp XCL, 뒤에 _c<열>
names = [d['name'] for d in inst]
assert len(names) == len(set(names))
n_need = {'clamp_d2r': NH, 'cb_tgw_n20': NC, 'cb_tg_n2': 4 * NC + (NC - NH)}
for cell, n in n_need.items():
    assert sum(1 for d in inst if d['cell'] == cell) == n, cell
for c in range(NC):                              # 열마다 다 있는지
    want = {'XT1', 'XT2', 'XT4', 'XT5', 'XT6'} | ({'XCL'} if c < NH else {'XSP'})
    got = {d['name'].split('_c')[0] for d in inst if d['name'].endswith(f'_c{c}')}
    assert got == want, (c, got)

# ── 전원 띠 (macro 줄 rail): (넷, y0, y1). TG r0: VSS 0.185–0.685 / VDD 8.44–8.94, mx 는 위아래 바꿈
def rails(cell, y, o):
    h = {'cb_tg_n2': TGH, 'cb_tgw_n20': TGWH}[cell]
    vss, vdd = (0.185, 0.685), (h - 0.725, h - 0.225)
    if o == 'mx':
        vss, vdd = (h - 0.685, h - 0.185), (0.225, 0.725)
    return [('VSS', r5(y + vss[0]), r5(y + vss[1])), ('VDD', r5(y + vdd[0]), r5(y + vdd[1]))]


rl = []
for r in range(NTG):
    rl += rails('cb_tg_n2', yT0 + r * TGH, ORIENT_TG[r])
rl += rails('cb_tgw_n20', yW0, 'r0') + rails('cb_tgw_n20', yW0 + TGWH, 'mx')
rl += [('VSS', r5(yC0 + 0.15), r5(yC0 + 0.70))]  # clamp 기판 tap rail
rl.sort(key=lambda t: t[1])
bands = []
for n, y0, y1 in rl:                             # 1.5 µm 안의 같은 넷 rail 은 한 띠로 (맞댄 줄 경계)
    if bands and bands[-1][0] == n and y0 - bands[-1][2] < 1.5:
        bands[-1][2] = max(bands[-1][2], y1)
    else:
        bands.append([n, y0, y1])
for (n0, _, t0), (n1, b1, _) in zip(bands, bands[1:]):
    assert b1 - t0 > 0.3, ('띠 사이가 너무 가까움', n0, t0, n1, b1)

# ── 후처리 메움 (줄마다): nwell (VDD 쪽 끝까지) · psdm (VSS 쪽 끝까지) · hvi (줄 전체)
NW = {('cb_tg_n2', 'r0'): (4.095, TGH), ('cb_tg_n2', 'mx'): (0.0, TGH - 4.095),
      ('cb_tgw_n20', 'r0'): (7.095, TGWH), ('cb_tgw_n20', 'mx'): (0.0, TGWH - 7.095)}
PS = {('cb_tg_n2', 'r0'): (0.0, 0.81), ('cb_tg_n2', 'mx'): (TGH - 0.81, TGH),
      ('cb_tgw_n20', 'r0'): (0.0, 0.81), ('cb_tgw_n20', 'mx'): (TGWH - 0.81, TGWH + 0.10)}   # +0.10 = clamp psdm (0.075 위) 와 겹침
fill = []
rows_j = []
mrows = [(f'TG{r}', 'cb_tg_n2', r5(yT0 + r * TGH), ORIENT_TG[r]) for r in range(NTG)] + \
        [('TGW0', 'cb_tgw_n20', yW0, 'r0'), ('TGW1', 'cb_tgw_n20', r5(yW0 + TGWH), 'mx')]
xs = [d['x'] for d in inst if d['cell'] != 'clamp_d2r']
xm0, xm1 = r5(min(xs)), r5(max(xs) + TGW_)
for nm, cell, y, o in mrows:
    h = TGH if cell == 'cb_tg_n2' else TGWH
    ins = [d for d in inst if d['cell'] == cell and d['y'] == y]
    x0, x1 = min(d['x'] for d in ins), max(d['x'] for d in ins) + TGW_
    rows_j.append(dict(name=nm, cell=cell, y=y, h=h, orient=o, n=len(ins), x0=r5(x0), x1=r5(x1)))
    fill.append(('nwell', r5(xm0), r5(y + NW[(cell, o)][0]), r5(xm1), r5(y + NW[(cell, o)][1])))
    fill.append(('psdm', r5(xm0), r5(y + PS[(cell, o)][0]), r5(xm1), r5(y + PS[(cell, o)][1])))
fill.append(('hvi', xm0, yT0, xm1, yT1))
fill.append(('hvi', xm0, yW0, xm1, yW1))

# ── 핀 (core 기준; die 끝 좌표는 Tcl 에서)
west = ['sdi', 'rstb', 'col1_clk', 'col2_clk', 'sel_en', 'PROG', 'VER', 'SENSE', 'WRANY', 'lo', 'READ', 'READb']
_st = min(3.0, (yS1 - 5.0) / (len(west) - 1))         # std S 높이 안에 고르게 (최대 3 µm 간격)
pin_w = [(p, r5(3.0 + _st * k)) for k, p in enumerate(west)]
assert pin_w[-1][1] < yS1 - 1.0
rowy = {ROW_TYPE[r]: r5(yT0 + (r + 0.5) * TGH) for r in ROW_TYPE}
pin_e = [('vzero', r5(yW0 + TGWH), 1.0), ('vw', rowy['T2'], 1.0), ('vbus', rowy['T4'], 0.3),
         ('C1', rowy['T5'], 0.3), ('C2', rowy['T6'], 0.3)]
pin_rail = [('vrailp', r5(yC0 + 1.55), r5(yC0 + 2.10)), ('vrailm', r5(yC0 + 8.33), r5(yC0 + 8.88))]
x_clamp_end = r5(max(d['x'] for d in inst if d['cell'] == 'clamp_d2r') + CLW)
x_clamp_beg = r5(min(d['x'] for d in inst if d['cell'] == 'clamp_d2r'))

# ── col_fp.tcl
T = ['# col_fp.tcl — GENERATED by gen_colblk.py (손으로 고치지 말 것). 좌표 = core 왼쪽 아래 기준 µm (+ $cx1 / $cy1)',
     f'set FP_WC {Wc:.3f}', f'set FP_HC {Hc:.3f}',
     f'set FP_MG {{{MG["l"]} {MG["b"]} {MG["r"]} {MG["t"]}}}',
     f'set FP_KEEP_ROWS {{{" ".join(map(str, keep_rows))}}}',
     f'set FP_STD {{{{0 {yS1:.3f}}} {{{yN0:.3f} {yN1:.3f}}}}}',
     f'set FP_PGZ {PGZ}',
     f'set FP_XC0 {xc(0):.4f}', f'set FP_PITCH {PITCH}', f'set FP_NC {NC}',
     'proc fp_place_macros {cx1 cy1} {', '  set n 0']
for d in inst:
    T.append(f'  place_inst {d["name"]} [list [expr {{$cx1 + {d["x"]:.3f}}}] [expr {{$cy1 + {d["y"]:.3f}}}]] {d["orient"]} -fixed; incr n')
T += ['  return $n', '}']
T.append('set FP_BANDS {')
T += [f'  {{{n} {y0:.3f} {y1:.3f}}}' for n, y0, y1 in bands]
T.append('}')
T.append(f'set FP_BLOCK {{{{0 {yS1:.3f} {Wc:.3f} {yN0:.3f}}} {{0 {yN1:.3f} {Wc:.3f} {Hc:.3f}}}}}')
T.append('set FP_PIN_W {' + ' '.join(f'{{{p} {y:.3f}}}' for p, y in pin_w) + '}')
T.append('set FP_PIN_E {' + ' '.join(f'{{{p} {y:.3f} {w}}}' for p, y, w in pin_e) + '}')
T.append('set FP_PIN_RAIL {' + ' '.join(f'{{{p} {y0:.3f} {y1:.3f}}}' for p, y0, y1 in pin_rail) + '}')
T.append(f'set FP_CLAMP_X {{{x_clamp_beg:.3f} {x_clamp_end:.3f}}}')
T.append(f'set FP_TG_Y {{{yT0:.3f} {yT1:.3f}}}')
T.append(f'set FP_TGW_Y {{{yW0:.3f} {yW1:.3f}}}')
(H / 'col_fp.tcl').write_text('\n'.join(T) + '\n')

# ── col_macros.vh (merge_netlist.py 가 col_blk 모듈 안에 넣음)
V = ['  // col_macros.vh — GENERATED by gen_colblk.py']
for d in inst:
    V.append(f'  {d["cell"]} {d["name"]} (' + ', '.join(f'.{p}({n})' for p, n in d['conn'].items()) + ');')
(H / 'col_macros.vh').write_text('\n'.join(V) + '\n')

json.dump(dict(core=dict(w=Wc, h=Hc), std=[[0, yS1], [yN0, yN1]], rows=rows_j, fill=fill, bands=bands,
               clamp=dict(y=yC0, x0=x_clamp_beg, x1=x_clamp_end), insts=inst,
               col_x=[r5(xc(c)) for c in range(NC)]),
          open(H / 'col_rows.json', 'w'), indent=1)

# ── tb/tb_col_blk.v: 매크로 핀까지 보는 testbench (매크로 = 빈 모형, 핀 값만 읽음)
OUTS = ['wvw', 'wvwb', 'wz', 'wzb', 'vfy', 'vfyb', 'sns1', 'sns1b', 'sns2', 'sns2b']
A_PORTS = ['vw', 'vbus', 'C1', 'C2', 'vzero', 'vrailp', 'vrailm']


def expr(net):                                   # 핀에 기대하는 값 (testbench 식)
    if net.startswith('col['):
        return f'colv[{net[4:-1]}]'
    if net in A_PORTS:
        return f'av[{A_PORTS.index(net)}]'
    if net in ('READ', 'READb'):
        return net
    o, c = net[:-1].split('[')
    return f'r{o}[{c}]'


B = ['// tb_col_blk.v — GENERATED by gen_colblk.py: col_blk netlist (합성 뒤 / 배치·배선 뒤) 의 매크로 핀이 맞는 신호에 붙었는지 본다',
     '//   ctl·ctlb = chip_lib COLL 기준 모형 (tb/ref_coll.v) + token 사슬 모형, a·b = 블록 핀 (col[c]·vw·vbus·C1·C2·vzero) 에 준 무늬',
     '//   매크로는 빈 모형 (핀만), 값은 dut.<인스턴스>.<핀> 으로 읽음. 끝에 "TB_BLK: PASS/FAIL n"',
     '`timescale 1ns / 1ps',
     'module cb_tg_n2 (a, b, ctl, ctlb); inout a, b; input ctl, ctlb; endmodule',
     'module cb_tgw_n20 (a, b, ctl, ctlb); inout a, b; input ctl, ctlb; endmodule',
     'module clamp_d2r (col, vrailp, vrailm); inout col, vrailp, vrailm; endmodule',
     'module tb_col_blk;',
     f'    localparam NH = {NH}, NC = {NC};',
     '    reg sdi = 0, col1_clk = 0, col2_clk = 0, rstb = 0;',
     '    reg sel_en = 0, PROG = 0, VER = 0, SENSE = 0, WRANY = 0, lo = 0, READ = 0, READb = 1;',
     '    reg [NC-1:0] colv = 0;', '    reg [6:0] av = 0;',
     '    wire [NC-1:0] col;', '    assign col = colv;',
     '    wire vw, vbus, C1, C2, vzero, vrailp, vrailm;',
     '    assign {vrailm, vrailp, vzero, C2, C1, vbus, vw} = av;',
     '    col_blk dut (.col(col), .vw(vw), .vbus(vbus), .C1(C1), .C2(C2), .vzero(vzero), .vrailp(vrailp), .vrailm(vrailm),',
     '        .sdi(sdi), .rstb(rstb), .col1_clk(col1_clk), .col2_clk(col2_clk), .sel_en(sel_en), .PROG(PROG), .VER(VER),',
     '        .SENSE(SENSE), .WRANY(WRANY), .lo(lo), .READ(READ), .READb(READb));',
     '    reg [NH-1:0] m1 = 0, m2 = 0;',
     '    wire [NC-1:0] mt1 = {{(NC-NH){lo}}, m1};', '    wire [NC-1:0] mt2 = {{(NC-NH){lo}}, m2};',
     '    wire [NC-1:0] ' + ', '.join(f'r{o}' for o in OUTS) + ';',
     '    genvar g;',
     '    generate for (g = 0; g < NC; g = g + 1) begin : g_ref',
     '        ref_coll u (mt1[g], mt2[g], sel_en, PROG, VER, SENSE, WRANY, ' + ', '.join(f'r{o}[g]' for o in OUTS) + ');',
     '    end endgenerate',
     '    integer nerr = 0, ncmp = 0, npin = 0, i, c;',
     '    task chk(input [8*16-1:0] nm, input got, input exp);',
     '        begin npin = npin + 1; if (got !== exp) begin nerr = nerr + 1;',
     '            if (nerr <= 20) $display("MISMATCH %0s got %b exp %b", nm, got, exp); end end',
     '    endtask',
     '    task check;', '        begin', '            #20; ncmp = ncmp + 1;']
for d in inst:
    for p, n in d['conn'].items():
        B.append(f'            chk("{d["name"]}.{p}", dut.{d["name"]}.{p}, {expr(n)});')
B += ['        end', '    endtask',
      '    task pulse1(input b); begin sdi = b; #30; m1 = {m1[NH-2:0], sdi}; col1_clk = 1; #50; col1_clk = 0; #20; end endtask',
      '    task pulse2(input b); begin sdi = b; #30; m2 = {m2[NH-2:0], sdi}; col2_clk = 1; #50; col2_clk = 0; #20; end endtask',
      '    reg [31:0] seed = 32\'d20261028;',
      '    task rnd_all; begin {lo, sel_en, PROG, VER, SENSE, WRANY, READ} = $random(seed); READb = $random(seed);',
      '        colv = {$random(seed), $random(seed)}; av = $random(seed); check; end endtask',
      '    initial begin',
      '        rstb = 0; #100; rnd_all; rstb = 1; #50;',
      '        for (i = 0; i < NH; i = i + 1) pulse1($random(seed));',
      '        for (i = 0; i < NH; i = i + 1) pulse2($random(seed));',
      '        for (c = 0; c < 40; c = c + 1) rnd_all;',
      '        // 열 하나씩: col 무늬 = 열 c 만 1 (a·b 가 엉뚱한 열에 붙으면 잡힘), 전역 = 쓰기·verify·감지 조합',
      '        for (c = 0; c < NC; c = c + 1) begin',
      '            colv = 0; colv[c] = 1; av = 7\'b1010101; {lo, sel_en, PROG, VER, SENSE, WRANY} = 6\'b011001; READ = 1; READb = 0; check;',
      '            colv = ~colv; av = ~av; {lo, sel_en, PROG, VER, SENSE, WRANY} = 6\'b110111; READ = 0; READb = 1; check;',
      '        end',
      '        // token 하나 걷기 (COL1·COL2): 이웃 열 decoder 출력이 달라져 매크로 ctl·ctlb 가 엉뚱한 열에 붙으면 잡힘',
      '        rstb = 0; #50; m1 = 0; m2 = 0; rstb = 1; #50;',
      '        for (i = 0; i < NH; i = i + 1) begin pulse1(i == 0); pulse2(i == 0);',
      '            {lo, sel_en, PROG, VER, SENSE, WRANY} = 6\'b011111; READ = i[0]; READb = ~i[0]; check;',
      '            {lo, sel_en, PROG, VER, SENSE, WRANY} = 6\'b010010; check; end',
      '        for (i = 0; i < NH; i = i + 1) pulse1(~m1[NH-1]);',
      '        for (i = 0; i < NH; i = i + 1) pulse2(~m2[NH-1]);',
      '        for (c = 0; c < 40; c = c + 1) rnd_all;',
      '        #7 rstb = 0; m1 = 0; m2 = 0; #13; rnd_all;',
      '        $display("TB_BLK: checks %0d, pin compares %0d", ncmp, npin);',
      '        if (nerr == 0) $display("TB_BLK: PASS"); else $display("TB_BLK: FAIL %0d", nerr);',
      '        $finish;', '    end', 'endmodule', '']
(H / 'tb' / 'tb_col_blk.v').write_text('\n'.join(B))

# ── 요약
die_w, die_h = Wc + MG['l'] + MG['r'], Hc + MG['b'] + MG['t']
print(f'core {Wc:.2f} x {Hc:.2f} um (rows {nrow}, std rows S {a.ns} + N {a.nn}), die ≈ {die_w:.2f} x {die_h:.2f}')
print(f'y: std S 0–{yS1:.2f} | TG {yT0:.2f}–{yT1:.2f} | std N {yN0:.2f}–{yN1:.2f} | TGW {yW0:.2f}–{yW1:.2f} | clamp {yC0:.2f}–{Hc:.2f}')
print(f'macros: clamp {NH}, TGW {NC}, TG {4 * NC + NC - NH}; TG 줄별 개수 {[len(tg_rows[r]) for r in range(NTG)]} (칸 {len(slots)}/줄)')
print(f'TG col 핀 ↔ 열 x 차: 최대 {max(dx_all):.2f}, 평균 {sum(dx_all) / len(dx_all):.2f} um; 줄 0 종류 {sorted({t for _, t, _ in tg_rows[0]})}')
print(f'bands {len(bands)}, fill {len(fill)}, col x[0] = core + {xc(0):.4f}, x[63] = core + {xc(63):.4f}')
