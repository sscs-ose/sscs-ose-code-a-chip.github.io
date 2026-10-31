#!/usr/bin/env python3
"""results/load_energy.csv: gate-level energy of one full weight reload (N_IN row loads + slot/S column loads),
real weights from the vectors (first 50 cases, each case reloads). Window = load_en high; energy = power x N_IN cycles x clock."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PER = int(re.search(r"clock_period_ns:\s*(\d+)", (ROOT / "spec/spec.yaml").read_text()).group(1))
ppa = {r["design"]: r["run_dir"] for r in csv.DictReader(open(ROOT / "results/ppa.csv"))}
ROWS = [(d, 32, PER, ppa[d]) for d in ("sidecarcim_top_ff_pipe_s3", "sidecarcim_top_ff", "dcim_core_ff", "dcim_w6a4_ff", "dcim_w8a4_ff", "dcim_w7a4_ff", "dcim_w4a8_ff") if d in ppa]
for clk in (35, 40):
    for n, lab in (("s3k4", "sidecar pipe SBITS=3 K=4 (headline)"), ("w6a4", "dcim W6A4"), ("w4a4", "dcim W4A4")):
        run = ROOT / "flow" / "p128" / ("c%d_%s" % (clk, n)) / "runs" / "layout"
        if (run / "power_load.rpt").exists():
            ROWS.append(("%s 128-row %d ns" % (lab, clk), 128, clk, str(run.relative_to(ROOT))))
# dcim_core_ff reload with the naive W4A4 real_layer.npz weights (no migration), kept as a labelled row
if "dcim_core_ff" in ppa:
    ROWS.append(("dcim_core_ff plain W4A4 (no migration)", 32, PER, ppa["dcim_core_ff"], "power_load_nomig.rpt"))
hr = ROOT / "flow" / "p128" / "c35h_s3k4" / "runs" / "layout"
if (hr / "power_load.rpt").exists():
    ROWS.append(("sidecar pipe SBITS=3 K=4 (headline) 128-row 35 ns, hold-repair margins", 128, 35, str(hr.relative_to(ROOT))))
out = []
for d, ni, clk, run, *rpt in ROWS:
    f = ROOT / run / (rpt[0] if rpt else "power_load.rpt")
    if not f.exists():
        continue
    p = None
    for l in f.read_text().splitlines():
        if l.startswith("Total"):
            p = float(re.findall(r"[-+]?\d+\.\d+e[-+]\d+", l)[3]) * 1e3
    if p is None:
        continue
    e = p * ni * clk
    out.append({"design": d, "n_in": ni, "window_cycles": ni, "clock_ns": clk, "power_mw_load_window": float("%.4g" % p),
                "energy_per_reload_pj": round(e, 1), "energy_per_row_load_pj": round(e / ni, 2), "run_dir": run,
                "note": "gate-level, real weights, includes slot/S column loads where present"})
with open(ROOT / "results" / "load_energy.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, list(out[0]))
    w.writeheader()
    w.writerows(out)
print(open(ROOT / "results" / "load_energy.csv").read())
