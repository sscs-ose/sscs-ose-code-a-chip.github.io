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
    if not nonzero.outcome.isin(("correct", "wrong", "unresolved")).all():
        raise ValueError("Unrecognized nonzero-input outcome")


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
            rows.append({
                "minimum_abs_input_mv": minimum, "deadline_ns": deadline, "design": design,
                "correct": int(values.correct), "points": points,
                "fully_passing_conditions": int(values.fully_passing_conditions),
                "conditions": 49, "simulated_points": int(values.simulated_points),
                "mean_core_energy_fj": float(values.mean_core_energy_fj),
                "all_correct": bool(values.correct == points and values.fully_passing_conditions == 49),
            })
        design_rows.extend(rows)
        specifications.append({
            "minimum_abs_input_mv": minimum, "deadline_ns": deadline, **choose(rows),
        })
    return {
        "schema": 1, "scope": SCOPE, "policy": "local_boundary",
        "analysis": "descriptive_posthoc_existing_data", "new_physical_simulations": 0,
        "minimum_abs_input_mv": list(MINIMUMS_MV), "deadlines_ns": list(DEADLINES_NS),
        "compared_designs": list(DESIGNS), "conditions": 49,
        "qualification": "Every included nonzero signed input at every condition must be correct",
        "objective": "Minimum measured mean full-cycle core energy over the included sampled band",
        "tie_rule": "Exact equal means: report all tied minima, select first in compared_designs order",
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
    } for minimum, deadline in EXAMPLES])


def write_artifacts(evidence: dict) -> dict:
    result = analyze(evidence)
    FOLDER.mkdir(parents=True, exist_ok=True)
    plot = figure(result)
    plot.savefig(FOLDER / "selection_map.png", dpi=150)
    plt.close(plot)
    result["figure_sha256"] = entry.digest(FOLDER / "selection_map.png")
    (FOLDER / "summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    return result


def load_checked(evidence: dict) -> dict:
    saved = json.loads((FOLDER / "summary.json").read_bytes())
    figure_hash = saved.pop("figure_sha256")
    if saved != analyze(evidence) or figure_hash != entry.digest(FOLDER / "selection_map.png"):
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
