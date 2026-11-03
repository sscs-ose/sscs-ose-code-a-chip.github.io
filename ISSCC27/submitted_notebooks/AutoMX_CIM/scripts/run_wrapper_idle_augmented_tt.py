"""Test an idle-column calibration repair at the measured 820 fF TT point.

Add five predetermined no-activity training parents to the existing 820 fF
training set, freeze new thresholds, then test MHA ranks 96..127. Prior MHA
ranks 64..95 informed this design change and are never reused as the new
holdout. This is a passive-core diagnostic, not physical ADC/wrapper proof.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.config import Sky130MHAConfig
from scripts.run_core_candidate_full_tt import _checkpoint
from scripts.run_core_candidate_pex import make_pex_deck
from scripts.run_core_pex_coverage import Case, mha_cases
from scripts.run_post49_partition_full_tt import _calibration_analysis, _holdout_analysis
from scripts.run_wrapper_input_loading_screen import _case, _read, _sources
from scripts.run_wrapper_load_full_tt import (
    OUTPUT as PRIOR_OUTPUT, SCREEN, TARGETED, _measure, _phase_jobs,
)
import scripts.run_wrapper_load_full_tt as prior_runner

OUTPUT = Path("results/sky130/wrapper_idle_augmented_tt")
LOAD_FF = 820
PWM_UNIT_PS = 50


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def idle_training_cases(config: Sky130MHAConfig) -> list[Case]:
    """Exercise every idle column with active neighbouring columns, plus all idle."""
    bases = mha_cases(config, 4)
    cases = []
    for column, base in enumerate(bases):
        weights = tuple(tuple(0 if col == column else base.weights[row][col]
                              for col in range(4)) for row in range(4))
        cases.append(Case(f"idle_c{column}", base.acts, weights))
    cases.append(Case("idle_all", bases[0].acts,
                      tuple((0, 0, 0, 0) for _ in range(4))))
    return cases


def fresh_holdout_cases(config: Sky130MHAConfig,
                        prior_vectors: set[tuple]) -> list[Case]:
    all_mha = mha_cases(config, 128)
    fresh = all_mha[96:128]
    if (len(fresh) != 32 or
            [case.name for case in fresh] !=
            [f"mha_{index:02d}" for index in range(96, 128)] or
            any((case.acts, case.weights) in prior_vectors for case in fresh) or
            len({(case.acts, case.weights) for case in fresh}) != 32):
        raise ValueError("MHA ranks 96..127 are not an unseen 32-parent set")
    return fresh


def _verified_previous(root: Path, model: Path, pex: Path,
                       budget_v: float) -> dict:
    path = root / PRIOR_OUTPUT / f"c{LOAD_FF}ff/measured.json"
    report = _read(path)
    jobs = report.get("jobs", {})
    version = report.get("ngspice_version")
    expected_groups = {"targeted_training": 32, "level_training": 78,
                       "fresh_holdout": 64}
    checks = {
        "report format": report.get("format") == "automx-cim-wrapper-load-full-tt-v1",
        "measurement status": report.get("status") == "MEASURED_TT_LOAD_DIAGNOSTIC",
        "820 fF load": report.get("load_ff") == LOAD_FF,
        "50 ps PWM unit": report.get("pwm_unit_ps") == PWM_UNIT_PS,
        "target budget": report.get("target_budget_v") == budget_v,
        "PEX hash": report.get("pex_sha256") == _sha(pex),
        "PDK model hash": report.get("model_sha256") == _sha(model),
        "input-loading screen hash": (root / SCREEN).is_file() and
        report.get("screen_sha256") == _sha(root / SCREEN),
        "targeted 2+2 report hash": (root / TARGETED).is_file() and
        report.get("targeted_sha256") == _sha(root / TARGETED),
        "820 fF runner script hash": report.get("script_sha256") ==
        _sha(Path(prior_runner.__file__)),
        "174 completed simulations": report.get("planned_sims") ==
        report.get("completed_sims") == 174,
        "ngspice version": isinstance(version, str) and bool(version),
        "three complete job groups": isinstance(jobs, dict) and
        set(jobs) == set(expected_groups) and
        all(isinstance(jobs[name], list) and len(jobs[name]) == count
            for name, count in expected_groups.items()),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("complete hash-linked 820 fF measurement required; failed: "
                         + ", ".join(failed)
                         + ". Refresh the changed upstream report(s), then rerun "
                           "run_wrapper_load_full_tt.py before this idle diagnostic.")
    for group in jobs.values():
        for item in group:
            case = _case(item)
            deck, log, checkpoint = (root / item[key] for key in
                                     ("deck", "log", "checkpoint"))
            if (not deck.is_file() or _sha(deck) != item["deck_sha256"] or
                    deck.read_text(encoding="utf-8") != make_pex_deck(
                        case, model, pex, LOAD_FF, PWM_UNIT_PS)):
                raise ValueError(f"old 820 fF deck differs: {case.name}")
            saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                                pex_sha256=_sha(pex), model_sha256=_sha(model),
                                ngspice_version=version, log=log)
            if saved is None or saved["measurements_v"] != item.get("measurements_v"):
                raise ValueError(f"old 820 fF checkpoint differs: {case.name}")
    old_training = _calibration_analysis(jobs["level_training"],
                                         jobs["targeted_training"], budget_v)
    if old_training != report.get("training_analysis"):
        raise ValueError("old 820 fF training summary differs from jobs")
    return report


def _summary(training: dict | None, holdout: dict | None) -> dict:
    result = {}
    if training:
        result["training_minimum_gap_v"] = min(
            training["phases"][phase]["threshold_training"]["minimum_gap_equivalent_v"]
            for phase in ("a", "b"))
    if holdout:
        result.update({
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
    return result


def _measure_new(root: Path, jobs: list[dict], ngspice: str, version: str,
                 model_sha: str, pex_sha: str, timeout_s: int,
                 recover_stale: bool) -> None:
    """Preserve stale evidence in this new output tree before reusing runner logic."""
    if recover_stale:
        allowed = (root / OUTPUT).resolve()
        for item in jobs:
            deck, log, checkpoint = (root / item[key] for key in
                                     ("deck", "log", "checkpoint"))
            saved = _checkpoint(checkpoint, deck_sha256=item["deck_sha256"],
                                pex_sha256=pex_sha, model_sha256=model_sha,
                                ngspice_version=version, log=log)
            if saved is not None:
                continue
            if (not deck.parent.is_relative_to(allowed) or
                    log.parent != deck.parent or checkpoint.parent != deck.parent or
                    log.name != f"{item['case']}.log" or
                    checkpoint.name != f"{item['case']}.receipt.json"):
                raise ValueError(f"unexpected idle-diagnostic evidence path: {deck}")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            archived = []
            for old in (log, checkpoint):
                if old.exists():
                    candidate = old.with_name(f"{old.name}.stale.{stamp}")
                    if candidate.exists():
                        raise FileExistsError(f"stale archive name exists: {candidate}")
                    old.rename(candidate)
                    archived.append(str(candidate.relative_to(root)))
            if archived:
                item["archived_stale_artifacts"] = archived
    _measure(root, jobs, ngspice, version, model_sha, pex_sha, timeout_s)


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600,
        recover_stale: bool = False) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    _, _, model, pex, budget = _sources(root)
    previous = _verified_previous(root, model, pex, budget)
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    idle_parents = idle_training_cases(config)
    prior_vectors = {(case.acts, case.weights) for case in mha_cases(config, 96)}
    prior_vectors.update((case.acts, case.weights) for case in idle_parents)
    holdout_parents = fresh_holdout_cases(config, prior_vectors)
    folder = root / OUTPUT / f"c{LOAD_FF}ff"
    idle_jobs = _phase_jobs(root, folder / "idle_training", idle_parents,
                            model, pex, LOAD_FF)
    holdout_jobs = _phase_jobs(root, folder / "fresh_holdout", holdout_parents,
                               model, pex, LOAD_FF)
    version = previous["ngspice_version"]
    ngspice = shutil.which("ngspice") if execute else None
    if execute:
        if not ngspice:
            raise FileNotFoundError("ngspice not on PATH")
        actual = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                timeout=15, check=False)
        if (actual.stdout + actual.stderr).strip() != version:
            raise ValueError("ngspice version differs from previous 820 fF run")
        _measure_new(root, idle_jobs, ngspice, version, _sha(model), _sha(pex),
                     timeout_s, recover_stale)
    old_jobs = previous["jobs"]
    training = (_calibration_analysis(old_jobs["level_training"] + idle_jobs,
                                      old_jobs["targeted_training"], budget)
                if execute else None)
    if execute and training["training_margin_candidate"]:
        _measure_new(root, holdout_jobs, ngspice, version, _sha(model), _sha(pex),
                     timeout_s, recover_stale)
    holdout = (_holdout_analysis(holdout_jobs, {"analysis": training},
                                 holdout_parents, budget)
               if execute and training["training_margin_candidate"] else None)
    status = ("PREPARED" if not execute else "BLOCKED_TRAINING" if holdout is None
              else "MEASURED_TT_IDLE_AUGMENTATION_DIAGNOSTIC")
    conclusion = ("NOT_MEASURED" if not execute else
                  "BLOCKED_TRAINING_OVERLAP_OR_MARGIN" if holdout is None else
                  "TT_HOLDOUT_CANDIDATE" if holdout["tt_holdout_candidate"] else
                  "BLOCKED_HOLDOUT_DECODE_OR_MARGIN")
    report = {
        "format": "automx-cim-wrapper-idle-augmented-tt-v1",
        "status": status, "conclusion": conclusion,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "820 fF TT passive-core: five added idle training parents and fresh MHA 96..127 holdout; no sample/hold, ADC, noise, PVT or wrapper",
        "load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
        "target_budget_v": budget, "pex_sha256": _sha(pex),
        "model_sha256": _sha(model), "ngspice_version": version,
        "previous_820ff_report_sha256": _sha(root / PRIOR_OUTPUT / f"c{LOAD_FF}ff/measured.json"),
        "script_sha256": _sha(Path(__file__)),
        "reused_training_sims": len(old_jobs["targeted_training"]) +
                                len(old_jobs["level_training"]),
        "planned_new_sims": len(idle_jobs) + len(holdout_jobs),
        "completed_new_sims": sum("measurements_v" in item for item in
                                  idle_jobs + holdout_jobs),
        "reused_new_checkpoints": sum(item.get("reused_checkpoint", False)
                                      for item in idle_jobs + holdout_jobs),
        "archived_stale_artifacts": sum(len(item.get("archived_stale_artifacts", []))
                                        for item in idle_jobs + holdout_jobs),
        "idle_parent_cases": [{"case": case.name, "activation_x2": list(case.acts),
                               "ternary_weights": [list(row) for row in case.weights],
                               "integer_sums": list(case.sums)} for case in idle_parents],
        "fresh_holdout_parent_names": [case.name for case in holdout_parents],
        "summary": _summary(training, holdout),
        "training_analysis": training, "fresh_holdout_analysis": holdout,
        "jobs": {"idle_training": idle_jobs, "fresh_holdout": holdout_jobs},
        "not_signoff": "new training and holdout at TT only; physical input range, ADC/noise/PVT and wrapper remain unmeasured",
    }
    target = folder / ("measured.json" if holdout is not None else
                       "blocked.json" if execute else "prepared.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    parser.add_argument("--recover-stale", action="store_true")
    args = parser.parse_args()
    report = run(args.root, execute=args.run, timeout_s=args.timeout_s,
                 recover_stale=args.recover_stale)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("jobs", "training_analysis", "fresh_holdout_analysis",
                                     "idle_parent_cases", "fresh_holdout_parent_names")},
                     indent=2))
