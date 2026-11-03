"""Summarize the hold-margin re-runs of the NTT layouts (results/asic/hold_margin_check.json).

The committed NTT layouts violate hold by a few ps at the fast corner, because ORFS repairs
hold at the typical corner only. Their violating endpoints have roughly 130-140 ps of hold
slack at the typical corner, so each layout was re-run with HOLD_SLACK_MARGIN = 0.17 ns
(a first attempt with 0.05 ns changed nothing, since every path already exceeded that
margin). For each layout this script records the three-corner hold and setup slack
(OpenSTA, results/sta_corners/), the cost of the repair and the gate-level check.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
LAYOUTS = ["ntt_dp_20ns", "ntt_sp_20ns", "ntt_opt_b1_w12_20ns", "ntt_opt_pipe_w12_20ns", "ntt_opt_pipe_w12_12ns"]
SUFFIX = "_hm170"
CORNERS = ["ss_100C_1v60", "tt_025C_1v80", "ff_n40C_1v95"]


def row_for(run: str) -> dict:
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
    return row


def main() -> None:
    out = {"margin_ns": 0.17, "layouts": {}}
    for base in LAYOUTS:
        if not (ROOT / "results/sta_corners" / f"{base}{SUFFIX}_{CORNERS[-1]}.log").exists():
            print(f"skipping {base}: no corner analysis of the re-run yet")
            continue
        out["layouts"][base] = {"committed": row_for(base), "hold margin 0.17 ns": row_for(base + SUFFIX)}
    p = ROOT / "results/asic/hold_margin_check.json"
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(p.read_text())


if __name__ == "__main__":
    main()
