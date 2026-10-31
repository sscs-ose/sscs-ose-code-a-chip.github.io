#!/usr/bin/env python3
"""results/ppa_128.csv: 128-row x 8-column gated layouts (post-layout estimates, real GPT-2 activity).
Energy per MVM = power x compute cycles (4) x clock period; one MVM = one 128-input x 8-output dot-product set.
128-row layouts: flow/scale/<name>/runs/layoutcg ; power from power_real.rpt (gate-level sim, 128-row real vectors)."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PER = int(re.search(r"clock_period_ns:\s*(\d+)", (ROOT / "spec/spec.yaml").read_text()).group(1))
N_IN, N_OUT, CYC = 128, 8, 4
ROWS = [  # label, scale dir, weight bits, k
    ("dcim W4A4 (dcim_core)", "dcim_core_n128", 4, ""),
    ("dcim W6A4", "dcim_w6a4_n128", 6, ""),
    ("dcim W8A4", "dcim_w8a4_n128", 8, ""),
    ("SidecarCIM K=2", "sidecarcim_top_n128", 4, 2),
    ("SidecarCIM K=4", "sidecarcim_topkk4_n128", 4, 4),
]
NOTE = "128-row projection, timing not closed at 30 ns for some designs; energy per MVM at 30 ns"
rows = []
for label, d, wb, k in ROWS:
    run = ROOT / "flow" / "scale" / d / "runs" / "layoutcg"
    mj = run / "final" / "metrics.json"
    if not mj.exists():
        st = next((ROOT / "flow" / "scale" / d / "runs" / "layoutcg").glob("*synthesis/reports/stat.rpt"), None)
        if st is None:
            continue
        a = float(re.findall(r"Chip area for (?:top )?module '[^']+': ([\d.]+)", st.read_text())[-1])
        rows.append({"design": label, "n_in": N_IN, "n_out": N_OUT, "weight_bits": wb, "k": k, "area_um2": round(a, 1),
                     "note": "did not route (OpenROAD global routing aborted, GRT-0183 heap underflow, at util 25 after util 30 never finished routing): synthesis area only, no timing/power", "clock_period_ns": PER,
                     "run_dir": str((ROOT / "flow" / "scale" / d / "runs" / "layoutcg").relative_to(ROOT))})
        continue
    m = json.loads(mj.read_text())
    ws = m["timing__setup__ws"]
    util = json.loads((ROOT / "flow" / "scale" / d / "config.json").read_text()).get("FP_CORE_UTIL")
    pw, e = None, None
    rpt = run / "power_real.rpt"
    if rpt.exists():
        for l in rpt.read_text().splitlines():
            if l.startswith("Total"):
                pw = float(re.findall(r"[-+]?\d+\.\d+e[-+]\d+", l)[3]) * 1e3
        if pw is not None:
            e = pw * CYC * PER
    rows.append({
        "design": label, "n_in": N_IN, "n_out": N_OUT, "weight_bits": wb, "k": k,
        "area_um2": m["design__instance__area__stdcell"], "cell_count": m["design__instance__count__stdcell"],
        "wns_ns": round(ws, 4), "fmax_mhz_est": round(1000.0 / (PER - ws), 2),
        "setup_vio": m["timing__setup_vio__count"], "hold_vio": m["timing__hold_vio__count"],
        "drc": m["magic__drc_error__count"] + m["klayout__drc_error__count"], "lvs": m["design__lvs_error__count"],
        "power_mw_est": None if pw is None else float("%.4g" % pw),
        "energy_per_mvm_pj_est": None if e is None else round(e, 1),
        "energy_per_mac_fj_est": None if e is None else round(e * 1000.0 / (N_IN * N_OUT), 2),
        "cycles_per_mvm": CYC, "clock_period_ns": PER, "fp_core_util": util,
        "note": NOTE,
        "activity": "real GPT-2 h.0 c_fc 128-row tiles (gate-level)", "run_dir": str(run.relative_to(ROOT)),
    })
for r in rows:
    r["build"] = "first build, 30 ns"
NEW = [("c%d_s3k4", "SidecarCIM headline (PIPE_MERGE=1, SBITS=3) K=4", 4, 4, 5),
       ("c%d_w6a4", "dcim W6A4", 6, "", 4), ("c%d_w4a4", "dcim W4A4", 4, "", 4)]
HOLD = ("c35h_s3k4", "SidecarCIM headline (PIPE_MERGE=1, SBITS=3) K=4", 4, 4, 5)
for clk in (35, 40, "35h"):
    for pat, label, wb, k, cyc in ([HOLD] if clk == "35h" else NEW):
        if clk == "35h":
            pat = "c35h_s3k4"; clkv = 35
        else:
            clkv = clk
        run = ROOT / "flow" / "p128" / (pat % clkv if "%" in pat else pat) / "runs" / "layout"
        mj = run / "final" / "metrics.json"
        if not mj.exists():
            continue
        m = json.loads(mj.read_text())
        ws = m["timing__setup__ws"]
        util = json.loads((ROOT / "flow" / "p128" / (pat % clkv if "%" in pat else pat) / "config.json").read_text()).get("FP_CORE_UTIL")
        pw = e = None
        rpt = run / "power_real.rpt"
        if rpt.exists():
            for l in rpt.read_text().splitlines():
                if l.startswith("Total"):
                    pw = float(re.findall(r"[-+]?\d+\.\d+e[-+]\d+", l)[3]) * 1e3
            if pw is not None:
                e = pw * cyc * clkv
        rows.append({
            "design": label, "n_in": N_IN, "n_out": N_OUT, "weight_bits": wb, "k": k,
            "area_um2": m["design__instance__area__stdcell"], "cell_count": m["design__instance__count__stdcell"],
            "wns_ns": round(ws, 4), "fmax_mhz_est": round(1000.0 / (clkv - ws), 2),
            "setup_vio": m["timing__setup_vio__count"], "hold_vio": m["timing__hold_vio__count"],
            "drc": m["magic__drc_error__count"] + m["klayout__drc_error__count"], "lvs": m["design__lvs_error__count"],
            "power_mw_est": None if pw is None else float("%.4g" % pw),
            "energy_per_mvm_pj_est": None if e is None else round(e, 1),
            "energy_per_mac_fj_est": None if e is None else round(e * 1000.0 / (N_IN * N_OUT), 2),
            "cycles_per_mvm": cyc, "clock_period_ns": clkv, "fp_core_util": util,
            "note": "128-row redo at %d ns, headline build; energy per MVM at %d ns%s%s" % (
                clkv, clkv, "; 5-cycle window incl. y-register update" if cyc == 5 else "",
                "; ONLY setting that differs from the other 35 ns rows: PL_RESIZER_HOLD_SLACK_MARGIN 0.2 (default 0.1), GRT_RESIZER_HOLD_SLACK_MARGIN 0.15 (default 0.05)" if clk == "35h" else ""),
            "build": ("redo, 35 ns, hold-repair margins (replaces the 2-hold-violation row)" if clk == "35h" else
                      "redo, 35 ns, default hold margins (superseded: 2 hold violations at max_ff, -0.065 ns)" if pat.endswith("s3k4") else "redo, %d ns" % clk),
            "activity": "real GPT-2 h.0 c_fc 128-row tiles (gate-level)", "run_dir": str(run.relative_to(ROOT)),
        })
if rows:
    cols = []
    for r in rows:
        for c in r:
            if c not in cols:
                cols.append(c)
    with open(ROOT / "results" / "ppa_128.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(rows)
    print(open(ROOT / "results" / "ppa_128.csv").read())
