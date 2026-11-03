"""Fixed-vs-random TVLA on simulated NTT leakage traces.

Step 1 (`gen`): write leak_in.hex -- a random interleaving of one fixed
polynomial and fresh random polynomials, plus the class labels.
Step 2 (`analyze`): read leak_traces.txt produced by tb_ntt_leak.sv, add
Gaussian measurement noise (model assumption), and compute Welch's t per
clock cycle. |t| > 4.5 is the usual TVLA threshold for detectable leakage.

The traces are a Hamming-distance *model* from RTL simulation, not measured
power; they show where data-dependent switching exists, not how many real
traces an attacker would need.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random

import numpy as np

import mlkem_ref as ref


def gen(out: pathlib.Path, n: int, seed: int, masked: bool = False) -> None:
    """Write the inputs for n traces. With masked=True each secret a is split
    into two arithmetic shares (a - m, m) with a fresh uniform mask m; the
    engine transforms both, and NTT(a) = NTT(a - m) + NTT(m) by linearity."""
    rng = random.Random(seed)
    fixed = [rng.randrange(ref.Q) for _ in range(256)]
    labels = [rng.randrange(2) for _ in range(n)]  # 0 = fixed, 1 = random
    runs = 0
    with open(out / "leak_in.hex", "w") as f:
        for lab in labels:
            poly = fixed if lab == 0 else [rng.randrange(ref.Q) for _ in range(256)]
            if masked:
                mask = [rng.randrange(ref.Q) for _ in range(256)]
                share = [(x - y) % ref.Q for x, y in zip(poly, mask)]
                assert [(x + y) % ref.Q for x, y in zip(ref.ntt(share), ref.ntt(mask))] == ref.ntt(poly)
                for p in (share, mask):
                    f.writelines(f"{c:04x}\n" for c in p)
                runs += 2
            else:
                f.writelines(f"{c:04x}\n" for c in poly)
                runs += 1
    (out / "leak_labels.json").write_text(json.dumps({"labels": labels, "runs_per_trace": 2 if masked else 1}))
    (out / "leak_counts.vh").write_text(f"`define N_LEAK {runs}\n")


def welch_t(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    va, vb = a.var(axis=0, ddof=1), b.var(axis=0, ddof=1)
    den = np.sqrt(va / len(a) + vb / len(b))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (a.mean(axis=0) - b.mean(axis=0)) / den
    return np.nan_to_num(t)


def analyze(out: pathlib.Path, sigma: float, seed: int) -> dict:
    meta = json.loads((out / "leak_labels.json").read_text())
    if isinstance(meta, list):          # files written before masking support
        meta = {"labels": meta, "runs_per_trace": 1}
    labels = np.array(meta["labels"]); k = meta["runs_per_trace"]
    runs = [[int(x) for x in ln.split()]
            for ln in (out / "leak_traces.txt").read_text().splitlines() if ln.strip()]
    # one trace = the k consecutive NTT runs that process one secret
    traces = np.array([sum(runs[i:i + k], []) for i in range(0, len(runs), k)], dtype=float)
    assert traces.shape[0] == len(labels), "trace/label count mismatch"
    noisy = traces + np.random.default_rng(seed).normal(0.0, sigma, traces.shape)
    t = welch_t(noisy[labels == 0], noisy[labels == 1])
    np.save(out / "tvla_t.npy", t)
    np.save(out / "mean_trace.npy", traces.mean(axis=0))
    leaky = np.abs(t) > 4.5
    # Negative control: split the random class in two halves. Both halves come
    # from the same distribution, so |t| should stay below the threshold; if
    # it does not, the test setup (not the design) is producing the "leakage".
    rnd = noisy[labels == 1]
    perm = np.random.default_rng(seed + 1).permutation(len(rnd))
    t_ctrl = welch_t(rnd[perm[: len(rnd) // 2]], rnd[perm[len(rnd) // 2:]])
    np.save(out / "tvla_t_control.npy", t_ctrl)
    res = {
        "runs_per_trace": k,
        "control_max_abs_t": float(np.abs(t_ctrl).max()),
        "control_cycles_over_4p5": int((np.abs(t_ctrl) > 4.5).sum()),
        "traces": int(traces.shape[0]), "fixed": int((labels == 0).sum()),
        "cycles": int(traces.shape[1]), "noise_sigma_hd": sigma,
        "max_abs_t": float(np.abs(t).max()),
        "cycles_over_4p5": int(leaky.sum()),
        "fraction_over_4p5": float(leaky.mean()),
        "first_leaky_cycle": int(np.argmax(leaky)) if leaky.any() else None,
    }
    (out / "tvla_summary.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["gen", "analyze"])
    ap.add_argument("--out", default="../results/leakage")
    ap.add_argument("-n", type=int, default=400)
    ap.add_argument("--sigma", type=float, default=4.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--masked", action="store_true", help="first-order arithmetic masking")
    a = ap.parse_args()
    o = pathlib.Path(a.out); o.mkdir(parents=True, exist_ok=True)
    if a.step == "gen":
        gen(o, a.n, a.seed, a.masked)
    else:
        print(analyze(o, a.sigma, a.seed))
