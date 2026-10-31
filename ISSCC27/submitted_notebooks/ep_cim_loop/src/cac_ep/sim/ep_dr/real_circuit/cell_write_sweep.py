"""1T1R 셀 하나 (SKY130 RRAM VA + 접근 nFET W1.5/L0.5, body = VSS −2.5 V) 에 SET·RESET 펄스 — ±2.5 V 칩에서 쓰기 방식 고르기 (10/25 pre-sim).
이전 판 특성표 (ep_demo/char/out/dg_table_p0d.csv, body 0 V·0–5 V 전원) 는 RESET 이 WL 5 V 에서만 되고 2.5–3 V 에서는 안 됨 →
이 칩 (WL 최대 +2.5 V) 에서 RESET 을 어떻게 걸지 비교한다. 셀: 행 → RRAM (TE 행 쪽) → nFET → 열, 게이트 = WL.
경우 (펄스 10 ns, 처음 G = 50 µS): SET 행 +V / 열 0 · RESET ① 단극성 행 0 / 열 +V · ② 양극성 행 −V / 열 0 · ③ 반씩 행 −V/2 / 열 +V/2.
읽기 = 펄스 앞뒤 0.1 V (행 0.1 V, 열 0, WL 2.5 V) 전류 / 0.1 V.
쓰임: python cell_write_sweep.py → decks/cws.sp, 결과는 python cell_write_sweep.py check (out/cws.lis)
"""
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
VA = f"{OLY}/ep_demo/char/va/sky130_fd_pr_reram__reram_cell.va"
TOX, TFREF, IK1, VREF = 5.0e-9, 4.7249e-9, 6.140e-5, 0.430
tf_for_g = lambda g: TOX + (TOX - TFREF) * math.log(g * 0.1 / (IK1 * math.sinh(0.1 / VREF)))
G0, PW, TE = 50e-6, 10e-9, 1e-9
CASES = ([('SET', v, (v, 0.0)) for v in (1.6, 1.7, 1.8, 2.0)]
         + [('RST_uni', v, (0.0, v)) for v in (1.4, 1.6, 1.8, 2.0)]
         + [('RST_bip', v, (-v, 0.0)) for v in (1.4, 1.6, 1.8, 2.0)]
         + [('RST_half', v, (-v / 2, v / 2)) for v in (1.4, 1.6, 1.8, 2.0)]
         # 셀 방향을 뒤집음 (10/25 사용자 "칼럼에서 집어넣는 방식"): 행 → nFET → RRAM (TE 안쪽, BE 열 쪽) → 열
         + [('F_SET', v, (v, 0.0)) for v in (1.6, 1.8, 2.0, 2.4)]
         + [('F_RST_col', v, (0.0, v)) for v in (1.4, 1.6, 1.8, 2.0)])
T_RD0, T_P, T_RD1, TEND = 5e-9, 15e-9, 40e-9, 50e-9


def pwl(pts):
    return "PWL(" + " ".join(f"{t:.4e} {v:.4f}" for t, v in pts) + ")"


if len(sys.argv) < 2 or sys.argv[1] == 'write':
    L = ['* cws: 1T1R 셀 하나 SET / RESET 방식 비교 (body = VSS)', '.option post=0 ingold=2 numdgt=10 measdgt=10 method=gear',
         f'.hdl "{VA}"', f".lib '{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice' tt", '.temp 25', '.param tstep=10p',
         'Vss vss 0 -2.5']
    for k, (nm, v, (vr, vc)) in enumerate(CASES):
        # 행: 0 → 읽기 0.1 V → 0 → 펄스 vr → 0 → 읽기 0.1 V. 열: 펄스 때만 vc. WL: 2.5 V 계속
        row = [(0, 0), (T_RD0 - TE, 0), (T_RD0, 0.1), (T_RD0 + 5e-9, 0.1), (T_RD0 + 5e-9 + TE, 0), (T_P, 0), (T_P + TE, vr),
               (T_P + TE + PW, vr), (T_P + 2 * TE + PW, 0), (T_RD1 - TE, 0), (T_RD1, 0.1), (TEND, 0.1)]
        col = [(0, 0), (T_P, 0), (T_P + TE, vc), (T_P + TE + PW, vc), (T_P + 2 * TE + PW, 0), (TEND, 0)]
        L += [f"Vr{k} r{k} 0 {pwl(row)}", f"Vc{k} c{k} 0 {pwl(col)}", f"Vw{k} w{k} 0 2.5",
              f"Vs{k} r{k} te{k} 0",
              *([f"Xr{k} te{k} nd{k} sky130_fd_pr_reram__reram_cell Tfilament_0={tf_for_g(G0):.6e} t_step=tstep",
                 f"Xm{k} nd{k} w{k} c{k} vss sky130_fd_pr__nfet_g5v0d10v5 w=1.5 l=0.5"] if not nm.startswith('F_') else
                [f"Xm{k} te{k} w{k} nd{k} vss sky130_fd_pr__nfet_g5v0d10v5 w=1.5 l=0.5",
                 f"Xr{k} nd{k} c{k} sky130_fd_pr_reram__reram_cell Tfilament_0={tf_for_g(G0):.6e} t_step=tstep"]),
              f".meas tran g0_{k} find par('i(Vs{k})/0.1') at={T_RD0 + 4e-9:.4e}",
              f".meas tran g1_{k} find par('i(Vs{k})/0.1') at={TEND - 1e-9:.4e}",
              f".meas tran vc_{k} find " + (f"v(te{k},nd{k})" if not nm.startswith('F_') else f"v(nd{k},c{k})") + f" at={T_P + TE + PW / 2:.4e}",
              f".meas tran ip_{k} find i(Vs{k}) at={T_P + TE + PW / 2:.4e}"]
    L += [f".tran 10p {TEND:.4e}", '.end']
    (HERE / 'decks').mkdir(exist_ok=True)
    (HERE / 'decks' / 'cws.sp').write_text('\n'.join(L) + '\n')
    print('decks/cws.sp', len(CASES), '경우')
else:
    M = {k.lower(): float(v) for k, v in re.findall(r'^\s*(\w+)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)', (HERE / 'out' / 'cws.lis').read_text(), re.M)}
    print('경우 | 펄스 | RRAM 양단 (펄스 중) | 전류 | G 전 → 후 (0.1 V 읽기)')
    for k, (nm, v, (vr, vc)) in enumerate(CASES):
        print(f"{nm:9s} V {v:.1f} (행 {vr:+.2f}, 열 {vc:+.2f}) | {M[f'vc_{k}']:+.3f} V | {M[f'ip_{k}']*1e6:+8.1f} µA | "
              f"{M[f'g0_{k}']*1e6:6.2f} → {M[f'g1_{k}']*1e6:6.2f} µS ({(M[f'g1_{k}'] - M[f'g0_{k}'])*1e6:+.2f})")
