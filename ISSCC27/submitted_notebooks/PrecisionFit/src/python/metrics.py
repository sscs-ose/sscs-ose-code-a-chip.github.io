"""Accuracy metrics: fixed-point output vs floating-point reference."""
import numpy as np

from reference import verify_spec


def error_stats(y_float_ref: np.ndarray, y_fixed: np.ndarray) -> dict:
    """Basic error statistics between reference and fixed-point output."""
    err = np.asarray(y_fixed, dtype=np.float64) - np.asarray(y_float_ref, dtype=np.float64)
    return dict(
        max_abs_error=float(np.max(np.abs(err))),
        rms_error=float(np.sqrt(np.mean(err ** 2))),
        mean_error=float(np.mean(err)),  # DC bias from rounding
        snr_db=float(10 * np.log10(np.mean(np.asarray(y_float_ref) ** 2) /
                                   (np.mean(err ** 2) + 1e-300))),
    )


def freq_response_error(h_fixed_float: np.ndarray, h_ref_float: np.ndarray,
                        spec: dict, n_fft: int = 8192) -> dict:
    """
    Compare frequency response of quantized coefficients against the
    original spec -- does the quantized filter still meet the requirement,
    not just "is it close to the float version".
    """
    v_fixed = verify_spec(h_fixed_float, spec, n_fft)
    v_ref = verify_spec(h_ref_float, spec, n_fft)
    return dict(
        fixed=v_fixed,
        ref=v_ref,
        passband_ripple_delta_db=v_fixed["passband_ripple_db"] - v_ref["passband_ripple_db"],
        stopband_atten_delta_db=v_ref["stopband_atten_db"] - v_fixed["stopband_atten_db"],
        meets_spec=v_fixed["passband_ok"] and v_fixed["stopband_ok"],
    )


def worst_case_bound(cfg, n_taps: int) -> float:
    """
    Analytical worst-case output error bound from coefficient quantization
    alone (uniform precision). This is a MATHEMATICAL bound, separate from
    empirical measurement -- report both, never conflate them.

        |e| <= sum_i |x[i]| * |dh_i| ,  |dh_i| <= 2**-f / 2 (round-to-nearest)
             <= n_taps * 1.0 * 2**-f / 2   for |x| <= 1

    Note this bound also uses the worst-case *symmetric-folded* gain: with
    symmetric folding a pair error is counted once against the folded input,
    which is already covered by the n_taps * ... form.
    """
    coeff_lsb = 2 ** (-cfg.coeff_frac_bits)
    max_coeff_quant_error = coeff_lsb / 2
    return n_taps * max_coeff_quant_error * 1.0


def worst_case_bound_per_tap(frac_bits_per_tap, n_taps: int,
                             max_input_abs: float = 1.0) -> float:
    """
    Analytical worst-case coefficient-quantization error bound for the
    per-tap (sensitivity-guided) design. Same argument as above, but each
    tap contributes its own 2**-f_i / 2 (and its symmetric partner shares
    the same coefficient, so folded pairs contribute twice).
    """
    frac = np.asarray(frac_bits_per_tap, dtype=int)
    half_lsb = 0.5 * 2.0 ** (-frac)
    # folded pairs: coefficient c_i multiplies (x[i] + x[n-1-i]) -> 2 unit inputs
    pair_terms = 2 * half_lsb[:len(frac) - 1]
    center_term = half_lsb[-1]
    return max_input_abs * (pair_terms.sum() + center_term)
