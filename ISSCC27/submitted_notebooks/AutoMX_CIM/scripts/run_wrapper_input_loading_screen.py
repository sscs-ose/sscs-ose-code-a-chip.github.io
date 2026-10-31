"""PEX screen of extra bitline capacitance before choosing a 2+2 sense front end.

The old holdout chooses difficult cases; it is reused diagnostics, not an
independent validation set. The script keeps the calibration thresholds frozen
and never emits wrapper/ADC sign-off receipts or a physical GDS.
"""

from __future__ import annotations

import argparse
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

from automx_cim.physical.stage5 import CORE, core_pins, parse_spice_subckt_pins
from automx_cim.spice import parse_measurements
from scripts.run_core_candidate_pex import make_pex_deck
from scripts.run_core_pex_coverage import Case
from scripts.run_core_candidate_full_tt import _checkpoint, _expected
from scripts.run_post49_calibration_tt import analyze_feature_holdout
from scripts.run_post49_partition_full_tt import _budget

BASE = Path("results/sky130/wrapper_input_loading_screen")
CALIBRATION = Path("results/sky130/post49_partition_full_tt/calibration/measured.json")
HOLDOUT = Path("results/sky130/post49_partition_full_tt/holdout/measured.json")
STAGE5 = Path("results/receipts/physical/stage5_summary.json")
STAGE4_MANIFEST = Path("generated/sky130/spice/stage4_manifest.json")
BASELINE_FF = 800
PWM_UNIT_PS = 50


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _checked_path(root: Path, value: str) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else root / path).resolve()
    if not path.is_file() or not path.stat().st_size:
        raise FileNotFoundError(f"physical input missing: {path}")
    return path


def _evidence_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("missing project-relative evidence path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"missing or escaping evidence path: {relative}")
    return path


def audit_copied_evidence(root: str | Path) -> dict:
    """Check copied Stage-5 and 2+2 evidence without a local PDK or ngspice."""
    root = Path(root).resolve()
    calibration_path = _evidence_path(root, str(CALIBRATION))
    holdout_path = _evidence_path(root, str(HOLDOUT))
    calibration, holdout = _read(calibration_path), _read(holdout_path)
    summary = _read(_evidence_path(root, str(STAGE5)))
    if (summary.get("status") != "PASS" or
            calibration.get("format") != "automx-cim-post49-partition-calibration-v1" or
            holdout.get("format") != "automx-cim-post49-partition-holdout-v1" or
            calibration.get("status") != "MEASURED_2P2_LEVEL_SCREEN" or
            holdout.get("status") != "MEASURED_2P2_HOLDOUT_TT" or
            calibration.get("conclusion") != "TT_TRAINING_MARGIN_CANDIDATE" or
            holdout.get("conclusion") != "BLOCKED_HOLDOUT_DECODE_OR_MARGIN" or
            holdout.get("calibration_sha256") != _sha(calibration_path) or
            calibration.get("partition") != "adjacent" or
            holdout.get("partition") != "adjacent" or
            calibration.get("load_ff") != BASELINE_FF or
            holdout.get("load_ff") != BASELINE_FF or
            calibration.get("pwm_unit_ps") != PWM_UNIT_PS or
            holdout.get("pwm_unit_ps") != PWM_UNIT_PS or
            calibration.get("planned_sims") != calibration.get("completed_sims") or
            holdout.get("planned_sims") != holdout.get("completed_sims") or
            calibration.get("failures") or holdout.get("failures") or
            calibration.get("model_sha256") != holdout.get("model_sha256") or
            calibration.get("ngspice_version") != holdout.get("ngspice_version")):
        raise ValueError("copied 2+2 reports have incomplete or inconsistent provenance")
    contract = _evidence_path(root, "physical/sky130/macro/macro_contract.json")
    blackbox = _evidence_path(root, "rtl/automx_ternary_cim_4x4_core_blackbox.sv")
    if (summary.get("contract_sha256") != _sha(contract) or
            summary.get("views", {}).get("blackbox_rtl", {}).get("sha256") != _sha(blackbox)):
        raise ValueError("copied Stage-5 contract or blackbox differs from receipt")
    for filename, expected in summary.get("receipts", {}).items():
        receipt = _evidence_path(root, f"results/receipts/physical/{filename}")
        if _sha(receipt) != expected:
            raise ValueError(f"copied Stage-5 receipt differs: {filename}")
    views = summary.get("views", {})
    view_hashes = {}
    for kind, suffix in (("gds", ".gds"), ("lef", ".lef"),
                         ("extracted_spice", ".pex.spice")):
        local = _evidence_path(root, f"physical/sky130/macro/{CORE}{suffix}")
        actual = _sha(local)
        if actual != views.get(kind, {}).get("sha256"):
            raise ValueError(f"copied Stage-5 {kind} hash differs from receipt")
        view_hashes[kind] = actual
    pex_sha = view_hashes["extracted_spice"]
    if (calibration.get("pex_sha256") != pex_sha or
            holdout.get("pex_sha256") != pex_sha or
            calibration.get("target_budget_v") != _budget(root) or
            any(holdout["analysis"]["phases"][phase].get("error_budget_v") != _budget(root)
                for phase in ("a", "b"))):
        raise ValueError("PEX or frozen error budget differs from 2+2 reports")
    for name, report, expected_jobs, expected_parents in (
            ("calibration", calibration, 78, 39),
            ("holdout", holdout, 64, 32)):
        jobs = report.get("jobs", [])
        if len(jobs) != expected_jobs:
            raise ValueError(f"expected all {expected_jobs} paired {name} simulations")
        pairs: dict[str, set[str]] = {}
        for item in jobs:
            case = _case(item)
            phase = item.get("phase")
            if (phase not in ("a", "b") or
                    item.get("parent_case") != case.name.removesuffix(f"_{phase}")):
                raise ValueError(f"{name} parent/phase mismatch: {case.name}")
            pairs.setdefault(item["parent_case"], set()).add(phase)
            deck = _evidence_path(root, item["deck"])
            log = _evidence_path(root, item["log"])
            checkpoint = _evidence_path(root, item["checkpoint"])
            if _sha(deck) != item["deck_sha256"]:
                raise ValueError(f"{name} deck hash differs: {case.name}")
            saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                                pex_sha256=pex_sha, model_sha256=report["model_sha256"],
                                ngspice_version=report["ngspice_version"], log=log)
            if saved is None or saved["measurements_v"] != item.get("measurements_v"):
                raise ValueError(f"{name} log/checkpoint differs: {case.name}")
        if (len(pairs) != expected_parents or
                any(phases != {"a", "b"} for phases in pairs.values())):
            raise ValueError(f"{name} is missing a measured row-pair phase")
    jobs = holdout["jobs"]
    analysis = _analyze(calibration, jobs, _budget(root))
    published = holdout["analysis"]
    if (analysis["sample_count"] != 512 or
            analysis["decode_mismatches"] != published["partial_decode_mismatches"] or
            analysis["below_target_budget_samples"] != published["below_target_budget_samples"] or
            analysis["common_mode_outside_training_samples"] !=
            published["common_mode_outside_training_samples"]):
        raise ValueError("recomputed holdout result differs from published analysis")
    selected = select_parents(calibration, holdout)
    report = {
        "format": "automx-cim-copied-2p2-evidence-audit-v1",
        "status": "COPIED_EVIDENCE_INTEGRITY_VERIFIED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "local hash and result recomputation only; no local SPICE, ADC, wrapper or PVT measurement",
        "stage5_summary_sha256": _sha(root / STAGE5),
        "stage5_view_sha256": view_hashes,
        "calibration_sha256": _sha(calibration_path),
        "holdout_sha256": _sha(holdout_path),
        "model_sha256_from_server_receipts": holdout["model_sha256"],
        "stage5_receipts_verified": len(summary["receipts"]),
        "calibration_jobs_verified": len(calibration["jobs"]),
        "holdout_jobs_verified": len(jobs),
        "holdout_analysis": analysis,
        "selected_parents_for_loading_screen": selected,
        "selection_uses_old_holdout": True,
    }
    target = root / BASE / "copied_evidence_audit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _sources(root: Path) -> tuple[dict, dict, Path, Path, float]:
    calibration = _read(root / CALIBRATION)
    holdout = _read(root / HOLDOUT)
    summary = _read(root / STAGE5)
    manifest = _read(root / STAGE4_MANIFEST)
    if (calibration.get("format") != "automx-cim-post49-partition-calibration-v1" or
            holdout.get("format") != "automx-cim-post49-partition-holdout-v1" or
            calibration.get("status") != "MEASURED_2P2_LEVEL_SCREEN" or
            calibration.get("conclusion") != "TT_TRAINING_MARGIN_CANDIDATE" or
            holdout.get("status") != "MEASURED_2P2_HOLDOUT_TT" or
            holdout.get("calibration_sha256") != _sha(root / CALIBRATION) or
            calibration.get("failures") or holdout.get("failures") or
            calibration.get("planned_sims") != calibration.get("completed_sims") or
            holdout.get("planned_sims") != holdout.get("completed_sims")):
        raise ValueError("linked measured adjacent 2+2 calibration/holdout required")
    if calibration.get("partition") != "adjacent" or holdout.get("partition") != "adjacent":
        raise ValueError("adjacent two-row partition required")
    if len(holdout.get("jobs", [])) != 64:
        raise ValueError("complete 64-deck 2+2 holdout required")
    view = summary.get("views", {}).get("extracted_spice", {})
    pex = _checked_path(root, view.get("path", ""))
    model = _checked_path(root, manifest.get("model_library", ""))
    if (summary.get("status") != "PASS" or view.get("sha256") != _sha(pex) or
            calibration.get("pex_sha256") != _sha(pex) or
            holdout.get("pex_sha256") != _sha(pex) or
            calibration.get("model_sha256") != _sha(model) or
            holdout.get("model_sha256") != _sha(model) or
            parse_spice_subckt_pins(pex, f"{CORE}_pex") != core_pins()):
        raise ValueError("Stage-5 PEX or PDK model differs from measured 2+2 data")
    if calibration.get("ngspice_version") != holdout.get("ngspice_version"):
        raise ValueError("calibration/holdout ngspice versions differ")
    budget = _budget(root)
    if (calibration.get("load_ff") != BASELINE_FF or
            holdout.get("load_ff") != BASELINE_FF or
            calibration.get("pwm_unit_ps") != PWM_UNIT_PS or
            holdout.get("pwm_unit_ps") != PWM_UNIT_PS or
            calibration.get("target_budget_v") != budget or
            any(holdout["analysis"]["phases"][phase].get("error_budget_v") != budget
                for phase in ("a", "b"))):
        raise ValueError("2+2 measured stimulus or target budget differs")
    return calibration, holdout, model, pex, budget


def select_parents(calibration: dict, holdout: dict, count: int = 4) -> list[dict]:
    """Include low-margin and common-mode-extreme old holdout parents."""
    if count < 2:
        raise ValueError("at least two parents required")
    scores: dict[str, dict[str, float]] = {}
    for phase in ("a", "b"):
        training = calibration["analysis"]["phases"][phase]["threshold_training"]
        tested = holdout["analysis"]["phases"][phase]
        for column in tested["columns"]:
            index = int(column["column"])
            low, high = training["columns"][index]["training_common_mode_range_v"]
            for detail in column["details"]:
                name = str(detail["case"])
                if not name.endswith(f"_{phase}"):
                    raise ValueError("holdout phase/detail mismatch")
                parent = name.removesuffix(f"_{phase}")
                margin = float(detail["nearest_threshold_distance_equivalent_v"])
                cm = float(detail["common_mode_v"])
                if not all(math.isfinite(x) for x in (margin, cm, low, high)):
                    raise ValueError("nonfinite holdout voltage")
                item = scores.setdefault(parent, {"minimum_margin_v": math.inf,
                                                  "maximum_cm_extension_v": 0.0})
                item["minimum_margin_v"] = min(item["minimum_margin_v"], margin)
                item["maximum_cm_extension_v"] = max(
                    item["maximum_cm_extension_v"], max(low - cm, cm - high, 0.0))
    if len(scores) < count:
        raise ValueError("insufficient holdout parents for loading screen")
    by_margin = sorted(scores, key=lambda name: (scores[name]["minimum_margin_v"], name))
    by_cm = sorted(scores, key=lambda name: (-scores[name]["maximum_cm_extension_v"], name))
    selected = by_margin[:count - 1]
    if by_cm[0] not in selected:
        selected.append(by_cm[0])
    else:
        selected.append(next(name for name in by_margin if name not in selected))
    return [{"parent_case": name, **scores[name]} for name in selected]


def _case(job: dict) -> Case:
    case = Case(str(job["case"]),
                tuple(int(x) for x in job["activation_x2"]),
                tuple(tuple(int(x) for x in row) for row in job["ternary_weights"]))
    if list(case.sums) != job["integer_sums"]:
        raise ValueError(f"holdout arithmetic changed: {case.name}")
    return case


def _analyze(calibration: dict, jobs: list[dict], budget_v: float) -> dict:
    phases = {}
    for phase in ("a", "b"):
        subset = [job for job in jobs if job["phase"] == phase]
        frozen = calibration["analysis"]["phases"][phase]["threshold_training"]
        phases[phase] = analyze_feature_holdout(frozen, subset, budget_v)
    details = [detail for phase in phases.values() for col in phase["columns"]
               for detail in col["details"]]
    return {"sample_count": len(details),
            "decode_mismatches": sum(phase["decode_mismatches"] for phase in phases.values()),
            "below_target_budget_samples": sum(
                phase["samples_below_error_budget"] for phase in phases.values()),
            "common_mode_outside_training_samples": sum(
                phase["common_mode_outside_training_samples"] for phase in phases.values()),
            "minimum_threshold_distance_v": min(
                detail["nearest_threshold_distance_equivalent_v"] for detail in details)}


def run(root: str | Path, *, execute: bool = False,
        loads_ff: tuple[int, ...] = (800, 820, 850),
        max_parents: int = 4, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if (not loads_ff or loads_ff[0] != BASELINE_FF or
            sorted(set(loads_ff)) != list(loads_ff) or
            any(not BASELINE_FF <= load <= 2000 for load in loads_ff) or
            max_parents < 2 or timeout_s <= 0):
        raise ValueError("loads must be sorted unique 800..2000 fF; count/timeout positive")
    calibration, holdout, model, pex, budget = _sources(root)
    selected = select_parents(calibration, holdout, max_parents)
    names = {item["parent_case"] for item in selected}
    old_jobs = [job for job in holdout["jobs"] if job["parent_case"] in names]
    if len(old_jobs) != 2 * len(names) or any(job.get("phase") not in ("a", "b")
                                            for job in old_jobs):
        raise ValueError("selected parents lack both measured phases")
    for job in old_jobs:
        case = _case(job)
        old_deck = _checked_path(root, job["deck"])
        expected = make_pex_deck(case, model, pex, BASELINE_FF, PWM_UNIT_PS)
        if old_deck.read_text(encoding="utf-8") != expected or _sha(old_deck) != job["deck_sha256"]:
            raise ValueError(f"old holdout deck changed: {case.name}")
        if set(job.get("measurements_v", {})) != set(_expected()):
            raise ValueError(f"old holdout measurements incomplete: {case.name}")
    folder = root / BASE
    folder.mkdir(parents=True, exist_ok=True)
    outcomes = [{"load_ff": BASELINE_FF, "status": "REUSED_MEASURED_HOLDOUT",
                 "analysis": _analyze(calibration, old_jobs, budget)}]
    jobs = []
    for load in loads_ff[1:]:
        point = folder / f"c{load}ff"
        point.mkdir(parents=True, exist_ok=True)
        for original in old_jobs:
            case = _case(original)
            deck = point / f"{case.name}.spice"
            content = make_pex_deck(case, model, pex, load, PWM_UNIT_PS)
            if deck.exists() and deck.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"refusing to overwrite changed deck: {deck}")
            deck.write_text(content, encoding="utf-8")
            jobs.append({"load_ff": load, "case": case.name,
                         "phase": original["phase"], "parent_case": original["parent_case"],
                         "integer_sums": list(case.sums),
                         "deck": str(deck.relative_to(root)), "deck_sha256": _sha(deck),
                         "log": str((point / f"{case.name}.log").relative_to(root)),
                         "checkpoint": str((point / f"{case.name}.receipt.json").relative_to(root))})
    failures = []
    ngspice = shutil.which("ngspice") if execute else None
    if execute:
        if not ngspice:
            failures.append("ngspice not on PATH")
        else:
            version = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                     timeout=15, check=False)
            if (version.stdout + version.stderr).strip() != holdout["ngspice_version"]:
                failures.append("ngspice version differs from holdout")
    for item in jobs if execute and not failures else []:
        deck, log, checkpoint = (root / item[key] for key in ("deck", "log", "checkpoint"))
        saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                            pex_sha256=_sha(pex), model_sha256=_sha(model),
                            ngspice_version=holdout["ngspice_version"], log=log)
        if saved is not None:
            item["measurements_v"] = saved["measurements_v"]
            item["log_sha256"] = saved["log_sha256"]
            item["reused_checkpoint"] = True
            continue
        try:
            process = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                     cwd=deck.parent, text=True, capture_output=True,
                                     timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired:
            failures.append(f"{item['case']} at {item['load_ff']} fF timed out")
            break
        output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        values = parse_measurements(output, _expected())
        if (process.returncode or set(values) != set(_expected()) or
                not all(math.isfinite(value) for value in values.values())):
            failures.append(f"incomplete PEX result: {item['case']} at {item['load_ff']} fF")
            break
        item["measurements_v"] = values
        item["log_sha256"] = _sha(log)
        checkpoint.write_text(json.dumps({
            "status": "PASS", "deck_sha256": item["deck_sha256"],
            "pex_sha256": _sha(pex), "model_sha256": _sha(model),
            "ngspice_version": holdout["ngspice_version"],
            "log_sha256": item["log_sha256"], "measurements_v": values,
        }, indent=2) + "\n", encoding="utf-8")
    if execute and not failures:
        for load in loads_ff[1:]:
            subset = [item for item in jobs if item["load_ff"] == load]
            outcomes.append({"load_ff": load, "status": "MEASURED_PEX_DIAGNOSTIC",
                             "analysis": _analyze(calibration, subset, budget)})
    result = {"format": "automx-cim-wrapper-input-loading-screen-v1",
              "status": "FAIL" if failures else "MEASURED_LOADING_DIAGNOSTIC" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "same passive-core PEX, increased lumped bitline capacitance; no sample/hold switch, charge injection, ADC, noise, PVT or wrapper layout",
              "holdout_reused_for_selection": True,
              "calibration_sha256": _sha(root / CALIBRATION),
              "holdout_sha256": _sha(root / HOLDOUT),
              "pex_sha256": _sha(pex), "model_sha256": _sha(model),
              "loads_ff": list(loads_ff), "target_budget_v": budget,
              "selected_parents": selected, "outcomes": outcomes,
              "planned_new_sims": len(jobs),
              "completed_new_sims": sum("measurements_v" in item for item in jobs),
              "jobs": jobs, "failures": failures}
    target = folder / ("attempt.json" if failures else
                       "measured.json" if execute else "prepared.json")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--audit-copied", action="store_true",
                        help="verify copied reports/views/logs without local PDK or ngspice")
    parser.add_argument("--loads-ff", type=int, nargs="+", default=[800, 820, 850])
    parser.add_argument("--max-parents", type=int, default=4)
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    if args.audit_copied:
        if args.run:
            parser.error("--audit-copied cannot be combined with --run")
        print(json.dumps(audit_copied_evidence(args.root), indent=2))
        raise SystemExit(0)
    report = run(args.root, execute=args.run, loads_ff=tuple(args.loads_ff),
                 max_parents=args.max_parents, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in report.items() if key != "jobs"},
                     indent=2))
    if report["status"] == "FAIL":
        raise SystemExit(1)
