"""
Precision search: generate a config for every (coeff_bits, input_bits,
acc_guard) combination in a grid, evaluate each against the golden model,
measure accuracy, and record results. This produces:
  1. The "conservative uniform" baseline (widest reasonable config that
     clearly passes with margin).
  2. The "best uniform" baseline (narrowest config that still meets spec --
     found by sweeping down until failure, NOT chosen arbitrarily).
Both are real search results, not strawmen -- this matters for the
comparison's credibility.

The same `_evaluate` machinery backs `evaluate_nonuniform_config` (used by the
sensitivity-guided search), so the uniform and per-tap paths are compared with
identical accuracy metrics, identical signals and an identical error budget.
"""
import itertools

import numpy as np
import pandas as pd

import paths
from reference import (FILTER_A_SPEC, design_filter, float_reference,
                       make_test_signals)
from fixedpoint import (FixedPointConfig, quantize_coeffs, quantize_coeffs_per_tap,
                        fixed_to_float, run_model)
from metrics import error_stats, freq_response_error

ERROR_BUDGET = dict(
    max_rms_error=1e-3,       # output RMS error budget vs. float reference
    min_snr_db=60.0,          # equivalently, minimum SNR
)


def make_cfg(coeff_bits: int, input_bits: int, acc_guard: int,
             rounding: str = "round", saturate_output: bool = True,
             output_extra_bits: int = 0) -> FixedPointConfig:
    """Uniform config: 2 integer bits (sign + 1), rest fractional."""
    return FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=coeff_bits - 2,
        input_int_bits=2, input_frac_bits=input_bits - 2,
        acc_guard_bits=acc_guard,
        output_int_bits=2, output_frac_bits=input_bits - 2 + output_extra_bits,
        rounding=rounding, saturate_output=saturate_output,
    )


def effective_coeff_float(h_float, cfg, bit_widths=None) -> np.ndarray:
    """
    Coefficient values actually implemented by the hardware, as floats:
    quantized with the allocated widths and aligned to the common binary point
    (per-tap mode), or plain uniform quantization.
    """
    if bit_widths is None:
        return fixed_to_float(quantize_coeffs(h_float, cfg), cfg.coeff_frac_bits)

    n_taps = len(h_float)
    frac = np.asarray(bit_widths, dtype=int) - cfg.coeff_int_bits
    pairs = frac[:len(frac) - 1]
    full_frac = np.concatenate([pairs, [frac[-1]], pairs[::-1]])
    F = int(frac.max())
    full = quantize_coeffs_per_tap(h_float, cfg, frac)
    common = np.array([int(full[i]) << int(F - full_frac[i]) for i in range(n_taps)])
    return fixed_to_float(common, F)


def _evaluate(h_float, spec, test_signals, cfg, coeff_bits, input_bits, acc_guard,
              bit_widths=None, rounding="round", saturate_output=True,
              model_fn=None) -> dict:
    """Shared accuracy/spec evaluation for uniform and per-tap configs."""
    model_fn = model_fn or run_model

    h_eff = effective_coeff_float(h_float, cfg, bit_widths)
    freq_result = freq_response_error(h_eff, h_float, spec)

    x = test_signals["random_wideband"]
    y_ref_float = float_reference(x, h_float)
    r = model_fn(x, h_float, cfg, bit_widths)
    stats = error_stats(y_ref_float, r["y_float"])

    x_music = test_signals["random_music_like"]
    y_ref_music = float_reference(x_music, h_float)
    r_music = model_fn(x_music, h_float, cfg, bit_widths)
    stats_music = error_stats(y_ref_music, r_music["y_float"])

    passes = (
        freq_result["meets_spec"]
        and stats["rms_error"] <= ERROR_BUDGET["max_rms_error"]
        and stats["snr_db"] >= ERROR_BUDGET["min_snr_db"]
    )

    row = dict(
        coeff_bits=coeff_bits, input_bits=input_bits, acc_guard=acc_guard,
        rounding=rounding, saturate_output=saturate_output,
        # pre-synthesis area proxy; the real number comes from synthesis
        total_bits_per_tap=coeff_bits,
        passband_ripple_db=freq_result["fixed"]["passband_ripple_db"],
        stopband_atten_db=freq_result["fixed"]["stopband_atten_db"],
        meets_freq_spec=freq_result["meets_spec"],
        rms_error_wideband=stats["rms_error"],
        snr_db_wideband=stats["snr_db"],
        rms_error_music=stats_music["rms_error"],
        snr_db_music=stats_music["snr_db"],
        overflow_events=r["overflow_events"],
        passes_error_budget=passes,
        cfg=cfg,
    )
    if bit_widths is not None:
        row["avg_bits_per_unique_coeff"] = float(np.mean(bit_widths))
        row["bit_widths"] = list(int(b) for b in bit_widths)
    return row


def evaluate_uniform_config(h_float, coeff_bits, input_bits, acc_guard,
                            spec, test_signals, rounding="round",
                            saturate_output=True) -> dict:
    """
    Evaluate ONE uniform-precision config: accuracy + spec compliance.
    Does NOT synthesize -- that's a separate, more expensive step run only on
    configs that pass this filter (see sweep_with_synth.py).
    """
    cfg = make_cfg(coeff_bits, input_bits, acc_guard, rounding, saturate_output)
    return _evaluate(h_float, spec, test_signals, cfg, coeff_bits, input_bits,
                     acc_guard, rounding=rounding,
                     saturate_output=saturate_output)


def evaluate_nonuniform_config(h_float, input_bits, acc_guard, bit_widths,
                               spec, test_signals, rounding="round",
                               saturate_output=True, min_bits=None,
                               max_bits=None, n_levels=None) -> dict:
    """
    Evaluate ONE sensitivity-guided (per-tap width) config. Same error budget,
    same signals, same metrics as the uniform path.
    """
    bit_widths = np.asarray(bit_widths, dtype=int)
    coeff_bits = int(round(float(np.mean(bit_widths))))
    cfg = make_cfg(coeff_bits, input_bits, acc_guard, rounding, saturate_output)
    row = _evaluate(h_float, spec, test_signals, cfg, coeff_bits, input_bits,
                    acc_guard, bit_widths=bit_widths, rounding=rounding,
                    saturate_output=saturate_output)
    row.update(min_bits=min_bits, max_bits=max_bits, n_levels=n_levels)
    return row


def uniform_sweep(h_float, spec, test_signals) -> pd.DataFrame:
    coeff_bit_range = range(4, 17)   # sweep from aggressively small to generous
    input_bit_range = range(6, 19)
    acc_guard_range = [2, 4]

    rows = []
    for coeff_bits, input_bits, acc_guard in itertools.product(
            coeff_bit_range, input_bit_range, acc_guard_range):
        rows.append(evaluate_uniform_config(
            h_float, coeff_bits, input_bits, acc_guard, spec, test_signals))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)
    sigs = make_test_signals(FILTER_A_SPEC["fs"], n_samples=2048)
    df = uniform_sweep(h, FILTER_A_SPEC, sigs)
    df.drop(columns=["cfg"]).to_csv(paths.SWEEPS_DIR / "uniform_sweep.csv", index=False)

    passing = df[df["passes_error_budget"]]
    print(f"Total configs swept: {len(df)}")
    print(f"Passing configs: {len(passing)}")

    if len(passing):
        best = passing.loc[passing["total_bits_per_tap"].idxmin()]
        print("\nBest (narrowest) uniform config:")
        print(f"  coeff_bits={best['coeff_bits']}, input_bits={best['input_bits']}, "
              f"acc_guard={best['acc_guard']}")
        print(f"  RMS error: {best['rms_error_wideband']:.3e}, "
              f"SNR: {best['snr_db_wideband']:.1f} dB")

        margin = passing[passing["total_bits_per_tap"] >=
                         best["total_bits_per_tap"] + 4]
        conservative = margin.iloc[0] if len(margin) else \
            passing.loc[passing["total_bits_per_tap"].idxmax()]
        print("\nConservative uniform config (baseline):")
        print(f"  coeff_bits={conservative['coeff_bits']}, "
              f"input_bits={conservative['input_bits']}, "
              f"acc_guard={conservative['acc_guard']}")
        print(f"  RMS error: {conservative['rms_error_wideband']:.3e}, "
              f"SNR: {conservative['snr_db_wideband']:.1f} dB")
    print(f"\nSaved: {paths.rel(paths.SWEEPS_DIR / 'uniform_sweep.csv')}")
