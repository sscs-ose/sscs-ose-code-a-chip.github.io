"""Figures drawn exclusively from completed, integrity-checked SPICE experiments."""

from __future__ import annotations

import base64
import html
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np

from .experiments import MODES, load_results, summary
from .spice import EVALUATION_START_S, ROOT, Point, Simulator

COLORS = {"untrimmed": "#64748b", "frozen": "#e99c35", "retuned": "#00a89d"}
LABELS = {
    "untrimmed": "Code zero",
    "frozen": "Nominal trim, frozen",
    "retuned": "Locally recalibrated",
}


def style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titleweight": "bold", "figure.facecolor": "white", "savefig.facecolor": "white",
    })


def atlas_figure(frame, deadline_ns: float = 0.5):
    style()
    selected = frame[(frame.deadline_ns == deadline_ns) & (frame.input_mv != 0)].copy()
    mapping = {"correct": 2, "wrong": 0, "unresolved": 1}
    selected["status"] = selected.outcome.map(mapping)
    case_order = list(dict.fromkeys(selected.case_id))
    cmap = ListedColormap(["#df5363", "#e9b44c", "#17a897"])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
    fig, axes = plt.subplots(1, 3, figsize=(17, max(4.5, len(case_order) * 0.35)), sharey=True)
    for ax, mode in zip(axes, MODES):
        table = selected[selected["mode"] == mode].pivot(
            index="case_id", columns="input_mv", values="status",
        ).reindex(case_order)
        image = ax.imshow(table.values, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
        ax.set_title(LABELS[mode])
        ax.set_xticks(range(len(table.columns)), [f"{value:g}" for value in table.columns], rotation=65)
        ax.set_xlabel("Differential input (mV), categorical spacing")
    axes[0].set_yticks(range(len(case_order)), case_order)
    fig.subplots_adjust(left=0.26, right=0.86, bottom=0.22, top=0.88, wspace=0.08)
    colorbar_axis = fig.add_axes([0.88, 0.30, 0.012, 0.45])
    colorbar = fig.colorbar(image, cax=colorbar_axis, ticks=[0, 1, 2])
    colorbar.ax.set_yticklabels(["Wrong", "Unresolved", "Correct"])
    fig.suptitle(f"Decision atlas | {deadline_ns:g} ns after clock midpoint | no transient noise", y=1.01)
    return fig


def boundary_figure(reports):
    style()
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(reports))
    for mode, key, shift in (("untrimmed", "baseline", -0.1), ("retuned", "selected", 0.1)):
        centers = [report["calibration"][key]["midpoint_mv"] for report in reports]
        widths = [report["calibration"][key]["halfwidth_mv"] for report in reports]
        ax.errorbar(x + shift, centers, yerr=widths, fmt="o", capsize=3,
                    color=COLORS[mode], label=LABELS[mode])
    ax.axhline(0, color="#cbd5e1", linewidth=1)
    ax.set_xticks(x, [str(index + 1) for index in x])
    ax.set_xlabel("Case number (same order as the decision atlas)")
    ax.set_ylabel("Switching-boundary midpoint (mV)")
    ax.set_title("Foreground calibration: residual boundary, not a foundry offset distribution")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    return fig


def tradeoff_figure(frame):
    style()
    scored = frame[frame.input_mv != 0].copy()
    scored["correct"] = scored.outcome == "correct"
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for mode in MODES:
        subset = scored[scored["mode"] == mode]
        passing = subset.groupby("deadline_ns").correct.mean()
        axes[0].plot(passing.index, 100 * passing, "o-", color=COLORS[mode], label=LABELS[mode])
    energy = scored[scored.deadline_ns == scored.deadline_ns.max()]
    arrays = [energy[energy["mode"] == mode].core_energy_fj.values for mode in MODES]
    boxes = axes[1].boxplot(arrays, tick_labels=[LABELS[mode] for mode in MODES], patch_artist=True)
    for patch, mode in zip(boxes["boxes"], MODES):
        patch.set_facecolor(COLORS[mode])
        patch.set_alpha(0.7)
    axes[0].set(xlabel="Decision deadline (ns)", ylabel="Passing grid points (%)",
                title="Deadline tradeoff (not probability or yield)", ylim=(-2, 102))
    axes[0].legend(fontsize=8)
    axes[1].set(ylabel="DUT VDD energy / full cycle (fJ)",
                title="The analog cost of enabling trim")
    axes[1].tick_params(axis="x", labelsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    return fig


def waveform_figure(output: Path, reports):
    style()
    nominal = next(
        report for report in reports
        if report["point"]["corner"] == "tt"
        and report["point"]["pair_skew"] == 0.04
        and report["point"]["vdd_v"] == 1.8
        and report["point"]["temperature_c"] == 27
    )
    sim = Simulator(output / "runs")
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for ax, code, title in zip(
        axes, (0, nominal["calibration"]["code"]),
        ("Code-zero circuit", "The same circuit with foreground trim"),
    ):
        trace = sim.run(Point(differential_v=-0.001, trim_code=code))
        values = trace.values
        time_ns = (values[:, 0] - EVALUATION_START_S) * 1e9
        selection = (time_ns > -0.3) & (time_ns < 1.5)
        for column, label, color in (
            (1, "Clock", "#94a3b8"), (2, "Q+", "#00a89d"), (3, "Q-", "#df5363"),
        ):
            ax.plot(time_ns[selection], values[selection, column], label=label, color=color)
        ax.axvline(0.5, color="#e99c35", linestyle="--", label="0.5 ns deadline")
        ax.set(title=f"{title}; trim {code:+d}; differential input -1 mV", ylabel="Voltage (V)")
        ax.legend(loc="upper right", ncol=4, fontsize=8)
    axes[-1].set_xlabel("Time from evaluation clock midpoint (ns)")
    fig.tight_layout()
    return fig


def render(output: Path) -> Path:
    frame, reports, manifest = load_results(output)
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    factories = {
        "atlas.png": lambda: atlas_figure(frame),
        "boundaries.png": lambda: boundary_figure(reports),
        "tradeoffs.png": lambda: tradeoff_figure(frame),
        "waveforms.png": lambda: waveform_figure(output, reports),
    }
    for name, factory in factories.items():
        figure = factory()
        figure.savefig(figures / name, dpi=160, bbox_inches="tight")
        plt.close(figure)
    statistics = summary(output)
    pictures = {}
    for name in factories:
        encoded = base64.b64encode((figures / name).read_bytes()).decode("ascii")
        pictures[name] = f'<img alt="{html.escape(name)}" src="data:image/png;base64,{encoded}">'
    limitations = "".join(f"<li>{html.escape(item)}</li>" for item in manifest["limitations"])
    pdk_revision = html.escape(manifest["provenance"]["pdk_revision"])
    version_match = re.search(r"\bngspice-(\S+)", manifest["provenance"]["ngspice_version"])
    if version_match is None:
        raise ValueError("Simulator provenance does not contain a recognizable ngspice version")
    simulator_label = html.escape("ngspice " + version_match.group(1))
    report = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comparator Atlas | Real SPICE, visible tradeoffs</title>
<style>
body{{margin:0;background:#edf2f7;color:#14213d;font:16px/1.65 system-ui,sans-serif}}
header{{background:#101e36;color:#fff;padding:54px max(5vw,24px)}}
header small{{color:#64dfcf;letter-spacing:.16em;font-weight:700}}
h1{{font-size:clamp(36px,5vw,64px);line-height:1.1;margin:20px 0}}
header p{{max-width:820px;color:#c4d2e7}} .tag{{display:inline-block;padding:5px 12px;
border:1px solid #55718c;border-radius:20px;font-size:13px;margin-right:10px}}
main{{max-width:1220px;margin:auto;padding:28px 22px 60px}}
section{{background:#fff;border:1px solid #dce5ee;border-radius:15px;margin:24px 0;padding:28px}}
h2{{margin-top:0}} img{{width:100%;height:auto}} .notice{{border-left:5px solid #e99c35}}
table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{padding:10px;text-align:right;
border-bottom:1px solid #e2e8f0}} th:first-child{{text-align:left}} code{{overflow-wrap:anywhere}}
.cards{{display:flex;gap:18px;flex-wrap:wrap}} .card{{flex:1;min-width:150px;background:#1c304e;
padding:18px;border-radius:10px}} .card strong{{display:block;font-size:30px;color:#64dfcf}}
.muted{{color:#64748b;font-size:14px}} a{{color:#007f78}}
</style>
<header><small>OPEN ANALOG DESIGN / IEEE SSCS CODE-A-CHIP CANDIDATE</small>
<h1>Comparator Atlas</h1><p>When does a dynamic comparator make the wrong decision?
When does it run out of time? What does offset trim actually cost?
A reproducible, transistor-level experiment makes the tradeoffs visible.</p>
<span class="tag">SKY130</span><span class="tag">{simulator_label}</span>
<span class="tag">Research prototype / not submitted</span>
<div class="cards" style="margin-top:28px">
<div class="card"><strong>{manifest["case_count"]}</strong>declared PVT/stress cases</div>
<div class="card"><strong>{manifest["unique_run_count"]}</strong>distinct SPICE runs</div>
<div class="card"><strong>{manifest["row_count"]}</strong>deadline-level observations</div></div></header>
<main><section class="notice"><h2>Evidence, not a performance promise</h2>
<p>This is an original experiment around a conventional StrongARM topology, not a claim of a new
comparator architecture. Every plotted point comes from the pinned transistor models.
The green cells are passing <em>test-grid points</em>, not measured yield or error probability.</p>
<p><strong>Read all three modes:</strong> code zero; a trim code calibrated at TT / 1.8 V / 27 C and
then frozen; and a code recalibrated locally. A local recalibration is an upper-reference policy,
not a free on-chip feature.</p></section>
<section><h2>01 / The decision atlas</h2>{pictures["atlas.png"]}
<p class="muted">Complementary 80% / 20% output rails are required at the stated deadline.
Zero input is excluded from pass-rate denominators. Cases are equally weighted; no operating
distribution is assumed.</p></section>
<section><h2>02 / Offset correction has a cost</h2>{pictures["boundaries.png"]}{pictures["tradeoffs.png"]}
<p class="muted">Error bars bound the measured switching transition at a 3.5 ns calibration deadline;
they are not statistical confidence intervals. Energy includes the entire 10 ns core-rail cycle,
including reset, but excludes all external drivers and control logic.</p>
{statistics.to_html(float_format=lambda value: f"{value:.3f}", border=0)}
<p class="muted">Table pass fractions use the 0.5 ns deadline.</p></section>
<section><h2>03 / Inspect an actual decision</h2>{pictures["waveforms.png"]}
<p class="muted">Illustrative nominal case only. The atlas above includes the other declared cases,
including the cases where calibration fails to help.</p></section>
<section><h2>04 / Reproduce and challenge it</h2>
<p>Open <code>Comparator_Atlas.ipynb</code>, or run
<code>.\\.venv\\Scripts\\python.exe -m comparator_atlas run --profile {manifest["profile"]}</code>.</p>
<p>PDK commit: <code>{pdk_revision}</code>. The manifest records source, model, executable,
and result hashes; each local raw run retains its netlist, logs, and compressed waveform.</p>
<h3>Current scope and missing evidence</h3><ul>{limitations}</ul>
<p class="muted">No award, tapeout, silicon measurement, or submission readiness is implied.
Entrant identity and final research claims must be reviewed before publication.</p></section>
</main></html>"""
    destination = output / "report.html"
    destination.write_text(report, encoding="utf-8")
    return destination
