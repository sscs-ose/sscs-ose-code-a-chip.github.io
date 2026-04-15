# This script is for running the spice testbench locally
import subprocess
from pathlib import Path

# Control Parameters
PROJECT_ROOT = Path(
    "/home/xtoml/CaC_Spring26"
)  # Modify to where your repository path is

PDK_ROOT = "~/.ciel"  # Modify to where your PDK root is
SPICE_PATH = PROJECT_ROOT / "spice"

TB_DIR = SPICE_PATH / "testbenches"
TB_NAME = "tb_phase_detector.sp"

NETLIST_DIR = SPICE_PATH / "netlists"
NETLIST_NAME = "phase_detector_syn_edge.spice"

RESULTS_DIR = SPICE_PATH / "results"
RESULT_NAME = "pd_syn_edge_clkout_lead_results.csv"

# Only used for phase detector test benches
CLK_IN_DELAY = "22n"
CLK_OUT_DELAY = "20n"


def run_ngspice():
    """
    Resolve paths in a testbench template and run ngspice.

    Reads   spice/testbenches/{testbench_name}
    Writes  /tmp/{testbench_name}  (with resolved paths)
    Output  spice/results/
    """
    tb_template = (TB_DIR / TB_NAME).read_text()

    tb_resolved = (
        tb_template.replace("__PDK_ROOT__", str(PDK_ROOT))
        .replace("__NETLIST_PATH__", str(NETLIST_DIR / NETLIST_NAME))
        .replace("__RESULTS_DIR__", str(RESULTS_DIR))
        .replace("__RESULT_NAME__", str(RESULT_NAME))
        .replace("__CLK_IN_DELAY__", CLK_IN_DELAY)
        .replace("__CLK_OUT_DELAY__", CLK_OUT_DELAY)
    )

    # Ensure that result directory exists
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Creates temp directory
    tmp_dir = SPICE_PATH / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    resolved_path = tmp_dir / "temp_tb.sp"
    resolved_path.write_text(tb_resolved)

    print("Running ngspice...")

    result = subprocess.run(
        ["ngspice", "-b", str(resolved_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"\n[ERROR] ngspice exited with code {result.returncode}")
    else:
        print(f"\n[OK] Results written to {RESULTS_DIR}/")

    return result.returncode


if __name__ == "__main__":
    run_ngspice()
