"""DRN 회로 그대로 학습, 셀 쓰기는 Oh 2023 부호 규칙 (README §1, §4 단계 4·5).

한 표본 (online, 표본 하나씩):
  free  : 크로스바 1 — 입력만
  nudge : 크로스바 2 — 같은 G, 출력 y+ 에 +β·e, y− 에 −β·e, e = sgn(t − (y+ − y−)_free), t = ±1 V
          이 회로는 |y+ − y−| < 1 V 라 e = t → 두 크로스바를 기다림 없이 한 번에 푼다 (2B 개 회로를 한 호출로).
          |y+ − y−| ≥ 1 V 가 나오면 이 가정이 깨지므로 멈춘다.
  갱신  : W1·W2 셀마다 b = |ΔV_n| − |ΔV_f| (ΔV = V_행 − V_열), 준위 −sgn(b) (b = 0 이면 + 로 봄, Oh 2023).
          모든 학습 셀이 매 표본 한 준위씩 움직이고 [0, 2^N − 1] 에서 멈춘다. G_bz·HRS 셀은 고정.
  해상도: 준위 2^N 개, G = G_min + L·ΔG_N, ΔG_N = (G_max − G_min)/(2^N − 1) (README §3 #5).
  초기화: 학습 셀마다 35 % 맨 위 준위 / 65 % 맨 아래 (README §3 #8). seed 가 같으면 bit 가 달라도 같은 배치.
batch 축은 표본이 아니라 독립 실행 (bit × seed) 이다. 실행들은 같은 표본 순서를 본다.
--n_val > 0 이면 학습 셋에서 val 을 떼어 평가·최고점 선택에 쓰고, test 는 끝에 val 최고점에서 한 번만 잰다.

사용: python train.py --bits 3 4 5 6 --seeds 0 1 2 --epochs 10 --n_val 1000 --tag main
"""
import argparse
import csv
import itertools
import json
import time
from pathlib import Path

import numpy as np
import torch

from circuit import D_RS, G_WIN, NONE, R_ON, V_B, W1, W2, Layout, init_G, row_drive
from data import DIGITS, THR, load_task
from solver import branch_iv, cell_iv, cell_voltage, diode_iv, solve

LAY = Layout(n_in=49, n_hid=30, n_out=3, rows=128, cols=64)     # 107 × 61 사용 → 128 × 64
LAY_NS = Layout(n_in=49, n_hid=30, n_out=3, rows=128, cols=64, stab=False)   # stabilizer 없음 (10/25, README §12): 106 × 60 사용


def layout_of(W):
    """정리 파일 (export_weights.py) 의 배치: 'stab' 키가 0 이면 LAY_NS, 없거나 1 이면 LAY."""
    return LAY_NS if ('stab' in W.files and not bool(W['stab'])) else LAY
FIELDS = ['epoch', 'step', 'run', 'bits', 'seed', 'train_acc', 'val_acc', 'test_acc', 'mean_abs_b_V', 'frac_min',
          'frac_max', 'vh_abs_mean', 'vh_frac_over_0p24', 'vy_abs_mean', 'cell_abs_max_V', 'cell_abs_max_train_V',
          'vh_frac_clamp', 'vy_frac_clamp', 'p_neuron_uW', 'p_xbar_uW', 'sec']
# cell_abs_max_V: 평가 (free) 의 학습 셀 최대 |V|. cell_abs_max_train_V: 직전 평가 뒤 학습 표본들의 free·nudge 두 단계,
# 연결된 모든 셀 (G_bz·HRS 포함) 최대 |V| — 읽기 교란 한도 0.6 V 확인용.
# *_frac_clamp: 다이오드 dI/dV ≥ 그 노드에 붙은 셀 dI/dV 합인 노드 비율 (노드의 입력 → 전압 기울기 ≤ 0.5, clamp 가 거는 구간).
# p_neuron_uW: free 표본당 다이오드 가지 (R_ser 포함) 전력 합, p_xbar_uW: free 표본당 연결 셀 (R_on 포함) 전력 합.


def levels_init(lay, seed, lmax):
    """학습 셀: 35 % → lmax, 65 % → 0. 나머지 칸은 0 (쓰지 않음)."""
    m = (lay.kind == W1) | (lay.kind == W2)
    L = np.zeros((lay.rows, lay.cols))
    L[m] = np.where(np.random.default_rng(seed).random(int(m.sum())) < 0.35, lmax, 0)
    return L


@torch.no_grad()
def evaluate(lay, G, X, y, a, r_on, m, v_b=V_B, r_ser=D_RS, out_diode=True):
    """정확도와 노드·셀 통계 (실행별)."""
    B, dev = G.shape[0], G.device
    chunk = max(1, 1024 // B)
    hit = torch.zeros(B, device=dev, dtype=torch.float64)
    vh_abs, vh_on, vy_abs, cmax, hcl, ycl, pn, px = (torch.zeros(B, device=dev, dtype=torch.float64) for _ in range(8))
    yt = torch.as_tensor(y, device=dev)
    conn = torch.as_tensor(lay.kind != NONE, device=dev)
    c_h, r_y = torch.as_tensor(lay.c_h, device=dev), torch.as_tensor(lay.r_y, device=dev)
    for i0 in range(0, len(X), chunk):
        n = min(chunk, len(X) - i0)
        u = torch.as_tensor(row_drive(lay, X[i0:i0 + n], a), device=dev).repeat(B, 1)
        Gn = G.repeat_interleave(n, 0)
        vh, vy, _ = solve(lay, Gn, u, r_on=r_on, v_b=v_b, r_ser=r_ser, out_diode=out_diode)
        d = (vy[:, 0::2] - vy[:, 1::2]).view(B, n, -1)
        hit += (d.argmax(-1) == yt[i0:i0 + n]).sum(1)
        vh_abs += vh.abs().view(B, -1).mean(1) * n
        vh_on += (vh.abs() > 0.24).double().view(B, -1).mean(1) * n
        vy_abs += vy.abs().view(B, -1).mean(1) * n
        Vc = cell_voltage(lay, u, vh, vy)
        cmax = torch.maximum(cmax, Vc[:, m].abs().view(B, -1).max(1).values)
        I, g = cell_iv(Gn, Vc, r_on)
        hcl += (diode_iv(vh, v_b, r_ser)[1] >= g[:, :, c_h].sum(1)).double().view(B, -1).mean(1) * n
        if out_diode:
            ycl += (diode_iv(vy, v_b, r_ser)[1] >= g[:, r_y, :].sum(2)).double().view(B, -1).mean(1) * n
        vn = torch.cat([vh, vy], 1) if out_diode else vh
        p = branch_iv(vn + v_b, r_ser)[0] * (vn + v_b) + branch_iv(v_b - vn, r_ser)[0] * (v_b - vn)
        pn += p.sum(1).view(B, n).sum(1)
        px += (I * Vc)[:, conn].sum(1).view(B, n).sum(1)
    N = len(X)
    return hit / N, dict(vh_abs_mean=vh_abs / N, vh_frac_over_0p24=vh_on / N, vy_abs_mean=vy_abs / N, cell_abs_max_V=cmax,
                         vh_frac_clamp=hcl / N, vy_frac_clamp=ycl / N, p_neuron_uW=pn / N * 1e6, p_xbar_uW=px / N * 1e6)


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bits', type=int, nargs='+', default=[5])
    ap.add_argument('--seeds', type=int, nargs='+', default=[0])
    ap.add_argument('--epochs', type=int, default=10)
    ap.add_argument('--beta', type=float, default=1e-7, help='nudge 전류 [A] (Oh 2023: 0.1 µA)')
    ap.add_argument('--g_bz', type=float, default=10e-6, help='stabilizer 고정값 [S]')
    ap.add_argument('--a', type=float, default=0.3, help='입력 진폭 [V] (x± = Vcm ± a)')
    ap.add_argument('--r_on', type=float, default=R_ON, help='1T1R 직렬 저항 [Ω], 0 이면 없음')
    ap.add_argument('--v_b', type=float, default=V_B, help='clamp 레일 오프셋 [V]: rail_up = Vcm − v_b, rail_dn = Vcm + v_b')
    ap.add_argument('--r_ser', type=float, default=D_RS, help='다이오드 가지 직렬 저항 [Ω] (기본 1 kΩ = 이전 카드 rs)')
    ap.add_argument('--no_out_clamp', action='store_true', help='출력 노드 다이오드 없음 (hidden 만 tanh, Oh 2023 neuron 배치)')
    # 10/25 pre-sim (README §13): 회로가 갱신 bit 를 틀리게 만드는 몫을 학습에 넣어 본다. 기본값이면 지금과 같다
    ap.add_argument('--th1', type=float, default=0.0, help='first stage 판정 경계 [V]: δ = |ΔV_n| − |ΔV_f| ≥ th1 이면 RESET (weight update 회로 offset)')
    ap.add_argument('--th2', type=float, default=0.0, help='last stage 판정 경계 [V]')
    ap.add_argument('--freeze1', action='store_true', help='first stage 셀을 갱신하지 않음')
    ap.add_argument('--xbar_sig', type=float, default=0.0, help='free·nudge 크로스바 학습 셀 컨덕턴스 차이 σ (상대값, 실행마다 고정). 추론은 free 배열')
    ap.add_argument('--n_val', type=int, default=0, help='학습 셋에서 떼어 낼 val 장수. 0 이면 test 로 평가')
    ap.add_argument('--n_train', type=int, default=0, help='val 을 뗀 나머지에서 쓸 장수. 0 이면 전부')
    ap.add_argument('--n_test', type=int, default=0, help='0 이면 전부 (3,097)')
    ap.add_argument('--eval_every', type=int, default=0, help='표본 수. 0 이면 epoch 끝에만')
    ap.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    ap.add_argument('--tag', default='run')
    return ap


def train(a, report=None):
    """report(step, acc (B,)) 를 평가마다 부른다 (Optuna 가지치기용). 반환: 마지막·최고 평가 정확도 등."""
    out = Path(__file__).parent / 'out' / 'runs' / a.tag
    out.mkdir(parents=True, exist_ok=True)
    dev = torch.device(a.device)
    Xtr, ytr = load_task('train')
    Xte, yte = load_task('t10k')
    if a.n_val:
        p = np.random.default_rng(2).permutation(len(ytr))
        Xva, yva, Xtr, ytr = Xtr[p[:a.n_val]], ytr[p[:a.n_val]], Xtr[p[a.n_val:]], ytr[p[a.n_val:]]
    if a.n_train:
        i = np.random.default_rng(0).choice(len(ytr), a.n_train, replace=False); Xtr, ytr = Xtr[i], ytr[i]
    if a.n_test:
        i = np.random.default_rng(1).choice(len(yte), a.n_test, replace=False); Xte, yte = Xte[i], yte[i]
    EX, Ey, ename = (Xva, yva, 'val') if a.n_val else (Xte, yte, 'test')
    T = np.where(np.eye(LAY.n_out)[ytr] > 0, 1.0, -1.0)

    runs = list(itertools.product(a.bits, a.seeds))
    B = len(runs)
    lmax = torch.tensor([2 ** n - 1 for n, _ in runs], device=dev, dtype=torch.float64).view(B, 1, 1)
    dg = (G_WIN[1] - G_WIN[0]) / lmax
    m = torch.as_tensor((LAY.kind == W1) | (LAY.kind == W2), device=dev)
    conn = torch.as_tensor(LAY.kind != NONE, device=dev)
    base = torch.as_tensor(init_G(LAY, np.random.default_rng(0), '2023', a.g_bz)[0], device=dev)  # 고정 칸 (G_bz·HRS)
    L = torch.stack([torch.as_tensor(levels_init(LAY, s, 2 ** n - 1), device=dev) for n, s in runs])
    G_of = lambda L: torch.where(m, G_WIN[0] + L * dg, base)
    mW1 = torch.as_tensor(LAY.kind == W1, device=dev)
    th = torch.where(mW1, a.th1, a.th2)                                     # 셀마다 판정 경계 (stage 별)
    mu = m & ~mW1 if a.freeze1 else m                                        # 갱신하는 셀
    if a.xbar_sig:                                                           # free·nudge 배열 컨덕턴스 차이 (실행마다 고정)
        gen = torch.Generator().manual_seed(777 + a.seeds[0])
        ef, en = (1 + a.xbar_sig * torch.randn((B, LAY.rows, LAY.cols), generator=gen, dtype=torch.float64).to(dev) * m
                  for _ in range(2))
    else:
        ef = en = torch.ones((), dtype=torch.float64, device=dev)

    cfg = {**vars(a), 'digits': DIGITS, 'thr': THR, 'runs': runs, 'eval_set': ename,
           'n_train_used': len(ytr), 'n_val_used': len(Ey) if a.n_val else 0, 'n_test_used': len(yte),
           'layout': dict(n_in=LAY.n_in, n_hid=LAY.n_hid, n_out=LAY.n_out, rows=LAY.rows, cols=LAY.cols, bias=LAY.bias)}
    (out / 'config.json').write_text(json.dumps(cfg, indent=1))
    fcsv = open(out / 'log.csv', 'w', newline='')
    wr = csv.DictWriter(fcsv, fieldnames=FIELDS); wr.writeheader()
    best = torch.full((B,), -1.0, dtype=torch.float64, device=dev)
    L_best = L.clone()
    t0 = time.time()

    def row(ep, step, j, extra):
        n, s = runs[j]
        return dict(epoch=ep, step=step, run=j, bits=n, seed=s, sec=round(time.time() - t0, 1), **extra)

    def log(ep, step, tr_acc, b_mean, cmax_tr=None):
        nonlocal best, L_best
        acc, st = evaluate(LAY, G_of(L) * ef, EX, Ey, a.a, a.r_on, m, a.v_b, a.r_ser, not a.no_out_clamp)
        up = acc > best
        best = torch.where(up, acc, best)
        L_best[up] = L[up]
        Lm = L[:, m]
        for j in range(B):
            wr.writerow(row(ep, step, j, {
                'train_acc': float(tr_acc[j]) if tr_acc is not None else '', f'{ename}_acc': float(acc[j]),
                'mean_abs_b_V': float(b_mean[j]) if b_mean is not None else '',
                'cell_abs_max_train_V': float(cmax_tr[j]) if cmax_tr is not None else '',
                'frac_min': float((Lm[j] == 0).double().mean()), 'frac_max': float((Lm[j] == lmax[j, 0, 0]).double().mean()),
                **{k: float(v[j]) for k, v in st.items()}}))
        fcsv.flush()
        print(f'ep {ep} step {step} {time.time() - t0:7.1f}s {ename} | ' + ' '.join(
            f'{n}b/s{s} {float(acc[j]):.4f}' for j, (n, s) in enumerate(runs)), flush=True)
        if report is not None:
            report(step, acc.cpu().numpy())
        return acc

    try:
        acc = log(0, 0, None, None)
        ny = len(LAY.r_y)
        prev = None
        step = 0
        for ep in range(1, a.epochs + 1):
            order = np.random.default_rng(1000 + ep).permutation(len(ytr))
            hit = torch.zeros(B, dtype=torch.float64, device=dev)
            b_sum = torch.zeros(B, dtype=torch.float64, device=dev)
            cmax_tr = torch.zeros(B, dtype=torch.float64, device=dev)
            seen = 0
            for idx in order:
                u = torch.as_tensor(row_drive(LAY, Xtr[idx:idx + 1], a.a), device=dev).expand(2 * B, -1)
                inj = torch.zeros(2 * B, ny, dtype=torch.float64, device=dev)
                t = torch.as_tensor(T[idx], device=dev)
                inj[B:, 0::2], inj[B:, 1::2] = a.beta * t, -a.beta * t
                G = G_of(L)
                vh, vy, _ = solve(LAY, torch.cat([G * ef, G * en]), u, i_nudge=inj, r_on=a.r_on, v0=prev, v_b=a.v_b, r_ser=a.r_ser,
                                  out_diode=not a.no_out_clamp)
                prev = (vh, vy)
                d = vy[:B, 0::2] - vy[:B, 1::2]
                if d.abs().max() >= 1:
                    raise RuntimeError(f'|y+ − y−| = {d.abs().max():.3f} V ≥ 1 V → e ≠ t, 한 번에 풀 수 없음')
                hit += (d.argmax(1) == int(ytr[idx])).double()
                V = cell_voltage(LAY, u, vh, vy)
                b = V[B:].abs() - V[:B].abs()
                b_sum += b[:, m].abs().mean(1)
                cmax_tr = torch.maximum(cmax_tr, V[:, conn].abs().view(2, B, -1).amax((0, 2)))
                L = torch.where(mu, torch.minimum((L - torch.where(b >= th, 1.0, -1.0)).clamp(min=0), lmax), L)
                seen += 1; step += 1
                if a.eval_every and step % a.eval_every == 0 and seen < len(order):
                    acc = log(ep, step, hit / seen, b_sum / seen, cmax_tr)
                    cmax_tr.zero_()
            acc = log(ep, step, hit / seen, b_sum / seen, cmax_tr)
        if a.n_val:                                       # val 최고점과 마지막 가중치에서 test 한 번씩
            te, _ = evaluate(LAY, G_of(L_best) * ef, Xte, yte, a.a, a.r_on, m, a.v_b, a.r_ser, not a.no_out_clamp)
            tf, _ = evaluate(LAY, G_of(L) * ef, Xte, yte, a.a, a.r_on, m, a.v_b, a.r_ser, not a.no_out_clamp)
            for j in range(B):
                wr.writerow(row('best', step, j, {'val_acc': float(best[j]), 'test_acc': float(te[j])}))
                wr.writerow(row('final', step, j, {'val_acc': float(acc[j]), 'test_acc': float(tf[j])}))
        else:
            te = best
    finally:
        fcsv.close()
    np.savez(out / 'ckpt.npz', L_final=L.cpu().numpy().astype(np.int16), L_best=L_best.cpu().numpy().astype(np.int16),
             best_eval_acc=best.cpu().numpy(), test_at_best=te.cpu().numpy(), runs=np.array(runs))
    print('best', {f'{n}b/s{s}': (round(float(best[j]), 4), round(float(te[j]), 4)) for j, (n, s) in enumerate(runs)},
          f'({ename}, test)', flush=True)
    return dict(acc_last=acc.cpu().numpy(), best=best.cpu().numpy(), test_at_best=te.cpu().numpy(), runs=runs, out=str(out))


if __name__ == '__main__':
    train(build_parser().parse_args())
