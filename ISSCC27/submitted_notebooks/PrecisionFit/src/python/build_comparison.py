"""
Assemble the three-way comparison the brief asks for:
  1. Conservative uniform-precision (baseline)
  2. Best uniform-precision meeting requirements (strong baseline)
  3. Sensitivity-guided (proposed method)

All measured with identical architecture, throughput and timing constraints.
Writes results/pareto/three_way_comparison.csv, results/pareto/pareto_frontier.png
and results/pareto/headline_configs.json (so the stress test / notebook can
rebuild exactly the same three designs).
"""
import json
import sys

import matplotlib
# Only force a headless backend in scripts; inside a notebook that would
# silently disable inline figure display for every cell that runs afterwards.
if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import paths
from reference import FILTER_A_SPEC, design_filter
from search import make_cfg
from rtlgen import generate_rtl, generate_rtl_nonuniform

UNIFORM_CSV = paths.SWEEPS_DIR / "uniform_sweep_synth.csv"
SENS_CSV = paths.SWEEPS_DIR / "sensitivity_sweep_synth.csv"
COMPARISON_CSV = paths.PARETO_DIR / "three_way_comparison.csv"
PLOT_PATH = paths.PARETO_DIR / "pareto_frontier.png"
HEADLINE_JSON = paths.PARETO_DIR / "headline_configs.json"


def select_conservative_uniform(uniform_synth_df: pd.DataFrame) -> pd.Series:
    """
    Select the "conservative uniform" design from a synthesized uniform-sweep
    DataFrame.

    Criterion: the config whose ``min(coeff_bits, input_bits)`` is highest —
    this picks a *balanced* wide design rather than an imbalanced grid point
    that happens to have many cells (e.g. huge input_bits but tiny coeff_bits).
    Among ties the config with the most synthesized cells is chosen (falls back
    to the widest area proxy).

    Used by both Filter A (``build_comparison``) and Filter B
    (``generalization_filter_b``) so both comparisons apply an identical
    selection rule.
    """
    df = uniform_synth_df.copy()
    df["_min_width"] = df[["coeff_bits", "input_bits"]].min(axis=1)
    result = df.sort_values(
        ["_min_width", "total_cells"], ascending=[False, False]).iloc[0]
    return result.drop(labels=["_min_width"])


def build_comparison(h=None, verbose=True):
    paths.ensure_dirs()
    uniform = pd.read_csv(UNIFORM_CSV)
    sens = pd.read_csv(SENS_CSV)

    # "Best uniform" = fewest synthesized cells among passing configs.
    best_uniform = uniform.loc[uniform["total_cells"].idxmin()]
    # "Conservative uniform" = the balanced, widest-margin config.
    conservative_uniform = select_conservative_uniform(uniform)
    best_sensitivity = sens.loc[sens["total_cells"].idxmin()]

    comparison = pd.DataFrame([
        dict(name="Conservative uniform",
             cells=int(conservative_uniform["total_cells"]),
             rms_error=float(conservative_uniform["rms_error_wideband"]),
             snr_db=float(conservative_uniform["snr_db_wideband"]),
             coeff_bits=int(conservative_uniform["coeff_bits"]),
             input_bits=int(conservative_uniform["input_bits"]),
             acc_guard=int(conservative_uniform["acc_guard"]),
             bit_widths=",".join([str(int(conservative_uniform["coeff_bits"]))] * 9)),
        dict(name="Best uniform",
             cells=int(best_uniform["total_cells"]),
             rms_error=float(best_uniform["rms_error_wideband"]),
             snr_db=float(best_uniform["snr_db_wideband"]),
             coeff_bits=int(best_uniform["coeff_bits"]),
             input_bits=int(best_uniform["input_bits"]),
             acc_guard=int(best_uniform["acc_guard"]),
             bit_widths=",".join([str(int(best_uniform["coeff_bits"]))] * 9)),
        dict(name="Sensitivity-guided",
             cells=int(best_sensitivity["total_cells"]),
             rms_error=float(best_sensitivity["rms_error_wideband"]),
             snr_db=float(best_sensitivity["snr_db_wideband"]),
             coeff_bits=int(round(best_sensitivity["avg_bits_per_unique_coeff"])),
             input_bits=int(best_sensitivity["input_bits"]),
             acc_guard=int(best_sensitivity["acc_guard"]),
             bit_widths=best_sensitivity["bit_widths"]),
    ])
    comparison.to_csv(COMPARISON_CSV, index=False)

    # ---- persist the three headline configs so they can be rebuilt ----------
    headline = dict(
        filter="A",
        configs=dict(
            conservative_uniform=dict(
                kind="uniform",
                coeff_bits=int(conservative_uniform["coeff_bits"]),
                input_bits=int(conservative_uniform["input_bits"]),
                acc_guard=int(conservative_uniform["acc_guard"]),
                total_cells=int(conservative_uniform["total_cells"]),
            ),
            best_uniform=dict(
                kind="uniform",
                coeff_bits=int(best_uniform["coeff_bits"]),
                input_bits=int(best_uniform["input_bits"]),
                acc_guard=int(best_uniform["acc_guard"]),
                total_cells=int(best_uniform["total_cells"]),
            ),
            sensitivity_guided=dict(
                kind="nonuniform",
                bit_widths=[int(b) for b in str(best_sensitivity["bit_widths"]).split(",")],
                input_bits=int(best_sensitivity["input_bits"]),
                acc_guard=int(best_sensitivity["acc_guard"]),
                total_cells=int(best_sensitivity["total_cells"]),
            ),
        ),
    )
    HEADLINE_JSON.write_text(json.dumps(headline, indent=2))

    # ---- Pareto plot --------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(uniform["total_cells"], uniform["rms_error_wideband"],
               alpha=0.45, label="Uniform precision (all passing configs)",
               color="steelblue")
    ax.scatter(sens["total_cells"], sens["rms_error_wideband"],
               alpha=0.45, label="Sensitivity-guided (all passing configs)",
               color="darkorange")
    for _, row in comparison.iterrows():
        ax.scatter(row["cells"], row["rms_error"], s=200, marker="*", zorder=5,
                   color="black")
        ax.annotate(row["name"], (row["cells"], row["rms_error"]),
                    textcoords="offset points", xytext=(8, 8), fontsize=9)
    ax.set_xlabel("Synthesized cell count (area proxy)")
    ax.set_ylabel("RMS error vs. float reference")
    ax.set_yscale("log")
    ax.set_title("Accuracy-Area Pareto Frontier:\nUniform vs. Sensitivity-Guided Precision")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)

    if verbose:
        print(comparison.to_string(index=False))
        print(f"\nSaved: {paths.rel(COMPARISON_CSV)}")
        print(f"Saved: {paths.rel(PLOT_PATH)}")
        print(f"Saved: {paths.rel(HEADLINE_JSON)}")
    return comparison


def headline_configs(h=None):
    """
    Rebuild the three headline designs as (name, cfg, rtl_path, module_name,
    bit_widths) so the stress test and notebook verify exactly the same RTL
    that the comparison table reports.
    """
    if h is None:
        h = design_filter(FILTER_A_SPEC)
    spec = json.loads(HEADLINE_JSON.read_text())
    out = {}
    for name, c in spec["configs"].items():
        cfg = make_cfg(c["coeff_bits"] if c["kind"] == "uniform"
                       else int(round(np.mean(c["bit_widths"]))),
                       c["input_bits"], c["acc_guard"])
        if c["kind"] == "uniform":
            rtl_path = generate_rtl(h, cfg, config_name=name)
            bit_widths = None
        else:
            bit_widths = np.asarray(c["bit_widths"], dtype=int)
            rtl_path = generate_rtl_nonuniform(h, cfg, bit_widths, config_name=name)
        out[name] = dict(cfg=cfg, rtl_path=rtl_path, module_name=f"fir_{name}",
                         bit_widths=bit_widths, total_cells=c.get("total_cells"))
    return out


if __name__ == "__main__":
    build_comparison()
