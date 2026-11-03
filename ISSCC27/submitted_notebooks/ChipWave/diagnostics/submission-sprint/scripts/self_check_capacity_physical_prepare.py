"""Exercise actual SDK preparation and frozen constraints without running EDA."""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from capacity_integration_physical import CASE, ROOT, PERIOD_PS, CONFIGURATION, prepare
from study_protocol import digest, write_json

sys.path.append(str(CASE/"scripts"))


def check():
    os.environ.update(ORFS_ROOT=str(CASE/"toolchain/orfs"), NUM_CORES="2")
    rows = []
    with tempfile.TemporaryDirectory(prefix="capacity-physical-prepare-") as tmp:
        for task in ("A1", "A2", "B1", "B2"):
            project = Path(tmp)/task
            manifest = prepare(project, task)
            sdc = (project/"physical/chip-nebula/constraints.sdc").read_text()
            assert "10.526" in sdc and "set_clock_uncertainty 0.1" in sdc
            assert "rst_n" in sdc and "remove_from_collection" not in sdc
            header = (project/"rtl/integration/nebula_cpu_npu_top.sv").read_text().split(");", 1)[0]+");\nendmodule\n"
            stub = project/"port-stub.v"
            stub.write_text(header.replace("logic", "wire"))
            constrained = re.search(r"set_input_delay[^\n]*\[get_ports \{([^}]+)\}\]", sdc)[1]
            tcl = project/"check-sdc.tcl"
            platform = CASE/"toolchain/orfs/flow/platforms/sky130hd"
            tcl.write_text(
                "if {[catch {\n"
                f"read_liberty {{{platform/'lib/sky130_fd_sc_hd__tt_025C_1v80.lib'}}}\n"
                f"read_lef {{{platform/'lef/sky130_fd_sc_hd.tlef'}}}\n"
                f"read_lef {{{platform/'lef/sky130_fd_sc_hd_merged.lef'}}}\n"
                f"read_verilog {{{stub}}}\nlink_design nebula_cpu_npu_top\n"
                f"read_sdc {{{project/'physical/chip-nebula/constraints.sdc'}}}\n"
                f"if {{[llength [all_inputs]] != {69 if task.startswith('A') else 71}}} "
                '{error "Unexpected frozen input population"}\n'
                f"if {{[llength [get_ports {{{constrained}}}]] != {68 if task.startswith('A') else 70}}} "
                '{error "Input constraints omit frozen inputs"}\n'
                'puts "CAPACITY_SDC_PASS"\n'
                "} message options]} {puts stderr $message; exit 1}\nexit\n")
            result = subprocess.run(["openroad", "-no_init", "-exit", "-threads", "2", str(tcl)],
                                    text=True, capture_output=True, timeout=30)
            if result.returncode or "CAPACITY_SDC_PASS" not in result.stdout:
                raise AssertionError(result.stdout+result.stderr)
            assert manifest["period_ps"] == PERIOD_PS and manifest["configuration"] == CONFIGURATION
            assert all(digest(project/p) == h for p, h in manifest["rtl_sha256"].items())
            before = digest(project/"benchmark-candidate.json")
            try:
                prepare(project, task)
            except ValueError:
                pass
            else:
                raise AssertionError("Existing frozen candidate overwritten")
            assert digest(project/"benchmark-candidate.json") == before
            rows.append(dict(task=task, passed=True, source_files=len(manifest["rtl_sha256"]),
                             period_ns=PERIOD_PS/1000))
    report = dict(passed=True, model_calls=0, physical_attempts=0, rows=rows,
                  configuration=CONFIGURATION,
                  scope="Actual Workbench/Recipe/TaskGraph preparation only; no physical run")
    report["real_sdc_read_passed"] = True
    write_json(ROOT/"checks/integration-physical-preparation-v2.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(check()))
