"""Numerical refinement and explicitly out-of-selection operating stresses."""

from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .spice import (
    EVALUATION_START_S, Point, ROOT, SimulationError, Simulator, Trace, measure, sha256, write_json,
)
from .study import CACHE, STUDY, Evidence, _receipt, checked_manifest, load_validation

EXTREMES = (
    ("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("ss", 1.62, 125.0),
    ("ff", 1.95, -40.0), ("ff", 1.95, 125.0),
)
STRESS_NAMES = (
    "ideal_reference", "opposite_input_history", "source_1k_20f", "source_5k_20f",
    "settling_10k_200f", "common_mode_0p45", "common_mode_0p60", "output_load_20f",
)
REPORTING_DEADLINES = (0.25, 0.35, 0.5, 0.75, 1.0, 2.0)
REFINEMENT_STEPS_PS = (2.5, 1.25, 0.625, 0.3125, 0.15625)


def stressed_point(base: Point, name: str, differential_v: float) -> Point:
    point = replace(base, differential_v=differential_v)
    previous = -0.03 if differential_v > 0 else 0.03
    if name == "ideal_reference":
        return point
    if name == "opposite_input_history":
        return replace(point, previous_differential_v=previous)
    if name == "source_1k_20f":
        return replace(point, source_resistance_ohm=1000, sample_cap_ff=20)
    if name == "source_5k_20f":
        return replace(point, source_resistance_ohm=5000, sample_cap_ff=20)
    if name == "settling_10k_200f":
        return replace(point, source_resistance_ohm=10000, sample_cap_ff=200,
                       previous_differential_v=previous)
    if name == "common_mode_0p45":
        return replace(point, common_mode_ratio=0.45)
    if name == "common_mode_0p60":
        return replace(point, common_mode_ratio=0.60)
    if name == "output_load_20f":
        return replace(point, load_ff=20)
    raise ValueError(f"Unknown operating stress: {name}")


def input_disturbance(trace: Trace) -> dict[str, float]:
    values = trace.values
    if values.shape[1] != 9:
        raise SimulationError("Input-disturbance analysis requires actual input-pin voltage traces")
    mask = (values[:, 0] >= EVALUATION_START_S) & (values[:, 0] <= EVALUATION_START_S + 3.5e-9)
    if not mask.any():
        raise SimulationError("Input-disturbance measurement has no evaluation samples")
    plus, minus = values[mask, 7], values[mask, 8]
    return {
        "max_differential_input_error_mv": float(1000 * np.max(np.abs(
            plus - minus - trace.point.differential_v,
        ))),
        "max_common_mode_input_error_mv": float(1000 * np.max(np.abs(
            (plus + minus) / 2 - trace.point.common_mode_ratio * trace.point.vdd_v,
        ))),
    }


def numerical_points(frame: pd.DataFrame, reports: list[dict], selected_name: str) -> list[Point]:
    selected = set()
    lookup = {(report["design_name"], report["case_id"]): report for report in reports}
    for report in reports:
        point = Point(**report["point"])
        include = point.design_name == selected_name or (
            point.pair_skew == 0.04 and (point.corner, point.vdd_v, point.temperature_c) in EXTREMES
        )
        if include:
            for policy in ("local_boundary", "deadline_aware"):
                code = report["codes"][policy]
                if code is not None:
                    selected.update(replace(point, trim_code=code, differential_v=value)
                                    for value in (-0.001, 0.001))
    scored = frame[frame.policy_available & (frame.input_mv != 0)].copy()
    positive_margin = np.minimum(scored.qp_at_deadline_v - 0.8 * scored.vdd_v,
                                 0.2 * scored.vdd_v - scored.qn_at_deadline_v)
    negative_margin = np.minimum(scored.qn_at_deadline_v - 0.8 * scored.vdd_v,
                                 0.2 * scored.vdd_v - scored.qp_at_deadline_v)
    near = scored[np.maximum(positive_margin, negative_margin).abs() <= 0.005]
    for row in near.itertuples():
        point = Point(**lookup[(row.design_name, row.case_id)]["point"])
        selected.add(replace(point, differential_v=row.input_mv / 1000, trim_code=int(row.trim_code)))
    return sorted(selected, key=lambda point: (
        point.design_name, point.corner, point.vdd_v, point.temperature_c,
        point.pair_skew, point.trim_code, point.differential_v,
    ))


def compare_resolution(coarse: Trace, fine: Trace) -> list[dict]:
    rows = []
    for deadline in REPORTING_DEADLINES:
        first, second = measure(coarse, deadline), measure(fine, deadline)
        if second.core_energy_fj <= 0:
            raise SimulationError("Fine-step reference energy must be positive")
        energy_error = 100 * abs(first.core_energy_fj - second.core_energy_fj) / second.core_energy_fj
        delay_error = None
        if first.decision_time_ns is not None and second.decision_time_ns is not None:
            delay_error = abs(first.decision_time_ns - second.decision_time_ns)
        passed = first.outcome == second.outcome and first.decision == second.decision \
            and energy_error <= 1.0 and (delay_error is None or delay_error <= 0.02)
        rows.append({
            **asdict(coarse.point), "deadline_ns": deadline,
            "coarse_max_step_ps": coarse.point.max_step_ps,
            "fine_max_step_ps": fine.point.max_step_ps,
            "coarse_run_id": coarse.run_id, "fine_run_id": fine.run_id,
            "coarse_outcome": first.outcome, "fine_outcome": second.outcome,
            "energy_difference_percent": energy_error, "latency_difference_ns": delay_error,
            "passed": passed,
        })
    return rows


def apply_refinements(frame: pd.DataFrame, updates: pd.DataFrame) -> pd.DataFrame:
    corrected = frame.copy()
    corrected["initial_run_id"] = corrected.run_id
    corrected["numerically_refined"] = False
    if updates.empty:
        return corrected
    if updates.duplicated(["original_run_id", "deadline_ns"]).any():
        raise SimulationError("Duplicate numerical corrections would overwrite the same measurement")
    fields = (
        "run_id", "max_step_ps", "decision", "outcome", "decision_time_ns", "core_energy_fj",
        "reset_ok", "qp_at_deadline_v", "qn_at_deadline_v",
    )
    for update in updates.to_dict("records"):
        mask = (corrected.initial_run_id == update["original_run_id"]) \
            & (corrected.deadline_ns == update["deadline_ns"])
        if not mask.any():
            raise SimulationError("A numerical correction has no matching original validation point")
        for field in ("design_name", "corner", "vdd_v", "temperature_c", "pair_skew",
                      "trim_code", "differential_v", "common_mode_ratio", "load_ff"):
            if not (corrected.loc[mask, field] == update[field]).all():
                raise SimulationError(f"A numerical correction changed the physical experiment: {field}")
        if not 0 < update["max_step_ps"] < corrected.loc[mask, "max_step_ps"].min():
            raise SimulationError("Numerical correction must use a strictly finer timestep")
        for field in fields:
            corrected.loc[mask, field] = update[field]
        corrected.loc[mask, "numerically_refined"] = True
    return corrected


def run_stress() -> Path:
    frame, reports, validation = load_validation()
    selection = json.loads((STUDY / "selection.json").read_text())
    selected_name = selection["selected_design"]
    write_json(STUDY / "stress_manifest.json", {"status": "running"})
    evidence = Evidence(Simulator(CACHE))
    reference_points = numerical_points(frame, reports, selected_name)
    fine_points = [replace(point, max_step_ps=5.0) for point in reference_points]
    traces = evidence.sim.run_many(reference_points + fine_points)
    indexed = {trace.point: trace for trace in traces}
    initial = []
    by_reference: dict[Point, list[dict]] = {}
    accepted: dict[Point, Trace] = {}
    for trace in traces:
        evidence.observe(trace)
    for point, fine_point in zip(reference_points, fine_points):
        coarse, fine = indexed[point], indexed[fine_point]
        checks = compare_resolution(coarse, fine)
        initial.extend(checks)
        by_reference[point] = checks
    pd.DataFrame(initial).to_csv(STUDY / "initial_numerical_checks.csv", index=False)
    pending = {
        point: indexed[replace(point, max_step_ps=5.0)]
        for point, checks in by_reference.items() if not all(row["passed"] for row in checks)
    }
    initially_sensitive = len(pending)
    streak = {point: 0 for point in pending}
    refinement_history = []
    for step in REFINEMENT_STEPS_PS:
        if not pending:
            break
        current_points = list(pending)
        refined = evidence.sim.run_many([replace(point, max_step_ps=step) for point in current_points])
        for point, fine in zip(current_points, refined):
            evidence.observe(fine)
            checks = compare_resolution(pending[point], fine)
            refinement_history.extend(checks)
            by_reference[point] = checks
            stable = all(row["passed"] for row in checks)
            streak[point] = streak[point] + 1 if stable else 0
            pending[point] = fine
            # Require two consecutive passing halvings and at least a 0.625 ps endpoint.
            if streak[point] >= 2 and step <= 0.625:
                accepted[point] = fine
                del pending[point]
        print(f"Sensitive-point refinement at {step:g} ps: {len(accepted)}/{initially_sensitive} stable", flush=True)
    numerical = [row for point in reference_points for row in by_reference[point]]
    pd.DataFrame(numerical).to_csv(STUDY / "numerical_checks.csv", index=False)
    pd.DataFrame(refinement_history, columns=pd.DataFrame(initial).columns).to_csv(
        STUDY / "refinement_history.csv", index=False,
    )
    updates = []
    for point, trace in accepted.items():
        for deadline in REPORTING_DEADLINES:
            updates.append({
                **asdict(trace.point), **asdict(measure(trace, deadline)),
                "original_run_id": indexed[point].run_id, "run_id": trace.run_id,
            })
    update_columns = [*asdict(Point()), *asdict(measure(traces[0], 1.0)), "original_run_id", "run_id"]
    corrections = pd.DataFrame(updates, columns=list(dict.fromkeys(update_columns)))
    corrections.to_csv(STUDY / "measurement_refinements.csv", index=False)
    verified = apply_refinements(frame, corrections)
    verified.to_csv(STUDY / "verified_measurements.csv", index=False)
    print(
        f"Initial numerical checks: {sum(row['passed'] for row in initial)}/{len(initial)}; "
        f"after explicit refinement: {sum(row['passed'] for row in numerical)}/{len(numerical)}; "
        f"{len(accepted)} physical points corrected", flush=True,
    )

    operating = []
    for report in reports:
        base = Point(**report["point"])
        if base.pair_skew != 0.04 or (base.corner, base.vdd_v, base.temperature_c) not in EXTREMES:
            continue
        code = report["codes"]["local_boundary"]
        for name in STRESS_NAMES:
            if code is None:
                raise SimulationError("Operating-stress reference calibration is unavailable")
            points = [
                stressed_point(replace(base, trim_code=code), name, value / 1000)
                for value in (-3, -1, 1, 3)
            ]
            for trace in evidence.sim.run_many(points):
                evidence.observe(trace)
                disturbance = input_disturbance(trace)
                for deadline in (1.0, 2.0):
                    operating.append({
                        **asdict(trace.point), "case_id": report["case_id"],
                        "stress": name, "input_mv": 1000 * trace.point.differential_v,
                        "calibration_policy": "fixed local code from ideal inputs and 0.5*VDD common mode",
                        **asdict(measure(trace, deadline)), **disturbance, "run_id": trace.run_id,
                    })
        print(f"Operating stress: {base.design_name} / {report['case_id']}", flush=True)
    pd.DataFrame(operating).to_csv(STUDY / "operating_stress.csv", index=False)
    manifest = _receipt(evidence, (
        "initial_numerical_checks.csv", "numerical_checks.csv", "refinement_history.csv",
        "measurement_refinements.csv", "verified_measurements.csv", "operating_stress.csv",
    ))
    manifest.update({
        "stress_source_sha256": sha256(Path(__file__)),
        "validation_measurements_sha256": validation["artifact_sha256"]["validation_measurements.csv"],
        "numerical_passed": not pending and all(row["passed"] for row in numerical),
        "numerical_checks": len(numerical), "numerical_reference_points": len(reference_points),
        "numerical_failures": sum(not row["passed"] for row in numerical),
        "initial_numerical_failures": sum(not row["passed"] for row in initial),
        "initially_sensitive_physical_points": initially_sensitive,
        "refined_physical_points": len(accepted),
        "refined_validation_rows": int(verified.numerically_refined.sum()),
        "refinement_history_rows": len(refinement_history),
        "refinement_policy": (
            "Keep original 10-to-5 ps failures. For affected physical points, halve the timestep "
            "through 2.5, 1.25, 0.625, 0.3125 and 0.15625 ps as needed. Require two consecutive "
            "passing comparisons with the unchanged outcome/energy/latency limits and an endpoint "
            "no larger than 0.625 ps. Publish the finest accepted waveform for every matching "
            "policy/deadline row, without changing circuit, code, stimulus, deadline or selection."
        ),
        "numerical_limits": {"energy_difference_percent": 1.0, "resolved_latency_difference_ns": 0.02},
        "numerical_scope": (
            "Selected design at all 49 conditions for +/-1 mV and both local policies; baseline "
            "at five extreme/nominal conditions; additionally every validation run with an output "
            "decision margin within 5 mV of a rail threshold. All six reporting deadlines are checked. "
            "Initially sensitive points are subsequently refined under the recorded halving policy."
        ),
        "operating_rows": len(operating), "operating_profiles": list(STRESS_NAMES),
        "operating_scope": (
            "Five conditions per design, four differential inputs, eight declared stresses, two deadlines. "
            "Calibration is frozen before changing source loading, input history, common mode or output load."
        ),
        "input_error_definition": (
            "Peak departure of actual input-pin differential/common-mode voltage from requested voltage "
            "during evaluation. Includes deterministic settling and kickback; not random input noise."
        ),
    })
    write_json(STUDY / "stress_manifest.json", manifest)
    if not manifest["numerical_passed"]:
        raise RuntimeError("Numerical refinement exceeded declared limits; preserve and inspect failed rows")
    return STUDY


def load_stress() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    manifest = checked_manifest("stress_manifest.json")
    if manifest["stress_source_sha256"] != sha256(Path(__file__)):
        raise SimulationError("Stress-analysis code changed; regenerate its results")
    validation = checked_manifest("validation_manifest.json")
    if manifest["validation_measurements_sha256"] != validation["artifact_sha256"]["validation_measurements.csv"]:
        raise SimulationError("Stress evidence is based on different validation measurements")
    numerical = pd.read_csv(STUDY / "numerical_checks.csv")
    operating = pd.read_csv(STUDY / "operating_stress.csv")
    if len(numerical) != manifest["numerical_checks"] or len(operating) != manifest["operating_rows"]:
        raise SimulationError("Stress evidence does not match its declared output counts")
    return numerical, operating, manifest


def load_verified_validation() -> tuple[pd.DataFrame, list[dict], dict]:
    original, reports, manifest = load_validation()
    _, _, stress = load_stress()
    if not stress["numerical_passed"]:
        raise SimulationError("Numerically sensitive validation points remain unresolved")
    verified = pd.read_csv(STUDY / "verified_measurements.csv")
    updates = pd.read_csv(STUDY / "measurement_refinements.csv")
    expected = apply_refinements(original, updates)
    if len(verified) != len(original) or int(verified.numerically_refined.sum()) != stress["refined_validation_rows"]:
        raise SimulationError("Refined validation does not preserve the declared grid")
    identity_columns = ["design_name", "case_id", "policy", "input_mv", "deadline_ns", "run_id", "outcome"]
    if not verified[identity_columns].equals(expected[identity_columns]):
        raise SimulationError("Published refined measurements disagree with their explicit corrections")
    return verified, reports, {
        **manifest, "reported_measurements": "verified_measurements.csv",
        "refined_validation_rows": stress["refined_validation_rows"],
    }


def verified_comparison(deadline_ns: float = 1.0, minimum_input_mv: float = 1.0,
                        *, reserved_only: bool = False) -> pd.DataFrame:
    frame, reports, _ = load_verified_validation()
    selected = frame[(frame.deadline_ns == deadline_ns) & (frame.input_mv != 0)
                     & (frame.input_mv.abs() >= minimum_input_mv)].copy()
    if reserved_only:
        training = {(item["design_name"], item["case_id"]) for item in reports
                    if item["used_for_design_selection"]}
        selected = selected[[(name, case) not in training
                             for name, case in zip(selected.design_name, selected.case_id)]]
    selected["correct"] = selected.outcome == "correct"
    selected["unavailable"] = ~selected.policy_available
    return selected.groupby(["design_name", "policy"], sort=False).agg(
        points=("correct", "size"), correct=("correct", "sum"), pass_fraction=("correct", "mean"),
        unavailable_points=("unavailable", "sum"), simulated_points=("core_energy_fj", "count"),
        mean_core_energy_fj=("core_energy_fj", "mean"), refined_points=("numerically_refined", "sum"),
    )
