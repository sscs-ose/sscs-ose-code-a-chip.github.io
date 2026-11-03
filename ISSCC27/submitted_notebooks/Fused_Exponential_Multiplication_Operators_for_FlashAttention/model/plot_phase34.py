#!/usr/bin/env python3
"""Phase 3/4 figures: GLUE accuracy and hardware area/power."""
from __future__ import annotations

import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.3, "axes.axisbelow": True,
})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def plot_area():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "results/phase4/area_model.csv"))))
    ds = sorted({int(r["d"]) for r in rows})
    base = [float(next(r["total"] for r in rows if int(r["d"]) == d and r["variant"] == "baseline")) for d in ds]
    exp = [float(next(r["total"] for r in rows if int(r["d"]) == d and r["variant"] == "expmul")) for d in ds]
    sav = [100 * (1 - e / b) for b, e in zip(base, exp)]

    fig, ax = plt.subplots(1, 2, figsize=(9.4, 3.2))
    x = np.arange(len(ds))
    w = 0.36
    ax[0].bar(x - w / 2, np.array(base) / 1e3, w, label="baseline (PWL exp + FP mul)", color="tab:gray")
    ax[0].bar(x + w / 2, np.array(exp) / 1e3, w, label="ExpMul", color="tab:green")
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(ds)
    ax[0].set_xlabel("hidden dimension d")
    ax[0].set_ylabel("block area (10$^3$ µm$^2$, 45 nm)")
    ax[0].set_title("synthesized block area")
    ax[0].legend(fontsize=7.5)
    for i, s in enumerate(sav):
        ax[0].text(x[i], max(base[i], exp[i]) / 1e3 * 1.02, f"-{s:.1f}%",
                   ha="center", fontsize=7.5, color="tab:green")

    # paper numbers (FP32, Fig.3)
    paper = {16: 23.6, 64: 29.7, 256: 33.1}
    ax[1].plot(ds, sav, "o-", color="tab:green", label="this work (45 nm)")
    px = [d for d in ds if d in paper]
    ax[1].plot(px, [paper[d] for d in px], "s--", color="tab:blue", label="paper Fig.3 (28 nm)")
    ax[1].axhline(28.8, color="k", ls=":", lw=1, label="paper average 28.8%")
    ax[1].set_xscale("log", base=2)
    ax[1].set_xticks(ds)
    ax[1].set_xticklabels(ds)
    ax[1].set_xlabel("hidden dimension d")
    ax[1].set_ylabel("area saving (%)")
    ax[1].set_ylim(0, 45)
    ax[1].legend(fontsize=7.5)
    ax[1].set_title("area reduction vs paper")
    fig.suptitle("ExpMul area: RTL synthesis (Yosys+ABC, nangate45) vs the paper", y=1.02)
    fig.tight_layout()
    out = os.path.join(ROOT, "results/phase4/phase4_area.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


def plot_units():
    units = [("FP32 mul", 4069.5), ("FP32 add", 1519.7), ("PWL exp", 4320.9),
             ("rcp PWL", 1668.4), ("ExpMul", 699.6)]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    names = [u[0] for u in units]
    vals = [u[1] for u in units]
    colors = ["tab:gray", "tab:gray", "tab:orange", "tab:gray", "tab:green"]
    bars = ax.bar(names, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.01, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_ylabel("area (µm², 45 nm)")
    ax.set_title("datapath primitives (same library, same flow)")
    fig.tight_layout()
    out = os.path.join(ROOT, "results/phase4/phase4_units.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


def plot_power():
    path = os.path.join(ROOT, "results/phase4/lane_pnr.json")
    if not os.path.exists(path):
        print("no lane_pnr.json yet, skip power figure")
        return
    d = json.load(open(path))
    dts = [k for k in ("fp32", "bf16") if k in d]
    fig, ax = plt.subplots(1, 2, figsize=(9.0, 3.2))
    x = np.arange(len(dts))
    w = 0.34
    area_b = [d[t]["base"]["area_um2"] / 1000 for t in dts]
    area_e = [d[t]["exp"]["area_um2"] / 1000 for t in dts]
    pow_b = [d[t]["base"]["power_mw"] for t in dts]
    pow_e = [d[t]["exp"]["power_mw"] for t in dts]
    ax[0].bar(x - w / 2, area_b, w, label="baseline", color="tab:gray")
    ax[0].bar(x + w / 2, area_e, w, label="ExpMul", color="tab:green")
    ax[0].set_xticks(x); ax[0].set_xticklabels([t.upper() for t in dts])
    ax[0].set_ylabel("post-route area (10$^3$ µm$^2$)")
    ax[0].set_title("lane area (nangate45)")
    for i, t in enumerate(dts):
        ax[0].text(x[i], max(area_b[i], area_e[i]) * 1.02,
                   f"-{d[t]['area_saving_pct']:.1f}%", ha="center", fontsize=8,
                   color="tab:green")
    ax[1].bar(x - w / 2, pow_b, w, label="baseline", color="tab:gray")
    ax[1].bar(x + w / 2, pow_e, w, label="ExpMul", color="tab:green")
    ax[1].set_xticks(x); ax[1].set_xticklabels([t.upper() for t in dts])
    ax[1].set_ylabel("power at 50 MHz (mW)")
    ax[1].set_title("post-route power with VCD activity")
    for i, t in enumerate(dts):
        ax[1].text(x[i], max(pow_b[i], pow_e[i]) * 1.02,
                   f"-{d[t]['power_saving_pct']:.1f}%", ha="center", fontsize=8,
                   color="tab:green")
    ax[0].legend(fontsize=8); ax[1].legend(fontsize=8)
    fig.suptitle("fa_lane (D=1 sigma* update): baseline vs ExpMul, FP32 and BF16", y=1.02)
    fig.tight_layout()
    out = os.path.join(ROOT, "results/phase4/phase4_power.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


def plot_glue():
    path = os.path.join(ROOT, "results/phase3/glue_results.csv")
    if not os.path.exists(path):
        print("no glue_results.csv yet, skip GLUE figure")
        return
    rows = list(csv.DictReader(open(path)))
    tasks = []
    for r in rows:
        if r["task"] not in tasks:
            tasks.append(r["task"])
    variants = []
    for r in rows:
        if r["variant"] not in variants:
            variants.append(r["variant"])
    metric = "accuracy" if "accuracy" in rows[0] else "pearson"
    acc = {(r["task"], r["variant"]): float(r.get(metric) or 0) for r in rows}

    fig, ax = plt.subplots(figsize=(10.0, 3.4))
    x = np.arange(len(tasks))
    w = 0.8 / max(len(variants), 1)
    colors = {"fp32": "tab:gray", "fp32_exp": "tab:blue", "fp32_mi": "tab:green",
              "bf16": "tab:orange", "bf16_mi": "tab:red"}
    for i, v in enumerate(variants):
        ys = [acc.get((t, v), np.nan) for t in tasks]
        ax.bar(x + (i - (len(variants) - 1) / 2) * w, ys, w, label=v,
               color=colors.get(v, None))
    ax.set_xticks(x)
    ax.set_xticklabels(tasks, rotation=20, fontsize=8)
    ax.set_ylabel(metric)
    ax.set_title("GLUE / Flan-T5 (100 examples per task)")
    ax.legend(fontsize=7.5, ncol=len(variants))
    fig.tight_layout()
    out = os.path.join(ROOT, "results/phase3/phase3_glue.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    plot_units()
    plot_area()
    plot_power()
    plot_glue()
