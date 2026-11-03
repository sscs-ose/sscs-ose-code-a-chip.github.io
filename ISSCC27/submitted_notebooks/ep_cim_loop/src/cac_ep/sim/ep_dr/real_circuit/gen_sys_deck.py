"""크로스바 두 벌 (free·nudge) + 모든 행·열 TG + weight update 회로 두 벌 (first stage·last stage) SPICE 덱 (README §9).

- 크로스바: ../spice_check.py write_deck 과 같은 소자 (sinh 셀 + R_on, 다이오드 + R_ser 두 가지, stabilizer 판이면 G_bz), Vcm = 0 V (GND).
  10/25 부터 기본 가중치는 stabilizer 행·열이 없는 판 (`--weights` 로 바꿈, train.layout_of 가 배치를 고름).
  입력 행·nudge 전류는 1차로 이상 전원 (README §9 다음 단계에서 실제 회로로 바꿈).
- TG (게이트 0 / VDD): free·nudge 각 크로스바에서
    입력·bias 행 100 개 → 버스 R1f / R1n,  출력 행 6 개 → R2f / R2n,
    hidden 열 60 개 → C1f / C1n (first stage 용) 과 C2f / C2n (last stage 용) 에 하나씩.
  같은 자리의 free·nudge TG 는 같은 select 신호로 켠다.
- weight update 회로 WU1 (R1f, C1f, R1n, C1n) = first stage, WU2 (R2f, C2f, R2n, C2n) = last stage (wu_lib.py).
- 시간 칸마다 WU1 은 first stage 셀 하나, WU2 는 last stage 셀 하나를 동시에 본다. 셀 사이는 모든 select 를 끈 뒤 켠다.
- 정답 = 같은 G·입력으로 ../solver.py 가 푼 free·nudge 해의 sgn(|ΔV_n| − |ΔV_f|) (b ≥ 0 → RESET, train.py 와 같음).
쓰임: python gen_sys_deck.py --name sys0 --n1 24 --n2 24   → decks/sys0.sp, decks/sys0_ref.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from circuit import D_IS, D_N, NONE, V_REF, W1, W2, row_drive   # noqa: E402
from data import load_task                                       # noqa: E402
from solver import cell_voltage, solve                           # noqa: E402
from train import layout_of                                            # noqa: E402
from wu_lib import primitives, wu_subckt                         # noqa: E402

OLY = '/home/grads/s/seokjindaveoh/work'
ap = argparse.ArgumentParser()
ap.add_argument('--name', default='sys0')
ap.add_argument('--weights', default=str(HERE.parent / 'out' / 'weights' / 'nostab_5bit.npz'),
                help='10/25 부터 stabilizer 없는 판 (README §12). 이전 판 = tanh5_5bit.npz')
ap.add_argument('--key', default='5b_s0')
ap.add_argument('--state', default='best', choices=['init', 'best', 'final'])
ap.add_argument('--sample', type=int, default=0, help='MNIST train (0·1·4) 표본 번호')
ap.add_argument('--n1', type=int, default=24, help='first stage 에서 볼 셀 수')
ap.add_argument('--n2', type=int, default=24, help='last stage 에서 볼 셀 수')
ap.add_argument('--range1', default='', help="셀 전체 확인용 (10/25): first stage 셀을 행 우선 순서로 번호 매겨 'i0:i1' 구간을 본다 (--n1 대신)")
ap.add_argument('--range2', default='', help="같은 방식의 last stage 구간. 비우면 --n2 (0 이면 last stage 칸 없음)")
ap.add_argument('--mc', type=int, default=0, help='Monte Carlo (소자 부정합) 표본 번호 k ≥ 1: models_mc lib + mc_mm_switch 1 + sweep monte=list(k). 0 이면 끔')
ap.add_argument('--lib_mc', default=f'{OLY}/ep_dr/real_circuit/models_mc/sky130_5v_tt_mc.lib.spice')
ap.add_argument('--comp3', choices=['hog', 'sa', 'pa_sa'], default='pa_sa', help='10/25 사용자: 비교기 (StrongARM) 로. pa_sa = 전치 증폭기 + StrongARM')
ap.add_argument('--lib', default=f'{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice')
ap.add_argument('--hog', default=f'{OLY}/sern_hog/char/decks/hog_tr.spice')
ap.add_argument('--r_diff', type=float, default=1e6)
ap.add_argument('--cf', type=float, default=20e-15)
ap.add_argument('--a_gain', type=float, default=2.0, help='A1–A4 차동 이득 (학위 1). 10/25 기본 2 (전치 증폭기와 함께 표본 3 개 144/144)')
ap.add_argument('--c_abs', type=float, default=20e-15, help='COMP3 입력 노드 C (wu_lib.wu_core). 사용자 10/25 "p 단위 cap은 너무 커" → 20 fF + 전치 증폭기')
ap.add_argument('--cnode', type=float, default=100e-15, help='hidden·출력 노드 C')
ap.add_argument('--cbus', type=float, default=200e-15, help='버스 C')
ap.add_argument('--t_sel', type=float, default=100e-9)
ap.add_argument('--t_abs', type=float, default=300e-9)
ap.add_argument('--t_lat', type=float, default=20e-9)
ap.add_argument('--drv', choices=['ideal', 'nmos'], default='nmos',
                help='입력 행 구동: 이상 전원 / 행마다 NMOS 2:1 스위치 (±a 레일 패드, 게이트 0 / VDD)')
ap.add_argument('--w_drv', type=float, default=1000.0, help='NMOS 스위치 W [µm] (L 0.5). 1 mA 에서 강하 4.0 / 2.7 mV (dbg_drv)')
ap.add_argument('--r_pad', type=float, default=0.0, help='±a 레일 패드·배선 직렬 저항 [Ω]')
ap.add_argument('--nudge', choices=['ideal', 'mirror'], default='mirror',
                help='nudge: 이상 전류원 / 스위치 SW1–SW4 + PMOS·NMOS 전류 미러 (Oh 2023 Fig. 2b), 기준 Iref = β 패드')
ap.add_argument('--w_mp', type=float, default=42.0, help='PMOS 미러 W [µm]')
ap.add_argument('--w_mn', type=float, default=15.0, help='NMOS 미러 W [µm]')
ap.add_argument('--l_m', type=float, default=2.0, help='미러 L [µm]')
ap.add_argument('--print', dest='prt', default='', help="진단: .print 할 노드 (쉼표). --win 구간만 출력하고 그 끝에서 멈춤")
ap.add_argument('--win', default='', help="진단 구간 't0,t1' [s]")
ap.add_argument('--ng_cell', choices=['osdi', 'bsrc'], default='osdi',
                help='ngspice 셀: OSDI (va/sinhcell.va, OpenVAF) / B 소스 식 (느림, ng_sys2 21 분 넘게)')
ap.add_argument('--sim', choices=['spice', 'ngspice'], default='spice',
                help='ngspice: 같은 회로를 ngspice 문법으로 (셀 G CUR= → B I=, 옵션), 덱 .cir. 실행 폴더에 .spiceinit (ngbehavior=hsa)')
a = ap.parse_args()

# ── 가중치·표본·Python 해 ──
W = np.load(a.weights)
LAY = layout_of(W)                                               # stabilizer 있는 판 / 없는 판 (README §12)
info = {i['key']: i for i in json.loads(str(W['info']))}[a.key]
c = info['config']
G = W[f'{a.key}/G_{a.state}']
X, y = load_task('train')
s, lab = X[a.sample:a.sample + 1], int(y[a.sample])
t = np.where(np.eye(LAY.n_out)[lab] > 0, 1.0, -1.0)
u = torch.as_tensor(row_drive(LAY, s, c['a']))
Gt = torch.as_tensor(G)[None]
vh_f, vy_f, _ = solve(LAY, Gt, u, r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'], out_diode=not c['no_out_clamp'])
d = (vy_f[:, 0::2] - vy_f[:, 1::2])[0].numpy()
e = np.sign(t - d)
inj = torch.as_tensor(np.stack([c['beta'] * e, -c['beta'] * e], 1).reshape(1, -1))
vh_n, vy_n, _ = solve(LAY, Gt, u, i_nudge=inj, r_on=c['r_on'], v0=(vh_f, vy_f), v_b=c['v_b'], r_ser=c['r_ser'],
                      out_diode=not c['no_out_clamp'])
Vf, Vn = cell_voltage(LAY, u, vh_f, vy_f)[0].numpy(), cell_voltage(LAY, u, vh_n, vy_n)[0].numpy()
bexact = (np.abs(Vn) - np.abs(Vf)) >= 0                                    # True = RESET (준위 −1)


def pick(kind, n):
    """|δ| 분위로 고르게 n 개 (작은 δ 쪽을 더 촘촘히)."""
    rc = np.argwhere(LAY.kind == kind)
    dl = np.abs(np.abs(Vn) - np.abs(Vf))[rc[:, 0], rc[:, 1]]
    o = np.argsort(dl)
    q = np.unique(np.round((np.linspace(0, 1, n) ** 2) * (len(o) - 1)).astype(int))
    return [tuple(rc[o[i]]) for i in q]


def span(kind, rg):
    """행 우선 순서 셀 목록의 'i0:i1' 구간."""
    i0, i1 = (int(x) for x in rg.split(':'))
    return [tuple(x) for x in np.argwhere(LAY.kind == kind)[i0:i1]]


cells1 = span(W1, a.range1) if a.range1 else pick(W1, a.n1)
cells2 = span(W2, a.range2) if a.range2 else (pick(W2, a.n2) if a.n2 > 0 else [])

# ── 덱 ──
v_b, r_ser = c['v_b'], c['r_ser']
L = [f"* {a.name}: free/nudge crossbars + row/col TG + weight update x2 (first, last stage), {a.key} {a.state}, "
     f"train sample {a.sample} label {lab}",
     ".option post=0 ingold=2 numdgt=8 measdgt=8 method=gear", ".temp 25",   # Python solver 와 같은 온도 (circuit.py T_K, spice_check .temp 25). 27 이면 다이오드가 더 켜져 노드 −1.9 % (sys0)
     ".option accurate relv=1e-7 absv=1e-10 reli=1e-7 absi=1e-15",
     *([f".lib '{a.lib_mc}' tt", ".param mc_mm_switch=1"] if a.mc else [f".lib '{a.lib}' tt"]),
     ".param cc=100f rz=3k nls=1", f".include '{a.hog}'",
     "Vdd vdd 0 2.5", "Vss vss 0 -2.5",
     "Xbias vbn vbp vbpc vdd vss HOG_BIAS", "Vbnc vbnc 0 -1.0", "Vbpc vbpc 0 0.7"]
L += primitives() + wu_subckt(a.r_diff, a.cf, a.comp3, a.c_abs, a.a_gain)
L += [f".model dlv1 d (level=1 is={D_IS} n={D_N} rs=0)", f"Vrup vrup 0 {-v_b}", f"Vrdn vrdn 0 {v_b}"]
fixed_r = set(np.r_[LAY.r_x, LAY.r_b].tolist()) | ({LAY.r_s} if LAY.stab else set())
uu = u[0].numpy()
NF, PF = 'sky130_fd_pr__nfet_g5v0d10v5', 'sky130_fd_pr__pfet_g5v0d10v5'
nf = lambda w: max(1, int(round(w / 5)))                                  # finger 5 µm
if a.drv == 'nmos':                                                       # ±a 레일 = 외부 패드
    L += [f"Vraip raip0 0 {c['a']}", f"Vraim raim0 0 {-c['a']}"]
    L += ([f"Rpadp raip0 raip {a.r_pad:g}", f"Rpadm raim0 raim {a.r_pad:g}"] if a.r_pad > 0
          else ["Vpadp raip raip0 0", "Vpadm raim raim0 0"])
if a.nudge == 'mirror':                                                   # 미러 기준 (한 벌, Iref = β)
    L += [f"XMPref pref pref vdd vdd {PF} w={a.w_mp:g} l={a.l_m:g} nf={nf(a.w_mp)}", f"Iprf pref vss {c['beta']:.9e}",
          f"XMNref nref nref vss vss {NF} w={a.w_mn:g} l={a.l_m:g} nf={nf(a.w_mn)}", f"Inrf vdd nref {c['beta']:.9e}"]
for p in 'fn':
    rn = lambda r: '0' if r == LAY.r_s else f'{p}r{r}'
    cn = lambda cc: f'{p}c{cc}' if cc in LAY.c_h else '0'
    for r in np.r_[LAY.r_x, LAY.r_b]:
        if a.drv == 'ideal':
            L.append(f"V{p}u{r} {rn(r)} 0 {uu[r]:.9e}")                  # 입력·bias 행 이상 전원
        elif r in LAY.r_b:
            L.append(f"V{p}u{r} {rn(r)} {'raip' if uu[r] > 0 else 'raim'} 0")   # bias 행은 레일에 바로
        else:                                                             # 입력 행: NMOS 2:1 (게이트 D = vdd / D̄ = 0)
            up = uu[r] > 0
            L += [f"X{p}Dp{r} {rn(r)} {'vdd' if up else '0'} raip vss {NF} w={a.w_drv:g} l=0.5 nf={nf(a.w_drv)}",
                  f"X{p}Dm{r} {rn(r)} {'0' if up else 'vdd'} raim vss {NF} w={a.w_drv:g} l=0.5 nf={nf(a.w_drv)}"]
    for r, cc in zip(*np.nonzero(LAY.kind != NONE)):
        if r in fixed_r and cc not in LAY.c_h:
            continue
        A, B = rn(r), cn(cc)
        if c['r_on']:
            L.append(f"R{p}_{r}_{cc} {A} {p}m{r}_{cc} {c['r_on']}")
            A = f'{p}m{r}_{cc}'
        L.append(f"G{p}_{r}_{cc} {A} {B} CUR='{G[r, cc]:.12e}*{V_REF}*sinh((V({A})-V({B}))/{V_REF})'")
    nodes = [cn(cc) for cc in LAY.c_h] + ([] if c['no_out_clamp'] else [rn(r) for r in LAY.r_y])
    for nd in nodes:
        L += [f"R{p}da_{nd} {nd} {p}da_{nd} {r_ser}", f"D{p}a_{nd} {p}da_{nd} vrup dlv1",
              f"D{p}b_{nd} vrdn {p}db_{nd} dlv1", f"R{p}db_{nd} {p}db_{nd} {nd} {r_ser}"]
    L += [f"C{p}n_{cn(cc)} {cn(cc)} 0 {a.cnode:g}" for cc in LAY.c_h] + [f"C{p}n_{rn(r)} {rn(r)} 0 {a.cnode:g}" for r in LAY.r_y]
    if p == 'n' and a.nudge == 'ideal':
        for j in range(LAY.n_out):                                       # nudge 이상 전류원
            L += [f"Inu{j}p 0 {rn(LAY.r_y[2 * j])} {c['beta'] * e[j]:.9e}", f"Inu{j}m 0 {rn(LAY.r_y[2 * j + 1])} {-c['beta'] * e[j]:.9e}"]
    if p == 'n' and a.nudge == 'mirror':
        # 출력 쌍마다 I+ (PMOS 미러, β 를 내보냄) · I− (NMOS 미러, β 를 받음) 와 SW1–SW4 (게이트 0 / VDD).
        # Din = (e > 0): SW1 I+ → y+, SW3 I− → y−  /  Din̄: SW2 I+ → y−, SW4 I− → y+  (Oh 2023 Fig. 2b)
        for j in range(LAY.n_out):
            yp, ym = rn(LAY.r_y[2 * j]), rn(LAY.r_y[2 * j + 1])
            on, off = ('vdd', '0'), ('0', 'vdd')
            dn, db = (on, off) if e[j] > 0 else (off, on)
            L += [f"XMP{j} ip{j} pref vdd vdd {PF} w={a.w_mp:g} l={a.l_m:g} nf={nf(a.w_mp)}",
                  f"XMN{j} in{j} nref vss vss {NF} w={a.w_mn:g} l={a.l_m:g} nf={nf(a.w_mn)}",
                  f"XSW1_{j} ip{j} {yp} {dn[0]} {dn[1]} vdd vss TG", f"XSW2_{j} ip{j} {ym} {db[0]} {db[1]} vdd vss TG",
                  f"XSW3_{j} in{j} {ym} {dn[0]} {dn[1]} vdd vss TG", f"XSW4_{j} in{j} {yp} {db[0]} {db[1]} vdd vss TG"]
    # 행·열 TG → 버스
    for r in np.r_[LAY.r_x, LAY.r_b]:
        L.append(f"X{p}T1r{r} {rn(r)} R1{p} s1r{r} s1r{r}b vdd vss TG")
    for r in LAY.r_y:
        L.append(f"X{p}T2r{r} {rn(r)} R2{p} s2r{r} s2r{r}b vdd vss TG")
    for cc in LAY.c_h:
        L += [f"X{p}T1c{cc} {cn(cc)} C1{p} s1c{cc} s1c{cc}b vdd vss TG", f"X{p}T2c{cc} {cn(cc)} C2{p} s2c{cc} s2c{cc}b vdd vss TG"]
L += [f"Cb{b} {b} 0 {a.cbus:g}" for b in ('R1f', 'C1f', 'R1n', 'C1n', 'R2f', 'C2f', 'R2n', 'C2n')]
L += ["XWU1 R1f C1f R1n C1n ck ck3 lat latb lq1 sen1 absf1 absn1 q1a q2a vbn vbp vbnc vbpc vdd vss WU",
      "XWU2 R2f C2f R2n C2n ck ck3 lat latb lq2 sen2 absf2 absn2 q1b q2b vbn vbp vbnc vbpc vdd vss WU"]

# ── 시퀀스 ──
ctl = {}
def put(nm, t0, v):
    s_ = ctl.setdefault(nm, [(0.0, 0)])
    if s_[-1][1] != v:
        s_ += [(t0, s_[-1][1]), (t0 + 0.2e-9, v)]
nslot = max(len(cells1), len(cells2))
t0, meas = 20e-9, []
for n in range(nslot):
    sel = []
    if n < len(cells1):
        r, cc = cells1[n]; sel += [f's1r{r}', f's1c{cc}']
    if n < len(cells2):
        r, cc = cells2[n]; sel += [f's2r{r}', f's2c{cc}']
    for nm in sel:
        put(nm, t0, 1)
    put('ck', t0 + a.t_sel, 1)
    tm = t0 + a.t_sel + a.t_abs
    if a.comp3 in ('sa', 'pa_sa'):   # COMP3 가 StrongARM 이면 ck3
        put('ck3', tm - 10e-9, 1)
    put('lat', tm, 1); put('lat', tm + a.t_lat, 0)
    meas.append((n, tm, tm + a.t_lat + 10e-9))
    t1 = tm + a.t_lat + 20e-9
    for nm in sel:
        put(nm, t1, 0)
    put('ck', t1, 0)
    if a.comp3 in ('sa', 'pa_sa'):   # COMP3 가 StrongARM 이면 ck3
        put('ck3', t1, 0)
    t0 = t1 + 10e-9
tend = t0 + 5e-9
used = set(ctl)
sel_all = ([f's1r{r}' for r in np.r_[LAY.r_x, LAY.r_b]] + [f's2r{r}' for r in LAY.r_y]
           + [f's1c{cc}' for cc in LAY.c_h] + [f's2c{cc}' for cc in LAY.c_h])
for nm in sel_all:                                    # 크로스바 select: 0 / VDD (켜짐 = en VDD, enb 0)
    if nm in used:
        w = ctl[nm]
        L += [f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.6e} {2.5 if b else 0}" for x, b in w) + ")",
              f"V{nm}b {nm}b 0 PWL(" + " ".join(f"{x:.6e} {0 if b else 2.5}" for x, b in w) + ")"]
    else:
        L += [f"V{nm} {nm} 0 0", f"V{nm}b {nm}b 0 2.5"]
for nm in ('ck', 'ck3', 'lat'):                       # weight update 회로 안 클록: ±2.5 V
    w = ctl.get(nm, [(0.0, 0)])
    L += [f"V{nm} {nm} 0 PWL(" + " ".join(f"{x:.6e} {2.5 if b else -2.5}" for x, b in w) + ")"]
    if nm == 'lat':
        L += ["Vlatb latb 0 PWL(" + " ".join(f"{x:.6e} {-2.5 if b else 2.5}" for x, b in w) + ")"]
# 측정: 처음 (select 전) 노드 전압 = DC 평형, 시간 칸마다 버스·판정
for p in 'fn':
    L += [f".meas tran {p}h{j} find v({p}c{cc}) at=10n" for j, cc in enumerate(LAY.c_h)]
    L += [f".meas tran {p}y{j} find v({p}r{r}) at=10n" for j, r in enumerate(LAY.r_y)]
for n, tm, th in meas:
    for k in (1, 2):
        L += [f".meas tran lq{k}_{n} find v(lq{k}) at={th:.6e}", f".meas tran sen{k}_{n} find v(sen{k}) at={tm:.6e}",
              f".meas tran af{k}_{n} find v(absf{k}) at={tm:.6e}", f".meas tran an{k}_{n} find v(absn{k}) at={tm:.6e}"]
        L += [f".meas tran b{k}{bn}{p}_{n} find v({bn}{k}{p}) at={tm:.6e}" for bn in ('R', 'C') for p in 'fn']
if a.prt:
    w0, w1 = (float(v) for v in a.win.split(','))
    L += [".print tran " + " ".join(f"v({nd})" for nd in a.prt.split(',')), f".tran 0.1n {w1:.6e} START={w0:.6e}", ".end"]
else:
    L += [f".meas tran idd avg i(Vdd) from=0 to={tend:.6e}", f".meas tran iss avg i(Vss) from=0 to={tend:.6e}",
          f".tran 0.1n {tend:.6e}" + (f" sweep monte=list({a.mc})" if a.mc else ''), ".end"]
(HERE / 'decks').mkdir(exist_ok=True)


def to_ngspice(lines):
    """SPICE 줄 → ngspice 줄. 회로는 그대로, 문법만: 옵션, .lib/.include 따옴표, VCCS 식 → B 소스."""
    import re
    out = []
    for l in lines:
        if l.startswith('.option'):
            continue
        if l.startswith('.lib ') or l.startswith('.include '):
            l = l.replace("'", '')
        m = re.match(r"^G(\S+) (\S+) (\S+) CUR='(.*)'$", l)
        if m and a.ng_cell == 'osdi':
            g = re.match(r"^([0-9.eE+-]+)\*", m.group(4)).group(1)          # 'g*V_REF*sinh(...)' 의 g
            l = f"N{m.group(1)} {m.group(2)} {m.group(3)} sinhm g={g}"
        elif m:
            l = f"B{m.group(1)} {m.group(2)} {m.group(3)} I={{{m.group(4)}}}"
        out.append(l)
    hdr = [".options reltol=1e-6 abstol=1e-15 vntol=1e-10 method=gear klu", ".options tnom=25 noacct"]   # ngspice 기본 TNOM 27 (SPICE 25)
    if a.ng_cell == 'osdi':
        hdr.append(f".model sinhm sinhcell vref={V_REF}")                    # .spiceinit 의 pre_osdi sinhcell.osdi
    return out[:1] + hdr + out[1:]


if a.sim == 'ngspice':
    (HERE / 'decks' / f'{a.name}.cir').write_text("\n".join(to_ngspice(L)) + "\n")
else:
    (HERE / 'decks' / f'{a.name}.sp').write_text("\n".join(L) + "\n")


def cinfo(rc):
    r, cc = int(rc[0]), int(rc[1])
    return dict(row=r, col=cc, vf=float(Vf[r, cc]), vn=float(Vn[r, cc]), delta=float(abs(Vn[r, cc]) - abs(Vf[r, cc])),
                reset=bool(bexact[r, cc]))
json.dump(dict(args=vars(a), label=lab, e=e.tolist(), cells1=[cinfo(x) for x in cells1], cells2=[cinfo(x) for x in cells2],
               vh_f=vh_f[0].tolist(), vy_f=vy_f[0].tolist(), vh_n=vh_n[0].tolist(), vy_n=vy_n[0].tolist(),
               c_h=LAY.c_h.tolist(), r_y=LAY.r_y.tolist(), tend=tend, t_slot_ns=(tend - 20e-9) / nslot * 1e9),
          open(HERE / 'decks' / f'{a.name}_ref.json', 'w'), indent=1)
d1 = [abs(x['delta']) for x in map(cinfo, cells1)]; d2 = [abs(x['delta']) for x in map(cinfo, cells2)] or [np.nan]
print(f"{a.name}.{'cir' if a.sim == 'ngspice' else 'sp'}: {len(L)} 줄, 시간 칸 {nslot}, t_end {tend*1e6:.1f} µs, label {lab}, e {e}, "
      f"|δ| first {min(d1)*1e6:.1f}–{max(d1)*1e6:.1f} µV, last {min(d2)*1e3:.2f}–{max(d2)*1e3:.2f} mV")
