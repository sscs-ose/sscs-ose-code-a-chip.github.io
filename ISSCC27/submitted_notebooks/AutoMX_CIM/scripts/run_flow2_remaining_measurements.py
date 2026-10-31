#!/usr/bin/env python3
"""Run the remaining feasible Flow-2 TT readout screens into one JSON ledger.

The campaign is resumable from hash-checked per-deck checkpoints. Its single
summary.json contains every group's per-job measurements and analysis. It
stops before a fresh holdout if the inspected-case aperture or training fails.
All controls and TG devices are schematic/ideal; no physical ADC or wrapper is
created by this runner.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_core_pex_coverage import Case, mha_cases  # noqa: E402
from scripts.run_post49_row_partition import split_case  # noqa: E402
from scripts.run_wrapper_idle_augmented_tt import idle_training_cases  # noqa: E402
from scripts.run_wrapper_input_loading_screen import _case, _sources  # noqa: E402
from scripts.run_flow2_sample_hold_sweep import make_sweep_deck  # noqa: E402
from scripts.flow2_stimulus_catalog import load_stimuli  # noqa: E402
from scripts.run_flow2_sample_hold_settled_tt import make_settled_deck  # noqa: E402
from scripts.run_flow2_sample_hold_aperture_tt import (  # noqa: E402
    _expected, _metrics, make_aperture_deck)
from scripts import run_flow2_sample_hold_aperture_tt as sparse  # noqa: E402
from scripts import run_flow2_sample_hold_refined_aperture_tt as refined  # noqa: E402

OUTPUT = Path("results/sky130/flow2_remaining_measurements")
SUMMARY = OUTPUT / "summary.json"
REFINED = Path("results/sky130/flow2_sample_hold_refined_aperture_tt")
CALIBRATION = Path("results/sky130/post49_partition_full_tt/calibration/measured.json")
TARGETED = Path("results/sky130/post49_row_partition/adjacent/measured.json")
WIDTH_UM = 0.84
FALL_PS = 5
BROAD_TIMES_NS = (2.065, 2.075, 2.085, 2.095, 2.105)
DENSE_TIMES_NS = (2.065, 2.070, 2.075, 2.080, 2.085,
                  2.090, 2.095, 2.100, 2.105)
OFFSETS_V = (-0.001, -0.00075, -0.0005, -0.00025, -0.00015,
             0.0, 0.00015, 0.00025, 0.0005, 0.00075, 0.001)
PVT_POINTS = (("tt", 1.8, 25), ("ss", 1.8, 25), ("ff", 1.8, 25))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def _snapshot(report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    _save(Path(report["root"]) / SUMMARY, report)


def _vectors(case: Case) -> dict:
    return {"case": case.name, "activation_x2": list(case.acts),
            "ternary_weights": [list(row) for row in case.weights],
            "integer_sums": list(case.sums)}


def _verified_inputs(root: Path) -> dict:
    calibration, holdout, model, pex, budget = _sources(root)
    pex_sha, model_sha = _sha(pex), _sha(model)
    refined_path = root / REFINED / f"pex_{pex_sha[:12]}/measured.json"
    checked = _read(refined_path)
    if (checked.get("format") != "automx-cim-flow2-sample-hold-refined-aperture-tt-v1" or
            checked.get("status") != "MEASURED_TT_REFINED_APERTURE_DIAGNOSTIC" or
            checked.get("planned_new_sims") != checked.get("completed_new_sims") or
            checked.get("planned_new_sims") != 12 or
            checked.get("pex_sha256") != pex_sha or
            checked.get("model_sha256") != model_sha or
            checked.get("script_sha256") != _sha(Path(refined.__file__)) or
            len(checked.get("grid", [])) != 8):
        raise ValueError("matching 12-job refined aperture result required")
    sparse_path = root / sparse.OUTPUT / f"pex_{pex_sha[:12]}/measured.json"
    sparse_report = _read(sparse_path)
    sparse_anchors = refined._validate_sparse(
        root, sparse_report, pex_sha=pex_sha, model_sha=model_sha,
        version=holdout["ngspice_version"])
    if (checked.get("source_sparse_sha256") != _sha(sparse_path) or
            checked.get("anchors") != sparse_anchors):
        raise ValueError("refined timing anchors differ from measured sparse source")
    # The preceding runner verified all source checksums. Independently check
    # its twelve new job logs/checkpoints before using its timing grid.
    verified_jobs = []
    for item in checked.get("jobs", []):
        deck, log, receipt = (root / item[name] for name in
                              ("deck", "log", "checkpoint"))
        if (not all(p.is_file() for p in (deck, log, receipt)) or
                _sha(deck) != item.get("deck_sha256") or
                _sha(log) != item.get("log_sha256")):
            raise ValueError(f"refined aperture file changed: {item['case']}")
        saved = _read(receipt)
        parsed = parse_measurements(log.read_text(
            encoding="utf-8", errors="replace"), _expected())
        if (saved.get("status") != "PASS" or
                saved.get("deck_sha256") != item["deck_sha256"] or
                saved.get("log_sha256") != item["log_sha256"] or
                saved.get("pex_sha256") != pex_sha or
                saved.get("model_sha256") != model_sha or
                saved.get("ngspice_version") != holdout["ngspice_version"] or
                set(parsed) != set(_expected()) or
                parsed != saved.get("measurements_v") or
                parsed != item.get("measurements_v")):
            raise ValueError(f"refined aperture checkpoint changed: {item['case']}")
        verified_jobs.append(item)
    if len(checked.get("jobs", [])) != 12:
        raise ValueError("all twelve refined aperture jobs are required")
    new_points = [_metrics(item) for item in verified_jobs]
    if (checked.get("new_points") != new_points or
            checked.get("grid") != refined._grid(sparse_anchors + new_points)):
        raise ValueError("refined aperture grid differs from verified measurements")
    old, stimulus_provenance = load_stimuli(root, model_sha256=model_sha)
    return {"calibration": calibration, "holdout": holdout, "model": model,
            "pex": pex, "pex_sha": pex_sha, "model_sha": model_sha,
            "budget_v": budget, "version": holdout["ngspice_version"],
            "refined": checked, "refined_sha": _sha(refined_path), "old": old,
            "stimulus_provenance": stimulus_provenance}


def _select_broad(old: dict) -> list[Case]:
    jobs = old["jobs"]["fresh_holdout"]
    lookup = {item["case"]: _case(item) for item in jobs}
    fixed = ("mha_96_b", "mha_118_b", "mha_119_a", "mha_119_b")
    if any(name not in lookup for name in fixed):
        raise ValueError("expected phase and zero stimuli are absent")
    ranked = sorted((case for name, case in lookup.items()
                     if name not in fixed and name not in ("mha_96_a", "mha_118_a")),
                    key=lambda case: (-max(abs(x) for x in case.sums), case.name))
    selected = [lookup[name] for name in fixed] + ranked[:4]
    if len(selected) != 8 or len({case.name for case in selected}) != 8:
        raise ValueError("eight deterministic broad-aperture stimuli required")
    return selected


def _spice(case: Case, model: Path, pex: Path, *, off_ns: float,
           point: tuple[str, float, int] = ("tt", 1.8, 25)) -> str:
    source = make_sweep_deck(case, model, pex, width_um=WIDTH_UM,
                             fall_ps=FALL_PS)
    source = make_settled_deck(source, fall_ps=FALL_PS)
    source = make_aperture_deck(source, turnoff_ns=off_ns)
    corner, vdd, temperature = point
    if corner not in ("tt", "ss", "ff") or not 1.0 < vdd < 2.1 or not -100 <= temperature <= 150:
        raise ValueError("unsupported PVT point")
    lines = source.splitlines()
    library = [i for i, line in enumerate(lines) if line.startswith(".lib ")]
    supply = [i for i, line in enumerate(lines) if line.startswith(".param VDD=")]
    temp = [i for i, line in enumerate(lines) if line.startswith(".temp ")]
    if len(library) != 1 or len(supply) != 1 or len(temp) != 1 or not lines[library[0]].endswith(" tt"):
        raise ValueError("unexpected source model, supply or temperature")
    lines[library[0]] = lines[library[0]][:-2] + corner
    lines[supply[0]] = f".param VDD={vdd:g}"
    lines[temp[0]] = f".temp {temperature}"
    return "\n".join(lines) + "\n"


def _job(root: Path, group: str, case: Case, *, off_ns: float,
         model: Path, pex: Path,
         point: tuple[str, float, int] = ("tt", 1.8, 25),
         job_base: Path = OUTPUT) -> dict:
    folder = root / job_base / group
    folder.mkdir(parents=True, exist_ok=True)
    tag = f"{case.name}_off{off_ns:.3f}_{point[0]}".replace(".", "p")
    deck = folder / f"{tag}.spice"
    content = _spice(case, model, pex, off_ns=off_ns, point=point)
    if deck.is_file() and deck.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"changed deck needs inspection: {deck}")
    deck.write_text(content, encoding="utf-8")
    return {**_vectors(case), "phase": case.name.rsplit("_", 1)[-1],
            "turnoff_start_ns": off_ns,
            "point": {"corner": point[0], "vdd_v": point[1],
                      "temperature_c": point[2]},
            "deck": str(deck.relative_to(root)), "deck_sha256": _sha(deck),
            "log": str((folder / f"{tag}.log").relative_to(root)),
            "checkpoint": str((folder / f"{tag}.receipt.json").relative_to(root))}


def _ngspice(expected_version: str) -> str:
    executable = shutil.which("ngspice")
    if not executable:
        raise FileNotFoundError("ngspice is not on PATH")
    result = subprocess.run([executable, "-v"], capture_output=True,
                            text=True, timeout=15, check=False)
    if (result.stdout + result.stderr).strip() != expected_version:
        raise ValueError("ngspice version differs from current 2+2 evidence")
    return executable


def _measure(root: Path, job: dict, *, executable: str, version: str,
             pex_sha: str, model_sha: str, timeout_s: int) -> dict:
    deck, log, receipt = (root / job[name] for name in
                          ("deck", "log", "checkpoint"))
    saved = None
    if log.is_file() and receipt.is_file():
        try:
            candidate = _read(receipt)
            parsed = parse_measurements(log.read_text(
                encoding="utf-8", errors="replace"), _expected())
            if (candidate.get("status") == "PASS" and
                    candidate.get("deck_sha256") == job["deck_sha256"] and
                    candidate.get("log_sha256") == _sha(log) and
                    candidate.get("pex_sha256") == pex_sha and
                    candidate.get("model_sha256") == model_sha and
                    candidate.get("ngspice_version") == version and
                    set(parsed) == set(_expected()) and
                    parsed == candidate.get("measurements_v")):
                saved = candidate
        except (OSError, ValueError, TypeError):
            pass
    if saved is None:
        if log.exists() or receipt.exists():
            allowed = (root / OUTPUT).resolve()
            if (not deck.parent.resolve().is_relative_to(allowed) or
                    log.parent != deck.parent or receipt.parent != deck.parent or
                    log.stem != deck.stem or receipt.name != f"{deck.stem}.receipt.json"):
                raise ValueError(f"unexpected stale evidence path: {deck}")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            archived = []
            for old in (log, receipt):
                if old.exists():
                    target = old.with_name(f"{old.name}.stale.{stamp}")
                    if target.exists():
                        raise FileExistsError(f"stale archive exists: {target}")
                    old.rename(target)
                    archived.append(str(target.relative_to(root)))
            job["archived_stale_artifacts"] = archived
        try:
            result = subprocess.run([executable, "-b", "-o", str(log), str(deck)],
                                    cwd=deck.parent, capture_output=True,
                                    text=True, timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"{job['case']}: ngspice exceeded {timeout_s}s") from exc
        parsed = parse_measurements(log.read_text(
            encoding="utf-8", errors="replace") if log.is_file() else "", _expected())
        if (result.returncode or set(parsed) != set(_expected()) or
                not all(math.isfinite(value) for value in parsed.values())):
            raise RuntimeError(f"incomplete ngspice measurement: {log}")
        saved = {"status": "PASS", "deck_sha256": job["deck_sha256"],
                 "log_sha256": _sha(log), "pex_sha256": pex_sha,
                 "model_sha256": model_sha, "ngspice_version": version,
                 "measurements_v": parsed}
        _save(receipt, saved)
    job["measurements_v"] = saved["measurements_v"]
    job["log_sha256"] = saved["log_sha256"]
    return job


def _run_jobs(root: Path, report: dict, name: str, jobs: list[dict],
              *, executable: str, inputs: dict, timeout_s: int) -> list[dict]:
    group = {"status": "RUNNING", "planned_sims": len(jobs),
             "completed_sims": 0, "jobs": jobs}
    report["groups"][name] = group
    _snapshot(report)
    for index, job in enumerate(jobs, 1):
        _measure(root, job, executable=executable, version=inputs["version"],
                 pex_sha=inputs["pex_sha"], model_sha=inputs["model_sha"],
                 timeout_s=timeout_s)
        group["completed_sims"] = index
        _snapshot(report)
        if index == 1 or index % 10 == 0 or index == len(jobs):
            print(f"{name}: {index}/{len(jobs)} {job['case']}", flush=True)
    group["status"] = "MEASURED_TT_DIAGNOSTIC"
    _snapshot(report)
    return jobs


def _held(job: dict, column: int) -> tuple[float, float]:
    values = job["measurements_v"]
    positive = float(values[f"aper_hblp_c{column}_late"])
    negative = float(values[f"aper_hbln_c{column}_late"])
    if not all(math.isfinite(x) for x in (positive, negative)):
        raise ValueError(f"nonfinite held node: {job['case']} c{column}")
    return negative - positive, (negative + positive) / 2


def _train(jobs: list[dict], budget_v: float) -> dict:
    phases = {}
    for phase in ("a", "b"):
        columns = []
        subset = [job for job in jobs if job["phase"] == phase]
        for column in range(4):
            observed: dict[int, list[float]] = {}
            common_modes = []
            for job in subset:
                differential, common_mode = _held(job, column)
                observed.setdefault(int(job["integer_sums"][column]), []).append(
                    differential)
                common_modes.append(common_mode)
            levels = sorted(observed)
            intervals = [{"sum": level, "minimum_v": min(observed[level]),
                          "maximum_v": max(observed[level]),
                          "sample_count": len(observed[level])}
                         for level in levels]
            gaps = [higher["minimum_v"] - lower["maximum_v"]
                    for lower, higher in zip(intervals, intervals[1:])]
            thresholds = [(lower["maximum_v"] + higher["minimum_v"]) / 2
                          for lower, higher in zip(intervals, intervals[1:])]
            columns.append({"column": column, "sum_levels": levels,
                            "intervals": intervals, "thresholds_v": thresholds,
                            "overlap_count": sum(gap <= 0 for gap in gaps),
                            "minimum_gap_v": min(gaps) if gaps else None,
                            "training_common_mode_range_v":
                                [min(common_modes), max(common_modes)]})
        phases[phase] = {"columns": columns, "training_cases": len(subset)}
    from scripts.run_post49_partition_full_tt import reachable_two_row_sums
    required = reachable_two_row_sums()
    all_columns = [column for phase in phases.values() for column in phase["columns"]]
    minimum_gap = min(column["minimum_gap_v"] for column in all_columns)
    candidate = (all(column["sum_levels"] == required and
                     column["overlap_count"] == 0 for column in all_columns)
                 and minimum_gap > 2 * budget_v)
    model = {"feature": "held_differential_v", "sample_time": "2.400 ns",
             "phases": phases, "minimum_gap_v": minimum_gap,
             "minimum_required_gap_v": 2 * budget_v,
             "training_margin_candidate": candidate,
             "scope": "one TT held sample per training case; schematic TG/ideal control; no ADC"}
    model["frozen_decoder_sha256"] = _canonical_sha(
        {key: value for key, value in model.items() if key != "frozen_decoder_sha256"})
    return model


def _predict(model: dict, phase: str, column: int,
             differential_v: float) -> tuple[int, float]:
    item = model["phases"][phase]["columns"][column]
    thresholds = item["thresholds_v"]
    position = bisect_right(thresholds, differential_v)
    distance = min(abs(differential_v - threshold) for threshold in thresholds)
    return item["sum_levels"][position], distance


def _decode_holdout(jobs: list[dict], parents: list[Case],
                    model: dict, budget_v: float) -> dict:
    details = []
    by_case = {}
    for job in jobs:
        by_case[job["case"]] = job
        phase = job["phase"]
        for column in range(4):
            differential, common_mode = _held(job, column)
            predicted, distance = _predict(model, phase, column, differential)
            low, high = model["phases"][phase]["columns"][column][
                "training_common_mode_range_v"]
            details.append({"case": job["case"], "phase": phase,
                            "column": column,
                            "expected_partial_sum": job["integer_sums"][column],
                            "predicted_partial_sum": predicted,
                            "held_differential_v": differential,
                            "held_common_mode_v": common_mode,
                            "nearest_threshold_distance_v": distance,
                            "below_error_budget": distance <= budget_v,
                            "common_mode_outside_training":
                                not low <= common_mode <= high})
    partial = {(d["case"], d["column"]): d["predicted_partial_sum"]
               for d in details}
    combined = []
    for parent in parents:
        for column in range(4):
            a = partial[(f"{parent.name}_a", column)]
            b = partial[(f"{parent.name}_b", column)]
            combined.append({"parent_case": parent.name, "column": column,
                             "expected_sum": parent.sums[column],
                             "predicted_sum": a + b})
    partial_errors = sum(d["expected_partial_sum"] != d["predicted_partial_sum"]
                         for d in details)
    full_errors = sum(d["expected_sum"] != d["predicted_sum"] for d in combined)
    below = sum(d["below_error_budget"] for d in details)
    outside = sum(d["common_mode_outside_training"] for d in details)
    return {"partial_samples": len(details), "combined_samples": len(combined),
            "partial_decode_mismatches": partial_errors,
            "combined_decode_mismatches": full_errors,
            "below_error_budget_samples": below,
            "common_mode_outside_training_samples": outside,
            "minimum_threshold_distance_v": min(
                d["nearest_threshold_distance_v"] for d in details),
            "tt_holdout_candidate": (partial_errors == 0 and full_errors == 0 and
                                     below == 0 and outside == 0),
            "details": details, "combined": combined,
            "scope": "fresh deterministic MHA TT held-node cohort; no ADC/noise/PVT sign-off"}


def _sensitivity(jobs: list[dict], model: dict, requirements: dict) -> dict:
    observations = [(job["phase"], column, int(job["integer_sums"][column]),
                     _held(job, column)[0])
                    for job in jobs for column in range(4)]

    def screen(shift_v: float) -> dict:
        mismatches = sum(_predict(model, phase, column, value + shift_v)[0] != expected
                         for phase, column, expected, value in observations)
        return {"injected_differential_shift_v": shift_v,
                "decode_mismatches": mismatches, "samples": len(observations)}

    acceptance = requirements["acceptance"]
    sigma = float(acceptance["maximum_input_referred_noise_rms_v"])
    offset_limit = float(acceptance["maximum_input_referred_offset_abs_v"])
    noise_shifts = (-5 * sigma, -sigma, 0.0, sigma, 5 * sigma)
    aggregate_budget = (offset_limit + 5 * sigma +
                        float(acceptance["maximum_reference_threshold_error_abs_v"]) +
                        float(acceptance["maximum_aperture_induced_shift_abs_v"]))
    offset = [screen(x) for x in OFFSETS_V]
    noise = [screen(x) for x in noise_shifts]
    combined = [screen(-aggregate_budget), screen(aggregate_budget)]
    return {"status": "OFFLINE_DETERMINISTIC_SENSITIVITY",
            "conclusion": ("NO_ERRORS_AT_INJECTED_BUDGET_EXTREMES" if
                           all(item["decode_mismatches"] == 0 for item in combined)
                           else "BLOCKED_INJECTED_BUDGET_ERRORS"),
            "offset_sweep": offset,
            "noise_injection_sweep": noise,
            "combined_budget_extremes": combined,
            "specified_offset_abs_v": offset_limit,
            "specified_noise_rms_v": sigma,
            "combined_budget_v": aggregate_budget,
            "not_signoff": "deterministic held-voltage perturbations only; no transistor noise, ADC offset distribution or 1e-6 BER proof"}


def _broad_result(jobs: list[dict], refined_grid: list[dict],
                  target_v: float) -> dict:
    measured = [_metrics(job) for job in jobs]
    grid = []
    for when in BROAD_TIMES_NS:
        subset = [p for p in measured if p["turnoff_start_ns"] == when]
        old = next(item for item in refined_grid if item["turnoff_start_ns"] == when)
        if len(subset) != 8:
            raise ValueError("broad-aperture case/time grid incomplete")
        error = max(old["maximum_capture_error_late_v"],
                    *(item["maximum_capture_error_late_v"] for item in subset))
        grid.append({"turnoff_start_ns": when,
                     "maximum_capture_error_late_v": error,
                     "target_met_in_ten_inspected_cases": error <= target_v,
                     "maximum_held_node_v": max(
                         old["maximum_held_node_v"],
                         *(item["maximum_held_node_v"] for item in subset))})
    passing = [item for item in grid if item["target_met_in_ten_inspected_cases"]]
    paired = [item for index, item in enumerate(passing)
              if (index > 0 and item["turnoff_start_ns"] -
                  passing[index - 1]["turnoff_start_ns"] < 0.011) or
              (index + 1 < len(passing) and
               passing[index + 1]["turnoff_start_ns"] -
               item["turnoff_start_ns"] < 0.011)]
    adjacent_pass = bool(paired)
    selected = (min(paired, key=lambda item: item["maximum_capture_error_late_v"])
                if paired else None)
    return {"grid": grid, "selected_turnoff_start_ns":
            selected["turnoff_start_ns"] if adjacent_pass and selected else None,
            "two_adjacent_grid_points_pass": adjacent_pass,
            "scope": "ten inspected TT phase cases at five discrete times; not a continuous aperture",
            "not_signoff": "ideal control/schematic TG; real driver, layout PEX and comparator unmeasured"}


def _dense_jobs(root: Path, broad_cases: list[Case], old: dict,
                inputs: dict, *, job_base: Path = OUTPUT) -> list[dict]:
    old_cases = {item["case"]: _case(item) for item in
                 old["jobs"]["fresh_holdout"]}
    anchors = [old_cases[name] for name in ("mha_96_a", "mha_118_a")]
    refined_times = {item["turnoff_start_ns"] for item in inputs["refined"]["grid"]}
    cases_and_times = [(case, when) for when in DENSE_TIMES_NS
                       if when not in BROAD_TIMES_NS for case in broad_cases]
    cases_and_times += [(case, when) for when in DENSE_TIMES_NS
                        if when not in refined_times for case in anchors]
    jobs = [_job(root, "aperture_5ps_grid", case, off_ns=when,
                 model=inputs["model"], pex=inputs["pex"],
                 job_base=job_base)
            for case, when in cases_and_times]
    if len(jobs) != 40:
        raise ValueError("expected 40 new five-picosecond aperture jobs")
    return jobs


def _dense_result(coarse: list[dict], dense: list[dict], refined_report: dict,
                  target_v: float) -> dict:
    broad_points = [_metrics(job) for job in coarse + dense
                    if job["case"] not in ("mha_96_a", "mha_118_a")]
    old_anchor_points = refined_report["anchors"] + refined_report["new_points"]
    new_anchor_points = [_metrics(job) for job in dense
                         if job["case"] in ("mha_96_a", "mha_118_a")]
    anchor_points = old_anchor_points + new_anchor_points
    grid = []
    for when in DENSE_TIMES_NS:
        broad = [p for p in broad_points if p["turnoff_start_ns"] == when]
        anchors = [p for p in anchor_points if p["turnoff_start_ns"] == when]
        if len(broad) != 8 or len(anchors) != 2:
            raise ValueError(f"incomplete ten-case dense aperture at {when} ns")
        all_points = broad + anchors
        maximum = max(p["maximum_capture_error_late_v"] for p in all_points)
        grid.append({"turnoff_start_ns": when,
                     "maximum_capture_error_late_v": maximum,
                     "target_met_in_ten_inspected_cases": maximum <= target_v,
                     "maximum_held_node_v": max(p["maximum_held_node_v"]
                                                for p in all_points)})
    runs: list[list[dict]] = []
    current: list[dict] = []
    for row in grid:
        if row["target_met_in_ten_inspected_cases"]:
            current.append(row)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    longest = max(runs, key=len, default=[])
    selected = longest[len(longest) // 2] if len(longest) >= 3 else None
    slopes = []
    for case in sorted({point["case"] for point in broad_points + anchor_points}):
        sequence = sorted((p for p in broad_points + anchor_points
                           if p["case"] == case),
                          key=lambda p: p["turnoff_start_ns"])
        for first, second in zip(sequence, sequence[1:]):
            if first["turnoff_start_ns"] not in DENSE_TIMES_NS or second[
                    "turnoff_start_ns"] not in DENSE_TIMES_NS:
                continue
            for column in range(4):
                delta = (second["columns"][column]["held_late_vdiff_v"] -
                         first["columns"][column]["held_late_vdiff_v"])
                slopes.append({"case": case, "column": column,
                               "from_ns": first["turnoff_start_ns"],
                               "to_ns": second["turnoff_start_ns"],
                               "held_differential_change_v": delta})
    return {"grid": grid,
            "longest_passing_sampled_window_ns":
                [longest[0]["turnoff_start_ns"],
                 longest[-1]["turnoff_start_ns"]] if longest else None,
            "passing_sampled_points": len(longest),
            "selected_turnoff_start_ns": selected["turnoff_start_ns"] if selected else None,
            "maximum_abs_5ps_neighbor_held_shift_v": max(
                (abs(item["held_differential_change_v"]) for item in slopes),
                default=None),
            "held_shift_by_neighbor": slopes,
            "continuous_aperture_proven": False,
            "scope": "ten inspected TT cases on a 5 ps discrete grid; no real clock-jitter waveform or ADC",
            "not_signoff": "sampled passing window is not a continuous physical aperture"}


def _training_cases(inputs: dict, config: Sky130MHAConfig) -> list[Case]:
    from scripts.run_post49_partition_full_tt import reachable_two_row_sums
    calibration = inputs["calibration"]
    if (len(calibration.get("jobs", [])) != 78 or
            calibration.get("reachable_partial_sums") != reachable_two_row_sums()):
        raise ValueError("78-case current-PEX 2+2 calibration required")
    targeted = _read(inputs["root"] / TARGETED)
    if (targeted.get("status") != "MEASURED_PARTITION_TT_DIAGNOSTIC" or
            targeted.get("pex_sha256") != inputs["pex_sha"] or
            len(targeted.get("jobs", [])) != 32):
        raise ValueError("32 inspected current-PEX hard cases required")
    cases = [_case(item) for item in calibration["jobs"] + targeted["jobs"]]
    for parent in idle_training_cases(config):
        cases.extend(split_case(_vectors(parent), "adjacent"))
    if len(cases) != 120 or len({case.name for case in cases}) != 120:
        raise ValueError("expected 120 unique held-node training cases")
    return cases


def _fresh_parents(inputs: dict, config: Sky130MHAConfig,
                   training: list[Case]) -> list[Case]:
    all_cases = mha_cases(config, 160)
    if len(all_cases) != 160:
        raise ValueError("MHA generator cannot reserve ranks 128..159")
    old = {item["case"]: item for item in inputs["old"]["jobs"]["fresh_holdout"]}
    for parent in all_cases[96:128]:
        for phase in split_case(_vectors(parent), "adjacent"):
            recorded = old.get(phase.name)
            if (recorded is None or _vectors(phase)["activation_x2"] !=
                    recorded["activation_x2"] or
                    _vectors(phase)["ternary_weights"] != recorded["ternary_weights"]):
                raise ValueError("MHA generator differs from the frozen 96..127 catalog")
    parents = all_cases[128:160]
    seen = {(case.acts, case.weights) for case in [*all_cases[:128], *training]}
    if (len(parents) != 32 or len({(case.acts, case.weights) for case in parents}) != 32 or
            any((case.acts, case.weights) in seen for case in parents)):
        raise ValueError("ranks 128..159 are not an untouched MHA cohort")
    return parents


def _pvt_cases(training_jobs: list[dict], model: dict) -> list[Case]:
    scored = []
    for job in training_jobs:
        distances = [_predict(model, job["phase"], column,
                              _held(job, column)[0])[1] for column in range(4)]
        scored.append((min(distances), job["case"], _case(job)))
    selected = []
    for phase in ("a", "b"):
        zero = next((case for _, _, case in scored
                     if case.name == f"idle_all_{phase}"), None)
        if zero is None:
            raise ValueError("idle-zero training case missing from PVT selection")
        selected.append(zero)
        selected.extend(case for _, _, case in sorted(scored)
                        if case.name.endswith(f"_{phase}") and case.name != zero.name)
    # Keep the three smallest-margin cases per phase plus both idle-zero cases.
    compact = []
    for phase in ("a", "b"):
        phase_cases = [case for case in selected if case.name.endswith(f"_{phase}")]
        compact.extend(phase_cases[:4])
    if len(compact) != 8 or len({case.name for case in compact}) != 8:
        raise ValueError("eight unique PVT training cases required")
    return compact


def _pvt_result(jobs: list[dict], model: dict, budget_v: float) -> dict:
    points = []
    for corner, vdd, temperature in PVT_POINTS:
        subset = [job for job in jobs if job["point"] == {
            "corner": corner, "vdd_v": vdd, "temperature_c": temperature}]
        errors, distances, capture = 0, [], []
        for job in subset:
            for column in range(4):
                value, _ = _held(job, column)
                predicted, distance = _predict(model, job["phase"], column, value)
                errors += int(predicted != job["integer_sums"][column])
                distances.append(distance)
            capture.append(_metrics(job)["maximum_capture_error_late_v"])
        points.append({"corner": corner, "vdd_v": vdd,
                       "temperature_c": temperature, "jobs": len(subset),
                       "decode_mismatches_with_frozen_tt_thresholds": errors,
                       "minimum_threshold_distance_v": min(distances),
                       "samples_below_error_budget": sum(x <= budget_v for x in distances),
                       "maximum_capture_error_late_v": max(capture)})
    plausible = all(item["jobs"] == 8 and
                    item["decode_mismatches_with_frozen_tt_thresholds"] == 0 and
                    item["samples_below_error_budget"] == 0 and
                    item["maximum_capture_error_late_v"] <= budget_v
                    for item in points)
    return {"status": "MEASURED_THREE_CORNER_TT_THRESHOLD_DIAGNOSTIC",
            "conclusion": ("THREE_POINT_DIAGNOSTIC_CANDIDATE" if plausible else
                           "BLOCKED_FROZEN_TT_THRESHOLD_OR_CAPTURE_AT_PVT"),
            "points": points,
            "not_signoff": "TT/SS/FF at nominal VDD/25C on eight training cases; no 27-point matrix, PVT recalibration, physical ADC or switch PEX"}


def _physical_state(root: Path) -> dict:
    base = root / "physical/sky130/wrapper"
    stem = "automx_ternary_cim_4x4"
    required = [base / f"{stem}.{suffix}" for suffix in ("gds", "lef", "lib", "spef")]
    missing = [str(path.relative_to(root)) for path in required
               if not path.is_file() or not path.stat().st_size]
    receipt = root / "results/receipts/wrapper_signoff.json"
    signed = _read(receipt) if receipt.is_file() else None
    return {"status": ("EXISTING_SIGNOFF_REQUIRES_SEPARATE_AUDIT"
                       if not missing and signed and signed.get("status") == "PASS"
                       else "BLOCKED_NO_VERIFIED_PHYSICAL_WRAPPER"),
            "missing_views": missing,
            "wrapper_signoff_status": signed.get("status") if signed else None,
            "scope": "inventory only; this TT schematic runner does not create or sign off wrapper views"}


def _job_namespace(previous: dict | None, pex_sha: str,
                   model_sha: str) -> Path:
    """Keep old-PEX decks intact while preserving legacy same-PEX resume."""
    tagged = OUTPUT / f"pex_{pex_sha[:12]}_model_{model_sha[:8]}"
    if (previous and previous.get("pex_sha256") == pex_sha and
            previous.get("model_sha256") == model_sha):
        selected = Path(previous.get("job_base", OUTPUT))
        if selected not in (OUTPUT, tagged):
            raise ValueError(f"unexpected prior job namespace: {selected}")
        return selected
    return tagged


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    inputs = _verified_inputs(root)
    inputs["root"] = root
    previous = _read(root / SUMMARY) if (root / SUMMARY).is_file() else None
    if not execute and previous and previous.get("status") not in ("PREPARED",):
        return previous  # A dry run must not replace measured aggregate evidence.
    job_base = _job_namespace(previous, inputs["pex_sha"], inputs["model_sha"])
    expected = {"broader_aperture": 40, "aperture_5ps_grid": 40,
                "held_node_training": 120,
                "fresh_mha_holdout": 64, "pvt_smoke": 16}
    report = {
        "format": "automx-cim-flow2-remaining-measurements-v1",
        "status": "RUNNING" if execute else "PREPARED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "scope": "current core PEX with schematic TG/ideal controls; 2+2 TT readout diagnostics, deterministic sensitivity, three-corner PVT smoke",
        "source_refined_sha256": inputs["refined_sha"],
        "source_stimulus_catalog": inputs["stimulus_provenance"],
        "source_calibration_sha256": _sha(root / CALIBRATION),
        "source_targeted_sha256": _sha(root / TARGETED),
        "requirements_sha256": _sha(root / "configs/sky130_post49_requirements.json"),
        "config_sha256": _sha(root / "configs/sky130_mha_tiny.json"),
        "pex_sha256": inputs["pex_sha"], "model_sha256": inputs["model_sha"],
        "job_base": job_base.as_posix(),
        "ngspice_version": inputs["version"],
        "script_sha256": _sha(Path(__file__)),
        "planned_new_spice_sims": sum(expected.values()),
        "expected_new_sims_by_group": expected,
        "groups": {name: {"status": "WAITING_FOR_PRIOR_GATE",
                          "planned_sims": count, "completed_sims": 0}
                   for name, count in expected.items()},
        "offline_sensitivity": {"status": "WAITING_FOR_HOLDOUT"},
        "continuous_aperture": {"status": "UNPROVEN_DISCRETE_GRID_ONLY"},
        "physical_adc_transfer": {"status": "BLOCKED_NO_PHYSICAL_SENSE_ADC"},
        "full_27_point_pvt": {"status": "BLOCKED_PDK_MODEL_MATRIX_UNAPPROVED"},
        "physical_measurements": {
            name: {"status": "NOT_RUN_REQUIRES_PHYSICAL_WRAPPER",
                   "reason": "no verified clocked sense/ADC wrapper circuit and matching physical views"}
            for name in ("switch_and_control_pex", "adc_transfer",
                         "transistor_noise_and_offset", "wrapper_drc",
                         "wrapper_lvs", "wrapper_pex", "wrapper_postlayout",
                         "wrapper_sta")},
        "physical_wrapper": _physical_state(root),
        "stage8_macro_bound": {"status": "BLOCKED_UNTIL_WRAPPER_SIGNOFF"},
        "frozen_decoder_sha256": None,
        "not_signoff": "no physical control driver, switch PEX, ADC, transistor noise, full PVT, wrapper views or top-level composite sign-off",
        "summary_path": str(SUMMARY),
    }
    if previous:
        prior_path = root / SUMMARY
        prior_sha = _sha(prior_path)
        archive = prior_path.with_name(f"summary.prior.{prior_sha[:12]}.json")
        if execute:
            if archive.is_file():
                if _sha(archive) != prior_sha:
                    raise ValueError(f"prior aggregate archive differs: {archive}")
            else:
                shutil.copy2(prior_path, archive)
        report["previous_aggregate"] = {
            "sha256": prior_sha,
            "archived_path": str(archive.relative_to(root)) if execute else None,
            "status": previous.get("status"),
            "timestamp_utc": previous.get("timestamp_utc"),
            "pex_sha256": previous.get("pex_sha256"),
            "job_base": previous.get("job_base", OUTPUT.as_posix()),
            "completed_sims_by_group": {
                name: group.get("completed_sims", 0)
                for name, group in previous.get("groups", {}).items()},
        }
    _snapshot(report)
    if not execute:
        return report
    stage = "preflight"
    try:
        executable = _ngspice(inputs["version"])
        config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
        stage = "broader_aperture"
        broad_cases = _select_broad(inputs["old"])
        broad_jobs = [_job(root, stage, case, off_ns=when,
                           model=inputs["model"], pex=inputs["pex"],
                           job_base=job_base)
                      for when in BROAD_TIMES_NS for case in broad_cases]
        _run_jobs(root, report, stage, broad_jobs, executable=executable,
                  inputs=inputs, timeout_s=timeout_s)
        broad = _broad_result(broad_jobs, inputs["refined"]["grid"],
                              inputs["budget_v"])
        report["groups"][stage]["analysis"] = broad
        _snapshot(report)
        if broad["selected_turnoff_start_ns"] is None:
            report["status"] = "BLOCKED_BROAD_APERTURE"
            report["blocked_at"] = stage
            _snapshot(report)
            return report

        stage = "aperture_5ps_grid"
        dense_jobs = _dense_jobs(root, broad_cases, inputs["old"], inputs,
                                 job_base=job_base)
        _run_jobs(root, report, stage, dense_jobs, executable=executable,
                  inputs=inputs, timeout_s=timeout_s)
        dense = _dense_result(broad_jobs, dense_jobs, inputs["refined"],
                              inputs["budget_v"])
        report["groups"][stage]["analysis"] = dense
        report["continuous_aperture"] = {
            "status": "UNPROVEN_DISCRETE_5PS_GRID_ONLY",
            "sampled_window_ns": dense["longest_passing_sampled_window_ns"],
            "maximum_abs_5ps_neighbor_held_shift_v":
                dense["maximum_abs_5ps_neighbor_held_shift_v"]}
        _snapshot(report)
        off_ns = dense["selected_turnoff_start_ns"]
        if off_ns is None:
            report["status"] = "BLOCKED_5PS_APERTURE_GRID"
            report["blocked_at"] = stage
            _snapshot(report)
            return report

        stage = "held_node_training"
        training_cases = _training_cases(inputs, config)
        training_jobs = [_job(root, stage, case, off_ns=off_ns,
                              model=inputs["model"], pex=inputs["pex"],
                              job_base=job_base)
                         for case in training_cases]
        _run_jobs(root, report, stage, training_jobs, executable=executable,
                  inputs=inputs, timeout_s=timeout_s)
        decoder = _train(training_jobs, inputs["budget_v"])
        report["groups"][stage]["analysis"] = decoder
        report["frozen_decoder_sha256"] = decoder["frozen_decoder_sha256"]
        report["selected_turnoff_start_ns"] = off_ns
        _snapshot(report)
        if not decoder["training_margin_candidate"]:
            report["status"] = "BLOCKED_HELD_NODE_TRAINING"
            report["blocked_at"] = stage
            _snapshot(report)
            return report
        if (previous and previous.get("frozen_decoder_sha256") and
                previous["frozen_decoder_sha256"] != decoder["frozen_decoder_sha256"]):
            raise ValueError("frozen decoder differs from a previous campaign run")

        stage = "fresh_mha_holdout"
        parents = _fresh_parents(inputs, config, training_cases)
        holdout_cases = [phase for parent in parents
                         for phase in split_case(_vectors(parent), "adjacent")]
        holdout_jobs = [_job(root, stage, case, off_ns=off_ns,
                             model=inputs["model"], pex=inputs["pex"],
                             job_base=job_base)
                        for case in holdout_cases]
        _run_jobs(root, report, stage, holdout_jobs, executable=executable,
                  inputs=inputs, timeout_s=timeout_s)
        report["groups"][stage]["frozen_decoder_sha256"] = decoder[
            "frozen_decoder_sha256"]
        held = _decode_holdout(holdout_jobs, parents, decoder, inputs["budget_v"])
        report["groups"][stage]["analysis"] = held
        _snapshot(report)

        requirements = _read(root / "configs/sky130_post49_requirements.json")
        report["offline_sensitivity"] = _sensitivity(holdout_jobs, decoder,
                                                       requirements)
        _snapshot(report)
        if not held["tt_holdout_candidate"]:
            report["status"] = "BLOCKED_FRESH_TT_HOLDOUT"
            report["blocked_at"] = stage
            _snapshot(report)
            return report

        stage = "pvt_smoke"
        cases = _pvt_cases(training_jobs, decoder)
        selected_names = {case.name for case in cases}
        reused_tt = [job for job in training_jobs if job["case"] in selected_names]
        if len(reused_tt) != 8 or {job["case"] for job in reused_tt} != selected_names:
            raise ValueError("eight measured TT training cases required for PVT reuse")
        pvt_jobs = [_job(root, stage, case, off_ns=off_ns,
                         model=inputs["model"], pex=inputs["pex"], point=point,
                         job_base=job_base)
                    for point in PVT_POINTS if point[0] != "tt" for case in cases]
        _run_jobs(root, report, stage, pvt_jobs, executable=executable,
                  inputs=inputs, timeout_s=timeout_s)
        report["groups"][stage]["reused_tt_training_jobs"] = [
            {"case": job["case"], "checkpoint": job["checkpoint"],
             "deck_sha256": job["deck_sha256"], "log_sha256": job["log_sha256"]}
            for job in reused_tt]
        pvt = _pvt_result(reused_tt + pvt_jobs, decoder, inputs["budget_v"])
        report["groups"][stage]["analysis"] = pvt
        report["status"] = (
            "MEASURED_READOUT_DIAGNOSTICS_NO_WRAPPER" if
            pvt["conclusion"] == "THREE_POINT_DIAGNOSTIC_CANDIDATE" and
            report["offline_sensitivity"]["conclusion"] ==
            "NO_ERRORS_AT_INJECTED_BUDGET_EXTREMES" else
            "BLOCKED_READOUT_SENSITIVITY_OR_PVT")
        _snapshot(report)
        return report
    except (OSError, ValueError, RuntimeError, TimeoutError, KeyError, TypeError) as error:
        report["status"] = "FAILED"
        report["blocked_at"] = stage
        report["failure"] = f"{type(error).__name__}: {error}"
        _snapshot(report)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items() if key not in
                      ("root", "groups")}, indent=2, ensure_ascii=False))
    print(f"Combined result: {args.root.resolve() / SUMMARY}")
    if result["status"] == "FAILED":
        raise SystemExit(1)
