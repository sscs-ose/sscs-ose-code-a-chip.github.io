#!/usr/bin/env python3
"""stdin: cgcheck.sh output for one design (arg1) -> append rows to results/cg_slack.csv"""
import csv
import sys
from pathlib import Path
d = sys.argv[1]
rows = {}
for l in sys.stdin:
    p = l.split()
    if len(p) == 4 and p[0] == "CG":
        rows.setdefault(p[1], {})[p[2]] = p[3]
f = Path(__file__).resolve().parents[1] / "results" / "cg_slack.csv"
new = not f.exists()
with open(f, "a", newline="") as fh:
    w = csv.writer(fh)
    if new:
        w.writerow(["design", "corner", "clock_gating_setup_slack_ns", "clock_gating_hold_slack_ns"])
    for c, v in sorted(rows.items()):
        w.writerow([d, c, v.get("max", ""), v.get("min", "")])
