"""A predeclared circuit search followed by reserved PVT and operating-stress studies."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import threading

import numpy as np
import pandas as pd

from .designs import DESIGNS, circuit_text, get_design
from .experiments import (
    CalibrationError, DEADLINES_NS, case_id, cases, select_trim, source_hashes,
)
from .spice import Point, ROOT, SimulationError, Simulator, Trace, measure, sha256, write_json

STUDY = ROOT / "results" / "study"
CACHE = ROOT / ".cache" / "spice"
TRAINING_INPUTS_MV = (-18, -6, -2, 2, 6, 18)
VALIDATION_INPUTS_MV = (-30, -10, -3, -1, -0.5, -0.25, 0, 0.25, 0.5, 1, 3, 10, 30)
TARGET_DEADLINE_NS = 1.0
POLICIES = ("code_zero", "nominal_frozen", "local_boundary", "deadline_aware")


def study_hashes() -> dict[str, str]:
    return {**source_hashes(), str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__))}


def training_cases(design_name: str) -> list[Point]:
    return [
        Point(design_name=design_name, corner=corner, vdd_v=vdd, temperature_c=temp, differential_v=0)
        for corner, vdd, temp in (
            ("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("ff", 1.95, 125.0),
        )
    ]


def protocol() -> dict:
    return {
        "version": 1,
        "title": "Deadline-constrained mixed-threshold comparator design and calibration",
        "candidate_family": [design.report() for design in DESIGNS.values()],
        "training_cases": [asdict(point) for point in training_cases("baseline")],
        "training_inputs_mv": list(TRAINING_INPUTS_MV),
        "target_deadline_ns": TARGET_DEADLINE_NS,
        "validation_inputs_mv": list(VALIDATION_INPUTS_MV),
        "validation_deadlines_ns": list(DEADLINES_NS),
        "validation_cases": [asdict(point) for point in cases("full")],
        "policies": list(POLICIES),
        "selection_order": [
            "Among candidates within the energy and gate-area budgets:",
            "maximize worst training-case correct fraction at 1 ns",
            "maximize mean training correct fraction at 1 ns",
            "minimize largest absolute confirmed calibration-boundary endpoint",
            "minimize mean core-rail energy, then gate-area proxy",
        ],
        "budgets": {
            "maximum_mean_training_energy_relative_to_baseline": 2.0,
            "maximum_gate_area_proxy_relative_to_baseline": 4.0,
        },
        "calibration_window_mv": [-80, 80],
        "calibration_resolution_mv": 0.2,
        "late_calibration_deadline_ns": 3.5,
        "deadline_aware_calibration_deadline_ns": 1.0,
        "qualification_reporting": "Separately report |input| >= 1 mV and the complete nonzero grid.",
        "selection_disclosure": (
            "The first prototype informed this finite family. Selection uses only the declared three "
            "training conditions and six training inputs. The other PVT conditions are reserved for "
            "validation; this is an engineering study, not a blinded independent benchmark."
        ),
        "failure_rule": (
            "Simulator or data-integrity errors abort. A physically unbracketable calibration is "
            "recorded as unavailable, scores as a failed policy point, and is never silently replaced "
            "with a successful code or zero energy."
        ),
    }


def ensure_protocol() -> None:
    STUDY.mkdir(parents=True, exist_ok=True)
    path = STUDY / "protocol.json"
    expected = protocol()
    if path.exists():
        if json.loads(path.read_text()) != expected:
            raise RuntimeError("The predeclared protocol changed; preserve this campaign and create a new version")
    else:
        write_json(path, expected)


class Evidence:
    def __init__(self, simulator: Simulator) -> None:
        self.sim = simulator
        self.run_ids: set[str] = set()
        self.warnings: dict[str, list[str]] = {}
        self.calibrations: dict[tuple[Point, float], dict] = {}

    def observe(self, trace: Trace) -> None:
        self.run_ids.add(trace.run_id)
        if trace.warnings:
            self.warnings[trace.run_id] = list(trace.warnings)

    def calibration(self, point: Point, deadline_ns: float = 3.5) -> dict:
        point = replace(point, differential_v=0, trim_code=0, previous_differential_v=None)
        key = (point, deadline_ns)
        if key in self.calibrations:
            return self.calibrations[key]
        cache: dict[tuple[float, int], int] = {}
        probe_ids: set[str] = set()

        def batch(requests: list[tuple[float, int]]) -> list[int]:
            missing = list(dict.fromkeys(request for request in requests if request not in cache))
            points = [replace(point, differential_v=value, trim_code=code) for value, code in missing]
            for request, trace in zip(missing, self.sim.run_many(points)):
                self.observe(trace)
                probe_ids.add(trace.run_id)
                cache[request] = measure(trace, deadline_ns).decision
            return [cache[request] for request in requests]

        try:
            selection = select_trim(
                lambda value, code: batch([(value, code)])[0],
                max_code=get_design(point.design_name).max_code,
                batch_probe=batch, deadline_ns=deadline_ns,
            )
        except CalibrationError as error:
            result = {
                "available": False, "reason": str(error), "selection": None,
                "deadline_ns": deadline_ns,
            }
        else:
            result = {
                "available": True, "reason": None, "selection": selection,
                "deadline_ns": deadline_ns,
            }
        result.update({"point": asdict(point), "probe_run_ids": sorted(probe_ids)})
        self.calibrations[key] = result
        return result

    def observations(
        self, point: Point, policy_codes: dict[str, int | None],
        inputs_mv: tuple[float, ...], deadlines: tuple[float, ...],
    ) -> list[dict]:
        requests = [
            replace(point, differential_v=value / 1000, trim_code=code)
            for code in policy_codes.values() if code is not None for value in inputs_mv
        ]
        traces = self.sim.run_many(requests)
        indexed = {trace.point: trace for trace in traces}
        for trace in traces:
            self.observe(trace)
        rows = []
        for policy, code in policy_codes.items():
            if code is not None and type(code) is not int:
                raise CalibrationError("A selected code must be an integer")
            for value in inputs_mv:
                actual = replace(point, differential_v=value / 1000, trim_code=0 if code is None else code)
                for deadline in deadlines:
                    base = {
                        **asdict(actual), "case_id": case_id(point), "policy": policy,
                        "input_mv": value, "deadline_ns": deadline,
                        "policy_available": code is not None,
                    }
                    if code is None:
                        rows.append({
                            **base, "trim_code": None, "outcome": "calibration_unavailable",
                            "decision": None, "decision_time_ns": None, "core_energy_fj": None,
                            "reset_ok": None, "qp_at_deadline_v": None, "qn_at_deadline_v": None,
                            "run_id": None,
                        })
                    else:
                        trace = indexed[actual]
                        rows.append({**base, **asdict(measure(trace, deadline)), "run_id": trace.run_id})
        return rows


def chosen_code(calibration: dict) -> int | None:
    return calibration["selection"]["code"] if calibration["available"] else None


def _receipt(evidence: Evidence, artifacts: tuple[str, ...]) -> dict:
    return {
        "status": "complete", "completed_utc": datetime.now(timezone.utc).isoformat(),
        "source_hashes": study_hashes(), "protocol_sha256": sha256(STUDY / "protocol.json"),
        "python_version": platform.python_version(), "platform": platform.platform(),
        "provenance": evidence.sim.provenance,
        "model_hashes": evidence.sim.model_hashes,
        "run_ids": sorted(evidence.run_ids), "unique_run_count": len(evidence.run_ids),
        "process_count_this_invocation": evidence.sim.processes,
        "new_simulations": evidence.sim.executed, "cache_hits": evidence.sim.cached,
        "warnings": evidence.warnings,
        "artifact_sha256": {name: sha256(STUDY / name) for name in artifacts},
    }


def _running_manifest(name: str) -> None:
    write_json(STUDY / name, {
        "status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_hashes": study_hashes(),
    })


def optimize() -> Path:
    ensure_protocol()
    _running_manifest("optimization_manifest.json")
    evidence = Evidence(Simulator(CACHE))
    candidates = []
    observations = []
    for index, design in enumerate(DESIGNS.values(), 1):
        calibrations = []
        rows = []
        for point in training_cases(design.name):
            calibration = evidence.calibration(point)
            calibrations.append(calibration)
            rows.extend(evidence.observations(
                point, {"training_local": chosen_code(calibration)},
                TRAINING_INPUTS_MV, (TARGET_DEADLINE_NS,),
            ))
        frame = pd.DataFrame(rows)
        correct = frame.assign(correct=frame.outcome == "correct")
        case_fractions = correct.groupby("case_id").correct.mean()
        available = all(item["available"] for item in calibrations)
        candidates.append({
            "design": design.report(),
            "calibration_available_at_all_training_cases": available,
            "worst_case_correct_fraction": float(case_fractions.min()),
            "mean_correct_fraction": float(correct.correct.mean()),
            "worst_boundary_mv": max(
                item["selection"]["selected"]["worst_absolute_mv"] for item in calibrations
            ) if available else None,
            "mean_core_energy_fj": float(frame.core_energy_fj.mean()) if available else None,
            "calibrations": calibrations,
        })
        observations.extend(rows)
        print(
            f"SEARCH [{index}/{len(DESIGNS)}] {design.name}: "
            f"worst={case_fractions.min():.1%}, overall={correct.correct.mean():.1%}, "
            f"area_proxy={design.gate_area_um2:.2f} um2; "
            f"{evidence.sim.executed} waveforms / {evidence.sim.processes} ngspice processes",
            flush=True,
        )
    baseline = next(candidate for candidate in candidates if candidate["design"]["name"] == "baseline")
    if baseline["mean_core_energy_fj"] is None:
        raise RuntimeError("Baseline training calibration failed; energy-budget comparison is undefined")
    for candidate in candidates:
        energy = candidate["mean_core_energy_fj"]
        candidate["energy_budget_pass"] = energy is not None and energy <= 2 * baseline["mean_core_energy_fj"]
        candidate["area_budget_pass"] = candidate["design"]["gate_area_proxy_um2"] <= 4 * baseline["design"]["gate_area_proxy_um2"]
        candidate["eligible"] = (
            candidate["calibration_available_at_all_training_cases"]
            and candidate["energy_budget_pass"] and candidate["area_budget_pass"]
        )
    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    if not eligible:
        raise RuntimeError("No candidate meets the declared budgets; no winner will be fabricated")
    selected = min(eligible, key=lambda candidate: (
        -candidate["worst_case_correct_fraction"], -candidate["mean_correct_fraction"],
        candidate["worst_boundary_mv"], candidate["mean_core_energy_fj"],
        candidate["design"]["gate_area_proxy_um2"], candidate["design"]["name"],
    ))
    selection = {
        "selected_design": selected["design"]["name"],
        "selection_status": "baseline_retained" if selected is baseline else "candidate_selected",
        "candidates": candidates,
        "selection_was_made_before_full_validation": True,
    }
    pd.DataFrame(observations).to_csv(STUDY / "training_measurements.csv", index=False)
    write_json(STUDY / "selection.json", selection)
    (STUDY / "selected_circuit.spice").write_text(
        circuit_text(get_design(selection["selected_design"])), encoding="utf-8",
    )
    write_json(STUDY / "optimization_manifest.json", _receipt(
        evidence, ("training_measurements.csv", "selection.json", "selected_circuit.spice"),
    ))
    print(f"Selected: {selection['selected_design']} (before reserved validation)", flush=True)
    return STUDY


def checked_manifest(name: str) -> dict:
    manifest = json.loads((STUDY / name).read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise SimulationError(f"{name} is not complete")
    if manifest["source_hashes"] != study_hashes():
        raise SimulationError(f"Scientific source changed after {name}; regenerate the affected study")
    if manifest["protocol_sha256"] != sha256(STUDY / "protocol.json"):
        raise SimulationError("The predeclared protocol was modified")
    for filename, expected in manifest["artifact_sha256"].items():
        if sha256(STUDY / filename) != expected:
            raise SimulationError(f"Study artifact was modified: {filename}")
    return manifest


def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_case_checkpoint(path: Path, identity: dict) -> dict | None:
    if not path.exists():
        return None
    checkpoint = json.loads(path.read_text(encoding="utf-8"))
    if checkpoint["identity"] != identity:
        raise SimulationError("A validation checkpoint belongs to a different experiment")
    payload = checkpoint["payload"]
    if checkpoint["payload_sha256"] != _payload_hash(payload):
        raise SimulationError("Validation checkpoint data was modified")
    expected_rows = len(POLICIES) * len(VALIDATION_INPUTS_MV) * len(DEADLINES_NS)
    if len(payload["rows"]) != expected_rows:
        raise SimulationError("Validation checkpoint has an incomplete observation grid")
    return payload


def validate_full() -> Path:
    ensure_protocol()
    optimization = checked_manifest("optimization_manifest.json")
    selection = json.loads((STUDY / "selection.json").read_text())
    selected_name = selection["selected_design"]
    _running_manifest("validation_manifest.json")
    evidence = Evidence(Simulator(CACHE))
    designs = list(dict.fromkeys(("baseline", selected_name)))
    points = [replace(base, design_name=name) for name in designs for base in cases("full")]
    nominal_points = list(dict.fromkeys(
        Point(design_name=point.design_name, pair_skew=point.pair_skew, differential_v=0)
        for point in points
    ))
    for index, point in enumerate(nominal_points, 1):
        evidence.calibration(point)
        print(f"Nominal reference [{index}/{len(nominal_points)}]: {point.design_name} / skew {point.pair_skew:+.0%}", flush=True)
    seed_calibrations = dict(evidence.calibrations)
    checkpoints = ROOT / ".cache" / "validation_cases"
    checkpoints.mkdir(parents=True, exist_ok=True)
    worker_state = threading.local()
    identity_base = {
        "source_hashes": study_hashes(), "protocol_sha256": sha256(STUDY / "protocol.json"),
        "selection_sha256": optimization["artifact_sha256"]["selection.json"],
        "ngspice_binary_sha256": evidence.sim.provenance["ngspice_binary_sha256"],
        "model_hashes": evidence.sim.model_hashes,
    }

    def evaluate(point: Point) -> tuple[dict, int, int, int, bool]:
        if not hasattr(worker_state, "sim"):
            worker_state.sim = Simulator(CACHE, workers=1)
        simulator = worker_state.sim
        before = (simulator.executed, simulator.cached, simulator.processes)
        identity = {**identity_base, "point": asdict(point)}
        checkpoint_path = checkpoints / (_payload_hash(identity) + ".json")
        saved = read_case_checkpoint(checkpoint_path, identity)
        if saved is not None:
            raw_points = []
            for run_id in saved["run_ids"]:
                if not re.fullmatch(r"[0-9a-f]{24}", run_id):
                    raise SimulationError("Invalid raw-run ID in validation checkpoint")
                metadata_path = CACHE / run_id / "metadata.json"
                if not metadata_path.is_file():
                    raise SimulationError("A completed validation checkpoint lost its raw evidence")
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                raw_points.append(Point(**metadata["identity"]["point"]))
            traces = simulator.run_many(raw_points)
            if [trace.run_id for trace in traces] != saved["run_ids"]:
                raise SimulationError("Checkpoint raw identities no longer match the experiment")
            return saved, 0, simulator.cached - before[1], 0, True
        local_evidence = Evidence(simulator)
        local_evidence.calibrations = dict(seed_calibrations)
        nominal = Point(design_name=point.design_name, pair_skew=point.pair_skew, differential_v=0)
        frozen = local_evidence.calibration(nominal)
        local = local_evidence.calibration(point)
        aware = local_evidence.calibration(point, TARGET_DEADLINE_NS)
        policy_codes = {
            "code_zero": 0, "nominal_frozen": chosen_code(frozen),
            "local_boundary": chosen_code(local), "deadline_aware": chosen_code(aware),
        }
        case_rows = local_evidence.observations(point, policy_codes, VALIDATION_INPUTS_MV, DEADLINES_NS)
        training_condition = any(
            (point.corner, point.vdd_v, point.temperature_c, point.pair_skew)
            == (training.corner, training.vdd_v, training.temperature_c, training.pair_skew)
            for training in training_cases(point.design_name)
        )
        report = {
            "design_name": point.design_name, "case_id": case_id(point), "point": asdict(point),
            "used_for_design_selection": training_condition, "codes": policy_codes,
            "frozen": frozen, "local": local, "deadline_aware": aware,
        }
        payload = {
            "report": report, "rows": case_rows,
            "run_ids": sorted(local_evidence.run_ids), "warnings": local_evidence.warnings,
        }
        write_json(checkpoint_path, {
            "identity": identity, "payload": payload, "payload_sha256": _payload_hash(payload),
        })
        return (
            payload, simulator.executed - before[0], simulator.cached - before[1],
            simulator.processes - before[2], False,
        )

    rows = []
    reports = []
    resumed_cases = 0
    # Independent conditions run concurrently, but ngspice concurrency remains capped at two.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for count, result in enumerate(pool.map(evaluate, points), 1):
            payload, executed, cached, processes, resumed = result
            rows.extend(payload["rows"])
            reports.append(payload["report"])
            evidence.run_ids.update(payload["run_ids"])
            evidence.warnings.update(payload["warnings"])
            evidence.sim.executed += executed
            evidence.sim.cached += cached
            evidence.sim.processes += processes
            resumed_cases += int(resumed)
            report = payload["report"]
            print(
                f"PVT [{count:02d}/{len(points)}] {report['design_name']} / {report['case_id']} / "
                f"codes={report['codes']}; {evidence.sim.executed} new waveforms"
                + (" [verified checkpoint]" if resumed else ""), flush=True,
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(STUDY / "validation_measurements.csv", index=False)
    write_json(STUDY / "validation_calibration.json", reports)
    manifest = _receipt(evidence, ("validation_measurements.csv", "validation_calibration.json"))
    manifest.update({
        "designs": designs, "case_count_per_design": len(cases("full")),
        "row_count": len(frame), "selection_sha256": optimization["artifact_sha256"]["selection.json"],
        "selection_source_manifest_sha256": sha256(STUDY / "optimization_manifest.json"),
        "resumed_case_checkpoints": resumed_cases,
        "maximum_concurrent_simulators": 2,
        "limitations": limitations(),
    })
    write_json(STUDY / "validation_manifest.json", manifest)
    return STUDY


def limitations() -> list[str]:
    return [
        "Schematic-level BSIM simulation, not silicon measurement, layout area, DRC/LVS or PEX.",
        "Width skew is controlled sensitivity stress, not foundry Monte Carlo, yield or mismatch statistics.",
        "No transient noise; unresolved decisions do not measure metastability probability.",
        "Energy covers the core VDD rail over a full cycle; input/clock drivers and calibration controller are excluded.",
        "Gate-area proxy is the sum of transistor W*L, not placed/routed area or manufacturing cost.",
        "The host implements calibration and supplies ideal trim-bit voltages; an on-chip controller is not implemented.",
        "Search is bounded to the published candidate family and informed by the earlier prototype; no global optimum or new topology is claimed.",
        "Unavailable calibration counts as failed policy coverage and has no invented waveform or zero-energy substitute.",
        "The finite validation grid and stress tests do not constitute production signoff or a blinded external benchmark.",
    ]


def load_validation() -> tuple[pd.DataFrame, list[dict], dict]:
    manifest = checked_manifest("validation_manifest.json")
    checked_manifest("optimization_manifest.json")
    if manifest["selection_sha256"] != sha256(STUDY / "selection.json"):
        raise SimulationError("Design selection changed after full validation")
    frame = pd.read_csv(STUDY / "validation_measurements.csv")
    reports = json.loads((STUDY / "validation_calibration.json").read_text())
    expected = len(manifest["designs"]) * 49 * len(POLICIES) * len(VALIDATION_INPUTS_MV) * len(DEADLINES_NS)
    if len(frame) != expected or len(frame) != manifest["row_count"]:
        raise SimulationError("Full validation does not have the declared output shape")
    if frame.duplicated(["design_name", "case_id", "policy", "input_mv", "deadline_ns"]).any():
        raise SimulationError("Duplicate validation observations would bias the comparison")
    available = frame[frame.policy_available]
    if available.run_id.isna().any() or available.core_energy_fj.isna().any() or not available.reset_ok.all():
        raise SimulationError("Executed validation rows have missing evidence or failed reset")
    unavailable = frame[~frame.policy_available]
    if unavailable.run_id.notna().any() or unavailable.core_energy_fj.notna().any():
        raise SimulationError("Unavailable calibration has been represented as a simulated success")
    return frame, reports, manifest


def comparison(deadline_ns: float = 1.0, minimum_input_mv: float = 1.0, *, reserved_only: bool = False) -> pd.DataFrame:
    frame, reports, _ = load_validation()
    selected = frame[
        (frame.deadline_ns == deadline_ns) & (frame.input_mv.abs() >= minimum_input_mv)
        & (frame.input_mv != 0)
    ].copy()
    if reserved_only:
        training = {
            (report["design_name"], report["case_id"]) for report in reports
            if report["used_for_design_selection"]
        }
        selected = selected[
            [(design, case) not in training for design, case in zip(selected.design_name, selected.case_id)]
        ]
    selected["correct"] = selected.outcome == "correct"
    selected["unavailable"] = ~selected.policy_available
    return selected.groupby(["design_name", "policy"], sort=False).agg(
        points=("correct", "size"), correct=("correct", "sum"),
        pass_fraction=("correct", "mean"), unavailable_points=("unavailable", "sum"),
        simulated_points=("core_energy_fj", "count"), mean_core_energy_fj=("core_energy_fj", "mean"),
    )
