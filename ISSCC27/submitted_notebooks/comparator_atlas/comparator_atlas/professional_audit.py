"""Post-selection, energy-efficient comparator control and calibrated-probe accounting."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading

import numpy as np
import pandas as pd

from .designs import get_design
from .experiments import DEADLINES_NS, case_id, cases
from .spice import Point, Simulator, measure, sha256, write_json
from .stress import compare_resolution, load_verified_validation
from .study import CACHE, STUDY, Evidence, VALIDATION_INPUTS_MV, chosen_code, study_hashes

OUTPUT = STUDY / "professional"
CONTROL = "lvt_base_3b"


def protocol() -> dict:
    return {
        "version": 1,
        "purpose": "Test whether an existing lower-energy candidate provides a better engineering tradeoff.",
        "disclosure": (
            "Post-selection ablation, designed after seeing the original 49-condition comparison. "
            "It is not a newly blinded test set and does not replace the frozen nine-candidate selection."
        ),
        "control_design": get_design(CONTROL).report(),
        "conditions": [asdict(replace(point, design_name=CONTROL)) for point in cases("full")],
        "inputs_mv": list(VALIDATION_INPUTS_MV),
        "deadlines_ns": list(DEADLINES_NS),
        "policies": ["code_zero", "local_boundary"],
        "refinement": (
            "All measured nonzero input points for both policies are checked at 10 and 5 ps. "
            "Sensitive points use successive timestep halving and two consecutive passing comparisons "
            "ending at 0.625 ps or finer, under the existing fixed outcome/1% energy/20 ps limits."
        ),
        "calibration_accounting": (
            "Report distinct simulated calibration probes and sum one measured core-VDD cycle per "
            "distinct probe. This is a lower-scope workload measure, not on-chip calibration energy: "
            "warmup, stimulus/reference generation, input/clock drivers and control logic are excluded."
        ),
    }


def identity_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _probe_accounting(calibration: dict, simulator: Simulator) -> dict:
    points = []
    for run_id in calibration["probe_run_ids"]:
        metadata = json.loads((CACHE / run_id / "metadata.json").read_text())
        points.append(Point(**metadata["identity"]["point"]))
    traces = simulator.run_many(points)
    if [trace.run_id for trace in traces] != calibration["probe_run_ids"]:
        raise RuntimeError("Calibration probe identities disagree with retained evidence")
    energy = sum(measure(trace, 3.5).core_energy_fj for trace in traces)
    return {
        "distinct_probe_count": len(traces),
        "measured_probe_core_cycles_energy_fj": float(energy),
        "simulated_transient_duration_ns": 30 * len(traces),
    }


def run_audit() -> Path:
    _, _, reference = load_verified_validation()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected = protocol()
    declared = OUTPUT / "protocol.json"
    if declared.exists() and json.loads(declared.read_text()) != expected:
        raise RuntimeError("The post-selection audit protocol changed")
    if not declared.exists():
        write_json(declared, expected)
    write_json(OUTPUT / "manifest.json", {"status": "running"})
    state = threading.local()
    source_hashes = {**study_hashes(), "comparator_atlas\\professional_audit.py": sha256(Path(__file__))}
    checkpoint_root = CACHE.parent / "professional_cases"
    checkpoint_root.mkdir(exist_ok=True)

    def evaluate(base: Point) -> dict:
        if not hasattr(state, "sim"):
            state.sim = Simulator(CACHE, workers=1)
        simulator = state.sim
        point = replace(base, design_name=CONTROL)
        identity = {
            "source_hashes": source_hashes, "point": asdict(point),
            "protocol_sha256": sha256(declared), "binary": simulator.provenance["ngspice_binary_sha256"],
        }
        checkpoint = checkpoint_root / (identity_digest(identity) + ".json")
        if checkpoint.exists():
            saved = json.loads(checkpoint.read_text())
            if saved["identity"] != identity or saved["payload_sha256"] != identity_digest(saved["payload"]):
                raise RuntimeError("The post-selection audit checkpoint is inconsistent")
            return saved["payload"]
        evidence = Evidence(simulator)
        calibration = evidence.calibration(point)
        code = chosen_code(calibration)
        coarse_rows = evidence.observations(
            point, {"code_zero": 0, "local_boundary": code}, VALIDATION_INPUTS_MV, DEADLINES_NS,
        )
        points = list(dict.fromkeys(
            replace(point, differential_v=value / 1000, trim_code=trim)
            for trim in (0, code) if trim is not None
            for value in VALIDATION_INPUTS_MV if value != 0
        ))
        coarse = {trace.point: trace for trace in simulator.run_many(points)}
        fine = simulator.run_many([replace(item, max_step_ps=5) for item in points])
        initial = []
        final_checks = {}
        pending = {}
        accepted = {}
        history = []
        for original, refined in zip(points, fine):
            evidence.observe(coarse[original])
            evidence.observe(refined)
            checks = compare_resolution(coarse[original], refined)
            initial.extend(checks)
            final_checks[original] = checks
            if not all(row["passed"] for row in checks):
                pending[original] = refined
        streak = {item: 0 for item in pending}
        for step in (2.5, 1.25, 0.625, 0.3125, 0.15625):
            if not pending:
                break
            originals = list(pending)
            refined = simulator.run_many([replace(item, max_step_ps=step) for item in originals])
            for original, trace in zip(originals, refined):
                evidence.observe(trace)
                checks = compare_resolution(pending[original], trace)
                history.extend(checks)
                final_checks[original] = checks
                streak[original] = streak[original] + 1 if all(row["passed"] for row in checks) else 0
                pending[original] = trace
                if streak[original] >= 2 and step <= 0.625:
                    accepted[coarse[original].run_id] = trace
                    del pending[original]
        rows = []
        for row in coarse_rows:
            current = dict(row)
            current["initial_run_id"] = row["run_id"]
            current["numerically_refined"] = row["run_id"] in accepted
            if row["run_id"] in accepted:
                trace = accepted[row["run_id"]]
                current.update({
                    **asdict(trace.point), **asdict(measure(trace, row["deadline_ns"])),
                    "run_id": trace.run_id,
                })
            rows.append(current)
        payload = {
            "case_id": case_id(point), "point": asdict(point), "calibration": calibration,
            "calibration_accounting": _probe_accounting(calibration, simulator),
            "rows": rows, "coarse_rows": coarse_rows, "initial_checks": initial,
            "final_checks": [row for item in points for row in final_checks[item]],
            "refinement_history": history, "refined_points": len(accepted),
            "numerically_stable": not pending,
            "run_ids": sorted(evidence.run_ids), "warnings": evidence.warnings,
        }
        write_json(checkpoint, {
            "identity": identity, "payload": payload, "payload_sha256": identity_digest(payload),
        })
        return payload

    payloads = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for index, payload in enumerate(pool.map(evaluate, cases("full")), 1):
            payloads.append(payload)
            scored = [row for row in payload["rows"] if row["policy"] == "local_boundary"
                      and row["deadline_ns"] == 1 and abs(row["input_mv"]) >= 1]
            print(f"CONTROL [{index}/49] {payload['case_id']}: "
                  f"{sum(row['outcome'] == 'correct' for row in scored)}/{len(scored)}; "
                  f"numerically_stable={payload['numerically_stable']}", flush=True)
    artifacts = []
    for filename, key in (
        ("measurements.csv", "rows"), ("coarse_measurements.csv", "coarse_rows"),
        ("initial_numerical.csv", "initial_checks"), ("final_numerical.csv", "final_checks"),
        ("refinement_history.csv", "refinement_history"),
    ):
        pd.DataFrame([row for payload in payloads for row in payload[key]]).to_csv(OUTPUT / filename, index=False)
        artifacts.append(filename)
    calibration = [
        {key: payload[key] for key in ("case_id", "point", "calibration", "calibration_accounting")}
        for payload in payloads
    ]
    write_json(OUTPUT / "calibration.json", calibration)
    artifacts.append("calibration.json")
    final = [row for payload in payloads for row in payload["final_checks"]]
    stable = all(payload["numerically_stable"] for payload in payloads) and all(row["passed"] for row in final)
    manifest = {
        "status": "complete", "completed_utc": datetime.now(timezone.utc).isoformat(),
        "source_hashes": source_hashes, "protocol_sha256": sha256(declared),
        "reference_validation_artifact_sha256": reference["artifact_sha256"],
        "row_count": sum(len(payload["rows"]) for payload in payloads),
        "case_count": len(payloads), "numerically_stable": stable,
        "initial_failed_checks": sum(not row["passed"] for payload in payloads for row in payload["initial_checks"]),
        "final_failed_checks": sum(not row["passed"] for row in final),
        "refined_physical_points": sum(payload["refined_points"] for payload in payloads),
        "run_ids": sorted({run_id for payload in payloads for run_id in payload["run_ids"]}),
        "warnings": {key: value for payload in payloads for key, value in payload["warnings"].items()},
        "artifact_sha256": {name: sha256(OUTPUT / name) for name in artifacts},
    }
    write_json(OUTPUT / "manifest.json", manifest)
    if not stable:
        raise RuntimeError("The energy-efficient control still contains unresolved numerical sensitivity")
    return OUTPUT


if __name__ == "__main__":
    print(run_audit())
