"""Strict post-hoc selection over existing calibrated schematic samples; no simulations."""

import argparse
from itertools import product
import json
import math

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import pandas as pd

import entry_tools as entry
from comparator_atlas.experiments import case_id
from comparator_atlas.spice import Point

DESIGNS = ("baseline", "lvt_balanced_4b", "lvt_base_3b")
MINIMUMS_MV = (0.25, 0.5, 1.0, 3.0, 10.0, 30.0)
DEADLINES_NS = (0.25, 0.35, 0.5, 0.75, 1.0, 2.0)
SCOPE = "Calibrated SCHEMATIC only: 49 controlled-width-stress conditions; not the 45-PVT RC grid"
NO_FEASIBLE = "No feasible compared design"
FOLDER = entry.STUDY / "specification_map"
EXAMPLES = ((1.0, 1.0), (3.0, 1.0), (30.0, 1.0), (10.0, 2.0), (10.0, 0.75), (30.0, 0.5))
OUTCOMES = ("correct", "wrong", "unresolved")
SAMPLE_KEY = ["design_name", "case_id", "input_mv"]
LOCATION = ["corner", "vdd_v", "temperature_c", "pair_skew", "trim_code"]
OBSERVATION = [
    *SAMPLE_KEY, *LOCATION, "deadline_ns", "run_id", "outcome",
    "decision_time_ns", "core_energy_fj",
]
SOURCES = (
    "entry_tools.py", "presentation/specification_map.py",
    "results/study/protocol.json", "results/study/selection.json",
    "results/study/optimization_manifest.json", "results/study/validation_manifest.json",
    "results/study/stress_manifest.json", "results/study/verified_measurements.csv",
    "results/study/professional/manifest.json", "results/study/professional/measurements.csv",
)


def validate_grid(evidence: dict) -> None:
    protocol = json.loads((entry.STUDY / "protocol.json").read_bytes())
    cases = [case_id(Point(**point)) for point in protocol["validation_cases"]]
    inputs = sorted(protocol["validation_inputs_mv"])
    if len(cases) != 49 or len(set(cases)) != 49 \
            or inputs != sorted([0.0, *MINIMUMS_MV, *(-value for value in MINIMUMS_MV)]) \
            or tuple(protocol["validation_deadlines_ns"]) != DEADLINES_NS:
        raise ValueError("The declared schematic grid is not the original 49-condition study")
    frame = evidence["frame"]
    part = frame[frame.policy.eq("local_boundary")]
    key = ["design_name", "case_id", "input_mv", "deadline_ns"]
    expected = pd.MultiIndex.from_tuples(list(product(DESIGNS, cases, inputs, DEADLINES_NS)))
    actual = pd.MultiIndex.from_frame(part[key])
    if actual.has_duplicates or len(actual) != len(expected) \
            or len(expected.difference(actual)) or len(actual.difference(expected)):
        raise ValueError("Missing, duplicate or unexpected calibrated schematic observations")
    if not part.policy_available.eq(True).all() or not part.reset_ok.eq(True).all():
        raise ValueError("Unavailable calibration or invalid reset cannot qualify")
    numeric = part[["input_mv", "deadline_ns", "core_energy_fj"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or (part.core_energy_fj < 0).any() \
            or part.run_id.isna().any() or part.run_id.eq("").any():
        raise ValueError("Nonfinite inputs/energy or missing execution identity cannot qualify")
    nonzero = part[part.input_mv.ne(0)]
    if not nonzero.outcome.isin(OUTCOMES).all():
        raise ValueError("Unrecognized nonzero-input outcome")
    locations = {case_id(Point(**point)): point for point in protocol["validation_cases"]}
    for field in ("corner", "vdd_v", "temperature_c", "pair_skew"):
        expected_values = part.case_id.map(lambda name: locations[name][field])
        if not part[field].eq(expected_values).all():
            raise ValueError(f"Sample location differs from protocol: {field}")
    if not np.isfinite(part.trim_code.to_numpy(dtype=float)).all() \
            or not part.trim_code.mod(1).eq(0).all() \
            or part.groupby(["design_name", "case_id"]).trim_code.nunique().ne(1).any():
        raise ValueError("Missing or inconsistent local calibration code")
    resolved = nonzero[nonzero.outcome.ne("unresolved")]
    times = resolved.decision_time_ns
    # Seconds-to-nanoseconds conversion leaves a few ULPs at exact deadline endpoints.
    beyond = times.gt(resolved.deadline_ns) & ~np.isclose(
        times, resolved.deadline_ns, rtol=0, atol=4e-15)
    if not np.isfinite(times.to_numpy(dtype=float)).all() \
            or times.lt(0).any() or beyond.any():
        raise ValueError("Resolved observations require finite decision times within deadline")
    if nonzero.loc[nonzero.outcome.eq("unresolved"), "decision_time_ns"].notna().any():
        raise ValueError("Unresolved observations must retain unavailable decision time")


def sampled_limits(part: pd.DataFrame) -> dict | None:
    if part.empty:
        raise ValueError("Cannot compute limits for an empty scoring band")
    if not part.outcome.eq("correct").all():
        return None
    margins = (part.deadline_ns - part.decision_time_ns) * 1000
    if not np.isfinite(margins.to_numpy(dtype=float)).all() \
            or not np.isfinite(part.core_energy_fj.to_numpy(dtype=float)).all() \
            or margins.lt(-4e-12).any():
        raise ValueError("Nonfinite or negative sampled margin/energy observation")
    minimum, maximum = float(margins.min()), float(part.core_energy_fj.max())
    return {
        "minimum_decision_margin_ps": minimum,
        "maximum_core_energy_fj": maximum,
        "timing_limiting_samples": part.loc[margins.eq(minimum), OBSERVATION].sort_values(
            SAMPLE_KEY).to_dict("records"),
        "energy_limiting_samples": part.loc[part.core_energy_fj.eq(maximum), OBSERVATION].sort_values(
            SAMPLE_KEY).to_dict("records"),
    }


def matched_transitions(part: pd.DataFrame) -> pd.DataFrame:
    endpoints = []
    for deadline in (1.0, 2.0):
        endpoint = part[part.deadline_ns.eq(deadline)][OBSERVATION]
        if endpoint.empty or endpoint.duplicated(SAMPLE_KEY).any():
            raise ValueError("Missing or duplicate transition endpoint")
        endpoints.append(endpoint)
    joined = endpoints[0].merge(
        endpoints[1], on=SAMPLE_KEY, how="outer", validate="one_to_one",
        suffixes=("_1ns", "_2ns"), indicator=True,
    )
    if not joined["_merge"].eq("both").all():
        raise ValueError("Unmatched 1 ns / 2 ns sample keys")
    for field in LOCATION:
        if not joined[f"{field}_1ns"].eq(joined[f"{field}_2ns"]).all():
            raise ValueError(f"Transition endpoints disagree on sample metadata: {field}")
        joined[field] = joined.pop(f"{field}_1ns")
        joined.pop(f"{field}_2ns")
    return joined.drop(columns="_merge").sort_values(SAMPLE_KEY).reset_index(drop=True)


def failure_analysis(evidence: dict) -> dict:
    validate_grid(evidence)
    frame = evidence["frame"]
    part = frame[frame.policy.eq("local_boundary") & frame.input_mv.ne(0)]
    dimensions = {
        "design_deadline": ["design_name", "deadline_ns"],
        "signed_input": ["design_name", "deadline_ns", "input_mv"],
        **{name: ["design_name", "deadline_ns", name]
           for name in ("corner", "vdd_v", "temperature_c", "pair_skew", "case_id")},
    }
    groups = {}
    for name, keys in dimensions.items():
        counts = part.groupby(keys + ["outcome"], sort=True).size().unstack(
            "outcome", fill_value=0).reindex(columns=OUTCOMES, fill_value=0)
        counts["points"] = counts.sum(axis=1)
        groups[name] = counts.reset_index().to_dict("records")
    transitions = matched_transitions(part[part.input_mv.abs().ge(1)])
    matrix = []
    for design in DESIGNS:
        rows = transitions[transitions.design_name.eq(design)]
        for before, after in product(OUTCOMES, repeat=2):
            matrix.append({
                "design": design, "outcome_1ns": before, "outcome_2ns": after,
                "points": int((rows.outcome_1ns.eq(before) & rows.outcome_2ns.eq(after)).sum()),
            })
    selected = transitions[transitions.design_name.eq("lvt_balanced_4b")]
    first = set(map(tuple, selected.loc[selected.outcome_1ns.eq("wrong"), SAMPLE_KEY].values))
    second = set(map(tuple, selected.loc[selected.outcome_2ns.eq("wrong"), SAMPLE_KEY].values))
    wrong = selected[selected.outcome_1ns.eq("wrong") | selected.outcome_2ns.eq("wrong")]

    def records(rows):
        return rows.astype(object).where(pd.notna(rows), None).to_dict("records")

    return {
        "grouped_scope": "All 12 signed nonzero inputs (0.25 through 30 mV), all six deadlines",
        "transition_scope": "Matched sample keys at 1 ns and 2 ns, |input| >= 1 mV",
        "sample_key": SAMPLE_KEY, "ordering": "Lexicographic group/sample keys; declared outcome/design order for matrix",
        "grouped_counts": groups, "matched_samples": records(transitions),
        "transition_matrix": matrix,
        "selected_wrong": {
            "count_1ns": len(first), "count_2ns": len(second),
            "same_sample_set": first == second, "samples": records(wrong),
        },
        "limits": "Outcome classes need not be monotonic. Locations/codes do not establish a physical failure cause.",
    }


def choose(rows: list[dict]) -> dict:
    if len(rows) != 3 or {row["design"] for row in rows} != set(DESIGNS):
        raise ValueError("Selection requires exactly the three compared designs")
    if any(not math.isfinite(row["mean_core_energy_fj"]) for row in rows):
        raise ValueError("Nonfinite mean core energy cannot rank designs")
    feasible = [row for row in rows if row["all_correct"]]
    if not feasible:
        return {
            "status": NO_FEASIBLE, "winner": None, "mean_core_energy_fj": None,
            "qualifying_designs": [], "minimum_energy_ties": [],
        }
    minimum = min(row["mean_core_energy_fj"] for row in feasible)
    ties = [name for name in DESIGNS if any(
        row["design"] == name and row["mean_core_energy_fj"] == minimum for row in feasible
    )]
    return {
        "status": "All sampled points correct", "winner": ties[0],
        "mean_core_energy_fj": minimum,
        "qualifying_designs": [name for name in DESIGNS if any(row["design"] == name for row in feasible)],
        "minimum_energy_ties": ties,
    }


def analyze(evidence: dict) -> dict:
    validate_grid(evidence)
    design_rows, specifications = [], []
    for minimum, deadline in product(MINIMUMS_MV, DEADLINES_NS):
        table = entry.summary(evidence, minimum, deadline)
        rows = []
        points = 49 * 2 * sum(value >= minimum for value in MINIMUMS_MV)
        for design in DESIGNS:
            values = table.loc[design]
            if values.points != points or values.conditions != 49 or values.simulated_points != points:
                raise ValueError("Scoring-band coverage differs from the declared grid")
            part = evidence["frame"]
            part = part[part.policy.eq("local_boundary") & part.design_name.eq(design)
                        & part.deadline_ns.eq(deadline) & part.input_mv.abs().ge(minimum)]
            rows.append({
                "minimum_abs_input_mv": minimum, "deadline_ns": deadline, "design": design,
                "correct": int(values.correct), "points": points,
                "fully_passing_conditions": int(values.fully_passing_conditions),
                "conditions": 49, "simulated_points": int(values.simulated_points),
                "mean_core_energy_fj": float(values.mean_core_energy_fj),
                "all_correct": bool(values.correct == points and values.fully_passing_conditions == 49),
                "sampled_limits": sampled_limits(part),
            })
        design_rows.extend(rows)
        choice = choose(rows)
        specifications.append({
            "minimum_abs_input_mv": minimum, "deadline_ns": deadline, **choice,
            "sampled_limits": next(
                (row["sampled_limits"] for row in rows if row["design"] == choice["winner"]), None),
        })
    return {
        "schema": 2, "scope": SCOPE, "policy": "local_boundary",
        "analysis": "descriptive_posthoc_existing_data", "new_physical_simulations": 0,
        "minimum_abs_input_mv": list(MINIMUMS_MV), "deadlines_ns": list(DEADLINES_NS),
        "compared_designs": list(DESIGNS), "conditions": 49,
        "qualification": "Every included nonzero signed input at every condition must be correct",
        "objective": "Minimum measured mean full-cycle core energy over the included sampled band",
        "tie_rule": "Exact equal means: report all tied minima, select first in compared_designs order",
        "sampled_limits_contract": (
            "Qualified designs/winners only: minimum (deadline - recorded decision_time_ns) * 1000 ps; "
            "maximum observed full-cycle core energy. All exact equal limiting values retain every "
            "sample in lexicographic key order. Unqualified/NONE limits are null. "
            "Finite observations, not timing signoff, noise/jitter bounds or worst-cycle/system energy guarantees."
        ),
        "limits": [
            "No interpolation or continuous-input, yield or silicon guarantee.",
            "Not a worst-cycle energy bound; excludes drivers and calibration/system energy.",
            "The lower-energy control and this specification analysis are post-selection.",
            "No change to calibration, original training selection or recorded outcomes.",
            "No energy budget is imposed; no feasible design is never replaced by a best-average fallback.",
            "Baseline is never chosen only within this compared calibrated sampled domain.",
        ],
        "source_sha256": {name: entry.digest(entry.ROOT / name) for name in SOURCES},
        "per_design": design_rows, "per_specification": specifications,
        "failure_analysis": failure_analysis(evidence),
    }


def figure(result: dict):
    codes = {None: 0, "lvt_balanced_4b": 1, "lvt_base_3b": 2, "baseline": 3}
    symbols = {None: "NONE", "lvt_balanced_4b": "SEL", "lvt_base_3b": "CTL", "baseline": "BASE"}
    rows = {(row["minimum_abs_input_mv"], row["deadline_ns"]): row for row in result["per_specification"]}
    values = [[codes[rows[(minimum, deadline)]["winner"]]
               for minimum in MINIMUMS_MV] for deadline in DEADLINES_NS]
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    ax.imshow(values, cmap=ListedColormap(["#edf0f4", "#b7e2df", "#f7dfaf", "#c8ced8"]),
              vmin=0, vmax=3, aspect="auto")
    for y, deadline in enumerate(DEADLINES_NS):
        for x, minimum in enumerate(MINIMUMS_MV):
            row = rows[(minimum, deadline)]
            label = symbols[row["winner"]]
            if row["winner"] is not None:
                label += f"\n{row['mean_core_energy_fj']:.2f} fJ"
            ax.text(x, y, label, ha="center", va="center", fontsize=10)
    ax.set_xticks(range(6), [f"{value:g}" for value in MINIMUMS_MV])
    ax.set_yticks(range(6), [f"{value:g}" for value in DEADLINES_NS])
    ax.set(xlabel="Minimum |sampled input| (mV); both signs, up to 30 mV",
           ylabel="Recorded decision deadline (ns)",
           title="Strict all-point qualification, then least mean full-cycle core energy\n"
                 "Calibrated SCHEMATIC: all 49 controlled-width-stress conditions (not RC)")
    fig.text(0.5, 0.055,
             "NONE = No feasible compared design | SEL = lvt_balanced_4b | CTL = lvt_base_3b\n"
             "BASE = baseline (no winning cell here). Post-hoc recorded samples only; zero new SPICE.\n"
             "Mean core energy is not a worst-cycle/system budget. No continuous-input guarantee.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    return fig


def example_table(result: dict) -> pd.DataFrame:
    rows = {(row["minimum_abs_input_mv"], row["deadline_ns"]): row for row in result["per_specification"]}
    return pd.DataFrame([{
        "min_abs_input_mV": minimum, "deadline_ns": deadline,
        "choice": rows[(minimum, deadline)]["winner"] or NO_FEASIBLE,
        "mean_core_energy_fJ": rows[(minimum, deadline)]["mean_core_energy_fj"],
        "min_sampled_margin_ps": (
            rows[(minimum, deadline)]["sampled_limits"]["minimum_decision_margin_ps"]
            if rows[(minimum, deadline)]["sampled_limits"] is not None else None),
        "max_sampled_core_energy_fJ": (
            rows[(minimum, deadline)]["sampled_limits"]["maximum_core_energy_fj"]
            if rows[(minimum, deadline)]["sampled_limits"] is not None else None),
    } for minimum, deadline in EXAMPLES])


def failure_table(result: dict) -> pd.DataFrame:
    matched = pd.DataFrame(result["failure_analysis"]["matched_samples"])
    return pd.DataFrame([{
        "design": design, "deadline_ns": deadline, **{
            outcome: int((matched.design_name.eq(design)
                          & matched[f"outcome_{deadline}ns"].eq(outcome)).sum())
            for outcome in OUTCOMES
        },
    } for design, deadline in product(DESIGNS, (1, 2))])


def selected_wrong_table(result: dict) -> pd.DataFrame:
    rows = result["failure_analysis"]["selected_wrong"]["samples"]
    return pd.DataFrame(rows, columns=[
        "case_id", "input_mv", "trim_code", "outcome_1ns", "outcome_2ns",
    ])


def failure_figure(result: dict):
    rows = result["failure_analysis"]["transition_matrix"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.8), sharey=True)
    for ax, design in zip(axes, DESIGNS):
        values = np.array([row["points"] for row in rows if row["design"] == design]).reshape(3, 3)
        ax.imshow(values, cmap="Blues", vmin=0, vmax=392)
        for y, x in product(range(3), repeat=2):
            ax.text(x, y, str(values[y, x]), ha="center", va="center",
                    color="white" if values[y, x] > 196 else "black")
        ax.set_xticks(range(3), OUTCOMES, rotation=20)
        ax.set_yticks(range(3), OUTCOMES)
        ax.set(title=design, xlabel="Outcome at 2 ns")
    axes[0].set_ylabel("Outcome at 1 ns")
    fig.suptitle("Matched schematic samples: 392 per design, |input| >= 1 mV\n"
                 "Local calibration, all 49 controlled-width-stress conditions")
    fig.text(0.5, 0.025, "Paired by design/case/signed input, not subtracted totals.\n"
             "Longer deadlines do not imply monotonic outcome classes.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.16, 1, 0.91))
    return fig


def write_artifacts(evidence: dict) -> dict:
    result = analyze(evidence)
    FOLDER.mkdir(parents=True, exist_ok=True)
    plot = figure(result)
    plot.savefig(FOLDER / "selection_map.png", dpi=150)
    plt.close(plot)
    result["figure_sha256"] = entry.digest(FOLDER / "selection_map.png")
    plot = failure_figure(result)
    plot.savefig(FOLDER / "failure_transitions.png", dpi=150)
    plt.close(plot)
    result["failure_figure_sha256"] = entry.digest(FOLDER / "failure_transitions.png")
    (FOLDER / "summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    return result


def load_checked(evidence: dict) -> dict:
    saved = json.loads((FOLDER / "summary.json").read_bytes())
    figure_hash = saved.pop("figure_sha256")
    failure_hash = saved.pop("failure_figure_sha256")
    if saved != analyze(evidence) or figure_hash != entry.digest(FOLDER / "selection_map.png") \
            or failure_hash != entry.digest(FOLDER / "failure_transitions.png"):
        raise RuntimeError("Saved specification map differs from the verified schematic evidence")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate only the derived JSON and figure")
    args = parser.parse_args()
    try:
        evidence = entry.load_evidence()
        result = write_artifacts(evidence) if args.write else load_checked(evidence)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        parser.exit(1, f"Specification map FAILED: {error}\n")
    print(SCOPE)
    print(example_table(result).to_string(index=False))
    print("108 per-design rows; 36 specification cells; zero new simulations.")


if __name__ == "__main__":
    main()
