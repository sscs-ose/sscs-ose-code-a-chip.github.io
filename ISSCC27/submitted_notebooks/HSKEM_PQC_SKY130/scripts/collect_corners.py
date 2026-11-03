"""Summarize multi-corner STA logs (results/sta_corners/*.log) into one CSV.

For each routed design and corner it records the design-level setup and hold
WNS and the worst register-to-register setup and hold slack, from which the
register-to-register fmax at that corner is derived.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "results" / "sta_corners"
SLACK = re.compile(r"^\S+\s+\(\S+\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\((?:MET|VIOLATED)\)", re.M)


def main() -> None:
    rows = []
    for log in sorted(D.glob("*.log")):
        m = re.match(r"(.+_\d+ns)_(ss_100C_1v60|tt_025C_1v80|ff_n40C_1v95)\.log", log.name)
        if not m:
            continue
        clk_ns = float(re.search(r"_(\d+)ns$", m[1])[1])      # clock target from the run name
        txt = log.read_text(errors="replace")
        setup = re.search(r"RESULT setup_wns (-?[\d.]+)", txt)
        hold = re.search(r"RESULT hold_wns (-?[\d.]+)", txt)
        max_sec = txt.split("max_delay/setup", 1)[1].split("min_delay/hold", 1)[0]
        min_sec = txt.split("min_delay/hold", 1)[1]
        r2r_setup = float(SLACK.search(max_sec)[3])
        r2r_hold = float(SLACK.search(min_sec)[3])
        rows.append({
            "design": m[1], "corner": m[2],
            "setup_wns_ns": float(setup[1]), "hold_wns_ns": float(hold[1]),
            "reg2reg_setup_slack_ns": r2r_setup, "reg2reg_hold_slack_ns": r2r_hold,
            "reg2reg_fmax_mhz": round(1e3 / (clk_ns - r2r_setup), 2),
        })
    out = D / "summary.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
