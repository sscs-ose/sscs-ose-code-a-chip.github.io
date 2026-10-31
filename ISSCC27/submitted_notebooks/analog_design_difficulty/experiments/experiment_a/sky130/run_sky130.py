#!/usr/bin/env python3
"""Run the SKY130 transistor-level experiment of the sample-and-hold front end.

Conditions, tests, metrics and readings are defined in DESIGN_BRIEF.md; the
switch-width study in SWITCH_WIDTH_STUDY.md. This script
1. records the environment (ngspice, SKY130 revision, Python packages);
2. runs the DC and small-signal bring-up benches and the light-load check;
3. sweeps the transmission-gate on-resistance and sets the interface value R_if;
4. runs tests (a) input step, (b) output-port test with the interface model,
   (c) connected transmission gate, and (m) matched control over the
   Vtarget x Vprev operating points at tt / 27 C;
5. runs the numerical-convergence, corner, hold-step, switch-width, and
   conditional second-stage checks;
6. writes compact CSV/JSON data under results/data/ and the simulation
   figures under results/figures/.

The two follow-up studies are in run_followup.py.

Usage (from the repository root):
    python experiments/experiment_a/sky130/run_sky130.py
"""
from __future__ import annotations

import csv
import json
import platform
import sys
from importlib import metadata
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spice_runner as sr  # noqa: E402

REPO = sr.REPO
RESULTS_DATA = REPO / "results" / "data"
RESULTS_FIG = REPO / "results" / "figures"

# ---- design brief (DESIGN_BRIEF.md) ---------------------------------------------
LEVELS = [0.6, 0.9, 1.2]          # grid for both Vtarget and Vprev (operating range 0.6-1.2 V)
EPS = 0.29e-3                     # acquisition-settling tolerance at the end of acquisition (about 1/2070 of 0.6 V)
TACQ = 40e-9                      # acquisition-time allocation
CS = "1p"
IREF = "10u"
T_EVENT = 25e-9
MID_LEVEL = 0.9                   # bring-up and small-signal operating point
TG_MN, TG_MP = 3, 6               # transmission gate: nfet 5/0.15 x 3, pfet 5/0.15 x 6
WIDTHS = {"half": (3, 6, 2.5), "chosen": (3, 6, 5), "double": (6, 12, 5)}  # (n fingers, p fingers, finger W um)
FULL_SCALE = [(1.2, 0.6), (0.6, 1.2)]   # (Vtarget, Vprev): source supplies / sinks charge
REPORT_T_NS = [5, 10, 15, 20, 25, 30, 40, 60, 80]
T_GRID_NS = np.arange(1, 81, 1.0)
NONCOLLAPSE_MIN = 0.10
AGREE_NS = 1.0
NUM_SETTLE_NS, NUM_ERR_MV = 0.2, 0.1 * EPS * 1e3
LIGHT_LOAD = "1f"

COMMAND_BLUE = "#2a78d6"
MODEL_GREEN = "#2e8b57"
DISTURB_ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#d9d8d4"

VECTORS = ["out", "samp", "xnode", "vcmd", "i_m6", "i_m7"]
BASELINE_SRC = "source_two_stage.spice"
VARIATION_SRC = "source_two_stage_2x.spice"  # second stage at 200 uA


def key(vt: float, vp: float) -> str:
    """Grid-point label: target/previous."""
    return f"{vt:.1f}/{vp:.1f}"


def base_tokens(corner: str = "tt", temp: int = 27, tmax: str = "20p", src: str = BASELINE_SRC,
                reltol: str = "1e-4", **extra) -> dict:
    return {**{"CORNER": corner, "TEMP": temp, "IREF": IREF, "VTARGET": MID_LEVEL, "CS": CS, "TMAX": tmax,
            "CLOAD": "1p", "SRCFILE": src, "RELTOL": reltol, "MN": TG_MN, "MP": TG_MP, "WF": 5}, **extra}


def grid_jobs(points, tests, rif: float | None = None, tag: str = "", **tok_kw) -> list:
    tok = base_tokens(**tok_kw)
    jobs = []
    for vt, vp in points:
        k = f"{vt:.1f}_{vp:.1f}{tag}"
        p = {**tok, "VTARGET": vt}
        if "a" in tests and vt != vp:
            jobs.append(("tb_t0_command.spice", f"a_{k}", {**p, "VCMD0": vp}))
        if "b" in tests:
            jobs.append(("tb_t3_interface_model.spice", f"b_{k}", {**p, "VPREV": vp, "RIF": f"{rif:.6g}"}))
        if "c" in tests:
            jobs.append(("tb_t1_connected.spice", f"c_{k}", {**p, "VPREV": vp}))
        if "m" in tests and vt != vp:
            jobs.append(("tb_t2_matched.spice", f"m_{k}", {**p, "VCMD0": vp}))
    return jobs


def load(case_dir: Path) -> dict:
    r = sr.read_wrdata(case_dir / "tran.dat", VECTORS)
    t = r["scale"]
    vref = float(r["out"][t > t[-1] - 20e-9].mean())
    post = t >= T_EVENT - 1e-15
    w = {k: r[k][post] for k in VECTORS}
    w["t"] = t[post] - T_EVENT
    w["vref"] = vref
    pre = (t > T_EVENT - 3e-9) & (t < T_EVENT - 0.5e-9)
    w["out_pre"] = float(r["out"][pre].mean())
    w["samp_pre"] = float(r["samp"][pre].mean())
    w["raw_t"], w["raw_samp"] = t, r["samp"]
    return w


def err_at(w: dict, node: str, t: float) -> float:
    return float(np.interp(t, w["t"], w[node] - w["vref"]))


def settle_time(w: dict, node: str, eps: float = EPS, tmax: float = 200e-9) -> float:
    e = np.abs(w[node] - w["vref"])
    m = w["t"] <= tmax
    bad = np.nonzero(e[m] >= eps)[0]
    return float(w["t"][m][bad[-1]]) if bad.size else 0.0


# ---- bring-up benches ------------------------------------------------------
def bringup(src: str = BASELINE_SRC, tag: str = "", write_csv: bool = True) -> dict:
    tok = base_tokens(src=src)
    dc_dir, ac_dir = sr.run_many([("tb_dc.spice", f"bringup_dc{tag}", tok), ("tb_ac.spice", f"bringup_ac{tag}", tok)])
    logv = sr.read_log_values(dc_dir)
    dc = sr.read_wrdata(dc_dir / "dc_transfer.dat", ["out", "tail"])
    vc = dc["scale"]
    track_err = dc["out"] - vc
    ok = np.abs(track_err) < 1e-3
    dc_range = [float(vc[ok].min()), float(vc[ok].max())] if ok.any() else None
    acv = sr.read_log_values(ac_dir)
    ac = sr.read_wrdata(ac_dir / "ac.dat", ["lgdb", "lgph", "gdb", "gph", "zm", "zph"])
    f = ac["scale"]
    small_signal_csv = RESULTS_DATA / f"sky130_small_signal{tag}.csv"
    with small_signal_csv.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["freq_Hz", "loop_gain_dB", "loop_phase_deg", "Gcmd_dB", "Zout_ohm"])
        for i in range(0, f.size, 2):
            wr.writerow([f"{f[i]:.6g}", f"{ac['lgdb'][i]:.4f}", f"{ac['lgph'][i]:.3f}",
                         f"{ac['gdb'][i]:.4f}", f"{ac['zm'][i]:.3f}"])
    ip = int(np.argmax(ac["zm"]))
    gpk = int(np.argmax(ac["gdb"]))
    m = "@m.xsrc.xm{}.msky130_fd_pr__{}[{}]"
    return {
        "vout_dc_at_0p9_V": logv.get("v(out)"),
        "dc_tracking_error_at_0p9_mV": 1e3 * (logv.get("v(out)", np.nan) - MID_LEVEL),
        "dc_tracking_within_1mV_Vcmd_range_V": dc_range,
        "node_x_V": logv.get("v(xsrc.x)"), "node_d1_V": logv.get("v(xsrc.d1)"),
        "node_tail_V": logv.get("v(xsrc.tail)"),
        "id_M1_A": logv.get(m.format(1, "nfet_01v8_lvt", "id")),
        "id_M6_A": logv.get(m.format(6, "pfet_01v8_lvt", "id")),
        "id_M7_A": logv.get(m.format(7, "nfet_01v8", "id")),
        "gm_M1_S": logv.get(m.format(1, "nfet_01v8_lvt", "gm")),
        "gm_M6_S": logv.get(m.format(6, "pfet_01v8_lvt", "gm")),
        "vds_minus_vdsat_V": {
            "M1": logv.get(m.format(1, "nfet_01v8_lvt", "vds")) - logv.get(m.format(1, "nfet_01v8_lvt", "vdsat")),
            "M2": logv.get(m.format(2, "nfet_01v8_lvt", "vds")) - logv.get(m.format(2, "nfet_01v8_lvt", "vdsat")),
            "M3": logv.get(m.format(3, "pfet_01v8_lvt", "vds")) - logv.get(m.format(3, "pfet_01v8_lvt", "vdsat")),
            "M5": logv.get(m.format(5, "nfet_01v8", "vds")) - logv.get(m.format(5, "nfet_01v8", "vdsat")),
            "M6": logv.get(m.format(6, "pfet_01v8_lvt", "vds")) - logv.get(m.format(6, "pfet_01v8_lvt", "vdsat")),
            "M7": logv.get(m.format(7, "nfet_01v8", "vds")) - logv.get(m.format(7, "nfet_01v8", "vdsat")),
        },
        "loop_unity_freq_Hz": acv.get("f_unity"),
        "phase_margin_deg": 180.0 + acv.get("ph_unity", np.nan),
        "gain_margin_dB": -acv.get("gmargin_db", np.nan),
        "loop_gain_lowfreq_dB": acv.get("a0_db"),
        "Gcmd_peak_dB": float(ac["gdb"][gpk]),
        "Gcmd_minus3dB_Hz": float(f[np.nonzero(ac["gdb"] < -3.0)[0][0]]) if np.any(ac["gdb"] < -3) else None,
        "Zout_lowfreq_ohm": float(ac["zm"][0]),
        "Zout_peak_ohm": float(ac["zm"][ip]),
        "Zout_peak_freq_Hz": float(f[ip]),
    }


# ---- sampler on-resistance, light load ---------------------------------------
def switch_ron() -> dict:
    """DC on-resistance of the transmission gate (half, chosen, double width) versus level."""
    d = sr.run("tb_switch_ron.spice", "switch_ron", {"CORNER": "tt", "TEMP": 27})
    r = sr.read_wrdata(d / "ron.dat", ["ron_half", "ron", "ron_double"])
    v = r["scale"]
    with (RESULTS_DATA / "sky130_switch_ron.csv").open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["level_V", "Ron_half_width_ohm", "Ron_ohm", "Ron_double_width_ohm"])
        for i in range(v.size):
            wr.writerow([f"{v[i]:.3f}", f"{r['ron_half'][i]:.6g}", f"{r['ron'][i]:.6g}", f"{r['ron_double'][i]:.6g}"])
    inr = (v >= 0.6 - 1e-9) & (v <= 1.2 + 1e-9)
    out = {}
    for name in ("ron_half", "ron", "ron_double"):
        x = r[name]
        out[name] = {"max_ohm": float(x[inr].max()), "at_V": float(v[inr][np.argmax(x[inr])]),
                     "min_ohm": float(x[inr].min()),
                     "at_levels_ohm": {f"{lv:.1f}": float(np.interp(lv, v, x)) for lv in (0.6, 0.9, 1.0, 1.2)}}
    return {"width_um": {"ron_half": [7.5, 15], "ron": [15, 30], "ron_double": [30, 60]}, "sweep": out,
            "R_if_ohm": out["ron"]["max_ohm"], "R_if_definition": "maximum DC Ron of the chosen gate over 0.6-1.2 V, tt"}


def light_load_stability() -> dict:
    """Loop margins with only the source's own output parasitics (1 fF)."""
    d = sr.run("tb_ac.spice", "ac_light_load", {**base_tokens(), "CLOAD": LIGHT_LOAD})
    acv = sr.read_log_values(d)
    return {"Cload": LIGHT_LOAD, "loop_unity_freq_Hz": acv.get("f_unity"),
            "phase_margin_deg": 180.0 + acv.get("ph_unity", np.nan),
            "gain_margin_dB": -acv.get("gmargin_db", np.nan)}


# ---- summaries ------------------------------------------------------------------
def point_summary(w: dict, node: str, vt: float, vp: float) -> dict:
    early = w["t"] <= 1e-9
    e40 = err_at(w, node, TACQ)
    return {"Vtarget_V": vt, "Vprev_V": vp, "Vref_V": w["vref"],
            "error_at_Tacq_mV": e40 * 1e3, "pass_at_Tacq": abs(e40) < EPS,
            "last_ge_eps_ns": settle_time(w, node) * 1e9,
            "error_mV": {f"{t:g}": abs(err_at(w, node, t * 1e-9)) * 1e3 for t in REPORT_T_NS},
            "out_error_extreme_first_1ns_mV": float(1e3 * (w["out"][early] - w["vref"])[
                np.argmax(np.abs(w["out"][early] - w["vref"]) * (w["t"][early] > 0.1e-9))]),
            "i_m6_peak_uA": float(w["i_m6"].max() * 1e6), "i_m7_max_uA": float(w["i_m7"].max() * 1e6)}


def summarize(waves: dict, tag: str = "") -> dict:
    out = {"a": {}, "b": {}, "c": {}, "m": {}}
    for name, w in waves.items():
        test, rest = name.split("_", 1)
        if test not in out or not rest.endswith(tag) or (not tag and rest.count("_") != 1):
            continue
        vt, vp = (float(x) for x in rest[: len(rest) - len(tag) if tag else None].split("_"))
        node = "out" if test == "a" else "samp"
        out[test][key(vt, vp)] = point_summary(w, node, vt, vp)
    return {k: v for k, v in out.items() if v}


def interface_vs_connected(nom: dict) -> dict:
    """Test (b) (interface model) against test (c) (transmission gate) at every grid point."""
    per = {}
    for k, c in nom["c"].items():
        b = nom["b"][k]
        diff = b["last_ge_eps_ns"] - c["last_ge_eps_ns"]
        per[k] = {"t_b_ns": b["last_ge_eps_ns"], "t_c_ns": c["last_ge_eps_ns"], "t_b_minus_t_c_ns": diff,
                  "b_is": "agrees" if abs(diff) <= AGREE_NS else ("optimistic" if diff < 0 else "conservative"),
                  "pass_b": b["pass_at_Tacq"], "pass_c": c["pass_at_Tacq"],
                  "error_at_Tacq_b_mV": b["error_at_Tacq_mV"], "error_at_Tacq_c_mV": c["error_at_Tacq_mV"]}
    t = lambda test, vp: nom[test][key(0.9, vp)]["last_ge_eps_ns"]  # noqa: E731
    dt_b, dt_c = t("b", 1.2) - t("b", 0.6), t("c", 1.2) - t("c", 0.6)
    return {"per_point": per, "agree_count": sum(v["b_is"] == "agrees" for v in per.values()),
            "pass_mismatch_points": [k for k, v in per.items() if v["pass_b"] != v["pass_c"]],
            "polarity_at_0p9": {"dt_b_ns": dt_b, "dt_c_ns": dt_c,
                                "source_share": dt_b / dt_c if abs(dt_c) > 1e-12 else None}}


def noncollapse(waves: dict, vt: float, vp: float) -> dict:
    w1, w2 = waves[f"c_{vt:.1f}_{vp:.1f}"], waves[f"m_{vt:.1f}_{vp:.1f}"]
    tgrid = np.linspace(0, 40e-9, 4001)
    d = vt - vp
    e1 = np.interp(tgrid, w1["t"], w1["samp"] - w1["vref"]) / (-d)
    e2 = np.interp(tgrid, w2["t"], w2["samp"] - w2["vref"]) / (-d)
    i = int(np.argmax(np.abs(e1 - e2)))
    return {"max_abs_normalized_difference_0_40ns": float(abs(e1[i] - e2[i])), "at_ns": float(tgrid[i] * 1e9),
            "initial_samp_error_c_mV": 1e3 * (w1["samp_pre"] - w1["vref"]),
            "initial_samp_error_m_mV": 1e3 * (w2["samp_pre"] - w2["vref"]),
            "last_ge_eps_ns_c": settle_time(w1, "samp") * 1e9, "last_ge_eps_ns_m": settle_time(w2, "samp") * 1e9}


def hold_steps() -> dict:
    """Change of the held voltage when the transmission gate opens at the end of Tacq."""
    cases = [(lv, *WIDTHS["chosen"], "chosen") for lv in LEVELS] + [(0.9, *WIDTHS[w], w) for w in ("half", "double")]
    jobs = [("tb_t4_hold.spice", f"hold_{size}_{lv:.1f}",
             {**base_tokens(), "VTARGET": lv, "VPREV": lv, "MN": mn, "MP": mp, "WF": wf})
            for lv, mn, mp, wf, size in cases]
    out = {}
    for (lv, mn, mp, wf, size), d in zip(cases, sr.run_many(jobs)):
        r = sr.read_wrdata(d / "tran.dat", VECTORS)
        t, v = r["scale"], r["samp"]
        before = v[(t >= 63.0e-9) & (t <= 64.8e-9)].mean()
        after = v[(t >= 75e-9) & (t <= 85e-9)].mean()
        out[f"{size}_{lv:.1f}"] = {"size": size, "Wn_um": mn * wf, "Wp_um": mp * wf, "Vtarget_V": lv,
                                   "hold_step_mV": float(1e3 * (after - before)),
                                   "hold_step_over_eps": float((after - before) / EPS)}
    return out


def width_study(nom: dict) -> dict:
    """Connected test (c) at half and double gate width (SWITCH_WIDTH_STUDY.md)."""
    points = FULL_SCALE + [(0.9, 0.9)]
    jobs = []
    for w in ("half", "double"):
        mn, mp, wf = WIDTHS[w]
        jobs += grid_jobs(points, "c", tag=f"_w{w}", MN=mn, MP=mp, WF=wf)
    waves = {d.name: load(d) for d in sr.run_many(jobs)}
    out = {}
    for w in ("half", "chosen", "double"):
        mn, mp, wf = WIDTHS[w]
        res = {}
        for vt, vp in points:
            if w == "chosen":
                v = nom["c"][key(vt, vp)]
            else:
                v = point_summary(waves[f"c_{vt:.1f}_{vp:.1f}_w{w}"], "samp", vt, vp)
            res[key(vt, vp)] = {"last_ge_eps_ns": v["last_ge_eps_ns"], "error_at_Tacq_mV": v["error_at_Tacq_mV"],
                                "pass_at_Tacq": v["pass_at_Tacq"],
                                "turn_on_excursion_mV": v["out_error_extreme_first_1ns_mV"]}
        out[w] = {"Wn_um": mn * wf, "Wp_um": mp * wf, "points": res,
                  "T_fullscale_ns": max(res[key(vt, vp)]["last_ge_eps_ns"] for vt, vp in FULL_SCALE)}
    d_half = out["half"]["T_fullscale_ns"] - out["chosen"]["T_fullscale_ns"]
    d_double = out["double"]["T_fullscale_ns"] - out["chosen"]["T_fullscale_ns"]
    out["driver_dominated_reading"] = {"dT_half_minus_chosen_ns": d_half, "dT_double_minus_chosen_ns": d_double,
                 "driver_dominated": abs(d_half) < 1.0 and abs(d_double) < 1.0}
    z = [out[w]["points"][key(0.9, 0.9)] for w in ("half", "chosen", "double")]
    out["turn_on_reading"] = {"zero_step_last_ge_eps_ns": [p["last_ge_eps_ns"] for p in z],
                 "turn_on_excursion_mV": [p["turn_on_excursion_mV"] for p in z],
                 "both_grow_with_width": all(z[i + 1]["last_ge_eps_ns"] > z[i]["last_ge_eps_ns"] and
                                             abs(z[i + 1]["turn_on_excursion_mV"]) > abs(z[i]["turn_on_excursion_mV"])
                                             for i in range(2))}
    return out


def write_data(waves: dict, nom: dict) -> None:
    tgrid = np.round(np.arange(-2e-9, 80.0001e-9, 50e-12), 15)
    names = sorted(n for n in waves if n.count("_") == 2 and n[0] in "abcm")
    with (RESULTS_DATA / "sky130_waveforms_tt.csv").open("w", newline="") as fh:
        wr = csv.writer(fh)
        header = ["t_after_event_ns"]
        for n in names:
            header += [f"{n}_out_err_mV", f"{n}_samp_err_mV", f"{n}_x_V"]
        wr.writerow(header)
        cols = [tgrid * 1e9]
        for n in names:
            w = waves[n]
            for node, scale, ref in (("out", 1e3, w["vref"]), ("samp", 1e3, w["vref"]), ("xnode", 1.0, 0.0)):
                cols.append(scale * (np.interp(tgrid, w["t"], w[node], left=np.nan) - ref))
        for row in zip(*cols):
            wr.writerow([f"{v:.6g}" for v in row])
    with (RESULTS_DATA / "sky130_grid_error_tt.csv").open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["test", "Vtarget_V", "Vprev_V"] + [f"error_mV_at_{t:g}ns" for t in T_GRID_NS])
        for test in ("a", "b", "c"):
            for k, v in nom[test].items():
                w = waves[f"{test}_{v['Vtarget_V']:.1f}_{v['Vprev_V']:.1f}"]
                node = "out" if test == "a" else "samp"
                wr.writerow([test, f"{v['Vtarget_V']:.1f}", f"{v['Vprev_V']:.1f}"]
                            + [f"{abs(err_at(w, node, t * 1e-9)) * 1e3:.5g}" for t in T_GRID_NS])


# ---- figures -----------------------------------------------------------------------
def style(ax) -> None:
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK_2)
    ax.tick_params(colors=INK_2, labelcolor=INK)


def figure_block_tests(waves: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6), constrained_layout=True)
    t = np.arange(0.25, 40.001, 0.25)
    floor = 1e-3
    titles = {(1.2, 0.6): "Full-scale step up: 0.6 → 1.2 V\n(driver supplies charge)",
              (0.6, 1.2): "Full-scale step down: 1.2 → 0.6 V\n(driver sinks charge)"}
    for ax, (vt, vp) in zip(axes, FULL_SCALE):
        k = f"{vt:.1f}_{vp:.1f}"
        series = ((waves[f"a_{k}"], "out", COMMAND_BLUE, "--", "(a) input step, 1 pF hard-wired"),
                  (waves[f"b_{k}"], "samp", MODEL_GREEN, "-", "(b) output-port test, switch as R_if"),
                  (waves[f"c_{k}"], "samp", DISTURB_ORANGE, "-", "(c) connected, transmission gate"))
        for w, node, color, ls, lab in series:
            e = np.maximum(np.abs([err_at(w, node, x * 1e-9) for x in t]) * 1e3, floor)
            ts = settle_time(w, node) * 1e9
            ax.plot(t, e, color=color, lw=2.0, ls=ls, label=f"{lab}  [last ≥ ε: {ts:.1f} ns]")
            ax.plot([ts], [EPS * 1e3], marker="o", color=color, ms=5, zorder=5)
        ax.axhline(EPS * 1e3, color=INK, lw=1.1)
        ax.text(0.5, EPS * 1e3 * 0.75, "ε = 0.29 mV", ha="left", va="top", fontsize=8, color=INK)
        ax.axvline(TACQ * 1e9, color=INK_2, lw=0.8, ls=":")
        ax.set_yscale("log")
        ax.set_ylim(floor, 1000)
        ax.set_xlim(0, 40)
        ax.set_title(titles[(vt, vp)], fontsize=9.5, color=INK)
        ax.set_xlabel("Time after the sampling event (ns)", color=INK)
        ax.legend(fontsize=7.6, frameon=False, loc="upper right")
        style(ax)
    axes[0].set_ylabel("|error| (mV)", color=INK)
    fig.suptitle("SKY130: two block tests of the driver and the connected test, full-scale transitions",
                 fontsize=11, color=INK)
    fig.text(0.5, -0.02,
             "(a) and (b) are block tests of the driver; (c) connects the driver to the real sampling network. "
             "(b) represents the switch by one linear resistance R_if,\nits maximum DC on-resistance over the range. "
             "Dots: last time |error| ≥ ε. Dotted line: Tacq = 40 ns. tt, 27 °C. Gate edges 0.2 ns.\n"
             "(Testbenches: tb_t0_command.spice, tb_t3_interface_model.spice, tb_t1_connected.spice.)",
             ha="center", va="top", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_block_tests_and_connected.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


def figure_turn_on(waves: dict) -> None:
    """Zero-step points: the turn-on disturbance of the transmission gate, absent from the R_if model."""
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), constrained_layout=True)
    colors = {0.6: "#7a4fb0", 0.9: DISTURB_ORANGE, 1.2: "#8a5a00"}
    for lv in LEVELS:
        w = waves[f"c_{lv:.1f}_{lv:.1f}"]
        m = w["t"] <= 15e-9
        axes[0].plot(w["t"][m] * 1e9, (w["out"][m] - w["vref"]) * 1e3, color=colors[lv], lw=1.8,
                     label=f"target = previous = {lv:.1f} V")
        e = np.maximum(np.abs(w["samp"][m] - w["vref"]) * 1e3, 1e-3)
        ts = settle_time(w, "samp") * 1e9
        axes[1].plot(w["t"][m] * 1e9, e, color=colors[lv], lw=1.8, label=f"{lv:.1f} V  [last ≥ ε: {ts:.1f} ns]")
        axes[1].plot([ts], [EPS * 1e3], marker="o", color=colors[lv], ms=5, zorder=5)
    axes[0].axhline(0, color=INK_2, lw=0.8)
    axes[0].set_xlim(-0.5, 15)
    axes[0].set_ylabel("Vout − Vref (mV)", color=INK)
    axes[0].set_title("Driver output after the gate closes\n(no charge to transfer: Vprev = Vtarget)", fontsize=9.5,
                      color=INK)
    axes[1].axhline(EPS * 1e3, color=INK, lw=1.1)
    axes[1].text(14.8, EPS * 1e3 * 1.25, "ε = 0.29 mV", ha="right", va="bottom", fontsize=8, color=INK)
    axes[1].set_yscale("log")
    axes[1].set_ylim(1e-3, 100)
    axes[1].set_xlim(0, 15)
    axes[1].set_ylabel("|Vsamp − Vref| (mV)", color=INK)
    axes[1].set_title("Sampling-capacitor error, connected test (c)\n(test (b) with R_if: only the driver's DC tracking "
                      "error, below ε within 0.8 ns)", fontsize=9.5, color=INK)
    for ax in axes:
        ax.set_xlabel("Time after the sampling event (ns)", color=INK)
        ax.legend(fontsize=7.8, frameon=False, loc="upper right")
        style(ax)
    fig.suptitle("SKY130: turn-on disturbance of the transmission gate at the three zero-step points", fontsize=11,
                 color=INK)
    fig.text(0.5, -0.02, "Connected test (c), chosen gate (15 / 30 µm), complementary 0.2 ns gate edges, tt, 27 °C. "
             "(Testbench: tb_t1_connected.spice.)", ha="center", va="top", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_turn_on_disturbance.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


def figure_switch_width(ron: dict, hold: dict, width: dict) -> None:
    """One design variable, three consequences: on-resistance, connected acquisition, turn-off hold step."""
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1.15, 1, 1]})
    ax = axes[0]
    cols = {"level_V": [], "Ron_half_width_ohm": [], "Ron_ohm": [], "Ron_double_width_ohm": []}
    with (RESULTS_DATA / "sky130_switch_ron.csv").open() as fh:
        for row in csv.DictReader(fh):
            for c in cols:
                cols[c].append(float(row[c]))
    ax.axvspan(0.6, 1.2, color=GRID, alpha=0.5, lw=0)
    ax.plot(cols["level_V"], cols["Ron_half_width_ohm"], color=DISTURB_ORANGE, lw=1.2, ls="--",
            label="half (7.5 / 15 µm)")
    ax.plot(cols["level_V"], cols["Ron_ohm"], color=DISTURB_ORANGE, lw=2.2, label="chosen (15 / 30 µm)")
    ax.plot(cols["level_V"], cols["Ron_double_width_ohm"], color=DISTURB_ORANGE, lw=1.2, ls=":",
            label="double (30 / 60 µm)")
    ax.axhline(ron["R_if_ohm"], color=MODEL_GREEN, lw=1.6, label=f"R_if = {ron['R_if_ohm']:.0f} Ω (chosen, maximum)")
    ax.set_yscale("log")
    ax.set_xlim(0.5, 1.3)
    ax.set_xlabel("Level at both gate terminals (V)", color=INK)
    ax.set_ylabel("DC on-resistance (Ω)", color=INK)
    ax.set_title("1  On-resistance falls with width\n(shaded: operating range)", fontsize=9.5, color=INK)
    ax.legend(fontsize=7.2, frameon=False, loc="upper left")
    style(ax)
    wn = [width[w]["Wn_um"] for w in ("half", "chosen", "double")]
    ax = axes[1]
    for (vt, vp), color, lab in (((0.6, 1.2), COMMAND_BLUE, "full-scale step down"),
                                 ((1.2, 0.6), MODEL_GREEN, "full-scale step up"),
                                 ((0.9, 0.9), DISTURB_ORANGE, "zero step at 0.9 V (turn-on only)")):
        ax.plot(wn, [width[w]["points"][key(vt, vp)]["last_ge_eps_ns"] for w in ("half", "chosen", "double")],
                marker="o", color=color, lw=1.8, label=lab)
    ax.axhline(TACQ * 1e9, color=INK_2, lw=0.8, ls=":")
    ax.text(wn[0], TACQ * 1e9 - 0.6, "Tacq = 40 ns", fontsize=8, color=INK_2, va="top")
    ax.set_xscale("log")
    ax.set_xticks(wn, [f"{x:g}" for x in wn])
    ax.set_ylim(0, 42)
    ax.set_xlabel("NMOS width (µm); PMOS twice as wide", color=INK)
    ax.set_ylabel("Last time |Vsamp − Vref| ≥ ε (ns)", color=INK)
    ax.set_title("2  Connected acquisition settling\n(test (c), tt, 27 °C)", fontsize=9.5, color=INK)
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.legend(fontsize=7.4, frameon=False, loc="center", bbox_to_anchor=(0.5, 0.6))
    style(ax)
    ax = axes[2]
    hs = [hold[f"{w}_0.9"]["hold_step_mV"] for w in ("half", "chosen", "double")]
    ax.plot(wn, hs, marker="o", color=DISTURB_ORANGE, lw=1.8, label="held level 0.9 V, three widths")
    for lv, mk in ((0.6, "v"), (1.2, "^")):
        h = hold[f"chosen_{lv:.1f}"]["hold_step_mV"]
        ax.plot([wn[1]], [h], marker=mk, color=INK_2, ls="none", ms=7,
                label=f"chosen gate, held level {lv:.1f} V ({h:+.1f} mV)")
    ax.axhline(0, color=INK_2, lw=0.8)
    ax.set_xscale("log")
    ax.set_xticks(wn, [f"{x:g}" for x in wn])
    ax.set_ylim(-9, 10.5)
    ax.set_xlabel("NMOS width (µm); PMOS twice as wide", color=INK)
    ax.set_ylabel("Held-voltage step at turn-off (mV)", color=INK)
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_title("3  Raw turn-off hold step, before correction\n(magnitude grows with width; sign depends on level)",
                 fontsize=9.5, color=INK)
    ax.legend(fontsize=7.2, frameon=False, loc="upper left")
    style(ax)
    fig.suptitle("SKY130: one design variable, the width of the transmission gate, acting on three quantities",
                 fontsize=11, color=INK)
    fig.text(0.5, -0.02, "Panel 1: DC sweep, both terminals at the level, gates fully on. Panel 2: connected test (c) "
             "(SWITCH_WIDTH_STUDY.md). Panel 3: mean held voltage 10–20 ns after the gate opens minus its value just before (zero step).\n"
             "The raw step includes offset and gain, which the two-point correction of the held-sample check removes, so no limit is drawn. "
             "(Testbenches: tb_switch_ron.spice, tb_t1_connected.spice, tb_t4_hold.spice.)",
             ha="center", va="top", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_switch_width.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


def figure_matched(waves: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 6.6), sharex=True, constrained_layout=True)
    for col, (vt, vp) in enumerate(FULL_SCALE):
        k = f"{vt:.1f}_{vp:.1f}"
        w1, w2 = waves[f"c_{k}"], waves[f"m_{k}"]
        d = vt - vp
        ax = axes[0, col]
        ax.plot(w2["t"] * 1e9, (w2["samp"] - w2["vref"]) / (-d), color=COMMAND_BLUE, lw=2,
                label="(m) input step, gate already closed")
        ax.plot(w1["t"] * 1e9, (w1["samp"] - w1["vref"]) / (-d), color=DISTURB_ORANGE, lw=2,
                label="(c) charged Cs connected, input held")
        ax.axhline(0, color=INK_2, lw=0.8)
        ax.axvline(TACQ * 1e9, color=INK_2, lw=0.8, ls=":")
        ax.set_ylim(-0.35, 1.1)
        side = "driver supplies charge" if d > 0 else "driver sinks charge"
        ax.set_title(f"{vp:.1f} → {vt:.1f} V  ({side})", fontsize=10, color=INK)
        if col == 0:
            ax.set_ylabel("Sampling-capacitor error\n/ initial error", color=INK)
        ax.legend(loc="upper right", fontsize=8, frameon=False)
        style(ax)
        ax = axes[1, col]
        ax.plot(w2["t"] * 1e9, w2["xnode"], color=COMMAND_BLUE, lw=2, label="(m) input step")
        ax.plot(w1["t"] * 1e9, w1["xnode"], color=DISTURB_ORANGE, lw=2, label="(c) connection event")
        ax.axhline(w1["xnode"][-1], color=INK_2, lw=0.8)
        ax.set_xlabel("Time after the event (ns)", color=INK)
        if col == 0:
            ax.set_ylabel("Internal node x (V)\n(M6 gate / first-stage output)", color=INK)
        ax.legend(loc="upper right" if d > 0 else "lower right", fontsize=8, frameon=False)
        style(ax)
    axes[0, 0].set_xlim(-1, 40)
    fig.suptitle("SKY130 driver: input step versus connection of a charged sampling capacitor", fontsize=11,
                 color=INK)
    fig.text(0.5, -0.02,
             "Matched in each column: same transmission gate and Cs = 1 pF, same initial sampling-capacitor error, "
             "same time axis.\nThe control steps the external input with the gate already closed; the connected test "
             "holds the input and applies stored charge at the output port. tt, 27 °C, VDD = 1.8 V. Dotted line: "
             "Tacq = 40 ns.\n(Testbenches: tb_t2_matched.spice, tb_t1_connected.spice.)",
             ha="center", va="top", fontsize=8, color=INK_2)
    for ext in ("png", "svg"):
        fig.savefig(RESULTS_FIG / f"figure_sky130_input_step_vs_connection.{ext}", dpi=180, bbox_inches="tight",
                    metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)


def environment() -> dict:
    lib = sr.pdk_library()
    sources = lib.parents[2] / "SOURCES"
    pkgs = {}
    for p in ("numpy", "scipy", "matplotlib", "nbformat", "nbconvert"):
        try:
            pkgs[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            pkgs[p] = None
    smoke = sr.read_log_values(sr.run("tb_smoke_mos.spice", "smoke_mos", base_tokens()))
    return {
        "smoke_test_op_currents_A": {"nfet_01v8_W2_L0p5": smoke.get("i(vdn)"),
                                     "pfet_01v8_W2_L0p5": smoke.get("i(vdp)")},
        "os": platform.platform(),
        "python": platform.python_version(),
        "python_packages": pkgs,
        "ngspice": sr.ngspice_version(),
        "sky130_library": "sky130A/libs.tech/ngspice/sky130.lib.spice",
        "sky130_sources": sources.read_text().strip() if sources.is_file() else "unknown",
        "corner_nominal": "tt",
        "temperature_nominal_C": 27,
    }


def main() -> None:
    RESULTS_DATA.mkdir(parents=True, exist_ok=True)
    RESULTS_FIG.mkdir(parents=True, exist_ok=True)
    env = environment()
    print("environment:", env["ngspice"], "|", env["sky130_sources"])
    bu = bringup()
    print(f"bring-up: UGF {bu['loop_unity_freq_Hz'] / 1e6:.1f} MHz, PM {bu['phase_margin_deg']:.1f} deg")
    ron = switch_ron()
    light = light_load_stability()
    rif = ron["R_if_ohm"]
    print(f"transmission gate: R_if = max Ron(0.6-1.2 V) = {rif:.1f} Ohm at {ron['sweep']['ron']['at_V']:.2f} V; "
          f"light load: PM {light['phase_margin_deg']:.1f} deg")

    grid = [(vt, vp) for vt in LEVELS for vp in LEVELS]
    jobs = grid_jobs(grid, "abc", rif=rif) + grid_jobs(FULL_SCALE, "m")
    jobs += grid_jobs(FULL_SCALE, "bc", rif=rif, tag="_dt10p", tmax="10p")
    jobs += grid_jobs(FULL_SCALE, "c", tag="_rt5", reltol="1e-5")
    for corner in ("ss", "ff"):
        jobs += grid_jobs(FULL_SCALE, "abc", rif=rif, tag=f"_{corner}", corner=corner)
    dirs = sr.run_many(jobs)
    waves = {d.name: load(d) for d in dirs}

    nom = summarize(waves)
    matched = {key(vt, vp): noncollapse(waves, vt, vp) for vt, vp in FULL_SCALE}
    numerics = {}
    for vt, vp in FULL_SCALE:
        k = f"{vt:.1f}_{vp:.1f}"
        ref_c, ref_b = waves[f"c_{k}"], waves[f"b_{k}"]
        numerics[key(vt, vp)] = {
            "last_ge_eps_ns": {"c": settle_time(ref_c, "samp") * 1e9, "c_dt10p": settle_time(waves[f"c_{k}_dt10p"], "samp") * 1e9,
                               "c_reltol1e-5": settle_time(waves[f"c_{k}_rt5"], "samp") * 1e9,
                               "b": settle_time(ref_b, "samp") * 1e9, "b_dt10p": settle_time(waves[f"b_{k}_dt10p"], "samp") * 1e9},
            "error_at_Tacq_mV": {"c": err_at(ref_c, "samp", TACQ) * 1e3, "c_dt10p": err_at(waves[f"c_{k}_dt10p"], "samp", TACQ) * 1e3,
                                 "c_reltol1e-5": err_at(waves[f"c_{k}_rt5"], "samp", TACQ) * 1e3,
                                 "b": err_at(ref_b, "samp", TACQ) * 1e3, "b_dt10p": err_at(waves[f"b_{k}_dt10p"], "samp", TACQ) * 1e3},
        }
    dts = [abs(v["last_ge_eps_ns"][x] - v["last_ge_eps_ns"][x.split("_")[0]]) for v in numerics.values()
           for x in ("c_dt10p", "c_reltol1e-5", "b_dt10p")]
    des = [abs(v["error_at_Tacq_mV"][x] - v["error_at_Tacq_mV"][x.split("_")[0]]) for v in numerics.values()
           for x in ("c_dt10p", "c_reltol1e-5", "b_dt10p")]
    numerics["max_change_last_ge_eps_ns"] = max(dts)
    numerics["max_change_error_at_Tacq_mV"] = max(des)
    numerics["within_preregistered_limits"] = max(dts) <= NUM_SETTLE_NS and max(des) <= NUM_ERR_MV
    comparison = interface_vs_connected(nom)
    corners = {c: summarize({k: v for k, v in waves.items() if k.endswith(f"_{c}")}, tag=f"_{c}") for c in ("ss", "ff")}
    hold = hold_steps()
    width = width_study(nom)

    # Conditional second-stage variation (DESIGN_BRIEF.md Section 5).
    up, down = nom["c"][key(1.2, 0.6)], nom["c"][key(0.6, 1.2)]
    sink_limited = (down["last_ge_eps_ns"] > up["last_ge_eps_ns"] and down["i_m7_max_uA"] < 1.2 * 1e6 * bu["id_M7_A"])
    variation = {"applied": False, "condition_met": sink_limited}
    if sink_limited:
        bu_v = bringup(src=VARIATION_SRC, tag="_2x")
        vdirs = sr.run_many(grid_jobs(FULL_SCALE, "ac", tag="_2x", src=VARIATION_SRC))
        vwaves = {d.name: load(d) for d in vdirs}
        variation = {"applied": True, "condition_met": True,
                     "reason": "full-scale sink transition slower than source transition while M7 stays at its bias",
                     "second_stage_bias_uA": 1e6 * bu_v["id_M7_A"], "phase_margin_deg": bu_v["phase_margin_deg"],
                     "loop_unity_freq_Hz": bu_v["loop_unity_freq_Hz"], "results": summarize(vwaves, tag="_2x")}

    summary = {
        "environment": env, "bringup": bu,
        "design_brief": {"levels_V": LEVELS, "epsilon_mV": EPS * 1e3, "Tacq_ns": TACQ * 1e9,
                         "Cs_pF": 1.0, "switch": "CMOS transmission gate, nfet_01v8 15 um / pfet_01v8 30 um, L 0.15 um",
                         "clock_edge_ns": 0.2, "R_if_ohm": rif},
        "nominal_tt_27C": nom, "interface_vs_connected": comparison, "matched_c_vs_m": matched,
        "numerical_check": numerics, "corner_sanity_27C": corners, "hold_step": hold, "switch_width": width, "second_stage_variation": variation,
        "switch_ron": ron, "light_load_stability": light}
    (RESULTS_DATA / "sky130_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    write_data(waves, nom)
    figure_block_tests(waves)
    figure_turn_on(waves)
    figure_switch_width(ron, hold, width)
    figure_matched(waves)

    for test in ("a", "b", "c"):
        for k, v in nom[test].items():
            print(f"({test}) {k}: error at 40 ns {v['error_at_Tacq_mV']:+.4f} mV ({'PASS' if v['pass_at_Tacq'] else 'FAIL'}), "
                  f"last >= eps {v['last_ge_eps_ns']:.2f} ns")
    for k, v in comparison["per_point"].items():
        print(f"(b) vs (c) {k}: {v['t_b_ns']:.2f} / {v['t_c_ns']:.2f} ns -> {v['b_is']}")
    print("polarity at 0.9 V:", comparison["polarity_at_0p9"])
    for k, v in matched.items():
        print(f"matched {k}: max|dn|={v['max_abs_normalized_difference_0_40ns']:.3f} at {v['at_ns']:.2f} ns")
    print("numerics:", numerics["max_change_last_ge_eps_ns"], numerics["max_change_error_at_Tacq_mV"],
          numerics["within_preregistered_limits"])
    for k, v in hold.items():
        print(f"hold step {k}: {v['hold_step_mV']:+.3f} mV ({v['hold_step_over_eps']:+.1f} x eps)")
    for w in ("half", "chosen", "double"):
        print(f"width {w}: " + "; ".join(f"{k} {v['last_ge_eps_ns']:.2f} ns, {v['error_at_Tacq_mV']:+.4f} mV, "
                                         f"turn-on {v['turn_on_excursion_mV']:+.1f} mV"
                                         for k, v in width[w]["points"].items()))
    print("switch width:", width["driver_dominated_reading"], width["turn_on_reading"])
    print("variation:", {k: v for k, v in variation.items() if k != "results"})


if __name__ == "__main__":
    main()
