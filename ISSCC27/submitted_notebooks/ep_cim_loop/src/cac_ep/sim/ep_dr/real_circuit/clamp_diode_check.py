"""은닉 clamp 다이오드: 덱 카드 (level-1 is 5e-10 n 1.2) 대 실제 SKY130 소자 (10/28, 사용자 "동시 확인 한번 해 봐").
열 블록 clamp 매크로 (digital/macros/clamp_d2r.cdl) = diode_pd2nw_11v0 면적 2.548 µm² · 둘레 7.97 µm + 직렬 100 Ω, 가지 둘
(위: 노드 → R → D → rail_up, 아래: rail_dn → D → R → 노드). 덱은 rail_up = −v_b, rail_dn = +v_b (v_b 0.3 V, 칩에서는 VRAILM·VRAILP).
모형 파일: volare sky130A libs.ref/sky130_fd_pr/spice/sky130_fd_pr__diode_pd2nw_11v0.model.spice → Olympus real_circuit/models/ 사본.
면적·둘레 단위는 µm²·µm (모형 cj·js 가 µm 당 값, sky130_fd_io 의 area=5e13 은 scale 1e-6 을 쓰는 추출 netlist 라 다름).
write: decks/clamp_iv.sp (노드 전압 −1.5…1.5 V 쓸기, 변형마다 같은 노드에 0 V 전류계):
  card = 덱 카드 ±v_b,  real = 실제 소자 ±v_b (지금 칩 연결),  real_d<ΔV> = 실제 소자, rail 을 ±(v_b + ΔV) 로 벌림 (따로 패드를 둘 때)
compare: .lis 표를 읽어 가지 전류 1·10·100 µA 에서의 노드 전압, 카드와 가장 가까운 ΔV.
쓰임: python clamp_diode_check.py write   /   python clamp_diode_check.py compare
"""
import argparse
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OLY = '/home/grads/s/seokjindaveoh/work'
D_IS, D_N, V_B, R_SER = 5e-10, 1.2, 0.3, 100.0
AREA, PJ = 2.548, 7.97
DVS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
ap = argparse.ArgumentParser()
ap.add_argument('task', choices=['write', 'compare'])
ap.add_argument('--name', default='clamp_iv')
a = ap.parse_args()
# SPICE 는 level-3 다이오드의 area·pj 를 1e-12·1e-6 배로 읽음 (area=2.548 → 1.5 V 에서 1e-14 A, 10/28 잡 721212) → GEO 로 맞춤.
# 해석식 (PDK 의도, 면적 계수 = µm² 숫자): Is = js·A + jsw·P = 2.1483e-17·2.548 + 4.02e-18·7.97 = 8.68e-17 A, n 1.3632, RS = 600/A = 235 Ω → lv1eq
GEO = f'area={AREA}e12 pj={PJ}e6'
VAR = [('card', 0.0, 'dlv1', ''), ('real', 0.0, 'sky130_fd_pr__diode_pd2nw_11v0', GEO),
       ('real_raw', 0.0, 'sky130_fd_pr__diode_pd2nw_11v0', f'area={AREA} pj={PJ}'), ('lv1eq', 0.0, 'dlv1eq', '')] + \
      [(f'real_d{int(round(d * 100))}', d, 'sky130_fd_pr__diode_pd2nw_11v0', GEO) for d in DVS]

if a.task == 'write':
    L = [f'* {a.name}: hidden clamp branch I-V, deck card vs SKY130 diode_pd2nw_11v0 (area {AREA} um2, pj {PJ} um)',
         '.option post=0 ingold=2 numdgt=8 nomod', '.temp 25',
         f".lib '{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice' tt",
         f".include '{OLY}/ep_dr/real_circuit/models/sky130_fd_pr__diode_pd2nw_11v0.model.spice'",
         f'.model dlv1 d (level=1 is={D_IS} n={D_N} rs=0)', '.model dlv1eq d (level=1 is=8.68e-17 n=1.3632 rs=235)', 'Vn n 0 0']
    for k, (nm, dv, mdl, geo) in enumerate(VAR):
        vb = V_B + dv
        L += [f'Vm{k} n n{k} 0', f'Vu{k} ru{k} 0 {-vb:g}', f'Vd{k} rd{k} 0 {vb:g}',
              f'Ra{k} n{k} a{k} {R_SER:g}', f'Da{k} a{k} ru{k} {mdl} {geo}',
              f'Db{k} rd{k} b{k} {mdl} {geo}', f'Rb{k} b{k} n{k} {R_SER:g}',
              f'Vmu{k} n n{k}u 0', f'Rau{k} n{k}u au{k} {R_SER:g}', f'Dau{k} au{k} ru{k} {mdl} {geo}']   # 위 가지만 (켜짐 전압 읽기)
    L += ['.dc Vn -1.5 1.5 0.005', '.print dc ' + ' '.join(f'i(Vm{k}) i(Vmu{k})' for k in range(len(VAR))), '.end']
    (HERE / 'decks' / f'{a.name}.sp').write_text('\n'.join(L) + '\n')
    print(f'{a.name}.sp: 변형 {len(VAR)} 개')
else:
    txt = (HERE / 'out' / f'{a.name}.lis').read_text()
    rows = []
    for blk in re.split(r'\n\s*x\s*\n', txt)[1:]:
        for ln in blk.split('\n'):
            t = ln.split()
            if len(t) > 2:
                try:
                    rows.append([float(v) for v in t])
                except ValueError:
                    pass
            if ln.strip().startswith('y'):
                break
    # .print 이 열이 많으면 표가 여러 덩어리로 나뉨 → 같은 V 끼리 이어 붙임
    by_v = {}
    for r in rows:
        by_v.setdefault(round(r[0], 6), []).extend(r[1:])
    V = np.array(sorted(by_v)); M = np.array([by_v[v] for v in V])
    assert M.shape[1] == 2 * len(VAR), M.shape
    print(f'노드 전압 쓸기 {V[0]:.2f}…{V[-1]:.2f} V, 점 {len(V)}')
    up = {nm: M[:, 2 * k + 1] for k, (nm, *_) in enumerate(VAR)}
    tot = {nm: M[:, 2 * k] for k, (nm, *_) in enumerate(VAR)}
    v_at = lambda i, I: float(np.interp(I, np.abs(i[V > 0]), V[V > 0]))    # 위 가지: V > 0 쪽에서 |I| 가 커짐
    print('위 가지 전류 → 노드 전압 (V):   1 µA   10 µA   100 µA')
    for nm in up:
        print(f'  {nm:10s} ' + '  '.join(f'{v_at(up[nm], I):6.3f}' for I in (1e-6, 1e-5, 1e-4)))
    m = (np.abs(V) <= 0.6)
    print('노드 전압 |V| ≤ 0.6 V 에서 clamp 전체 전류 (카드 대비), 0 V 근처 기울기 (µS):')
    g0 = lambda i: float(np.gradient(i, V)[np.argmin(np.abs(V))]) * 1e6
    for nm in tot:
        err = np.max(np.abs(tot[nm][m] - tot['card'][m])) * 1e6
        print(f'  {nm:10s} 최대 차 {err:8.2f} µA,  I(0.3 V) {tot[nm][np.argmin(np.abs(V - 0.3))] * 1e6:8.3f} µA,  기울기 {g0(tot[nm]):8.2f}')
