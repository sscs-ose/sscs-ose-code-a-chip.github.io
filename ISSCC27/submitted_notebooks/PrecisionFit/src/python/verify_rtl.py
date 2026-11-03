"""
Bit-exact RTL vs. Python fixed-point model comparison.

Any mismatch here is a correctness bug -- not a rounding/precision
"acceptable difference". The whole project's numbers are meaningless if this
does not pass.

Simulation backend: the build script prefers Verilator (fast) and falls back
to Icarus Verilog, which is what the reference environment has installed.
Both harnesses apply the same stimulus protocol, so the comparison result is
identical; only the wall-clock cost differs.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

import paths
sys.path.insert(0, str(paths.TB_DIR))
import tb_utils  # noqa: E402  (needs the src/tb path insert above)

from fixedpoint import FixedPointConfig, run_model  # noqa: E402

# Number of leading samples in the RTL output stream that must be discarded to
# line it up with the golden model's y[0].
#
# Derivation for the generated architecture (input register -> accumulator
# register -> output register, with stimulus applied before the rising edge):
# after clock k the accumulator holds y[k-1] and the output register holds
# y[k-2], while out_valid is high for k = 1..n. So the RTL emits
# [y[-1], y[0], y[1], ..., y[n-2]] and exactly one leading zero-padding sample
# (y[-1] == 0) must be skipped. This was CONFIRMED empirically against the
# model on the impulse signal before being trusted -- get it wrong and every
# sample looks mismatched by a constant offset, which is a classic red herring.
LATENCY_CYCLES = 1

BUILD_SCRIPT = paths.TB_DIR / "build_and_run.sh"
VECTOR_DIR = Path(tempfile.gettempdir()) / "precisionfit_vectors"


def lint_rtl(rtl_path) -> dict:
    """Lint/elaborate the generated RTL. Uses Verilator if present, else Icarus.

    Verilator's -Wall catches combinational loops, sensitivity-list gaps and
    implicit-net bugs that Icarus silently accepts. When Verilator is absent
    the function falls back to Icarus and records a visible WARNING so callers
    know they are getting the weaker check.
    """
    if _which("verilator"):
        cmd = ["verilator", "--lint-only", "-Wall", str(rtl_path)]
        fallback = False
    elif _which("iverilog"):
        cmd = ["iverilog", "-g2012", "-Wall", "-o", "/dev/null", str(rtl_path)]
        fallback = True
    else:
        return dict(ok=False, backend=None, output="no lint tool available",
                    fallback=False)

    r = subprocess.run(cmd, capture_output=True, text=True)
    result = dict(ok=(r.returncode == 0), backend=cmd[0],
                  output=r.stdout + r.stderr, fallback=fallback)
    if fallback:
        import warnings
        warnings.warn(
            f"verilator not found; using {cmd[0]} as lint fallback. "
            "Icarus does not catch combinational-loop or sensitivity-list bugs. "
            "Install Verilator for a complete lint check.",
            stacklevel=2,
        )
    return result


def _which(prog: str) -> bool:
    from shutil import which
    return which(prog) is not None


def run_rtl(rtl_path, module_name: str, x_fixed: np.ndarray, cfg: FixedPointConfig,
            tag: str) -> np.ndarray:
    """Run one vector file through the DUT and return the raw output samples."""
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    in_path = VECTOR_DIR / f"{tag}_in.txt"
    out_path = VECTOR_DIR / f"{tag}_out.txt"
    out_path.unlink(missing_ok=True)

    tb_utils.write_input_vectors(x_fixed, in_path)
    tb_v = tb_utils.render_icarus_tb(module_name, cfg.input_total_bits,
                                     cfg.output_total_bits)

    cmd = [str(BUILD_SCRIPT), str(rtl_path), module_name, tb_v,
           str(in_path), str(out_path), str(len(x_fixed)),
           str(cfg.output_total_bits)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"simulation failed for {module_name}:\n{r.stdout}\n{r.stderr}")
    if not out_path.exists():
        raise RuntimeError(f"simulation produced no output file for {module_name}")
    return tb_utils.read_output_vectors(out_path)


def verify_config(h_float, cfg: FixedPointConfig, rtl_path: str, module_name: str,
                  test_signals: dict, latency_cycles: int = LATENCY_CYCLES,
                  bit_widths=None) -> dict:
    """
    Returns per-signal pass/fail. `bit_widths` selects per-tap precision.
    All signals are compared as raw integer bit patterns (y_raw vs out_data),
    which is the strictest possible check.
    """
    results = {}
    for name, x in test_signals.items():
        model = run_model(x, h_float, cfg, bit_widths)
        y_model = model["y_raw"]

        rtl_out = run_rtl(rtl_path, module_name, model["x_fixed"], cfg,
                          tag=f"{module_name}_{name}")

        n_take = len(rtl_out) - latency_cycles
        if n_take <= 0:
            results[name] = dict(passed=False, n_samples=0, n_mismatch=0,
                                 note=f"rtl produced only {len(rtl_out)} samples")
            continue

        y_model_aligned = y_model[:n_take]
        rtl_aligned = rtl_out[latency_cycles:latency_cycles + n_take]

        match = bool(np.array_equal(y_model_aligned, rtl_aligned))
        n_mismatch = int(np.sum(y_model_aligned != rtl_aligned))

        results[name] = dict(
            passed=match,
            n_samples=len(y_model_aligned),
            n_mismatch=n_mismatch,
            first_mismatch_idx=(int(np.argmax(y_model_aligned != rtl_aligned))
                                if n_mismatch else None),
        )
    return results


def print_results(results: dict) -> bool:
    ok = True
    for name, r in results.items():
        if r["passed"]:
            status = f"PASS ({r['n_samples']} samples)"
        else:
            status = f"FAIL ({r['n_mismatch']} mismatches"
            if r.get("first_mismatch_idx") is not None:
                status += f", first at {r['first_mismatch_idx']}"
            status += ")"
            ok = False
        print(f"  {name:>20}: {status}")
    return ok


if __name__ == "__main__":
    import warnings
    from reference import FILTER_A_SPEC, design_filter, make_test_signals
    from rtlgen import generate_rtl

    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)

    # ------------------------------------------------------------------ #
    # 1. Saturating design (the production path)                          #
    # ------------------------------------------------------------------ #
    cfg_sat = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14,
        acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )
    rtl_path = generate_rtl(h, cfg_sat, config_name="baseline_conservative")
    module_name = "fir_baseline_conservative"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        lint = lint_rtl(rtl_path)
    backend_label = lint["backend"].split("/")[-1] if lint["backend"] else "none"
    fallback_note = " (WARNING: Verilator absent, weaker check)" if lint.get("fallback") else ""
    print(f"lint ({backend_label}){fallback_note}: {'clean' if lint['ok'] else 'WARNINGS/ERRORS'}")
    if not lint["ok"]:
        print(lint["output"])

    sigs = make_test_signals(FILTER_A_SPEC["fs"], n_samples=512)
    results = verify_config(h, cfg_sat, rtl_path, module_name, sigs,
                            latency_cycles=LATENCY_CYCLES)
    ok = print_results(results)

    # ------------------------------------------------------------------ #
    # 2. Wrap-on-overflow design (saturate_output=False)                  #
    #                                                                     #
    # Uses a narrowed output width so that a full-scale wideband signal   #
    # reliably overflows and exercises the two's-complement wrap path.    #
    # The golden model's wrap() function must agree bit-for-bit with the  #
    # RTL's non-saturating requantizer on every overflowing sample.       #
    # ------------------------------------------------------------------ #
    cfg_wrap = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14,
        acc_guard_bits=4,
        output_int_bits=0, output_frac_bits=3,    # 4-bit output: max ±0.875 float
        rounding="round", saturate_output=False,  # wrap path under test
    )
    rtl_wrap = generate_rtl(h, cfg_wrap, config_name="test_baseline_wrap")
    # Full-scale + wideband: both cause overflow with the narrow output width
    sigs_wrap = {
        k: v for k, v in make_test_signals(FILTER_A_SPEC["fs"], n_samples=512).items()
        if k in ("full_scale", "random_wideband")
    }
    results_wrap = verify_config(h, cfg_wrap, rtl_wrap, "fir_test_baseline_wrap",
                                 sigs_wrap, latency_cycles=LATENCY_CYCLES)
    # Confirm the wrap path is actually exercised (at least one wrap must occur)
    wrap_exercised = False
    for sig in sigs_wrap.values():
        m = run_model(sig, h, cfg_wrap)
        out_max = (1 << (cfg_wrap.output_total_bits - 1)) - 1
        if np.any(np.abs(m["y_raw"]) > out_max):
            wrap_exercised = True
            break
    if not wrap_exercised:
        print("  wrap_mode: SKIP (no overflow on these signals "
              "-- widen output or use louder signal)")
    else:
        ok_wrap = print_results(results_wrap)
        ok = ok and ok_wrap

    if ok:
        print("\nAll signals bit-exact. RTL matches golden model.")
    else:
        print("\nMISMATCH -- do not trust downstream results until fixed.")
        sys.exit(1)
