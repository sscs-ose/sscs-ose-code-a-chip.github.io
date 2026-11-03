"""free·nudge 크로스바가 따로 있을 때 두 배열의 셀 컨덕턴스 차이 (프로그래밍 오차) 가 갱신 bit 를 얼마나 틀리게 하는지 (10/25, pre-sim).
학습 셀 (W1·W2) 마다 G_f = G·(1 + σ·N₁), G_n = G·(1 + σ·N₂) (독립 정규분포), free 해는 G_f, nudge 해는 G_n 로 푼다.
정답 bit = 같은 G 로 푼 sgn(|ΔV_n| − |ΔV_f|) (train.py), 틀린 비율을 stage 마다 센다. 회로 오차 (offset) 는 넣지 않는다.
쓰임: python xbar_mismatch.py [--n_x 200] [--sig 0.0001 0.001 0.003 0.01 0.03] [--draws 3] → 화면 표 + out/xbar_mismatch.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from circuit import W1, W2, row_drive
from data import load_task
from solver import cell_voltage, solve
from train import layout_of

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--n_x', type=int, default=200)
ap.add_argument('--sig', type=float, nargs='+', default=[1e-4, 1e-3, 3e-3, 1e-2, 3e-2])
ap.add_argument('--draws', type=int, default=3)
ap.add_argument('--weights', default=str(HERE / 'out' / 'weights' / 'nostab_5bit.npz'))
ap.add_argument('--key', default='5b_s0')
a = ap.parse_args()
W = np.load(a.weights)
LAY = layout_of(W)
c = {i['key']: i for i in json.loads(str(W['info']))}[a.key]['config']
G0 = W[f'{a.key}/G_best']
X, y = load_task('train')
X, y = X[:a.n_x], y[:a.n_x]
u = torch.as_tensor(row_drive(LAY, X, c['a']))
kw = dict(r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'], out_diode=not c['no_out_clamp'])
t = torch.as_tensor(np.where(np.eye(len(LAY.r_y) // 2)[y] > 0, 1.0, -1.0))
learn = (LAY.kind == W1) | (LAY.kind == W2)


def bits(Gf, Gn):
    gf = torch.as_tensor(Gf)[None].expand(len(y), -1, -1)
    gn = torch.as_tensor(Gn)[None].expand(len(y), -1, -1)
    vh_f, vy_f, _ = solve(LAY, gf, u, **kw)
    e = torch.sign(t - (vy_f[:, 0::2] - vy_f[:, 1::2]))
    inj = torch.stack([c['beta'] * e, -c['beta'] * e], -1).reshape(len(y), -1)
    vh_n, vy_n, _ = solve(LAY, gn, u, i_nudge=inj, v0=(vh_f, vy_f), **kw)
    d = (cell_voltage(LAY, u, vh_n, vy_n).abs() - cell_voltage(LAY, u, vh_f, vy_f).abs()).numpy()
    return d >= 0


ref = bits(G0, G0)
rng = np.random.default_rng(0)
res = {}
for s in a.sig:
    fr = {1: [], 2: []}
    for _ in range(a.draws):
        Gf, Gn = G0.copy(), G0.copy()
        Gf[learn] *= 1 + s * rng.standard_normal(int(learn.sum()))
        Gn[learn] *= 1 + s * rng.standard_normal(int(learn.sum()))
        b = bits(Gf, Gn)
        for st, kd in ((1, W1), (2, W2)):
            msk = LAY.kind == kd
            fr[st].append(float((b[:, msk] != ref[:, msk]).mean()))
    res[s] = fr
    print(f"σ(G)/G {s*100:.2f} %: 갱신 bit 이 틀린 셀 first {np.mean(fr[1])*100:.1f} % (draw {', '.join(f'{x*100:.1f}' for x in fr[1])}), "
          f"last {np.mean(fr[2])*100:.1f} % (draw {', '.join(f'{x*100:.1f}' for x in fr[2])})", flush=True)
json.dump({str(k): v for k, v in res.items()}, open(HERE / 'out' / 'xbar_mismatch.json', 'w'), indent=1)
