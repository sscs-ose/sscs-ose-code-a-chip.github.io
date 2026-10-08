"""Address-pin transitions of the SRAM macro in routed NTT blocks (Appendix B.4).

Runs flow/macro_pin_slew.tcl in OpenROAD on each run's routed database and extracted parasitics and adds
the result to results/asic/macro_pin_slew.json. Address bits that the block ties to a constant (the
macro's unused most significant bit) are left out.

usage: python3 scripts/macro_pin_slew.py <run> <macro> [<run> <macro> ...]
       e.g. ntt_packed_20ns sky130_sram_1rw_24x128   (needs the ORFS work directory of the run)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ORFS = pathlib.Path(os.environ.get("ORFS_ROOT", "/opt/eda/orfs-6101364b"))
WORK = pathlib.Path(os.environ.get("CAC_WORK", pathlib.Path.home() / "cac_runs"))
OUT = ROOT / "results" / "asic" / "macro_pin_slew.json"
LIMIT = 0.04          # ns, the macro's Liberty limit on its address pins


def pin_slews(run: str, macro: str) -> dict:
    base = WORK / run / "results" / "sky130hd" / f"cac_{run}" / "base"
    env = dict(os.environ, LIB=str(ORFS / "flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"),
               LIB_MACRO=str(ROOT / "flow/macros" / f"{macro}_TT_1p8V_25C.lib"), ODB=str(base / "6_final.odb"),
               SDC=str(base / "6_final.sdc"), SPEF=str(base / "6_final.spef"))
    with tempfile.TemporaryDirectory() as t:        # OpenROAD can stall on files of a mounted Windows drive
        tcl = pathlib.Path(t) / "macro_pin_slew.tcl"
        tcl.write_text((ROOT / "flow/macro_pin_slew.tcl").read_text())
        out = subprocess.run([str(ORFS / "tools/install/OpenROAD/bin/openroad"), "-no_splash", "-exit", str(tcl)],
                             env=env, capture_output=True, text=True, check=True).stdout
    pins = {m[1]: float(m[2]) for m in re.finditer(r"^PIN \S+/(addr0\[\d+\]) slew ([\d.eE+-]+)", out, re.M)}
    # a pin driven by a constant shows a near-zero transition: the unused address bit
    return {p: round(v, 4) for p, v in pins.items() if v > 0.005}


def main(args: list[str]) -> None:
    data = json.loads(OUT.read_text()) if OUT.exists() else {"limit_ns": LIMIT, "runs": {}}
    data["source"] = ("OpenROAD STA on the routed database with the extracted SPEF, typical corner "
                      "(flow/macro_pin_slew.tcl, scripts/macro_pin_slew.py; drivers placed by "
                      "flow/post_grt_macro_pins.tcl)")
    for run, macro in zip(args[::2], args[1::2]):
        pins = pin_slews(run, macro)
        data["runs"][run] = {"address_pin_transition_ns": pins, "max_ns": max(pins.values()),
                             "pins_over_limit": sum(v > LIMIT for v in pins.values())}
        print(run, data["runs"][run])
    OUT.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
