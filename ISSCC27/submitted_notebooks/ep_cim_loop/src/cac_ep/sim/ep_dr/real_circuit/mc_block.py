"""weight update 회로 부품의 Monte Carlo (소자 부정합) 덱 — 셀 판정 경계 δ_th 를 이루는 두 몫을 따로 잰다 (10/25, 사용자 "모테카를로도 하긴 해야지").

COMP3 는 absf − absn = 2(|ΔV_f| − |ΔV_n|) + (e_f − e_n) 을 offset V_os3 과 비교하므로, 판정이 바뀌는 δ = |ΔV_n| − |ΔV_f| 는
    δ_th = (e_f − e_n − V_os3) / 2
e_f·e_n = free·nudge 쪽 차동 증폭기 (A1/A2, A3/A4) 의 출력 오차 (= out − 2|ΔV|), V_os3 = COMP3 (전치 증폭기 + StrongARM) 입력 환산 offset.
  paths : A1–A4 를 따로 세워 (TG 켬, 출력 따로) DC 쓸기 × MC → e_k(ΔV). A1·A3 은 (row, hid), A2·A4 는 부호를 뒤집은 입력.
  comp  : 비교기 하나에 입력차를 클록마다 0.5 mV 씩 올려 (−30 → +30 mV) 처음 1 이 되는 칸 = offset. COMP3 (PRE + SA) / COMP1 (SA).
쓰임: python mc_block.py --n 200 → decks/mc_paths.sp, decks/mc_c3_cm{06,02}.sp, decks/mc_c1_cm01.sp
"""
import argparse
from pathlib import Path

from wu_lib import diff_amp, primitives

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
ap = argparse.ArgumentParser()
ap.add_argument('--n', type=int, default=200, help='MC 표본 수')
ap.add_argument('--lib_mc', default=f'{OLY}/ep_dr/real_circuit/models_mc/sky130_5v_tt_mc.lib.spice')
ap.add_argument('--hog', default=f'{OLY}/sern_hog/char/decks/hog_tr.spice')
ap.add_argument('--r_diff', type=float, default=1e6)
ap.add_argument('--cf', type=float, default=20e-15)
ap.add_argument('--a_gain', type=float, default=2.0)
a = ap.parse_args()

HEAD = ['.option post=0 ingold=2 numdgt=8 measdgt=8', '.temp 25',
        f".lib '{a.lib_mc}' tt", '.param mc_mm_switch=1', '.param cc=100f rz=3k nls=1', f".include '{a.hog}'",
        'Vdd vdd 0 2.5', 'Vss vss 0 -2.5', 'Xbias vbn vbp vbpc vdd vss HOG_BIAS', 'Vbnc vbnc 0 -1.0', 'Vbpc vbpc 0 0.7']
(HERE / 'decks').mkdir(exist_ok=True)

# ── paths: row = +0.3 V, hid 를 바꿔 ΔV = 0.02 / 0.1 / 0.2 / 0.4 V
HID = [0.28, 0.2, 0.1, -0.1]
L = ['* mc_paths: A1–A4 출력 오차 e = out − 2|ΔV| (Monte Carlo), mc_block.py'] + HEAD + primitives()
L += [".param hid=0", "Vrow fp 0 0.3", "Vhid fm 0 'hid'", "Vrowm gp 0 -0.3", "Vhidm gm 0 '-hid'"]
for k, (vp, vm) in {1: ('fp', 'fm'), 3: ('fp', 'fm'), 2: ('gm', 'gp'), 4: ('gm', 'gp')}.items():
    L += diff_amp(k, vp, vm, 'vdd', 'vss', f'o{k}', a.r_diff, a.cf, a.a_gain)          # TG 켬: en = VDD, enb = VSS
    L += [f"Co{k} o{k} 0 20f", f"Ro{k} o{k} 0 1e12"]
for j, h in enumerate(HID):
    for k in (1, 2, 3, 4):
        L.append(f".meas dc e{k}_{j} find par('v(o{k})-{a.a_gain:g}*(0.3-({h}))') at={h}")
L += [f".dc hid POI {len(HID)} " + ' '.join(f'{h}' for h in HID) + f" sweep monte={a.n}", '.end']
(HERE / 'decks' / 'mc_paths.sp').write_text('\n'.join(L) + '\n')

# ── comp: 클록 40 ns (낮음 20 ns = reset, 높음 20 ns = 판정). 입력차는 reset 칸 가운데서 다음 값으로 → 칸 i 판정은 V0 + i·DV
T, N_ST, V0, DV = 40e-9, 121, -30e-3, 0.5e-3


def comp_deck(name, kind, cm):
    L = [f'* {name}: {kind} 입력 환산 offset (Monte Carlo), 공통 {cm} V, 입력차 {V0*1e3:g} mV 부터 칸마다 +{DV*1e3:g} mV'] + HEAD + primitives()
    pts = [(0.0, V0)]
    for i in range(1, N_ST):
        t = i * T + T / 4
        pts += [(t, V0 + DV * (i - 1)), (t + 0.2e-9, V0 + DV * i)]
    L += ["Vd vd 0 PWL(" + ' '.join(f'{t:.5e} {v:.6e}' for t, v in pts) + ")",
          "Vcm cmn 0 " + f"{cm}", "Ep inp cmn vd 0 0.5", "En inn cmn vd 0 -0.5"]
    # 실제 회로처럼 입력은 약한 노드: 3 kΩ (TG + 증폭기 출력) + 20 fF
    L += ["Rip inp inpx 3k", "Rin inn innx 3k", "Cip inpx 0 20f", "Cin innx 0 20f"]
    ck = [(0.0, -2.5)]
    for i in range(N_ST):
        ck += [(i * T + T / 2, -2.5), (i * T + T / 2 + 0.2e-9, 2.5), ((i + 1) * T - 0.2e-9, 2.5), ((i + 1) * T, -2.5)]
    L += ["Vck ck 0 PWL(" + ' '.join(f'{t:.5e} {v:g}' for t, v in ck) + ")"]
    if kind == 'COMP3':
        L += ["XP3 inpx innx pa3p pa3n vbn vdd vss PRE", "XC3 pa3p pa3n ck q qb vdd vss SA"]
    else:
        L += ["XC1 inpx innx ck q qb vdd vss SA"]
    L += [".option accurate relv=1e-7 absv=1e-10 reli=1e-7 absi=1e-15",
          ".meas tran tflip when v(q)=0 rise=1", f".tran 0.1n {N_ST*T:.4e} sweep monte={a.n}", '.end']
    (HERE / 'decks' / f'{name}.sp').write_text('\n'.join(L) + '\n')


comp_deck('mc_c3_cm06', 'COMP3', 0.6)
comp_deck('mc_c3_cm02', 'COMP3', 0.2)
comp_deck('mc_c1_cm01', 'COMP1', 0.1)
print('decks: mc_paths, mc_c3_cm06, mc_c3_cm02, mc_c1_cm01', f'(MC {a.n}, 판정 칸 {N_ST}, 칸 {T*1e9:.0f} ns)')
