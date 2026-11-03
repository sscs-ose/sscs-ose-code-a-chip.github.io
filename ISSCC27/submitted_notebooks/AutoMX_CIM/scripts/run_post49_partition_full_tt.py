"""Full signed-level TT screen and fresh holdout for the 2+2-row read.

The calibration phase adds one deterministic pattern for each of the 39
reachable two-row sums to *each* physical row pair and column. The 16 prior
hard-case measurements add within-level variation. A separate phase tests 32
previously uninspected MHA patterns, without retuning the frozen thresholds.
Neither phase proves ADC noise, continuous aperture, PVT or wrapper sign-off.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from itertools import product
import json
import math
from pathlib import Path
import shutil
import subprocess

from automx_cim.circuit.sky130 import E2M1_MAGNITUDES_X2
from automx_cim.config import Sky130MHAConfig
from automx_cim.spice import parse_measurements
from scripts.analyze_post49_decoder_architectures import _read_reports
from scripts.run_core_candidate_full_tt import (
    LOAD_FF, PWM_UNIT_PS, _checkpoint, _digest, _expected, _provenance,
    analyze_transfer,
)
from scripts.run_core_candidate_pex import make_pex_deck
from scripts.run_core_pex_coverage import Case, mha_cases
from scripts.run_post49_calibration_tt import (
    analyze_feature_holdout, analyze_feature_training,
)
from scripts.run_post49_row_partition import select_hard_cases, split_case


ROOT = Path(__file__).resolve().parents[1]
BASE = Path("results/sky130/post49_partition_full_tt")
TARGETED = Path("results/sky130/post49_row_partition/adjacent/measured.json")
FEATURE = "differential_v"
PARTITION = "adjacent"


def reachable_two_row_sums() -> list[int]:
    signed = set(E2M1_MAGNITUDES_X2) | {-value for value in E2M1_MAGNITUDES_X2}
    return sorted({a + b for a in signed for b in signed})


def fresh_holdout_cases(config: Sky130MHAConfig, prior_jobs: list[dict]) -> list[Case]:
    """Reserve MHA ranks 32–63, rejecting any prior 4-row vector."""
    previous = {(tuple(int(value) for value in item["activation_x2"]),
                 tuple(tuple(int(value) for value in row)
                       for row in item["ternary_weights"]))
                for item in prior_jobs}
    cases = mha_cases(config, 64)[32:64]
    if (len(cases) != 32 or
            [case.name for case in cases] !=
            [f"mha_{index:02d}" for index in range(32, 64)] or
            any((case.acts, case.weights) in previous for case in cases) or
            len({(case.acts, case.weights) for case in cases}) != 32):
        raise ValueError("MHA ranks 32–63 are not an independent 2+2 holdout")
    return cases


def calibration_cases() -> list[Case]:
    """Use both row pairs and vary legal weight decompositions by column."""
    signed = sorted(set(E2M1_MAGNITUDES_X2) | {-x for x in E2M1_MAGNITUDES_X2})
    solutions: dict[int, list[tuple[int, int, int, int]]] = {}
    for a, b, wa, wb in product(signed, signed, (-1, 0, 1), (-1, 0, 1)):
        total = a * wa + b * wb
        solutions.setdefault(total, []).append((a, b, wa, wb))
    cases = []
    for total in reachable_two_row_sums():
        ranked = sorted(solutions[total], key=lambda item: (
            -(abs(item[0] * item[2]) + abs(item[1] * item[3])),
            -(item[2] != 0) - (item[3] != 0),
            item))
        first = ranked[0]
        second = next((item for item in ranked[1:]
                       if item[:2] != first[:2]), first)
        acts = (first[0], first[1], second[0], second[1])
        a_options = [(wa, wb) for wa, wb in product((-1, 0, 1), repeat=2)
                     if acts[0] * wa + acts[1] * wb == total]
        b_options = [(wa, wb) for wa, wb in product((-1, 0, 1), repeat=2)
                     if acts[2] * wa + acts[3] * wb == total]
        weights = tuple(tuple((a_options[col % len(a_options)] +
                               b_options[(col + 1) % len(b_options)])[row]
                              for col in range(4)) for row in range(4))
        name = f"p2cal_{'p' if total >= 0 else 'n'}{abs(total):02d}"
        case = Case(name, acts, weights)
        a, b = split_case({"case": name, "activation_x2": list(acts),
                           "ternary_weights": [list(row) for row in weights],
                           "integer_sums": list(case.sums)}, PARTITION)
        if a.sums != (total,) * 4 or b.sums != (total,) * 4:
            raise ValueError(f"two-row generator lost signed sum {total}")
        cases.append(case)
    return cases


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _within(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"evidence path escapes project: {relative}")
    return target


def _verify_jobs(root: Path, jobs: list[dict], *, model: Path,
                 pex: Path, version: str) -> None:
    for item in jobs:
        deck = _within(root, item["deck"])
        log = _within(root, item["log"])
        checkpoint = _within(root, item["checkpoint"])
        if not deck.is_file() or _digest(deck) != item["deck_sha256"]:
            raise ValueError(f"deck changed or missing: {item['case']}")
        saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                            pex_sha256=_digest(pex), model_sha256=_digest(model),
                            ngspice_version=version, log=log)
        if saved is None or saved["measurements_v"] != item.get("measurements_v"):
            raise ValueError(f"measurement/checkpoint changed: {item['case']}")


def _verify_targeted(root: Path, reports: dict, hashes: dict,
                     model: Path, pex: Path) -> dict:
    path = root / TARGETED
    measured = _read(path)
    selected = select_hard_cases(reports)
    jobs = measured.get("jobs", [])
    if (measured.get("format") != "automx-cim-post49-row-partition-v1" or
            measured.get("status") != "MEASURED_PARTITION_TT_DIAGNOSTIC" or
            measured.get("partition") != PARTITION or
            measured.get("selected_parents") != selected or
            measured.get("input_report_sha256") != hashes or
            measured.get("pex_sha256") != _digest(pex) or
            measured.get("model_sha256") != _digest(model) or
            measured.get("ngspice_version") != reports["cell49"]["ngspice_version"] or
            measured.get("planned_sims") != 32 or
            measured.get("completed_sims") != 32 or
            measured.get("failures") or len(jobs) != 32 or
            not measured.get("analysis", {}).get(
                "both_partial_transfers_ordered_in_selected_set")):
        raise ValueError("complete ordered 4.12d adjacent PEX screen required")
    expected = [(parent, phase, case)
                for parent in selected
                for phase, case in zip(("a", "b"), split_case(parent, PARTITION))]
    for item, (parent, phase, case) in zip(jobs, expected):
        if (item.get("case") != case.name or item.get("phase") != phase or
                item.get("parent_case") != parent["case"] or
                item.get("activation_x2") != list(case.acts) or
                item.get("ternary_weights") != [list(row) for row in case.weights] or
                item.get("integer_sums") != list(case.sums)):
            raise ValueError(f"4.12d selected case changed: {case.name}")
        if _within(root, item["deck"]).read_text(encoding="utf-8") != make_pex_deck(
                case, model, pex, LOAD_FF, PWM_UNIT_PS):
            raise ValueError(f"4.12d stimulus differs from expected: {case.name}")
    _verify_jobs(root, jobs, model=model, pex=pex,
                 version=measured["ngspice_version"])
    recalculated = {phase: analyze_transfer([item for item in jobs
                                             if item["phase"] == phase])
                    for phase in ("a", "b")}
    if measured["analysis"]["phases"] != recalculated:
        raise ValueError("4.12d cached transfer differs from raw measurements")
    return measured


def _budget(root: Path) -> float:
    acceptance = _read(root / "configs/sky130_post49_requirements.json")["acceptance"]
    terms = (float(acceptance["maximum_input_referred_offset_abs_v"]),
             float(acceptance["maximum_input_referred_noise_rms_v"]),
             float(acceptance["maximum_reference_threshold_error_abs_v"]),
             float(acceptance["maximum_aperture_induced_shift_abs_v"]))
    if not all(math.isfinite(value) and value >= 0 for value in terms):
        raise ValueError("finite nonnegative prototype error-budget terms required")
    return terms[0] + 5 * terms[1] + terms[2] + terms[3]


def _prepare_and_run(root: Path, folder: Path, parents: list[Case],
                     model: Path, pex: Path, *, execute: bool,
                     timeout_s: int, expected_version: str) -> tuple[list[dict], list[str], str | None]:
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for parent in parents:
        original = {"case": parent.name, "activation_x2": list(parent.acts),
                    "ternary_weights": [list(row) for row in parent.weights],
                    "integer_sums": list(parent.sums)}
        for phase, case in zip(("a", "b"), split_case(original, PARTITION)):
            deck = folder / f"{case.name}.spice"
            deck.write_text(make_pex_deck(case, model, pex, LOAD_FF, PWM_UNIT_PS),
                            encoding="utf-8")
            jobs.append({"case": case.name, "parent_case": parent.name,
                         "phase": phase, "activation_x2": list(case.acts),
                         "ternary_weights": [list(row) for row in case.weights],
                         "integer_sums": list(case.sums),
                         "deck": str(deck.relative_to(root)),
                         "deck_sha256": _digest(deck),
                         "log": str((folder / f"{case.name}.log").relative_to(root)),
                         "checkpoint": str((folder / f"{case.name}.receipt.json").relative_to(root))})
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = None
    if ngspice:
        result = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                timeout=15, check=False)
        version = (result.stdout + result.stderr).strip()
        if version != expected_version:
            failures.append("ngspice version changed since 4.12d")
    for index, item in enumerate(jobs if execute and not failures else [], start=1):
        deck, log, checkpoint = (_within(root, item[key])
                                 for key in ("deck", "log", "checkpoint"))
        saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                            pex_sha256=_digest(pex), model_sha256=_digest(model),
                            ngspice_version=version, log=log)
        if saved:
            values = saved["measurements_v"]
            item["reused_checkpoint"] = True
        else:
            if log.is_file():
                log.unlink()  # Only this runner's exact generated log path.
            try:
                result = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                        cwd=folder, text=True, capture_output=True,
                                        timeout=timeout_s, check=False)
            except subprocess.TimeoutExpired:
                failures.append(f"{item['case']}: ngspice timeout after {timeout_s}s")
                break
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if (result.returncode or set(values) != set(_expected()) or
                    not all(math.isfinite(value) for value in values.values())):
                failures.append(f"{item['case']}: incomplete ngspice result; see {log}")
                break
            checkpoint.write_text(json.dumps({
                "status": "PASS", "deck_sha256": item["deck_sha256"],
                "pex_sha256": _digest(pex), "model_sha256": _digest(model),
                "ngspice_version": version, "log_sha256": _digest(log),
                "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        item["measurements_v"] = values
        if index == 1 or index % 10 == 0 or index == len(jobs):
            print(f"2+2 {folder.name}: {index}/{len(jobs)} ({item['case']})", flush=True)
    return jobs, failures, version


def _calibration_analysis(jobs: list[dict], targeted_jobs: list[dict],
                          budget_v: float) -> dict:
    levels = reachable_two_row_sums()
    phases = {}
    for phase in ("a", "b"):
        combined = ([item for item in targeted_jobs if item["phase"] == phase] +
                    [item for item in jobs if item["phase"] == phase])
        transfer = analyze_transfer(combined)
        transfer["scope_warning"] = "55 selected/calibration TT PEX cases in this physical row pair only; not full pattern or ADC/PVT sign-off"
        training = analyze_feature_training(combined, FEATURE)
        if any(col["sum_levels"] != levels for col in training["columns"]):
            raise ValueError(f"phase {phase} did not cover all 39 sums in every column")
        phases[phase] = {"case_count": len(combined), "transfer": transfer,
                         "threshold_training": training}
    candidate = all(
        phases[phase]["transfer"]["transfer_observation"] == "ORDERED_IN_MEASURED_SET"
        and phases[phase]["threshold_training"]["minimum_gap_equivalent_v"] > 2 * budget_v
        for phase in ("a", "b"))
    return {"phases": phases, "minimum_required_gap_v": 2 * budget_v,
            "training_margin_candidate": candidate,
            "scope_warning": "39 signed levels per phase plus 16 selected prior cases at TT PEX. One synthetic case per level is not full pattern, noise or PVT coverage."}


def run_calibration(root: str | Path, *, execute: bool = False,
                    timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    reports, hashes = _read_reports(root)
    _, _, model, pex = _provenance(root)
    targeted = _verify_targeted(root, reports, hashes, model, pex)
    parents = calibration_cases()
    folder = root / BASE / "calibration"
    jobs, failures, version = _prepare_and_run(
        root, folder, parents, model, pex, execute=execute, timeout_s=timeout_s,
        expected_version=targeted["ngspice_version"])
    complete = sum("measurements_v" in item for item in jobs)
    budget = _budget(root)
    analysis = (_calibration_analysis(jobs, targeted["jobs"], budget)
                if execute and not failures and complete == len(jobs) else None)
    report = {"format": "automx-cim-post49-partition-calibration-v1",
              "status": "FAIL" if failures else "MEASURED_2P2_LEVEL_SCREEN" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "partition": PARTITION,
              "targeted_sha256": _digest(root / TARGETED),
              "input_report_sha256": hashes,
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "script_sha256": _digest(Path(__file__)),
              "ngspice_version": version, "load_ff": LOAD_FF,
              "pwm_unit_ps": PWM_UNIT_PS, "target_budget_v": budget,
              "reachable_partial_sums": reachable_two_row_sums(),
              "planned_sims": len(jobs), "completed_sims": complete,
              "reused_checkpoints": sum(item.get("reused_checkpoint", False)
                                        for item in jobs),
              "conclusion": ("NOT_MEASURED" if analysis is None else
                             "TT_TRAINING_MARGIN_CANDIDATE" if analysis["training_margin_candidate"]
                             else "BLOCKED_TRAINING_OVERLAP_OR_MARGIN"),
              "analysis": analysis, "failures": failures,
              "parent_cases": [{"case": p.name, "activation_x2": list(p.acts),
                                "ternary_weights": [list(row) for row in p.weights],
                                "integer_sums": list(p.sums)} for p in parents],
              "jobs": jobs,
              "not_signoff": "TT passive-core level screen only; no physical ADC, noise/PVT or wrapper proof"}
    target = folder / ("measured.json" if execute else "prepared.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _verified_calibration(root: Path, targeted: dict, hashes: dict,
                          model: Path, pex: Path) -> dict:
    path = root / BASE / "calibration/measured.json"
    report = _read(path)
    parents = calibration_cases()
    jobs = report.get("jobs", [])
    if (report.get("format") != "automx-cim-post49-partition-calibration-v1" or
            report.get("status") != "MEASURED_2P2_LEVEL_SCREEN" or
            report.get("conclusion") != "TT_TRAINING_MARGIN_CANDIDATE" or
            report.get("partition") != PARTITION or report.get("failures") or
            report.get("targeted_sha256") != _digest(root / TARGETED) or
            report.get("input_report_sha256") != hashes or
            report.get("pex_sha256") != _digest(pex) or
            report.get("model_sha256") != _digest(model) or
            report.get("script_sha256") != _digest(Path(__file__)) or
            report.get("ngspice_version") != targeted["ngspice_version"] or
            report.get("reachable_partial_sums") != reachable_two_row_sums() or
            report.get("planned_sims") != 2 * len(parents) or
            report.get("completed_sims") != 2 * len(parents) or
            len(jobs) != 2 * len(parents) or
            report.get("parent_cases") != [{
                "case": parent.name, "activation_x2": list(parent.acts),
                "ternary_weights": [list(row) for row in parent.weights],
                "integer_sums": list(parent.sums)} for parent in parents] or
            [item["case"] for item in jobs] != [case.name
                for parent in parents for case in split_case({
                    "case": parent.name, "activation_x2": list(parent.acts),
                    "ternary_weights": [list(row) for row in parent.weights],
                    "integer_sums": list(parent.sums)}, PARTITION)]):
        raise ValueError("complete, hash-matched 2+2 level screen required")
    expected = [(parent, phase, case) for parent in parents
                for phase, case in zip(("a", "b"), split_case({
                    "case": parent.name, "activation_x2": list(parent.acts),
                    "ternary_weights": [list(row) for row in parent.weights],
                    "integer_sums": list(parent.sums)}, PARTITION))]
    for item, (parent, phase, case) in zip(jobs, expected):
        if (item.get("parent_case") != parent.name or item.get("phase") != phase or
                item.get("activation_x2") != list(case.acts) or
                item.get("ternary_weights") != [list(row) for row in case.weights] or
                item.get("integer_sums") != list(case.sums) or
                _within(root, item["deck"]).read_text(encoding="utf-8") !=
                make_pex_deck(case, model, pex, LOAD_FF, PWM_UNIT_PS)):
            raise ValueError(f"2+2 calibration vector/deck changed: {case.name}")
    _verify_jobs(root, jobs, model=model, pex=pex,
                 version=report["ngspice_version"])
    recomputed = _calibration_analysis(jobs, targeted["jobs"], _budget(root))
    if report.get("analysis") != recomputed or not recomputed["training_margin_candidate"]:
        raise ValueError("2+2 calibration summary differs from measurements")
    return report


def _holdout_analysis(jobs: list[dict], training: dict,
                      parents: list[Case], budget_v: float) -> dict:
    phases = {}
    predicted: dict[tuple[str, int, str], dict[str, int]] = {}
    for phase in ("a", "b"):
        phase_jobs = [item for item in jobs if item["phase"] == phase]
        frozen = training["analysis"]["phases"][phase]["threshold_training"]
        tested = analyze_feature_holdout(frozen, phase_jobs, budget_v)
        phases[phase] = tested
        for column in tested["columns"]:
            for detail in column["details"]:
                key = (detail["case"].removesuffix(f"_{phase}"),
                       column["column"], detail["time"])
                predicted.setdefault(key, {})[phase] = detail["predicted_sum"]
    comparisons = []
    for parent in parents:
        for col in range(4):
            for time in ("t19", "t21"):
                pair = predicted[(parent.name, col, time)]
                comparisons.append({"case": parent.name, "column": col, "time": time,
                                    "expected_sum": parent.sums[col],
                                    "predicted_sum": pair["a"] + pair["b"],
                                    "predicted_partial_a": pair["a"],
                                    "predicted_partial_b": pair["b"]})
    errors = sum(item["expected_sum"] != item["predicted_sum"]
                 for item in comparisons)
    partial_errors = sum(phase["decode_mismatches"] for phase in phases.values())
    near_threshold = sum(phase["samples_below_error_budget"]
                         for phase in phases.values())
    cm_outside = sum(phase["common_mode_outside_training_samples"]
                     for phase in phases.values())
    return {"phases": phases, "combined": {"samples": len(comparisons),
                                           "decode_mismatches": errors,
                                           "details": comparisons},
            "partial_decode_mismatches": partial_errors,
            "below_target_budget_samples": near_threshold,
            "common_mode_outside_training_samples": cm_outside,
            "tt_holdout_candidate": (errors == 0 and partial_errors == 0 and
                                     near_threshold == 0 and cm_outside == 0),
            "scope_warning": "32 new MHA parents at two TT samples; ideal frozen thresholds only. No physical ADC, continuous aperture, noise statistics or PVT sign-off."}


def run_holdout(root: str | Path, *, execute: bool = False,
                timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    reports, hashes = _read_reports(root)
    _, _, model, pex = _provenance(root)
    targeted = _verify_targeted(root, reports, hashes, model, pex)
    training = _verified_calibration(root, targeted, hashes, model, pex)
    prior = [*reports["cell49"]["jobs"], *reports["calibration"]["jobs"],
             *reports["old_holdout"]["jobs"], *training["parent_cases"]]
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    parents = fresh_holdout_cases(config, prior)
    folder = root / BASE / "holdout"
    jobs, failures, version = _prepare_and_run(
        root, folder, parents, model, pex, execute=execute, timeout_s=timeout_s,
        expected_version=targeted["ngspice_version"])
    complete = sum("measurements_v" in item for item in jobs)
    analysis = (_holdout_analysis(jobs, training, parents, _budget(root))
                if execute and not failures and complete == len(jobs) else None)
    report = {"format": "automx-cim-post49-partition-holdout-v1",
              "status": "FAIL" if failures else "MEASURED_2P2_HOLDOUT_TT" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "partition": PARTITION,
              "calibration_sha256": _digest(root / BASE / "calibration/measured.json"),
              "targeted_sha256": _digest(root / TARGETED),
              "input_report_sha256": hashes,
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "script_sha256": _digest(Path(__file__)), "ngspice_version": version,
              "load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
              "planned_sims": len(jobs), "completed_sims": complete,
              "reused_checkpoints": sum(item.get("reused_checkpoint", False)
                                        for item in jobs),
              "conclusion": ("NOT_MEASURED" if analysis is None else
                             "TT_HOLDOUT_CANDIDATE" if analysis["tt_holdout_candidate"]
                             else "BLOCKED_HOLDOUT_DECODE_OR_MARGIN"),
              "analysis": analysis, "failures": failures,
              "parent_cases": [{"case": p.name, "activation_x2": list(p.acts),
                                "ternary_weights": [list(row) for row in p.weights],
                                "integer_sums": list(p.sums)} for p in parents],
              "jobs": jobs,
              "not_signoff": "Fresh TT passive-core holdout only; no physical ADC, noise/PVT or wrapper proof"}
    target = folder / ("measured.json" if execute else "prepared.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--mode", choices=("calibration", "holdout"),
                        default="calibration")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    selected_run = run_calibration if args.mode == "calibration" else run_holdout
    result = selected_run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("jobs", "analysis", "parent_cases")}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)
