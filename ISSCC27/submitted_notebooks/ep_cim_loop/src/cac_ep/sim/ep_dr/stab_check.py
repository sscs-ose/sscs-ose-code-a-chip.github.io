"""stabilizer (G_bz) 가 지금 결과에 얼마나 영향을 주는지 (10/25 사용자 "Stabilizer의 효과가 유의미한가?").
학습된 가중치 (out/weights/tanh5_5bit.npz, val 최고점) 는 그대로 두고 G_bz 칸만 바꾼다 — 다시 학습하지 않는다.
  (1) 노드에 붙은 컨덕턴스 합 중 G_bz 비율 (hidden 열, 출력 행; R_on 은 빼고 셈)
  (2) test 정확도 (3,097장): 학습한 그대로 / G_bz → HRS (0.2984 µS, 프로그래밍 안 함) / G_bz → 0 (칸 없음)
  (3) 갱신 bit: 학습 표본 앞 N 장에서 sgn(|ΔV_n| − |ΔV_f|) 가 학습한 그대로일 때와 달라지는 셀 비율 (first / last stage)
쓰임: python stab_check.py [--n_bits 500] [--device cpu]  → 화면 표 + out/stab_check.json
"""
import argparse
import json

import numpy as np
import torch

from circuit import G_HRS, GBZ, NONE, W1, W2, row_drive
from data import load_task
from solver import cell_voltage, solve
from train import LAY, evaluate

ap = argparse.ArgumentParser()
ap.add_argument('--n_bits', type=int, default=500)
ap.add_argument('--device', default='cpu')
a = ap.parse_args()

W = np.load('out/weights/tanh5_5bit.npz')
infos = {i['key']: i for i in json.loads(str(W['info']))}
keys = sorted(infos)
kind = LAY.kind
m = torch.as_tensor((kind == W1) | (kind == W2), device=a.device)
VAR = ['trained', 'G_bz->HRS', 'G_bz->0']


def variants(G0):
    out = [G0.copy(), G0.copy(), G0.copy()]
    out[1][kind == GBZ] = G_HRS
    out[2][kind == GBZ] = 0.0
    return out


res = {}
# (1) 비율
for k in keys:
    G0 = np.where(kind != NONE, W[f'{k}/G_best'], 0.0)
    sh, sy = G0[:, LAY.c_h].sum(0), G0[LAY.r_y, :].sum(1)
    fh, fy = G0[LAY.r_s, LAY.c_h] / sh, G0[LAY.r_y, LAY.c_s] / sy
    res[k] = dict(share_hidden=[float(fh.min()), float(np.median(fh)), float(fh.max())],
                  share_out=[float(fy.min()), float(np.median(fy)), float(fy.max())],
                  sum_hidden_uS=[float(sh.min() * 1e6), float(sh.max() * 1e6)], sum_out_uS=[float(sy.min() * 1e6), float(sy.max() * 1e6)])
    print(f"{k}: G_bz 비율 hidden {fh.min()*100:.2f}–{fh.max()*100:.2f} % (중앙 {np.median(fh)*100:.2f}), "
          f"출력 {fy.min()*100:.2f}–{fy.max()*100:.2f} % (중앙 {np.median(fy)*100:.2f}) | "
          f"합 hidden {sh.min()*1e6:.0f}–{sh.max()*1e6:.0f} µS, 출력 {sy.min()*1e6:.0f}–{sy.max()*1e6:.0f} µS", flush=True)

# (2) test 정확도 — seed 3 × 변형 3 을 batch 하나로 (config 는 seed 끼리 같음)
c = infos[keys[0]]['config']
CK = ('a', 'r_on', 'v_b', 'r_ser', 'no_out_clamp', 'beta', 'g_bz')
assert all(infos[k]['config'][x] == c[x] for k in keys for x in CK)   # seed·tag 만 다름
kw = dict(v_b=c['v_b'], r_ser=c['r_ser'], out_diode=not c['no_out_clamp'])
Xte, yte = load_task('t10k')
Gb = torch.as_tensor(np.stack([g for k in keys for g in variants(W[f'{k}/G_best'])]), device=a.device)
acc, _ = evaluate(LAY, Gb, Xte, yte, c['a'], c['r_on'], m, **kw)
acc = acc.view(len(keys), 3).cpu().numpy()
for i, k in enumerate(keys):
    res[k]['test_acc'] = dict(zip(VAR, acc[i].tolist()))
    print(f"{k}: test " + " / ".join(f"{v} {acc[i, j]*100:.2f} %" for j, v in enumerate(VAR)), flush=True)

# (3) 갱신 bit
Xtr, ytr = load_task('train')
X, y = Xtr[:a.n_bits], ytr[:a.n_bits]
n_out = len(LAY.r_y) // 2
mW1, mW2 = torch.as_tensor(kind == W1, device=a.device), torch.as_tensor(kind == W2, device=a.device)
for k in keys:
    Gv = torch.as_tensor(np.stack(variants(W[f'{k}/G_best'])), device=a.device)      # (3, R, C)
    diff = np.zeros((3, 2)); tot = np.zeros(2)
    for i0 in range(0, len(X), 100):
        s, lab = X[i0:i0 + 100], y[i0:i0 + 100]
        n = len(s)
        u = torch.as_tensor(row_drive(LAY, s, c['a']), device=a.device).repeat(3, 1)
        Gn = Gv.repeat_interleave(n, 0)
        t = torch.as_tensor(np.where(np.eye(n_out)[lab] > 0, 1.0, -1.0), device=a.device).repeat(3, 1)
        vh_f, vy_f, _ = solve(LAY, Gn, u, r_on=c['r_on'], **kw)
        e = torch.sign(t - (vy_f[:, 0::2] - vy_f[:, 1::2]))
        inj = torch.stack([c['beta'] * e, -c['beta'] * e], -1).reshape(len(u), -1)
        vh_n, vy_n, _ = solve(LAY, Gn, u, i_nudge=inj, r_on=c['r_on'], v0=(vh_f, vy_f), **kw)
        b = ((cell_voltage(LAY, u, vh_n, vy_n).abs() - cell_voltage(LAY, u, vh_f, vy_f).abs()) >= 0).view(3, n, *kind.shape)
        for j in range(3):
            for st, mm in enumerate((mW1, mW2)):
                diff[j, st] += (b[j][:, mm] != b[0][:, mm]).sum().item()
        tot += [n * mW1.sum().item(), n * mW2.sum().item()]
    res[k]['bit_flip_frac'] = {VAR[j]: (diff[j] / tot).tolist() for j in (1, 2)}
    print(f"{k}: 갱신 bit 이 바뀐 셀 (학습 표본 {len(X)} 장) — " + " / ".join(
        f"{VAR[j]}: first {diff[j,0]/tot[0]*100:.2f} %, last {diff[j,1]/tot[1]*100:.2f} %" for j in (1, 2)), flush=True)

json.dump(res, open('out/stab_check.json', 'w'), indent=1)
