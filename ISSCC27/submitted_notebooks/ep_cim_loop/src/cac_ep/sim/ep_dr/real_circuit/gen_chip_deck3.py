"""칩 전체 덱 v3 + 배열마다 write buffer (10/27, 사용자 "배열마다 하나씩 두면 좋지 않나? 그래 그렇게 하게") — gen_chip_deck2.py 사본을 고침.
바꾼 것: ⑥ WBUF 두 개 (XWBf → vwf, XWBn → vwn, 같은 wp·pol·VWH·VWLO), 배열마다 row·열 MUX 는 자기 V_W 만.
  ⑦ 쓰기 덱 열 부하: 열마다 --c_col (셀 128 개 접합 + 선 어림, 기본 0.4 pF) — v3 쓰기 덱은 선택 행·열·대각 셀만 있고 vw 에 1 pF 하나뿐이었음.
  ⑧ 측정: V_W 두 개, 선택 안 된 열 (이웃·먼 열) 의 펄스 시작 뒤 2·5 ns 전압, VWH 순간 전류. --probe 면 고른 node 파형 저장 (노트북 WRITE 파형).
아래는 gen_chip_deck2.py 원래 설명.
칩 전체 덱 v3 (10/26 핀 줄이기, README §13) — gen_chip_deck.py (v2b) 사본을 고침. v2b 는 그대로 둔다 (chip_read1·chip_write1).
바꾼 것 (사용자 10/26 "그래 1번부터 진행해봐"):
  ① 설정 레지스터 12 bit (chip_lib.CFG: MODE[1:0]·PV·POL·WU_EN·RD_OUT·DLOAD·TSEL[4:0]) — SLD 높음 + SCK 로 밀고, SLD 내리면 적용.
     MODE·PV·POL·WU_EN 패드와 DATA latch 패드가 없어짐.
  ② 레지스터 다섯 개 (DATA·ROW1·ROW2·COL1·COL2) 가 SCK·SDI 하나를 같이 씀 — SLD 낮을 때 TSEL 이 고른 레지스터만 민다.
  ③ 판독 TG: R2 버스 → VBUS_F·VBUS_N 패드 (RD_OUT). READ 에서 ROW2 token 으로 출력 행을 하나씩 골라 패드에서 읽는다.
     WRITE 에서는 같은 패드가 verify 전류계 (0 V).
  ④ 입력 구동 레일 = δ clamp 레일 (VRAILP = +a = clamp 아래 다이오드, VRAILM = −a = 위 다이오드). READ ±0.3 V, 쓰기 ∓2.5 V.
  ⑤ nudge β = HOG bias 기준 5 µA × 7.624 미러 (chip_lib.beta_mirror), 이상 전류원 Iprf·Inrf 없앰.
  ⑥ LATB 는 칩 안 inverter.
패드 (전원 VDD·VSS·0 V 빼고): 디지털 입력 9 (SCK SDI SLD RST SEL_EN WP CK CK3 LAT), 출력 2 (LQ1 LQ2),
  아날로그 10 (VRAILP VRAILM VWH VWLO VWL VBUS_F VBUS_N IBIAS VBNC VBPC). IBIAS 는 덱에서 HOG_BIAS 안 5 µA 전류원이 대신한다.
--test read : 설정 (TSEL 네 개) → SDI 1 → token 네 개 0 번 / 설정 (TSEL DATA) → 표본 49 bit + Din 3 bit / 설정 (READ, DLOAD, WU_EN,
              RD_OUT, TSEL ROW2) → 추론 → 출력 행 6 개를 VBUS 로 판독 (칸마다 ROW2 token 한 칸, 마지막에 SDI 1 로 0 번에 다시)
              → 설정 (RD_OUT 0, TSEL COL1·COL2) → 감지 칸 (v2b 와 같음, 칸마다 SCK 하나로 열 token 한 칸).
--test write: 설정 (TSEL ROW1·COL1) → token (행, 열) → verify → SET → verify → RESET → verify → FORM → verify → 열 token 한 칸 → 이웃 verify.
              동작이 바뀔 때마다 설정 12 bit 를 새로 민다 (PV·POL 도 설정 bit).
쓰임: python gen_chip_deck2.py --test read --name chip_read2 --slots 4 / --test write --name chip_write2 → decks/<name>.sp + _ref.json
      결과는 python parse_chip.py <name>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from chip_lib import CFG, and2, beta_mirror, config_block, global_decode, lib   # noqa: E402
from circuit import D_IS, D_N, NONE, V_REF, row_drive             # noqa: E402
from data import load_task                                       # noqa: E402
from solver import cell_voltage, solve                           # noqa: E402
from train import layout_of                                      # noqa: E402
from wu_lib import primitives, wu_subckt                         # noqa: E402


OLY = '/home/grads/s/seokjindaveoh/work'
ap = argparse.ArgumentParser()
ap.add_argument('--test', choices=['read', 'write'], default='read')
ap.add_argument('--name', default='chip_write3')
ap.add_argument('--weights', default=str(HERE.parent / 'out' / 'weights' / 'nostab_5bit.npz'))
ap.add_argument('--key', default='5b_s0')
ap.add_argument('--sample', type=int, default=0)
ap.add_argument('--slots', type=int, default=4, help='감지 칸 수 (칸마다 열 token 한 칸)')
ap.add_argument('--lib', default=f'{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice')
ap.add_argument('--hog', default=f'{OLY}/sern_hog/char/decks/hog_tr.spice')
ap.add_argument('--tc', type=float, default=10e-9, help='SCK 주기')
ap.add_argument('--t_ro', type=float, default=60e-9, help='출력 행 하나 판독 시간 (SEL_EN 켜고 잴 때까지)')
ap.add_argument('--c_pad', type=float, default=2e-12, help='VBUS 패드 용량 (READ)')
ap.add_argument('--v_set', type=float, default=2.0)
ap.add_argument('--v_rst', type=float, default=1.8)
ap.add_argument('--v_form', type=float, default=2.3)
ap.add_argument('--v_wl', type=float, default=2.5, help='쓰기 때 선택 WL')
ap.add_argument('--v_rd', type=float, default=0.2)
ap.add_argument('--pw', type=float, default=10e-9)
ap.add_argument('--g0', type=float, default=50e-6)
ap.add_argument('--rc', type=int, nargs=2, default=[2, 1], help='쓰기 시험 셀 (행, 열)')
ap.add_argument('--c_col', type=float, default=0.4e-12, help='쓰기 덱 열 하나의 부하 (셀 128 개 접합 + 선, 어림)')
ap.add_argument('--probe', action='store_true', help='고른 node 파형 저장 (post=1 probe)')
ap.add_argument('--seq', choices=['all', 'set', 'rst'], default='all', help='쓰기 순서: 전부 / verify·SET·verify 만 / verify·RESET·verify 만 (10/30, ngspice 를 구간별로)')
a = ap.parse_args()

W = np.load(a.weights)
LAY = layout_of(W)
c = {i['key']: i for i in json.loads(str(W['info']))}[a.key]['config']
assert abs(c['a'] - c['v_b']) < 1e-9, 'VRAIL 공유는 입력 구동 a = clamp v_b 일 때만'
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


# ── 밖 (FPGA) 파형. 디지털 패드는 레벨 변환 뒤 ±2.5 V, WU 클록 ±2.5 V, 아날로그 패드는 값 그대로
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


def shift(t0, bits):                                              # SLD 낮음: TSEL 이 고른 레지스터에 bits 를 차례로
    for j, b in enumerate(bits):
        put(wv, 'sdi', t0 + j * TC, b); clkpulse('sck', t0 + j * TC)
    t1 = t0 + len(bits) * TC
    put(wv, 'sdi', t1, 0)
    return t1


cur = {n: 0 for n in CFG}
n_cfg = [0]


def cfg(t0, **kv):                                                # 설정 12 bit 를 새로 밀고 SLD 를 내림 → 돌려준 시각 5 ns 전에 적용
    cur.update(kv)
    put(wv, 'sld', t0, 1)
    t1 = shift(t0 + 2e-9, [cur[n] for n in CFG][::-1])
    put(wv, 'sld', t1, 0)
    n_cfg[0] += 1
    return t1 + 5e-9


wv, clk, ana = {}, {}, {}
# RST 는 0 ns 부터 높게 (전원 켤 때 reset). 10/26 chip_write2 둘째 판: 0 ns 에 RST 가 낮으면 설정 레지스터가 아무 값 (READ) 으로 떠
# 입력 게이트가 켜지고 행이 VRAIL (쓰기 때 −2.5 V) 로 → 셀이 시작 전에 RESET 됨 (chip_write2_t0 로 확인)
wv['rst'] = [(0.0, 1)]; put(wv, 'rst', 15e-9, 0)
slots, meas_w, bits, ro = [], [], [], []
r_s, c_s = a.rc
VRAIL_RD = c['a']
if a.test == 'read':
    bits = [int(x > 0) for x in s[0]] + [int(x > 0) for x in e]   # DATA: D_0…D_48, Din_0…Din_2 (먼저 넣은 bit 가 끝 = q51)
    tt = cfg(20e-9, ts_row1=1, ts_row2=1, ts_col1=1, ts_col2=1)
    tt = shift(tt, [1]) + 2e-9                                    # token 네 개를 0 번에
    tt = cfg(tt, ts_row1=0, ts_row2=0, ts_col1=0, ts_col2=0, ts_data=1)
    tt = shift(tt, bits[::-1]) + 2e-9
    t_read = cfg(tt, m1=1, m0=1, dload=1, wu_en=1, rd_out=1, ts_data=0, ts_row2=1)
    t_inf = t_read + 120e-9
    tt = t_inf + 10e-9
    for j in range(len(LAY.r_y)):                                 # 출력 행 j → R2 버스 → VBUS 패드
        put(wv, 'sel_en', tt, 1); tm = tt + a.t_ro; ro.append((j, tm)); put(wv, 'sel_en', tm + 2e-9, 0)
        tt = shift(tm + 4e-9, [int(j == len(LAY.r_y) - 1)]) + 2e-9  # 마지막 칸: SDI 1 → token 이 0 번으로 돌아옴
    tt = cfg(tt, rd_out=0, ts_row2=0, ts_col1=1, ts_col2=1)
    T_SEL, T_ABS, T_LAT, SLOT = 100e-9, 290e-9, 20e-9, 480e-9
    t0 = tt + 10e-9
    t_sense = t0
    for n in range(a.slots):
        put(wv, 'sel_en', t0, 1); put(clk, 'ck', t0 + T_SEL, 1)
        tm = t0 + T_SEL + T_ABS + 10e-9
        put(clk, 'ck3', tm - 10e-9, 1); put(clk, 'lat', tm, 1); put(clk, 'lat', tm + T_LAT, 0)
        t1 = tm + T_LAT + 20e-9
        put(wv, 'sel_en', t1, 0); put(clk, 'ck', t1, 0); put(clk, 'ck3', t1, 0)
        slots.append((n, tm, tm + T_LAT + 10e-9))
        shift(t1 + 2e-9, [0])                                     # 열 token 두 개 한 칸
        t0 += SLOT
    tend = t0
    for nm, v in (('vrailp', VRAIL_RD), ('vrailm', -VRAIL_RD), ('vwl', 0.0), ('vwh', 0.0), ('vwlo', 0.0)):
        aput(nm, 0, v)
else:
    t_inf = t_read = t_sense = 0.0
    assert r_s < NRX
    k0 = min(r_s, c_s)
    tt = cfg(20e-9, ts_row1=1, ts_col1=1)
    tt = shift(tt, [1] + [0] * k0) + 2e-9                         # token 두 개를 k0 번에
    if r_s != c_s:
        tt = cfg(tt, ts_row1=int(r_s > c_s), ts_col1=int(c_s > r_s))
        tt = shift(tt, [0] * abs(r_s - c_s)) + 2e-9
    for nm, v in (('vrailp', -2.5), ('vrailm', 2.5), ('vwl', a.v_wl), ('vwh', 0.0), ('vwlo', 0.0)):
        aput(nm, 0, v)                                            # 쓰기: δ clamp 다이오드 역바이어스, 입력 구동 NMOS 는 게이트 VSS 로 꺼짐

    def verify(tag, t):                                           # WRITE·PV: V_W 버스 = V_RD (SET 극성, 긴 WP), 선택 열 → VBUS
        t = cfg(t, m1=1, m0=0, pv=1, pol=0, ts_row1=0, ts_col1=1)
        aput('vwh', t, a.v_rd); put(wv, 'sel_en', t + 2e-9, 1); put(wv, 'wp', t + 4e-9, 1)
        meas_w.append(('i', tag, t + 27e-9)); put(wv, 'wp', t + 30e-9, 0); put(wv, 'sel_en', t + 31e-9, 0)
        aput('vwh', t + 33e-9, 0.0)
        return t + 40e-9

    def pulse(tag, t, pol, v, m=(1, 0)):
        t = cfg(t, m1=m[0], m0=m[1], pv=0, pol=pol)
        aput('vwh', t, v if pol == 0 else 0.0); aput('vwlo', t, 0.0 if pol == 0 else -v)
        put(wv, 'sel_en', t + 4e-9, 1); put(wv, 'wp', t + 8e-9, 1); meas_w.append(('v', tag, t + 8e-9 + a.pw / 2))
        put(wv, 'wp', t + 8e-9 + a.pw, 0); put(wv, 'sel_en', t + 12e-9 + a.pw, 0)
        aput('vwh', t + 14e-9 + a.pw, 0.0); aput('vwlo', t + 14e-9 + a.pw, 0.0)
        return t + 20e-9 + a.pw
    tt = verify('v0', tt)
    if a.seq in ('all', 'set'):
        tt = pulse('set', tt, 0, a.v_set); tt = verify('v1', tt)
    if a.seq in ('all', 'rst'):
        tt = pulse('rst', tt, 1, a.v_rst); tt = verify('v2', tt)
    if a.seq == 'all':
        tt = pulse('form', tt, 0, a.v_form, m=(0, 1)); tt = verify('v3', tt)   # FORM (01): SET 경로를 더 큰 V 로
        tt = shift(tt, [0]) + 2e-9                                    # 열 token 한 칸 → 같은 행 이웃 (억제됐던 셀)
        tt = verify('vn', tt)
    tend = tt

# ── 덱
OLYVA = f"{OLY}/ep_demo/char/va/sky130_fd_pr_reram__reram_cell.va"
L = [f"* {a.name}: chip v3 (config reg + shared SCK/SDI + mode decoder + line MUX + write buffer + 2 crossbars + WU x2 + readout TG"
     f" + beta mirror), test {a.test}, {a.key}, sample {a.sample} label {lab}",
     (".option post=1 probe ingold=2 numdgt=8 measdgt=8 method=gear" if a.probe else ".option post=0 ingold=2 numdgt=8 measdgt=8 method=gear"), ".temp 25",
     ".option accurate relv=1e-7 absv=1e-10 reli=1e-7 absi=1e-15",
     f".lib '{a.lib}' tt", ".param cc=100f rz=3k nls=1", f".include '{a.hog}'",
     "Vdd vdd 0 2.5", "Vss vss 0 -2.5",
     "Xbias vbn vbp vbpc vdd vss HOG_BIAS", "Vbnc vbnc 0 -1.0", "Vbpc vbpc 0 0.7"]
if a.test == 'write':
    L += [f'.hdl "{OLYVA}"', ".param tstep=50p"]
L += primitives() + wu_subckt(1e6, 20e-15, 'pa_sa', 20e-15, 2.0) + lib()
for nm, w in sorted(wv.items()):
    L.append(f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.5e} {2.5 if b else -2.5}" for x, b in w) + ")")
for nm in ('sck', 'sdi', 'sld', 'sel_en', 'wp'):
    if nm not in wv:
        L.append(f"V{nm} {nm} 0 -2.5")
for nm in ('ck', 'ck3', 'lat'):
    w = clk.get(nm, [(0.0, 0)])
    L.append(f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.5e} {2.5 if b else -2.5}" for x, b in w) + ")")
L.append("XIlat lat latb vdd vss INV")
for nm, w in sorted(ana.items()):
    L.append(f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.5e} {v:.4f}" for x, v in w) + ")")
L += global_decode() + config_block() + ["XWBf wp pol vwf vwh vwlo vdd vss WBUF", "XWBn wp pol vwn vwh vwlo vdd vss WBUF"]   # 배열마다 하나
# ── 레지스터 (입력 모두 SDI, 클록 = config_block 의 <reg>_clk)
prev = 'sdi'
for k in range(LAY.n_in + LAY.n_out):                             # DATA: q_k = bits[k], latch 투명 = DLOAD
    L += [f"XFd{k} {prev} data_clk rst rstb dq{k} vdd vss DFFR", f"XLd{k} dq{k} dload dload_b dl{k} dlb{k} vdd vss DLATCH"]
    prev = f'dq{k}'
for r, n in (('row1', NRX), ('row2', len(LAY.r_y)), ('col1', len(LAY.c_h)), ('col2', len(LAY.c_h))):
    prev = 'sdi'
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
assert abs(c['beta'] - 3.812e-05) < 1e-9, 'beta_mirror 크기는 β 38.12 µA 용 (beta_size.py 로 다시 고른다)'
L += beta_mirror()
TOX, TFREF, IK1, VREFv = 5.0e-9, 4.7249e-9, 6.140e-5, 0.430
tf_for_g = lambda g: TOX + (TOX - TFREF) * np.log(g * 0.1 / (IK1 * np.sinh(0.1 / VREFv)))
wcells = sorted({(r_s, cc) for cc in range(NC)} | {(r, c_s) for r in range(NR)} | {(r_s + 1, c_s + 1)})
for p in 'fn':
    rn = lambda r: f'{p}r{r}'
    cn = lambda cc: f'{p}c{cc}'
    for r in range(NR):
        bus = f'R1{p}' if r < NRX else f'R2{p}'
        L.append(f"X{p}RM{r} {rn(r)} {p}wl{r} {bus} vw{p} vwl " + ' '.join(f'r{r}{o} r{r}{o}b' for o in RO) + " vdd vss ROWM")
    for i in range(LAY.n_in):                                     # 입력 구동 레일 = VRAILP (+a) / VRAILM (−a)
        for r, gu, gd in ((LAY.r_x[2 * i], f'ga{i}', f'gb{i}'), (LAY.r_x[2 * i + 1], f'gb{i}', f'ga{i}')):
            L += [f"X{p}Dp{r} {rn(r)} {gu} vrailp vss {NF} w=1000 l=0.5 nf=200", f"X{p}Dm{r} {rn(r)} {gd} vrailm vss {NF} w=1000 l=0.5 nf=200"]
    for r, rail in ((LAY.r_b[0], 'vrailp'), (LAY.r_b[1], 'vrailm')):
        L.append(f"X{p}Db{r} {rn(r)} READ {rail} vss {NF} w=1000 l=0.5 nf=200")
    for cc in range(NC):
        L.append(f"X{p}CM{cc} {cn(cc)} vw{p} vbus{p} C1{p} C2{p} " + ' '.join(f'c{cc}{o} c{cc}{o}b' for o in CO) + " vdd vss COLM")
        if cc not in LAY.c_h:
            L.append(f"X{p}SP{cc} {cn(cc)} 0 READ READb vdd vss TG")
        if a.test == 'write':                                     # 열 부하 (셀 128 개 + 선, 어림)
            L.append(f"C{p}cl{cc} {cn(cc)} 0 {a.c_col:g}")
    if a.test == 'read':                                          # 셀: 정적 sinh + R_on (WL 은 READ 에서 모두 VDD)
        for r, cc in zip(*np.nonzero(LAY.kind != NONE)):
            A, B = rn(r), cn(cc)
            L += [f"R{p}_{r}_{cc} {A} {p}m{r}_{cc} {c['r_on']}",
                  f"G{p}_{r}_{cc} {p}m{r}_{cc} {B} CUR='{G[r, cc]:.12e}*{V_REF}*sinh((V({p}m{r}_{cc})-V({B}))/{V_REF})'"]
    else:                                                         # 셀: VA RRAM (TE = 행) + 접근 nFET W 3 µm (게이트 = WL)
        for r, cc in wcells:
            L += [f"X{p}R{r}_{cc} {rn(r)} {p}nd{r}_{cc} sky130_fd_pr_reram__reram_cell Tfilament_0={tf_for_g(a.g0):.6e} t_step=tstep",
                  f"X{p}A{r}_{cc} {p}nd{r}_{cc} {p}wl{r} {cn(cc)} vss {NF} w=3 l=0.5"]
    for cc in LAY.c_h:                                            # δ clamp: 위 다이오드 → VRAILM (−v_b), 아래 다이오드 ← VRAILP (+v_b)
        nd = cn(cc)
        L += [f"R{p}da_{nd} {nd} {p}da_{nd} {c['r_ser']}", f"D{p}a_{nd} {p}da_{nd} vrailm dlv1",
              f"D{p}b_{nd} vrailp {p}db_{nd} dlv1", f"R{p}db_{nd} {p}db_{nd} {nd} {c['r_ser']}", f"C{p}n_{nd} {nd} 0 100f"]
    L += [f"C{p}n_r{r} {rn(r)} 0 100f" for r in LAY.r_y]
    L.append(f"XRO{p} R2{p} vbus{p} rd_out rd_out_b vdd vss TG")  # 판독 TG: R2 버스 → VBUS 패드
    if a.test == 'read':
        L += [f"C{p}pad vbus{p} 0 {a.c_pad:g}", f"R{p}pad vbus{p} 0 1e9"]   # 패드 + 밖 전압계 (고임피던스)
    else:
        L += [f"Vver{p} vbus{p} 0 0"]                             # verify: 밖 전류계 (0 V)
L.append(f".model dlv1 d (level=1 is={D_IS} n={D_N} rs=0)")
for j in range(LAY.n_out):
    yp, ym = f'nr{LAY.r_y[2 * j]}', f'nr{LAY.r_y[2 * j + 1]}'
    L += [f"XMP{j} ip{j} pref vdd vdd {PF} w=42 l=2 nf=8", f"XMN{j} in{j} nref vss vss {NF} w=15 l=2 nf=3",
          f"XSW1_{j} ip{j} {yp} sp{j} spb{j} vdd vss TG", f"XSW2_{j} ip{j} {ym} sm{j} smb{j} vdd vss TG",
          f"XSW3_{j} in{j} {ym} sp{j} spb{j} vdd vss TG", f"XSW4_{j} in{j} {yp} sm{j} smb{j} vdd vss TG"]
L += [f"Cb{b} {b} 0 200f" for b in ('R1f', 'C1f', 'R1n', 'C1n', 'R2f', 'C2f', 'R2n', 'C2n')] + [f"Cvw{p} vw{p} 0 0.2p" for p in 'fn']   # write buffer 가 배열 옆 → 짧은 버스
L += ["XWU1 R1f C1f R1n C1n ck ck3 lat latb lq1 sen1 absf1 absn1 q1a q2a vbn vbp vbnc vbpc vdd vss WU",
      "XWU2 R2f C2f R2n C2n ck ck3 lat latb lq2 sen2 absf2 absn2 q1b q2b vbn vbp vbnc vbpc vdd vss WU"]
# ── 측정
if a.test == 'read':
    L += [f".meas tran fy{j} find v(fr{r}) at={t_inf:.5e}" for j, r in enumerate(LAY.r_y)]
    L += [f".meas tran ny{j} find v(nr{r}) at={t_inf:.5e}" for j, r in enumerate(LAY.r_y)]
    L += [f".meas tran fx{k} find v(fr{r}) at={t_inf:.5e}" for k, r in enumerate(LAY.r_x[:4])]
    L += [f".meas tran dl{k} find v(dl{k}) at={t_inf:.5e}" for k in range(len(bits))]
    L += [f".meas tran cf_{n} find v({n}) at={t_inf:.5e}" for n in CFG]
    L += [f".meas tran ibp find i(Vbm_p) at={t_inf:.5e}", f".meas tran ibn find i(Vbm_n) at={t_inf:.5e}"]
    for j, tm in ro:
        r = LAY.r_y[j]
        L += [f".meas tran ro{j}f find v(vbusf) at={tm:.5e}", f".meas tran ro{j}n find v(vbusn) at={tm:.5e}",
              f".meas tran ry{j}f find v(fr{r}) at={tm:.5e}", f".meas tran ry{j}n find v(nr{r}) at={tm:.5e}"]
    L += [f".meas tran r2tok{k} find v(row2q{k}) at={t_sense:.5e}" for k in range(len(LAY.r_y))]
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
            t_on = tm - a.pw / 2                                  # wp 올라간 때
            cfar = NC - 1 if NC - 1 != c_s else 0
            for p in 'fn':
                L += [f".meas tran vbus_{tag}_{p} find v(vw{p}) at={tm:.5e}"]
                L += [f".meas tran vcolu{d}_{tag}_{p} find v({p}c{c_s + 1}) at={t_on + d * 1e-9:.5e}" for d in (2, 5)]
                L += [f".meas tran vcfar{d}_{tag}_{p} find v({p}c{cfar}) at={t_on + d * 1e-9:.5e}" for d in (2, 5)]
            L += [f".meas tran ivwh_max_{tag} max i(Vvwh) from={t_on - 1e-9:.5e} to={t_on + a.pw:.5e}",
                  f".meas tran ivwh_min_{tag} min i(Vvwh) from={t_on - 1e-9:.5e} to={t_on + a.pw:.5e}",
                  f".meas tran ivwlo_max_{tag} max i(Vvwlo) from={t_on - 1e-9:.5e} to={t_on + a.pw:.5e}",
                  f".meas tran ivwlo_min_{tag} min i(Vvwlo) from={t_on - 1e-9:.5e} to={t_on + a.pw:.5e}"]
    if a.probe:                                                   # 노트북 WRITE 파형용 node 만
        L.append(".probe tran v(wp) v(vwf) v(vwn) " + ' '.join(f"v({p}r{r_s}) v({p}c{c_s}) v({p}c{c_s + 1}) v({p}wl{r_s})" for p in 'fn')
                 + " i(Vverf) i(Vvern) i(Vvwh) i(Vvwlo)")
    L += [f".tran 20p {tend:.6e}", ".end"]
(HERE / 'decks').mkdir(exist_ok=True)
(HERE / 'decks' / f'{a.name}.sp').write_text("\n".join(L) + "\n")
# ── 정답
ci = lambda rc: dict(row=int(rc[0]), col=int(rc[1]), vf=float(Vf[rc]), vn=float(Vn[rc]), delta=float(abs(Vn[rc]) - abs(Vf[rc])),
                     reset=bool(abs(Vn[rc]) - abs(Vf[rc]) >= 0))
cells1 = [(0, n) for n in range(a.slots)]; cells2 = [(int(LAY.r_y[0]), n) for n in range(a.slots)]
json.dump(dict(args=vars(a), test=a.test, label=lab, e=e.tolist(), bits=bits, vy_f=vy_f[0].tolist(), vy_n=vy_n[0].tolist(),
               pred=int(np.argmax(d)), cells1=[ci(x) for x in cells1] if a.test == 'read' else [],
               cells2=[ci(x) for x in cells2] if a.test == 'read' else [], meas_w=meas_w, ro=ro, cfg_names=CFG, cfg_last=cur,
               n_cfg=n_cfg[0], beta=c['beta'], t_inf=t_inf, t_read=t_read, tend=tend),
          open(HERE / 'decks' / f'{a.name}_ref.json', 'w'), indent=1)
print(f"{a.name}.sp: {len(L)} 줄, test {a.test}, 설정 쓰기 {n_cfg[0]} 번, t_end {tend*1e9:.0f} ns, label {lab}, Python 예측 {int(np.argmax(d))}")
