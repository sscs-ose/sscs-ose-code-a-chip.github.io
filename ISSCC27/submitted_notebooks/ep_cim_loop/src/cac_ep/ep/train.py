"""Training loop: data split, one epoch of online EP, evaluation, logging, fit.

Same results as sim/ep_dr/train.py `train()` (same random streams, same update, same log.csv / ckpt.npz).
"""
import csv
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from data import DIGITS, THR, load_task
from solver import branch_iv, cell_iv, cell_voltage, diode_iv

FIELDS = ['epoch', 'step', 'run', 'bits', 'seed', 'train_acc', 'val_acc', 'test_acc', 'mean_abs_b_V', 'frac_min',
          'frac_max', 'vh_abs_mean', 'vh_frac_over_0p24', 'vy_abs_mean', 'cell_abs_max_V', 'cell_abs_max_train_V',
          'vh_frac_clamp', 'vy_frac_clamp', 'p_neuron_uW', 'p_xbar_uW', 'sec']
# cell_abs_max_V: 평가 (free) 의 학습 셀 최대 |V|. cell_abs_max_train_V: 직전 평가 뒤 학습 표본들의 free·nudge 두 단계,
# 연결된 모든 셀 (G_bz·HRS 포함) 최대 |V| — 읽기 교란 한도 0.6 V 확인용.
# *_frac_clamp: 다이오드 dI/dV ≥ 그 노드에 붙은 셀 dI/dV 합인 노드 비율 (노드의 입력 → 전압 기울기 ≤ 0.5, clamp 가 거는 구간).
# p_neuron_uW: free 표본당 다이오드 가지 (R_ser 포함) 전력 합, p_xbar_uW: free 표본당 연결 셀 (R_on 포함) 전력 합.


def prepare_data(cfg, n_out=3):
    """MNIST digits 0/1/4 at 7x7, binarized to +-1. Splits: val = n_val images taken out of the training set (rng 2),
    then n_train of the rest (rng 0), n_test of t10k (rng 1). Evaluation during training uses val if n_val else test.
    Returns a namespace with Xtr, ytr, T (targets +-1, (n, n_out)), Xva, yva, Xte, yte, EX, Ey, ename."""
    Xtr, ytr = load_task('train')
    Xte, yte = load_task('t10k')
    Xva = yva = None
    if cfg.n_val:
        p = np.random.default_rng(2).permutation(len(ytr))
        Xva, yva, Xtr, ytr = Xtr[p[:cfg.n_val]], ytr[p[:cfg.n_val]], Xtr[p[cfg.n_val:]], ytr[p[cfg.n_val:]]
    if cfg.n_train:
        i = np.random.default_rng(0).choice(len(ytr), cfg.n_train, replace=False); Xtr, ytr = Xtr[i], ytr[i]
    if cfg.n_test:
        i = np.random.default_rng(1).choice(len(yte), cfg.n_test, replace=False); Xte, yte = Xte[i], yte[i]
    EX, Ey, ename = (Xva, yva, 'val') if cfg.n_val else (Xte, yte, 'test')
    T = np.where(np.eye(n_out)[ytr] > 0, 1.0, -1.0)
    return SimpleNamespace(Xtr=Xtr, ytr=ytr, T=T, Xva=Xva, yva=yva, Xte=Xte, yte=yte, EX=EX, Ey=Ey, ename=ename)


@torch.no_grad()
def evaluate(net, X, y, L=None):
    """Accuracy (n_runs,) of the free circuit on X, y, and node / cell statistics per run (dict of (n_runs,) tensors).
    L: levels to evaluate (default net.L)."""
    lay, c, m = net.lay, net.cfg, net.m
    B, dev = net.n_runs, net.dev
    chunk = max(1, 1024 // B)
    hit = torch.zeros(B, device=dev, dtype=torch.float64)
    vh_abs, vh_on, vy_abs, cmax, hcl, ycl, pn, px = (torch.zeros(B, device=dev, dtype=torch.float64) for _ in range(8))
    yt = torch.as_tensor(y, device=dev)
    c_h, r_y = torch.as_tensor(lay.c_h, device=dev), torch.as_tensor(lay.r_y, device=dev)
    for i0 in range(0, len(X), chunk):
        n = min(chunk, len(X) - i0)
        u, Gn, vh, vy = net.solve_free(X[i0:i0 + n], L)
        d = (vy[:, 0::2] - vy[:, 1::2]).view(B, n, -1)
        hit += (d.argmax(-1) == yt[i0:i0 + n]).sum(1)
        vh_abs += vh.abs().view(B, -1).mean(1) * n
        vh_on += (vh.abs() > 0.24).double().view(B, -1).mean(1) * n
        vy_abs += vy.abs().view(B, -1).mean(1) * n
        Vc = cell_voltage(lay, u, vh, vy)
        cmax = torch.maximum(cmax, Vc[:, m].abs().view(B, -1).max(1).values)
        I, g = cell_iv(Gn, Vc, c.r_on)
        hcl += (diode_iv(vh, c.v_b, c.r_ser)[1] >= g[:, :, c_h].sum(1)).double().view(B, -1).mean(1) * n
        if c.out_clamp:
            ycl += (diode_iv(vy, c.v_b, c.r_ser)[1] >= g[:, r_y, :].sum(2)).double().view(B, -1).mean(1) * n
        vn = torch.cat([vh, vy], 1) if c.out_clamp else vh
        p = branch_iv(vn + c.v_b, c.r_ser)[0] * (vn + c.v_b) + branch_iv(c.v_b - vn, c.r_ser)[0] * (c.v_b - vn)
        pn += p.sum(1).view(B, n).sum(1)
        px += (I * Vc)[:, net.conn].sum(1).view(B, n).sum(1)
    N = len(X)
    return hit / N, dict(vh_abs_mean=vh_abs / N, vh_frac_over_0p24=vh_on / N, vy_abs_mean=vy_abs / N, cell_abs_max_V=cmax,
                         vh_frac_clamp=hcl / N, vy_frac_clamp=ycl / N, p_neuron_uW=pn / N * 1e6, p_xbar_uW=px / N * 1e6)


class RunLog:
    """Writes log.csv, keeps the best evaluation accuracy per run and its levels (L_best), prints one line per evaluation.
    report(step, acc) is called after each evaluation (e.g. Optuna pruning)."""

    def __init__(self, out, net, data, report=None):
        self.net, self.data, self.report = net, data, report
        self.f = open(Path(out) / 'log.csv', 'w', newline='')
        self.wr = csv.DictWriter(self.f, fieldnames=FIELDS); self.wr.writeheader()
        self.best = torch.full((net.n_runs,), -1.0, dtype=torch.float64, device=net.dev)
        self.L_best = net.L.clone()
        self.t0 = time.time()

    def row(self, ep, step, j, extra):
        n, s = self.net.runs[j]
        return dict(epoch=ep, step=step, run=j, bits=n, seed=s, sec=round(time.time() - self.t0, 1), **extra)

    def __call__(self, ep, step, tr_acc=None, b_mean=None, cmax_tr=None):
        """Evaluate on the eval set (val or test), log one row per run, update best. Returns acc (n_runs,)."""
        net, ename = self.net, self.data.ename
        acc, st = evaluate(net, self.data.EX, self.data.Ey)
        up = acc > self.best
        self.best = torch.where(up, acc, self.best)
        self.L_best[up] = net.L[up]
        Lm = net.L[:, net.m]
        for j in range(net.n_runs):
            self.wr.writerow(self.row(ep, step, j, {
                'train_acc': float(tr_acc[j]) if tr_acc is not None else '', f'{ename}_acc': float(acc[j]),
                'mean_abs_b_V': float(b_mean[j]) if b_mean is not None else '',
                'cell_abs_max_train_V': float(cmax_tr[j]) if cmax_tr is not None else '',
                'frac_min': float((Lm[j] == 0).double().mean()), 'frac_max': float((Lm[j] == net.lmax[j, 0, 0]).double().mean()),
                **{k: float(v[j]) for k, v in st.items()}}))
        self.f.flush()
        print(f'ep {ep} step {step} {time.time() - self.t0:7.1f}s {ename} | ' + ' '.join(
            f'{n}b/s{s} {float(acc[j]):.4f}' for j, (n, s) in enumerate(net.runs)), flush=True)
        if self.report is not None:
            self.report(step, acc.cpu().numpy())
        return acc

    def close(self):
        self.f.close()


def train_epoch(net, data, ep, step, log):
    """One epoch of online EP: shuffle (rng 1000 + ep), then per image equilibrium (free + nudge) -> update.
    Evaluates every cfg.eval_every images (if > 0) and at the end of the epoch. Returns (step, acc of the last evaluation)."""
    B, dev, every, stop = net.n_runs, net.dev, net.cfg.eval_every, net.cfg.stop_step
    order = np.random.default_rng(1000 + ep).permutation(len(data.ytr))
    hit = torch.zeros(B, dtype=torch.float64, device=dev)
    b_sum = torch.zeros(B, dtype=torch.float64, device=dev)
    cmax_tr = torch.zeros(B, dtype=torch.float64, device=dev)
    seen = 0
    for idx in order:
        eq = net.equilibrium(data.Xtr[idx:idx + 1], data.T[idx])
        hit += (eq['d'].argmax(1) == int(data.ytr[idx])).double()
        b_sum += eq['b'][:, net.m].abs().mean(1)
        cmax_tr = torch.maximum(cmax_tr, eq['V'][:, net.conn].abs().view(2, B, -1).amax((0, 2)))
        net.update(eq)
        seen += 1; step += 1
        if stop:                                      # fixed length: no evaluation on the way
            if step >= stop:
                break
            continue
        if every and step % every == 0 and seen < len(order):
            log(ep, step, hit / seen, b_sum / seen, cmax_tr)
            cmax_tr.zero_()
    if stop:
        return step, None
    return step, log(ep, step, hit / seen, b_sum / seen, cmax_tr)


def fit(net, cfg=None, report=None, out_dir=None):
    """Train net for cfg.epochs (cfg defaults to net.cfg), then measure test accuracy at the best-val and the final levels.

    out_dir: run folder (default ./out/runs/<cfg.tag>). Writes config.json, log.csv and ckpt.npz
    (L_final, L_best as int16, best_eval_acc, test_at_best, runs).
    Returns dict(acc_last, best, test_at_best, runs, out) like sim/ep_dr/train.py train().
    """
    cfg = cfg or net.cfg
    out = Path(out_dir) if out_dir is not None else Path('out') / 'runs' / cfg.tag
    out.mkdir(parents=True, exist_ok=True)
    data = prepare_data(cfg, len(net.lay.r_y) // 2)
    lay = net.lay
    info = {**cfg.to_dict(), 'no_out_clamp': not cfg.out_clamp, 'digits': DIGITS, 'thr': THR, 'runs': net.runs,
            'eval_set': data.ename, 'n_train_used': len(data.ytr), 'n_val_used': len(data.Ey) if cfg.n_val else 0,
            'n_test_used': len(data.yte),
            'layout': dict(n_in=lay.n_in, n_hid=lay.n_hid, n_out=lay.n_out, rows=lay.rows, cols=lay.cols, bias=lay.bias)}
    (out / 'config.json').write_text(json.dumps(info, indent=1))
    if cfg.stop_step:                                 # train a fixed number of images, then measure once
        return _fit_fixed(net, cfg, data, out)
    log = RunLog(out, net, data, report)
    try:
        acc = log(0, 0)
        step = 0
        for ep in range(1, cfg.epochs + 1):
            step, acc = train_epoch(net, data, ep, step, log)
        if cfg.n_val:                                     # val 최고점과 마지막 가중치에서 test 한 번씩
            te, _ = evaluate(net, data.Xte, data.yte, L=log.L_best)
            tf, _ = evaluate(net, data.Xte, data.yte)
            for j in range(net.n_runs):
                log.wr.writerow(log.row('best', step, j, {'val_acc': float(log.best[j]), 'test_acc': float(te[j])}))
                log.wr.writerow(log.row('final', step, j, {'val_acc': float(acc[j]), 'test_acc': float(tf[j])}))
        else:
            te = log.best
    finally:
        log.close()
    best, runs = log.best, net.runs
    np.savez(out / 'ckpt.npz', L_final=net.L.cpu().numpy().astype(np.int16), L_best=log.L_best.cpu().numpy().astype(np.int16),
             best_eval_acc=best.cpu().numpy(), test_at_best=te.cpu().numpy(), runs=np.array(runs))
    print('best', {f'{n}b/s{s}': (round(float(best[j]), 4), round(float(te[j]), 4)) for j, (n, s) in enumerate(runs)},
          f'({data.ename}, test)', flush=True)
    return dict(acc_last=acc.cpu().numpy(), best=best.cpu().numpy(), test_at_best=te.cpu().numpy(), runs=runs, out=str(out))


def _fit_fixed(net, cfg, data, out):
    """cfg.stop_step images of online EP (same image order as fit), then one validation and one test measurement.
    The weights at that step are saved as L_final (= L_best) in ckpt.npz; log.csv gets one row per run."""
    t0, step, ep = time.time(), 0, 0
    while step < cfg.stop_step:
        ep += 1
        step, _ = train_epoch(net, data, ep, step, None)
        print(f'ep {ep} step {step} {time.time() - t0:7.1f}s', flush=True)
    va, _ = evaluate(net, data.EX, data.Ey)
    te, st = evaluate(net, data.Xte, data.yte)
    L = net.L.cpu().numpy().astype(np.int16)
    with open(out / 'log.csv', 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=['epoch', 'step', 'run', 'bits', 'seed', 'val_acc', 'test_acc', 'sec'])
        wr.writeheader()
        for j, (n, s) in enumerate(net.runs):
            wr.writerow(dict(epoch=ep, step=step, run=j, bits=n, seed=s, val_acc=float(va[j]), test_acc=float(te[j]),
                             sec=round(time.time() - t0, 1)))
    np.savez(out / 'ckpt.npz', L_final=L, L_best=L, best_eval_acc=va.cpu().numpy(), test_at_best=te.cpu().numpy(),
             runs=np.array(net.runs))
    print('stop', step, {f'{n}b/s{s}': (round(float(va[j]), 4), round(float(te[j]), 4)) for j, (n, s) in enumerate(net.runs)},
          '(val, test)', flush=True)
    return dict(acc_last=va.cpu().numpy(), best=va.cpu().numpy(), test_at_best=te.cpu().numpy(), runs=net.runs, out=str(out))
