"""Notebook figures (matplotlib, static).  One style for all charts:
validated categorical palette in fixed order, recessive grid, direct labels."""
from __future__ import annotations

import warnings
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MODEL_COLOR = {"M0": CAT[0], "M1": CAT[1], "M2": CAT[2], "SPICE": INK}


def style():
    matplotlib.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK, "xtick.color": MUTED,
        "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.axisbelow": True, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 2,
        "lines.markersize": 7, "legend.frameon": False, "figure.dpi": 110})


def _label_end(ax, x, y, text, color):
    ax.annotate(text, (x, y), xytext=(5, 0), textcoords="offset points", va="center", color=INK2, fontsize=9)


# ------------------------------------------------------------------ 1 hazard demo
def hazard_waveforms(trace_ideal, trace_timed, nets, t_end_ps, title):
    style()
    fig, axes = plt.subplots(len(nets), 1, figsize=(7.5, 0.75 * len(nets) + 0.8), sharex=True)
    for ax, n in zip(axes, nets):
        for tr, color, lw, lab in ((trace_ideal, MUTED, 1.5, "zero-delay"), (trace_timed, CAT[0], 2, "timed")):
            t, v = [0.0], [tr["init"][n]]
            for (tt, nn, val) in tr["events"]:
                if nn == n:
                    t += [tt, tt]; v += [v[-1], val]
            t.append(t_end_ps); v.append(v[-1])
            ax.plot(t, np.array(v) + (0.04 if lab == "zero-delay" else 0), color=color, lw=lw, label=lab,
                    drawstyle="default")
        ax.set_yticks([0, 1]); ax.set_ylim(-0.25, 1.35); ax.set_ylabel(n, rotation=0, ha="right", va="center")
        ax.grid(False)
    axes[0].legend(loc="upper left", bbox_to_anchor=(1.0, 1.15), fontsize=9)
    axes[-1].set_xlabel("time (ps)")
    axes[0].set_title(title)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ 2 SPICE pulse curves
def pulse_curves(cells=("inv_1", "nand2_1", "buf_1", "xor2_1")):
    style()
    c = _read_csv(ROOT / "data/m2/m2_curves.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    grid = np.linspace(0, 3, 61)
    for i, cell in enumerate(cells):
        for pol, ls in (("positive", "-"), ("negative", "--")):
            rows = [r for r in c if r["cell"] == cell and r["polarity"] == pol]
            keys = sorted({(r["slew_ps"], r["load_ff"]) for r in rows})
            pk, se = [], []
            for k in keys:
                g = sorted((float(r["r"]), float(r["peak_frac"]), float(r["S_E"])) for r in rows
                           if (r["slew_ps"], r["load_ff"]) == k)
                x = np.array([q[0] for q in g])
                pk.append(np.interp(grid, x, [q[1] for q in g], left=np.nan, right=np.nan))
                se.append(np.interp(grid, x, [q[2] for q in g], left=np.nan, right=np.nan))
            for ax, arr in ((a1, pk), (a2, se)):
                with warnings.catch_warnings():       # grid points outside every sweep -> NaN
                    warnings.simplefilter("ignore", RuntimeWarning)
                    med = np.nanmedian(np.vstack(arr), axis=0)
                ax.plot(grid, med, color=CAT[i], ls=ls, lw=1.6 if ls == "-" else 1.2,
                        label=cell if pol == "positive" else None)
    for ax in (a1, a2):
        ax.axvline(1.0, color=MUTED, lw=1, ls="--")
        ax.set_xlabel("input pulse width / cell delay   (r = w / t_pd)")
        ax.set_xlim(0, 3.0)
    a2.plot([], [], color=INK2, ls="-", label="positive pulse")
    a2.plot([], [], color=INK2, ls="--", label="negative pulse")
    a2.legend(loc="lower right", fontsize=8.5, ncol=2)
    a1.axhline(0.5, color=AXIS, lw=1)
    a1.text(1.02, 0.03, "M1 assumes\nfilter at r = 1", color=MUTED, fontsize=8)
    a1.set_ylabel("output peak excursion (× VDD)")
    a1.set_title("Does a pulse survive the gate? (ngspice, SKY130;\nmedian over slews and loads, per pulse polarity)", fontsize=10)
    a2.set_ylabel("supply energy / full-cycle energy"); a2.set_title("…and what does it cost?")
    fig.tight_layout()
    return fig


def r_filter_dots():
    style()
    rows = _read_csv(ROOT / "data/m2/m2_conditions.csv")
    cells = sorted({r["cell"] for r in rows})
    fig, ax = plt.subplots(figsize=(7.5, 0.33 * len(cells) + 1.2))
    for j, pol in enumerate(["positive", "negative"]):
        for i, cell in enumerate(cells):
            v = [float(r["r_filter"]) for r in rows if r["cell"] == cell and r["polarity"] == pol and r["r_filter"] != ""]
            v = [x for x in v if np.isfinite(x)]
            if v:
                y = i + (0.15 if j else -0.15)
                ax.plot([min(v), max(v)], [y, y], color=CAT[j], lw=2, alpha=0.5)
                ax.plot(np.median(v), y, "o", color=CAT[j], ms=7, label=f"{pol} output pulse" if i == 0 else None)
    ax.axvline(1.0, color=MUTED, ls="--", lw=1); ax.text(1.01, -0.6, "M1 (r = 1)", color=MUTED, fontsize=8)
    ax.set_yticks(range(len(cells))); ax.set_yticklabels(cells); ax.set_xlabel("rejection threshold r_filter (× cell delay)")
    ax.set_title("SPICE-calibrated rejection thresholds (median and range over slew/load)")
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, fontsize=9)
    ax.set_title("SPICE-calibrated rejection thresholds (median, range over slew/load)", pad=22)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ 3 reality checks
def reality_check():
    style()
    rows = _read_csv(ROOT / "data/b8/b8dq_schematic_control_results.csv")
    eff = _read_csv(ROOT / "data/b8/b8dq_factorial_effects_stratified.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6))
    for i, tr in enumerate(["input_rise_output_fall", "input_fall_output_rise"]):
        g = sorted((float(r["load_ff"]), float(r["delay_rel_error_pct"])) for r in rows if r["transition"] == tr
                   and float(r["spice_delay_ps"]) > 0)
        a1.plot([q[0] for q in g], [q[1] for q in g], "o", color=CAT[i], label=tr.replace("_", " "), alpha=0.85)
    a1.axhline(0, color=AXIS, lw=1); a1.set_xscale("log")
    a1.set_xlabel("load (fF)"); a1.set_ylabel("SPICE vs Liberty delay error (%)")
    a1.set_title("INV1: open Liberty vs open SPICE timing"); a1.legend(fontsize=8)
    doms = ["A", "Y", "P", "G"]          # B8DQ factor ids: input, output, VPWR, VGND
    for i, tr in enumerate(["input_rise_output_fall", "input_fall_output_rise"]):
        vals = []
        for d in doms:
            v = [float(r["mean"]) for r in eff if r["effect_id"] == d and r["metric"] == "tpd_ps"
                 and r["transition"] == tr and r["load_ff"] == "" and r["input_slew_ps"] == ""]
            vals.append(v[0] if v else 0.0)
        x = np.arange(len(doms)) + (i - 0.5) * 0.36
        a2.bar(x, vals, width=0.34, color=CAT[i], edgecolor=SURFACE, linewidth=2, label=tr.replace("_", " "))
        for xx, vv in zip(x, vals):
            a2.text(xx, vv, f"{vv:.1f}", ha="center", va="bottom", fontsize=8, color=INK2)
    a2.set_xticks(range(len(doms))); a2.set_xticklabels(["input A", "output Y", "VPWR", "VGND"])
    a2.set_ylabel("added delay from extracted R (ps)"); a2.set_title("Where the mismatch comes from (PEX R ablation)")
    a2.set_axisbelow(True)
    a2.legend(fontsize=8)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ 4 energy split and validation
def glitch_fraction():
    style()
    d = json.loads((ROOT / "data/notebook/bench_energy.json").read_text())
    benches = list(d)
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    for i, m in enumerate(["M0", "M1", "M2"]):
        x = np.arange(len(benches)) + (i - 1) * 0.26
        v = [100 * d[b][m]["glitch_fraction"] for b in benches]
        ax.bar(x, v, width=0.24, color=MODEL_COLOR[m], edgecolor=SURFACE, linewidth=2, label=m)
        for xx, vv in zip(x, v):
            ax.text(xx, vv + 0.6, f"{vv:.0f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(range(len(benches))); ax.set_xticklabels([f"{b}\n({d[b]['cells']} cells)" for b in benches])
    ax.set_ylabel("glitch share of dynamic energy (%)")
    ax.set_title("How much energy goes into glitches? (300 random vectors)")
    ax.legend(title="pulse model", fontsize=9)
    fig.tight_layout()
    return fig


def trail_slew():
    """Trailing-edge slew: rejection threshold vs the slew of the edge that ends the pulse (ngspice)."""
    style()
    d = json.loads((ROOT / "data/m2/trail_slew_sweep.json").read_text())
    rows, alpha = d["rows"], d["alpha"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6), gridspec_kw=dict(width_ratios=[1, 1.4]))
    ds = [0, 80, 260]
    inp_pos = {(r["cell"], r["out_polarity"]): r["input_pulse"] == "pos" for r in rows}   # input pulse of each arc
    edge = lambda c, pol: "falls" if inp_pos[(c, pol)] else "rises"                        # noqa: E731  closing input edge
    for k, (cell, pol, col) in enumerate([("nor2_1", "positive", CAT[0]), ("inv_1", "positive", CAT[2]),
                                          ("nor2_1", "negative", CAT[1]), ("and2_1", "positive", CAT[3])]):
        r = next(x for x in rows if x["cell"] == cell and x["out_polarity"] == pol and x["slew_ps"] == 40.0
                 and x["load_ff"] == 10.0)
        w = r["w_threshold_ps"]
        a1.plot(ds, [x - w[0] for x in w], "-o", color=col, ms=5, lw=1.8,
                label=f"{cell.split('_')[0]}, closing edge {edge(cell, pol)} (α {r['alpha']:.2f})")
    a1.set_xlabel("closing-edge slew − opening-edge slew (ps)")
    a1.set_ylabel("extra width needed to pass (ps)")
    a1.set_title("A slow closing edge kills wider pulses\n(one condition: 40 ps slew, 10 fF)", fontsize=10)
    a1.legend(fontsize=7.5, loc="upper left")
    cells = list(alpha)
    x = np.arange(len(cells))
    rise = [next(v for p, v in alpha[c].items() if edge(c, p) == "rises") for c in cells]
    fall = [next(v for p, v in alpha[c].items() if edge(c, p) == "falls") for c in cells]
    a2.bar(x - 0.2, rise, 0.4, color=CAT[0], label="closing input edge rises")
    a2.bar(x + 0.2, fall, 0.4, color=CAT[1], label="closing input edge falls")
    a2.set_xticks(x); a2.set_xticklabels([c.replace("_1", "").replace("_0", "") for c in cells], rotation=45, fontsize=8)
    a2.set_ylabel("α (fraction of the slew difference)")
    a2.set_title("α per cell (median of 4 slew/load conditions)", fontsize=10)
    a2.set_ylim(0, 0.5)
    for xi, (r_, f_) in enumerate(zip(rise, fall)):
        for dx, v_ in ((-0.2, r_), (0.2, f_)):
            if v_ < 0.005:
                a2.text(xi + dx, 0.01, "0", ha="center", fontsize=7, color=INK2)
    a2.legend(fontsize=8, ncol=2, loc="upper center")
    fig.tight_layout()
    return fig


def spice_validation():
    """GlitchScope vs whole-circuit ngspice.  Reference: the parasitic-extracted cells where that run
    exists (filled markers), else the PDK's schematic cells; hollow grey: M2 vs the schematic cells."""
    style()
    names = [("rca8", "rca8"), ("ks8", "ks8"), ("mul4", "mul4"), ("c432", "ISCAS'85 c432"),
             ("c880", "ISCAS'85 c880"), ("arraymul8", "8×8 NOR array mult."), ("mac", "MAC (real flops)")]
    names = [n for n in names if (ROOT / f"data/bench/spice_validation_{n[0]}.json").exists()]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 0.5 * len(names) + 1.5))
    for j, (f, lab) in enumerate(names):
        sch = json.loads((ROOT / f"data/bench/spice_validation_{f}.json").read_text())
        pf = ROOT / f"data/bench/spice_validation_{f}_pex.json"
        v = json.loads(pf.read_text()) if pf.exists() else sch
        K = lambda d, m, e: d.get(f"{m}+{e}", d.get(f"{m}_{e}"))
        G = lambda r: r.get("glitch_transition_ratio", r.get("glitch_ratio"))
        for i, m in enumerate(["M0", "M1", "M2"]):
            a1.plot(G(K(v, m, "LIB")), j + (i - 1) * 0.18, "o", color=MODEL_COLOR[m], label=m if j == 0 else None)
        if pf.exists():
            a1.plot(G(K(sch, "M2", "LIB")), j + 0.36, "o", mfc="none", mec=INK2, mew=1.2,
                    label="M2 vs schematic cells" if j == 0 else None)
        a2.plot(K(v, "M0", "LIB")["E_ratio"], j - 0.12, "o", color=MODEL_COLOR["M0"],
                label="M0" if j == 0 else None)
        a2.plot(K(v, "M2", "CAL")["E_ratio"], j + 0.12, "o", color=MODEL_COLOR["M2"],
                label="M2 (GlitchScope default)" if j == 0 else None)
        if pf.exists():
            a2.plot(K(sch, "M2", "CAL")["E_ratio"], j + 0.32, "o", mfc="none", mec=INK2, mew=1.2,
                    label="M2 vs schematic cells" if j == 0 else None)
    for ax in (a1, a2):
        ax.axvline(1.0, color=INK2, lw=1)
        ax.set_yticks(range(len(names))); ax.set_yticklabels([n[1] for n in names]); ax.invert_yaxis()
    a1.set_xlabel("glitch transitions / SPICE"); a2.set_xlabel("total dynamic energy / SPICE")
    a1.set_title("Glitch count vs SPICE (extracted cells)"); a2.set_title("Energy vs SPICE (extracted cells)")
    a1.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4)
    a2.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3)
    fig.tight_layout()
    return fig


def mac_per_cycle():
    style()
    d = json.loads((ROOT / "data/notebook/mac_per_cycle.json").read_text())
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    k = np.arange(1, len(d["spice"]) + 1)
    for key, lab, col in (("spice", "SPICE (extracted cells, real flops)", INK), ("M0", "GlitchScope M0", CAT[0]),
                          ("M2_CAL", "GlitchScope M2", CAT[2])):
        ax.plot(k, d[key], "-o", color=col, ms=5, lw=1.8, label=lab)
    ax.set_xlabel("clock cycle"); ax.set_ylabel("combinational energy (fJ)")
    ax.set_title("MAC: energy per clock cycle"); ax.legend(fontsize=9, ncol=3, loc="upper left")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ 5 attribution
def attribution(bench="mul4"):
    style()
    d = json.loads((ROOT / f"data/bench/counterfactual_{bench}.json").read_text())
    s, g = d["single"], d["structural"]
    cells = sorted(set(s) | set(g))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw=dict(width_ratios=[1.2, 1]))
    x = [100 * g.get(c, 0) for c in cells]; y = [100 * s.get(c, 0) for c in cells]
    a1.plot(x, y, "o", color=CAT[0], alpha=0.75)
    lim = max(max(x), max(y)) * 1.1
    a1.plot([0, lim], [0, lim], color=AXIS, lw=1)
    for c in sorted(cells, key=lambda c: -s.get(c, 0))[:4]:
        a1.annotate(c, (100 * g.get(c, 0), 100 * s.get(c, 0)), xytext=(5, 3), textcoords="offset points", fontsize=8, color=INK2)
    a1.set_xlabel("structural trace-and-sum credit (%)"); a1.set_ylabel("interventional suppression potential (%)")
    a1.set_title(f"{bench}: what tracing credits vs what fixing saves (ρ = {d['spearman']:.2f})")
    top = d["top"]
    vals = [100 * d["sum_single_top"], 100 * d["joint_top"]]
    a2.barh([1, 0], vals, color=[CAT[1], CAT[2]], edgecolor=SURFACE, linewidth=2, height=0.5)
    for yy, vv, t in ((1, vals[0], "sum of single-gate savings"), (0, vals[1], "fix all six together")):
        a2.text(vv + 1, yy, f"{vv:.0f}%  {t}", va="center", fontsize=9, color=INK2)
    a2.set_axisbelow(True); a2.set_yticks([]); a2.set_xlim(0, max(vals) * 1.6); a2.set_xlabel("glitch energy removed (%)")
    a2.set_title(f"Top-{len(top)} fixes interact")
    fig.tight_layout()
    return fig


def skew_and_balancing():
    style()
    rows = _read_csv(ROOT / "data/bench/skew_mul4.csv")
    sweep = json.loads((ROOT / "data/notebook/balance_sweep.json").read_text())
    targets = ["_35_", "_24_", "_41_", "_40_", "_36_"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6))
    for i, c in enumerate(targets):
        v = np.array([float(r["skew_ps"]) for r in rows if r["cell"] == c])
        R = np.median([float(r["reject_ps"]) for r in rows if r["cell"] == c])
        a1.boxplot(v, positions=[i], widths=0.5, vert=True, patch_artist=True,
                   boxprops=dict(facecolor=GRID, color=AXIS), medianprops=dict(color=CAT[0], lw=2),
                   whiskerprops=dict(color=AXIS), capprops=dict(color=AXIS), flierprops=dict(markeredgecolor=MUTED, ms=3))
        a1.plot([i - 0.3, i + 0.3], [R, R], color=CAT[1], lw=2)
    a1.set_xticks(range(len(targets))); a1.set_xticklabels(targets)
    a1.set_ylabel("input arrival skew of hazards (ps)"); a1.set_title("mul4 top targets: skew spread vs rejection window")
    a1.text(len(targets) - 0.6, a1.get_ylim()[1] * 0.92, "— rejection window R", color=CAT[1], fontsize=8, ha="right")
    for i, (k, s) in enumerate(sweep.items()):
        n = [r["n_buf"] for r in s["rows"]]
        a2.plot(n, [r["d_total_pct"] for r in s["rows"]], "-o", color=CAT[i], ms=5, label=f"{k} total")
        a2.plot(n, [r["d_glitch_pct"] for r in s["rows"]], "--", color=CAT[i], lw=1.4, label=f"{k} glitch")
    a2.axhline(0, color=INK2, lw=1)
    a2.set_xlabel("buffers inserted on the leading input"); a2.set_ylabel("energy change (%)")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=CAT[i], lw=2, label=k) for i, k in enumerate(sweep)]
    h += [Line2D([], [], color=INK2, lw=2, label="total energy"), Line2D([], [], color=INK2, lw=1.4, ls="--", label="glitch energy")]
    a2.legend(handles=h, fontsize=7, loc="upper left")
    a2.set_title("Path balancing with buffers: no gain on any target tried")
    fig.tight_layout()
    return fig


def data_attribution(path):
    style()
    rows = _read_csv(path)[:10]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    y = np.arange(len(rows))[::-1]
    v = [100 * float(r["share_of_glitch_energy"]) for r in rows]
    ax.barh(y, v, color=CAT[0], edgecolor=SURFACE, linewidth=2, height=0.6)
    for yy, vv, r in zip(y, v, rows):
        ax.text(vv + 0.3, yy, f"{vv:.1f}%  ({float(r['glitch_fJ_per_toggle']):.0f} fJ/toggle)", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([r["input_or_state_bit"] for r in rows])
    ax.set_xlabel("share of glitch energy explained by toggles of this bit (%)")
    ax.set_title("MAC: which input / state bits trigger glitch energy"); ax.set_xlim(0, max(v) * 1.6)
    fig.tight_layout()
    return fig


def _read_csv(p):
    with open(p) as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ fix gap (where vs how)
def fix_gap(path):
    """Oracle suppression potential of each target cell vs the best function-preserving
    edit found for it (both as % of baseline glitch energy)."""
    style()
    d = json.loads(Path(path).read_text())
    cells = d["cells"]
    pot = [100 * (d["potential"].get(c) or 0) for c in cells]
    best = []
    for c in cells:
        rs = [r for r in d["rows"] if r["cell"] == c and r["dE_total_fJ"] < 0]
        best.append(max([-r["dE_glitch_pct"] for r in rs] + [0.0]))
    fig, ax = plt.subplots(figsize=(7.6, 0.42 * len(cells) + 1.3))
    y = np.arange(len(cells))[::-1]
    ax.barh(y + 0.19, pot, height=0.36, color=CAT[0], label="if the gate were glitch-free (oracle)")
    ax.barh(y - 0.19, best, height=0.36, color=CAT[1], label="best real edit for glitch energy (resize / pin swap)")
    for yy, p, b in zip(y, pot, best):
        ax.text(p + 0.2, yy + 0.19, f"{p:.1f} %", va="center", fontsize=8.5, color=INK2)
        ax.text(b + 0.2, yy - 0.19, f"{b:.1f} %", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(cells); ax.grid(axis="y", visible=False)
    ax.set_xlabel("glitch energy removed (% of baseline)")
    c = d.get("combined")
    ax.set_title(f"{d['bench']}: where vs how; all best edits together: glitch {c['dE_glitch_pct']:+.1f} %, "
                 f"total {c['dE_total_pct']:+.1f} %" if c else f"{d['bench']}: where vs how")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_xlim(0, max(pot + [1]) * 1.18)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ large design: groups
def group_attribution(path):
    """Measured suppression potential vs traced (trace-and-sum) credit for adder rows
    and logic-depth bands of the 16x16 array multiplier."""
    style()
    d = json.loads(Path(path).read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [1.25, 1]})
    for ax, key, title, order in (
            (axes[0], "rows", "Adder rows (pp = partial products, rf = final adder)",
             lambda g: (0 if g == "pp" else 2 if g == "rf" else 1, g)),
            (axes[1], "levels", "Logic-depth bands", lambda g: g)):
        r = d[key]
        gs = sorted(r["single"], key=order)
        x = np.arange(len(gs))
        pot = [100 * r["single"][g] for g in gs]; st = [100 * r["structural"].get(g, 0) for g in gs]
        ax.bar(x - 0.2, pot, width=0.38, color=CAT[0], label="measured suppression potential")
        ax.bar(x + 0.2, st, width=0.38, color=CAT[1], label="traced credit (trace-and-sum)")
        picks = [g for g, _ in r["greedy"]]
        for i, g in enumerate(gs):
            if g in picks:
                ax.annotate(f"fix #{picks.index(g) + 1}", (i - 0.2, pot[i]), xytext=(0, 4), textcoords="offset points",
                            ha="center", fontsize=8, color=INK2)
        labels = [g.replace("depth ", "").replace("-", "–") for g in gs]
        ax.set_xticks(x); ax.set_xticklabels(labels, rotation=60 if key == "levels" else 0, fontsize=8,
                                             ha="right" if key == "levels" else "center")
        ax.grid(axis="x", visible=False); ax.set_ylim(0, 75)
        ax.set_ylabel("% of glitch energy"); ax.set_title(title)
        ax.text(0.99, 0.97, f"greedy {len(picks)}: {100 * r['greedy'][-1][1]:.0f} % together",
                transform=ax.transAxes, ha="right", va="top", fontsize=9, color=INK2)
    axes[0].legend(loc="upper left", fontsize=8.5, bbox_to_anchor=(0, 0.93))
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ layout study
def layout_study(root=None):
    """Post-layout comparison of the three 16x16 multiplier variants: glitch heat map on
    the real placement (same colour scale) and the power / area table as bars."""
    from .layoutviz import read_def, plot_layout
    style()
    root = Path(root or ROOT)
    S = json.loads((root / "data/layout/summary.json").read_text())["variants"]
    S = {k: S[k] for k in ("v0", "v1", "v2")}
    sizes = {k: tuple(v) for k, v in json.loads((root / "data/layout/cell_sizes.json").read_text()).items()}
    vals, defs = {}, {}
    for v in S:
        rows = _read_csv(root / f"data/layout/{v}/glitchscope/glitch_cells.csv")
        n = 41
        vals[v] = {r["cell"]: float(r["consumed_glitch_fJ"]) / n for r in rows}
        defs[v] = read_def(root / f"data/layout/{v}/6_final.def.gz")
    vmax = float(np.percentile([x for d in vals.values() for x in d.values() if x > 0], 98))
    fig = plt.figure(figsize=(12, 7.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1], hspace=0.35, wspace=0.18)
    titles = {"v0": "V0 · no pipeline", "v1": "V1 · cut after row 3\n(where trace-and-sum points)",
              "v2": "V2 · cut after row 9\n(where GlitchScope points)"}
    pc = None
    for i, v in enumerate(S):
        ax = fig.add_subplot(gs[0, i])
        comps = defs[v]["components"]
        pipe = {c for c in comps if c.startswith("pipe_r")}
        io = {c for c, m in comps.items() if "dfxtp" in m[0] and c not in pipe}
        pc = plot_layout(ax, defs[v], sizes, values=vals[v], vmax=vmax, highlight=pipe, highlight2=io,
                         title=titles[v]) or pc
        ax.set_xticks([0, 50, 100, 150]); ax.tick_params(labelsize=8)
        if i:
            ax.set_yticklabels([])
    cb = fig.colorbar(pc, ax=fig.axes[:3], fraction=0.02, pad=0.01)
    cb.set_label("glitch energy per cycle (fJ)", fontsize=9); cb.ax.tick_params(labelsize=8)
    fig.text(0.13, 0.955, "dark blue: added pipeline register · light blue: input / output registers · "
             "orange: glitch energy burnt in each cell", fontsize=8.5, color=INK2)
    # power stack and deltas
    ax = fig.add_subplot(gs[1, :2])
    names = list(S); x = np.arange(len(names))
    comb = [S[v]["opensta_mW"]["Combinational"] for v in names]
    seq = [S[v]["opensta_mW"]["Sequential"] for v in names]
    clk = [S[v]["opensta_mW"]["Clock"] for v in names]
    ax.barh(x, comb, color=CAT[1], height=0.55, label="combinational (glitch-accurate activity)")
    ax.barh(x, seq, left=comb, color=CAT[0], height=0.55, label="flip-flops")
    ax.barh(x, clk, left=np.add(comb, seq), color=CAT[2], height=0.55, label="clock tree")
    base = S["v0"]["opensta_mW"]["Total"]
    for i, v in enumerate(names):
        t = S[v]["opensta_mW"]["Total"]
        ax.text(t + 0.08, i, f"{t:.2f} mW" + (f"  ({100 * (t / base - 1):+.0f} %)" if i else ""), va="center",
                fontsize=9, color=INK2)
    ax.set_yticks(x); ax.set_yticklabels(["V0", "V1", "V2"]); ax.invert_yaxis()
    ax.set_xlabel("total power after place & route, 66.7 MHz (OpenSTA + GlitchScope SAIF + SPEF)")
    ax.set_xlim(0, base * 1.3); ax.grid(axis="y", visible=False)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.28), ncol=3, fontsize=8.5)
    ax.set_title("Post-layout power")
    ax2 = fig.add_subplot(gs[1, 2])
    a0 = S["v0"]["area_um2"]
    ar = [S[v]["area_um2"] for v in names]
    ax2.bar(x, ar, color=MUTED, width=0.55)
    for i, a in enumerate(ar):
        ax2.text(i, a + 150, f"{a / 1000:.1f}k" + (f"\n{100 * (a / a0 - 1):+.0f} %" if i else ""),
                 ha="center", fontsize=8.5, color=INK2)
    ax2.set_xticks(x); ax2.set_xticklabels(["V0", "V1", "V2"]); ax2.set_ylim(0, max(ar) * 1.25)
    ax2.set_ylabel("cell area (µm²)"); ax2.set_title("Area"); ax2.grid(axis="x", visible=False)
    return fig


# ------------------------------------------------------------------ automatic register placement
def glitchfix(root=None):
    """Left: measured energy per cycle of the four register placements of the 16x16
    multiplier (same latency, same clock), split into logic, glitches and registers.
    Right: total power after place and route (OpenSTA + GlitchScope SAIF + SPEF)."""
    style()
    root = Path(root or ROOT)
    O = json.loads((root / "data/glitchfix/mul16_r/optimize.json").read_text())
    S = json.loads((root / "data/layout/summary.json").read_text())["variants"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.9), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=0.45))
    keys = [("original", "original"), ("min_register", "min-register\nretiming"),
            ("timing_driven", "min-period\nretiming"), ("best_cuts", "GlitchScope:\narrival-time cuts"),
            ("best_milp", "GlitchScope:\ncalibrated MILP")]
    if not O.get("best_milp"):
        keys = keys[:3] + [("glitch_aware", "GlitchScope\n(glitch-aware)")]
    keys = [(k, l) for k, l in keys if O.get(k)]
    y = np.arange(len(keys))
    fun = np.array([O[k]["functional"] for k, _ in keys]) / 1e3
    gl = np.array([O[k]["glitch"] for k, _ in keys]) / 1e3
    rg = np.array([O[k]["flop_clock"] + O[k]["flop_data"] + O[k]["inputs"] for k, _ in keys]) / 1e3
    a1.barh(y, fun, color=AXIS, height=0.6, label="logic, functional")
    a1.barh(y, gl, left=fun, color=CAT[1], height=0.6, label="logic, glitches")
    a1.barh(y, rg, left=fun + gl, color=CAT[0], height=0.6, label="flip-flops + clock tree")
    b = O["original"]["total"] / 1e3
    for i, (k, _) in enumerate(keys):
        t = O[k]["total"] / 1e3
        a1.text(t + 1.2, i, f"{t:.1f} pJ" + (f" ({100 * (t / b - 1):+.1f} %)" if i else "") + f"\n{O[k]['flops']} flops",
                va="center", fontsize=8.5, color=INK2)
    a1.set_yticks(y); a1.set_yticklabels([l for _, l in keys], fontsize=9); a1.invert_yaxis()
    a1.set_xlim(0, b * 1.32); a1.grid(axis="y", visible=False)
    a1.set_xlabel("energy per cycle, measured before layout (pJ)")
    a1.set_title("Same latency, same clock: where the registers sit")
    a1.legend(loc="upper left", bbox_to_anchor=(0, -0.2), ncol=3, fontsize=8.5)
    names = [v for v in ("v0", "v2", "r_td", "r_ga", "r_milp") if v in S]
    lab = {"v0": "original\n(latency 2)", "v2": "hand-placed pipeline\n(§5 V2, latency 3)",
           "r_td": "min-period\nretiming (latency 2)", "r_ga": "GlitchScope:\ncuts (latency 2)",
           "r_milp": "GlitchScope:\ncalibrated MILP (latency 2)"}
    x = np.arange(len(names))
    comb = [S[v]["opensta_mW"]["Combinational"] for v in names]
    seq = [S[v]["opensta_mW"]["Sequential"] + S[v]["opensta_mW"]["Clock"] for v in names]
    a2.barh(x, comb, color=CAT[1], height=0.6, label="combinational")
    a2.barh(x, seq, left=comb, color=CAT[0], height=0.6, label="flip-flops + clock tree")
    p0 = S["v0"]["opensta_mW"]["Total"]
    for i, v in enumerate(names):
        t = S[v]["opensta_mW"]["Total"]
        a2.text(t + 0.1, i, f"{t:.2f} mW" + (f" ({100 * (t / p0 - 1):+.1f} %)" if i else "") +
                f"\narea {100 * (S[v]['area_um2'] / S['v0']['area_um2'] - 1):+.0f} %" * bool(i),
                va="center", fontsize=8.5, color=INK2)
    a2.set_yticks(x); a2.set_yticklabels([lab[v] for v in names], fontsize=9); a2.invert_yaxis()
    a2.set_xlim(0, p0 * 1.38); a2.grid(axis="y", visible=False)
    a2.set_xlabel("total power after place & route, 66.7 MHz (mW)")
    a2.set_title("Re-evaluated after place and route (OpenROAD, OpenSTA,\nGlitchScope activity, extracted wires)", fontsize=10)
    a2.legend(loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2, fontsize=8.5)
    return fig


# ------------------------------------------------------------------ standard benchmark suites
SUITE_LABEL = {"iscas85": "ISCAS'85", "iscas89": "ISCAS'89", "itc99": "ITC'99", "epfl": "EPFL"}


def benchmark_suite(path=None):
    """Glitch share of dynamic energy across the standard suites (M2 filled, M0 hollow)
    and simulation time per clock cycle against circuit size."""
    style()
    S = json.loads(Path(path or ROOT / "data/benchmarks/suite.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.28))
    suites = [k for k in SUITE_LABEL if any(r["suite"] == k for r in S.values())]
    rng = np.random.default_rng(3)
    for i, su in enumerate(suites):
        rows = [r for r in S.values() if r["suite"] == su and r["cells"] >= 20]
        x = i + rng.uniform(-0.18, 0.18, len(rows))
        m2 = [100 * r["M2"]["glitch_share"] for r in rows]
        m0 = [100 * r["M0"]["glitch_share"] for r in rows]
        a1.scatter(x, m0, s=22, facecolors="none", edgecolors=MUTED, lw=1, label="M0 transport (no filtering)" if not i else None)
        a1.scatter(x, m2, s=26, color=CAT[i], label=None)
        a1.text(i, -9, f"{len(rows)} circuits", ha="center", fontsize=8.5, color=INK2)
        med = np.median(m2)
        a1.plot([i - 0.3, i + 0.3], [med, med], color=INK, lw=1.5)
    a1.set_xticks(range(len(suites))); a1.set_xticklabels([SUITE_LABEL[k] for k in suites])
    a1.scatter([], [], s=26, color=INK2, label="M2, GlitchScope (median: bar)")
    a1.set_ylim(-14, 118); a1.set_yticks(range(0, 101, 20)); a1.set_ylabel("glitch share of dynamic energy (%)")
    a1.set_title("Glitch share per suite")
    a1.legend(loc="upper center", ncol=2, fontsize=8.5); a1.grid(axis="x", visible=False)
    for i, su in enumerate(suites):
        rows = [r for r in S.values() if r["suite"] == su]
        a2.scatter([r["cells"] for r in rows], [1e3 * r["M2"]["seconds_per_cycle"] for r in rows], s=24, color=CAT[i],
                   label=SUITE_LABEL[su])
    a2.set_xscale("log"); a2.set_yscale("log")
    a2.set_xlabel("cells"); a2.set_ylabel("simulation + analysis time per cycle (ms)")
    a2.set_title("Run time (compiled core, M2, 1 core)"); a2.legend(fontsize=8.5)
    return fig


def retiming_benchmarks(path=None):
    """Left: measured energy saving of GlitchScope's register placement against exact
    minimum-register retiming and timing-driven retiming, same target clock, per benchmark.
    Right: the saving against the share of the original design's total energy (logic,
    flip-flops and clock tree) that goes into glitches."""
    style()
    R = json.loads(Path(path or ROOT / "data/benchmarks/retiming.json").read_text())
    rows = [(k, r) for k, r in R.items() if r.get("glitchscope") and r.get("classic")]
    import re
    is_ctrl = lambda k: re.match(r"b\d\d@", k) is not None          # noqa: E731  ITC'99 b01..b22
    ctrl = sorted([x for x in rows if is_ctrl(x[0])], key=lambda x: x[1]["cells"])
    arith = [x for x in rows if not is_ctrl(x[0])]
    arith.sort(key=lambda x: (x[0].split("@")[0], x[0].split("@")[1]))
    order = ctrl + arith
    fig, (ax, a2) = plt.subplots(1, 2, figsize=(13, 0.3 * len(order) + 1.8),
                                 gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.08))
    y = np.arange(len(order))
    s_min = [100 * r.get("saving_vs_classic", 0) for _, r in order]
    s_td = [100 * r.get("saving_vs_timing_driven", 0) for _, r in order]
    ax.barh(y + 0.2, s_td, height=0.38, color=AXIS, label="vs FEAS retiming (just meets the clock)")
    ax.barh(y - 0.2, s_min, height=0.38, color=CAT[0], label="vs exact minimum-register retiming")
    lab = []
    for k, r in order:
        name, f = k.split("@")
        tgt = "own clock" if float(f) <= 0 else f"{float(f):.1f}× T_min"
        lab.append(f"{name.replace('_r', ' (reg.)')}  {r['cells']} cells, {tgt}")
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8); ax.invert_yaxis()
    if ctrl and arith:
        ax.axhline(len(ctrl) - 0.5, color=INK2, lw=1)
        ax.text(52, len(ctrl) - 0.8, "ITC'99 (control)", ha="right", fontsize=8, color=INK2)
        ax.text(52, len(ctrl) - 0.2, "arithmetic", ha="right", va="top", fontsize=8, color=INK2)
    ax.set_xlim(0, 53)
    ax.set_xlabel("measured total-energy saving of GlitchScope's placement (%)")
    ax.set_title("Same clock, every netlist verified")
    ax.legend(loc="lower right", fontsize=8); ax.grid(axis="y", visible=False)
    for k, r in order:
        o = r["original"]
        g = 100 * o["glitch"] / o["total"]
        own = float(k.split("@")[1]) <= 0
        c = CAT[1] if is_ctrl(k) else CAT[0]
        a2.plot(g, 100 * r.get("saving_vs_classic", 0), "o", ms=7, color=c, mfc=c if own else "none", mew=1.4)
        if r.get("saving_vs_classic", 0) > 0.05:
            a2.annotate(k.split("@")[0].replace("_r", "").replace("_v0", ""), (g, 100 * r["saving_vs_classic"]),
                        xytext=(5, -3), textcoords="offset points", fontsize=8, color=INK2)
    a2.plot([], [], "o", color=CAT[1], label="ITC'99 (control)")
    a2.plot([], [], "o", color=CAT[0], label="arithmetic")
    a2.plot([], [], "o", color=MUTED, mfc="none", label="hollow: 1.1× minimum period")
    a2.set_xlabel("glitch share of the original's total energy (%)\n(logic + flip-flops + clock tree)")
    a2.set_ylabel("saving vs minimum-register retiming (%)")
    a2.yaxis.set_label_position("right"); a2.yaxis.tick_right()
    a2.set_title("It pays where glitches dominate the total")
    a2.set_xlim(0, 100); a2.legend(fontsize=8, loc="upper left")
    return fig


# ------------------------------------------------------------------ technology trend
def pdk_trend(path=None):
    """Same 16x16 array multiplier in six open technologies (180 nm -> 2 nm)."""
    style()
    d = json.loads(Path(path or ROOT / "data/pdk/trend.json").read_text())
    rows = sorted(d.values(), key=lambda r: -r["node_nm"])
    short = {"GF180MCU": "GF180", "SKY130 HD": "SKY130", "IHP SG13G2": "IHP", "Nangate45": "Nangate", "ASAP7": "ASAP7", "GT2N": "GT2N"}
    labels = [f"{short.get(r['label'], r['label'])}\n{r['node_nm']} nm\n{r['vdd']:g} V" for r in rows]
    x = np.arange(len(rows))
    nv = rows[0]["vectors"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(13, 4.1))
    # energy per multiplication
    e1 = [r["models"]["M1"]["totals"]["E_total_fJ"] / r["vectors"] / 1e3 for r in rows]
    a1.bar(x, e1, color=CAT[0], width=0.6)
    for i, r in enumerate(rows):
        a1.text(i, e1[i] * 1.12, f"{e1[i]:.3g}", ha="center", fontsize=8, color=INK2)
    a1.set_yscale("log"); a1.set_ylabel("dynamic energy per multiplication (pJ, M1)")
    a1.set_title("Energy per operation"); a1.grid(axis="x", visible=False)
    a1.set_ylim(min(e1) / 2, max(e1) * 3)
    # glitch share by model
    for m, col, mk, lab in (("M0", CAT[1], "o", "M0 transport (no filtering)"),
                            ("M1", CAT[0], "s", "M1 inertial"),
                            ("M2", CAT[2], "D", "M2 SPICE-calibrated")):
        ys = [100 * r["models"][m]["totals"]["glitch_fraction"] if m in r["models"] else np.nan for r in rows]
        a2.plot(x, ys, mk, color=col, ms=8, label=lab, linestyle="none")
    a2.set_ylabel("glitch share of dynamic energy (%)"); a2.set_title("Glitch share"); a2.set_ylim(80, 100)
    a2.legend(fontsize=8, loc="lower left")
    # glitch transitions per functional transition
    for m, col, mk in (("M0", CAT[1], "o"), ("M1", CAT[0], "s"), ("M2", CAT[2], "D")):
        ys = [r["models"][m]["counts"]["glitch_transitions"] / max(1, r["models"][m]["counts"]["functional_transitions"])
              if m in r["models"] else np.nan for r in rows]
        a3.plot(x, ys, mk, color=col, ms=8, linestyle="none")
    a3.set_ylabel("glitch transitions per required transition"); a3.set_title("Glitch activity")
    for ax in (a1, a2, a3):
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
    fig.suptitle(f"Same circuit, six open technologies: c6288-class 16×16 multiplier, {nv} random vectors",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ cycle sampling
def sampling_convergence(path=None):
    style()
    d = json.loads(Path(path or ROOT / "data/notebook/sampling_mac.json").read_text())
    truth = d["truth_glitch_fJ"]
    sizes = sorted(d["sizes"], key=int)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"width_ratios": [1.6, 1]})
    for i, n in enumerate(sizes):
        rows = d["sizes"][n][:8]
        for j, r in enumerate(rows):
            x = i + (j - 3.5) * 0.07
            hit = r["lo"] <= truth <= r["hi"]
            a1.plot([x, x], [r["lo"], r["hi"]], color=CAT[0] if hit else CAT[1], lw=1.6)
            a1.plot(x, r["mean"], "o", color=CAT[0] if hit else CAT[1], ms=3.5)
    a1.axhline(truth, color=INK2, lw=1, ls="--")
    a1.text(-0.45, truth, f"full run ({d['cycles']} cycles)", va="bottom", ha="left", fontsize=8.5, color=INK2,
            bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1))
    a1.set_xticks(range(len(sizes))); a1.set_xticklabels([f"{n} cycles" for n in sizes])
    a1.set_ylabel("glitch energy per cycle (fJ)"); a1.grid(axis="x", visible=False)
    a1.set_title("Sampled estimate and 95 % CI (8 of the 20 random samples per size)")
    cov = [100 * sum(r["lo"] <= truth <= r["hi"] for r in d["sizes"][n]) / len(d["sizes"][n]) for n in sizes]
    hw = [100 * sum((r["hi"] - r["lo"]) / 2 for r in d["sizes"][n]) / len(d["sizes"][n]) / truth for n in sizes]
    x = np.arange(len(sizes))
    a2.bar(x - 0.18, cov, width=0.36, color=CAT[0], label="CI covers the full-run value (%)")
    a2.bar(x + 0.18, hw, width=0.36, color=CAT[2], label="CI half-width (% of value)")
    a2.axhline(95, color=MUTED, lw=1, ls=":")
    a2.set_xticks(x); a2.set_xticklabels(sizes); a2.set_xlabel("sampled cycles")
    a2.set_ylim(0, 110); a2.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)
    a2.set_title("Coverage and precision (20 random samples per size)")
    a2.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ PVT and mismatch robustness
def robustness(root=None):
    """Left: energy per cycle of the 16x16 multiplier (original, timing-driven retiming,
    GlitchScope placement chosen at the typical corner) against supply voltage at the slow
    (-40 C) and fast (-40 C) corners.  Right: saving of both placements at all 12 Liberty
    corners and on 2 x 30 Monte-Carlo dies with SPICE-measured local mismatch."""
    style()
    root = Path(root or ROOT)
    P = json.loads((root / "data/pvt/pvt.json").read_text())
    M = json.loads((root / "data/mismatch/study.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw=dict(width_ratios=[1, 1.15], wspace=0.28))
    lab = {"original": "original", "timing_driven": "min-period retiming", "glitchscope": "GlitchScope (calibrated MILP)"}
    col = {"original": MUTED, "timing_driven": AXIS, "glitchscope": CAT[0]}
    for fam, mk, ls in (("ss_n40C", "o", "-"), ("ff_n40C", "s", "--")):
        rows = sorted([r for k, r in P.items() if k.startswith(fam)], key=lambda r: float(r["corner"][-4:].replace("v", ".")))
        v = [float(r["corner"][-4:].replace("v", ".")) for r in rows]
        for k in ("original", "timing_driven", "glitchscope"):
            a1.plot(v, [r[k]["total"] / 1e3 for r in rows], mk + ls, color=col[k], ms=5,
                    label=lab[k] if fam == "ss_n40C" else None)
    a1.plot([], [], "o-", color=INK, mfc="white", ms=5, lw=0.8, label="line style: slow corner (ss), −40 °C")
    a1.plot([], [], "s--", color=INK, mfc="white", ms=5, lw=0.8, label="line style: fast corner (ff), −40 °C")
    a1.set_xlabel("supply voltage (V)"); a1.set_ylabel("energy per cycle (pJ)")
    a1.set_title("At equal supply, the fix holds at every voltage")
    a1.legend(fontsize=8.5, loc="upper left")
    order = list(P)
    x = np.arange(len(order))
    for k, dx in (("timing_driven", -0.12), ("glitchscope", 0.12)):
        a2.plot(x + dx, [100 * P[c][k]["saving"] for c in order], "o", color=col[k], ms=6, label=lab[k])
    rng = np.random.default_rng(1)
    for j, (ss, run) in enumerate(sorted(M["runs"].items())):
        xx = len(order) + 0.8 + 1.3 * j
        for k, dx in (("timing_driven", -0.18), ("glitchscope", 0.18)):
            s = [100 * (1 - r[k]["total"] / r["original"]["total"]) for r in run["rows"]]
            a2.plot(xx + dx + rng.uniform(-0.1, 0.1, len(s)), s, "o", color=col[k], ms=3.5, alpha=0.7)
    ticks = list(x) + [len(order) + 0.8 + 1.3 * j for j in range(len(M["runs"]))]
    names = [c.replace("_", " ").replace("C ", "°C ").replace("n40", "−40") for c in order] + \
        [f"mismatch\n×{float(s):g} (30 dies)" for s in sorted(M["runs"])]
    a2.set_xticks(ticks); a2.set_xticklabels(names, rotation=60, ha="right", fontsize=7.5)
    a2.axvline(len(order) + 0.2, color=INK2, lw=0.8)
    ys = [v for ln in a2.get_lines() if ln.get_marker() == "o" for v in ln.get_ydata()]
    a2.set_ylabel("total-energy saving vs original (%)"); a2.set_ylim(np.floor(min(ys)) - 3, np.ceil(max(ys)) + 2)
    a2.set_title("12 PVT corners and Monte-Carlo mismatch")
    a2.legend(fontsize=8.5, loc="lower left"); a2.grid(axis="x", visible=False)
    return fig


def _die_map(ax, d, norm, title):
    """One placed-and-routed layout: logic cells coloured by the glitch energy they burn, flip-flops in blue."""
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Rectangle
    logic = [r for r in d["cells"] if r[4] == "logic"]
    ff = [r for r in d["cells"] if r[4] == "ff"]
    pc = PatchCollection([Rectangle((x, y), w, h) for x, y, w, h, *_ in logic], cmap="Oranges", norm=norm, linewidths=0)
    pc.set_array(np.array([max(r[5], 1.0) for r in logic]))
    ax.add_collection(pc)
    ax.add_collection(PatchCollection([Rectangle((x, y), w, h) for x, y, w, h, *_ in ff], facecolor=CAT[0], linewidths=0))
    ax.add_patch(Rectangle((0, 0), d["die"][2], d["die"][3], fill=False, lw=0.8, ec=INK2))
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, fontsize=10)
    return pc


def visual_abstract(root=ROOT):
    """Front-page figure: where glitch energy burns on the routed 16x16 multiplier before/after GlitchScope's
    fix (model, per cell), and the transistor-level (SPICE) confirmation of the saving."""
    from matplotlib.colors import LogNorm
    style()
    D = json.loads((root / "data/layout/glitch_map.json").read_text())
    PL = json.loads((root / "data/glitchfix/mul16_r/spice_postlayout.json").read_text())["designs"]
    fig = plt.figure(figsize=(13, 5.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8], wspace=0.1)
    a0, a1, a2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])
    norm = LogNorm(1, 300)
    lim = max(D["v0"]["die"][2], D["r_milp"]["die"][2])
    _die_map(a0, D["v0"], norm, f"original: {D['v0']['flops']} flip-flops at the I/O\n"
                                f"glitch energy {D['v0']['glitch_pJ']:.0f} pJ/cycle\n(model, 40 random cycles, no wires)")
    pc = _die_map(a1, D["r_milp"], norm, f"GlitchScope's fix: {D['r_milp']['flops']} flip-flops\nmoved into the array; "
                                         f"glitch energy {D['r_milp']['glitch_pJ']:.0f} pJ/cycle\n(model, same cycles, no wires)")
    for a in (a0, a1):
        a.set_xlim(-2, lim + 2); a.set_ylim(-2, lim + 2)
    cb = fig.colorbar(pc, ax=[a0, a1], orientation="horizontal", fraction=0.045, pad=0.03, aspect=40)
    cb.set_label("glitch energy burnt per cell (fJ/cycle; GlitchScope model, 40 random cycles)\n"
                 "blue: flip-flops · cell positions from the routed SKY130 layouts", fontsize=8.5)
    o = PL["original"]["total"]
    rows = [("min-period retiming", PL["timing_driven"], AXIS), ("GlitchScope", PL["glitchscope"], CAT[0])]
    flops = {"timing_driven": 174, "glitchscope": 137}
    for i, (lab, r, col) in enumerate(rows):
        s = 100 * r["saving"]; lo, hi = (100 * v for v in r["saving_ci95"])
        a2.barh(i, s, color=col, height=0.5)
        a2.errorbar(s, i, xerr=[[s - lo], [hi - s]], color=INK, capsize=4, lw=1.2)
        a2.text(1, i - 0.36, f"{lab} ({flops['glitchscope' if i else 'timing_driven']} flip-flops)", fontsize=9,
                color=INK2, va="center")
        a2.text(hi + 2.5, i, f"−{s:.0f} %", va="center", fontsize=12, color=INK, fontweight="bold")
    a2.set_yticks([]); a2.set_ylim(1.6, -0.75)
    a2.set_xlim(0, 68)
    a2.set_xlabel("energy saving vs original (%)")
    a2.set_title(f"Transistor-level SPICE of the routed netlists\n(real clock tree, extracted wire C; "
                 f"{PL['glitchscope']['paired_cycles']} paired cycles, 95 % CI)", fontsize=10)
    a2.grid(axis="y", visible=False)
    fig.suptitle("16×16 array multiplier, same function, latency and clock: GlitchScope finds where glitches burn energy, "
                 "moves the registers there,\ncertifies the retiming, places and routes it, and measures the layout in "
                 "transistor-level SPICE", fontsize=10.5, y=1.03)
    return fig


def spice_confirmation(root=ROOT):
    """Transistor-level confirmation of the automatic fix: SPICE saving (95 % CI) vs GlitchScope's prediction."""
    style()
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.4))
    lab = {"timing_driven": "min-period retiming", "best_cuts": "GlitchScope, arrival-time cuts",
           "best_milp": "GlitchScope, calibrated MILP"}
    for ax, (case, title) in zip(axs, (("mul16_r", "16×16 multiplier"), ("mul8_r", "8×8 multiplier"))):
        D = json.loads((root / f"data/glitchfix/{case}/spice_confirm_pex.json").read_text())["designs"]
        pick = json.loads((root / f"data/glitchfix/{case}/optimize.json").read_text())["glitch_aware"]["flops"]
        keys = [k for k in ("timing_driven", "best_cuts", "best_milp") if k in D]
        plf = root / f"data/glitchfix/{case}/spice_postlayout.json"
        PL = json.loads(plf.read_text())["designs"] if plf.exists() else {}
        for i, k in enumerate(keys):
            q = PL.get({"timing_driven": "timing_driven", "best_milp": "glitchscope"}.get(k, ""))
            if q:
                sp = 100 * q["saving"]; l2, h2 = (100 * v for v in q["saving_ci95"])
                ax.errorbar(sp, i + 0.36, xerr=[[sp - l2], [h2 - sp]], fmt="D", color=INK, ms=6, capsize=3, lw=1.1)
                ax.text(h2 + 3, i + 0.36, f"SPICE {sp:.1f} % after layout", va="center", fontsize=8, color=INK2)
            r = D[k]
            s = 100 * r["saving_spice"]; lo, hi = (100 * v for v in r["saving_spice_ci95"])
            chosen = k.startswith("best") and r["flops"] == pick
            ax.barh(i, s, height=0.55, color=CAT[0] if chosen else (CAT[0] + "66" if k.startswith("best") else AXIS))
            ax.errorbar(s, i, xerr=[[s - lo], [hi - s]], color=INK, capsize=3, lw=1.1)
            ax.plot(100 * r["saving_glitchscope"], i, "o", mfc="none", mec=INK2, ms=7, mew=1.4)
            ax.text(max(hi, 100 * r["saving_glitchscope"], 0) + 3, i,
                    f"SPICE {s:.1f} %  (predicted {100 * r['saving_glitchscope']:.1f} %)".replace("-", "−"), va="center",
                    fontsize=8.5, fontweight="bold" if chosen else "normal", color=INK)
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels([f"{lab[k]} ({D[k]['flops']} FF)" + (" ★" if k.startswith("best") and D[k]["flops"] == pick else "")
                            for k in keys], fontsize=8.5)
        ax.axvline(0, color=INK2, lw=0.8); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
        ax.set_title(f"{title}: saving vs original, ngspice", fontsize=10)
        ax.set_xlabel("energy saving (%)")
    axs[0].plot([], [], "o", mfc="none", mec=INK2, ms=7, mew=1.4, label="GlitchScope's prediction")
    axs[0].plot([], [], "D", color=INK, ms=6, label="routed netlist: real clock tree, wire C")
    axs[0].set_xlim(-5, 95); axs[1].set_xlim(-20, 45)
    fig.legend(*axs[0].get_legend_handles_labels(), fontsize=8.5, loc="lower right", bbox_to_anchor=(0.99, -0.13), ncol=2, frameon=False)
    fig.text(0.02, -0.09, "★ GlitchScope's choice · bars: SPICE before layout, paired-bootstrap 95 % CI · FF: flip-flops",
             ha="left", fontsize=8.5, color=INK2)
    fig.tight_layout(w_pad=4)
    return fig


def vdd_aware(root=ROOT):
    """Iso-throughput energy saving with supply scaling: timing-driven retiming, GlitchScope's fixed-supply choice
    and its voltage-aware choice (placement and supply chosen together), per clock, at both -40 C corner families."""
    style()
    S = json.loads((root / "data/glitchfix/mul16_vdd/select.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4), sharey=True)
    for ax, (fam, title) in zip(axs, (("ss_n40C", "slow corner, −40 °C (1.28–1.76 V)"),
                                      ("ff_n40C", "fast corner, −40 °C (1.56–1.95 V)"))):
        rows = S[fam]
        x = [r["clock_ns"] for r in rows]
        series = (("timing_driven", "min-period retiming", AXIS, "s"),
                  ("gs_milp", "GlitchScope, fixed-supply choice", CAT[0] + "88", "o"))
        for k, lab, col, mk in series:
            ax.plot(x, [100 * r["designs"][k]["saving"] for r in rows], mk + "-", color=col, lw=1.8, ms=6, label=lab)
        ax.plot(x, [100 * r["vdd_aware_saving"] for r in rows], "D-", color=CAT[0], lw=2.2, ms=6,
                label="GlitchScope, voltage-aware (placement + supply)")
        ax.set_xscale("log"); ax.set_xticks(x); ax.set_xticklabels([f"{v:.0f}" if v >= 10 else f"{v:.1f}" for v in x])
        ax.minorticks_off(); ax.invert_xaxis()
        ax.set_xlabel("clock period (ns) — tighter →"); ax.set_title(title, fontsize=10)
    axs[0].set_ylabel("energy saving vs original (%)\n(each design at its lowest supply\nthat meets the clock)")
    axs[0].legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    return fig
