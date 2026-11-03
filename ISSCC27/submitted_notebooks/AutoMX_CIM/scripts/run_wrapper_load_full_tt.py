"""Recharacterize one screened bitline load using the unchanged passive-core PEX.

Replay the 16 targeted training parents, all 39 two-row signed levels, and a
previously uninspected MHA 64..95 holdout. This is a TT passive-core diagnostic,
not a physical sample/hold, ADC, wrapper, noise, aperture or PVT sign-off.
The original 800 fF receipts and decks are never modified.
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

from automx_cim.config import Sky130MHAConfig
from automx_cim.spice import parse_measurements
from scripts.run_core_candidate_full_tt import _checkpoint, _expected
from scripts.run_core_candidate_pex import make_pex_deck
from scripts.run_core_pex_coverage import Case, mha_cases
from scripts.run_post49_partition_full_tt import (
    _calibration_analysis, _holdout_analysis, calibration_cases,
)
from scripts.run_post49_row_partition import split_case
from scripts.run_wrapper_input_loading_screen import _case, _read, _sources

SCREEN = Path("results/sky130/wrapper_input_loading_screen/measured.json")
TARGETED = Path("results/sky130/post49_row_partition/adjacent/measured.json")
OUTPUT = Path("results/sky130/wrapper_load_full_tt")
PWM_UNIT_PS = 50


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _screened_load(root: Path, load_ff: int, pex: Path,
                   model: Path, original_holdout: dict, budget_v: float) -> dict:
    screen = _read(root / SCREEN)
    if (screen.get("format") != "automx-cim-wrapper-input-loading-screen-v1" or
            screen.get("status") != "MEASURED_LOADING_DIAGNOSTIC" or
            screen.get("failures") or
            screen.get("target_budget_v") != budget_v or
            screen.get("pex_sha256") != _sha(pex) or
            screen.get("model_sha256") != _sha(model) or
            screen.get("calibration_sha256") != _sha(
                root / "results/sky130/post49_partition_full_tt/calibration/measured.json") or
            screen.get("holdout_sha256") != _sha(
                root / "results/sky130/post49_partition_full_tt/holdout/measured.json")):
        raise ValueError("measured input-loading screen must match original PEX/model/reports")
    outcomes = [entry for entry in screen.get("outcomes", [])
                if entry.get("load_ff") == load_ff and
                entry.get("status") == "MEASURED_PEX_DIAGNOSTIC"]
    if (len(outcomes) != 1 or outcomes[0]["analysis"]["sample_count"] != 64 or
            outcomes[0]["analysis"]["decode_mismatches"] != 0 or
            outcomes[0]["analysis"]["below_target_budget_samples"] != 0):
        raise ValueError(f"load {load_ff} fF lacks a complete measured screen")
    jobs = [item for item in screen.get("jobs", []) if item["load_ff"] == load_ff]
    if len(jobs) != 8 or screen.get("completed_new_sims") != screen.get("planned_new_sims"):
        raise ValueError("loading-screen jobs are incomplete")
    source_jobs = {item["case"]: item for item in original_holdout["jobs"]}
    for item in jobs:
        if item["case"] not in source_jobs:
            raise ValueError(f"screen case absent from linked holdout: {item['case']}")
        deck, log, receipt = (root / item[key] for key in ("deck", "log", "checkpoint"))
        if (not deck.is_file() or _sha(deck) != item["deck_sha256"] or
                deck.read_text(encoding="utf-8") != make_pex_deck(
                    _case(source_jobs[item["case"]]), model, pex, load_ff, PWM_UNIT_PS)):
            raise ValueError(f"screen deck differs: {item['case']}")
        saved = _checkpoint(receipt, deck_sha256=item["deck_sha256"],
                            pex_sha256=_sha(pex), model_sha256=_sha(model),
                            ngspice_version=original_holdout["ngspice_version"], log=log)
        if saved is None or saved["measurements_v"] != item.get("measurements_v"):
            raise ValueError(f"screen measurement differs: {item['case']}")
    return screen


def _fresh_parents(root: Path, prior_names: set[str]) -> list[Case]:
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    parents = mha_cases(config, 96)[64:96]
    if (len(parents) != 32 or [case.name for case in parents] !=
            [f"mha_{index:02d}" for index in range(64, 96)] or
            any(case.name in prior_names for case in parents) or
            len({(case.acts, case.weights) for case in parents}) != len(parents)):
        raise ValueError("MHA ranks 64..95 are not a fresh 32-parent holdout")
    return parents


def _phase_jobs(root: Path, folder: Path, parents: list[Case], model: Path,
                pex: Path, load_ff: int) -> list[dict]:
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for parent in parents:
        source = {"case": parent.name, "activation_x2": list(parent.acts),
                  "ternary_weights": [list(row) for row in parent.weights],
                  "integer_sums": list(parent.sums)}
        for phase, case in zip(("a", "b"), split_case(source, "adjacent")):
            deck = folder / f"{case.name}.spice"
            content = make_pex_deck(case, model, pex, load_ff, PWM_UNIT_PS)
            if deck.exists() and deck.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"refusing changed diagnostic deck: {deck}")
            deck.write_text(content, encoding="utf-8")
            jobs.append({"case": case.name, "parent_case": parent.name,
                         "phase": phase, "activation_x2": list(case.acts),
                         "ternary_weights": [list(row) for row in case.weights],
                         "integer_sums": list(case.sums),
                         "deck": str(deck.relative_to(root)), "deck_sha256": _sha(deck),
                         "log": str((folder / f"{case.name}.log").relative_to(root)),
                         "checkpoint": str((folder / f"{case.name}.receipt.json").relative_to(root))})
    return jobs


def _measure(root: Path, jobs: list[dict], ngspice: str, version: str,
             model_sha: str, pex_sha: str, timeout_s: int,
             recover_stale: bool = False) -> None:
    for index, item in enumerate(jobs, 1):
        deck, log, checkpoint = (root / item[key] for key in
                                 ("deck", "log", "checkpoint"))
        saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                            pex_sha256=pex_sha, model_sha256=model_sha,
                            ngspice_version=version, log=log)
        if saved is not None:
            item["measurements_v"] = saved["measurements_v"]
            item["reused_checkpoint"] = True
        else:
            if log.exists() or checkpoint.exists():
                if not recover_stale:
                    raise FileExistsError(
                        f"stale log/checkpoint needs inspection: {deck}; "
                        "rerun with --recover-stale to preserve and replace only this runner's files")
                output_root = (root / OUTPUT).resolve()
                if (not deck.parent.is_relative_to(output_root) or
                        log.parent != deck.parent or checkpoint.parent != deck.parent or
                        log.name != f"{item['case']}.log" or
                        checkpoint.name != f"{item['case']}.receipt.json"):
                    raise ValueError(f"refusing to archive unexpected evidence path: {deck}")
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                archived = []
                for old in (log, checkpoint):
                    if old.exists():
                        candidate = old.with_name(f"{old.name}.stale.{stamp}")
                        if candidate.exists():
                            raise FileExistsError(f"stale archive name already exists: {candidate}")
                        old.rename(candidate)
                        archived.append(str(candidate.relative_to(root)))
                item["archived_stale_artifacts"] = archived
            result = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                    cwd=deck.parent, text=True, capture_output=True,
                                    timeout=timeout_s, check=False)
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if (result.returncode or set(values) != set(_expected()) or
                    not all(math.isfinite(x) for x in values.values())):
                raise RuntimeError(f"incomplete ngspice result: {deck}")
            item["measurements_v"] = values
            checkpoint.write_text(json.dumps({
                "status": "PASS", "deck_sha256": item["deck_sha256"],
                "pex_sha256": pex_sha, "model_sha256": model_sha,
                "ngspice_version": version, "log_sha256": _sha(log),
                "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        if index == 1 or index % 10 == 0 or index == len(jobs):
            print(f"{deck.parent.name}: {index}/{len(jobs)} {item['case']}", flush=True)


def run(root: str | Path, *, load_ff: int = 820, execute: bool = False,
        timeout_s: int = 600, recover_stale: bool = False) -> dict:
    root = Path(root).resolve()
    if not 801 <= load_ff <= 2000 or timeout_s <= 0:
        raise ValueError("candidate load must be 801..2000 fF and timeout positive")
    original_cal, original_holdout, model, pex, budget = _sources(root)
    screen = _screened_load(root, load_ff, pex, model, original_holdout, budget)
    targeted = _read(root / TARGETED)
    if (targeted.get("status") != "MEASURED_PARTITION_TT_DIAGNOSTIC" or
            targeted.get("partition") != "adjacent" or
            targeted.get("pex_sha256") != _sha(pex) or
            targeted.get("model_sha256") != _sha(model) or
            targeted.get("ngspice_version") != original_holdout.get("ngspice_version") or
            len(targeted.get("selected_parents", [])) != 16):
        raise ValueError("original 16 targeted parents lack matching provenance")
    targeted_parents = [_case(item) for item in targeted["selected_parents"]]
    level_parents = calibration_cases()
    prior_names = ({item["case"] for item in targeted["selected_parents"]} |
                   {item["case"] for item in original_cal["parent_cases"]} |
                   {item["case"] for item in original_holdout["parent_cases"]})
    holdout_parents = _fresh_parents(root, prior_names)
    folder = root / OUTPUT / f"c{load_ff}ff"
    stages = {
        "targeted_training": _phase_jobs(root, folder / "targeted_training",
                                         targeted_parents, model, pex, load_ff),
        "level_training": _phase_jobs(root, folder / "level_training",
                                      level_parents, model, pex, load_ff),
        "fresh_holdout": _phase_jobs(root, folder / "fresh_holdout",
                                     holdout_parents, model, pex, load_ff),
    }
    version = original_holdout["ngspice_version"]
    ngspice = shutil.which("ngspice") if execute else None
    if execute:
        if not ngspice:
            raise FileNotFoundError("ngspice not on PATH")
        actual = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                timeout=15, check=False)
        if (actual.stdout + actual.stderr).strip() != version:
            raise ValueError("ngspice version differs from 800 fF evidence")
        for name in ("targeted_training", "level_training"):
            _measure(root, stages[name], ngspice, version, _sha(model), _sha(pex),
                     timeout_s, recover_stale=recover_stale)
    training = (_calibration_analysis(stages["level_training"],
                                      stages["targeted_training"], budget)
                if execute else None)
    if execute and training["training_margin_candidate"]:
        _measure(root, stages["fresh_holdout"], ngspice, version,
                 _sha(model), _sha(pex), timeout_s, recover_stale=recover_stale)
    frozen = {"analysis": training} if training else None
    holdout = (_holdout_analysis(stages["fresh_holdout"], frozen,
                                 holdout_parents, budget)
               if execute and training["training_margin_candidate"] else None)
    status = ("PREPARED" if not execute else "BLOCKED_TRAINING" if holdout is None
              else "MEASURED_TT_LOAD_DIAGNOSTIC")
    conclusion = ("NOT_MEASURED" if not execute else
                  "BLOCKED_TRAINING_OVERLAP_OR_MARGIN" if holdout is None else
                  "TT_HOLDOUT_CANDIDATE" if holdout["tt_holdout_candidate"] else
                  "BLOCKED_HOLDOUT_DECODE_OR_MARGIN")
    summary = {}
    if training:
        summary["training_minimum_gap_v"] = min(
            training["phases"][phase]["threshold_training"]["minimum_gap_equivalent_v"]
            for phase in ("a", "b"))
    if holdout:
        summary.update({
            "holdout_combined_decode_mismatches": holdout["combined"]["decode_mismatches"],
            "holdout_partial_decode_mismatches": holdout["partial_decode_mismatches"],
            "holdout_below_target_budget_samples": holdout["below_target_budget_samples"],
            "holdout_common_mode_outside_training_samples":
                holdout["common_mode_outside_training_samples"],
            "holdout_minimum_threshold_distance_v": min(
                detail["nearest_threshold_distance_equivalent_v"]
                for phase in ("a", "b") for column in holdout["phases"][phase]["columns"]
                for detail in column["details"]),
        })
    report = {
        "format": "automx-cim-wrapper-load-full-tt-v1", "status": status,
        "conclusion": conclusion,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "one TT passive-core load; 16 targeted training parents, 39 level training parents, 32 new MHA holdout parents; no physical sample/hold, ADC, noise, PVT or wrapper",
        "load_ff": load_ff, "pwm_unit_ps": PWM_UNIT_PS, "target_budget_v": budget,
        "pex_sha256": _sha(pex), "model_sha256": _sha(model),
        "ngspice_version": version, "screen_sha256": _sha(root / SCREEN),
        "source_calibration_sha256": _sha(root / "results/sky130/post49_partition_full_tt/calibration/measured.json"),
        "source_holdout_sha256": _sha(root / "results/sky130/post49_partition_full_tt/holdout/measured.json"),
        "targeted_sha256": _sha(root / TARGETED), "script_sha256": _sha(Path(__file__)),
        "planned_sims": sum(len(jobs) for jobs in stages.values()),
        "completed_sims": sum("measurements_v" in item for jobs in stages.values()
                              for item in jobs),
        "reused_checkpoints": sum(item.get("reused_checkpoint", False)
                                  for jobs in stages.values() for item in jobs),
        "archived_stale_artifacts": sum(len(item.get("archived_stale_artifacts", []))
                                        for jobs in stages.values() for item in jobs),
        "summary": summary,
        "training_analysis": training, "fresh_holdout_analysis": holdout,
        "jobs": stages,
        "not_signoff": "TT passive-core load recharacterization only; new analog front-end and 27-point PVT still required",
    }
    target = folder / ("measured.json" if status == "MEASURED_TT_LOAD_DIAGNOSTIC"
                       else "prepared.json" if status == "PREPARED" else "blocked.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--load-ff", type=int, default=820)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--recover-stale", action="store_true",
                        help="archive this runner's stale log/checkpoint, then rerun that case")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    report = run(args.root, load_ff=args.load_ff, execute=args.run,
                 timeout_s=args.timeout_s, recover_stale=args.recover_stale)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("jobs", "training_analysis", "fresh_holdout_analysis")},
                     indent=2))
