"""Check full-grid coverage before turning retained PVT observations into summary claims."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import re

import numpy as np
import pandas as pd

from comparator_atlas.spice import EVALUATION_START_S, Point, Trace, measure
from entry_tools import artifact_path, verify_files

CORNERS = ("tt", "ss", "ff", "sf", "fs")
VOLTAGES = (1.62, 1.8, 1.95)
TEMPERATURES = (-40, 27, 125)
INPUTS_MV = (-10, -3, 3, 10)
MODES = ("schematic", "rc")
DEADLINES = (1, 2)
POINT_KEY = ("corner", "vdd_v", "temperature_c", "differential_mv")
ROW_KEY = (*POINT_KEY, "mode")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "study" / "postlayout_pvt45"
REFERENCE_FILES = {
    "measurements.csv": "0710979ebc65c955a8d7071e5704e51a34ef9c03993ebe9138c7461d6856d9ca",
    "source-summary.json": "757f211e115c5cee2aeb1565c4b4bec9a5c64cce4d080f2b10c19e33123d89a7",
    "independent-audit.json": "5f1c3b7284d990a4e1296a0662e0a195e5f27a5987bcb10b3b5b01d911840a39",
    "condition-table.csv": "a10d93b84973780a558c36222f0a9d9388a63828c5069fc46996d4cb8705faec",
}
EXAMPLE_INDEX_SHA256 = "0860bdc0258e002abc0d633a12f1a1050122a7177bffb49091036f872b6390aa"

RC_MODEL_LABEL = "Archived RC-deck outcomes; model physical fidelity not yet qualified"
RC_MODEL_NOTICE = (
    "These RC results are outcomes of the archived 27-device simulation decks; "
    "extracted-model physical fidelity is not yet qualified. In the pinned Magic/open_pdks "
    "pipeline, mutual capacitances are retained while grounded capacitance increases. "
    "The physical error magnitude and direction are unknown; no exact duplication factor "
    "or corrected counts or energy are inferred. C-only is not independent ground truth, "
    "and RC-versus-C performance differences cannot be attributed solely to resistance. "
    "DRC/LVS establish their recorded structural checks, not parasitic-model fidelity. "
    "Schematic results are unaffected by this extraction concern. Recorded numerical "
    "agreement and simulation coverage do not establish silicon PVT performance."
)


def validate_grid(frame: pd.DataFrame) -> None:
    required = {
        *ROW_KEY, "pair_skew", "trim_code", "common_mode_ratio",
        "output_load_ff_each", "finest_step_ps", "run_identity",
        "execution_status", "numerically_qualified", "reset_ok", "core_energy_fj",
        *(
            f"{field}_{deadline}ns"
            for deadline in DEADLINES
            for field in ("outcome", "decision", "decision_time_ns", "qp_at_deadline_v", "qn_at_deadline_v")
        ),
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"PVT result table is missing fields: {sorted(missing)}")
    expected = set(product(CORNERS, VOLTAGES, TEMPERATURES, INPUTS_MV, MODES))
    actual = set(frame[list(ROW_KEY)].itertuples(index=False, name=None))
    if len(frame) != 360 or frame.duplicated(list(ROW_KEY)).any() or actual != expected:
        raise ValueError("The declared PVT table must contain exactly 180 points per mode, including missing results")
    for field, value in (("pair_skew", 0), ("trim_code", 0), ("common_mode_ratio", 0.5),
                         ("output_load_ff_each", 5)):
        if not frame[field].eq(value).all():
            raise ValueError(f"Fixed PVT stimulus changed: {field}")
    if not pd.api.types.is_bool_dtype(frame.numerically_qualified):
        raise ValueError("Numerical qualification must be explicit boolean data")
    if not frame.execution_status.isin(("success", "not_run")).all():
        raise ValueError("Execution errors require a separately reviewed error classification, not a coverage pass")
    absent = frame.execution_status == "not_run"
    if frame.loc[absent, "numerically_qualified"].any():
        raise ValueError("An unexecuted point cannot be numerically qualified")
    measured_fields = [
        "run_identity", "core_energy_fj", "finest_step_ps",
        *(
            f"{field}_{deadline}ns"
            for deadline in DEADLINES
            for field in ("outcome", "decision", "decision_time_ns", "qp_at_deadline_v", "qn_at_deadline_v")
        ),
    ]
    if frame.loc[absent, measured_fields].notna().any().any():
        raise ValueError("An unexecuted point contains invented measurements")
    observed = frame.loc[~absent]
    if not observed.reset_ok.eq(True).all() or observed.run_identity.isna().any():
        raise ValueError("A successful observation requires reset and its actual source identity")
    if not np.isfinite(observed.core_energy_fj).all() or not observed.core_energy_fj.gt(0).all():
        raise ValueError("Core energy must be a finite positive measurement")
    if observed.run_identity.duplicated().any():
        raise ValueError("One physical run identity was reused for different PVT points")
    fine = observed[observed.numerically_qualified]
    if not fine.finest_step_ps.isin((5, 2.5, 1.25, 0.625, 0.3125, 0.15625)).all():
        raise ValueError("Numerical confirmation cannot be assigned to an unpaired coarse observation")
    for deadline in DEADLINES:
        outcome = observed[f"outcome_{deadline}ns"]
        decision = observed[f"decision_{deadline}ns"]
        latency = observed[f"decision_time_ns_{deadline}ns"]
        qp, qn = observed[f"qp_at_deadline_v_{deadline}ns"], observed[f"qn_at_deadline_v_{deadline}ns"]
        if not np.isfinite(qp).all() or not np.isfinite(qn).all():
            raise ValueError("Recorded output voltages are incomplete")
        calculated = np.where(
            (qp >= 0.8 * observed.vdd_v) & (qn <= 0.2 * observed.vdd_v), 1,
            np.where((qn >= 0.8 * observed.vdd_v) & (qp <= 0.2 * observed.vdd_v), -1, 0),
        )
        if not np.array_equal(decision.to_numpy(), calculated):
            raise ValueError("Reported decision differs from the fixed complementary-rail criterion")
        expected_outcome = np.where(
            calculated == 0, "unresolved",
            np.where(calculated == np.sign(observed.differential_mv), "correct", "wrong"),
        )
        if not np.array_equal(outcome.to_numpy(), expected_outcome):
            raise ValueError("Reported correctness differs from the signed external input")
        unresolved = outcome == "unresolved"
        if latency[unresolved].notna().any():
            raise ValueError("A deadline-unresolved observation must not have an invented latency")
        if not latency[~unresolved].between(0, deadline + 1e-10).all():
            raise ValueError("A resolved decision has missing or out-of-window latency")


def coverage_table(frame: pd.DataFrame) -> pd.DataFrame:
    validate_grid(frame)
    rows = []
    for mode, deadline in product(MODES, DEADLINES):
        part = frame[frame["mode"] == mode]
        absent = part.execution_status == "not_run"
        qualified = part.numerically_qualified
        counts = {
            "confirmed_correct": int((qualified & part[f"outcome_{deadline}ns"].eq("correct")).sum()),
            "confirmed_wrong": int((qualified & part[f"outcome_{deadline}ns"].eq("wrong")).sum()),
            "confirmed_unresolved": int((qualified & part[f"outcome_{deadline}ns"].eq("unresolved")).sum()),
            "numerical_unknown": int((~absent & ~qualified).sum()),
            "not_run": int(absent.sum()),
        }
        if sum(counts.values()) != 180:
            raise ValueError("Coverage categories do not preserve the declared 180-point denominator")
        rows.append({"mode": mode, "deadline_ns": deadline, "declared_points": 180, **counts})
    return pd.DataFrame(rows)


def summary(frame: pd.DataFrame) -> dict:
    coverage = coverage_table(frame)
    indexed = coverage.set_index(["mode", "deadline_ns"])
    rc2 = indexed.loc[("rc", 2)]
    confirmed = frame[frame.numerically_qualified]
    sc = confirmed[confirmed["mode"] == "schematic"]
    rc = confirmed[confirmed["mode"] == "rc"]
    matched = sc.merge(rc, on=list(POINT_KEY), suffixes=("_schematic", "_rc"), validate="one_to_one")
    correctly_resolved = matched[
        matched.outcome_2ns_schematic.eq("correct") & matched.outcome_2ns_rc.eq("correct")
    ]
    statistics = None
    if len(correctly_resolved):
        worst = correctly_resolved.loc[correctly_resolved.decision_time_ns_2ns_rc.idxmax()]
        statistics = {
            "scope": "full_180_matched_points" if len(correctly_resolved) == 180 else "confirmed_correct_subset",
            "points": len(correctly_resolved),
            "mean_schematic_core_energy_fj": float(correctly_resolved.core_energy_fj_schematic.mean()),
            "mean_rc_core_energy_fj": float(correctly_resolved.core_energy_fj_rc.mean()),
            "mean_per_point_energy_overhead_percent": float(
                (100 * (correctly_resolved.core_energy_fj_rc / correctly_resolved.core_energy_fj_schematic - 1)).mean()
            ),
            "observed_max_rc_delay_ns": float(worst.decision_time_ns_2ns_rc),
            "observed_worst_point": {key: worst[key].item() if isinstance(worst[key], np.generic)
                                     else worst[key] for key in POINT_KEY},
        }
    return {
        "condition_count": 45,
        "declared_points_per_mode": 180,
        "data_grid_executed": bool(frame.execution_status.eq("success").all()),
        "all_point_histories_numerically_confirmed": bool(frame.numerically_qualified.all()),
        "all_180_rc_points_correct_at_2ns": bool(rc2.confirmed_correct == 180),
        "rc_primary_correct": int(rc2.confirmed_correct),
        "rc_primary_numerical_unknown": int(rc2.numerical_unknown),
        "rc_primary_not_run": int(rc2.not_run),
        "coverage": coverage.to_dict("records"),
        "matched_statistics": statistics,
        "execution_window_conformance_assessed_by_this_table": False,
        "qualification": "Pointwise table validation only; execution amendments and provenance remain separate.",
    }


def load_results() -> dict:
    for name, expected in REFERENCE_FILES.items():
        if hashlib.sha256((DATA / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"The fixed full-grid PVT evidence changed: {name}")
    source = json.loads((DATA / "source-summary.json").read_text(encoding="utf-8"))
    audit = json.loads((DATA / "independent-audit.json").read_text(encoding="utf-8"))
    frame = pd.read_csv(DATA / "measurements.csv")
    result = summary(frame)
    flags = source["separate_result_flags"]
    if not result["data_grid_executed"] or not result["all_point_histories_numerically_confirmed"] \
            or not result["all_180_rc_points_correct_at_2ns"]:
        raise RuntimeError("The full-grid reference is incomplete or its declared 2 ns criterion is unmet")
    if flags["RC_prospective2ns_all180_pass"] is not True \
            or flags["RC_original1ns_all_pass"] is not False \
            or audit["all720_originalNPZs_remeasured_by_unchanged_published_function"] is not True \
            or audit["all360_monotone_10to5ps_histories_qualified"] is not True:
        raise RuntimeError("The independently audited result flags disagree with the plotted result")
    if audit["actual_transients"] != 720 or audit["global_charged_slots"] != 722 \
            or audit["all_actual_WL_SI_log_audits_replayed"] != 19440 \
            or audit["true_log_warning_count"] != 0 or audit["true_log_error_count"] != 0:
        raise RuntimeError("Actual execution and independent-audit counts are inconsistent")
    identity = source["identity"]
    if identity["ngspice"] != "47" or identity["Python"] != "3.12.10" or identity["NumPy"] != "2.2.6":
        raise RuntimeError("The full-grid reference tool versions changed")
    native_paths = {
        "schematic_sha256": ROOT / "results" / "study" / "selected_circuit.spice",
        "RC_netlist_sha256": ROOT / "layout_compact_repair" / "evidence" / "attempt1" / "atlas.rc.spice",
        "GDS_sha256": ROOT / "layout_compact_repair" / "evidence" / "attempt1" / "atlas.gds",
    }
    for key, path in native_paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != identity[key]:
            raise RuntimeError(f"The full-grid study no longer matches the retained physical circuit: {key}")
    previous = {("tt", 1.8, 27), ("ss", 1.62, -40), ("ss", 1.62, 125),
                ("ff", 1.95, -40), ("ff", 1.95, 125)}
    for row in frame.itertuples():
        seen = (row.corner, row.vdd_v, row.temperature_c) in previous
        if bool(row.previously_observed_postlayout) != seen or bool(row.new_postlayout_not_blinded) == seen:
            raise RuntimeError("Previously observed and new post-layout conditions were relabeled")
    if audit["original_two_window_time_conformance"] is not False \
            or audit["latest_explicit_continuation_time_conformance"] is not True:
        raise RuntimeError("The separate execution-history disclosures changed")
    if audit["max_numerical_energy_error"]["energy_error_percent"] > 1 \
            or audit["max_numerical_latency_error"]["latency_error_ns"] > 0.020:
        raise RuntimeError("The independently recorded numerical comparison exceeds the fixed limits")
    return {"frame": frame, "summary": result, "source": source, "audit": audit, "folder": DATA}


def review_examples(data: dict) -> pd.DataFrame:
    directory = DATA / "representative-traces"
    path = directory / "review-index.json"
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXAMPLE_INDEX_SHA256:
        raise RuntimeError("The fixed representative PVT trace index changed")
    index = json.loads(path.read_text(encoding="utf-8"))
    if len(index["examples"]) != 10 or len(index["artifact_sha256"]) != 60:
        raise RuntimeError("The matched representative PVT examples are incomplete")
    verify_files(directory, index["artifact_sha256"])
    rows = []
    for example in index["examples"]:
        attempt = example["attempt_id"]
        if not re.fullmatch(r"a[0-9]{4}-[0-9a-f]{24}", attempt):
            raise RuntimeError("Invalid representative attempt identity")
        run = artifact_path(directory, attempt)
        original = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
        review = json.loads((run / "collector-review.json").read_text(encoding="utf-8"))
        if hashlib.sha256((run / "metadata.json").read_bytes()).hexdigest() != review["original_metadata_sha256"]:
            raise RuntimeError("Collector acceptance is not linked to the original unmodified metadata")
        if review["status"] != "success" or review["measurements"] != original["measurements"] \
                or review["attempt_id"] != original["attempt_id"] or review["attempt_id"] != attempt:
            raise RuntimeError("Collector acceptance changed the underlying physical observation")
        if original["status"] != example["original_metadata_status"] \
                or review["run_identity"] != example["point_run_identity"]:
            raise RuntimeError("A representative run or original collector status was relabeled")
        if review.get("geometry_device_count") != 27 or review.get("reset_ok") is not True:
            raise RuntimeError("The example lacks its actual device geometry or reset qualification")
        point = Point(**review["point"])
        if point.trim_code != 0 or point.pair_skew != 0 or point.max_step_ps != 5:
            raise RuntimeError("The representative trace is outside the declared nominal experiment")
        with np.load(run / "waveform.npz", allow_pickle=False) as saved:
            values = saved["values"]
        trace = Trace(point, values, review["run_identity"], run)
        recorded = data["frame"][data["frame"].finest_attempt_id == attempt]
        if len(recorded) != 1:
            raise RuntimeError("A representative trace is missing from the complete measured grid")
        table = recorded.iloc[0]
        if table["mode"] != example["mode"] or table.run_identity != review["run_identity"] \
                or table.corner != point.corner or table.vdd_v != point.vdd_v \
                or table.temperature_c != point.temperature_c \
                or not math.isclose(table.differential_mv, point.differential_v * 1000, abs_tol=1e-12):
            raise RuntimeError("A representative waveform was associated with a different physical test point")
        for deadline in DEADLINES:
            measured = asdict(measure(trace, deadline))
            archived = next(item for item in review["measurements"] if item["deadline_ns"] == deadline)
            for key, expected in archived.items():
                actual = measured[key]
                if isinstance(expected, (float, int)) and not isinstance(expected, bool):
                    if not isinstance(actual, (float, int)) or not math.isclose(
                        actual, expected, rel_tol=1e-11, abs_tol=1e-11,
                    ):
                        raise RuntimeError(f"Remeasured example differs from its retained observation: {key}")
                elif actual != expected:
                    raise RuntimeError(f"Remeasured example differs from its retained observation: {key}")
            if measured["outcome"] != table[f"outcome_{deadline}ns"] \
                    or not math.isclose(measured["core_energy_fj"], table.core_energy_fj, rel_tol=1e-11):
                raise RuntimeError("The representative waveform disagrees with the complete comparison table")
            if measured["decision_time_ns"] is None:
                if pd.notna(table[f"decision_time_ns_{deadline}ns"]):
                    raise RuntimeError("The comparison table invents a latency for an unresolved example")
            elif not math.isclose(
                measured["decision_time_ns"], table[f"decision_time_ns_{deadline}ns"],
                rel_tol=1e-11, abs_tol=1e-11,
            ):
                raise RuntimeError("The comparison table latency differs from the representative waveform")
            rows.append({
                "condition": f"{point.corner.upper()} / {point.vdd_v:g} V / {point.temperature_c:g} C",
                "mode": example["mode"], "input_mv": point.differential_v * 1000,
                "deadline_ns": deadline, "outcome": measured["outcome"],
                "decision_time_ns": measured["decision_time_ns"],
                "core_energy_fj": measured["core_energy_fj"],
                "attempt_id": attempt,
            })
    return pd.DataFrame(rows)


def worst_case_figure(data: dict):
    import matplotlib.pyplot as plt

    from presentation.figure_style import FigureProfile, publication_style

    index_path = DATA / "representative-traces" / "review-index.json"
    if hashlib.sha256(index_path.read_bytes()).hexdigest() != EXAMPLE_INDEX_SHA256:
        raise RuntimeError("The representative PVT index changed")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    verify_files(index_path.parent, index["artifact_sha256"])
    worst = data["source"]["global_RC_worst_latency"]
    examples = [
        example for example in index["examples"]
        if example["corner"] == worst["corner"] and example["vdd_v"] == worst["vdd_v"]
        and example["temperature_c"] == worst["temperature_c"]
        and example["differential_mv"] == worst["differential_mv"]
    ]
    if {example["mode"] for example in examples} != {"schematic", "rc"} or len(examples) != 2:
        raise RuntimeError("The full-grid worst-point matched waveform pair is incomplete")
    profile = FigureProfile(height_in=2.55)
    with publication_style(profile):
        figure, ax = plt.subplots(figsize=(profile.width_in, profile.height_in))
        figure.subplots_adjust(left=0.10, right=0.975, top=0.80, bottom=0.25)
        voltage = float(worst["vdd_v"])
        for example in sorted(examples, key=lambda item: item["mode"] != "schematic"):
            path = index_path.parent / example["attempt_id"] / "waveform.npz"
            with np.load(path, allow_pickle=False) as saved:
                values = saved["values"]
            time = (values[:, 0] - EVALUATION_START_S) * 1e9
            selected = (time >= -0.10) & (time <= 2.10)
            is_rc = example["mode"] == "rc"
            color = "#0072B2" if is_rc else "#444444"
            label = "RC" if is_rc else "Schematic"
            for column, signal, style in ((2, "Q+", "-"), (3, "Q-", "--")):
                ax.plot(time[selected], values[selected, column],
                        color=color, linestyle=style, linewidth=1.25 if is_rc else 1.0,
                        label=f"{label} {signal}")
        for rail in (0.2, 0.8):
            ax.axhline(rail * voltage, color="#999999", linestyle=":", linewidth=0.65)
        for deadline in (1, 2):
            ax.axvline(deadline, color="#999999", linestyle=":", linewidth=0.65)
        ax.set(xlim=(-0.1, 2.1), ylim=(-0.05, 1.82),
               xlabel="Time from evaluation-clock midpoint (ns)", ylabel="Output voltage (V)")
        ax.set_xticks([0, 0.5, 1, 1.5, 2])
        ax.set_yticks([0, 0.4, 0.8, 1.2, 1.6])
        figure.legend(ncol=4, frameon=False, loc="upper center",
                      bbox_to_anchor=(0.54, 0.995), columnspacing=1.2, handlelength=1.8)
        figure.text(0.5, 0.02, RC_MODEL_LABEL, ha="center", va="bottom", fontsize=profile.font_pt)
    return figure


def comparison_table(frame: pd.DataFrame) -> pd.DataFrame:
    info = summary(frame)
    if not info["data_grid_executed"] or not info["all_point_histories_numerically_confirmed"]:
        raise ValueError("A full-grid comparison must not average only the finished subset")
    rows = []
    for mode in MODES:
        points = frame[frame["mode"] == mode]
        all_correct = points.outcome_2ns.eq("correct").all()
        rows.append({
            "implementation": "Schematic" if mode == "schematic" else "Extracted RC",
            "points": len(points),
            "correct_at_1ns": int(points.outcome_1ns.eq("correct").sum()),
            "correct_at_2ns": int(points.outcome_2ns.eq("correct").sum()),
            "mean_core_energy_fj": float(points.core_energy_fj.mean()),
            "mean_delay_ns_at_2ns": float(points.decision_time_ns_2ns.mean()) if all_correct else None,
            "worst_delay_ns_at_2ns": float(points.decision_time_ns_2ns.max()) if all_correct else None,
        })
    return pd.DataFrame(rows)


def paired_points(frame: pd.DataFrame) -> pd.DataFrame:
    info = summary(frame)
    if not info["data_grid_executed"] or not info["all_point_histories_numerically_confirmed"]:
        raise ValueError("Matched full-grid figures require every declared observation")
    sc = frame[frame["mode"] == "schematic"]
    rc = frame[frame["mode"] == "rc"]
    matched = sc.merge(rc, on=list(POINT_KEY), suffixes=("_schematic", "_rc"), validate="one_to_one")
    if len(matched) != 180 or not matched.outcome_2ns_schematic.eq("correct").all() \
            or not matched.outcome_2ns_rc.eq("correct").all():
        raise ValueError("This paired-delay figure requires 180 matched, 2 ns-correct points")
    return matched


def case_table(frame: pd.DataFrame) -> pd.DataFrame:
    result = summary(frame)
    if not result["data_grid_executed"] or not result["all_point_histories_numerically_confirmed"]:
        raise ValueError("A complete PVT comparison requires every declared observation and numerical history")
    rows = []
    for corner, voltage, temperature in product(CORNERS, VOLTAGES, TEMPERATURES):
        condition = frame[
            (frame.corner == corner) & (frame.vdd_v == voltage)
            & (frame.temperature_c == temperature)
        ]
        schematic = condition[condition["mode"] == "schematic"]
        rc = condition[condition["mode"] == "rc"]
        correct_2ns = rc.outcome_2ns.eq("correct")
        rows.append({
            "corner": corner,
            "vdd_v": voltage,
            "temperature_c": temperature,
            "sampled_inputs": len(rc),
            "rc_correct_1ns": int(rc.outcome_1ns.eq("correct").sum()),
            "rc_correct_2ns": int(correct_2ns.sum()),
            "max_correct_rc_delay_ns": float(rc.decision_time_ns_2ns.max()) if correct_2ns.all() else None,
            "mean_schematic_energy_fj": float(schematic.core_energy_fj.mean()),
            "mean_rc_energy_fj": float(rc.core_energy_fj.mean()),
        })
    return pd.DataFrame(rows)


def timing_figure(frame: pd.DataFrame):
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.patches import Rectangle

    from presentation.figure_style import FigureProfile, contrast_ink, publication_style

    cases = case_table(frame)
    profile = FigureProfile()
    with publication_style(profile):
        fig = plt.figure(figsize=(profile.width_in, profile.height_in))
        palette = plt.get_cmap("cividis").copy()
        palette.set_bad("#efefef")
        norm = Normalize(vmin=0, vmax=2)
        for index, corner in enumerate(CORNERS):
            ax = fig.add_axes([
                (0.50 + index * 1.20) / profile.width_in,
                0.48 / profile.height_in,
                1.04 / profile.width_in,
                1.04 / profile.height_in,
            ])
            part = cases[cases.corner == corner].set_index(["temperature_c", "vdd_v"])
            matrix = part.max_correct_rc_delay_ns.unstack().reindex(
                index=TEMPERATURES, columns=VOLTAGES,
            )
            image = ax.pcolormesh(
                np.arange(4), np.arange(4), np.ma.masked_invalid(matrix.to_numpy()),
                cmap=palette, norm=norm, edgecolors="white", linewidth=0.5,
                shading="flat", rasterized=False,
            )
            for y, temperature in enumerate(TEMPERATURES):
                for x, voltage in enumerate(VOLTAGES):
                    value = matrix.loc[temperature, voltage]
                    color = palette(norm(value)) if pd.notna(value) else (0.94, 0.94, 0.94, 1)
                    label = f"{value:.2f}" if pd.notna(value) else "FAIL"
                    annotation = ax.text(x + 0.5, y + 0.5, label, ha="center", va="center",
                                         color=contrast_ink(color), fontsize=profile.font_pt)
                    annotation.set_gid(f"pvt-value-{corner}-{y}-{x}")
                    if part.loc[(temperature, voltage), "rc_correct_1ns"] < 4:
                        marker = Rectangle(
                            (x + 0.035, y + 0.035), 0.93, 0.93,
                            facecolor="none", edgecolor="black", linewidth=0.9,
                        )
                        marker.set_gid(f"pvt-secondary-miss-{corner}-{y}-{x}")
                        ax.add_patch(marker)
            ax.set(xlim=(0, 3), ylim=(3, 0), aspect="equal")
            ax.set_title(f"({chr(ord('a') + index)}) {corner.upper()}", pad=6, fontweight="normal")
            ax.set_xticks(np.arange(3) + 0.5, ["1.62", "1.80", "1.95"])
            ax.set_yticks(np.arange(3) + 0.5, ["-40", "27", "125"] if index == 0 else ["", "", ""])
            if index == 0:
                ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)", labelpad=4)
            else:
                ax.tick_params(axis="y", left=False)
        bar_ax = fig.add_axes([
            6.52 / profile.width_in, 0.48 / profile.height_in,
            0.10 / profile.width_in, 1.04 / profile.height_in,
        ])
        colorbar = fig.colorbar(image, cax=bar_ax, ticks=[0, 0.5, 1, 1.5, 2])
        colorbar.set_label("Max. delay (ns)", labelpad=5)
        colorbar.ax.tick_params(labelsize=profile.font_pt, pad=2)
        if colorbar.solids is not None:
            colorbar.solids.set_rasterized(False)
        fig.text(3.42 / profile.width_in, 0.055 / profile.height_in,
                 "Supply voltage (V)", ha="center", va="bottom", fontsize=profile.font_pt)
        fig.text(0.5, 0.97, RC_MODEL_LABEL, ha="center", va="top", fontsize=profile.font_pt)
    return fig


def tradeoff_figure(frame: pd.DataFrame):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    from presentation.figure_style import FigureProfile, publication_style

    pairs = paired_points(frame)
    profile = FigureProfile(height_in=2.90)
    colors = ("#0072B2", "#D55E00", "#009E73", "#8A548D", "#111111")
    markers = ("o", "s", "^", "D", "v")
    with publication_style(profile):
        fig, axes = plt.subplots(1, 2, figsize=(profile.width_in, profile.height_in))
        fig.subplots_adjust(left=0.095, right=0.98, top=0.84, bottom=0.32, wspace=0.38)
        for corner, color, marker in zip(CORNERS, colors, markers):
            part = pairs[pairs.corner == corner]
            for ax, x, y in (
                (axes[0], part.decision_time_ns_2ns_schematic, part.decision_time_ns_2ns_rc),
                (axes[1], part.core_energy_fj_schematic, part.core_energy_fj_rc),
            ):
                ax.scatter(x, y, s=15, marker=marker, facecolors="none",
                           edgecolors=color, linewidths=0.7, zorder=3)
        axes[0].plot([0, 0.85], [0, 0.85], linestyle="--", color="#555555", linewidth=0.8, zorder=1)
        axes[0].axhline(2, linestyle=":", color="#777777", linewidth=0.8, zorder=1)
        axes[0].set(
            xlim=(0, 0.85), ylim=(0, 2.1),
            xlabel="Schematic delay (ns)", ylabel="RC delay (ns)",
            xticks=[0, 0.2, 0.4, 0.6, 0.8], yticks=[0, 0.5, 1, 1.5, 2],
            title="(a) Decision time",
        )
        axes[0].set_xticks([0, 0.2, 0.4, 0.6, 0.8], ["0", "0.2", "0.4", "0.6", "0.8"])
        axes[0].set_yticks([0, 0.5, 1, 1.5, 2], ["", "0.5", "1.0", "1.5", "2.0"])
        axes[1].plot([0, 400], [0, 400], linestyle="--", color="#555555", linewidth=0.8, zorder=1)
        axes[1].set(
            xlim=(0, 400), ylim=(0, 650),
            xlabel="Schematic core energy (fJ)", ylabel="RC core energy (fJ)",
            xticks=[0, 100, 200, 300, 400], yticks=[0, 200, 400, 600],
            title="(b) Full-cycle energy",
        )
        axes[1].set_yticks([0, 200, 400, 600], ["", "200", "400", "600"])
        for ax in axes:
            ax.tick_params(direction="out")
        handles = [
            Line2D([], [], marker=marker, linestyle="none", color=color,
                   markerfacecolor="none", markersize=4, markeredgewidth=0.7, label=corner.upper())
            for corner, color, marker in zip(CORNERS, colors, markers)
        ]
        handles.append(Line2D([], [], color="#555555", linestyle="--", linewidth=0.8, label="Parity"))
        fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.53, 0.02),
                   ncol=6, frameon=False, handletextpad=0.45, columnspacing=1.15)
        fig.text(0.5, 0.98, RC_MODEL_LABEL, ha="center", va="top", fontsize=profile.font_pt)
    return fig
