"""Offline, interactive presentation of checked optimization and validation evidence."""

import base64
from dataclasses import replace
import html
import json
from pathlib import Path
import re
import shutil

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

from .designs import get_design
from .plots import style
from .spice import CORNERS, EVALUATION_START_S, Point, Simulator, sha256, write_json
from .stress import (
    STRESS_NAMES, load_stress, load_verified_validation as load_validation,
    verified_comparison as comparison,
)
from .study import (
    CACHE, POLICIES, STUDY, checked_manifest,
)

POLICY_LABELS = {
    "code_zero": "Code zero", "nominal_frozen": "Nominal code, frozen",
    "local_boundary": "Local 3.5 ns calibration", "deadline_aware": "Local 1 ns calibration",
}
POLICY_COLORS = {
    "code_zero": "#64748b", "nominal_frozen": "#e7a339",
    "local_boundary": "#099c90", "deadline_aware": "#6676dc",
}
STRESS_LABELS = {
    "ideal_reference": "Ideal input reference", "opposite_input_history": "Opposite input history",
    "source_1k_20f": "1 kohm source / 20 fF", "source_5k_20f": "5 kohm source / 20 fF",
    "settling_10k_200f": "10 kohm / 200 fF + history",
    "common_mode_0p45": "Common mode = 0.45 VDD",
    "common_mode_0p60": "Common mode = 0.60 VDD", "output_load_20f": "20 fF output load",
}


def search_figure(selection: dict):
    style()
    records = selection["candidates"]
    names = [record["design"]["name"] for record in records]
    chosen = selection["selected_design"]
    baseline = next(record for record in records if record["design"]["name"] == "baseline")
    colors = ["#099c90" if name == chosen else "#8798b1" for name in names]
    y = np.arange(len(records))
    figure, axes = plt.subplots(1, 3, figsize=(13.5, 5.5), sharey=True)
    axes[0].barh(y, [100 * record["worst_case_correct_fraction"] for record in records], color=colors)
    axes[0].set_yticks(y, names)
    axes[0].invert_yaxis()
    axes[0].set(xlabel="Worst training-case correct points (%)", xlim=(0, 105))
    energy = [
        record["mean_core_energy_fj"] / baseline["mean_core_energy_fj"]
        if record["mean_core_energy_fj"] is not None else np.nan for record in records
    ]
    area = [
        record["design"]["gate_area_proxy_um2"] / baseline["design"]["gate_area_proxy_um2"]
        for record in records
    ]
    axes[1].barh(y, energy, color=colors)
    axes[1].axvline(2, linestyle="--", color="#e7a339", label="Declared 2x budget")
    axes[1].set_xlabel("Mean core energy / baseline")
    axes[1].legend(fontsize=8)
    axes[2].barh(y, area, color=colors)
    axes[2].axvline(4, linestyle="--", color="#e7a339", label="Declared 4x budget")
    axes[2].set_xlabel("Gate-area proxy / baseline (not layout)")
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="x", alpha=0.15)
    figure.suptitle("Every declared candidate is visible; teal was selected before full PVT validation")
    figure.tight_layout()
    return figure


def coverage_figure(frame: pd.DataFrame, selected_name: str, deadline_ns: float = 1.0,
                    minimum_input_mv: float = 1.0, policy: str = "local_boundary"):
    style()
    cmap = LinearSegmentedColormap.from_list("coverage", ["#df5363", "#e9b44c", "#17a897"])
    names = ("baseline", selected_name)
    figure, axes = plt.subplots(2, 5, figsize=(14, 6.2), sharex=True, sharey=True)
    selected = frame[
        (frame.deadline_ns == deadline_ns) & (frame.input_mv.abs() >= minimum_input_mv)
        & (frame.input_mv != 0) & (frame.policy == policy) & (frame.pair_skew == 0.04)
    ].copy()
    selected["correct"] = selected.outcome == "correct"
    for row, name in enumerate(names):
        for column, corner in enumerate(CORNERS):
            data = selected[(selected.design_name == name) & (selected.corner == corner)]
            values = data.groupby(["temperature_c", "vdd_v"]).correct.mean().unstack().reindex(
                index=[-40, 27, 125], columns=[1.62, 1.8, 1.95],
            )
            if values.isna().any().any():
                raise ValueError("The regular 45-condition PVT figure is missing a cell")
            ax = axes[row, column]
            image = ax.imshow(values.values, vmin=0, vmax=1, cmap=cmap, aspect="auto")
            for y in range(3):
                for x in range(3):
                    ax.text(x, y, f"{100 * values.values[y, x]:.0f}%", ha="center", va="center", fontsize=10)
            ax.set_xticks([0, 1, 2], ["1.62", "1.80", "1.95"])
            ax.set_yticks([0, 1, 2], ["-40", "27", "125"])
            ax.set_title(corner.upper())
            if column == 0:
                ax.set_ylabel(("Original circuit" if row == 0 else "Selected circuit") + "\nTemperature (C)")
            if row == 1:
                ax.set_xlabel("VDD (V)")
    figure.subplots_adjust(left=0.09, right=0.90, bottom=0.11, top=0.85, hspace=0.35, wspace=0.18)
    color_axis = figure.add_axes([0.92, 0.23, 0.012, 0.52])
    figure.colorbar(image, cax=color_axis, label="Passing grid fraction (not yield)")
    figure.suptitle(
        f"Same policy, same inputs, same deadline | {POLICY_LABELS[policy]}\n"
        f"|input| >= {minimum_input_mv:g} mV at {deadline_ns:g} ns; +4% branch-width stress",
    )
    return figure


def policy_figure(frame: pd.DataFrame, selected_name: str):
    style()
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), sharey=True)
    for ax, name, title in zip(axes, ("baseline", selected_name), ("Original circuit", "Selected circuit")):
        data = frame[(frame.design_name == name) & (frame.input_mv.abs() >= 1)].copy()
        data["correct"] = data.outcome == "correct"
        for policy in POLICIES:
            grouped = data[data.policy == policy].groupby("deadline_ns").correct.mean()
            ax.plot(grouped.index, 100 * grouped.values, "o-", color=POLICY_COLORS[policy],
                    label=POLICY_LABELS[policy], markersize=4)
        ax.set(title=title, xlabel="Decision deadline (ns)", ylim=(-2, 102))
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Passing grid points (%)")
    axes[1].legend(fontsize=8, loc="lower right")
    figure.suptitle("49 declared conditions, |input| >= 1 mV; unavailable calibration remains in the denominator")
    figure.tight_layout()
    return figure


def guardband_figure(frame: pd.DataFrame, selected_name: str):
    style()
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), sharey=True)
    minimums = (0.25, 0.5, 1, 3, 10, 30)
    for ax, name, title in zip(axes, ("baseline", selected_name), ("Original circuit", "Selected circuit")):
        for policy in ("nominal_frozen", "local_boundary", "deadline_aware"):
            values = []
            for minimum in minimums:
                data = frame[(frame.design_name == name) & (frame.policy == policy)
                             & (frame.deadline_ns == 1) & (frame.input_mv.abs() >= minimum)]
                values.append(100 * (data.outcome == "correct").mean())
            ax.plot(range(len(minimums)), values, "o-", color=POLICY_COLORS[policy], label=POLICY_LABELS[policy])
        ax.set_xticks(range(len(minimums)), [str(value) for value in minimums])
        ax.set(title=title, xlabel="Minimum absolute input in scored band (mV)", ylim=(-2, 102))
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Passing grid points at 1 ns (%)")
    axes[1].legend(fontsize=8, loc="lower right")
    figure.suptitle("Resolution is not free: the tiny-input failures stay visible")
    figure.tight_layout()
    return figure


def operating_figure(operating: pd.DataFrame, selected_name: str):
    style()
    data = operating[operating.deadline_ns == 1].copy()
    data["correct"] = data.outcome == "correct"
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.8), sharey=True)
    y = np.arange(len(STRESS_NAMES))
    for name, shift, color, label in (
        ("baseline", -0.18, "#8798b1", "Original circuit"),
        (selected_name, 0.18, "#099c90", "Selected circuit"),
    ):
        selected = data[data.design_name == name]
        coverage = selected.groupby("stress").correct.mean().reindex(STRESS_NAMES)
        disturbance = selected.groupby("stress").max_differential_input_error_mv.max().reindex(STRESS_NAMES)
        axes[0].barh(y + shift, 100 * coverage.values, height=0.34, color=color, label=label)
        axes[1].barh(y + shift, disturbance.values, height=0.34, color=color)
    axes[0].set_yticks(y, [STRESS_LABELS[name] for name in STRESS_NAMES])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Passing points at 1 ns (%)")
    axes[0].set_xlim(0, 105)
    axes[0].legend(fontsize=8)
    axes[1].set_xlabel("Maximum differential input-pin error (mV)")
    for ax in axes:
        ax.grid(axis="x", alpha=0.2)
    figure.suptitle("No retraining after stress: driver loading, settling, common mode and output load")
    figure.tight_layout()
    return figure


def cold_waveform_figure(reports: list[dict], selected_name: str):
    style()
    simulator = Simulator(CACHE)
    figure, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for ax, design_name in zip(axes, ("baseline", selected_name)):
        report = next(report for report in reports if report["design_name"] == design_name
                      and report["point"]["corner"] == "ss" and report["point"]["vdd_v"] == 1.62
                      and report["point"]["temperature_c"] == -40 and report["point"]["pair_skew"] == 0.04)
        code = report["codes"]["local_boundary"]
        if code is None:
            raise ValueError("The documented cold-corner waveform has no available local code")
        point = replace(Point(**report["point"]), differential_v=-0.001, trim_code=code)
        trace = simulator.run(point)
        x = (trace.values[:, 0] - EVALUATION_START_S) * 1e9
        mask = (x >= -0.15) & (x <= 3.5)
        for column, label, color in ((1, "Clock", "#98a8bf"), (2, "Q+", "#099c90"), (3, "Q-", "#df5363")):
            ax.plot(x[mask], trace.values[mask, column], color=color, label=label)
        ax.axvline(1, linestyle="--", color="#e7a339", label="1 ns deadline")
        ax.set(title=f"{design_name}; local trim {code:+d}", ylabel="Voltage (V)")
        ax.legend(ncol=4, fontsize=8, loc="upper right")
    axes[1].set_xlabel("Time from evaluation clock midpoint (ns)")
    figure.suptitle("The known weak corner, not a cherry-picked nominal trace: SS / 1.62 V / -40 C / -1 mV")
    figure.tight_layout()
    return figure


def explorer_cube(frame: pd.DataFrame, reports: list[dict], selected_name: str) -> dict:
    designs = list(dict.fromkeys(frame.design_name))
    case_names = list(dict.fromkeys(frame.case_id))
    deadlines = sorted(frame.deadline_ns.unique().tolist())
    inputs = sorted(frame.input_mv.unique().tolist())
    designs_index = {value: index for index, value in enumerate(designs)}
    case_index = {value: index for index, value in enumerate(case_names)}
    deadline_index = {value: index for index, value in enumerate(deadlines)}
    input_index = {value: index for index, value in enumerate(inputs)}
    policy_index = {value: index for index, value in enumerate(POLICIES)}
    status = {"wrong": 0, "unresolved": 1, "correct": 2, "calibration_unavailable": 3, "reference": 4}
    rows = []
    for row in frame.itertuples():
        rows.append([
            designs_index[row.design_name], case_index[row.case_id], policy_index[row.policy],
            deadline_index[row.deadline_ns], input_index[row.input_mv],
            4 if row.input_mv == 0 else status[row.outcome],
            round(row.decision_time_ns, 4) if pd.notna(row.decision_time_ns) else None,
            round(row.core_energy_fj, 3) if pd.notna(row.core_energy_fj) else None,
            int(row.trim_code) if pd.notna(row.trim_code) else None,
        ])
    return {
        "designs": designs, "cases": case_names, "policies": list(POLICIES),
        "policyLabels": [POLICY_LABELS[name] for name in POLICIES],
        "deadlines": deadlines, "inputs": inputs, "rows": rows, "selectedDesign": selected_name,
        "trainingCases": sorted({
            case_index[report["case_id"]] for report in reports if report["used_for_design_selection"]
        }),
    }


def paired_energy(frame: pd.DataFrame, selected_name: str) -> dict:
    eligible = frame[(frame.policy == "local_boundary") & (frame.deadline_ns == 1)
                     & (frame.input_mv.abs() >= 1) & frame.policy_available]
    baseline = eligible[eligible.design_name == "baseline"][["case_id", "input_mv", "core_energy_fj"]]
    selected = eligible[eligible.design_name == selected_name][["case_id", "input_mv", "core_energy_fj"]]
    matched = baseline.merge(selected, on=["case_id", "input_mv"], suffixes=("_baseline", "_selected"), validate="one_to_one")
    if matched.empty:
        raise ValueError("There are no matched, actually simulated energy comparison points")
    original = float(matched.core_energy_fj_baseline.mean())
    improved = float(matched.core_energy_fj_selected.mean())
    return {
        "matched_points": len(matched), "baseline_fj": original, "selected_fj": improved,
        "relative_change_percent": 100 * (improved / original - 1),
        "gate_area_ratio": get_design(selected_name).gate_area_um2 / get_design("baseline").gate_area_um2,
    }


def render_study(*, refresh_figures: set[str] | None = None) -> Path:
    import layout_evidence as physical
    from presentation import pvt45_results, specification_map, waveform_lab

    frame, reports, manifest = load_validation()
    layout = physical.load_layout()
    full_pvt = pvt45_results.load_results()
    pvt45_results.review_examples(full_pvt)
    waveform_data = waveform_lab.load_lab()
    _, operating, stress = load_stress()
    optimization = checked_manifest("optimization_manifest.json")
    selection = json.loads((STUDY / "selection.json").read_text())
    name = selection["selected_design"]
    author = json.loads((STUDY.parents[1] / "entry_metadata.json").read_text())["authors"][0]
    professional = None
    professional_directory = STUDY / "professional"
    if (professional_directory / "manifest.json").is_file():
        professional_status = json.loads((professional_directory / "manifest.json").read_text())
        if professional_status["status"] == "complete":
            import entry_tools
            professional = entry_tools.load_evidence()
    score = comparison()
    reserved = comparison(reserved_only=True)
    energy = paired_energy(frame, name)
    baseline_fraction = float(score.loc[("baseline", "local_boundary"), "pass_fraction"])
    selected_fraction = float(score.loc[(name, "local_boundary"), "pass_fraction"])
    figures = STUDY / "figures"
    figures.mkdir(exist_ok=True)
    factories = {
        "search.png": lambda: search_figure(selection),
        "pvt.png": lambda: coverage_figure(frame, name),
        "policies.png": lambda: policy_figure(frame, name),
        "guardbands.png": lambda: guardband_figure(frame, name),
        "operating.png": lambda: operating_figure(operating, name),
        "cold_waveforms.png": lambda: cold_waveform_figure(reports, name),
        "actual_layout.png": lambda: physical.layout_figure(layout),
        "layout_deadlines.png": lambda: physical.deadline_figure(layout),
        "layout_costs.png": lambda: physical.tt_cost_figure(layout),
        "layout_waveforms.png": lambda: physical.review_layout_waveforms(layout)[1],
        "pvt45_timing.png": lambda: pvt45_results.timing_figure(full_pvt["frame"]),
        "pvt45_comparison.png": lambda: pvt45_results.tradeoff_figure(full_pvt["frame"]),
        "pvt45_worst_waveform.png": lambda: pvt45_results.worst_case_figure(full_pvt),
    }
    if professional is not None:
        factories["efficient_control.png"] = lambda: entry_tools.tradeoff_figure(professional)
    previous_artifacts = {}
    if refresh_figures is not None:
        if refresh_figures - factories.keys():
            raise ValueError("Requested report figure is not a declared factory")
        previous_artifacts = {
            name.replace("\\", "/"): digest
            for name, digest in json.loads(
                (STUDY / "presentation_manifest.json").read_text())["artifact_sha256"].items()
        }
    pictures = {}
    for filename, factory in factories.items():
        if refresh_figures is None or filename in refresh_figures:
            figure = factory()
            figure.savefig(figures / filename, dpi=150, bbox_inches="tight")
            plt.close(figure)
        else:
            recorded = previous_artifacts[f"figures/{filename}"]
            if sha256(figures / filename) != recorded:
                raise ValueError(f"Cannot reuse changed report figure: {filename}")
        data = base64.b64encode((figures / filename).read_bytes()).decode("ascii")
        pictures[filename] = f'<img alt="{filename}" src="data:image/png;base64,{data}">'
    guide = physical.circuit_guide_path()
    shutil.copyfile(guide, figures / "circuit_guide.png")
    guide_data = base64.b64encode(guide.read_bytes()).decode("ascii")
    pictures["circuit_guide.png"] = f'<img alt="circuit_guide.png" src="data:image/png;base64,{guide_data}">'
    cube = explorer_cube(frame, reports, name)
    write_json(STUDY / "explorer_data.json", cube)
    payload = json.dumps(cube, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    javascript_path = Path(__file__).parent / "assets" / "explorer.mjs"
    javascript = javascript_path.read_text(encoding="utf-8")
    waveform_javascript_path = STUDY.parents[1] / "presentation" / "waveform_explorer.mjs"
    waveform_javascript = waveform_javascript_path.read_text(encoding="utf-8")
    waveform_payload = json.dumps(waveform_data, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    professional_section = ""
    sampled_analysis = None
    if professional is not None:
        sampled = specification_map.load_checked(professional)
        sampled_analysis = {
            "source_sha256": sha256(Path(specification_map.__file__)),
            "summary_sha256": sha256(specification_map.FOLDER / "summary.json"),
        }
        target_band = entry_tools.summary(professional, minimum_mv=1)
        wide_band = entry_tools.summary(professional, minimum_mv=3)
        professional_section = f"""
<section><h2>Post-selection lower-energy control</h2>
<p>This is an explicitly <strong>post-selection ablation</strong> of an existing lower-energy
LVT candidate. It uses the same 49 conditions and input grid with separate numerical refinement;
it does not replace the frozen original selection or create a newly blinded benchmark.</p>
{pictures["efficient_control.png"]}
<h3>Local calibration, 1 ns, sampled |input| &ge; 1 mV</h3>
<div class="table-scroll">{target_band.to_html(float_format=lambda value: f"{value:.4g}", border=0)}</div>
<h3>Same policy and deadline, sampled |input| &ge; 3 mV</h3>
<div class="table-scroll">{wide_band.to_html(float_format=lambda value: f"{value:.4g}", border=0)}</div>
<p class="muted">All-sampled-points passing is not a guarantee between sample points.
Worst-condition coverage and the count of fully passing conditions are reported alongside
the mean. Neither circuit is asserted best for every energy, input-resolution or interface requirement.</p>
<h3>Calibration workload, not implemented on-chip calibration cost</h3>
<div class="table-scroll">{entry_tools.calibration_workload(professional).to_html(border=0)}</div>
<p class="muted">A distinct probe represents an offline three-cycle simulation.
Reference/input generation, drivers, control logic and storage are not included in core energy.
The additional control has not inherited the original/selected circuits' input-interface stress results.</p>
<h3>Matched failures and sampled specification limits</h3>
<p>The following static tables use only the calibrated schematic 49-condition
controlled-width-stress domain, not the nominal RC grid. Every included signed
sample must be correct before mean full-cycle core energy ranks qualified designs.
NONE means no feasible compared design and retains null metrics (shown as NaN),
not a best-average substitute. The 36 choices remain 28 NONE / 5 selected / 3 control.</p>
<div class="table-scroll">{specification_map.example_table(sampled).to_html(index=False, float_format=lambda value: f"{value:.4g}", border=0)}</div>
<p>Margins are deadline minus recorded decision time; maxima are observed core
energies over the same band. They are not noise/jitter/PVT confidence bounds,
timing signoff, worst-cycle guarantees or total system/calibration cost.
All exact limiting ties and source hashes are retained in
<a href="specification_map/summary.json">the auditable JSON</a>.</p>
<h4>Exactly matched 1 ns to 2 ns samples, |input| &ge; 1 mV</h4>
<div class="table-scroll">{specification_map.failure_table(sampled).to_html(index=False, border=0)}</div>
<p>Baseline's 60 unresolved samples become 29 correct, nine wrong and 22 unresolved;
the control's nine become six correct and three wrong. Longer deadlines need not
reduce wrong counts. Selected's 20 wrong samples are exactly the same keyed set
at both deadlines, all at +/-1 mV. Locations and local calibration codes below
are observations, not evidence of trim saturation, residual offset or noise.</p>
<div class="table-scroll">{specification_map.selected_wrong_table(sampled).to_html(index=False, border=0)}</div>
</section>"""
    version = re.search(r"\bngspice-(\S+)", manifest["provenance"]["ngspice_version"])
    if version is None:
        raise ValueError("Missing simulator version in the checked evidence")
    layout_table = physical.deadline_summary(layout)
    layout_geometry = physical.geometry_summary(layout)
    layout_costs = physical.matched_tt_comparison(layout)
    layout_section = f"""
<section id="layout-evidence"><h2>Layout geometry, structural checks and five-condition pilot</h2>
<p>The nominal 27-device layout has recorded GDS, named-style DRC, independent LVS,
wrong-net/bulk/width/SVT-LVT negative controls, and separate connectivity/C/RC exports.
The original layout development used <strong>five code-zero conditions</strong>.
The following expanded study covers 45 PVT conditions with the same nominal geometry.
Neither is a post-layout reproduction of the calibrated width-stress study.</p>
{pictures["actual_layout.png"]}
<div class="table-scroll">{layout_geometry.to_html(index=False, float_format=lambda value: f"{value:.4g}", border=0)}</div>
<p class="muted">The compact predecessor failed M2 pad-notch spacing and was never simulated.
Four M2 bridges repair it without changing devices, pins or the other mask geometry.
Archived-deck differences are measured against the prior <em>legal balanced layout</em>, not attributed to
the bridges alone. Listed capacitance is a sum of emitted elements, not an effective impedance.</p>
<p class="muted">Scope: {html.escape(pvt45_results.RC_SCOPE_NOTE)}</p>
{pictures["layout_costs.png"]}
<div class="table-scroll">{layout_costs.to_html(index=False, float_format=lambda value: f"{value:.4g}", border=0)}</div>
<h3>Earlier five-condition layout pilot (ngspice 42)</h3>
<p><strong>The original 1 ns pilot still fails:</strong> RC has 12/20 correct points and
8 late SS points. At the already recorded <strong>2 ns window</strong>, all 20 sampled RC
points are correct, with retained 10-to-5 ps comparisons meeting the same numerical limits.
This is post-hoc characterization, not a relaxed replacement for the original target.</p>
{pictures["layout_deadlines.png"]}
<div class="table-scroll">{layout_table.to_html(index=False, border=0)}</div>
{pictures["layout_waveforms.png"]}
<p class="muted">Each mode in this earlier pilot has five conditions times four inputs:
20 points, not 80 RC tests. Its original gated 45-condition extension did not run; 3.5 ns
was not evaluated. These records remain separate from the new full-grid study below.</p>
<p>Recorded verification run:
<a href="{html.escape(layout["receipt"]["run"]["run_url"])}">compact-layout repair evidence</a>.
The workflow's failure status reflects the preserved 1 ns performance gate,
not a hidden DRC/LVS failure. Source replay instructions bind the original experimental commit.</p>
</section>"""
    pvt_table = pvt45_results.comparison_table(full_pvt["frame"])
    pvt_section = f"""
<section id="pvt45-evidence"><h2>Nominal 45-PVT grid: 180 SC and 180 archived RC points</h2>
<p>The repaired nominal, code-zero schematic and RC circuits were evaluated at
five process corners, three supplies and three temperatures: <strong>45 conditions,
four signed inputs each, 180 points per mode</strong>. The primary 2 ns deadline
was declared before this expanded study; 1 ns is reported alongside it.</p>
<p><strong>Archived RC decks: 180/180 correct at 2 ns; 156/180 at 1 ns.</strong>
The other 24 points are late, with no wrong decisions. All point histories
meet the same numerical criteria at 10 and 5 ps.</p>
{pictures["pvt45_timing.png"]}
<p class="muted">Each cell is the maximum sampled delay over -10, -3, +3 and +10 mV.
Black outlines mark a missed 1 ns sample. Five conditions had been observed in the
earlier pilot; forty are new post-layout conditions, not a blinded external test.</p>
<div class="table-scroll">{pvt_table.to_html(index=False, float_format=lambda value: f"{value:.4g}", border=0)}</div>
{pictures["pvt45_comparison.png"]}
<p>The slowest sampled RC point is <strong>FS / 1.62 V / -40 C / -3 mV:
1.835 ns</strong>. Mean core energy is 245.84 fJ schematic versus 425.49 fJ RC.
The mean per-point overhead is 73.45%; the ratio of population means is 73.08%.</p>
{pictures["pvt45_worst_waveform.png"]}
<p class="muted">Both modes in this study use ngspice 47, the same pinned SKY130 models,
nominal dimensions, code zero, 5 fF output loads, 0.5 VDD common mode and a 10 ns clock
with 50 ps edges. This is a finite sampled result, not a noise, mismatch-yield or
continuous-input guarantee. It does not retroactively change the earlier 1 ns pilot.</p>
<p class="muted">Scope: {html.escape(pvt45_results.RC_SCOPE_NOTE)}
<a href="../../REPRODUCIBILITY.md#archived-rc-model-applicability">Extraction-model evidence and limitations</a>.</p>
<p>Publication-size vector figures:
<a href="postlayout_pvt45/figures/pvt45_timing.pdf">PVT timing</a>,
<a href="postlayout_pvt45/figures/pvt45_comparison.pdf">paired comparison</a>,
<a href="postlayout_pvt45/figures/pvt45_worst_waveform.pdf">worst-case waveform</a>.</p>
</section>"""
    html_body = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Comparator Atlas | SKY130 StrongARM characterization</title>
<style>
:root{{color-scheme:light;--ink:#222;--teal:#087f76;--muted:#525e6a}}
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:var(--ink);font:15px/1.65 system-ui,sans-serif}}
header{{max-width:1156px;margin:auto;padding:32px 28px 12px;border-bottom:2px solid #222}}
header small{{font-weight:600}}h1{{font-size:clamp(30px,4vw,42px);line-height:1.15;margin:14px 0}}
header p{{max-width:1000px}}main{{max-width:1156px;margin:auto;padding:0 28px 24px}}
section{{margin:24px 0;padding:18px 0;border-bottom:1px solid #dce5ef}}
h2{{margin:0 0 12px;font-size:25px}}h3{{margin-bottom:6px}}img{{width:100%;height:auto}}
.muted{{color:var(--muted);font-size:13px}}
.table-scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{padding:9px;text-align:right;border-bottom:1px solid #e2e8f0;white-space:nowrap}}th:first-child{{text-align:left}}
code{{overflow-wrap:anywhere;font-size:12px}}a{{color:#087f76}}.controls{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
label{{display:flex;align-items:center;gap:6px;font-size:13px}}select{{padding:8px;border:1px solid #cdd8e5;border-radius:7px;background:white;color:var(--ink)}}
#explorer-grid{{max-height:640px;overflow:auto;border:1px solid #dce5ef;border-radius:8px}}
.decision-grid th,.decision-grid td{{padding:2px;white-space:nowrap;font-size:10px;border:1px solid #fff}}
.decision-grid thead{{position:sticky;top:0;background:#eff4f9;z-index:2}}
.decision-grid th:first-child{{position:sticky;left:0;background:#f7f9fc;min-width:235px;z-index:1;padding-left:8px}}
.grid-cell{{display:block;width:100%;min-width:27px;height:21px;border:0;cursor:pointer;color:#fff;font-weight:700}}
.grid-cell:focus{{outline:2px solid #14213d;outline-offset:-2px}}.outside-score{{opacity:.32}}
#explorer-stats{{font-weight:700;color:#076e66}}#explorer-detail{{min-height:65px;padding:14px;background:#f0f5f9;border-radius:8px;font-size:13px}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;margin:12px 0}}.swatch{{width:12px;height:12px;display:inline-block;margin-right:5px}}
.metric{{font-weight:700;color:#087f76}}.split{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}}
.waveform-presets{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}}
.waveform-presets button{{border:1px solid #c4d6e0;border-radius:7px;background:#f1f7fa;padding:9px 12px;color:var(--ink);cursor:pointer}}
.waveform-presets button:focus-visible,#waveform-sample:focus-visible,#waveform-deadline:focus-visible{{outline:3px solid #159e92;outline-offset:2px}}
.waveform-controls{{display:grid;grid-template-columns:minmax(230px,1.4fr) minmax(220px,1fr);gap:20px;align-items:center}}
.waveform-controls label{{display:block}}.waveform-controls select,.waveform-controls input{{display:block;width:100%;margin-top:7px}}
.waveform-controls output{{font-weight:700;color:#087f76}}#waveform-plot svg{{display:block;width:100%;height:auto}}
#waveform-status{{font-size:18px;font-weight:700;padding:12px 15px;border-radius:8px;background:#edf5f7;margin:18px 0}}
#waveform-status[data-outcome="correct"]{{color:#08796b;background:#e8f7f1}}
#waveform-status[data-outcome="wrong"]{{color:#a32b3f;background:#fff0f2}}
#waveform-status[data-outcome="unresolved"]{{color:#885b10;background:#fff7e3}}
.waveform-metrics{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0}}
.waveform-metrics div{{background:#f2f6fa;border-radius:8px;padding:14px}}
.waveform-metrics strong{{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}}
#waveform-source{{font-size:11px;overflow-wrap:anywhere;color:var(--muted)}}#waveform-error{{color:#a32b3f;font-weight:700}}
@media(max-width:700px){{header{{padding:22px 18px 12px}}main{{padding:0 18px 18px}}section{{padding:14px 0}}.controls label{{width:100%}}}}
@media(max-width:700px){{.waveform-controls,.waveform-metrics{{grid-template-columns:1fr}}}}
@media print{{header{{padding:20px}}section{{break-inside:avoid}}.controls,#explorer-grid,#explorer-detail{{display:none}}}}
</style>
<header><small>IEEE SSCS Code-a-Chip / ISSCC 2027</small>
<h1>Comparator Atlas</h1>
<p><strong>{html.escape(author["name"])}</strong> &mdash; {html.escape(author["affiliation"])}</p>
<p>SKY130 StrongARM comparator: calibrated schematic characterization and archived
nominal-layout simulations. Decision correctness, delay and core-rail energy are
reported for explicit input, PVT and deadline conditions.</p>
</header><main>
<section><h2>Study design and aggregate schematic results</h2>
<p>The schematic study uses ngspice {html.escape(version.group(1))} and
49 &times; {len(manifest["designs"])} declared operating cases: 45 PVT combinations
plus four nominal stress controls per design. The selected circuit contains
{get_design(name).transistor_count} transistor instances, including physical trim branches.</p>
<p>With the same local calibration, a 1 ns deadline and sampled |input| &ge; 1 mV,
correct-point coverage changes from {100 * baseline_fraction:.1f}% to {100 * selected_fraction:.1f}%.
Mean core-rail energy changes by {energy["relative_change_percent"]:+.1f}% over
{energy["matched_points"]} matched points; this excludes external drivers and calibration infrastructure.</p>
<div class="split"><div><p>Selected circuit: <code>{html.escape(name)}</code>.</p>
<p>The transistor gate-area proxy is <span class="metric">{energy["gate_area_ratio"]:.2f}x</span> the original.
Matched mean core-rail energy is <strong>{energy["baseline_fj"]:.2f} &rarr; {energy["selected_fj"]:.2f} fJ/cycle</strong>.
This is not a claim of lower area, lower system power, silicon yield or a new comparator topology.</p></div>
<div><p>The comparison uses the same local calibration policy, input band and deadline.
A lower-energy candidate is included to show the accuracy-energy tradeoff.</p>
<p>The PVT comparison is schematic-level. The physical-layout section separately reports
nominal code-zero measurements and the remaining slow-corner limitation.</p></div></div></section>
<section><h2>27-device circuit topology and trim branches</h2>{pictures["circuit_guide.png"]}
<p class="muted">The source-checked MOS schematic shows the cross-coupled core, a reset PFET
repeated at the four listed nodes, and one trim bit repeated on both sides for k = 0–3.
Filled dots are electrical junctions; unmarked crossings are unconnected. Matching node labels
across panels denote the same net. All 27 instances, device flavors and body ties are retained.
<a href="../presentation/circuit_guide.pdf">Vector PDF schematic</a>.</p></section>
<section><h2>Nine-candidate selection on three declared conditions</h2>{pictures["search.png"]}
<p class="muted">Selection used TT/1.8 V/27 C, SS/1.62 V/-40 C and FF/1.95 V/125 C,
six declared input values, and 2x energy / 4x gate-area-proxy budgets. The initial prototype informed the family.
The recorded objective and candidate list were frozen before this campaign. No global optimum is asserted.</p></section>
<section><h2>Schematic PVT comparison at controlled width stress</h2>{pictures["pvt.png"]}
<p class="muted">The figure contains the regular 45-condition PVT grid at +4% branch-width stress.
All plots and tables are deterministic test coverage, not error probability or manufacturing yield.
The four additional nominal stress controls remain in the full table and explorer.</p>
<div class="table-scroll">{score.to_html(float_format=lambda value: f"{value:.4g}", border=0)}</div>
<h3>Reserved conditions only</h3>
<p class="muted">The following table removes the three selection conditions. It is an internal reserved evaluation,
not a blinded external benchmark. Unavailable calibration remains a failed coverage point; its energy is not invented.</p>
<div class="table-scroll">{reserved.to_html(float_format=lambda value: f"{value:.4g}", border=0)}</div></section>
{professional_section}
<section><h2>Stored decision map: circuit, calibration and deadline</h2>
<p>These controls filter stored SPICE observations; they do not launch simulations.
The input guardband changes the scoring band, not the underlying outcomes. Dimmed cells are outside that band.</p>
<div class="controls">
<label>Circuit <select id="explorer-design"></select></label>
<label>Policy <select id="explorer-policy"></select></label>
<label>Deadline <select id="explorer-deadline"></select></label>
<label>Scored inputs <select id="explorer-guardband"></select></label>
<label><input type="checkbox" id="explorer-reserved">Exclude selection conditions</label></div>
<div class="legend">
<span><i class="swatch" style="background:#17a897"></i>Correct</span>
<span><i class="swatch" style="background:#df5363"></i>Wrong</span>
<span><i class="swatch" style="background:#e9b44c"></i>Unresolved</span>
<span><i class="swatch" style="background:#8876c8"></i>Calibration unavailable</span>
<span><i class="swatch" style="background:#d5dee9"></i>Zero input, unscored</span></div>
<p id="explorer-stats" aria-live="polite"></p><div id="explorer-grid"></div>
<p id="explorer-detail" role="status"></p></section>
<section id="waveform-lab"><h2>Retained waveforms: wrong-sign, unresolved and correct decisions</h2>
<p><strong>Eight declared examples from retained waveforms</strong> compare the complementary
output rails against each recorded deadline.
These are representative teaching cases, not the raw trace for every atlas cell and not a new validation set.
Changing the deadline reads the same trace; it does not run SPICE or alter a circuit.</p>
<div class="waveform-presets" role="group" aria-label="Guided waveform examples">
<button type="button" data-waveform-example="schematic_untrimmed" data-waveform-deadline="1">1. Wrong is not late</button>
<button type="button" data-waveform-example="schematic_calibrated" data-waveform-deadline="1">2. Same circuit, calibrated</button>
<button type="button" data-waveform-example="layout_ss_cold_negative" data-waveform-deadline="1">3. A slow extracted decision</button>
<button type="button" data-waveform-example="layout_ss_cold_negative" data-waveform-deadline="2">4. Read the retained 2 ns window</button>
</div>
<div class="waveform-controls">
<label for="waveform-sample">Actual stored example<select id="waveform-sample"></select></label>
<label for="waveform-deadline">Decision deadline: <output id="waveform-deadline-value" for="waveform-deadline"></output>
<input id="waveform-deadline" type="range" aria-label="Recorded decision deadline"></label>
</div>
<p id="waveform-error" role="alert"></p>
<p id="waveform-status" role="status" aria-live="polite"></p>
<p id="waveform-scope" class="muted"></p>
<div class="legend"><span><i class="swatch" style="background:#009c8d"></i>Q+</span>
<span><i class="swatch" style="background:#cc5967"></i>Q-</span>
<span><i class="swatch" style="background:#98a8bb"></i>Clock</span>
<span>Horizontal dotted lines: fixed 80% / 20% supply thresholds</span></div>
<div id="waveform-plot"></div>
<p id="waveform-rails"></p>
<div class="waveform-metrics">
<div><strong>CORE-RAIL ENERGY</strong><span id="waveform-energy"></span></div>
<div><strong>RETAINED DECISION-TIME MEASUREMENT</strong><span id="waveform-latency"></span></div>
</div>
<p class="muted">Core energy is measured over the entire 10 ns cycle and does not shrink when the display deadline moves.
Cursor voltages use the original waveform samples; latency is a sampled measurement, not an exact crossing.
For layout examples, the original 1 ns pilot remains failed even when an individual trace resolves by 2 ns.</p>
<p class="muted">Scope: {html.escape(pvt45_results.RC_SCOPE_NOTE)}</p>
<details><summary>Source record</summary><p id="waveform-source"></p></details></section>
<section><h2>Calibration deadline and scored input band</h2>{pictures["policies.png"]}{pictures["guardbands.png"]}
<p class="muted">The hardware comparison uses the same local 3.5 ns calibration policy.
The 1 ns policy is a separate ablation: it minimizes the finite-deadline decision interval rather than
only its long-deadline offset. A failed calibration is explicitly unavailable, not silently replaced by code zero.</p></section>
<section><h2>Retained cold-corner schematic waveform</h2>{pictures["cold_waveforms.png"]}
<p class="muted">This condition was known to be weak in the first prototype and was included in selection.
It illustrates mechanism; the reserved/full PVT tables, not this one waveform, support generalization within the declared grid.</p></section>
<section><h2>Input history, settling and interface perturbations</h2>{pictures["operating.png"]}
<p class="muted">Five nominal/extreme PVT conditions, four inputs, and eight explicitly defined stresses per design.
Codes are frozen before perturbing the interface. The history step changes the external input at 18 to 18.05 ns;
evaluation starts at 22.025 ns. Pin error includes deterministic settling and kickback, not random noise.</p>
<p class="muted">{html.escape(stress["numerical_scope"])} Refinement limits are identical outcomes,
at most 1% core-energy difference and at most 20 ps resolved-latency difference. These checks are not production signoff.</p></section>
{layout_section}
{pvt_section}
<section><h2>Reproduction, scope and references</h2>
<p>Public entry: <code>Comparator_Atlas.ipynb</code>, with Python 3.10 review mode and Colab bootstrap.
Optional Windows bootstrap:
<code>node scripts\\setup.mjs</code>. Then run the CLI stages
<code>optimize</code>, <code>study</code>, <code>stress</code> and <code>report</code>
with the project Python and <code>-m comparator_atlas</code>.</p>
<p>Full commands, tool versions and source-data locations are in
<a href="../../REPRODUCIBILITY.md">REPRODUCIBILITY.md</a>.
Saved outputs are checked against their source records before analysis.</p>
<h3>Scope</h3>
<p>These are deterministic simulations. Controlled width perturbations are not a foundry
mismatch distribution or yield. Core energy excludes external drivers and calibration infrastructure.
The calibrated schematic and nominal-layout experiments have separate condition sets;
DRC/LVS do not establish silicon performance or complete foundry signoff.</p>
<h3>Established ideas and related work</h3>
<ul>
<li>B. Razavi, <a href="https://doi.org/10.1109/MSSC.2015.2418155">The StrongARM Latch</a>, 2015.</li>
<li>S. Li, Z. Xu and T. Iizuka, <a href="https://doi.org/10.1007/s10470-022-01992-6">
Analysis of strong-arm comparator with auxiliary pair for offset calibration</a>, 2022.</li>
<li><a href="https://github.com/ChrisZonghaoLi/sky130_comparator_rl">Open comparator optimization research</a>
and <a href="https://github.com/edonD/sky130-comparator">an existing SKY130/LVT comparator example</a>.
Their code, figures, performance claims and statistical assumptions are not reused as this study's evidence.</li>
<li><a href="https://github.com/google/skywater-pdk-libs-sky130_fd_pr">Official SKY130 primitive models</a>
and <a href="https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io">current competition rules</a>.</li>
</ul><p class="muted">GitHub Copilot assisted implementation, experiment automation, figures
and documentation. Original code is MIT licensed; model and tool licenses are retained.</p>
</section></main>
<script id="atlas-cube" type="application/json">{payload}</script>
<script id="waveform-lab-data" type="application/json">{waveform_payload}</script>
<script type="module">{javascript}</script>
<script type="module">{waveform_javascript}</script></html>"""
    path = STUDY / "report.html"
    path.write_text(html_body, encoding="utf-8")
    write_json(STUDY / "presentation_manifest.json", {
        "status": "complete",
        "validation_manifest_sha256": sha256(STUDY / "validation_manifest.json"),
        "stress_manifest_sha256": sha256(STUDY / "stress_manifest.json"),
        "report_source_sha256": sha256(Path(__file__)),
        "explorer_source_sha256": sha256(javascript_path),
        "professional_control_manifest_sha256": sha256(professional_directory / "manifest.json")
        if professional is not None else None,
        "layout_receipt_sha256": physical.RECEIPT_SHA256,
        "layout_review_source_sha256": sha256(physical.ROOT / "layout_evidence.py"),
        "waveform_lab_data_sha256": sha256(waveform_lab.FOLDER / "waveform_lab.json"),
        "waveform_lab_manifest_sha256": sha256(waveform_lab.FOLDER / "manifest.json"),
        "waveform_ui_source_sha256": sha256(waveform_javascript_path),
        "full_pvt45_input_sha256": pvt45_results.REFERENCE_FILES,
        "full_pvt45_plot_source_sha256": sha256(Path(pvt45_results.__file__)),
        "rc_model_applicability_notice": pvt45_results.RC_SCOPE_NOTE,
        "sampled_schematic_analysis": sampled_analysis,
        "artifact_sha256": {
            "report.html": sha256(path), "explorer_data.json": sha256(STUDY / "explorer_data.json"),
            **{str(Path("figures") / filename): sha256(figures / filename) for filename in pictures},
        },
    })
    return path
