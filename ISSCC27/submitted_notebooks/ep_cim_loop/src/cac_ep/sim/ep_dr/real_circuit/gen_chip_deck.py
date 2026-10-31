"""칩 전체 덱 — 레지스터 5 개·동작 decoder·줄마다 MUX 까지 넣고 동작 하나씩 확인 (README §13, 10/25 사용자 "각 동작에 대해서 시프트
레지스트랑 먹스 로직까지 포함한 걸로 일단 회로가 돌아가는지 한번 볼래 … 그냥 한 장씩만").

--test read : reset → DATA SR 에 학습 표본 한 장 (49 bit) + Din 3 bit 를 52 클록으로 넣고 latch → 행·열 token 0 번 → READ 로 바꿔
              free 출력을 Python 과 비교 → 감지: SEL_EN·WU 클록으로 셀 칸을 훑고 칸마다 COL token 을 한 칸씩 민다
              (first stage = 행 0 × 열 0…, last stage = 행 100 × 열 0…). 크로스바 셀은 gen_sys_deck.py 와 같은 정적 sinh + R_on.
크로스바·WU·nudge 주입기 부분은 gen_sys_deck.py 를 복사해 고침. 디지털은 chip_lib.py (0 / VDD), WU 클록은 ±2.5 V.
--test write: (v2, 1T1R 쓰기) reset → token 을 (행 2, 열 1) 로 → verify → SET → verify → RESET → verify → FORM (SET, 더 큰 V) → verify
              → 열 token 한 칸 → 같은 행 이웃 (억제된 셀) verify. 셀은 VA RRAM + 접근 nFET W 3 µm (선택 행·선택 열·대각 이웃 하나만).
v2 (10/25 밤): chip_lib v2 — 디지털 ±2.5 V, V_W 버스 하나 (WBUF), 선택 안 된 열 = V_W, WL 끔 = VSS. v1 (0 / VDD, V/2) = chip_read0.
쓰임: python gen_chip_deck.py --test read --name chip_read1 --slots 4 / --test write --name chip_write0  → decks/<name>.sp + _ref.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from chip_lib import and2, global_decode, lib                     # noqa: E402
from circuit import D_IS, D_N, NONE, V_REF, row_drive             # noqa: E402
from data import load_task                                       # noqa: E402
from solver import cell_voltage, solve                           # noqa: E402
from train import layout_of                                      # noqa: E402
from wu_lib import primitives, wu_subckt                         # noqa: E402

OLY = '/home/grads/s/seokjindaveoh/work'
ap = argparse.ArgumentParser()
ap.add_argument('--test', choices=['read', 'write'], default='read')
ap.add_argument('--name', default='chip_read0')
ap.add_argument('--weights', default=str(HERE.parent / 'out' / 'weights' / 'nostab_5bit.npz'))
ap.add_argument('--key', default='5b_s0')
ap.add_argument('--sample', type=int, default=0)
ap.add_argument('--slots', type=int, default=4, help='감지 칸 수 (칸마다 열 token 한 칸)')
ap.add_argument('--lib', default=f'{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice')
ap.add_argument('--hog', default=f'{OLY}/sern_hog/char/decks/hog_tr.spice')
ap.add_argument('--tc', type=float, default=10e-9, help='레지스터 클록 주기')
ap.add_argument('--v_set', type=float, default=2.0)
ap.add_argument('--v_rst', type=float, default=1.8)
ap.add_argument('--v_form', type=float, default=2.3)
ap.add_argument('--v_wl', type=float, default=2.5, help='쓰기 때 선택 WL')
ap.add_argument('--v_rd', type=float, default=0.2)
ap.add_argument('--pw', type=float, default=10e-9)
ap.add_argument('--g0', type=float, default=50e-6)
ap.add_argument('--rc', type=int, nargs=2, default=[2, 1], help='쓰기 시험 셀 (행, 열)')
a = ap.parse_args()

W = np.load(a.weights)
LAY = layout_of(W)
c = {i['key']: i for i in json.loads(str(W['info']))}[a.key]['config']
G = W[f'{a.key}/G_best']
X, y = load_task('train')
s, lab = X[a.sample:a.sample + 1], int(y[a.sample])
t = np.where(np.eye(LAY.n_out)[lab] > 0, 1.0, -1.0)
u = torch.as_tensor(row_drive(LAY, s, c['a']))
Gt = torch.as_tensor(G)[None]
kw = dict(r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'], out_diode=not c['no_out_clamp'])
vh_f, vy_f, _ = solve(LAY, Gt, u, **kw)
d = (vy_f[:, 0::2] - vy_f[:, 1::2])[0].numpy()
e = np.sign(t - d)
inj = torch.as_tensor(np.stack([c['beta'] * e, -c['beta'] * e], 1).reshape(1, -1))
vh_n, vy_n, _ = solve(LAY, Gt, u, i_nudge=inj, v0=(vh_f, vy_f), **kw)
Vf, Vn = cell_voltage(LAY, u, vh_f, vy_f)[0].numpy(), cell_voltage(LAY, u, vh_n, vy_n)[0].numpy()
NR, NC = LAY.r_used, LAY.cols                                     # 쓰는 행 106, 열 64 (hidden 60 + 남는 4)
NRX = len(LAY.r_x) + len(LAY.r_b)                                 # ROW1 이 맡는 행 (입력 + bias)
NF, PF = 'sky130_fd_pr__nfet_g5v0d10v5', 'sky130_fd_pr__pfet_g5v0d10v5'
TC = a.tc


# ── 밖 (FPGA) 파형. 디지털 패드는 레벨 변환 뒤 ±2.5 V (v2), WU 클록 ±2.5 V, 아날로그 패드는 값 그대로
def put(w, nm, t0, v):
    s_ = w.setdefault(nm, [(0.0, 0)])
    if s_[-1][1] != v:
        s_ += [(t0, s_[-1][1]), (t0 + 0.2e-9, v)]


def clkpulse(nm, t0):
    put(wv, nm, t0 + TC / 2, 1); put(wv, nm, t0 + 0.8 * TC, 0)


def aput(nm, t0, v):
    s_ = ana.setdefault(nm, [(0.0, v)])
    if s_[-1][1] != v:
        s_ += [(t0, s_[-1][1]), (t0 + 1e-9, v)]


wv, clk, ana = {}, {}, {}
put(wv, 'rst', 2e-9, 1); put(wv, 'rst', 15e-9, 0)
slots, meas_w, bits = [], [], []
r_s, c_s = a.rc
if a.test == 'read':
    bits = [int(x > 0) for x in s[0]] + [int(x > 0) for x in e]   # DATA: D_0…D_48, Din_0…Din_2 (먼저 넣은 bit 가 끝 = q51)
    T_D = 20e-9
    for j in range(len(bits)):
        t0 = T_D + j * TC
        put(wv, 'data_d', t0, bits[len(bits) - 1 - j]); clkpulse('data_clk', t0)
        if j == 0:                                                # token 4 개를 0 번에
            for r in ('row1', 'row2', 'col1', 'col2'):
                put(wv, f'{r}_d', t0, 1); clkpulse(f'{r}_clk', t0); put(wv, f'{r}_d', t0 + TC, 0)
    t_ld = T_D + len(bits) * TC + 5e-9
    put(wv, 'data_ld', t_ld, 1); put(wv, 'data_ld', t_ld + 0.8 * TC, 0)
    t_read = t_ld + 20e-9
    put(wv, 'm1', t_read, 1); put(wv, 'm0', t_read, 1)            # READ
    t_inf = t_read + 120e-9
    put(wv, 'wu_en', t_inf + 10e-9, 1)
    T_SEL, T_ABS, T_LAT, SLOT = 100e-9, 290e-9, 20e-9, 480e-9
    t0 = t_inf + 30e-9
    for n in range(a.slots):
        put(wv, 'sel_en', t0, 1); put(clk, 'ck', t0 + T_SEL, 1)
        tm = t0 + T_SEL + T_ABS + 10e-9
        put(clk, 'ck3', tm - 10e-9, 1); put(clk, 'lat', tm, 1); put(clk, 'lat', tm + T_LAT, 0)
        t1 = tm + T_LAT + 20e-9
        put(wv, 'sel_en', t1, 0); put(clk, 'ck', t1, 0); put(clk, 'ck3', t1, 0)
        slots.append((n, tm, tm + T_LAT + 10e-9))
        for r in ('col1', 'col2'):
            put(wv, f'{r}_clk', t1 + 2e-9, 1); put(wv, f'{r}_clk', t1 + 8e-9, 0)
        t0 += SLOT
    tend = t0
    for nm, v in (('vrup', -c['v_b']), ('vrdn', c['v_b']), ('vwl', 0.0), ('vwh', 0.0), ('vwlo', 0.0)):
        aput(nm, 0, v)
else:
    t_inf = t_read = 0.0
    def token(reg, pos, t0):                                      # 1 을 넣고 pos 칸 더 민다
        put(wv, f'{reg}_d', t0, 1)
        for j in range(pos + 1):
            clkpulse(f'{reg}_clk', t0 + j * TC)
        put(wv, f'{reg}_d', t0 + TC, 0)
        return t0 + (pos + 1) * TC
    assert r_s < NRX
    t = max(token('row1', r_s, 20e-9), token('col1', c_s, 20e-9)) + 10e-9
    for nm, v in (('vrup', 2.5), ('vrdn', -2.5), ('vwl', a.v_wl), ('vwh', 0.0), ('vwlo', 0.0)):
        aput(nm, 0, v)                                            # 쓰기 동안 δ clamp 다이오드는 역바이어스
    put(wv, 'm1', t, 1)                                           # WRITE (10)

    def verify(tag, t):                                           # v2b: V_W 버스 = V_RD (SET 극성, 긴 WP), 선택 열 → verify 버스
        put(wv, 'pv', t, 1); aput('vwh', t, a.v_rd); put(wv, 'sel_en', t + 2e-9, 1); put(wv, 'wp', t + 4e-9, 1)
        meas_w.append(('i', tag, t + 27e-9)); put(wv, 'wp', t + 30e-9, 0); put(wv, 'sel_en', t + 31e-9, 0)
        aput('vwh', t + 33e-9, 0.0); put(wv, 'pv', t + 34e-9, 0)
        return t + 42e-9

    def pulse(tag, t, pol, v):
        put(wv, 'pol', t, pol)
        aput('vwh', t, v if pol == 0 else 0.0); aput('vwlo', t, 0.0 if pol == 0 else -v)
        put(wv, 'sel_en', t + 4e-9, 1); put(wv, 'wp', t + 8e-9, 1); meas_w.append(('v', tag, t + 8e-9 + a.pw / 2))
        put(wv, 'wp', t + 8e-9 + a.pw, 0); put(wv, 'sel_en', t + 12e-9 + a.pw, 0)
        aput('vwh', t + 14e-9 + a.pw, 0.0); aput('vwlo', t + 14e-9 + a.pw, 0.0); put(wv, 'pol', t + 16e-9 + a.pw, 0)
        return t + 20e-9 + a.pw
    t = verify('v0', t)
    t = pulse('set', t, 0, a.v_set); t = verify('v1', t)
    t = pulse('rst', t, 1, a.v_rst); t = verify('v2', t)
    put(wv, 'm1', t, 0); put(wv, 'm0', t, 1)                      # FORM (01): SET 을 더 큰 V 로
    t = pulse('form', t + 2e-9, 0, a.v_form)
    put(wv, 'm1', t, 1); put(wv, 'm0', t, 0)                      # 다시 WRITE
    t = verify('v3', t + 2e-9)
    clkpulse('col1_clk', t); t += TC + 2e-9                       # 열 token 한 칸 → 같은 행 이웃 (억제됐던 셀)
    t = verify('vn', t)
    tend = t

# ── 덱
OLYVA = f"{OLY}/ep_demo/char/va/sky130_fd_pr_reram__reram_cell.va"
L = [f"* {a.name}: chip v2 (registers + mode decoder + line MUX + write buffer + 2 crossbars + WU x2), test {a.test}, {a.key}, "
     f"sample {a.sample} label {lab}", ".option post=0 ingold=2 numdgt=8 measdgt=8 method=gear", ".temp 25",
     ".option accurate relv=1e-7 absv=1e-10 reli=1e-7 absi=1e-15",
     f".lib '{a.lib}' tt", ".param cc=100f rz=3k nls=1", f".include '{a.hog}'",
     "Vdd vdd 0 2.5", "Vss vss 0 -2.5",
     "Xbias vbn vbp vbpc vdd vss HOG_BIAS", "Vbnc vbnc 0 -1.0", "Vbpc vbpc 0 0.7"]
if a.test == 'write':
    L += [f'.hdl "{OLYVA}"', ".param tstep=50p"]
L += primitives() + wu_subckt(1e6, 20e-15, 'pa_sa', 20e-15, 2.0) + lib()
for nm, w in sorted(wv.items()):
    L.append(f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.5e} {2.5 if b else -2.5}" for x, b in w) + ")")
for nm in ('data_d', 'data_clk', 'data_ld', 'row1_d', 'row1_clk', 'row2_d', 'row2_clk', 'col1_d', 'col1_clk', 'col2_d', 'col2_clk',
           'sel_en', 'wu_en', 'm1', 'm0', 'pv', 'pol', 'wp'):
    if nm not in wv:
        L.append(f"V{nm} {nm} 0 -2.5")
for nm in ('ck', 'ck3', 'lat'):
    w = clk.get(nm, [(0.0, 0)])
    L.append(f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.5e} {2.5 if b else -2.5}" for x, b in w) + ")")
L.append("Vlatb latb 0 PWL(" + " ".join(f"{x:.5e} {-2.5 if b else 2.5}" for x, b in clk.get('lat', [(0.0, 0)])) + ")")
for nm, w in sorted(ana.items()):
    L.append(f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.5e} {v:.4f}" for x, v in w) + ")")
L += [f"Vraip raip 0 {c['a']}", f"Vraim raim 0 {-c['a']}"]
L += global_decode() + ["XWB wp pol vw vwh vwlo vdd vss WBUF"]
# ── 레지스터
L += ["XIld data_ld data_ldb vdd vss INV"]
prev = 'data_d'
for k in range(LAY.n_in + LAY.n_out):                             # DATA: q_k = bits[k]
    L += [f"XFd{k} {prev} data_clk rst rstb dq{k} vdd vss DFFR", f"XLd{k} dq{k} data_ld data_ldb dl{k} dlb{k} vdd vss DLATCH"]
    prev = f'dq{k}'
for r, n in (('row1', NRX), ('row2', len(LAY.r_y)), ('col1', len(LAY.c_h)), ('col2', len(LAY.c_h))):
    prev = f'{r}_d'
    for k in range(n):
        L.append(f"XF{r}{k} {prev} {r}_clk rst rstb {r}q{k} vdd vss DFFR")
        prev = f'{r}q{k}'
# ── 줄마다 decoder (두 배열 공유) + 배열마다 MUX
RO = ['wsel', 'wz', 'sns', 'wlv', 'wlw', 'wl0']
CO = ['wvw', 'wz', 'vfy', 'sns1', 'sns2']
L.append("Vlo lo 0 -2.5")
for r in range(NR):
    tok = f'row1q{r}' if r < NRX else f'row2q{r - NRX}'
    L.append(f"XRL{r} {tok} sel_en PROG VER SENSE READb WRANY " + ' '.join(f'r{r}{o} r{r}{o}b' for o in RO) + " vdd vss ROWL")
for cc in range(NC):
    t1, t2 = (f'col1q{cc}', f'col2q{cc}') if cc in LAY.c_h else ('lo', 'lo')
    L.append(f"XCL{cc} {t1} {t2} sel_en PROG VER SENSE WRANY " + ' '.join(f'c{cc}{o} c{cc}{o}b' for o in CO) + " vdd vss COLL")
for i in range(LAY.n_in):                                         # 입력 구동 게이트 (공유): a_i = READ·D_i, b_i = READ·D̄_i
    L += and2('READ', f'dl{i}', f'ga{i}', f'gab{i}', f'g{i}a') + and2('READ', f'dlb{i}', f'gb{i}', f'gbb{i}', f'g{i}b')
for k in range(LAY.n_out):                                        # nudge 주입기 SW: SW1·SW3 = READ·Din, SW2·SW4 = READ·D̄in
    L += and2('READ', f'dl{LAY.n_in + k}', f'sp{k}', f'spb{k}', f'n{k}p') + and2('READ', f'dlb{LAY.n_in + k}', f'sm{k}', f'smb{k}', f'n{k}m')
L += [f"XMPref pref pref vdd vdd {PF} w=42 l=2 nf=8", f"Iprf pref vss {c['beta']:.9e}",
      f"XMNref nref nref vss vss {NF} w=15 l=2 nf=3", f"Inrf vdd nref {c['beta']:.9e}"]
TOX, TFREF, IK1, VREFv = 5.0e-9, 4.7249e-9, 6.140e-5, 0.430
tf_for_g = lambda g: TOX + (TOX - TFREF) * np.log(g * 0.1 / (IK1 * np.sinh(0.1 / VREFv)))
wcells = sorted({(r_s, cc) for cc in range(NC)} | {(r, c_s) for r in range(NR)} | {(r_s + 1, c_s + 1)})
for p in 'fn':
    rn = lambda r: f'{p}r{r}'
    cn = lambda cc: f'{p}c{cc}'
    for r in range(NR):
        bus = f'R1{p}' if r < NRX else f'R2{p}'
        L.append(f"X{p}RM{r} {rn(r)} {p}wl{r} {bus} vw vwl " + ' '.join(f'r{r}{o} r{r}{o}b' for o in RO) + " vdd vss ROWM")
    for i in range(LAY.n_in):
        for r, gu, gd in ((LAY.r_x[2 * i], f'ga{i}', f'gb{i}'), (LAY.r_x[2 * i + 1], f'gb{i}', f'ga{i}')):
            L += [f"X{p}Dp{r} {rn(r)} {gu} raip vss {NF} w=1000 l=0.5 nf=200", f"X{p}Dm{r} {rn(r)} {gd} raim vss {NF} w=1000 l=0.5 nf=200"]
    for r, rail in ((LAY.r_b[0], 'raip'), (LAY.r_b[1], 'raim')):
        L.append(f"X{p}Db{r} {rn(r)} READ {rail} vss {NF} w=1000 l=0.5 nf=200")
    for cc in range(NC):
        L.append(f"X{p}CM{cc} {cn(cc)} vw vbus{p} C1{p} C2{p} " + ' '.join(f'c{cc}{o} c{cc}{o}b' for o in CO) + " vdd vss COLM")
        if cc not in LAY.c_h:
            L.append(f"X{p}SP{cc} {cn(cc)} 0 READ READb vdd vss TG")
    if a.test == 'read':                                          # 셀: 정적 sinh + R_on (WL 은 READ 에서 모두 VDD)
        for r, cc in zip(*np.nonzero(LAY.kind != NONE)):
            A, B = rn(r), cn(cc)
            L += [f"R{p}_{r}_{cc} {A} {p}m{r}_{cc} {c['r_on']}",
                  f"G{p}_{r}_{cc} {p}m{r}_{cc} {B} CUR='{G[r, cc]:.12e}*{V_REF}*sinh((V({p}m{r}_{cc})-V({B}))/{V_REF})'"]
    else:                                                         # 셀: VA RRAM (TE = 행) + 접근 nFET W 3 µm (게이트 = WL)
        for r, cc in wcells:
            L += [f"X{p}R{r}_{cc} {rn(r)} {p}nd{r}_{cc} sky130_fd_pr_reram__reram_cell Tfilament_0={tf_for_g(a.g0):.6e} t_step=tstep",
                  f"X{p}A{r}_{cc} {p}nd{r}_{cc} {p}wl{r} {cn(cc)} vss {NF} w=3 l=0.5"]
    for cc in LAY.c_h:
        nd = cn(cc)
        L += [f"R{p}da_{nd} {nd} {p}da_{nd} {c['r_ser']}", f"D{p}a_{nd} {p}da_{nd} vrup dlv1",
              f"D{p}b_{nd} vrdn {p}db_{nd} dlv1", f"R{p}db_{nd} {p}db_{nd} {nd} {c['r_ser']}", f"C{p}n_{nd} {nd} 0 100f"]
    L += [f"C{p}n_r{r} {rn(r)} 0 100f" for r in LAY.r_y]
    L += [f"Vver{p} vbus{p} 0 0"]                                 # verify 버스 = 밖 전류계
L.append(f".model dlv1 d (level=1 is={D_IS} n={D_N} rs=0)")
for j in range(LAY.n_out):
    yp, ym = f'nr{LAY.r_y[2 * j]}', f'nr{LAY.r_y[2 * j + 1]}'
    L += [f"XMP{j} ip{j} pref vdd vdd {PF} w=42 l=2 nf=8", f"XMN{j} in{j} nref vss vss {NF} w=15 l=2 nf=3",
          f"XSW1_{j} ip{j} {yp} sp{j} spb{j} vdd vss TG", f"XSW2_{j} ip{j} {ym} sm{j} smb{j} vdd vss TG",
          f"XSW3_{j} in{j} {ym} sp{j} spb{j} vdd vss TG", f"XSW4_{j} in{j} {yp} sm{j} smb{j} vdd vss TG"]
L += [f"Cb{b} {b} 0 200f" for b in ('R1f', 'C1f', 'R1n', 'C1n', 'R2f', 'C2f', 'R2n', 'C2n')] + ["Cvw vw 0 1p"]
L += ["XWU1 R1f C1f R1n C1n ck ck3 lat latb lq1 sen1 absf1 absn1 q1a q2a vbn vbp vbnc vbpc vdd vss WU",
      "XWU2 R2f C2f R2n C2n ck ck3 lat latb lq2 sen2 absf2 absn2 q1b q2b vbn vbp vbnc vbpc vdd vss WU"]
# ── 측정
if a.test == 'read':
    L += [f".meas tran fy{j} find v(fr{r}) at={t_inf:.5e}" for j, r in enumerate(LAY.r_y)]
    L += [f".meas tran ny{j} find v(nr{r}) at={t_inf:.5e}" for j, r in enumerate(LAY.r_y)]
    L += [f".meas tran fx{k} find v(fr{r}) at={t_inf:.5e}" for k, r in enumerate(LAY.r_x[:4])]
    for n, tm, th in slots:
        L += [f".meas tran lq1_{n} find v(lq1) at={th:.5e}", f".meas tran lq2_{n} find v(lq2) at={th:.5e}"]
        L += [f".meas tran b{k}{bn}{p}_{n} find v({bn}{k}{p}) at={tm:.5e}" for k in (1, 2) for bn in ('R', 'C') for p in 'fn']
    L += [f".meas tran idd avg i(Vdd) from={t_read:.5e} to={tend:.5e}", f".meas tran iss avg i(Vss) from={t_read:.5e} to={tend:.5e}",
          f".tran 0.1n {tend:.6e}", ".end"]
else:
    pick = {'t': (r_s, c_s), 'nb': (r_s, c_s + 1), 'cm': (r_s + 1, c_s), 'dg': (r_s + 1, c_s + 1)}
    for kind, tag, tm in meas_w:
        for p in 'fn':
            if kind == 'i':
                L.append(f".meas tran i_{tag}_{p} find i(Vver{p}) at={tm:.5e}")
            else:
                L += [f".meas tran v_{tag}_{p}_{k} find v({p}r{r},{p}nd{r}_{cc}) at={tm:.5e}" for k, (r, cc) in pick.items()]
                L += [f".meas tran vrow_{tag}_{p} find v({p}r{r_s}) at={tm:.5e}", f".meas tran vcol_{tag}_{p} find v({p}c{c_s}) at={tm:.5e}",
                      f".meas tran vcolu_{tag}_{p} find v({p}c{c_s + 1}) at={tm:.5e}", f".meas tran vwl_{tag}_{p} find v({p}wl{r_s}) at={tm:.5e}",
                      f".meas tran vwlu_{tag}_{p} find v({p}wl{r_s + 1}) at={tm:.5e}"]
        if kind == 'v':
            L.append(f".meas tran vbus_{tag} find v(vw) at={tm:.5e}")
    L += [f".tran 20p {tend:.6e}", ".end"]
(HERE / 'decks').mkdir(exist_ok=True)
(HERE / 'decks' / f'{a.name}.sp').write_text("\n".join(L) + "\n")
# ── 정답
ci = lambda rc: dict(row=int(rc[0]), col=int(rc[1]), vf=float(Vf[rc]), vn=float(Vn[rc]), delta=float(abs(Vn[rc]) - abs(Vf[rc])),
                     reset=bool(abs(Vn[rc]) - abs(Vf[rc]) >= 0))
cells1 = [(0, n) for n in range(a.slots)]; cells2 = [(int(LAY.r_y[0]), n) for n in range(a.slots)]
json.dump(dict(args=vars(a), test=a.test, label=lab, e=e.tolist(), bits=bits, vy_f=vy_f[0].tolist(), vy_n=vy_n[0].tolist(),
               pred=int(np.argmax(d)), cells1=[ci(x) for x in cells1] if a.test == 'read' else [],
               cells2=[ci(x) for x in cells2] if a.test == 'read' else [], meas_w=meas_w, t_inf=t_inf, tend=tend),
          open(HERE / 'decks' / f'{a.name}_ref.json', 'w'), indent=1)
print(f"{a.name}.sp: {len(L)} 줄, test {a.test}, t_end {tend*1e9:.0f} ns, label {lab}, Python 예측 {int(np.argmax(d))}")
