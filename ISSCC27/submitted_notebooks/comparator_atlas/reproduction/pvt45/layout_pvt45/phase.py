"""Frozen input and prospective matrix/numerical contracts; no tool execution."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent
NOMINAL = ENTRY / "layout_nominal27"
sys.path.insert(0, str(NOMINAL))
import contract as historical
import simulate as native_simulator

PROTOCOL = json.loads((HERE / "protocol.json").read_text())
STEPS = PROTOCOL["numerics"]["initial_steps_ps"] + PROTOCOL["numerics"]["further_steps_ps"]
MODES = PROTOCOL["matrix"]["modes"]
DEADLINES = PROTOCOL["measurement"]["retained_reporting_deadlines_ns"]


class IntegrityError(RuntimeError):
    """A global source/runtime/geometry contract failure, not a circuit timeout."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrityError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def build_matrix() -> dict:
    matrix = PROTOCOL["matrix"]
    observed = [tuple(c) for c in matrix["previously_observed_postlayout_conditions"]]
    grid = list(itertools.product(matrix["corners"], matrix["supply_v"], matrix["temperature_c"]))
    require(len(grid) == len(set(grid)) == 45 and len(observed) == 5
            and set(observed) <= set(grid), "Changed 45-condition grid or observed flags")
    conditions = observed + [c for c in grid if c not in observed]
    points = []
    for index, (corner, vdd, temperature) in enumerate(conditions, 1):
        for differential in matrix["differential_mv"]:
            for mode in MODES:
                point_id = f"c{index:02d}-{mode}-{'m' if differential < 0 else 'p'}{abs(differential):02d}"
                points.append({
                    "point_id": point_id, "condition_id": f"c{index:02d}",
                    "condition": [corner, vdd, temperature], "mode": mode,
                    "differential_mv": differential,
                    "previously_observed_postlayout": (corner, vdd, temperature) in observed,
                    "new_postlayout_not_blinded": (corner, vdd, temperature) not in observed,
                    "physical_point": {
                        "corner": corner, "vdd_v": vdd, "temperature_c": temperature,
                        "differential_v": differential / 1000,
                        "common_mode_ratio": 0.5, "pair_skew": 0, "trim_code": 0,
                        "load_ff": 5, "design_name": "lvt_balanced_4b",
                        "source_resistance_ohm": 0, "sample_cap_ff": 0,
                        "previous_differential_v": None,
                    },
                })
    require(len(points) == 360 and sum(p["mode"] == "rc" for p in points) == 180,
            "Changed sampled-point denominator")
    return {
        "schema": 1, "protocol_sha256": sha256(HERE / "protocol.json"),
        "condition_count": 45, "point_count": 360,
        "previously_observed_conditions": 5, "new_postlayout_conditions": 40,
        "not_a_blinded_external_test": True, "points": points,
    }


def audit_inputs() -> dict:
    pins = json.loads((HERE / "inputs-sha256.json").read_text())
    observed, variants = {}, {}
    for name, expected in pins["files"].items():
        observed[name] = sha256(ENTRY / name)
        if observed[name] != expected:
            require(os.name == "nt" and os.environ.get("GITHUB_ACTIONS") != "true"
                    and observed[name] == pins["offline_windows_exact_variant"].get(name),
                    f"Frozen input hash mismatch: {name}")
            variants[name] = {"actual": observed[name], "committed_linux": expected}
    target = PROTOCOL["immutable_target"]
    for field in ("schematic", "rc", "gds", "physical_receipt"):
        require(sha256(ENTRY / target[f"{field}_path"]) == target[f"{field}_sha256"],
                f"Wrong immutable {field}")
    fixed = historical.PROTOCOL
    keys = ("source", "budget", "tools", "structural_gates", "extraction", "simulation", "numerics")
    require(canonical_sha256({key: fixed[key] for key in keys}) == target["old_nonlayout_policy_sha256"],
            "Historical non-layout policy changed")
    historical.audit_source()
    rc = historical.read_spice(ENTRY / target["rc_path"])
    rc_contract = historical.check_netlist(rc, rc=True)
    require(rc_contract["device_count"] == 27 and rc["ports"] == target["ordered_ports"],
            "Fixed extracted device/port interface changed")
    checks = json.loads((ENTRY / "layout_compact_repair" / "evidence" / "attempt1"
                         / "structural-results.json").read_text())
    require(len(checks) == 17 and all(r["status"] == "PASS" for r in checks),
            "Historical physical qualification receipt is invalid")
    require(DEADLINES == fixed["numerics"]["reporting_deadlines_ns"],
            "Measurement reporting windows changed")
    require(PROTOCOL["numerics"]["qualification_deadlines_ns"] == [1.0, 2.0]
            and STEPS == [10, 5, 2.5, 1.25, 0.625, 0.3125, 0.15625],
            "Prospective numerical endpoints changed")
    require(PROTOCOL["matrix"]["differential_mv"] == [-10, -3, 3, 10]
            and MODES == ["schematic", "rc"]
            and PROTOCOL["measurement"]["new_prospective_primary_deadline_ns"] == 2
            and PROTOCOL["measurement"]["parallel_original_deadline_ns"] == 1,
            "Prospective scoring scope changed")
    stimulus = PROTOCOL["stimulus"]
    old_stimulus = fixed["simulation"]["stimulus"]
    for new, old in (
        ("pair_skew", "pair_skew"), ("trim_code", "trim_code"),
        ("common_mode_ratio", "common_mode_ratio"), ("output_load_ff_each", "load_ff_each"),
        ("clock_period_ns", "clock_period_ns"), ("clock_delay_ns", "clock_delay_ns"),
        ("clock_high_ns", "clock_high_ns"), ("clock_edge_ps", "edge_ps"),
        ("source_resistance_ohm", "source_resistance_ohm"),
        ("rail_high_vdd", "rail_high_vdd"), ("rail_low_vdd", "rail_low_vdd"),
    ):
        require(stimulus[new] == old_stimulus[old], f"Fixed stimulus changed: {new}")
    require(stimulus["sample_cap_ff"] == 0 and stimulus["previous_differential_v"] is None
            and not stimulus["zero_differential_included"], "Unapproved stimulus or zero-input case")
    require(PROTOCOL["numerics"]["maximum_energy_relative_error_percent"] == 1
            and PROTOCOL["numerics"]["maximum_latency_error_ns"] == 0.02
            and PROTOCOL["numerics"]["sensitive_required_consecutive_passing_halvings"] == 2
            and PROTOCOL["numerics"]["sensitive_finest_at_most_ps"] == 0.625,
            "Fixed numerical limits changed")
    budget = PROTOCOL["authorization"]
    require(budget["maximum_jobs"] == 2 and budget["maximum_new_transient_attempts_total"] == 900
            and budget["initial_transient_attempts"] == 720 and budget["maximum_additional_attempts"] == 180
            and budget["maximum_concurrent_ngspice"] == 2 and budget["threads_per_ngspice"] == 1,
            "Hard execution budget changed")
    matrix = build_matrix()
    require(json.loads((HERE / "matrix.json").read_text()) == matrix,
            "Frozen matrix does not match the prospective protocol")
    return {
        "input_sha256": observed, "offline_windows_variants": variants,
        "protocol_sha256": sha256(HERE / "protocol.json"),
        "matrix_sha256": sha256(HERE / "matrix.json"),
        "historical_physical_checks": 17, "fresh_drc_lvs_extraction_performed": False,
        "fresh_read_only_rc_device_port_attachment_check": rc_contract,
        "rc_passive_metrics": historical.passive_metrics(rc),
    }


def history_state(history: list[dict]) -> dict:
    require(bool(history), "Empty numerical history")
    steps = [r["max_step_ps"] for r in history]
    require(steps == STEPS[:len(steps)], "Coarse restart, skipped step or nonmonotone history")
    identity = history[0]["physical_identity"]
    require(all(r["physical_identity"] == identity for r in history),
            "Numerical history changed physical identity")
    require(len({r["attempt_id"] for r in history}) == len(history), "Duplicated numerical evidence")
    base: dict[str, Any] = {
        "qualified": False, "state": "UNKNOWN", "finest_attempt_id": history[-1]["attempt_id"],
        "finest_max_step_ps": steps[-1], "history_attempt_ids": [r["attempt_id"] for r in history],
        "comparisons": [], "ever_sensitive": False,
    }
    if any(r["status"] != "success" for r in history):
        base["reason"] = "Simulator/reset/measurement/interruption evidence remains unqualified"
        return base
    if len(history) < 2:
        base["reason"] = "Both initial timestep observations are required"
        return base
    comparisons = []
    for coarse, fine in zip(history, history[1:]):
        complete = historical.compare_measurements(coarse["measurements"], fine["measurements"])
        selected = [d for d in complete["deadlines"]
                    if d["deadline_ns"] in PROTOCOL["numerics"]["qualification_deadlines_ns"]]
        require(len(selected) == 2, "Missing actual 1/2 ns numerical comparisons")
        comparisons.append({
            "coarse_attempt_id": coarse["attempt_id"], "fine_attempt_id": fine["attempt_id"],
            "passed": all(d["passed"] for d in selected), "qualification_deadlines": selected,
            "all_original_reporting_deadline_comparisons": complete,
        })
    sensitive = any(not c["passed"] for c in comparisons)
    streak = 0
    for comparison in reversed(comparisons):
        if not comparison["passed"]:
            break
        streak += 1
    qualified = comparisons[-1]["passed"] and (
        not sensitive or (streak >= 2 and steps[-1] <= 0.625))
    base.update(
        qualified=qualified, state="qualified" if qualified else "UNKNOWN",
        comparisons=comparisons, ever_sensitive=sensitive,
        consecutive_passing_halvings=streak,
        reason=None if qualified else "Finest evidence has not met fixed monotone confirmation",
    )
    return base


def outcome_counts(rows: list[dict], mode: str, deadline: int) -> dict:
    chosen = [r for r in rows if r["mode"] == mode]
    expected = 180
    require(len(chosen) == expected, f"Missing fixed {mode} rows in coverage denominator")
    counts = {key: 0 for key in (
        "correct", "wrong", "unresolved", "reset_failure", "simulator_error",
        "measurement_error", "integrity_error", "interrupted", "not_run", "numerical_unknown")}
    for row in chosen:
        if row["execution_status"] != "success":
            category = row["execution_status"]
        elif not row["numerically_qualified"]:
            category = "numerical_unknown"
        else:
            category = row[f"outcome_{deadline}ns"]
        require(category in counts, f"Unsupported result state: {category}")
        counts[category] += 1
    require(sum(counts.values()) == expected, "Dropped case in fixed denominator")
    return {"denominator": expected, **counts}


if __name__ == "__main__":
    if sys.argv[1:] == ["--freeze-matrix"]:
        destination = HERE / "matrix.json"
        require(not destination.exists(), "Do not overwrite a frozen matrix")
        write_json(destination, build_matrix())
    else:
        print(json.dumps(audit_inputs(), indent=2))
