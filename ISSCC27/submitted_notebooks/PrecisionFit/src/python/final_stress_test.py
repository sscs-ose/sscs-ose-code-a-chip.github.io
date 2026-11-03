"""
Full stress-test suite on the three headline configs: impulse, step,
full-scale chirp, two noise types, multitone, plus an explicit overflow stress
signal that deliberately drives the accumulator toward its limits.

For every config and signal this reports BOTH:
  * empirical error (measured, model + bit-exact RTL comparison), and
  * the analytical worst-case coefficient-quantization bound from
    metrics.worst_case_bound[_per_tap]
kept visually and numerically separate -- they answer different questions and
must never be merged into one number.
"""
import numpy as np
import pandas as pd

import paths
from reference import FILTER_A_SPEC, design_filter, float_reference, make_test_signals
from fixedpoint import run_model
from metrics import error_stats, worst_case_bound, worst_case_bound_per_tap
from build_comparison import headline_configs
from verify_rtl import verify_config, LATENCY_CYCLES

OUT_CSV = paths.PARETO_DIR / "stress_test.csv"


def overflow_stress_dc(n=4096, amp=0.999):
    """
    DC full-scale: worst case for accumulator growth in a symmetric lowpass,
    where every tap contributes the same sign.
    """
    return np.full(n, amp)


def overflow_stress_nyquist(n=4096, amp=0.999):
    """
    Alternating +/- full scale (Nyquist frequency). Worst case for
    highpass / bandpass architectures; exercised here for coverage.
    """
    x = np.empty(n)
    x[0::2] = amp
    x[1::2] = -amp
    return x


def run(h=None, n_samples=4096, verify=True):
    paths.ensure_dirs()
    if h is None:
        h = design_filter(FILTER_A_SPEC)
    sigs = make_test_signals(FILTER_A_SPEC["fs"], n_samples=n_samples)
    sigs["overflow_stress_dc"] = overflow_stress_dc(n_samples)
    sigs["overflow_stress_nyquist"] = overflow_stress_nyquist(n_samples)

    configs = headline_configs(h)
    rows = []
    rtl_summary = {}

    for name, c in configs.items():
        cfg, bit_widths = c["cfg"], c["bit_widths"]
        print(f"\n=== {name} ===")
        if bit_widths is None:
            bound = worst_case_bound(cfg, len(h))
            bound_note = "uniform, sum_i |x| * 2**-f/2, |x|<=1"
        else:
            bound = worst_case_bound_per_tap(
                np.asarray(bit_widths, dtype=int) - cfg.coeff_int_bits, len(h))
            bound_note = "per-tap, sum_i |x| * 2**-f_i/2, |x|<=1"
        print(f"  Analytical worst-case bound (coeff quantization only): {bound:.4e}")
        print("  (MATHEMATICAL bound, not an empirical measurement)")
        print(f"  bound formula: {bound_note}")

        rtl_results = None
        if verify:
            rtl_results = verify_config(h, cfg, c["rtl_path"], c["module_name"],
                                        sigs, latency_cycles=LATENCY_CYCLES,
                                        bit_widths=bit_widths)
        rtl_summary[name] = rtl_results

        for sig_name, x in sigs.items():
            model = run_model(x, h, cfg, bit_widths)
            y_ref = float_reference(x, h)
            stats = error_stats(y_ref, model["y_float"])
            rtl_status = "-"
            if rtl_results is not None:
                rtl_status = "PASS" if rtl_results[sig_name]["passed"] else "FAIL"
            print(f"  {sig_name:>18}: RMS={stats['rms_error']:.4e}  "
                  f"max={stats['max_abs_error']:.4e}  "
                  f"overflow_events={model['overflow_events']:>4}  "
                  f"RTL_match={rtl_status}")
            rows.append(dict(
                config=name, signal=sig_name,
                rms_error=stats["rms_error"], max_abs_error=stats["max_abs_error"],
                snr_db=stats["snr_db"], overflow_events=model["overflow_events"],
                rtl_bit_exact=(None if rtl_results is None
                               else bool(rtl_results[sig_name]["passed"])),
                # empirical and analytical kept in separate columns on purpose
                analytical_bound=bound,
                meets_analytical_bound=bool(stats["max_abs_error"] <= bound),
            ))

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {paths.rel(OUT_CSV)}")
    return df, rtl_summary


if __name__ == "__main__":
    # n_samples=2048 matches the notebook's stress-test cell (section 10), so
    # running this script standalone reproduces the committed
    # results/pareto/stress_test.csv byte-for-byte.
    df, rtl = run(n_samples=2048)
    all_exact = all(r["passed"] for res in rtl.values() if res for r in res.values())
    print(f"\nAll headline configs bit-exact against the golden model: {all_exact}")
    if not all_exact:
        raise SystemExit(1)
