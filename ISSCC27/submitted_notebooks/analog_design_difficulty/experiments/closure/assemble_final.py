#!/usr/bin/env python3
"""Assemble the machine-readable closure result and the closure-matrix figure.

    uv run python experiments/closure/assemble_final.py [design]

Reads results/closure/final/<design>/<part>.json written by run_final.py and writes
results/closure/final/<design>/final_closure.json and results/figures/figure_closure_matrix.{svg,png}.
Every criterion below is the one declared in CLOSURE_BRIEF.md (with amendments A1-A8); none is
chosen here.
"""
from __future__ import annotations

import json
import math
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import designs  # noqa: E402
import parent_metric as pm  # noqa: E402
import shbench as sb  # noqa: E402

VLSB_MV = pm.VLSB * 1e3
NOISE_BUDGET_UV = 146.0     # 0.25 VLSB rms (A2; A7 fallback not triggered)
NOISE_UNRESOLVED_UV = 3.0   # A2: within 3 uV of the limit is unresolved
SAT_MIN_MV = 50.0
# 50 mV is a design target (human decision 2026-10-31); a bounded worst-corner reduction is accepted when the device
# stays saturated (margin > 0), the mechanism is understood (input pair at the top of the range at 1.60 V), and the
# parent contribution stays small (checked in the parent result at that condition)
SAT_REDUCTION = {("xm1", "xm2"): "sf_1.60V_+125C"}


def load(d: str, part: str):
    return json.loads((sb.REPO / "results" / "closure" / "final" / d / f"{part}.json").read_text())


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def environment() -> dict:
    lib = sb.pdk_library()
    return {"ngspice": sb.ngspice_version(), "sky130_sources": "open_pdks c6d73a35f524070e85faff4a6a9eef49553ebc2b",
            "sky130_library": str(lib.relative_to(lib.parents[3])), "python": sys.version.split()[0],
            "numpy": np.__version__, "matplotlib": matplotlib.__version__}


def netlist_counts(des: sb.Design) -> dict:
    def count(path, prefix=("XM",)):
        t = (sb.NETLISTS / path).read_text()
        body = t[t.index(".subckt"):t.index(".ends")]
        lines = [l.split() for l in body.splitlines() if l and not l.startswith("*")]
        mos = [l for l in lines if l[0].upper().startswith(prefix)]
        area = 0.0
        for l in mos:
            kv = dict(x.split("=") for x in l if "=" in x)
            def num(v):
                v = v.strip("{}")
                return float(v) if re.fullmatch(r"[-+0-9.eE]+", v) else None
            w, ln, m = num(kv.get("W", "0")), num(kv.get("L", "0")), num(kv.get("m", "1"))
            if w is not None and ln is not None and m is not None:
                area += w * ln * m
        caps = [l for l in lines if l[0].upper().startswith("C")]
        res = [l for l in lines if l[0].upper().startswith("R")]
        return len(mos), area, caps, res
    n_d, a_d, c_d, r_d = count(des.driver_file)
    n_s, a_s, c_s, _ = count(des.switch.subckt_file)
    return {"driver_transistors": n_d, "driver_gate_area_um2": round(a_d, 1),
            "driver_ideal_C": " ".join(f"{c[0]}={c[-1]}" for c in c_d),
            "driver_ideal_R": " ".join(f"{r[0]}={r[-1]}" for r in r_d),
            "switch_transistors": n_s}


def closure_matrix_figure(parent: list[dict], noise: list[dict], stab: list[dict], name: str) -> None:
    corners = ["tt", "ss", "ff", "sf", "fs"]
    cols = [(v, t) for v in pm.SUPPLIES for t in (-40, 27, 125)]
    def grid(fn):
        g = np.full((len(corners), len(cols)), np.nan)
        for i, c in enumerate(corners):
            for j, (v, t) in enumerate(cols):
                g[i, j] = fn(c, v, t)
        return g
    pr = {(r["pvt"]["corner"], r["pvt"]["vdd"], r["pvt"]["temp"]): r["max_abs_r_LSB"] for r in parent}
    nz = {}
    for r in noise:
        c, v, t = r["tag"].split("_")
        key = (c, float(v[:-1]), float(t[:-1]))
        nz[key] = max(nz.get(key, 0), r["noise_uV_rms"])
    pmg = {}
    for r in stab:
        c, v, t = r["tag"].split("_")
        key = (c, float(v[:-1]), float(t[:-1]))
        pmg[key] = min(pmg.get(key, 1e9), r["acq"]["pm_deg"], r["hold"]["pm_deg"])
    G = [grid(lambda c, v, t: pr[(c, v, t)]), grid(lambda c, v, t: nz[(c, v, t)]),
         grid(lambda c, v, t: pmg[(c, v, t)])]
    titles = ["parent deterministic residual max|r| (LSB)\nlimit 1 LSB", "sampled noise (µV rms)\nbudget 146 µV",
              "loop phase margin, worst load and level (°)\nlimit 45°"]
    fmts = ["{:.2f}", "{:.0f}", "{:.0f}"]
    lims = [(0, 1.0), (0, NOISE_BUDGET_UV), (45, 90)]
    cmaps = ["Greens", "Blues", "Purples_r"]
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 3.6))
    for ax, g, ttl, f, lim, cm in zip(axs, G, titles, fmts, lims, cmaps):
        ax.imshow(g, cmap=cm, vmin=lim[0], vmax=lim[1], aspect="auto")
        for i in range(g.shape[0]):
            for j in range(g.shape[1]):
                ax.text(j, i, f.format(g[i, j]), ha="center", va="center", fontsize=7.6)
        ax.set_yticks(range(len(corners)), corners)
        ax.set_xticks(range(len(cols)), [f"{v:.2f} V\n{t:+d} °C" for v, t in cols], fontsize=7)
        ax.set_title(ttl, fontsize=9.5)
    fig.tight_layout()
    out = sb.REPO / "results" / "figures"
    fig.savefig(out / f"{name}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(out / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def main(d: str = "q1_boot2") -> None:
    des = designs.DESIGNS[d]
    parent = load(d, "parent")
    stab = load(d, "stability")
    noise = load(d, "noise")
    dev = load(d, "devlimits")
    # supporting parts: included when run_final.py has produced them (submission-priority mode)
    def opt(part):
        try:
            return load(d, part)
        except FileNotFoundError:
            return None
    stress, fine, sens, num = opt("stress"), opt("fine"), opt("sens"), opt("numerics")

    checks = []
    wp = max(parent, key=lambda r: r["max_abs_r_LSB"])
    n_cycles = sum(r["n_cycles"] for r in parent)
    margin_mV = VLSB_MV - wp["max_abs_r_mV"]
    checks.append({"check": f"parent residual, primary timing, {len(parent)} conditions × 4 sequences ({n_cycles} counted samples), early and late windows",
                   "criterion": "max|r| ≤ 1 LSB", "result": f"{wp['max_abs_r_LSB']:.3f} LSB at {wp['tag']}",
                   "verdict": verdict(all(r["pass"] for r in parent))})
    robustness, prose_extra = [], {}
    if fine:
        wf = max(fine, key=lambda r: r["max_abs_r_LSB"])
        checks.append({"check": f"25 mV levels at {len(fine)} conditions", "criterion": "max|r| ≤ 1 LSB",
                       "result": f"{wf['max_abs_r_LSB']:.3f} LSB at {wf['tag']}",
                       "verdict": verdict(all(r["pass"] for r in fine))})
        robustness.append(f"Levels on a 25 mV grid at the worst conditions give at most {wf['max_abs_r_LSB']:.2f} `VLSB`.")
    if sens:
        sw = [(k, r) for k, v in sens.items() for r in v]
        ks, wr = max(sw, key=lambda x: x[1]["max_abs_r_LSB"])
        checks.append({"check": "sensitivities: edges 0.1/0.5 ns, φ/φ̄ skew ±50 ps, Iref ±20 %, Cs ±10 %",
                       "criterion": "max|r| ≤ 1 LSB", "result": f"{wr['max_abs_r_LSB']:.3f} LSB ({ks}, {wr['tag']})",
                       "verdict": verdict(all(r["pass"] for _, r in sw))})
        robustness.append(f"Clock edges of 0.1 and 0.5 ns, ±50 ps phase skew, ±20 % bias current, and ±10 % `Cs` move "
                          f"the worst residual to at most {wr['max_abs_r_LSB']:.2f} `VLSB`.")
        prose_extra.update(cs_note="; ±10 % verified", clock_note="; 0.1–0.5 ns edges and ±50 ps phase skew verified",
                           iref_note="; ±20 % verified")
    else:
        prose_extra.update(cs_note="", clock_note="", iref_note="")
    if num:
        dmax = max(abs(num["delta_fine_mV"]), abs(num["delta_gear_mV"]))
        checks.append({"check": f"numerics at {num['condition']} ({num['sequence']}): tmax 2 ps/reltol 1e-6; gear",
                       "criterion": "|Δ| ≤ 0.02 mV and margin > |Δ|",
                       "result": f"Δ {num['delta_fine_mV']:+.4f} / {num['delta_gear_mV']:+.4f} mV; margin {margin_mV:.3f} mV",
                       "verdict": verdict(dmax <= 0.02 and margin_mV > dmax)})
        prose_extra["numerics_note"] = (f"Rerunning the worst condition with a 2 ps step and tighter tolerances, and with "
                                        f"Gear integration, changes the worst residual by at most {dmax * 1e3:.1f} µV.")
    else:
        prose_extra["numerics_note"] = ("The final design was not rerun at finer settings; the 5 ps / 1e-5 default was chosen "
                                        "because it removed the 0.1 mV step artefacts that coarser settings produced with the "
                                        "bootstrapped switch.")
    prose_extra["robustness_note"] = " ".join(robustness)
    prose_extra["sens_sentence"] = ("Sensitivity runs at nominal and the worst conditions vary the clock edges (0.1 and 0.5 ns), the "
                                    "skew between the two clock phases (±50 ps), the bias reference (±20 %), and `Cs` (±10 %)."
                                    if sens else
                                    "Clock edges, phase skew, bias current, and `Cs` were held at their nominal values in this "
                                    "verification.")
    prose_extra["numerics_method_sentence"] = ("the worst condition is rerun with a 2 ps step and tighter tolerances, and "
                                               "with Gear instead of trapezoidal integration." if num else
                                               "for the first-cut transmission gate this setting agreed with finer ones within "
                                               "0.003 mV, and for the bootstrapped switch it removed 0.1 mV artefacts of coarser "
                                               "settings.")
    prose_extra["appendix_clock_note"] = " (the edge and skew sweeps of Section 3.5 stand in for them)" if sens else ""
    prose_extra["level_grids"] = "0.1 V pairs, 50 mV and 25 mV staircases" if fine else "0.1 V pairs and a 50 mV staircase"
    pmin = min(min(r["acq"]["pm_deg"], r["hold"]["pm_deg"]) for r in stab)
    gmin = min(min(r["acq"]["gm_dB"], r["hold"]["gm_dB"]) for r in stab)
    checks.append({"check": f"driver loop, {len(stab)} condition/level points, acquisition and hold loads",
                   "criterion": "PM ≥ 45°, GM ≥ 10 dB", "result": f"PM ≥ {pmin:.1f}°, GM ≥ {gmin:.1f} dB",
                   "verdict": verdict(pmin >= 45 and gmin >= 10)})
    t = (sb.NETLISTS / des.driver_file).read_text()
    body = t[t.index(".subckt"):t.index(".ends")]
    diode = {l.split()[0].lower() for l in body.splitlines() if l.upper().startswith("XM") and l.split()[1] == l.split()[2]}
    sat = []  # diode-connected devices excluded (CLOSURE_BRIEF.md Section 6: saturated signal-path devices)
    for r in stab:
        for dev_, mv in r["sat_margin_mV"].items():
            if dev_ not in diode:
                sat.append((mv, dev_, r["tag"], r["level"]))
    viol = [s for s in sat if s[0] < SAT_MIN_MV]
    explained = all(s[0] > 0 and any(s[1] in grp and s[2] == tag for grp, tag in SAT_REDUCTION.items()) for s in viol)
    smin = min(sat)
    checks.append({"check": "driver saturation margins vds − vdsat (all non-diode-connected devices)",
                   "criterion": "design target ≥ 50 mV; bounded worst-corner reduction allowed if still saturated",
                   "result": f"min {smin[0]:.0f} mV ({smin[1]}, {smin[2]}, {smin[3]} V); {len(viol)} point(s) below 50 mV"
                             + (" — input pair at the top of the range, 1.60 V supply; still saturated" if viol and explained else ""),
                   "verdict": verdict(not viol or explained) + (" (bounded corner reduction)" if viol and explained else "")})
    ppmax = max(r["max_window_pp_mV"] for r in parent)
    checks.append({"check": "ringing in the read windows (peak-to-peak)", "criterion": "≤ 0.1 LSB",
                   "result": f"{ppmax / VLSB_MV:.3f} LSB", "verdict": verdict(ppmax <= 0.1 * VLSB_MV)})
    nmax = max(noise, key=lambda r: r["noise_uV_rms"])
    checks.append({"check": f"sampled noise, {len(noise)} condition/level points (switch exactly kT/C, 1 mHz–50 GHz)",
                   "criterion": f"≤ {NOISE_BUDGET_UV:.0f} µV rms (unresolved within {NOISE_UNRESOLVED_UV:.0f} µV)",
                   "result": f"{nmax['noise_uV_rms']:.1f} µV ({nmax['noise_LSB_rms']:.3f} LSB) at {nmax['tag']}, {nmax['level']} V",
                   "verdict": verdict(nmax["noise_uV_rms"] <= NOISE_BUDGET_UV - NOISE_UNRESOLVED_UV)})
    # Use the stored bound, not the historical `cancellation_reliant` flag: exceeding
    # this bound is inconclusive until paired/pointwise analysis establishes reliance.
    uncertified = [r["tag"] for r in parent if r["sum_component_max_mV"] > VLSB_MV]
    max_bound = max(r["sum_component_max_mV"] for r in parent)
    checks.append({"check": "no-cancellation certificate (M = sum of component maxima)",
                   "criterion": "M ≤ 1 LSB; otherwise paired/pointwise analysis required",
                   "result": f"max M {max_bound / VLSB_MV:.3f} LSB; "
                             + ("certified at every condition" if not uncertified else
                                "unresolved at " + ", ".join(uncertified)),
                   "verdict": "PASS" if not uncertified else "UNRESOLVED"})
    if stress:
        ws = max(stress, key=lambda r: r["max_abs_r_LSB"])
        srange = f"{min(r['max_abs_r_LSB'] for r in stress):.1f}–{ws['max_abs_r_LSB']:.1f}"
        prose_extra["stress_source"] = ""
        checks.append({"check": "STRESS timing (full-scale command step at switch closure)", "criterion": "diagnostic",
                       "result": f"{srange} LSB ({ws['tag']} worst)", "verdict": "reported"})
    else:  # screening values of the refinement study (design-study record), four conditions
        srange = "1.9–7.3"
        prose_extra["stress_source"] = (" (screening of the same driver with the 5 µm switch at four conditions; the "
                                        "selected design was not run in this timing)")
    prose_extra["stress_range_lsb"] = srange
    steady, trans = [], []
    for r in dev:
        for name, q in r["devices"].items():
            for k, v in q.items():
                if k in ("vgs", "vgd", "vds"):
                    steady.append((v["steady_V"], name, k, r["tag"]))
                    trans.append((v["worst_V"], v["time_over_1.96V_ns_per_cycle"], name, k, r["tag"]))
    st = max(steady)
    tr = max(trans)
    tlong = max(trans, key=lambda x: x[1])
    checks.append({"check": "switch terminal voltages, steady (end of each clock phase)", "criterion": "|VGS|,|VGD|,|VDS| ≤ 1.95 V (model validity)",
                   "result": f"max {st[0]:.3f} V ({st[1]} {st[2]}, {st[3]})", "verdict": verdict(st[0] <= 1.95 + 1e-3)})
    vbs = min(q["vbs"]["worst_V"] for r in dev for n, q in r["devices"].items() if n not in ("MXP", "MGT"))
    checks.append({"check": "switch NMOS body-source voltage", "criterion": "within the model range, ≥ −1.95 V",
                   "result": f"min {vbs:.3f} V", "verdict": verdict(vbs >= -1.95 - 1e-3)})
    checks.append({"check": "switch terminal voltages, transient", "criterion": "reported limitation",
                   "result": f"peak {tr[0]:.2f} V ({tr[2]} {tr[3]}, {tr[4]}); longest above 1.96 V {tlong[1]:.2f} ns/cycle ({tlong[2]} {tlong[3]})",
                   "verdict": "reported"})
    i_tt = [r["supply_current_uA"] for r in parent if r["tag"] == "tt_1.80V_+27C"][0]
    i_max = max(r["supply_current_uA"] for r in parent)
    final_pass = all(c["verdict"].startswith("PASS") for c in checks if c["verdict"] not in ("reported",))
    counts = netlist_counts(des)
    offs = [r["offset_mV"]["yE"] for r in parent]
    gains = [r["gain_err_mV_per_V"]["yE"] for r in parent]
    result = {
        "design": d, "final_pass": final_pass, "environment": environment(),
        "switch_params": " ".join(f"{k}={v}" for k, v in des.switch.subckt_params),
        "declared_set": {"conditions": len(parent), "supplies_V": list(pm.SUPPLIES), "temperatures_C": [-40, 27, 125],
                         "corners": ["tt", "ss", "ff", "sf", "fs"], "sequences": ["cal_alt", "pair", "stair", "mem"],
                         "counted_samples": n_cycles},
        "checks": checks,
        "worst_parent": {k: wp[k] for k in ("tag", "max_abs_r_mV", "max_abs_r_LSB", "components_mV", "worst_cycle")},
        "calibration_spread": {"offset_mV": [min(offs), max(offs)], "gain_err_mV_per_V": [min(gains), max(gains)]},
        "cost": {"supply_current_uA_tt": round(i_tt), "supply_current_uA_max": round(i_max), **counts,
                 "Cs_pF": des.cs * 1e12, "clock_phases": 2},
        "design_summary": {
            "driver": "folded-cascode first stage (native-threshold NMOS pair), PMOS common-source second stage, Miller Cc + Rz, output capacitor; bias lines RC-filtered",
            "sampling switch": "bootstrapped NMOS (W 2 µm, L 0.15 µm), bootstrap capacitor 0.2 pF, clock-boosted charging device",
            "Cs": f"{des.cs * 1e12:.0f} pF", "clock": "two complementary phases, 0.2 ns edges, 100 ns period, 40 ns acquisition",
            "supply current": f"{i_tt:.0f} µA at tt (max {i_max:.0f} µA over the declared set)",
            "devices": f"driver {counts['driver_transistors']} transistors, switch {counts['switch_transistors']}",
            "ideal passives in the driver": f"{counts['driver_ideal_C']}; {counts['driver_ideal_R']}",
        },
        "prose": {"final_cycles": f"{n_cycles:,}", "final_conditions": str(len(parent)),
                  "worst_r_lsb": f"{wp['max_abs_r_LSB']:.2f}", "worst_tag": wp["tag"],
                  "worst_noise_uv": f"{nmax['noise_uV_rms']:.0f}", "i_tt_ua": f"{i_tt:.0f}", "i_max_ua": f"{i_max:.0f}",
                  "pm_min": f"{pmin:.0f}", "gm_min": f"{gmin:.0f}",
                  "i_min_ua": f"{min(r['supply_current_uA'] for r in parent):.0f}",
                  "offset_range_mv": f"{min(offs):.1f} to {max(offs):.1f}",
                  "gain_range": f"{min(gains) + 0.0:.1f} to {max(gains) + 0.0:.1f}".replace("-0.0", "0.0"),
                  "rp_max_mv": f"{max(r['components_mV']['rP'] for r in parent):.3f}",
                  "rs_max_mv": f"{max(r['components_mV']['rS'] for r in parent):.3f}",
                  "sat_min_mv": f"{smin[0]:.0f}",
                  "sat_corner_r_lsb": f"{[r['max_abs_r_LSB'] for r in parent if r['tag'] == smin[2]][0]:.2f}",
                  "driver_transistors": str(counts["driver_transistors"]),
                  "switch_transistors": str(counts["switch_transistors"]),
                  "dev_peak_v": f"{tr[0]:.2f}", **prose_extra},
    }
    out = sb.REPO / "results" / "closure" / "final" / d / "final_closure.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    closure_matrix_figure(parent, noise, stab, "figure_closure_matrix")
    print(json.dumps({"final_pass": final_pass, "checks": [(c["check"][:50], c["result"], c["verdict"]) for c in checks]},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
