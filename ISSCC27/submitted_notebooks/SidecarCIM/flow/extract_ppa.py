#!/usr/bin/env python3
"""Write results/ppa.csv from LibreLane run outputs. Every number comes from run files.

Usage: python flow/extract_ppa.py [design=run_dir ...]   (default: newest run with final/metrics.json)
Power: <run>/power_vcd.rpt if present, else <run>/power_vectorless.rpt (made by flow/power.sh).
All power / energy / fmax values are post-layout estimates.
"""
import csv
import gzip
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flow"
OUT = ROOT / "results"

# design -> (flow dir, top module, cycles-per-dot rule)
DESIGNS = {
    "dcim_core": ("dcim_core", "dcim_core", "dcim"),
    "dcim_core_ff": ("dcim_core_ff", "dcim_core", "dcim"),
    "sidecarcim_top_ff": ("sidecarcim_top_ff", "sidecarcim_top", "dcim"),
    "sidecarcim_top_ff_par": ("sidecarcim_top_ff_par", "sidecarcim_top", "dcim"),
    "sidecarcim_top_ff_pipe": ("sidecarcim_top_ff_pipe", "sidecarcim_top", "dcim5"),
    "sidecarcim_top_ff_pipe_s3": ("sidecarcim_top_ff_pipe_s3", "sidecarcim_top", "dcim5"),
    "dcim_w7a4_ff": ("dcim_w7a4_ff", "dcim_core", "dcim"),
    "dcim_w4a8_ff": ("dcim_w4a8_ff", "dcim_core", "dcim8"),
    "dcim_w8a4_ff": ("dcim_w8a4_ff", "dcim_core", "dcim"),
    "dcim_w6a4_ff": ("dcim_w6a4_ff", "dcim_core", "dcim"),
    "dcim_8bit_ff": ("dcim_8bit_ff", "dcim_8bit", "dcim8"),
    "mac_baseline": ("mac_baseline", "mac_baseline", "mac"),
}


def spec_val(key):
    txt = (ROOT / "spec" / "spec.yaml").read_text()
    m = re.search(r"^\s*%s:\s*(\d+)" % key, txt, re.M)
    return int(m.group(1))


N_IN, N_OUT = spec_val("n_inputs"), spec_val("n_outputs")
ABITS = spec_val("act_bits")
PERIOD_NS = spec_val("clock_period_ns")
# compute cycles per dot product (start edge -> valid): dcim ABITS, mac N_IN*N_OUT.
# Power comes from the busy-window VCD (compute cycles only, no weight load / idle).
CYC = {"dcim5": ABITS + 1, "dcim": ABITS, "dcim8": 8, "mac": N_IN * N_OUT}


def latest_run(fd):
    runs = sorted((FLOW / fd / "runs").glob("RUN_*"))
    runs = [r for r in runs if (r / "final" / "metrics.json").exists()]
    return runs[-1] if runs else None


def parse_power(rpt):
    """Total row of OpenSTA report_power -> dict in mW."""
    for line in rpt.read_text().splitlines():
        if line.startswith("Total"):
            v = [float(x) for x in re.findall(r"[-+]?\d+\.\d+e[-+]\d+|[-+]?\d*\.\d+", line)[:4]]
            return {k: x * 1e3 for k, x in zip(("internal", "switching", "leakage", "total"), v)}
    return None


def r4(x):
    return None if x is None else round(x, 3)


def main():
    over = dict(a.split("=", 1) for a in sys.argv[1:])
    rows = []
    for name, (fd, top, kind) in DESIGNS.items():
        run = Path(over[name]) if name in over else latest_run(fd)
        if run is None:
            print("skip", name, "(no finished run)")
            continue
        if float(json.loads((run / "resolved.json").read_text())["CLOCK_PERIOD"]) != PERIOD_NS:
            print("skip", name, "(run clock != spec)")
            continue
        m = json.loads((run / "final" / "metrics.json").read_text())
        ws = m["timing__setup__ws"]            # worst over all corners, signed (+ = met)
        ws_tt = m.get("timing__setup__ws__corner:nom_tt_025C_1v80")
        pw, src = None, "none"
        for tag in ("real", "vcd", "vectorless"):
            f = run / ("power_%s.rpt" % tag)
            if f.exists():
                pw, src = parse_power(f), tag
                break
        cyc = CYC[kind]
        p_mw = pw["total"] if pw else None
        e_dot = p_mw * cyc * PERIOD_NS if pw else None     # mW * ns = pJ
        row = {
            "design": name,
            "area_um2": m["design__instance__area__stdcell"],
            "cell_count": m["design__instance__count__stdcell"],
            "fmax_mhz_est": round(1000.0 / (PERIOD_NS - ws), 2),   # worst corner (ss 100C 1.60V)
            "power_mw_est": None if p_mw is None else float("%.4g" % p_mw),   # 4 significant figures; energy uses the unrounded value
            "energy_per_dot_pj_est": r4(e_dot),
            "energy_per_mac_fj_est": r4(e_dot * 1000.0 / (N_IN * N_OUT)) if pw else None,
            "cycles_per_dot": cyc,
            "drc": m["magic__drc_error__count"] + m["klayout__drc_error__count"],
            "lvs": m["design__lvs_error__count"],
            "wns_ns": round(ws, 4),
            "run_dir": str(run.relative_to(ROOT)),
            "activity_source": src,
            # extras
            "core_area_um2": m["design__core__area"],
            "die_area_um2": m["design__die__area"],
            "setup_ws_nom_tt_ns": round(ws_tt, 4),
            "fmax_mhz_est_tt": round(1000.0 / (PERIOD_NS - ws_tt), 2),
            "hold_ws_ns": round(m["timing__hold__ws"], 4),
            "setup_vio_count": m["timing__setup_vio__count"],
            "hold_vio_count": m["timing__hold_vio__count"],
            "clock_period_ns": PERIOD_NS,
        }
        rows.append(row)
        # GDS + render
        (OUT / "gds").mkdir(parents=True, exist_ok=True)
        gds = run / "final" / "gds" / (top + ".gds")
        if gds.exists():
            with open(gds, "rb") as fi, gzip.open(OUT / "gds" / (name + ".gds.gz"), "wb") as fo:
                shutil.copyfileobj(fi, fo)
        png = run / "final" / "render" / (top + ".png")
        if png.exists():
            shutil.copy2(png, OUT / "gds" / (name + ".png"))
    if not rows:
        sys.exit("no runs found")
    cols = list(rows[0])
    with open(OUT / "ppa.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    print("wrote", OUT / "ppa.csv")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
