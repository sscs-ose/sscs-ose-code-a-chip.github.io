"""Summarize the hold-margin re-run of the final NTT (results/asic/hold_margin_check.json).

The committed layout of ntt_opt_pipe_w12 at 20 ns violates hold by a few ps at the fast
corner, because ORFS repairs hold at the typical corner only. Its single violating
endpoint has about 140 ps of hold slack at the typical corner, so the layout was re-run
with HOLD_SLACK_MARGIN = 0.17 ns (a first attempt with 0.05 ns changed nothing, since
every path already exceeded that margin). This script records the three-corner hold and
setup slack (OpenSTA, results/sta_corners/), the cost of the repair and the gate-level check.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = {"committed": "ntt_opt_pipe_w12_20ns", "hold margin 0.17 ns": "ntt_opt_pipe_w12_20ns_hm170"}
CORNERS = ["ss_100C_1v60", "tt_025C_1v80", "ff_n40C_1v95"]


def main() -> None:
    out = {"margin_ns": 0.17, "runs": {}}
    for label, run in RUNS.items():
        rep = json.loads(next((ROOT / "results/asic" / run / "logs").rglob("6_report.json")).read_text())
        row = {"run": run,
               "stdcell_area_um2": rep["finish__design__instance__area__stdcell"],
               "stdcell_count": rep["finish__design__instance__count__stdcell"],
               "fmax_mhz": rep["finish__timing__fmax"] / 1e6}
        for c in CORNERS:
            log = (ROOT / "results/sta_corners" / f"{run}_{c}.log").read_text()
            row[f"setup_wns_ns_{c}"] = float(re.search(r"RESULT setup_wns (-?[\d.]+)", log)[1])
            row[f"hold_wns_ns_{c}"] = float(re.search(r"RESULT hold_wns (-?[\d.]+)", log)[1])
        gls = ROOT / "results/gls_notebook" / run / "gls.log"
        row["gls_pass"] = gls.exists() and "PASS" in gls.read_text() and "errors=0" in gls.read_text()
        out["runs"][label] = row
    p = ROOT / "results/asic/hold_margin_check.json"
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(p.read_text())


if __name__ == "__main__":
    main()
