#!/usr/bin/env python3
"""Compose layout / stage comparison sheets from the ORFS visual reports."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "results/visuals")


def sheet(items, title, out, ncol=2):
    nrow = (len(items) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.2 * ncol, 6.1 * nrow))
    axes = axes.ravel() if nrow * ncol > 1 else [axes]
    for ax in axes:
        ax.axis("off")
    for ax, (path, label) in zip(axes, items):
        if os.path.exists(path):
            ax.imshow(mpimg.imread(path))
        ax.set_title(label, fontsize=10, pad=6)
    fig.suptitle(title, fontsize=13, y=0.995)
    fig.tight_layout(h_pad=2.2, w_pad=0.8)
    fig.savefig(out, bbox_inches="tight", dpi=110)
    plt.close(fig)
    print("wrote", out)


def main() -> int:
    configs = [
        ("fa_lane_b_top", "FP32 baseline\n30 539 µm² · 3.42 mW"),
        ("fa_lane_e_top", "FP32 ExpMul\n9 362 µm² · 1.02 mW"),
        ("fa_bf16_b_top", "BF16 baseline\n9 041 µm² · 0.931 mW"),
        ("fa_bf16_e_top", "BF16 ExpMul\n5 092 µm² · 0.554 mW"),
    ]
    sheet([(os.path.join(V, d, "base/final_all.webp.png"), lab) for d, lab in configs],
          "fa_lane post-route layout (nangate45, 20 ns): baseline vs ExpMul",
          os.path.join(V, "layout_compare.png"))

    stages = ["final_placement", "final_congestion", "final_ir_drop", "final_routing"]
    names = {"final_placement": "placement", "final_congestion": "congestion",
             "final_ir_drop": "IR drop", "final_routing": "routing"}
    sheet([(os.path.join(V, "fa_lane_b_top/base", f"{s}.webp.png"),
            f"FP32 baseline · {names[s]}") for s in stages],
          "ORFS stage views (FP32 baseline lane)",
          os.path.join(V, "stages_fp32_base.png"))

    sheet([(os.path.join(V, "fa_lane_e_top/base", f"{s}.webp.png"),
            f"FP32 ExpMul · {names[s]}") for s in stages],
          "ORFS stage views (FP32 ExpMul lane)",
          os.path.join(V, "stages_fp32_exp.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
