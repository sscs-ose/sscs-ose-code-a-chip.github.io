"""Cycle sampling: glitch-energy estimates with confidence intervals for long testbenches.

Every cycle's starting state is known from the functional (zero-delay) model, so
any subset of cycles can be simulated independently.  Cycles are stratified by
the number of input / state bits that toggle in them (known before simulation and
strongly correlated with energy), a proportional stratified random sample is
simulated, and per-cycle means are estimated with a stratified estimator and a
95 % confidence interval (Student t on the stratified variance; the glitch share,
a ratio, uses the linearised ratio-estimator variance).

    est = analyze_sampled(sim, energy, cycles, initial, n=60, seed=1)
    est["estimate"]["E_glitch_fJ_per_cycle"]  -> (mean, ci_low, ci_high)
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

import numpy as np

from .analyze import analyze


def _toggles(steps, initial):
    prev, out, prevs = dict(initial), [], []
    for st in steps:
        prevs.append(dict(prev))
        n = 0
        for _, u in (st if isinstance(st, list) else [(0, st)]):
            for k, v in u.items():
                n += prev.get(k) != v
                prev[k] = v
        out.append(n)
    return out, prevs


def _t95(df):
    table = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 8: 2.31, 10: 2.23, 15: 2.13,
             20: 2.09, 30: 2.04, 60: 2.00}
    for k in sorted(table):
        if df <= k:
            return table[k]
    return 1.96


def stratified_sample(steps, initial, n, seed=1, strata=4):
    """(sorted sample indices, starting state of every step, {stratum: members},
    {stratum: sampled indices}) for a proportional stratified random sample."""
    N = len(steps)
    tog, prevs = _toggles(steps, initial)
    n = max(2 * strata, min(n, N))
    # strata: quantiles of the toggle count
    qs = np.quantile(tog, np.linspace(0, 1, strata + 1)[1:-1]) if N > strata else []
    stratum = [int(np.searchsorted(qs, t, side="right")) for t in tog]
    members = defaultdict(list)
    for k, s in enumerate(stratum):
        members[s].append(k)
    rnd = random.Random(seed)
    alloc = {s: max(2, round(n * len(m) / N)) for s, m in members.items()}
    sample = {s: sorted(rnd.sample(m, min(alloc[s], len(m)))) for s, m in members.items()}
    idx = sorted(k for ks in sample.values() for k in ks)
    return idx, prevs, dict(members), sample


def estimate(per, members, sample, N):
    """Stratified means with 95 % CI from per-cycle (E_glitch, E_functional) values."""
    est = {}
    W = {s: len(m) / N for s, m in members.items()}

    def strat(idx):
        mean, var = 0.0, 0.0
        for s, ks in sample.items():
            x = np.array([per[k][idx] if idx < 2 else per[k][0] + per[k][1] for k in ks])
            mean += W[s] * x.mean()
            if len(x) > 1:
                fpc = 1 - len(x) / len(members[s])
                var += W[s] ** 2 * x.var(ddof=1) / len(x) * fpc
        return mean, var
    df = max(1, sum(len(k) for k in sample.values()) - len(sample))
    t = _t95(df)
    for name, idx in (("E_glitch_fJ_per_cycle", 0), ("E_functional_fJ_per_cycle", 1), ("E_total_fJ_per_cycle", 2)):
        m, v = strat(idx)
        est[name] = (m, m - t * math.sqrt(v), m + t * math.sqrt(v))
    mg, mt = est["E_glitch_fJ_per_cycle"][0], est["E_total_fJ_per_cycle"][0]
    R = mg / mt if mt else 0.0
    var = 0.0
    for s, ks in sample.items():
        d = np.array([per[k][0] - R * (per[k][0] + per[k][1]) for k in ks])
        if len(d) > 1:
            var += W[s] ** 2 * d.var(ddof=1) / len(d) * (1 - len(d) / len(members[s]))
    se = math.sqrt(var) / mt if mt else 0.0
    est["glitch_fraction"] = (R, R - t * se, R + t * se)
    return est


def analyze_sampled(sim, energy, steps, initial, n, seed=1, strata=4, t0_fs=100_000):
    N = len(steps)
    idx, prevs, members, sample = stratified_sample(steps, initial, n, seed, strata)
    per = {}
    for s, ks in sample.items():
        for k in ks:
            r = analyze(sim, energy, [steps[k]], initial=prevs[k], t0_fs=t0_fs)
            per[k] = (r["totals"]["E_glitch_fJ"], r["totals"]["E_functional_fJ"])
    est = estimate(per, members, sample, N)
    return dict(estimate=est, sampled_cycles=sum(len(k) for k in sample.values()), total_cycles=N,
                strata={int(s): dict(cycles=len(members[s]), sampled=len(sample[s])) for s in members},
                samples=sorted(per))
