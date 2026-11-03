#!/usr/bin/env python3
"""Phase-2 figures: baseline vs ExpMul accuracy in the FlashAttention-2 kernel."""
from __future__ import annotations

import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.3, "axes.axisbelow": True,
})

VARIANT_STYLE = {
    "baseline":     ("baseline (PWL exp + FP mul)", "tab:gray",   "o"),
    "expmul_exp":   ("ExpMul, exponent-only (Alg.3)", "tab:blue", "s"),
    "expmul_mi":    ("ExpMul, mantissa-interp", "tab:green", "D"),
}


def load_matrix(path):
    rows = list(csv.DictReader(open(path, newline="")))
    return {(int(r["d"]), r["dtype"], int(r["N"]), float(r["temp"]), r["variant"]):
            float(r["rel_l2_mean"]) for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/phase2")
    a = ap.parse_args()
    M = load_matrix(os.path.join(a.results, "errors_matrix.csv"))

    # ---- (1) error vs N, d = 64, T = 1 ----------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(9.4, 3.2), sharey=True)
    for k, dt in enumerate(("fp32", "bf16")):
        Ns = [16, 64, 128, 512]
        for var, (lab, col, mk) in VARIANT_STYLE.items():
            ys = [M[(64, dt, n, 1.0, var)] for n in Ns]
            ax[k].plot(Ns, ys, marker=mk, ms=4, lw=1.4, color=col, label=lab)
        ax[k].set_xscale("log", base=2)
        ax[k].set_yscale("log")
        ax[k].set_xticks(Ns)
        ax[k].set_xticklabels(Ns)
        ax[k].set_xlabel("sequence length N")
        ax[k].set_title(f"d = 64, {dt.upper()}")
        if k == 0:
            ax[k].set_ylabel(r"per-query $\|o-\mathrm{ref}\|_2/\|\mathrm{ref}\|_2$")
    ax[0].legend(fontsize=7.5, loc="lower right")
    fig.suptitle("FlashAttention-2 kernel: ExpMul vs baseline (double-precision reference)", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(a.results, "phase2_error_vs_N.png"), bbox_inches="tight")
    plt.close(fig)

    # ---- (2) per-query error histogram ----------------------------------
    rows = list(csv.DictReader(open(os.path.join(a.results, "detail_d64_N512_fp32.csv"),
                                   newline="")))
    fig, ax = plt.subplots(1, 2, figsize=(9.4, 3.0))
    for var, (lab, col, _) in VARIANT_STYLE.items():
        ys = np.array([float(r[f"rel_l2_{var}"]) for r in rows])
        ax[0].hist(ys, bins=np.linspace(0, 0.30, 61), histtype="step", lw=1.6,
                   color=col, label=lab)
        ax[1].hist(ys[ys > 1e-4], bins=np.logspace(-4, -0.5, 50), histtype="step",
                   lw=1.6, color=col, label=lab)
    ax[0].set_xlabel("per-query relative L2 error")
    ax[0].set_ylabel("queries")
    ax[0].set_title("d=64, N=512, FP32, temperature 1")
    ax[0].legend(fontsize=7.5)
    ax[1].set_xscale("log")
    ax[1].set_xlabel("per-query relative L2 error (log)")
    ax[1].set_ylabel("queries")
    ax[1].set_title("same, log-scale")
    fig.tight_layout()
    fig.savefig(os.path.join(a.results, "phase2_error_hist.png"), bbox_inches="tight")
    plt.close(fig)

    # ---- (3) numerical stability ----------------------------------------
    rows = list(csv.DictReader(open(os.path.join(a.results, "stability.csv"), newline="")))
    cases = [r for r in rows if r["dtype"] == "fp32"]
    labels = ["random", "temp4", "huge_1e3", "huge_1e6", "uniform", "single_key",
              "dominant", "v_large", "v_tiny"]
    fp32 = cases
    fig, ax = plt.subplots(figsize=(8.0, 3.0))
    x = np.arange(len(fp32))
    w = 0.26
    for i, var in enumerate(("base", "exp", "mi")):
        ys = [max(float(r[f"rel_l2_{var}"]), 1e-12) for r in fp32]
        ax.bar(x + (i - 1) * w, ys, w, label={"base": "baseline", "exp": "ExpMul Alg.3",
                                              "mi": "ExpMul MI"}[var])
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5, rotation=20)
    ax.set_ylabel("relative L2 error")
    ax.set_title("numerical stability cases (FP32, d=64, N=64 unless noted)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(a.results, "phase2_stability.png"), bbox_inches="tight")
    plt.close(fig)

    print("figures ->", a.results)
    print("\n d=64 FP32 T=1:")
    for var, (lab, _, _) in VARIANT_STYLE.items():
        print(f"   {lab:32s} " + "  ".join(f"N={n}: {M[(64,'fp32',n,1.0,var)]*100:5.2f}%"
                                           for n in (16, 64, 128, 512)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
