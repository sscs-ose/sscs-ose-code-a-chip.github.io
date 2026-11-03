"""
Sanity checks that must pass before anything downstream is trusted.

1. Convergence: as coefficient/input/output word length grows, the
   fixed-point output must converge to the floating-point reference at
   roughly 6 dB SNR per extra bit. A buggy model does NOT converge cleanly,
   so this is a cheap, powerful correctness check (guide section 2.4).
2. Golden-loop vs vectorized equivalence: `fir_fixed_point_fast` (used by the
   sweeps) must be bit-identical to `fir_fixed_point` (the audited model).
3. Uniform path vs per-tap path equivalence: `fir_fixed_point_per_tap` with all
   taps allocated equal widths must be bit-identical to `fir_fixed_point`.
"""
import numpy as np

from reference import FILTER_A_SPEC, design_filter, float_reference, make_test_signals
from fixedpoint import (FixedPointConfig, fir_fixed_point, fir_fixed_point_fast,
                        fir_fixed_point_per_tap, fir_fixed_point_per_tap_fast)
from metrics import error_stats


def convergence_table(h, x, y_ref_float):
    print(f"{'bits':>6} {'RMS err':>14} {'SNR (dB)':>10}")
    rows = []
    for total_bits in [4, 6, 8, 10, 12, 16, 20, 24]:
        cfg = FixedPointConfig(
            coeff_int_bits=2, coeff_frac_bits=total_bits - 2,
            input_int_bits=2, input_frac_bits=total_bits - 2,
            acc_guard_bits=4,
            output_int_bits=2, output_frac_bits=total_bits - 2,
            rounding="round", saturate_output=True,
        )
        r = fir_fixed_point(x, h, cfg)
        stats = error_stats(y_ref_float, r["y_float"])
        rows.append(stats)
        print(f"{total_bits:>6} {stats['rms_error']:>14.6e} {stats['snr_db']:>10.2f}")
    return rows


def check_fast_matches_golden(h, x, seed=0):
    """Random configs: the vectorized model must equal the golden loop exactly."""
    rng = np.random.default_rng(seed)
    for trial in range(12):
        coeff_bits = int(rng.integers(4, 15))
        input_bits = int(rng.integers(8, 17))
        guard = int(rng.integers(0, 6))
        cfg = FixedPointConfig(
            coeff_int_bits=2, coeff_frac_bits=coeff_bits - 2,
            input_int_bits=2, input_frac_bits=input_bits - 2,
            acc_guard_bits=guard,
            output_int_bits=2, output_frac_bits=max(input_bits - 2, 4),
            rounding="round", saturate_output=True,
        )
        a = fir_fixed_point(x, h, cfg)
        b = fir_fixed_point_fast(x, h, cfg)
        assert np.array_equal(a["y_raw"], b["y_raw"]), \
            f"fast/golden mismatch on trial {trial}: cfg={cfg}"
        assert np.array_equal(a["x_fixed"], b["x_fixed"])
    print("\nfast path == golden loop on 12 random configs: OK")


def check_uniform_matches_per_tap(h, x):
    """Per-tap path with equal widths must reduce exactly to the uniform path."""
    coeff_bits = 10
    bits = np.full(len(h) // 2 + 1, coeff_bits, dtype=int)
    cfg = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=coeff_bits - 2,
        input_int_bits=2, input_frac_bits=12,
        acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=12,
        rounding="round", saturate_output=True,
    )
    a = fir_fixed_point(x, h, cfg)
    b = fir_fixed_point_per_tap(x, h, cfg, bits - cfg.coeff_int_bits)
    c = fir_fixed_point_per_tap_fast(x, h, cfg, bits - cfg.coeff_int_bits)
    assert np.array_equal(a["y_raw"], b["y_raw"]), "uniform vs per-tap mismatch"
    assert np.array_equal(b["y_raw"], c["y_raw"]), "per-tap fast vs golden mismatch"
    print("uniform == per-tap(eq widths) == per-tap-fast: OK")


if __name__ == "__main__":
    h = design_filter(FILTER_A_SPEC)
    sigs = make_test_signals(FILTER_A_SPEC["fs"], n_samples=1024)
    x = sigs["random_wideband"]
    y_ref_float = float_reference(x, h)

    rows = convergence_table(h, x, y_ref_float)

    # monotone-ish convergence: every 4-bit step should buy a lot of SNR
    snrs = np.array([r["snr_db"] for r in rows])
    assert np.all(np.diff(snrs) > 0), f"SNR is not monotonically increasing: {snrs}"
    print(f"\nSNR increases monotonically across all {len(rows)} widths: OK")

    check_fast_matches_golden(h, x)
    check_uniform_matches_per_tap(h, x)
    print("\nfixedpoint.py is trustworthy -- downstream results depend on this.")
