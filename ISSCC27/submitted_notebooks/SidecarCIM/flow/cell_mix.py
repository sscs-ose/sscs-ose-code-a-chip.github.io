#!/usr/bin/env python3
"""results/cell_mix.csv for the design given as argv[1] (default sidecarcim_top_ff) from the final netlist of the run_dir in ppa.csv.
Top-10 logic cell types (physical-only decap/fill/tap/diode cells excluded), same layout as before."""
import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
D = sys.argv[1] if len(sys.argv) > 1 else "sidecarcim_top_ff"
run = [r["run_dir"] for r in csv.DictReader(open(ROOT / "results/ppa.csv")) if r["design"] == D][0]
nl = next((ROOT / run / "final" / "nl").glob("*.nl.v")).read_text()
cnt = Counter(re.findall(r"^\s*(sky130_fd_sc_hd__\w+|FILLER\w*|TAP\w*)\s+\S+\s*\(", nl, re.M))
phys_re = re.compile(r"fill|decap|tap|diode|ANTENNA|phy", re.I)
logic = Counter({k: v for k, v in cnt.items() if not phys_re.search(k)})
phys = sum(v for k, v in cnt.items() if phys_re.search(k))
# physical-only cells instantiated as FILLER_*/TAP_*/PHY_* instances (type names of the sky130 fill/tap cells)
tot = sum(logic.values())
ROLE = {"dfxtp": "D flip-flop (all state: weights, slots, S, x lanes, acc)",
        "mux2_1": "2:1 mux (S shifter; slot row select; remaining load/hold muxes)",
        "dlygate4sd3_1": "delay gate, hold-time fix (P&R)",
        "clkdlybuf4s25_1": "delay buffer, I/O and repair buffering (P&R)",
        "nand2": "NAND2 (AND of w and xbit; adder logic)", "xnor2": "XNOR2 (adder sum bits)",
        "nor2": "NOR2 (adder logic)", "or2": "OR2", "and2": "AND2", "a22o": "AND-OR (2x2)",
        "dlclkp": "integrated clock gate (one per weight row / slot column / S word)"}


def role(t):
    s = t.replace("sky130_fd_sc_hd__", "")
    for k, v in ROLE.items():
        if s == k or s.startswith(k + "_"):
            return v
    return ""


rows = logic.most_common(10)
with open(ROOT / "results" / "cell_mix.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["rank", "cell", "count", "pct_of_logic_cells", "role"])
    for i, (t, n) in enumerate(rows, 1):
        w.writerow([i, t, n, round(100 * n / tot, 1), role(t)])
    rest = tot - sum(n for _, n in rows)
    w.writerow(["", "other logic cell types (%d)" % (len(logic) - len(rows)), rest, round(100 * rest / tot, 1), ""])
    w.writerow(["", "total logic cells", tot, 100.0, ""])
    w.writerow(["", "physical-only (decap, fill, tap, diode)", phys, "", "not logic"])
    w.writerow(["", "source", run, "", "final/nl netlist"])
print(open(ROOT / "results/cell_mix.csv").read())
