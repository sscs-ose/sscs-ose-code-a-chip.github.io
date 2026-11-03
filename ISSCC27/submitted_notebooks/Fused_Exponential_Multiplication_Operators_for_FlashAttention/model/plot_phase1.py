#!/usr/bin/env python3
"""Phase-1 figures: ExpMul approximation quality against exact e^x*V."""
from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from expmul_ref import (expmul_mi_fp32, log2exp, to_q6_10, weight_from_L)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.3, "axes.axisbelow": True,
})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/phase1")
    a = ap.parse_args()
    os.makedirs(a.results, exist_ok=True)

    # ---- (1) weight ratio vs x ------------------------------------------
    x = np.linspace(-15.0, 0.0, 40000).astype(np.float32)
    xh = to_q6_10(x)
    Ln = log2exp(xh, "nearest")
    Lc = log2exp(xh, "ceil")
    wn = weight_from_L(Ln).astype(np.float64)
    wc = weight_from_L(Lc).astype(np.float64)
    wm = expmul_mi_fp32(x, np.ones_like(x)).astype(np.float64)
    ex = np.exp(x.astype(np.float64))

    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.2))
    ax[0].semilogy(x, ex, "k-", lw=1.6, label=r"$e^x$ (exact)")
    ax[0].semilogy(x[::10], wm[::10], ".", ms=1.2, color="tab:green",
                   label="ExpMul, mantissa-interp")
    ax[0].semilogy(x[::10], wn[::10], ".", ms=1.2, color="tab:blue",
                   label="ExpMul, exponent-only (Alg.3)")
    ax[0].set_xlabel("x  (score difference, $x\\leq 0$)")
    ax[0].set_ylabel(r"$e^x$ / weight")
    ax[0].set_title("weight value")
    ax[0].legend(fontsize=7.5, loc="lower right")

    ax[1].plot(x, wn / ex, lw=1.2, color="tab:blue", label="exponent-only")
    ax[1].plot(x, wc / ex, lw=1.0, color="tab:orange", alpha=0.8, label="exponent-only (ceil)")
    ax[1].plot(x, wm / ex, lw=1.4, color="tab:green", label="mantissa-interp")
    ax[1].axhline(1.0, color="k", lw=0.8, ls="--")
    ax[1].set_ylim(0.0, 2.0)
    ax[1].set_xlabel("x")
    ax[1].set_ylabel("weight / $e^x$")
    ax[1].set_title("relative weight error")
    ax[1].legend(fontsize=7.5, loc="lower left")
    fig.suptitle("ExpMul: logarithmic quantisation of $e^x$  (x clipped to [-15,0])", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(a.results, "phase1_weight_ratio.png"), bbox_inches="tight")
    plt.close(fig)

    # ---- (2) error histogram from the dumped pairs ----------------------
    import csv
    rel = {"exponent-only": [], "mantissa-interp": []}
    with open(os.path.join(a.results, "expmul_pairs.csv"), newline="") as f:
        for row in csv.DictReader(f):
            rel["exponent-only"].append(abs(float(row["rel_nearest"])))
            rel["mantissa-interp"].append(abs(float(row["rel_mi"])))
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.0))
    bins = np.linspace(0, 0.5, 101)
    ax[0].hist(rel["exponent-only"], bins=bins, color="tab:blue", alpha=0.8,
               label="exponent-only (Alg.3)")
    ax[0].hist(rel["mantissa-interp"], bins=bins, color="tab:green", alpha=0.7,
               label="mantissa-interp")
    ax[0].set_yscale("log")
    ax[0].set_xlabel("|relative error|  of  $e^x V$")
    ax[0].set_ylabel("count (log)")
    ax[0].legend(fontsize=8)
    ax[1].hist(rel["mantissa-interp"], bins=np.linspace(0, 0.15, 151),
               color="tab:green", alpha=0.85)
    ax[1].set_xlabel("|relative error|  (mantissa-interp zoom)")
    ax[1].set_ylabel("count (log)")
    ax[1].set_yscale("log")
    fig.suptitle("ExpMul error distribution, 2M random (x,V) pairs, seed 20250520", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(a.results, "phase1_error_hist.png"), bbox_inches="tight")
    plt.close(fig)

    # ---- (3) error vs x, one lane ---------------------------------------
    rng = np.random.default_rng(7)
    xs = rng.uniform(-15, 0, 20000).astype(np.float32)
    v = np.float32(1.0)
    yn = expmul_mi_fp32(xs, np.full_like(xs, v))       # MI
    y0 = np.ldexp(np.ones_like(xs), -log2exp(to_q6_10(xs), "nearest"))  # exponent-only
    ref = np.exp(xs.astype(np.float64))
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.plot(xs, y0 / ref - 1, ".", ms=1.5, alpha=0.35, color="tab:blue",
            label="exponent-only")
    ax.plot(xs, yn / ref - 1, ".", ms=1.5, alpha=0.55, color="tab:green",
            label="mantissa-interp")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylim(-0.55, 0.55)
    ax.set_xlabel("x")
    ax.set_ylabel("relative error")
    ax.set_title("ExpMul relative error vs x (V = 1)")
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(a.results, "phase1_error_vs_x.png"), bbox_inches="tight")
    plt.close(fig)

    # ---- (4) spot table --------------------------------------------------
    print("\n  x        e^x         Alg.3       ratio    mantissa    ratio")
    for xv in (0.0, -0.25, -0.5, -1.0, -2.0, -5.0, -10.0, -15.0):
        xx = np.array([xv], dtype=np.float32)
        e = float(np.exp(xv))
        y0 = float(np.ldexp(1.0, -int(log2exp(to_q6_10(xx), "nearest")[0])))
        ym = float(expmul_mi_fp32(xx, np.array([1.0], np.float32))[0])
        print(f"{xv:7.2f}  {e:10.4e}  {y0:10.4e}  {y0/e:7.4f}  {ym:10.4e}  {ym/e:7.4f}")
    print("\nfigures ->", a.results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
