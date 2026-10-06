"""
Sensitivity-guided precision search.

Uses the per-tap sensitivity scores to allocate a *non-uniform* coefficient
bit width, sweeps the allocation range and the datapath input width the same
way `search.uniform_sweep` sweeps uniform width, evaluates each candidate with
the identical error budget / signals / metrics, and synthesizes the passing
ones. That makes the section 5.4 comparison apples-to-apples.

Allocation score: `sensitivity.compute_sensitivities_response` (the exact,
spec-weighted response influence). The guide's finite-difference-of-the-margin
variant is kept in sensitivity.py and its eps-instability is reported in the
notebook as a documented finding -- see `compute_sensitivities`.
"""
import itertools

import numpy as np
import pandas as pd
from tqdm import tqdm

import paths
from reference import FILTER_A_SPEC, design_filter, make_test_signals
from sensitivity import (compute_sensitivities_response,
                         allocate_bits_by_sensitivity, unique_coeff_indices)
from search import evaluate_nonuniform_config
from rtlgen import generate_rtl_nonuniform
from synth_yosys import synthesize

# swept ranges (mirroring uniform_sweep's ranges so the two frontiers are
# comparable): total bits per tap varies between MIN and MAX across the taps,
# quantized to N_LEVELS discrete widths.
MIN_BIT_RANGE = [10, 11, 12, 13]
MAX_BIT_RANGE = [14, 15, 16]
N_LEVELS_RANGE = [3, 4]
INPUT_BIT_RANGE = [12, 13, 14, 15, 16]
ACC_GUARD_RANGE = [2, 4]


def sensitivity_guided_sweep(h_float, spec, test_signals, scores=None,
                             min_bit_range=None, max_bit_range=None,
                             n_levels_range=None, input_bit_range=None,
                             acc_guard_range=None) -> pd.DataFrame:
    """Evaluate every (min_bits, max_bits, n_levels, input_bits, acc_guard) point."""
    if scores is None:
        scores = compute_sensitivities_response(h_float, spec)
    min_bit_range = min_bit_range or MIN_BIT_RANGE
    max_bit_range = max_bit_range or MAX_BIT_RANGE
    n_levels_range = n_levels_range or N_LEVELS_RANGE
    input_bit_range = input_bit_range or INPUT_BIT_RANGE
    acc_guard_range = acc_guard_range or ACC_GUARD_RANGE

    rows = []
    combos = list(itertools.product(min_bit_range, max_bit_range, n_levels_range,
                                    input_bit_range, acc_guard_range))
    for min_bits, max_bits, n_levels, input_bits, acc_guard in tqdm(combos):
        if max_bits <= min_bits:
            continue
        bit_widths = allocate_bits_by_sensitivity(scores, min_bits, max_bits, n_levels)
        row = evaluate_nonuniform_config(
            h_float, input_bits, acc_guard, bit_widths, spec, test_signals,
            min_bits=min_bits, max_bits=max_bits, n_levels=n_levels)
        rows.append(row)
    return pd.DataFrame(rows)


def synthesize_passing(h, df, tag_prefix="s", max_configs=None) -> pd.DataFrame:
    """Generate + synthesize RTL for every passing config; return cell counts."""
    passing = df[df["passes_error_budget"]].copy()
    if max_configs is not None:
        passing = passing.sort_values("avg_bits_per_unique_coeff").head(max_configs)
    print(f"synthesizing {len(passing)} passing sensitivity-guided configs")

    rows = []
    for _, row in tqdm(passing.iterrows(), total=len(passing)):
        bits = np.asarray(row["bit_widths"], dtype=int)
        tag = (f"{tag_prefix}_lo{row['min_bits']}_hi{row['max_bits']}"
               f"_lv{row['n_levels']}_i{row['input_bits']}_g{row['acc_guard']}")
        cfg = row["cfg"]
        rtl_path = generate_rtl_nonuniform(h, cfg, bits, config_name=tag)
        module_name = f"fir_{tag}"
        try:
            res = synthesize(rtl_path, module_name)
        except RuntimeError as e:
            print(f"  synthesis failed for {tag}: {e}")
            continue
        rows.append(dict(
            tag=tag, module_name=module_name,
            # repo-relative so committed CSVs are machine-independent
            rtl_path=paths.rel(rtl_path),
            total_cells=res["total_cells"], flop_cells=res["flop_cells"],
            comb_cells=res["comb_cells"],
            min_bits=row["min_bits"], max_bits=row["max_bits"],
            n_levels=row["n_levels"], input_bits=row["input_bits"],
            acc_guard=row["acc_guard"],
            avg_bits_per_unique_coeff=row["avg_bits_per_unique_coeff"],
            rms_error_wideband=row["rms_error_wideband"],
            snr_db_wideband=row["snr_db_wideband"],
            stopband_atten_db=row["stopband_atten_db"],
            passband_ripple_db=row["passband_ripple_db"],
            bit_widths=",".join(str(int(b)) for b in bits),
        ))
    return pd.DataFrame(rows).sort_values("total_cells")


def main(quick=False):
    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)
    sigs = make_test_signals(FILTER_A_SPEC["fs"], n_samples=2048)

    scores = compute_sensitivities_response(h, FILTER_A_SPEC)
    indices = unique_coeff_indices(len(h))
    order = np.argsort(-scores)
    print("sensitivity ranking (most sensitive first): "
          + ", ".join(f"tap{indices[k]}={scores[k]:.1f}" for k in order))

    kwargs = dict()
    if quick:
        kwargs = dict(min_bit_range=[12, 13], max_bit_range=[15],
                      n_levels_range=[4], input_bit_range=[13, 14, 16],
                      acc_guard_range=[4])

    df = sensitivity_guided_sweep(h, FILTER_A_SPEC, sigs, scores=scores, **kwargs)
    df_out = df.drop(columns=["cfg"]).copy()
    # Serialize bit_widths comma-joined so both sweep CSVs share one format
    # (list-repr would need a special-case parser in every consumer).
    df_out["bit_widths"] = df_out["bit_widths"].map(
        lambda bw: ",".join(str(int(b)) for b in bw))
    df_out.to_csv(paths.SWEEPS_DIR / "sensitivity_sweep.csv", index=False)

    passing = df[df["passes_error_budget"]]
    print(f"\nTotal configs swept: {len(df)}")
    print(f"Passing configs: {len(passing)}")
    if len(passing):
        best = passing.loc[passing["avg_bits_per_unique_coeff"].idxmin()]
        print(f"Best (lowest avg bits/tap) passing config: "
              f"avg_bits={best['avg_bits_per_unique_coeff']:.2f}, "
              f"bits={best['bit_widths']}, input_bits={best['input_bits']}, "
              f"guard={best['acc_guard']}")
        print(f"  RMS error {best['rms_error_wideband']:.3e}, "
              f"SNR {best['snr_db_wideband']:.1f} dB, "
              f"stopband {best['stopband_atten_db']:.2f} dB")

    synth_df = synthesize_passing(h, df)
    out = paths.SWEEPS_DIR / "sensitivity_sweep_synth.csv"
    synth_df.to_csv(out, index=False)
    print(f"\nSynthesized {len(synth_df)} configs -> {paths.rel(out)}")
    print(synth_df[["tag", "total_cells", "avg_bits_per_unique_coeff",
                    "rms_error_wideband"]].head(10).to_string(index=False))
    return df, synth_df


if __name__ == "__main__":
    import sys
    main(quick="--quick" in sys.argv)
