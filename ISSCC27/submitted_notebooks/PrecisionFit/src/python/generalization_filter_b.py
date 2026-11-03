"""
Generalization test (guide section 6.6).

Repeats the Filter A pipeline -- reference design, sensitivity analysis,
uniform sweep, sensitivity-guided sweep, three-way comparison -- using
FILTER_B_SPEC instead of FILTER_A_SPEC, and test signals generated with a
DIFFERENT seed (so the accuracy measurement uses signals never used while
developing the method on Filter A).

This is the check that the *procedure* generalizes, not just the bit-width
numbers we happened to land on for Filter A.
"""
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
from reference import (FILTER_B_SPEC, design_filter, make_test_signals,
                       verify_spec)
from sensitivity import (compute_sensitivities_response,
                         unique_coeff_indices)
from search import uniform_sweep, make_cfg
from sweep_with_synth import synthesize_uniform_passing
from sensitivity_search import sensitivity_guided_sweep, synthesize_passing
from rtlgen import generate_rtl_nonuniform
from verify_rtl import verify_config, print_results
from build_comparison import select_conservative_uniform

UNIFORM_SWEEP = paths.SWEEPS_DIR / "filter_b_uniform_sweep.csv"
UNIFORM_SYNTH = paths.SWEEPS_DIR / "filter_b_uniform_sweep_synth.csv"
SENS_SWEEP = paths.SWEEPS_DIR / "filter_b_sensitivity_sweep.csv"
SENS_SYNTH = paths.SWEEPS_DIR / "filter_b_sensitivity_sweep_synth.csv"
COMPARISON = paths.PARETO_DIR / "filter_b_three_way_comparison.csv"
PLOT = paths.PARETO_DIR / "filter_b_pareto_frontier.png"


def run_filter_b(verify=True):
    paths.ensure_dirs()
    h = design_filter(FILTER_B_SPEC)
    v = verify_spec(h, FILTER_B_SPEC)
    print(f"Filter B reference: {len(h)} taps, ripple "
          f"{v['passband_ripple_db']:.3f} dB (ok={v['passband_ok']}), "
          f"stopband {v['stopband_atten_db']:.2f} dB (ok={v['stopband_ok']})")

    # different seed on purpose: signals never seen during Filter A development
    sigs = make_test_signals(FILTER_B_SPEC["fs"], n_samples=2048, seed=42)

    scores = compute_sensitivities_response(h, FILTER_B_SPEC)
    indices = unique_coeff_indices(len(h))
    print("Filter B sensitivity ranking (most sensitive first): "
          + ", ".join(f"tap{indices[k]}={scores[k]:.1f}"
                      for k in np.argsort(-scores)))
    print(f"  score spread: {scores.max() / scores.min():.2f}x")

    uni = uniform_sweep(h, FILTER_B_SPEC, sigs)
    uni.drop(columns=["cfg"]).to_csv(UNIFORM_SWEEP, index=False)
    uni_pass = uni[uni["passes_error_budget"]].copy()
    print(f"\nFilter B uniform sweep: {len(uni_pass)}/{len(uni)} configs pass")
    uni_synth = synthesize_uniform_passing(h, uni_pass, tag_prefix="b_u")
    uni_synth.to_csv(UNIFORM_SYNTH, index=False)

    sens = sensitivity_guided_sweep(h, FILTER_B_SPEC, sigs, scores=scores)
    sens_out = sens.drop(columns=["cfg"]).copy()
    # Same comma-joined bit_widths serialization as the Filter A sweep CSVs.
    sens_out["bit_widths"] = sens_out["bit_widths"].map(
        lambda bw: ",".join(str(int(b)) for b in bw))
    sens_out.to_csv(SENS_SWEEP, index=False)
    sens_pass = sens[sens["passes_error_budget"]]
    print(f"Filter B sensitivity-guided sweep: {len(sens_pass)}/{len(sens)} pass")
    sens_synth = synthesize_passing(h, sens, tag_prefix="b_s")
    sens_synth.to_csv(SENS_SYNTH, index=False)

    # ---- three-way comparison ----------------------------------------------
    best_u = uni_synth.loc[uni_synth["total_cells"].idxmin()]
    cons_u = select_conservative_uniform(uni_synth)
    best_s = sens_synth.loc[sens_synth["total_cells"].idxmin()]

    comparison = pd.DataFrame([
        dict(name="Conservative uniform", filter="B",
             cells=int(cons_u["total_cells"]),
             rms_error=float(cons_u["rms_error_wideband"])),
        dict(name="Best uniform", filter="B",
             cells=int(best_u["total_cells"]),
             rms_error=float(best_u["rms_error_wideband"])),
        dict(name="Sensitivity-guided", filter="B",
             cells=int(best_s["total_cells"]),
             rms_error=float(best_s["rms_error_wideband"])),
    ])
    comparison.to_csv(COMPARISON, index=False)
    print("\n" + comparison.to_string(index=False))

    improvement = (best_u["total_cells"] - best_s["total_cells"]) / best_u["total_cells"]
    print(f"\nSensitivity-guided vs best uniform on Filter B: "
          f"{improvement * 100:+.1f}% cells "
          f"({'better' if improvement > 0 else 'worse'})")
    print("Filter A equivalent was +3.6% cells (see results/pareto).")

    # ---- plot --------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(uni_synth["total_cells"], uni_synth["rms_error_wideband"],
               alpha=0.45, label="Uniform precision", color="steelblue")
    ax.scatter(sens_synth["total_cells"], sens_synth["rms_error_wideband"],
               alpha=0.45, label="Sensitivity-guided", color="darkorange")
    for _, row in comparison.iterrows():
        ax.scatter(row["cells"], row["rms_error"], s=200, marker="*",
                   zorder=5, color="black")
        ax.annotate(row["name"], (row["cells"], row["rms_error"]),
                    textcoords="offset points", xytext=(8, 8), fontsize=9)
    ax.set_xlabel("Synthesized cell count (area proxy)")
    ax.set_ylabel("RMS error vs. float reference")
    ax.set_yscale("log")
    ax.set_title("Filter B (generalization test): accuracy-area frontier")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.savefig(PLOT, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {paths.rel(COMPARISON)}")
    print(f"Saved: {paths.rel(PLOT)}")

    # ---- bit-exact verification of the Filter B winner ----------------------
    if verify:
        cfg = make_cfg(int(round(best_s["avg_bits_per_unique_coeff"])),
                       int(best_s["input_bits"]), int(best_s["acc_guard"]))
        bits = np.asarray([int(b) for b in str(best_s["bit_widths"]).split(",")])
        rtl_path = generate_rtl_nonuniform(h, cfg, bits, config_name="b_sens_best")
        print("\nBit-exact verification of the Filter B sensitivity-guided winner:")
        res = verify_config(h, cfg, rtl_path, "fir_b_sens_best", sigs,
                            bit_widths=bits)
        if not print_results(res):
            raise SystemExit("Filter B RTL is not bit-exact")

    return comparison


if __name__ == "__main__":
    run_filter_b()
