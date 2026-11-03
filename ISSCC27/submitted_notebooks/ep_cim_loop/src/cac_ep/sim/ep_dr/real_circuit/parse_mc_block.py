"""mc_block.py 덱 결과 → weight update 회로 한 벌 (= 칩 하나) 마다 판정 경계 δ_th, 그리고 그 칩에서 갱신 bit 가 틀리는 셀 비율.

  δ_th = (e_f − e_n − V_os3) / 2      셀의 δ = |ΔV_n| − |ΔV_f| 가 0 과 δ_th 사이면 bit 가 뒤집힌다
  e_f, e_n : ΔV > 0 셀은 A1 (free)·A3 (nudge), ΔV < 0 셀은 A2·A4 의 출력 오차 (mc_paths, ΔV 4 점)
  V_os3    : COMP3 (전치 증폭기 + StrongARM) offset — first stage 는 공통 0.6 V 덱, last stage 는 0.2 V 덱
SPICE MC 의 index 1 은 공칭 (부정합 없음) 이라 통계에서 뺀다. 경로 표본 i 와 비교기 표본 i 를 한 칩으로 묶는다 (서로 다른 소자라 독립).
셀 δ 분포: 기준 가중치 (nostab_5bit.npz, seed 0 최고점) 로 학습 표본 앞 --n_x 장의 free·nudge 해 (../solver.py).
쓰임: python parse_mc_block.py [--n_x 200]  → 화면 표 + out/mc_block.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from circuit import W1, W2, row_drive              # noqa: E402
from data import load_task                         # noqa: E402
from solver import cell_voltage, solve             # noqa: E402
from train import layout_of                        # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--n_x', type=int, default=200, help='셀 δ 분포에 쓸 학습 표본 수')
ap.add_argument('--weights', default=str(HERE.parent / 'out' / 'weights' / 'nostab_5bit.npz'))
ap.add_argument('--key', default='5b_s0')
a = ap.parse_args()
T, V0, DV = 40e-9, -30e-3, 0.5e-3                 # mc_block.py 와 같음
HID = [0.28, 0.2, 0.1, -0.1]                       # ΔV = 0.3 − hid


def table(f):
    rows = [l.split() for l in f.read_text().splitlines() if l.strip() and not l.startswith(('$', '.'))]
    hi = next(i for i, r in enumerate(rows) if r[0] == 'index')
    hdr = rows[hi]
    D = {h: [] for h in hdr}
    for r in rows[hi + 1:]:
        for h, v in zip(hdr, r):
            D[h].append(float(v) if v.lower() not in ('failed', 'nan') else np.nan)
    return {h: np.array(v) for h, v in D.items()}


P = table(HERE / 'out' / 'mc_paths.ms0')
ok = P['index'] > 1
e = {k: np.stack([P[f'e{k}_{j}'][ok] for j in range(len(HID))], 1) for k in (1, 2, 3, 4)}   # (표본, ΔV 점)


def vos(name):
    t = table(HERE / 'out' / f'{name}.mt0')['tflip'][1:]
    v = V0 + DV * np.floor(t / T) - DV / 2           # 마지막 0 과 처음 1 사이
    return np.where(np.isfinite(t), v, np.nan)


res = dict(n=int(ok.sum()), dV=[0.3 - h for h in HID])
print(f"MC 표본 {ok.sum()} 개 (공칭 제외)")
for k in (1, 2, 3, 4):
    print(f"  A{k} 출력 오차 e: 공칭 {P[f'e{k}_0'][0]*1e3:+.2f} mV, MC 평균 {np.nanmean(e[k][:, 0])*1e3:+.2f}, σ {np.nanstd(e[k][:, 0])*1e3:.2f} mV "
          f"(ΔV {0.3-HID[0]:.2f} V) / σ {np.nanstd(e[k][:, -1])*1e3:.2f} mV (ΔV {0.3-HID[-1]:.2f} V)")
d13, d24 = (e[1] - e[3]) / 2, (e[2] - e[4]) / 2
print(f"  (e_A1 − e_A3)/2 σ {np.nanstd(d13[:, 0])*1e3:.2f} mV, (e_A2 − e_A4)/2 σ {np.nanstd(d24[:, 0])*1e3:.2f} mV  (δ 로 환산한 경로 몫)")
vo = {n: vos(n) for n in ('mc_c3_cm06', 'mc_c3_cm02', 'mc_c1_cm01')}
for n, v in vo.items():
    print(f"  {n}: offset 평균 {np.nanmean(v)*1e3:+.2f} mV, σ {np.nanstd(v)*1e3:.2f} mV, ±30 mV 밖 {np.isnan(v).sum()} 개")
    res[n] = dict(mean=float(np.nanmean(v)), std=float(np.nanstd(v)), out_of_range=int(np.isnan(v).sum()))
n = min(len(d13), len(vo['mc_c3_cm06']))
th = {1: (d13[:n, 2] - vo['mc_c3_cm06'][:n] / 2, d24[:n, 2] - vo['mc_c3_cm06'][:n] / 2),     # first stage: |ΔV| 0.2 V 점
      2: (d13[:n, 1] - vo['mc_c3_cm02'][:n] / 2, d24[:n, 1] - vo['mc_c3_cm02'][:n] / 2)}     # last stage: |ΔV| 0.1 V 점
for s in (1, 2):
    p, q = th[s]
    print(f"  {'first' if s == 1 else 'last'} stage δ_th (ΔV>0 / <0): σ {np.nanstd(p)*1e3:.2f} / {np.nanstd(q)*1e3:.2f} mV, "
          f"|δ_th| 중앙 {np.nanmedian(np.abs(p))*1e3:.2f} mV")

# ── 셀 δ 분포 (Python) → 칩마다 틀리는 bit 비율
W = np.load(a.weights)
LAY = layout_of(W)
c = {i['key']: i for i in json.loads(str(W['info']))}[a.key]['config']
G = torch.as_tensor(W[f'{a.key}/G_best'])[None]
X, y = load_task('train')
X, y = X[:a.n_x], y[:a.n_x]
u = torch.as_tensor(row_drive(LAY, X, c['a']))
kw = dict(r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'], out_diode=not c['no_out_clamp'])
Gb = G.expand(len(y), -1, -1)
vh_f, vy_f, _ = solve(LAY, Gb, u, **kw)
t = torch.as_tensor(np.where(np.eye(len(LAY.r_y) // 2)[y] > 0, 1.0, -1.0))
e_ = torch.sign(t - (vy_f[:, 0::2] - vy_f[:, 1::2]))
inj = torch.stack([c['beta'] * e_, -c['beta'] * e_], -1).reshape(len(y), -1)
vh_n, vy_n, _ = solve(LAY, Gb, u, i_nudge=inj, v0=(vh_f, vy_f), **kw)
Vf, Vn = cell_voltage(LAY, u, vh_f, vy_f).numpy(), cell_voltage(LAY, u, vh_n, vy_n).numpy()
dl = np.abs(Vn) - np.abs(Vf)
for s, kd in ((1, W1), (2, W2)):
    msk = LAY.kind == kd
    d, pos = dl[:, msk], Vf[:, msk] > 0
    print(f"  {'first' if s == 1 else 'last'} stage 셀 |δ| (학습 표본 {len(y)} 장): 중앙 {np.median(np.abs(d))*1e3:.3f} mV, "
          f"10–90 % {np.percentile(np.abs(d), 10)*1e3:.3f}–{np.percentile(np.abs(d), 90)*1e3:.3f} mV")
    p, q = th[s]
    wrong = []
    for i in range(n):
        if not (np.isfinite(p[i]) and np.isfinite(q[i])):
            wrong.append(np.nan); continue
        tt = np.where(pos, p[i], q[i])                                  # 셀마다 그 부호의 경로 경계
        wrong.append(float((((d >= 0) != (d >= tt))).mean()))
    wrong = np.array(wrong)
    res[f'stage{s}'] = dict(th_pos=p.tolist(), th_neg=q.tolist(), wrong_frac=wrong.tolist(),
                            cell_abs_delta_median=float(np.median(np.abs(d))))
    print(f"    칩마다 bit 가 틀리는 셀 비율: 중앙 {np.nanmedian(wrong)*100:.1f} %, 10–90 % {np.nanpercentile(wrong, 10)*100:.1f}–"
          f"{np.nanpercentile(wrong, 90)*100:.1f} %, 공칭 (부정합 없음) 기준")
json.dump(res, open(HERE / 'out' / 'mc_block.json', 'w'), indent=1)
