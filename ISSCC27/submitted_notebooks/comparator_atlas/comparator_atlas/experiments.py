"""Foreground trim characterization, held-out inputs, and auditable PVT sweeps."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from itertools import product
import json
from pathlib import Path
import platform

import pandas as pd

from .spice import (
    CALIBRATION_DEADLINE_NS, CORNERS, ROOT, Point, SimulationError, Simulator,
    measure, sha256, write_json,
)

Probe = Callable[[float, int], int]
BatchProbe = Callable[[list[tuple[float, int]]], list[int]]
DEADLINES_NS = (0.25, 0.35, 0.5, 0.75, 1.0, 2.0)
QUICK_INPUTS_MV = (-30, -15, -8, -4, -2, -1, -0.25, 0, 0.25, 1, 2, 4, 8, 15, 30)
MODES = ("untrimmed", "frozen", "retuned")


class CalibrationError(RuntimeError):
    """The calibration experiment cannot support a switching-boundary claim."""


@dataclass(frozen=True)
class Boundary:
    negative_v: float
    positive_v: float

    @property
    def midpoint_mv(self) -> float:
        return 500 * (self.negative_v + self.positive_v)

    @property
    def halfwidth_mv(self) -> float:
        return 500 * (self.positive_v - self.negative_v)

    @property
    def worst_absolute_mv(self) -> float:
        return 1000 * max(abs(self.negative_v), abs(self.positive_v))

    def report(self) -> dict[str, float]:
        return {
            **asdict(self), "midpoint_mv": self.midpoint_mv,
            "halfwidth_mv": self.halfwidth_mv, "worst_absolute_mv": self.worst_absolute_mv,
        }


def switching_boundary(
    probe: Probe, code: int, *, limit_v: float = 0.08, tolerance_v: float = 0.0002,
) -> Boundary:
    return switching_boundaries(
        lambda requests: [probe(value, trim) for value, trim in requests],
        [code], limit_v=limit_v, tolerance_v=tolerance_v,
    )[code]


def switching_boundaries(
    probe: BatchProbe, codes: list[int], *, limit_v: float = 0.08, tolerance_v: float = 0.0002,
) -> dict[int, Boundary]:
    if not 0 < tolerance_v < limit_v:
        raise ValueError("Boundary tolerance must be positive and below the search limit")

    def checked(requests: list[tuple[float, int]]) -> list[int]:
        decisions = probe(requests)
        if len(decisions) != len(requests) or any(type(value) is not int or value not in (-1, 0, 1) for value in decisions):
            raise CalibrationError("Calibration batch returned missing or invalid decisions")
        return decisions

    endpoints = checked([(value, code) for code in codes for value in (-limit_v, limit_v)])
    for index, code in enumerate(codes):
        if endpoints[2 * index:2 * index + 2] != [-1, 1]:
            raise CalibrationError(f"Trim {code} does not bracket both polarities within +/-{limit_v} V")
    low = {code: -limit_v for code in codes}
    high = {code: limit_v for code in codes}
    high_decision = {code: 1 for code in codes}
    while active := [code for code in codes if high[code] - low[code] > tolerance_v]:
        requests = [((low[code] + high[code]) / 2, code) for code in active]
        for (middle, code), decision in zip(requests, checked(requests)):
            if decision == -1:
                low[code] = middle
            else:
                high[code] = middle
                high_decision[code] = decision
    negative = dict(low)
    unresolved = [code for code in codes if high_decision[code] == 0]
    for code in unresolved:
        low[code], high[code] = high[code], limit_v
    # Locate the other side of an unresolved band instead of reporting its center as certainty.
    while active := [code for code in unresolved if high[code] - low[code] > tolerance_v]:
        requests = [((low[code] + high[code]) / 2, code) for code in active]
        for (middle, code), decision in zip(requests, checked(requests)):
            if decision == 1:
                high[code] = middle
            else:
                low[code] = middle
    return {code: Boundary(negative[code], high[code]) for code in codes}


def select_trim(
    probe: Probe, *, max_code: int = 7, batch_probe: BatchProbe | None = None,
    deadline_ns: float = CALIBRATION_DEADLINE_NS,
) -> dict[str, object]:
    if type(max_code) is not int or not 1 <= max_code <= 31:
        raise ValueError("Calibration code range must be between 1 and 31")
    if not 0 < deadline_ns <= CALIBRATION_DEADLINE_NS:
        raise ValueError("Calibration deadline must be in (0, 3.5] ns")
    batch = batch_probe if batch_probe is not None else (
        lambda requests: [probe(value, code) for value, code in requests]
    )
    codes = tuple(range(-max_code, max_code + 1))
    values = batch([(0, code) for code in codes])
    if len(values) != len(codes) or any(type(value) is not int or value not in (-1, 0, 1) for value in values):
        raise CalibrationError("Zero-input calibration batch returned missing or invalid decisions")
    decisions = dict(zip(codes, values))
    candidates = {0}
    for code in codes[:-1]:
        if decisions[code] * decisions[code + 1] <= 0:
            candidates.update((code, code + 1))
    nonzero = [value for value in decisions.values() if value]
    monotonic = nonzero == sorted(nonzero) or nonzero == sorted(nonzero, reverse=True)
    if not monotonic:
        status = "nonmonotonic_zero_probe_exhaustive_search"
        candidates.update(codes)
    elif len(candidates) == 1:
        status = "no_zero_crossing_exhaustive_search"
        candidates.update(codes)
    else:
        status = "zero_crossing_candidates"
    boundaries = switching_boundaries(batch, sorted(candidates))
    chosen = min(
        boundaries,
        key=lambda code: (boundaries[code].worst_absolute_mv, abs(code), code),
    )
    return {
        "code": chosen,
        "status": status,
        "method": "zero-input scan; candidate switching-boundary bisection",
        "calibration_deadline_ns": deadline_ns,
        "boundary_tolerance_mv": 0.2,
        "zero_probe_decisions": {str(code): decision for code, decision in decisions.items()},
        "candidate_boundaries": {str(code): bound.report() for code, bound in boundaries.items()},
        "baseline": boundaries[0].report(),
        "selected": boundaries[chosen].report(),
    }


def cases(profile: str) -> list[Point]:
    if profile not in ("quick", "full"):
        raise ValueError("Profile must be 'quick' or 'full'")
    if profile == "full":
        points = [
            Point(corner=corner, vdd_v=vdd, temperature_c=temp, differential_v=0)
            for corner, vdd, temp in product(CORNERS, (1.62, 1.8, 1.95), (-40.0, 27.0, 125.0))
        ]
        skews = (-0.08, -0.04, 0.0, 0.08)
    else:
        points = [Point(corner=corner, differential_v=0) for corner in CORNERS]
        points.extend(
            Point(corner=corner, vdd_v=vdd, temperature_c=temp, differential_v=0)
            for corner, vdd, temp in (
                ("ss", 1.62, -40.0), ("ss", 1.62, 125.0),
                ("ff", 1.95, -40.0), ("ff", 1.95, 125.0),
            )
        )
        skews = (-0.04, 0.0)
    points.extend(Point(pair_skew=skew, differential_v=0) for skew in skews)
    return points


def case_id(point: Point) -> str:
    return (
        f"{point.corner.upper()} | {point.vdd_v:.2f} V | "
        f"{point.temperature_c:g} C | skew {point.pair_skew:+.0%}"
    )


def source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (
            ROOT / "circuits" / "strongarm.spice",
            ROOT / "comparator_atlas" / "spice.py",
            ROOT / "comparator_atlas" / "designs.py",
            Path(__file__),
        )
    }


def run_experiment(profile: str = "quick") -> Path:
    points = cases(profile)
    output = ROOT / "results" / profile
    sim = Simulator(output / "runs")
    inputs = QUICK_INPUTS_MV
    if profile == "full":
        inputs = tuple(sorted(set(inputs) | {-0.1, 0.1, -0.5, 0.5, -3, 3, -6, 6, -20, 20}))
    manifest = {
        "schema": 1, "status": "running", "profile": profile,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "provenance": sim.provenance,
        "model_hashes": sim.model_hashes,
        "source_hashes": source_hashes(),
        "case_count": len(points), "inputs_mv": inputs, "deadlines_ns": DEADLINES_NS,
        "limitations": [
            "Pre-layout schematic simulation; no silicon, DRC, LVS, or extracted parasitics.",
            "Width skew is a deterministic stress parameter, not foundry Monte Carlo or yield.",
            "No transient noise; unresolved outputs are not a measured metastability probability.",
            "Energy is the DUT VDD rail over a full 10 ns cycle, not total system energy.",
            "Clock, input-source and trim-control drivers, calibration controller and its overhead are excluded.",
            "Inputs are ideal DC voltage sources; input kickback and preceding-code history are not characterized.",
            "Foreground trim is selected by a host algorithm, not an implemented on-chip controller.",
            "Finite input and PVT grids are illustrative experiments, not production signoff.",
        ],
    }
    write_json(output / "manifest.json", manifest)
    used_runs: set[str] = set()
    warning_runs: dict[str, list[str]] = {}
    calibrations: dict[Point, dict[str, object]] = {}

    def get_calibration(point: Point) -> dict[str, object]:
        if point in calibrations:
            return calibrations[point]
        probe_runs: set[str] = set()

        def batch_probe(requests: list[tuple[float, int]]) -> list[int]:
            traces = sim.run_many([
                replace(point, differential_v=differential, trim_code=code)
                for differential, code in requests
            ])
            decisions = []
            for trace in traces:
                used_runs.add(trace.run_id)
                probe_runs.add(trace.run_id)
                if trace.warnings:
                    warning_runs[trace.run_id] = list(trace.warnings)
                decisions.append(measure(trace, CALIBRATION_DEADLINE_NS).decision)
            return decisions

        result = select_trim(lambda value, code: batch_probe([(value, code)])[0], batch_probe=batch_probe)
        result["probe_run_ids"] = sorted(probe_runs)
        result["unique_probe_count"] = len(probe_runs)
        calibrations[point] = result
        return result

    rows = []
    reports = []
    for index, point in enumerate(points, 1):
        nominal = Point(pair_skew=point.pair_skew, differential_v=0)
        frozen = get_calibration(nominal)
        local = get_calibration(point)
        codes = {"untrimmed": 0, "frozen": frozen["code"], "retuned": local["code"]}
        reports.append({
            "case_id": case_id(point), "point": asdict(point),
            "frozen_code": frozen["code"], "calibration": local,
        })
        for mode, code in codes.items():
            if type(code) is not int:
                raise CalibrationError("Selected trim code is not an integer")
            actual_points = [
                replace(point, differential_v=value / 1000, trim_code=code) for value in inputs
            ]
            for differential_mv, trace in zip(inputs, sim.run_many(actual_points)):
                actual = trace.point
                used_runs.add(trace.run_id)
                if trace.warnings:
                    warning_runs[trace.run_id] = list(trace.warnings)
                for deadline in DEADLINES_NS:
                    rows.append({
                        "case_id": case_id(point), **asdict(actual),
                        "input_mv": differential_mv, "mode": mode,
                        **asdict(measure(trace, deadline)), "run_id": trace.run_id,
                    })
        print(
            f"[{index:02d}/{len(points):02d}] {case_id(point)}: "
            f"frozen={frozen['code']:+d}, retuned={local['code']:+d}; "
            f"{sim.executed} new / {sim.cached} cached simulations",
            flush=True,
        )

    frame = pd.DataFrame(rows)
    frame.to_csv(output / "measurements.csv", index=False)
    write_json(output / "calibration.json", reports)
    manifest.update({
        "status": "complete",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(frame), "unique_run_count": len(used_runs),
        "new_simulations": sim.executed, "cache_hits": sim.cached,
        "run_ids": sorted(used_runs), "warnings": warning_runs,
        "artifact_sha256": {
            filename: sha256(output / filename)
            for filename in ("measurements.csv", "calibration.json")
        },
    })
    write_json(output / "manifest.json", manifest)
    return output


def load_results(output: Path) -> tuple[pd.DataFrame, list[dict], dict]:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise SimulationError("The experiment did not complete; rerun it before presenting results")
    if manifest["source_hashes"] != source_hashes():
        raise SimulationError("The experiment code changed; regenerate results instead of mixing versions")
    for filename, expected in manifest["artifact_sha256"].items():
        if sha256(output / filename) != expected:
            raise SimulationError(f"Result artifact was modified: {filename}")
    frame = pd.read_csv(output / "measurements.csv")
    reports = json.loads((output / "calibration.json").read_text(encoding="utf-8"))
    if len(frame) != manifest["row_count"] or len(reports) != manifest["case_count"]:
        raise SimulationError("Result counts do not match the experiment manifest")
    return frame, reports, manifest


def summary(output: Path, deadline_ns: float = 0.5) -> pd.DataFrame:
    frame, _, _ = load_results(output)
    scored = frame[(frame.input_mv != 0) & (frame.deadline_ns == deadline_ns)].copy()
    scored["correct"] = scored.outcome == "correct"
    return scored.groupby("mode", sort=False).agg(
        test_points=("correct", "size"),
        correct_points=("correct", "sum"),
        grid_pass_fraction=("correct", "mean"),
        mean_core_energy_fj=("core_energy_fj", "mean"),
    ).reindex(MODES)
