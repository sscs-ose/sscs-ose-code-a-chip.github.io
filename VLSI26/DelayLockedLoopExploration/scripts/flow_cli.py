import os
import glob
import argparse
import shutil
import subprocess
import re
import librelane
from librelane.flows import Flow
from pathlib import Path


def __is_valid_time_value(value):
    return bool(re.fullmatch(r"\d+(\.\d+)?[pnfum]", value))


def run_flow(design_name, base_dir):
    """
    Runs the flow and places the SPICE netlist in spice/netlists/
    """

    Classic = Flow.factory.get("Classic")
    librelane.logging.set_log_level("ERROR")

    DESIGN_DIR = Path(base_dir) / "librelane" / "design" / f"{design_name}"
    CONFIG_PATH = DESIGN_DIR / "config.json"

    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Could not find config.json at {CONFIG_PATH}")
        exit(1)

    print(f"-> Starting flow for '{design_name}'...")

    print(CONFIG_PATH)
    try:
        flow = Classic(str(CONFIG_PATH))
        flow.start()
    except Exception as e:
        print(f"Error: Flow failed for {design_name}. Details: {e}")
        exit(1)

    run_dir = flow.run_dir
    spice_search_path = os.path.join(run_dir, "final", "spice", "*.spice")
    spice_files = glob.glob(spice_search_path)

    if spice_files:
        print("\nExtracted SPICE file located at:")
        print(f"{spice_files[0]}\n")
    else:
        print(f"\nCouldn't locate the final SPICE file.")
        print(f"Check the logs in {run_dir} to see if Magic.SpiceExtraction failed.\n")
        exit(1)

    SPICE_DIR = Path(base_dir) / "spice"
    NETLISTS_DIR = SPICE_DIR / "netlists"
    NETLIST_DEST_PATH = NETLISTS_DIR / f"{design_name}.spice"

    print(f"Copying SPICE file to: {NETLIST_DEST_PATH}\n")
    try:
        os.makedirs(NETLIST_DEST_PATH.parent, exist_ok=True)
        shutil.copy2(spice_files[0], NETLIST_DEST_PATH)
    except Exception as e:
        print(
            f"Error: Failed to copy {spice_files[0]} to {NETLIST_DEST_PATH}. Details: {e}\n"
        )

    print("Flow complete!\n")


def run_ngspice(design_name, base_dir, pdk_root, clk_in_delay, clk_out_delay):
    """
    Runs NGSPICE for a given design whose SPICE netlist has already been generated.

    Reads   spice/testbenches/{testbench_name}
    Writes  /tmp/{testbench_name}  (with resolved paths)
    Output  spice/tmp_results/
    """
    SPICE_DIR = Path(base_dir) / "spice"

    TB_DIR = SPICE_DIR / "testbenches"

    NETLISTS_DIR = SPICE_DIR / "netlists"
    NETLIST_PATH = NETLISTS_DIR / f"{design_name}.spice"

    RESULTS_DIR = SPICE_DIR / "tmp_results"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if design_name in [
        "inv_dcdl",
        "inv_dcdl_cond",
        "inv_dcdl_glitch_free",
        "nand_dcdl",
        "controller_2mode",
        "controller_variable_step",
        "controller_saturate",
        "controller_filtered",
        "controller_locked",
    ]:
        # DCDLs have distinct spice testbenches
        TB_PATH = TB_DIR / f"tb_{design_name}.sp"
        result_name = f"{design_name}.csv"

        tb_template = TB_PATH.read_text()

        tb_resolved = (
            tb_template.replace("__PDK_ROOT__", str(pdk_root))
            .replace("__NETLIST_PATH__", str(NETLIST_PATH))
            .replace("__RESULTS_DIR__", str(RESULTS_DIR))
            .replace("__RESULT_NAME__", result_name)
        )
    elif design_name in [
        "phase_detector_syn_edge",
        "phase_detector_syn_ff1",
        "phase_detector_syn_pfd",
        "phase_detector_syn_xor1",
    ]:
        # Phase detectors share a spice testbench template
        TB_PATH = TB_DIR / "tb_phase_detector.sp"
        result_name = f"{design_name}_clkin{clk_in_delay}_clkout{clk_out_delay}.csv"
        tb_template = TB_PATH.read_text()

        tb_resolved = (
            tb_template.replace("__PDK_ROOT__", str(pdk_root))
            .replace("__NETLIST_PATH__", str(NETLIST_PATH))
            .replace("__RESULTS_DIR__", str(RESULTS_DIR))
            .replace("__RESULT_NAME__", result_name)
            .replace("__CLK_IN_DELAY__", str(clk_in_delay))
            .replace("__CLK_OUT_DELAY__", str(clk_out_delay))
        )

    # Creates temp directory for resolved testbench
    tmp_dir = SPICE_DIR / "tmp"
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
        print(f"\nERROR: ngspice exited with code {result.returncode}")
    else:
        print(f"\nResults written to {RESULTS_DIR / result_name}")

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run LibreLane flow and return the extracted SPICE file path."
    )

    parser.add_argument(
        "design_name",
        type=str,
        help="The name of the design to process (e.g., nand_dcdl, inv_dcdl)",
    )

    parser.add_argument(
        "--base-dir",
        type=str,
        default="/content/CAC_2026",
        help="Path to the base design directory",
    )

    parser.add_argument(
        "--process",
        type=str,
        default="flow",
        help="Which process to run: 'flow' or 'spice'",
    )

    parser.add_argument(
        "--pdk-root",
        type=str,
        default="~/.ciel",
        help="Root directory of the PDK files",
    )

    parser.add_argument(
        "--clk-in-delay",
        type=str,
        default="20n",
        help="Delay (in ns) of CLK_IN, only used for phase detector spice simulation",
    )

    parser.add_argument(
        "--clk-out-delay",
        type=str,
        default="20n",
        help="Delay (in ns) of CLK_OUT, only used for phase detector spice simulations",
    )

    args = parser.parse_args()
    design_name = args.design_name
    base_dir = args.base_dir
    process = args.process
    pdk_root = args.pdk_root

    clk_in_delay = args.clk_in_delay
    if not __is_valid_time_value(clk_in_delay):
        print("Invalid clk_in_delay, must be in the format like '20n' or '20p'")
        exit(1)

    clk_out_delay = args.clk_out_delay
    if not __is_valid_time_value(clk_in_delay):
        print("Invalid clk_in_delay, must be in the format like '20n' or '20p'")
        exit(1)

    if process.lower() == "flow":
        run_flow(design_name=design_name, base_dir=base_dir)
    elif process.lower() == "spice":
        run_ngspice(
            design_name=design_name,
            base_dir=base_dir,
            pdk_root=pdk_root,
            clk_in_delay=clk_in_delay,
            clk_out_delay=clk_out_delay,
        )
    else:
        print("Invalid process option. Available options are...")
        print("-> flow")
        print("-> spice")


if __name__ == "__main__":
    main()
