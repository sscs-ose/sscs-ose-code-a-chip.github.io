#!/usr/bin/env python3
"""results/area_breakdown.csv: synthesis (pre-layout, hierarchy kept) cell area per module,
from <flowdir>/runs/hier/*synthesis/reports/stat.rpt. Final layout area is in ppa.csv (flattened)."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = []
for fd in ("sidecarcim_top_ff", "sidecarcim_top_ff_par", "sidecarcim_top_ff_pipe_s3"):
    rpt = next((ROOT / "flow" / fd / "runs" / "hier").glob("*synthesis/reports/stat.rpt")).read_text()
    area = {}
    for m in re.finditer(r"Chip area for (top )?module '([^']+)': ([\d.]+)", rpt):
        if m.group(1):
            area["total"] = float(m.group(3))
            continue
        n = m.group(2)
        key = "sidecar" if n.endswith("sidecar") else "dense_dcim_core" if n.endswith("dcim_core") else "top_merge_logic"
        area[key] = float(m.group(3))
    tot = area["total"]
    for k in ("dense_dcim_core", "sidecar", "top_merge_logic"):
        rows.append({"design": fd, "module": k, "synth_area_um2": round(area[k], 1),
                     "pct_of_total": round(100 * area[k] / tot, 2)})
    rows.append({"design": fd, "module": "total", "synth_area_um2": round(tot, 1), "pct_of_total": 100.0})

# single-module dense variants: flat synthesis area of the final run (run_dir from ppa.csv)
try:
    ppa = {r["design"]: r["run_dir"] for r in csv.DictReader(open(ROOT / "results" / "ppa.csv"))}
except OSError:
    ppa = {}
for d in ("dcim_w8a4_ff", "dcim_w6a4_ff", "dcim_w7a4_ff", "dcim_w4a8_ff"):
    if d not in ppa:
        continue
    rpt = next((ROOT / ppa[d]).glob("*synthesis/reports/stat.rpt")).read_text()
    a = float(re.findall(r"Chip area for (?:top )?module '[^']+': ([\d.]+)", rpt)[-1])
    rows.append({"design": d, "module": "dense_dcim_core", "synth_area_um2": round(a, 1), "pct_of_total": 100.0})
    rows.append({"design": d, "module": "total", "synth_area_um2": round(a, 1), "pct_of_total": 100.0})
with open(ROOT / "results" / "area_breakdown.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(open(ROOT / "results" / "area_breakdown.csv").read())
