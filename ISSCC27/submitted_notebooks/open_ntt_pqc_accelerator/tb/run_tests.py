"""Python runner for the cocotb testbenches (works in a notebook cell too).

Usage:
    python tb/run_tests.py mod_mul
    python tb/run_tests.py butterfly
    python tb/run_tests.py ntt
    python tb/run_tests.py all
"""
import os
import sys
try:
    from cocotb_tools.runner import get_runner   # cocotb >= 2.0
except ImportError:
    from cocotb.runner import get_runner          # cocotb 1.x

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")

# Each test: (verilog sources, top module, test python module)
TESTS = {
    "mod_mul": (["mod_mul.v"], "mod_mul", "test_mod_mul"),
    "butterfly": (["mod_mul.v", "butterfly.v"], "butterfly", "test_butterfly"),
    "ntt": (["mod_mul.v", "butterfly.v", "coeff_ram.v", "twiddle_rom.v", "ntt_top.v"],
            "ntt_top", "test_ntt"),
    "twiddle_gen": (["mod_mul.v", "twiddle_gen.v"], "twiddle_gen", "test_twiddle_gen"),
    "mask": (["mask.v"], "mask", "test_mask"),
    "soc": (["mod_mul.v", "butterfly.v", "coeff_ram.v", "twiddle_rom.v", "ntt_top.v",
             "soc/ntt_pcpi.v", "soc/ntt_dma.v", "soc/open_ntt_soc.v"],
            "open_ntt_soc", "test_soc"),
    "butterfly_radix4": (["mod_mul.v", "butterfly_radix4.v"], "butterfly_radix4", "test_butterfly_radix4"),
    "banked_mem": (["banked_mem_ctrl.v"], "banked_mem_ctrl", "test_banked_mem"),
    "fault_detect": (["fault_detect.v"], "fault_detect", "test_fault_detect"),
    "perf_counters": (["perf_counters.v"], "perf_counters", "test_perf_counters"),
    "trng": (["trng.v"], "trng", "test_trng"),
    "keccak_xof": (["keccak_xof.v"], "keccak_xof", "test_keccak_xof"),
    "clock_jitter_cam": (["clock_jitter_cam.v"], "clock_jitter_cam", "test_clock_jitter_cam"),
    "ntt_dual_core": (["mod_mul.v", "butterfly.v", "ntt_dual_core.v"], "ntt_dual_core", "test_ntt_dual_core"),
    "poly_sampler": (["poly_sampler.v"], "poly_sampler", "test_poly_sampler"),
}

# tests that need the twiddle hex present in the vvp working directory
NEEDS_TWIDDLE = {"ntt", "soc"}


def run_one(name):
    sources, toplevel, test_module = TESTS[name]
    vsources = [os.path.join(SRC, s) for s in sources]

    runner = get_runner("icarus")
    runner.build(
        verilog_sources=vsources,
        hdl_toplevel=toplevel,
        build_dir=os.path.join(ROOT, "sim_build", name),
        timescale=("1ns", "1ps"),
        includes=[SRC],  # so twiddle_rom's `include resolves regardless of cwd
        always=True,
    )
    runner.test(
        hdl_toplevel=toplevel,
        test_module=test_module,
        test_dir=HERE,
    )


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(TESTS.keys()) if which == "all" else [which]
    for n in names:
        print("=== running %s ===" % n)
        run_one(n)
