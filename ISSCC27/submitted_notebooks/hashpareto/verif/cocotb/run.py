import argparse
import os
import sys
from pathlib import Path

from cocotb_tools.runner import get_runner

ROOT = Path(
    os.environ.get("HASHPARETO_ROOT")
) or Path(__file__).resolve().parents[2]

SOURCES = [
    ROOT / "rtl/generated/sha_top.sv",
    ROOT / "rtl/generated/sha256_core.sv",
    ROOT / "rtl/original/rtl/core/message_padder.sv",
    ROOT / "rtl/generated/digest_buffer.sv",
]

TESTS = [
    "test_sha256.test_known_vectors",
    "test_sha256.test_boundary_lengths",
    "test_sha256.test_random",
    "test_sha256.test_ingress_bubbles",
    "test_sha256.test_egress_backpressure",
]


def run(sim, unroll, waves, verbose):
    runner = get_runner(sim)
    build_dir = ROOT / f"flow/runs/cocotb_u{unroll}" / f"sim_build_{sim}"
    build_args = []
    if sim == "verilator":
        build_args = ["--timing", "-Wno-fatal", "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC"]
        if waves:
            build_args.append("--trace")
    runner.build(
        sources=[str(p) for p in SOURCES],
        hdl_toplevel="sha_top",
        parameters={"UNROLL": unroll},
        build_dir=str(build_dir),
        build_args=build_args,
        always=True,
        verbose=verbose,
    )
    results = runner.test(
        test_module="test_sha256",
        hdl_toplevel="sha_top",
        test_dir=str(ROOT / "verif/cocotb"),
        parameters={"UNROLL": unroll},
        build_dir=str(build_dir),
        waves=waves,
        verbose=verbose,
    )
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="verilator", choices=["verilator", "icarus"])
    ap.add_argument("--unroll", type=int, default=1)
    ap.add_argument("--waves", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    results = run(args.sim, args.unroll, args.waves, args.verbose)
    if args.waves:
        vcd = Path(results) / "dump.vcd"
        print("waves:", vcd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
