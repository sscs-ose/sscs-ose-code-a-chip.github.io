"""table_clockgating.{csv,md}: each design before / after clock gating.

Before = results/ppa_nocg.csv (hold-mux storage, CLK_GATE=0 runs), after =
results/ppa.csv (CLK_GATE=1). Area, real-activity energy per 32x8 MVM and
power are read from those CSVs; hold-buffer (dlygate*), mux2 and ICG
(dlclkp) counts are counted in each run's final netlist when the run
directory exists, otherwise kept from the saved CSV (CI copies have no run
directories). Flow settings come from each run's resolved.json. Gating-check
slack: results/cg_slack.csv. All values are post-layout estimates.
"""
import csv
import glob
import json
import os
import re
from collections import Counter

import plot_common as pc
import ppa_data as pd

DESIGNS = [("4-bit DCIM (FF)", "dcim_core_ff"),
           ("SidecarCIM bit-serial (FF)", "sidecarcim_top_ff"),
           ("SidecarCIM parallel (FF)", "sidecarcim_top_ff_par"),
           ("8-bit DCIM (FF)", "dcim_8bit_ff"),
           ("MAC baseline", "mac_baseline")]
CSV = os.path.join(pc.HERE, "table_clockgating.csv")
CELL = re.compile(r"^\s*sky130_fd_sc_hd__(\w+?)_\d+\s", re.M)
# control run: gated dcim_core_ff with the old fanout limit (10)
CONTROL = os.path.join("flow", "dcim_core_ff", "runs", "old_cg_trial_fanout10")


def ppa_rows(name):
    out = {}
    for r in pd.load_csv(name):
        out[r["design"]] = {k: (float(v) if re.match(r"^-?[\d.]+$", v)
                                else v) for k, v in r.items()}
    return out


def find_run(design, run_dir, area):
    """run_dir if present, else the run of that design whose final
    metrics.json has the same std-cell area (renamed run directories)."""
    if os.path.isdir(os.path.join(pc.ROOT, run_dir)):
        return run_dir
    for r in sorted(glob.glob(os.path.join(pc.ROOT, "flow", design, "runs",
                                           "*"))):
        mt = os.path.join(r, "final", "metrics.json")
        if os.path.exists(mt):
            a = json.load(open(mt))["design__instance__area__stdcell"]
            if abs(a - area) < 1.0:
                return os.path.relpath(r, pc.ROOT)
    return None


def cells(run):
    nl = glob.glob(os.path.join(pc.ROOT, run, "final", "nl", "*.nl.v"))
    if not nl:
        return None
    return Counter(CELL.findall(open(nl[0]).read()))


def setting(run, key):
    path = os.path.join(pc.ROOT, run, "resolved.json")
    if not os.path.exists(path):
        return ""
    return json.load(open(path)).get(key, "")


def energy_pj(power_mw, p):
    # P x clock period x cycles per MVM (same rule as ppa.csv)
    return power_mw * p["clock_period_ns"] * p["cycles_per_dot"]


def report_total_mw(path):
    for line in open(path):
        if line.startswith("Total"):
            return float(line.split()[4]) * 1e3
    return None


# The ungated 4-bit run and the fanout-10 control were measured with the
# naive W4A4 vectors (real_layer.npz); ppa.csv now holds the W4A4+mig+wclip
# energy. The before / after comparison uses the gated run's naive-vector
# report (power_real_nomig.rpt) so both sides see the same stimulus.
SAME_STIM = {"dcim_core_ff": "power_real_nomig.rpt"}


def same_stim(d, a):
    if d not in SAME_STIM:
        return a
    rp = os.path.join(pc.ROOT, a["run_dir"], SAME_STIM[d])
    a = dict(a)
    a["power_mw_est"] = float("%.4g" % report_total_mw(rp))
    a["energy_per_dot_pj_est"] = round(energy_pj(report_total_mw(rp), a), 3)
    return a


def main():
    before, after = ppa_rows("ppa_nocg.csv"), ppa_rows("ppa.csv")
    after["dcim_core_ff"] = same_stim("dcim_core_ff", after["dcim_core_ff"])
    old = {}
    if os.path.exists(CSV):
        old = {r["design"]: r for r in csv.DictReader(open(CSV))}
    slack = {}
    for r in pd.load_csv("cg_slack.csv"):
        s = slack.setdefault(r["design"], [[], []])
        s[0].append(float(r["clock_gating_setup_slack_ns"]))
        s[1].append(float(r["clock_gating_hold_slack_ns"]))
    rows = []
    for label, d in DESIGNS:
        if d not in before or d not in after:
            continue
        b, a = before[d], after[d]
        r = {"circuit": label, "design": d,
             "area_nocg_um2": b["area_um2"], "area_cg_um2": a["area_um2"],
             "area_change_pct": round(100 * (a["area_um2"] / b["area_um2"]
                                             - 1), 2),
             "energy_nocg_pj": b["energy_per_dot_pj_est"],
             "energy_cg_pj": a["energy_per_dot_pj_est"],
             "energy_change_pct": round(100 * (a["energy_per_dot_pj_est"] /
                                               b["energy_per_dot_pj_est"]
                                               - 1), 2),
             "power_nocg_mw": b["power_mw_est"],
             "power_cg_mw": a["power_mw_est"],
             "cells_nocg": int(b["cell_count"]),
             "cells_cg": int(a["cell_count"]),
             "wns_nocg_ns": b["wns_ns"], "wns_cg_ns": a["wns_ns"],
             "hold_ws_nocg_ns": b["hold_ws_ns"], "hold_ws_cg_ns": a["hold_ws_ns"]}
        for tag, row in (("nocg", b), ("cg", a)):
            run = find_run(d, row["run_dir"], row["area_um2"])
            cnt = cells(run) if run else None
            o = old.get(d, {})
            if cnt is None:
                for k in ("hold_buf", "mux2", "icg", "max_fanout"):
                    r["%s_%s" % (k, tag)] = o.get("%s_%s" % (k, tag), "")
                r["run_%s" % tag] = o.get("run_%s" % tag, row["run_dir"])
                continue
            r["hold_buf_%s" % tag] = sum(n for c, n in cnt.items()
                                         if c.startswith("dlygate"))
            r["mux2_%s" % tag] = sum(n for c, n in cnt.items()
                                     if c == "mux2")
            r["icg_%s" % tag] = sum(n for c, n in cnt.items()
                                    if c.startswith("dlclkp"))
            r["max_fanout_%s" % tag] = setting(run, "MAX_FANOUT_CONSTRAINT")
            r["run_%s" % tag] = run
        s = slack.get(d)
        r["cg_check_setup_min_ns"] = min(s[0]) if s else ""
        r["cg_check_hold_min_ns"] = min(s[1]) if s else ""
        rows.append(r)
    keys = list(rows[0].keys())
    with open(CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    from make_tables import md_table
    period = after[DESIGNS[0][1]]["clock_period_ns"]
    md = "# Clock gating: before / after per design (post-layout estimates)\n\n"
    md += "Generated by `results/make_clockgating.py`. Before = " \
          "`results/ppa_nocg.csv` (storage flip-flops hold their value " \
          "through a 2:1 mux), after = `results/ppa.csv` (one sky130 " \
          "dlclkp ICG per weight row / slot column; CLK_GATE=1). Both at " \
          "%g ns, SYNTH_STRATEGY DELAY 4. Energy = real GPT-2 activity per " \
          "32x8 MVM (256 MACs). Hold buffers = dlygate* cells, mux2 and " \
          "ICG counts from each run's final netlist. Gating-check slack = " \
          "worst over all corners in `results/cg_slack.csv`. The 4-bit " \
          "DCIM rows and the control run below use the naive W4A4 vectors " \
          "(`real_layer.npz`) on both sides, as the ungated run was " \
          "measured; its W4A4+mig+wclip energy is in `ppa.csv`.\n\n" % period
    head = ["circuit", "area before / after (um^2)", "area change",
            "energy/MVM before / after (pJ)", "energy change",
            "hold buffers before / after", "mux2 before / after", "ICGs",
            "gating check setup / hold (ns)"]

    def pair(r, k, fmt="%s"):
        v0, v1 = r[k + "_nocg"], r[k + "_cg"]
        f = (lambda v: "" if v == "" else fmt % float(v))
        return "%s / %s" % (f(v0), f(v1))
    md += md_table(head, [[
        r["circuit"],
        "%.0f / %.0f" % (float(r["area_nocg_um2"]), float(r["area_cg_um2"])),
        "%+.1f%%" % float(r["area_change_pct"]),
        "%.0f / %.0f" % (float(r["energy_nocg_pj"]),
                         float(r["energy_cg_pj"])),
        "%+.1f%%" % float(r["energy_change_pct"]),
        pair(r, "hold_buf", "%.0f"), pair(r, "mux2", "%.0f"),
        "" if r["icg_cg"] == "" else "%.0f" % float(r["icg_cg"]),
        "" if r["cg_check_setup_min_ns"] == "" else "%.2f / %.2f" % (
            float(r["cg_check_setup_min_ns"]),
            float(r["cg_check_hold_min_ns"]))] for r in rows])
    fo = sorted({str(r.get("max_fanout_nocg", "")) for r in rows})
    fn = sorted({str(r.get("max_fanout_cg", "")) for r in rows})
    md += "\nThe after runs also use the final shared " \
          "MAX_FANOUT_CONSTRAINT %s (before: %s), so each change is " \
          "clock gating plus that setting.\n" % ("/".join(fn), "/".join(fo))
    ctl = os.path.join(pc.ROOT, CONTROL)
    mt = os.path.join(ctl, "final", "metrics.json")
    rp = os.path.join(ctl, "power_real.rpt")
    if os.path.exists(mt) and os.path.exists(rp):
        a_ctl = json.load(open(mt))["design__instance__area__stdcell"]
        e_ctl = energy_pj(report_total_mw(rp), after["dcim_core_ff"])
        a0 = after["dcim_core_ff"]["area_um2"]
        e0 = after["dcim_core_ff"]["energy_per_dot_pj_est"]
        b0 = before["dcim_core_ff"]
        md += "A control run separates the two on the 4-bit DCIM: the gated " \
              "design with the old fanout limit %s (`%s`) has %.0f um^2 and " \
              "%.0f pJ/MVM, that is %+.1f%% area and %+.1f%% energy against " \
              "the ungated run, so the " \
              "fanout change alone moves the gated design by %+.1f%% area " \
              "and %+.1f%% energy.\n" % (
                  setting(CONTROL, "MAX_FANOUT_CONSTRAINT"), CONTROL, a_ctl,
                  e_ctl, 100 * (a_ctl / b0["area_um2"] - 1),
                  100 * (e_ctl / b0["energy_per_dot_pj_est"] - 1),
                  100 * (a0 / a_ctl - 1), 100 * (e0 / e_ctl - 1))
    with open(os.path.join(pc.HERE, "table_clockgating.md"), "w",
              encoding="utf8") as fh:
        fh.write(md)
    print("wrote table_clockgating")


if __name__ == "__main__":
    main()
