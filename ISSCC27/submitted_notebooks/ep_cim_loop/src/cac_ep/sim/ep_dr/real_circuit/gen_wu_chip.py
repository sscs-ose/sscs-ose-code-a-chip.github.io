"""[gen_wu_block.py 사본을 고침, 10/30] 칩 wu.cdl 구성 (COMP3 = pre-amp + StrongARM, A1–A4 이득 2) 도 만들 수 있게 --comp3 pa_sa, --gain 을 더함.
Oh 2023 weight update 회로 한 벌 (SPICE, SKY130 5 V, ±2.5 V) — 이상 전원 입력으로 판정 경계·정착·전력을 잰다.

구성 (학위 발표 2023-12-11 14장 그대로, Micromachines 14, 1367 Fig. 3a):
  입력 enable TG 4개 (en) : free_plus·free_minus·nudge_plus·nudge_minus = 선택 셀의 행·열 (free, nudge 크로스바)
  COMP1 / COMP2           : StrongARM 동적 비교기 + SR latch. q1 = 1 이면 ΔV_f = V(free_plus) − V(free_minus) > 0
  A1 / A2                 : HOG + 저항 4개 차동 증폭기 (이득 1). A1 = V+ − V− (q1 로 켬), A2 = V− − V+ (q1b) → 노드 abs_f = |ΔV_f|
  A3 / A4, COMP2          : nudge 쪽 같은 구조 → abs_n = |ΔV_n|
  COMP3                   : HOG 개방 루프 (inp = abs_f, inn = abs_n) → sen. 학위 그림대로 opamp. --comp3 sa 면 StrongARM
  D latch                 : dynamic D latch (TG + inverter 2개, lat 이 높을 때 투명). lq = 1 → |ΔV_f| > |ΔV_n| → SET (준위 +1)
  → Δg = −sgn(|ΔV_n| − |ΔV_f|)·Δg_fixed (Oh 2023 Eq. 3). register·programming pulse driver 는 넣지 않는다 (README §9).
AMP = 사용자 HOG (~/work/projects/sern_hog_classab_opamp, subckt SKY130_OTA_HOG_TR inp(+) inn(−) out ...).
쓰임: python gen_wu_block.py --name wu_blk0  → decks/wu_blk0.sp, decks/wu_blk0_ref.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

from wu_lib import primitives, wu_core

OLY = '/home/grads/s/seokjindaveoh/work'
ap = argparse.ArgumentParser()
ap.add_argument('--name', default='wu_blk0')
ap.add_argument('--lib', default=f'{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice')
ap.add_argument('--hog', default=f'{OLY}/sern_hog/char/decks/hog_tr.spice', help='HOG subckt (트랜지스터 바이어스판)')
ap.add_argument('--dvf', default='0.5,5,50,200,-0.5,-5,-50,-200', help='ΔV_f [mV]')
ap.add_argument('--delta', default='-3000,-1000,-300,-100,-30,30,100,300,1000,3000,10000', help='|ΔV_n| − |ΔV_f| [µV]')
ap.add_argument('--flip', type=int, default=1, help='1 이면 ΔV_n 부호를 뒤집은 경우도 넣음 (δ ≥ 0 만)')
ap.add_argument('--vcm_cell', type=float, default=0.1, help='셀 양단 평균 전압 [V]')
ap.add_argument('--rth', type=float, default=1e3, help='입력 전원 Thevenin [Ω] (노드 + 선택 TG 어림)')
ap.add_argument('--r_diff', type=float, default=1e6, help='A1–A4 저항 [Ω] (학위 그림 r=1M)')
ap.add_argument('--cf', type=float, default=20e-15, help='A1–A4 귀환 저항 병렬 C [F] (입력 극점 보상)')
ap.add_argument('--comp3', choices=['hog', 'sa', 'pa_sa'], default='hog')
ap.add_argument('--gain', type=float, default=1.0, help='A1–A4 이득 (칩 wu_rbank 저항 3 : 6 = 2)')
ap.add_argument('--t_sel', type=float, default=100e-9, help='입력 바뀐 뒤 COMP1/2 평가까지')
ap.add_argument('--t_abs', type=float, default=300e-9, help='COMP1/2 평가 뒤 A 경로·COMP3 정착')
ap.add_argument('--t_lat', type=float, default=20e-9, help='D latch 투명 구간')
a = ap.parse_args()

L = [f"* {a.name}: Oh 2023 weight update block (HOG, StrongARM, dynamic D latch), synthetic inputs",
     ".option post=0 ingold=2 numdgt=8 measdgt=8 method=gear", ".temp 27",
     # 기본 허용오차 (reltol 1e-3 ≈ 2.5 mV) 로는 mV 이하 판정이 시간 간격에 따라 바뀐다 (dbg_sa3 대 dbg_sa4) → 조임
     ".option accurate relv=1e-7 absv=1e-10 reli=1e-7 absi=1e-15",
     f".lib '{a.lib}' tt", ".param cc=100f rz=3k nls=1", f".include '{a.hog}'",
     "Vdd vdd 0 2.5", "Vss vss 0 -2.5",
     "Xbias vbn vbp vbpc vdd vss HOG_BIAS", "Vbnc vbnc 0 -1.0", "Vbpc vbpc 0 0.7"] + primitives()   # 부품: wu_lib.py

# 입력 enable → 내부 노드 fp, fm, np, nm, 그다음 회로 몸체 (wu_lib.wu_core)
L += [f"XTe{s} bus{s} {s} en enb vdd vss TG" for s in ('fp', 'fm', 'np', 'nm')]
L += wu_core(a.r_diff, a.cf, a.comp3, gain=a.gain)

# ── 입력 격자 ──
cells = []
for dvf in [float(v) * 1e-3 for v in a.dvf.split(',')]:
    for d in [float(v) * 1e-6 for v in a.delta.split(',')]:
        m = abs(dvf) + d
        if m < 0:
            continue
        for flip in ((1, -1) if a.flip and d >= 0 else (1,)):
            dvn = flip * np.sign(dvf) * m
            cells.append(dict(dvf=dvf, dvn=dvn, d=d, flip=flip))
for c in cells:
    c.update(fp=a.vcm_cell + c['dvf'] / 2, fm=a.vcm_cell - c['dvf'] / 2, np=a.vcm_cell + c['dvn'] / 2, nm=a.vcm_cell - c['dvn'] / 2)
    c['set_exact'] = int(abs(c['dvf']) > abs(c['dvn']))           # 1 = SET (|ΔV_n| < |ΔV_f|)

# ── 시퀀스 (셀마다): 입력 바꿈·en → t_sel → ck↑ (COMP1/2 평가) → t_abs → lat 투명 t_lat → lat↓ → 확인 → ck↓·en↓ ──
ctl, src = {}, {s: [(0.0, cells[0][s])] for s in ('fp', 'fm', 'np', 'nm')}
def put(nm, t0, v):
    s = ctl.setdefault(nm, [(0.0, 0)])
    if s[-1][1] != v:
        s += [(t0, s[-1][1]), (t0 + 0.2e-9, v)]
t, meas = 5e-9, []
for n, c in enumerate(cells):
    for s in src:
        src[s] += [(t, src[s][-1][1]), (t + 0.2e-9, c[s])]
    put('en', t, 1)
    put('ck', t + a.t_sel, 1)
    tm = t + a.t_sel + a.t_abs
    if a.comp3 in ('sa', 'pa_sa'):
        put('ck3', tm - 10e-9, 1)
    put('lat', tm, 1); put('lat', tm + a.t_lat, 0)
    meas.append((n, tm, tm + a.t_lat + 10e-9))
    t = tm + a.t_lat + 20e-9
    put('ck', t, 0); put('en', t, 0)
    if a.comp3 in ('sa', 'pa_sa'):
        put('ck3', t, 0)
    t += 10e-9
tend = t + 5e-9
pw = lambda s, inv: "PWL(" + " ".join(f"{x:.6e} {(-2.5 if b else 2.5) if inv else (2.5 if b else -2.5)}" for x, b in s) + ")"
for nm, s in ctl.items():
    L += [f"V{nm} {nm} 0 {pw(s, False)}", f"V{nm}b {nm}b 0 {pw(s, True)}"]
for s, w in src.items():
    L += [f"Vs{s} src{s} 0 PWL(" + " ".join(f"{x:.6e} {v:.9e}" for x, v in w) + ")", f"Rs{s} src{s} bus{s} {a.rth:g}"]
for n, tm, th in meas:
    L += [f".meas tran absf{n} find v(absf) at={tm:.6e}", f".meas tran absn{n} find v(absn) at={tm:.6e}",
          f".meas tran sen{n} find v(sen) at={tm:.6e}", f".meas tran q1_{n} find v(q1) at={tm:.6e}",
          f".meas tran q2_{n} find v(q2) at={tm:.6e}", f".meas tran lq{n} find v(lq) at={th:.6e}"]
L += [f".meas tran idd avg i(Vdd) from=0 to={tend:.6e}", f".meas tran iss avg i(Vss) from=0 to={tend:.6e}",
      f".tran 0.1n {tend:.6e}", ".end"]
out = Path(__file__).parent / 'decks'
out.mkdir(exist_ok=True)
(out / f'{a.name}.sp').write_text("\n".join(L) + "\n")
json.dump(dict(args=vars(a), cells=cells, t_cell_ns=(tend - 5e-9) / len(cells) * 1e9, tend=tend),
          open(out / f'{a.name}_ref.json', 'w'), indent=1)
print(f"{a.name}.sp: {len(cells)} cells, t_end {tend*1e6:.1f} µs ({(tend-5e-9)/len(cells)*1e9:.0f} ns/cell)")
