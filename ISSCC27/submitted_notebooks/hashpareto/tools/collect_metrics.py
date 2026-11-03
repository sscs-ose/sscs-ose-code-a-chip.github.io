#!/usr/bin/env python3
"""Harvest LibreLane PPA metrics for every finished variant run.

Scans flow/variants/u*/runs/<tag>/final/metrics.json plus the post-PnR STA
logs and writes one CSV row per finished run to results/metrics.csv.
Usage: python3 tools/collect_metrics.py [out.csv]
"""
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANTS = os.path.join(ROOT, "flow", "variants")

TOP = {
    "area_stdcell_um2": "design__instance__area__stdcell",
    "cells_stdcell": "design__instance__count__stdcell",
    "cells_total": "design__instance__count",
    "die_um2": "design__die__area",
    "utilization": "design__instance__utilization",
    "power_W": "power__total",
    "power_internal_W": "power__internal__total",
    "power_switching_W": "power__switching__total",
    "leakage_W": "power__leakage__total",
    "setup_wns_ns": "timing__setup__wns",
    "setup_ws_ns": "timing__setup__ws",
    "hold_wns_ns": "timing__hold__wns",
    "clock_skew_setup_ns": "clock__skew__worst_setup",
    "clock_skew_hold_ns": "clock__skew__worst_hold",
    "route_wirelength_um": "route__wirelength",
    "drc_errors": "route__drc_errors",
    "antenna_violations": "route__antenna_violation__count",
    "design_violations": "design__violations",
    "max_fanout_viol": "design__max_fanout_violation__count",
    "max_slew_viol": "design__max_slew_violation__count",
    "max_cap_viol": "design__max_cap_violation__count",
}

PRE = "timing__setup__wns__corner:"


def get_clock_period(cfg_path):
    txt = open(cfg_path, "r").read()
    m = re.search(r"CLOCK_PERIOD:\s*([0-9.]+)", txt)
    return float(m.group(1)) if m else None


def run_clock_period(run_dir, fallback):
    """Prefer the run's own resolved.json CLOCK_PERIOD, else variant config."""
    for cand in (os.path.join(run_dir, "resolved.json"),):
        if os.path.exists(cand):
            txt = open(cand, "r").read()
            m = re.search(r'"CLOCK_PERIOD":\s*([0-9.]+)', txt)
            if m:
                return float(m.group(1))
    return fallback


def sta_timing(run_dir):
    """Return {corner: (period_min_ns, fmax_MHz)} from post-PnR STA logs."""
    found = {}
    for log in glob.glob(os.path.join(run_dir, "*stapostpnr*", "*", "sta.log")):
        corner = os.path.basename(os.path.dirname(log))
        pm = fm = None
        with open(log, "r", errors="ignore") as f:
            for line in f:
                m = re.search(r"period_min\s*=\s*([0-9.]+)", line)
                if m:
                    pm = float(m.group(1))
                g = re.search(r"fmax\s*=\s*([0-9.]+)", line)
                if g:
                    fm = float(g.group(1))
        if pm is not None:
            found[corner] = (pm, fm)
    return found


def main():
    out_csv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "results", "metrics.csv")
    rows = []
    for vdir in sorted(glob.glob(os.path.join(VARIANTS, "u*"))):
        unroll = int(re.search(r"u(\d+)$", os.path.basename(vdir)).group(1))
        for run_dir in sorted(glob.glob(os.path.join(vdir, "runs", "*"))):
            met = os.path.join(run_dir, "final", "metrics.json")
            if not os.path.exists(met):
                continue
            d = json.load(open(met, "r"))
            if not d.get("design__instance__count__stdcell"):
                continue
            cfg = os.path.join(vdir, "config.yaml")
            period = run_clock_period(run_dir, get_clock_period(cfg))
            sta = sta_timing(run_dir)
            pm_ss, fm_ss = sta.get("nom_ss_100C_1v60", (None, None))
            pm_tt, fm_tt = sta.get("nom_tt_025C_1v80", (None, None))
            row = {
                "unroll": unroll,
                "run": os.path.basename(run_dir),
                "clock_period_ns": period,
                "gds_bytes": "",
            }
            for k, key in TOP.items():
                v = d.get(key)
                row[k] = "" if v is None else v
            for cn in ("nom_ss_100C_1v60", "nom_tt_025C_1v80"):
                row["wns_" + cn.replace("C_1v", "_1v")] = d.get(PRE + cn, "")
            # Per-corner worst setup slack (WS) -- survives slimming, unlike the
            # sta.log files, and carries actual margin information (A5).
            ws_all = {
                k.split("__corner:")[1]: v
                for k, v in d.items()
                if k.startswith("timing__setup__ws__corner:")
            }
            if ws_all:
                wc = min(ws_all, key=ws_all.get)
                row["setup_ws_worst_ns"] = round(ws_all[wc], 4)
                row["setup_ws_worst_corner"] = wc
                for cn in ("nom_tt_025C_1v80", "nom_ss_100C_1v60"):
                    if cn in ws_all:
                        row["setup_ws_" + cn.replace("C_1v", "_1v")] = round(ws_all[cn], 4)
                if period and (period - ws_all[wc]) > 0:
                    row["fmax_est_worst_mhz"] = round(1000.0 / (period - ws_all[wc]), 2)
                if period and "nom_tt_025C_1v80" in ws_all and (period - ws_all["nom_tt_025C_1v80"]) > 0:
                    row["fmax_est_tt_mhz"] = round(1000.0 / (period - ws_all["nom_tt_025C_1v80"]), 2)
            else:
                row["setup_ws_worst_ns"] = ""
                row["setup_ws_worst_corner"] = ""
            row["sta_period_min_nom_ss_ns"] = pm_ss if pm_ss is not None else ""
            row["sta_period_min_nom_tt_ns"] = pm_tt if pm_tt is not None else ""
            row["sta_fmax_nom_ss_mhz"] = fm_ss if fm_ss is not None else ""
            row["sta_fmax_nom_tt_mhz"] = fm_tt if fm_tt is not None else ""
            gds = glob.glob(os.path.join(run_dir, "final", "gds", "*.gds"))
            if gds:
                row["gds_bytes"] = os.path.getsize(gds[0])
            # A6: per-corner slew/cap/fanout so the notebook can disclose where
            # they occur (LibreLane's own repair does not clear ss/ff extremes).
            for kind in ("max_slew_violation", "max_cap_violation", "max_fanout_violation"):
                per = {
                    k.split("__corner:")[1]: v
                    for k, v in d.items()
                    if k.startswith(f"design__{kind}__count__corner:")
                }
                if per:
                    mc = max(per, key=per.get)
                    row[f"{kind}_worst_corner"] = mc
                    row[f"{kind}_worst_val"] = per[mc]
                    row[f"{kind}_nom_tt_val"] = per.get("nom_tt_025C_1v80", "")
            rows.append(row)

    for r in rows:
        print("u{r[unroll]} [{r[run]}]: {r[cells_stdcell]} cells, "
              "area {r[area_stdcell_um2]} um2, power {r[power_W]} W, "
              "wns {r[setup_wns_ns]} ns @ {r[clock_period_ns]} ns"
              .format(r=r))
    if rows:
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        cols = list(rows[0].keys())
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print("wrote {} row(s) -> {}".format(len(rows), out_csv))
    else:
        print("no finished runs found")


if __name__ == "__main__":
    main()