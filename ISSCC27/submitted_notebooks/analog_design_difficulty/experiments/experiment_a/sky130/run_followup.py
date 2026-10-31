#!/usr/bin/env python3
"""Run the two SKY130 follow-up studies of the sample-and-hold front end.

1. Small-step excitation-port comparison (SMALL_STEP_PORT_COMPARISON.md).
2. Held-sample error and one design response, dummy-switch compensation, with
   the extended switch-width ladder (HOLD_ERROR_DESIGN_RESPONSE.md).

Reads the driver's DC tracking error from results/data/sky130_summary.json,
which run_sky130.py writes first in the same regeneration. Writes
results/data/sky130_followup_summary.json and the follow-up figures under
results/figures/.

Usage (from the repository root, after run_sky130.py):
    python experiments/experiment_a/sky130/run_followup.py
    python experiments/experiment_a/sky130/run_followup.py --replot
The second form redraws the three figures from the saved summary and the small-step
waveforms already under results/generated/sky130/, without running ngspice.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice_runner as sr  # noqa: E402
from figure_sketches import bench, context_header  # noqa: E402
from run_sky130 import (COMMAND_BLUE, DISTURB_ORANGE, EPS, GRID, INK, INK_2, MODEL_GREEN, RESULTS_DATA,  # noqa: E402
                        RESULTS_FIG, T_EVENT, base_tokens, grid_jobs, key, load, point_summary, style)

SUMMARY = RESULTS_DATA / "sky130_summary.json"
OUT = RESULTS_DATA / "sky130_followup_summary.json"
VEC8 = ["out", "samp", "xnode", "vcmd", "i_m6", "i_m7", "i_m1", "i_m2"]

# ---- small-step port comparison (SMALL_STEP_PORT_COMPARISON.md) ---------------
SS_TARGET = 0.9
SS_STEPS_MV = [10, -10, 20, -20]   # + : Cs starts below the target (driver supplies charge)
SS_WINDOW = 40e-9
SS_SCALED = 0.02                   # scaled settling: last |e_n| >= 2 % of the initial error
SS_D_MIN = 0.10                    # port difference criterion (as for the full-scale comparison)
SS_IMBALANCE_LINEAR, SS_IMBALANCE_SLEW = 0.5, 0.9
SS_M6_RANGE = (0.5, 2.0)
SS_SHAPE_TOL = 0.05


def load8(case_dir: Path) -> dict:
    r = sr.read_wrdata(case_dir / "tran.dat", VEC8)
    t = r["scale"]
    vref = float(r["out"][t > t[-1] - 20e-9].mean())
    pre = (t > T_EVENT - 3e-9) & (t < T_EVENT - 0.5e-9)
    post = t >= T_EVENT - 1e-15
    w = {k: r[k][post] for k in VEC8}
    w["t"] = t[post] - T_EVENT
    w["vref"] = vref
    w["pre"] = {k: float(r[k][pre].mean()) for k in VEC8}
    w["e0"] = w["pre"]["samp"] - vref
    w["en"] = (w["samp"] - vref) / w["e0"]
    return w


def last_ge(t: np.ndarray, x: np.ndarray, level: float, tmax: float = 200e-9) -> float:
    m = t <= tmax
    bad = np.nonzero(np.abs(x[m]) >= level)[0]
    return float(t[m][bad[-1]]) if bad.size else 0.0


def case_metrics(w: dict) -> dict:
    m = w["t"] <= SS_WINDOW
    s = np.abs(w["i_m1"] - w["i_m2"]) / (w["i_m1"] + w["i_m2"])
    i6 = w["i_m6"][m] / w["pre"]["i_m6"]
    dx = np.abs(w["xnode"][m] - w["xnode"][-1])
    k = int(np.argmax(dx))
    return {"initial_Cs_error_mV": 1e3 * w["e0"], "Vref_V": w["vref"],
            "max_first_stage_imbalance": float(s[m].max()),
            "i_m6_min_over_bias": float(i6.min()), "i_m6_max_over_bias": float(i6.max()),
            "x_max_deviation_mV": float(1e3 * dx[k]), "x_max_deviation_at_ns": float(1e9 * w["t"][m][k]),
            "last_scaled_ns": 1e9 * last_ge(w["t"], w["en"], SS_SCALED),
            "last_ge_eps_ns": 1e9 * last_ge(w["t"], w["samp"] - w["vref"], EPS)}


def on_grid(w: dict, tg: np.ndarray, node: str = "en") -> np.ndarray:
    return np.interp(tg, w["t"], w[node])


def small_step(main: dict) -> tuple[dict, dict]:
    voff = main["bringup"]["vout_dc_at_0p9_V"] - SS_TARGET
    rif = main["switch_ron"]["R_if_ohm"]
    tok = {**base_tokens(), "VTARGET": SS_TARGET, "TMAX": "20p"}
    jobs, names = [], []
    for d in SS_STEPS_MV:
        start = SS_TARGET - d * 1e-3
        tag = f"{'p' if d > 0 else 'm'}{abs(d)}"
        jobs += [("tb_s1_input_step_rif.spice", f"ss_in_rif_{tag}", {**tok, "VCMD0": f"{start:.6f}", "RIF": f"{rif:.6g}"}),
                 ("tb_s2_output_port_rif.spice", f"ss_out_rif_{tag}",
                  {**tok, "VPREV": f"{start + voff:.7f}", "RIF": f"{rif:.6g}"}),
                 ("tb_s3_input_step_tg.spice", f"ss_in_tg_{tag}", {**tok, "VCMD0": f"{start:.6f}"}),
                 ("tb_s4_connected_tg.spice", f"ss_out_tg_{tag}", {**tok, "VPREV": f"{start + voff:.7f}"})]
    waves = {d.name: load8(d) for d in sr.run_many(jobs)}
    tg = np.linspace(0, SS_WINDOW, 4001)
    per = {}
    for d in SS_STEPS_MV:
        tag = f"{'p' if d > 0 else 'm'}{abs(d)}"
        res = {}
        for sw in ("rif", "tg"):
            wi, wo = waves[f"ss_in_{sw}_{tag}"], waves[f"ss_out_{sw}_{tag}"]
            diff = np.abs(on_grid(wi, tg) - on_grid(wo, tg))
            k = int(np.argmax(diff))
            res[sw] = {"input_step": case_metrics(wi), "output_port": case_metrics(wo),
                       "D": float(diff[k]), "D_at_ns": float(1e9 * tg[k])}
        res["composition"] = {"t_b_ns": res["rif"]["output_port"]["last_ge_eps_ns"],
                              "t_c_ns": res["tg"]["output_port"]["last_ge_eps_ns"]}
        per[f"{d:+d}mV"] = res
    # linear-regime conditions
    rif_cases = [per[k]["rif"][e] for k in per for e in ("input_step", "output_port")]
    L1 = all(c["max_first_stage_imbalance"] <= SS_IMBALANCE_LINEAR for c in rif_cases)
    L2 = all(SS_M6_RANGE[0] <= c["i_m6_min_over_bias"] and c["i_m6_max_over_bias"] <= SS_M6_RANGE[1] for c in rif_cases)
    shape = {}
    for exc, name in (("in", "input_step"), ("out", "output_port")):
        curves = [on_grid(waves[f"ss_{exc}_rif_{'p' if d > 0 else 'm'}{abs(d)}"], tg) for d in SS_STEPS_MV]
        shape[name] = float(max(np.abs(a - b).max() for i, a in enumerate(curves) for b in curves[i + 1:]))
    L3 = all(v <= SS_SHAPE_TOL for v in shape.values())
    Ds = [per[k]["rif"]["D"] for k in per]
    if all(D >= SS_D_MIN for D in Ds) and L1 and L2 and L3:
        reading = "port difference present in the approximately linear regime"
    elif all(D < SS_D_MIN for D in Ds):
        reading = "port difference largely collapses at small amplitude"
    else:
        reading = "mixed"
    slews = any(c["max_first_stage_imbalance"] >= SS_IMBALANCE_SLEW for c in rif_cases)
    out = {"target_V": SS_TARGET, "Voff_mV": 1e3 * voff, "R_if_ohm": rif, "per_step": per,
           "linear_conditions": {"L1_imbalance_le_0p5": L1, "L2_m6_within_0p5_2x": L2,
                                 "L3_shape_agreement_le_0p05": L3, "max_shape_difference": shape,
                                 "any_first_stage_slewing": slews},
           "D_rif": Ds, "reading": reading}
    return out, waves


def figure_small_step(ss: dict, waves: dict, full: dict | None = None) -> None:
    fig = plt.figure(figsize=(10.4, 8.0))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.42, 1, 1], hspace=0.3, wspace=0.18,
                          left=0.09, right=0.99, top=0.97, bottom=0.08)
    rif = f"R_if = {ss['R_if_ohm']:.0f} Ω"
    sketches = [("Input-port test: the input steps by ±20 mV", "input\nsteps", COMMAND_BLUE, True,
                 "settled at the\nold value", INK, None),
                ("Output-port test: a charged Cs is connected", "input\nheld", INK, False,
                 "starts ±20 mV\naway", MODEL_GREEN, "connected at t = 0")]
    for col, (title, lab, c_in, step, note, c_cs, arrow_label) in enumerate(sketches):
        ax = fig.add_subplot(gs[0, col])
        ax.set_xlim(-0.6, 5.2); ax.set_ylim(-1.05, 1.15); ax.set_aspect("equal"); ax.axis("off")
        bench(ax, 0.9, 0.2, lab, "rif", note, in_color=c_in, step=step, link_color=MODEL_GREEN if not step else INK,
              link_label=rif, cs_color=c_cs, arrow_label=arrow_label)
        ax.set_title(title, fontsize=9.5, color=COMMAND_BLUE if step else MODEL_GREEN, loc="left")
    ax0 = None
    for col, d in enumerate((20, -20)):
        tag = f"{'p' if d > 0 else 'm'}{abs(d)}"
        wi, wo = waves[f"ss_in_rif_{tag}"], waves[f"ss_out_rif_{tag}"]
        r = ss["per_step"][f"{d:+d}mV"]["rif"]
        ax = fig.add_subplot(gs[1, col], sharex=ax0)
        ax0 = ax0 or ax
        ax.plot(wi["t"] * 1e9, wi["en"], color=COMMAND_BLUE, lw=2, label="input-port test")
        ax.plot(wo["t"] * 1e9, wo["en"], color=MODEL_GREEN, lw=2, label="output-port test")
        ax.axhline(0, color=INK_2, lw=0.8)
        ax.set_ylim(-0.35, 1.1)
        side = "driver supplies charge" if d > 0 else "driver sinks charge"
        ax.set_title(f"{abs(d)} mV step, {side}: max |difference| = {r['D']:.2f} at {r['D_at_ns']:.1f} ns",
                     fontsize=9.2, color=INK)
        if col == 0:
            ax.set_ylabel("Cs error / initial error", color=INK)
        ax.legend(fontsize=8, frameon=False, loc="upper right")
        ax.tick_params(labelbottom=False)
        style(ax)
        ax = fig.add_subplot(gs[2, col], sharex=ax0)
        ax.plot(wi["t"] * 1e9, 1e3 * (wi["xnode"] - wi["xnode"][-1]), color=COMMAND_BLUE, lw=2,
                label="input-port test")
        ax.plot(wo["t"] * 1e9, 1e3 * (wo["xnode"] - wo["xnode"][-1]), color=MODEL_GREEN, lw=2,
                label="output-port test")
        ax.axhline(0, color=INK_2, lw=0.8)
        ax.set_xlabel("Time after the event (ns)", color=INK)
        if col == 0:
            ax.set_ylabel("Internal node x of the driver\n− settled value (mV)", color=INK)
        ax.legend(fontsize=8, frameon=False, loc="upper right" if d > 0 else "lower right")
        style(ax)
    ax0.set_xlim(-0.5, 25)
    c = ss["linear_conditions"]
    imb = max(v["rif"][e]["max_first_stage_imbalance"] for v in ss["per_step"].values()
              for e in ("input_step", "output_port"))
    context_header(fig, "Does the excitation port matter even without slewing?", [
        ("Circuit", f"first-cut driver (unity-gain follower), switch represented by {rif}, Cs = 1 pF; tt, 27 °C"),
        ("Test", "small step at 0.9 V applied at the driver input or at its output port; same Cs, same initial "
                 "Cs error"),
        ("Metric", f"normalized Cs error (top) and the driver's internal node (bottom); first-stage imbalance "
                   f"≤ {imb:.2f}, slewing would be ≥ 0.9"),
    ], top=0.995, line=0.026, key_x=0.09)
    fig.text(0.5, 0.005,
             f"Approximately linear regime: the ±10 mV steps (not drawn) overlay the ±20 mV curves within "
             f"{max(c['max_shape_difference'].values()):.3f}. Not a full-scale slew comparison. "
             "(Testbenches: tb_s1_input_step_rif.spice, tb_s2_output_port_rif.spice.)",
             ha="center", va="bottom", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_small_step_ports.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


# ---- held-sample error and design response (HOLD_ERROR_DESIGN_RESPONSE.md) ------
VLSB = 0.6 / 1024
HS_LEVELS = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
HS_VARIANTS = {"eighth": (3, 6, 0.625), "quarter": (3, 6, 1.25), "half": (3, 6, 2.5), "chosen": (3, 6, 5),
               "double": (6, 12, 5), "dummy": (3, 6, 5)}
HS_SHARE, HS_REMAINDER = VLSB / 4, VLSB / 2
POINTS9 = [(vt, vp) for vt in (0.6, 0.9, 1.2) for vp in (0.6, 0.9, 1.2)]
BRIDGE_POINTS = [(1.2, 0.6), (0.6, 1.2), (0.9, 0.9)]


def two_point_residual(v: np.ndarray, y: np.ndarray) -> np.ndarray:
    line = y[0] + (y[-1] - y[0]) * (v - v[0]) / (v[-1] - v[0])
    return y - line


def held_sample_residuals(names: list[str] | None = None) -> dict:
    """Hold-step and held-error residuals of the gate variants on the zero-step hold bench (tt, 27 C)."""
    jobs, cases = [], []
    for name in names or list(HS_VARIANTS):
        mn, mp, wf = HS_VARIANTS[name]
        bench = "tb_t6_hold_dummy.spice" if name == "dummy" else "tb_t4_hold.spice"
        for lv in HS_LEVELS:
            cases.append((name, lv))
            jobs.append((bench, f"hs_{name}_{lv:.1f}",
                         {**base_tokens(), "VTARGET": lv, "VPREV": lv, "MN": mn, "MP": mp, "WF": wf}))
    raw = {}
    for (name, lv), d in zip(cases, sr.run_many(jobs)):
        r = sr.read_wrdata(d / "tran.dat", ["out", "samp", "xnode", "vcmd", "i_m6", "i_m7"])
        t, v = r["scale"], r["samp"]
        raw.setdefault(name, {})[lv] = (float(v[(t >= 63.0e-9) & (t <= 64.8e-9)].mean()),
                                        float(v[(t >= 75e-9) & (t <= 85e-9)].mean()))
    out = {}
    lv = np.array(HS_LEVELS)
    for name, vals in raw.items():
        before = np.array([vals[x][0] for x in HS_LEVELS])
        after = np.array([vals[x][1] for x in HS_LEVELS])
        P, S, E = after - before, before - lv, after - lv
        RP, RS, RE = (two_point_residual(lv, y) for y in (P, S, E))
        mn, mp, wf = HS_VARIANTS[name]
        out[name] = {"Wn_um": mn * wf, "Wp_um": mp * wf, "dummies": name == "dummy", "levels_V": HS_LEVELS,
                     "hold_step_mV": list(1e3 * P), "pre_opening_error_mV": list(1e3 * S),
                     "held_error_mV": list(1e3 * E),
                     "residual_hold_step_mV": list(1e3 * RP), "residual_pre_opening_mV": list(1e3 * RS),
                     "residual_held_error_mV": list(1e3 * RE),
                     "max_residual_hold_step_mV": float(1e3 * np.abs(RP).max()),
                     "max_residual_pre_opening_mV": float(1e3 * np.abs(RS).max()),
                     "max_residual_held_error_mV": float(1e3 * np.abs(RE).max()),
                     "hold_step_offset_mV": float(1e3 * P[0]),
                     "hold_step_gain_mV_per_V": float(1e3 * (P[-1] - P[0]) / (lv[-1] - lv[0])),
                     "max_abs_hold_step_mV": float(1e3 * np.abs(P).max()),
                     "turn_off_within_share": bool(np.abs(RP).max() <= HS_SHARE),
                     "held_sample_check_pass": bool(np.abs(RE).max() <= HS_REMAINDER)}
    return out


def held_sample(main: dict) -> dict:
    out = held_sample_residuals()
    # acquisition settling: dummies over the nine points; eighth and quarter over the nine points
    jobs = []
    for vt, vp in POINTS9:
        jobs.append(("tb_t5_connected_dummy.spice", f"hsc_dummy_{vt:.1f}_{vp:.1f}",
                     {**base_tokens(), "VTARGET": vt, "VPREV": vp}))
    # The three points initially evaluated for the narrow gates are BRIDGE_POINTS (two full-scale
    # transitions and the 0.9 V zero step); the other six points were added after that three-point
    # result, as a check of the narrow candidates. ("bridge" survives only in data keys.)
    for name in ("eighth", "quarter"):
        mn, mp, wf = HS_VARIANTS[name]
        jobs += grid_jobs(POINTS9, "c", tag=f"_w{name}", MN=mn, MP=mp, WF=wf)
    waves = {d.name: load(d) for d in sr.run_many(jobs)}
    acq = {"dummy": {key(vt, vp): point_summary(waves[f"hsc_dummy_{vt:.1f}_{vp:.1f}"], "samp", vt, vp)
                     for vt, vp in POINTS9}}
    for name in ("eighth", "quarter"):
        acq[name] = {key(vt, vp): point_summary(waves[f"c_{vt:.1f}_{vp:.1f}_w{name}"], "samp", vt, vp)
                     for vt, vp in POINTS9}
    nom, sw = main["nominal_tt_27C"]["c"], main["switch_width"]
    acq["chosen"] = {k: nom[k] for k in nom}
    for name in ("half", "double"):
        acq[name] = sw[name]["points"]
    for name, pts in acq.items():
        out[name]["acquisition"] = {k: {"last_ge_eps_ns": v["last_ge_eps_ns"], "error_at_Tacq_mV": v["error_at_Tacq_mV"],
                                        "pass_at_Tacq": v["pass_at_Tacq"],
                                        "turn_on_excursion_mV": v.get("turn_on_excursion_mV",
                                                                      v.get("out_error_extreme_first_1ns_mV"))}
                                    for k, v in pts.items()}
        bp = [pts[key(vt, vp)] for vt, vp in BRIDGE_POINTS]
        out[name]["worst_last_ge_eps_bridge_points_ns"] = max(v["last_ge_eps_ns"] for v in bp)
        out[name]["acquisition_pass_bridge_points"] = all(v["pass_at_Tacq"] for v in bp)
        out[name]["acquisition_pass_all_evaluated"] = all(v["pass_at_Tacq"] for v in pts.values())
    ron_dir = sr.run("tb_switch_ron_narrow.spice", "ron_narrow", {"CORNER": "tt", "TEMP": 27})
    r = sr.read_wrdata(ron_dir / "ron.dat", ["eighth", "quarter"])
    inr = (r["scale"] >= 0.6 - 1e-9) & (r["scale"] <= 1.2 + 1e-9)
    sweep = main["switch_ron"]["sweep"]
    ron_max = {"eighth": float(r["eighth"][inr].max()), "quarter": float(r["quarter"][inr].max()),
               "half": sweep["ron_half"]["max_ohm"], "chosen": sweep["ron"]["max_ohm"], "dummy": sweep["ron"]["max_ohm"],
               "double": sweep["ron_double"]["max_ohm"]}
    for name in out:
        out[name]["Ron_max_ohm"] = ron_max[name]
        out[name]["worst_last_ge_eps_all_evaluated_ns"] = max(v["last_ge_eps_ns"] for v in out[name]["acquisition"].values())
    c, d = out["chosen"], out["dummy"]
    red = c["max_residual_hold_step_mV"] / d["max_residual_hold_step_mV"]
    if d["turn_off_within_share"] and d["acquisition_pass_all_evaluated"]:
        outcome = "A"
    elif red >= 2 and d["acquisition_pass_all_evaluated"]:
        outcome = "B"
    else:
        outcome = "C"
    bridge = [n for n in ("eighth", "quarter", "half", "chosen", "double")
              if out[n]["turn_off_within_share"] and out[n]["acquisition_pass_bridge_points"]]
    return {"VLSB_mV": 1e3 * VLSB, "share_mV": 1e3 * HS_SHARE, "remainder_mV": 1e3 * HS_REMAINDER,
            "variants": out, "turn_off_reduction_factor": red, "outcome": outcome,
            "widths_meeting_both": bridge}


# ---- acquisition-time sensitivity: block-PASS / connected-FAIL (DESIGN_BRIEF.md Section 6) ----
def acquisition_window(main: dict) -> dict:
    per = main["interface_vs_connected"]["per_point"]
    rows = {}
    for k, v in per.items():
        tb, tc = v["t_b_ns"], v["t_c_ns"]
        rows[k] = {"t_b_ns": tb, "t_c_ns": tc,
                   "block_pass_connected_fail_ns": [tb, tc] if tb < tc else None,
                   "block_fail_connected_pass_ns": [tc, tb] if tc < tb else None}
    def cls(pick):
        ks = [k for k in per if pick(*(float(x) for x in k.split("/")))]
        tb, tc = max(per[k]["t_b_ns"] for k in ks), max(per[k]["t_c_ns"] for k in ks)
        return {"points": ks, "t_b_ns": tb, "t_c_ns": tc,
                "block_pass_connected_fail_ns": [tb, tc] if tb < tc else None,
                "block_fail_connected_pass_ns": [tc, tb] if tc < tb else None}
    return {"per_point": rows, "classes": {"any previous sample": cls(lambda vt, vp: True),
                                           "zero steps only": cls(lambda vt, vp: vt == vp)}}


def figure_acquisition_window(win: dict, ss: dict) -> None:
    order = ["0.6/1.2", "0.9/1.2", "0.6/0.9", "1.2/0.6", "1.2/0.9", "0.9/0.6", "0.6/0.6", "0.9/0.9", "1.2/1.2"]

    def lab(k):
        vt, vp = k.split("/")
        return f"{vp} → {vt} V"
    rows = [(lab(k), win["per_point"][k]) for k in order]
    rows += [("small steps at 0.9 V", {
        "t_b_ns": max(v["composition"]["t_b_ns"] for v in ss["per_step"].values()),
        "t_c_ns": max(v["composition"]["t_c_ns"] for v in ss["per_step"].values())})]
    names = {"any previous sample": "worst case, any previous sample", "zero steps only": "worst case, zero steps only"}
    rows += [(names[n], v) for n, v in win["classes"].items()]
    fig = plt.figure(figsize=(11.4, 5.9))
    gs = fig.add_gridspec(2, 2, width_ratios=[0.78, 2.0], wspace=0.30, hspace=0.12,
                          left=0.01, right=0.99, top=0.97, bottom=0.10)
    rif = "R_if = 744 Ω"
    for i, (title, link, color, label, arrow_label) in enumerate([
            ("Block test: switch represented by R_if", "rif", MODEL_GREEN, rif, None),
            ("Connected circuit: real transmission gate", "tg", DISTURB_ORANGE, "gate closes",
             "charge kick\nat turn-on")]):
        ax = fig.add_subplot(gs[i, 0])
        ax.set_xlim(-0.9, 4.9); ax.set_ylim(-1.15, 1.35); ax.set_aspect("equal"); ax.axis("off")
        bench(ax, 0.6, 0.15, "input\nheld at\ntarget", link, "starts at\nprevious", link_color=color,
              link_label=None if arrow_label else label, cs_color=color, arrow_label=arrow_label)
        ax.set_title(title, fontsize=9.2, color=color, loc="left")
    ax = fig.add_subplot(gs[:, 1])
    for i, (lab_, v) in enumerate(rows):
        y = len(rows) - 1 - i
        tb, tc = v["t_b_ns"], v["t_c_ns"]
        if tb < tc:
            ax.barh(y, tc - tb, left=tb, height=0.55, color=DISTURB_ORANGE, alpha=0.35, lw=0)
        elif tc < tb:
            ax.barh(y, tb - tc, left=tc, height=0.55, color=INK_2, alpha=0.18, lw=0)
        ax.plot([tb], [y], marker="o", color=MODEL_GREEN, ms=7, ls="none")
        ax.plot([tc], [y], marker="D", color=DISTURB_ORANGE, ms=6, ls="none")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1], fontsize=8.5)
    ax.axhline(2.5, color=INK_2, lw=0.6)
    ax.axhline(5.5, color=INK_2, lw=0.6, ls=":")
    ax.text(45.6, 9.0, "transitions\n(previous → target)", fontsize=8, color=INK_2, ha="right", va="center")
    ax.text(45.6, 4.0, "zero steps:\nCs starts at\nthe target", fontsize=8, color=INK_2, ha="right", va="center")
    ax.axvline(40, color=INK_2, lw=0.8, ls=":")
    ax.text(39.6, len(rows) - 0.55, "declared\nTacq = 40 ns", fontsize=8, color=INK_2, va="top", ha="right")
    ax.set_xlim(0, 46)
    ax.set_xlabel("Shortest acquisition time that brings Cs within ε = 0.29 mV (ns)", color=INK)
    ax.plot([], [], marker="o", color=MODEL_GREEN, ls="none", label="block test with R_if")
    ax.plot([], [], marker="D", color=DISTURB_ORANGE, ls="none", label="connected circuit")
    from matplotlib.patches import Patch
    h, _ = ax.get_legend_handles_labels()
    h += [Patch(color=DISTURB_ORANGE, alpha=0.35, label="block test accepts, connected circuit fails"),
          Patch(color=INK_2, alpha=0.18, label="block test is conservative")]
    ax.legend(handles=h, fontsize=8, frameon=True, framealpha=0.95, edgecolor=GRID, loc="upper left",
              bbox_to_anchor=(0.0, 1.0))
    style(ax)
    context_header(fig, "Does the R_if block test predict the connected acquisition time?", [
        ("Circuit", "first-cut driver and Cs = 1 pF; the switch either as one resistance R_if or as the real "
                    "transmission gate; tt, 27 °C"),
        ("Test", "Cs starts at the previous sample, the input is held at the target, the switch closes at t = 0"),
        ("Metric", "last time the Cs error exceeds ε, read as the shortest acquisition time that would pass"),
    ], top=0.995, line=0.04, key_x=0.075)
    fig.text(0.5, 0.0, "Only the 40 ns acquisition was simulated; other times are read from the last crossings of ε. "
             "(Testbenches: tb_t3_interface_model.spice, tb_t1_connected.spice, tb_s2_output_port_rif.spice, "
             "tb_s4_connected_tg.spice.)", ha="center", va="bottom", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_acquisition_window.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


def figure_held_sample(hs: dict) -> None:
    V = hs["variants"]
    lv = HS_LEVELS
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.5), gridspec_kw={"width_ratios": [1, 1, 1.15]})
    fig.subplots_adjust(left=0.055, right=0.99, top=0.78, bottom=0.2, wspace=0.27)
    styles = {"chosen": (DISTURB_ORANGE, "-", "o", "first-cut gate (15 / 30 µm)"),
              "dummy": (COMMAND_BLUE, "-", "s", "first-cut gate + half-size dummies"),
              "eighth": (MODEL_GREEN, "--", "^", "one-eighth gate (1.9 / 3.8 µm)")}
    ax = axes[0]
    for n, (c, ls, mk, lab) in styles.items():
        ax.plot(lv, V[n]["hold_step_mV"], color=c, ls=ls, marker=mk, lw=1.8, ms=5, label=lab)
    ax.axhline(0, color=INK_2, lw=0.8)
    ax.axhspan(-hs["VLSB_mV"], hs["VLSB_mV"], color=GRID, alpha=0.6, lw=0)
    ax.text(0.61, hs["VLSB_mV"] * 1.3, "±1 LSB", fontsize=8, color=INK_2)
    ax.set_xlabel("Held level (V)", color=INK)
    ax.set_ylabel("Step at opening (mV)", color=INK)
    ax.set_title("1  Step at opening, uncorrected", fontsize=9.5, color=INK)
    ax.legend(fontsize=7.4, frameon=False, loc="upper left")
    style(ax)
    ax = axes[1]
    for n, (c, ls, mk, lab) in styles.items():
        ax.plot(lv, V[n]["residual_hold_step_mV"], color=c, ls=ls, marker=mk, lw=1.8, ms=5, label=lab)
    ax.plot(lv, V["chosen"]["residual_pre_opening_mV"], color=INK_2, ls=":", lw=1.6,
            label="driver error before opening (all gates)")
    ax.axhspan(-hs["share_mV"], hs["share_mV"], color=GRID, alpha=0.8, lw=0)
    ax.text(0.61, hs["share_mV"] * 1.15, "±¼ LSB local share", fontsize=8, color=INK_2)
    ax.axhline(0, color=INK_2, lw=0.8)
    ax.set_xlabel("Held level (V)", color=INK)
    ax.set_ylabel("After two-point correction (mV)", color=INK)
    ax.set_title("2  Level-dependent part of the step,\nand the driver error it adds to", fontsize=9.5, color=INK)
    ax.set_ylim(-0.95, 0.95)
    ax.legend(fontsize=7.2, frameon=False, loc="upper right")
    style(ax)
    ax = axes[2]
    ladder = ["eighth", "quarter", "half", "chosen", "double"]
    names = {"eighth": "1/8", "quarter": "1/4", "half": "1/2", "chosen": "first\ncut", "double": "2×"}
    xs = np.arange(len(ladder))
    loc = [V[n]["max_residual_hold_step_mV"] for n in ladder]
    par = [V[n]["max_residual_held_error_mV"] for n in ladder]
    ax.plot(xs, loc, color=DISTURB_ORANGE, marker="o", lw=1.6, label="local switch metric: corrected step at opening")
    ax.plot(xs, par, color=MODEL_GREEN, marker="s", lw=1.6, label="parent metric: corrected held-sample residual")
    d = V["dummy"]
    ax.plot([3.18], [d["max_residual_hold_step_mV"]], marker="o", mfc="white", mec=DISTURB_ORANGE, ms=7, ls="none")
    ax.plot([3.18], [d["max_residual_held_error_mV"]], marker="s", mfc="white", mec=MODEL_GREEN, ms=7, ls="none")
    ax.annotate("open markers:\nfirst cut + dummies", (3.18, d["max_residual_hold_step_mV"]), textcoords="offset points", xytext=(7, -4),
                fontsize=7.6, color=INK_2)
    ib, pb = int(np.argmin(loc)), int(np.argmin(par))
    ax.annotate("best by\nlocal metric", (xs[ib], loc[ib]), textcoords="offset points", xytext=(10, -2),
                ha="left", va="top", fontsize=7.8, color=DISTURB_ORANGE)
    ax.annotate("best by\nparent metric", (xs[pb], par[pb]), textcoords="offset points", xytext=(0, -12),
                ha="center", va="top", fontsize=7.8, color=MODEL_GREEN)
    ax.axhline(hs["VLSB_mV"], color=INK_2, lw=0.9, ls="--")
    ax.text(-0.3, hs["VLSB_mV"] * 1.07, "1 LSB", fontsize=8, color=INK_2, ha="left", va="bottom")
    ax.set_yscale("log")
    ax.set_ylim(0.04, 4)
    ax.set_xlim(-0.4, 4.4)
    ticks = [f"{names[n]}\n{V[n]['Ron_max_ohm'] / 1e3:.2g} kΩ\n{V[n]['worst_last_ge_eps_all_evaluated_ns']:.1f} ns"
             for n in ladder]
    ax.set_xticks(xs, ticks, fontsize=7.6)
    ax.set_xlabel("gate width (top), max Ron, worst settling to ε", color=INK, fontsize=8.6)
    ax.set_ylabel("Largest residual (mV)", color=INK)
    ax.set_title("3  Width ladder: the two metrics rank the widths differently", fontsize=9.5, color=INK)
    ax.legend(fontsize=7.2, frameon=False, loc="upper left")
    style(ax)
    context_header(fig, "Does improving the local switch metric improve the parent result?", [
        ("Circuit", "first-cut driver with the transmission gate at five widths, and with half-size dummy switches"),
        ("Test", "zero-step hold bench (Cs starts at the target), seven held levels, tt, 27 °C, 0.2 ns edges"),
        ("Metric", "local: level-dependent step at opening after correction; parent: corrected held-sample "
                   "residual (driver error + step, signed)"),
    ], top=0.86, line=0.05, key_x=0.06)
    fig.text(0.5, 0.0, "Step = mean V(Cs) 10–20 ns after opening minus its mean just before. Settling: first cut, "
             "dummies, 1/4 and 1/8 at nine operating points; 1/2 and 2× at three. "
             "(Testbenches: tb_t4_hold.spice, tb_t6_hold_dummy.spice, tb_t1_connected.spice, "
             "tb_t5_connected_dummy.spice.)", ha="center", va="bottom", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_held_sample.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


def replot() -> None:
    """Redraw Figures 5-7 from the saved summary and saved small-step waveforms (no ngspice)."""
    summary = json.loads(OUT.read_text())
    ss = summary["small_step_ports"]
    waves = {f"ss_{e}_rif_{t}": load8(sr.GENERATED / f"ss_{e}_rif_{t}") for e in ("in", "out") for t in ("p20", "m20")}
    figure_small_step(ss, waves)
    figure_held_sample(summary["held_sample"])
    figure_acquisition_window(summary["acquisition_window"], ss)


def main() -> None:
    main_summary = json.loads(SUMMARY.read_text())
    ss, ss_waves = small_step(main_summary)
    figure_small_step(ss, ss_waves, main_summary)
    hs = held_sample(main_summary)
    win = acquisition_window(main_summary)
    figure_held_sample(hs)
    figure_acquisition_window(win, ss)
    summary = {"small_step_ports": ss, "held_sample": hs, "acquisition_window": win}
    OUT.write_text(json.dumps(summary, indent=2, default=float))
    print("small-step reading:", ss["reading"], "| D (R_if):", [f"{x:.3f}" for x in ss["D_rif"]])
    print("linear conditions:", ss["linear_conditions"])
    for k, v in ss["per_step"].items():
        for sw in ("rif", "tg"):
            r = v[sw]
            print(f"{k} {sw}: D={r['D']:.3f}@{r['D_at_ns']:.1f}ns | " + " | ".join(
                f"{e}: e0={r[e]['initial_Cs_error_mV']:+.3f} mV, imb={r[e]['max_first_stage_imbalance']:.2f}, "
                f"M6 {r[e]['i_m6_min_over_bias']:.2f}-{r[e]['i_m6_max_over_bias']:.2f}, "
                f"x {r[e]['x_max_deviation_mV']:.1f} mV@{r[e]['x_max_deviation_at_ns']:.1f}, "
                f"2% {r[e]['last_scaled_ns']:.2f} ns, eps {r[e]['last_ge_eps_ns']:.2f} ns"
                for e in ("input_step", "output_port")))
        print(f"{k} composition: t_b {v['composition']['t_b_ns']:.2f} ns, t_c {v['composition']['t_c_ns']:.2f} ns")
    for n, v in hs["variants"].items():
        print(f"{n:8s} W {v['Wn_um']:g}/{v['Wp_um']:g}: P " + " ".join(f"{x:+.2f}" for x in v["hold_step_mV"])
              + f" | max|R_P| {v['max_residual_hold_step_mV']:.3f} max|R_S| {v['max_residual_pre_opening_mV']:.3f}"
              f" max|R_E| {v['max_residual_held_error_mV']:.3f} mV | check {'PASS' if v['held_sample_check_pass'] else 'FAIL'}"
              f" | Ron {v['Ron_max_ohm']:.0f} | worst acq {v['worst_last_ge_eps_all_evaluated_ns']:.1f} ns (bridge "
              f"{v['worst_last_ge_eps_bridge_points_ns']:.1f}) pass {v['acquisition_pass_all_evaluated']}")
    print("window:", win["classes"])
    print("outcome", hs["outcome"], "reduction", f"{hs['turn_off_reduction_factor']:.2f}", "widths meeting both",
          hs["widths_meeting_both"])


if __name__ == "__main__":
    replot() if "--replot" in sys.argv[1:] else main()
