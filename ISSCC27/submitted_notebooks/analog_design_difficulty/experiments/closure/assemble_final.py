#!/usr/bin/env python3
"""Assemble the machine-readable closure result and the closure-matrix figure.

    uv run python experiments/closure/assemble_final.py [design]

Reads results/closure/final/<design>/<part>.json written by run_final.py and writes
results/closure/final/<design>/final_closure.json and the closure-matrix figure:
results/figures/figure_closure_matrix.{svg,png} for the selected design (designs.SELECTED, the default),
figure_closure_matrix_<design>.{svg,png} for any other design.
Every criterion below is the one declared in CLOSURE_BRIEF.md (with amendments A1-A9); none is
chosen here. Each check carries a role: "closure" (decides final_pass), "supporting" (a pre-registered
criterion that also decides final_pass once the check has been run; under A9 its absence does not block),
or "diagnostic" (reported, not pass/fail).
"""
from __future__ import annotations

import json
import math
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
import numpy as np  # noqa: E402

import designs  # noqa: E402
import parent_metric as pm  # noqa: E402
import shbench as sb  # noqa: E402

sys.path.insert(0, str(sb.REPO / "experiments" / "experiment_a" / "sky130"))
from figure_sketches import context_header  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "svg.hashsalt": "closure", "svg.fonttype": "path"})

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


def switch_summary(des: sb.Design) -> str:
    p = dict(des.switch.subckt_params)
    if des.switch.subckt_name == "sw_nvt":
        return (f"native thick-oxide NMOS (sky130_fd_pr__nfet_03v3_nvt, W {float(p['WS']) * int(p['MS']):g} µm, "
                f"L 0.5 µm), gate driven directly by the track clock; no bootstrap")
    return (f"bootstrapped NMOS (W {float(p['WS']) * int(p['MS']):g} µm, L 0.15 µm), bootstrap capacitor "
            f"{str(p['CB']).replace('p', ' pF')}, clock-boosted charging device")


SUPPORTING = ("25 mV levels", "sensitivities", "numerics")


def role(c: dict) -> str:
    """closure: decides final_pass; supporting: pre-registered criterion, decides final_pass when run (A9);
    diagnostic: reported only (A6 STRESS timing, A8 transient terminal-voltage peaks)."""
    if c["verdict"] == "reported":
        return "diagnostic"
    return "supporting" if c["check"].startswith(SUPPORTING) else "closure"


def closure_matrix_figure(parent: list[dict], noise: list[dict], stab: list[dict], des: sb.Design, wp: dict,
                          nmax: dict, name: str) -> None:
    """Figure 7: the three closure quantities per PVT condition in separate panels (different units; they never
    add), each with its limit and its worst condition marked."""
    corners = ["tt", "ss", "ff", "sf", "fs"]
    marks = {"tt": "o", "ss": "v", "ff": "^", "sf": "s", "fs": "D"}
    groups = [(v, t) for v in pm.SUPPLIES for t in (-40, 27, 125)]
    xpos = {(c, v, t): g * 6 + i for g, (v, t) in enumerate(groups) for i, c in enumerate(corners)}

    def key(tag):
        c, v, t = tag.split("_")
        return c, float(v[:-1]), float(t[:-1])
    pr = {key(r["tag"]): r["max_abs_r_LSB"] for r in parent}
    mb = {key(r["tag"]): r["sum_component_max_mV"] / VLSB_MV for r in parent}
    nz, pmg = {}, {}
    for r in noise:
        nz[key(r["tag"])] = max(nz.get(key(r["tag"]), 0), r["noise_uV_rms"])
    for r in stab:
        pmg[key(r["tag"])] = min(pmg.get(key(r["tag"]), 1e9), r["acq"]["pm_deg"], r["hold"]["pm_deg"])
    wpm = min(pmg, key=pmg.get)
    panels = [
        (pr, "#1f7a4d", "parent residual\nmax |r| (LSB)", (0, 1.12), 1.0, "limit 1 LSB", key(wp["tag"]),
         f"worst {wp['max_abs_r_LSB']:.2f} LSB", "{:.2f}"),
        (nz, "#2f6690", "sampled noise\n(µV rms)", (0, 165), NOISE_BUDGET_UV, f"budget {NOISE_BUDGET_UV:.0f} µV",
         key(nmax["tag"]), f"worst {nmax['noise_uV_rms']:.0f} µV", "{:.0f}"),
        (pmg, "#6a4c93", "driver phase margin,\nworst load and level (°)", (40, 92), 45.0, "limit 45°", wpm,
         f"lowest {pmg[wpm]:.1f}°", "{:.1f}"),
    ]
    fig, axs = plt.subplots(3, 1, figsize=(10.5, 7.4), sharex=True)
    fig.subplots_adjust(left=0.115, right=0.985, top=0.975, bottom=0.11, hspace=0.18)
    for k, (ax, (vals, col, ylab, ylim, lim, limtxt, worst, wtxt, _)) in enumerate(zip(axs, panels)):
        for g in range(1, len(groups)):
            ax.axvline(g * 6 - 1, color="#dddddd", lw=0.8, zorder=0)
        for c in corners:
            ks = [q for q in vals if q[0] == c]
            ax.scatter([xpos[q] for q in ks], [vals[q] for q in ks], marker=marks[c], s=26, color=col, zorder=3)
        if k == 0:  # no-cancellation bound M per condition (sum of component maxima >= max|r|)
            ks = sorted(mb)
            ax.scatter([xpos[q] for q in ks], [mb[q] for q in ks], marker="_", s=60, color="#888888", zorder=2)
        ax.axhline(lim, color="#222222", lw=1.2, ls="--", zorder=1)
        ax.text(len(groups) * 6 - 1.6, lim, limtxt, ha="right", va="bottom" if k != 2 else "top", fontsize=8.5,
                color="#222222")
        ax.scatter([xpos[worst]], [vals[worst]], s=150, facecolors="none", edgecolors="#7a3010", lw=1.4, zorder=4)
        c, v, t = worst
        off, ha, va = [((-12, 8), "right", "bottom"), ((0, -42), "center", "top"), ((12, -4), "left", "top")][k]
        ax.annotate(f"{wtxt}\n{c}, {v:.2f} V, {t:+.0f} °C", (xpos[worst], vals[worst]), xytext=off,
                    textcoords="offset points", ha=ha, va=va, fontsize=8.2, color="#7a3010",
                    arrowprops=dict(arrowstyle="-", color="#7a3010", lw=0.8, shrinkB=7) if k == 1 else None)
        ax.set_ylim(*ylim)
        ax.set_ylabel(ylab, fontsize=9)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    handles = [Line2D([], [], ls="", marker=marks[c], color="#555555", label=c) for c in corners]
    handles.append(Line2D([], [], ls="", marker="_", ms=9, mew=1.6, color="#888888",
                          label="top panel: no-cancellation bound M (sum of the component maxima)"))
    axs[0].legend(handles=handles, frameon=False, fontsize=8, ncol=6, loc="lower left", bbox_to_anchor=(0.0, 1.0),
                  title="process corner (marker shape)", title_fontsize=8, alignment="left")
    axs[-1].set_xticks([g * 6 + 2 for g in range(len(groups))], [f"{v:.2f} V\n{t:+d} °C" for v, t in groups],
                       fontsize=8.6)
    axs[-1].set_xlim(-1.5, len(groups) * 6 - 0.5)
    axs[-1].set_xlabel("PVT condition: supply and temperature, five process corners each", fontsize=9)
    sw = dict(des.switch.subckt_params)
    if des.switch.subckt_name == "sw_nvt":
        sw_txt = f"one native thick-oxide NMOS switch (W {float(sw['WS']) * int(sw['MS']):g} µm, L 0.5 µm)"
    else:
        sw_txt = f"bootstrapped NMOS switch (W {float(sw['WS']) * int(sw['MS']):g} µm)"
    context_header(fig, "Does the selected design close the declared verification domain?", [
        ("Circuit", f"selected design: folded-cascode driver, {sw_txt}, Cs = {des.cs * 1e12:.0f} pF"),
        ("Test", f"final verification: {len(parent)} PVT conditions, four sequences, two read windows, input "
                 "changing during the hold"),
        ("Metric", "three separate checks, never added: corrected held-sample residual, sampled noise, phase margin"),
    ], top=1.03, line=0.026, key_x=0.105)
    fig.text(0.01, 0.005, "Not shown: the full-scale step at switch closure (a reported diagnostic, Section 3.5). "
             "Not covered: mismatch, layout extraction, silicon.", fontsize=8, color="#555555", ha="left",
             va="bottom")
    out = sb.REPO / "results" / "figures"
    fig.savefig(out / f"{name}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(out / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def main(d: str = designs.SELECTED) -> None:
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
                       "result": f"Δ {num['delta_fine_mV'] * 1e3:+.3f} / {num['delta_gear_mV'] * 1e3:+.3f} µV; margin {margin_mV:.3f} mV",
                       "verdict": verdict(dmax <= 0.02 and margin_mV > dmax)})
        prose_extra["numerics_note"] = (f"Rerunning the worst condition with a 2 ps step and tighter tolerances, and with "
                                        "Gear integration, changes the worst residual by "
                                        + (f"at most {dmax * 1e3:.2f} µV." if dmax * 1e3 >= 0.01 else "less than 0.01 µV."))
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
    checks.append({"check": f"sampled noise, {len(noise)} condition/level points (switch at the kT/C floor, 1 mHz–50 GHz)",
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
        checks.append({"check": "STRESS timing (full-scale input step at switch closure)", "criterion": "diagnostic",
                       "result": f"{srange} LSB ({ws['tag']} worst)", "verdict": "reported"})
    else:  # screening values of the refinement study (design-study record), four conditions
        srange = "1.9–7.3"
        prose_extra["stress_source"] = (" (screening of the same driver with the 5 µm switch at four conditions; the "
                                        "selected design was not run in this timing)")
    prose_extra["stress_range_lsb"] = srange
    # each device against its own class's published SPICE-model domain (1.8 V devices: 1.95 V); files written
    # before the per-device limit field existed contain only 1.8 V devices
    steady, trans = [], []
    multi = any(v.get("limit_V", 1.95) != 1.95 for r in dev for q in r["devices"].values()
                for k, v in q.items() if k in ("vgs", "vgd", "vds"))
    for r in dev:
        for name, q in r["devices"].items():
            for k, v in q.items():
                if k in ("vgs", "vgd", "vds"):
                    lim = v.get("limit_V", 1.95)
                    steady.append((v["steady_V"] - lim, v["steady_V"], lim, name, k, r["tag"]))
                    trans.append((v["worst_V"] - lim, v["worst_V"], lim,
                                  v.get("time_over_limit_ns_per_cycle", v.get("time_over_1.96V_ns_per_cycle")),
                                  name, k, r["tag"]))
    st = max(steady)
    tr = max(trans)
    tlong = max(trans, key=lambda x: x[3])
    lim_txt = "each device's model-domain limit (1.8 V devices 1.95 V)" if multi else "1.95 V"
    checks.append({"check": "switch terminal voltages, steady (end of each clock phase)",
                   "criterion": f"|VGS|,|VGD|,|VDS| ≤ {lim_txt} (model validity)",
                   "result": f"max {st[1]:.3f} V{f' of {st[2]:.2f} V' if multi else ''} ({st[3]} {st[4]}, {st[5]})",
                   "verdict": verdict(st[0] <= 1e-3)})
    rv = min((q["vbs"]["worst_V"] + q["vbs"].get("limit_V", 1.95), q["vbs"]["worst_V"], n)
             for r in dev for n, q in r["devices"].items() if q.get("model", "nfet").split("__")[-1][0] != "p"
             and n not in ("MXP", "MGT"))
    checks.append({"check": "switch NMOS body-source voltage, reverse",
                   "criterion": "within the model range, ≥ −1.95 V" if not multi else "within each device's model range (1.8 V devices ≥ −1.95 V)",
                   "result": f"min {rv[1]:.3f} V" + (f" ({rv[2]})" if multi else ""), "verdict": verdict(rv[0] >= -1e-3)})
    # reader-facing device classes of the switch devices, for device-specific limits in the criteria
    cls_name = {"nfet_01v8": "1.8 V NMOS", "pfet_01v8": "1.8 V PMOS", "nfet_01v8_lvt": "1.8 V low-Vt NMOS",
                "pfet_01v8_lvt": "1.8 V low-Vt PMOS", "nfet_03v3_nvt": "3.3 V native NMOS"}
    fwd_limits = {}
    for r in dev:
        for q in r["devices"].values():
            if "model" in q and "vbs_fwd" in q:
                cls = q["model"].split("__")[-1]
                fwd_limits[cls_name.get(cls, cls)] = q["vbs_fwd"]["limit_V"]
    fwd_criterion = ("within each device class's documented body-source model-validity range ("
                     + ", ".join(f"{c} ≤ {v:+.1f} V" for c, v in sorted(fwd_limits.items())) + ") (A3)"
                     if fwd_limits else "within the model range, NMOS ≤ +0.3 V, PMOS ≤ +0.1 V (A3)")
    # A3: "VBS must stay within the model range (+0.3 to -1.95 V)" -- the forward side, at every instant
    # (not limited to steady state; amendment A8 covers only excursions above 1.95 V). PMOS mirrored (+0.1 V).
    if all("vbs_fwd" in q for r in dev for q in r["devices"].values()):
        fw = max(((q["vbs_fwd"]["worst_V"] - q["vbs_fwd"]["limit_V"], q["vbs_fwd"]["worst_V"], q["vbs_fwd"]["limit_V"],
                   q["vbs_fwd"]["time_over_limit_ns_per_cycle"], n, r["tag"], r["timing"])
                  for r in dev for n, q in r["devices"].items()))
        checks.append({"check": "switch MOS body-source voltage, forward (all instants)",
                       "criterion": fwd_criterion,
                       "result": f"max {fw[1]:+.3f} V vs {fw[2]:+.1f} V ({fw[4]}, {fw[5]} {fw[6]}); "
                                 f"{fw[3]:.3f} ns/cycle beyond the limit",
                       "verdict": verdict(fw[0] <= 1e-3)})
    else:
        checks.append({"check": "switch MOS body-source voltage, forward (all instants)",
                       "criterion": "within the model range, NMOS ≤ +0.3 V, PMOS ≤ +0.1 V (A3)",
                       "result": "not evaluated (devlimits.json predates the forward-bias field)",
                       "verdict": "UNRESOLVED"})
    if multi:
        checks.append({"check": "switch terminal voltages, transient (all instants)",
                       "criterion": "reported (A8); each device against its published SPICE-model domain",
                       "result": f"peak {tr[1]:.2f} V of {tr[2]:.2f} V ({tr[4]} {tr[5]}, {tr[6]}); "
                                 f"{'inside the domain at every instant' if tr[0] <= 1e-3 else f'longest beyond the limit {tlong[3]:.2f} ns/cycle ({tlong[4]} {tlong[5]})'}",
                       "verdict": "reported"})
    else:
        checks.append({"check": "switch terminal voltages, transient",
                       "criterion": "reported (A8); a peak above 1.95 V lies outside the published SKY130 SPICE-model domain",
                       "result": f"peak {tr[1]:.2f} V ({tr[4]} {tr[5]}, {tr[6]}); longest above 1.96 V {tlong[3]:.2f} ns/cycle ({tlong[4]} {tlong[5]})",
                       "verdict": "reported"})
    i_tt = [r["supply_current_uA"] for r in parent if r["tag"] == "tt_1.80V_+27C"][0]
    i_max = max(r["supply_current_uA"] for r in parent)
    for c in checks:
        c["role"] = role(c)
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
            "sampling switch": switch_summary(des),
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
                  "dev_peak_v": f"{tr[1]:.2f}", **prose_extra},
    }
    out = sb.REPO / "results" / "closure" / "final" / d / "final_closure.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    # the notebook's figure belongs to the design it currently presents; other designs get their own file
    closure_matrix_figure(parent, noise, stab, des, wp, nmax,
                          "figure_closure_matrix" if d == designs.SELECTED else f"figure_closure_matrix_{d}")
    print(json.dumps({"final_pass": final_pass, "checks": [(c["check"][:50], c["result"], c["verdict"]) for c in checks]},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
