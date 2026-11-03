import os
import sys

sys.dont_write_bytecode = True
from pathlib import Path

from cocotb_tools.runner import get_runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = ROOT / "build" / "cocotb"


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    runner = get_runner("icarus")
    runner.build(
        sources=[ROOT / "rtl" / "cpu_core.v"],
        hdl_toplevel="cpu_core",
        build_dir=BUILD,
        always=True,
        timescale=("1ns", "1ps"),
        waves=True,
    )
    os.environ["ZC_TRACE"] = str(BUILD / "cocotb_trace.json")
    sys.path.insert(0, str(HERE))
    runner.test(
        hdl_toplevel="cpu_core",
        test_module="test_cpu",
        build_dir=BUILD,
        test_dir=HERE,
        results_xml=str(BUILD / "results.xml"),
        extra_env={"PYTHONDONTWRITEBYTECODE": "1"},
        waves=True,
    )


if __name__ == "__main__":
    main()
