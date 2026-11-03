#!/usr/bin/env python3
"""Independent Flow-2 TT recovery after the observed 128..159 holdout failed.

Ranks 160..191 extend training. Ranks 192..223 are reserved before any new
measurement and cannot enter decoder selection. All jobs use the frozen 2.100 ns
sample time and the same PEX/model as the source campaign. This is schematic
readout evidence, not a physical ADC or wrapper sign-off.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.config import Sky130MHAConfig  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402
from scripts.run_core_pex_coverage import mha_cases  # noqa: E402

OUTPUT = campaign.OUTPUT / "recovery"
BUDGET_V = 0.0008
TRAIN_RANKS = (160, 192)
VALIDATION_RANKS = (192, 224)


def _identity(case) -> tuple:
    return case.acts, case.weights


def _phases(parents: list) -> list:
    return [phase for parent in parents
            for phase in campaign.split_case(campaign._vectors(parent), "adjacent")]


def _cohorts(config: Sky130MHAConfig, original_jobs: list[dict]) -> tuple[list, list]:
    all_parents = mha_cases(config, VALIDATION_RANKS[1])
    if len(all_parents) != VALIDATION_RANKS[1]:
        raise ValueError("MHA generator did not produce 224 parents")
    training = all_parents[slice(*TRAIN_RANKS)]
    validation = all_parents[slice(*VALIDATION_RANKS)]
    prior = all_parents[:TRAIN_RANKS[0]]
    if ([p.name for p in training] != [f"mha_{i}" for i in range(*TRAIN_RANKS)] or
            [p.name for p in validation] != [f"mha_{i}" for i in range(*VALIDATION_RANKS)]):
        raise ValueError("MHA rank numbering changed")
    identities = [_identity(case) for case in prior + training + validation]
    if len(set(identities)) != len(identities):
        raise ValueError("new MHA cohort duplicates an earlier parent")
    old_phase = {_identity(campaign._case(job)) for job in original_jobs}
    earlier_phase = {_identity(phase) for phase in _phases(prior)}
    new_training_phase = {_identity(phase) for phase in _phases(training)}
    new_validation_phase = {_identity(phase) for phase in _phases(validation)}
    if (len(new_training_phase) != 64 or len(new_validation_phase) != 64 or
            (new_training_phase & (old_phase | earlier_phase)) or
            (new_validation_phase & (old_phase | earlier_phase | new_training_phase))):
        raise ValueError("training and reserved validation stimuli are not disjoint")
    return training, validation


def _reservation(parents: list) -> dict:
    vectors = [campaign._vectors(case) for case in _phases(parents)]
    return {"parent_names": [case.name for case in parents],
            "phase_vectors_sha256": campaign._canonical_sha(vectors),
            "phase_count": len(vectors)}


def _source(root: Path) -> tuple[dict, dict, list[dict], str]:
    source_path = root / campaign.SUMMARY
    original = campaign._read(source_path)
    if (original.get("format") != "automx-cim-flow2-remaining-measurements-v1" or
            original.get("status") != "BLOCKED_FRESH_TT_HOLDOUT" or
            original.get("blocked_at") != "fresh_mha_holdout" or
            original.get("script_sha256") != campaign._sha(Path(campaign.__file__)) or
            original.get("selected_turnoff_start_ns") != 2.100 or
            original.get("offline_sensitivity", {}).get("combined_budget_v") != BUDGET_V):
        raise ValueError("complete frozen failed Flow-2 campaign required")
    inputs = campaign._verified_inputs(root)
    for field in ("pex_sha", "model_sha", "version"):
        report_field = {"pex_sha": "pex_sha256", "model_sha": "model_sha256",
                        "version": "ngspice_version"}[field]
        if original.get(report_field) != inputs[field]:
            raise ValueError(f"source {report_field} differs from current inputs")
    if (original.get("source_refined_sha256") != inputs["refined_sha"] or
            original.get("config_sha256") != campaign._sha(root / "configs/sky130_mha_tiny.json") or
            original.get("requirements_sha256") != campaign._sha(root / "configs/sky130_post49_requirements.json")):
        raise ValueError("source aperture, config or requirements changed")
    for group, count in (("held_node_training", 120), ("fresh_mha_holdout", 64)):
        item = original["groups"][group]
        if (item.get("status") != "MEASURED_TT_DIAGNOSTIC" or
                item.get("planned_sims") != count or item.get("completed_sims") != count or
                len(item.get("jobs", [])) != count):
            raise ValueError(f"incomplete source group {group}")
        stage6._verified_jobs(root, original, group)
    old_jobs = original["groups"]["held_node_training"]["jobs"]
    old_decoder = campaign._train(old_jobs, BUDGET_V)
    if (old_decoder != original["groups"]["held_node_training"]["analysis"] or
            old_decoder["frozen_decoder_sha256"] != original["frozen_decoder_sha256"]):
        raise ValueError("original training decoder cannot be reproduced")
    old_holdout = original["groups"]["fresh_mha_holdout"]["analysis"]
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    old_parents = campaign._fresh_parents(inputs, config,
                                          [campaign._case(job) for job in old_jobs])
    if (campaign._decode_holdout(original["groups"]["fresh_mha_holdout"]["jobs"],
                                 old_parents, old_decoder, BUDGET_V) != old_holdout):
        raise ValueError("original failed holdout cannot be reproduced")
    if (old_holdout.get("tt_holdout_candidate") is not False or
            old_holdout.get("below_error_budget_samples", 0) +
            old_holdout.get("common_mode_outside_training_samples", 0) <= 0):
        raise ValueError("source holdout failure is missing")
    return original, inputs, old_jobs, campaign._sha(source_path)


def _write_report(path: Path, report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    campaign._save(path, report)


def _event(folder: Path, message: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "history.log").open("a", encoding="utf-8") as stream:
        stream.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")


def _run_jobs(root: Path, path: Path, report: dict, name: str,
              cases: list, inputs: dict, executable: str, timeout_s: int) -> list[dict]:
    jobs = [campaign._job(root, name, case, off_ns=2.100,
                          model=inputs["model"], pex=inputs["pex"],
                          job_base=path.parent.relative_to(root))
            for case in cases]
    group = {"status": "RUNNING", "planned_sims": len(jobs),
             "completed_sims": 0, "jobs": jobs}
    report["groups"][name] = group
    _write_report(path, report)
    _event(path.parent, f"START {name} {len(jobs)} jobs")
    for index, job in enumerate(jobs, 1):
        campaign._measure(root, job, executable=executable,
                          version=inputs["version"], pex_sha=inputs["pex_sha"],
                          model_sha=inputs["model_sha"], timeout_s=timeout_s)
        group["completed_sims"] = index
        _write_report(path, report)
        _event(path.parent, f"DONE {name} {index}/{len(jobs)} {job['case']} "
               f"log_sha256={job['log_sha256']}")
        if index == 1 or index % 10 == 0 or index == len(jobs):
            print(f"{name}: {index}/{len(jobs)} {job['case']}", flush=True)
    group["status"] = "MEASURED_TT_DIAGNOSTIC"
    _write_report(path, report)
    _event(path.parent, f"COMPLETE {name} {len(jobs)}/{len(jobs)}")
    return jobs


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    original, inputs, old_jobs, source_sha = _source(root)
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    extension, validation = _cohorts(config, old_jobs)
    script_sha = campaign._sha(Path(__file__))
    folder = root / OUTPUT / f"source_{source_sha[:12]}_runner_{script_sha[:12]}"
    path = folder / "summary.json"
    reservation = {"training": _reservation(extension),
                   "validation": _reservation(validation)}
    if path.is_file():
        previous = campaign._read(path)
        if (previous.get("source_campaign_sha256") != source_sha or
                previous.get("script_sha256") != script_sha or
                previous.get("cohort_reservation") != reservation or
                previous.get("pex_sha256") != inputs["pex_sha"]):
            raise FileExistsError(f"recovery summary differs: {path}")
        if not execute or previous["status"] in (
                "BLOCKED_EXTENDED_TRAINING", "BLOCKED_NEW_TT_HOLDOUT",
                "BLOCKED_READOUT_SENSITIVITY_OR_PVT",
                "MEASURED_RECOVERY_READOUT_DIAGNOSTICS_NO_WRAPPER"):
            return previous
    report = {"format": "automx-cim-flow2-recovery-v1",
              "status": "PREPARED" if not execute else "RUNNING",
              "source_campaign": campaign.SUMMARY.as_posix(),
              "source_campaign_sha256": source_sha,
              "script_sha256": script_sha,
              "pex_sha256": inputs["pex_sha"],
              "model_sha256": inputs["model_sha"],
              "ngspice_version": inputs["version"],
              "config_sha256": original["config_sha256"],
              "requirements_sha256": original["requirements_sha256"],
              "sample_turnoff_start_ns": 2.100,
              "error_budget_v": BUDGET_V,
              "summary_path": str(path.relative_to(root)),
              "history_path": str((folder / "history.log").relative_to(root)),
              "cohort_reservation": reservation,
              "original_failed_holdout": {
                  "partial_decode_mismatches": original["groups"]["fresh_mha_holdout"]["analysis"]["partial_decode_mismatches"],
                  "below_error_budget_samples": original["groups"]["fresh_mha_holdout"]["analysis"]["below_error_budget_samples"],
                  "common_mode_outside_training_samples": original["groups"]["fresh_mha_holdout"]["analysis"]["common_mode_outside_training_samples"],
                  "excluded_from_training_and_validation": True},
              "groups": {}, "offline_sensitivity": {"status": "PENDING"},
              "physical_status": "NO_ADC_SWITCH_PEX_OR_WRAPPER_SIGNOFF",
              "not_signoff": "schematic TG and ideal control at TT plus optional TT/SS/FF smoke only; no physical ADC, switch/control PEX, transistor noise, 27-point PVT or wrapper"}
    _write_report(path, report)
    if not execute:
        return report
    _event(folder, f"SESSION_START source={source_sha} pex={inputs['pex_sha']} "
           f"runner={script_sha} timeout_s={timeout_s}")
    stage = "preflight"
    try:
        executable = campaign._ngspice(inputs["version"])
        stage = "training_extension"
        extended_jobs = _run_jobs(root, path, report, stage, _phases(extension),
                                  inputs, executable, timeout_s)
        decoder = campaign._train(old_jobs + extended_jobs, BUDGET_V)
        report["groups"][stage]["analysis"] = decoder
        report["frozen_decoder_sha256"] = decoder["frozen_decoder_sha256"]
        _write_report(path, report)
        if not decoder["training_margin_candidate"]:
            report["status"] = "BLOCKED_EXTENDED_TRAINING"
            report["blocked_at"] = stage
            _write_report(path, report)
            _event(folder, f"GATE {report['status']} minimum_gap_v={decoder['minimum_gap_v']}")
            return report
        stage = "fresh_validation"
        validation_jobs = _run_jobs(root, path, report, stage, _phases(validation),
                                    inputs, executable, timeout_s)
        held = campaign._decode_holdout(validation_jobs, validation, decoder, BUDGET_V)
        report["groups"][stage]["analysis"] = held
        requirements = campaign._read(root / "configs/sky130_post49_requirements.json")
        report["offline_sensitivity"] = campaign._sensitivity(
            validation_jobs, decoder, requirements)
        _write_report(path, report)
        if (not held["tt_holdout_candidate"] or
                report["offline_sensitivity"]["conclusion"] !=
                "NO_ERRORS_AT_INJECTED_BUDGET_EXTREMES"):
            report["status"] = "BLOCKED_NEW_TT_HOLDOUT"
            report["blocked_at"] = stage
            _write_report(path, report)
            _event(folder, f"GATE {report['status']} "
                   f"below_budget={held['below_error_budget_samples']} "
                   f"cm_outside={held['common_mode_outside_training_samples']}")
            return report
        stage = "pvt_smoke"
        training_jobs = old_jobs + extended_jobs
        cases = campaign._pvt_cases(training_jobs, decoder)
        names = {case.name for case in cases}
        tt_jobs = [job for job in training_jobs if job["case"] in names]
        if len(tt_jobs) != 8:
            raise ValueError("eight TT training cases required for PVT reuse")
        pvt_cases = [(case, point) for point in campaign.PVT_POINTS
                     if point[0] != "tt" for case in cases]
        pvt_jobs = [campaign._job(root, stage, case, off_ns=2.100,
                                  model=inputs["model"], pex=inputs["pex"],
                                  point=point,
                                  job_base=path.parent.relative_to(root))
                    for case, point in pvt_cases]
        group = {"status": "RUNNING", "planned_sims": 16,
                 "completed_sims": 0, "jobs": pvt_jobs}
        report["groups"][stage] = group
        _write_report(path, report)
        _event(folder, "START pvt_smoke 16 jobs")
        for index, job in enumerate(pvt_jobs, 1):
            campaign._measure(root, job, executable=executable,
                              version=inputs["version"], pex_sha=inputs["pex_sha"],
                              model_sha=inputs["model_sha"], timeout_s=timeout_s)
            group["completed_sims"] = index
            _write_report(path, report)
            _event(folder, f"DONE pvt_smoke {index}/16 {job['case']} "
                   f"corner={job['point']['corner']} log_sha256={job['log_sha256']}")
            if index == 1 or index % 4 == 0 or index == 16:
                print(f"pvt_smoke: {index}/16 {job['case']}", flush=True)
        group["status"] = "MEASURED_TT_SS_FF_DIAGNOSTIC"
        group["reused_tt_training_cases"] = [job["case"] for job in tt_jobs]
        pvt = campaign._pvt_result(tt_jobs + pvt_jobs, decoder, BUDGET_V)
        group["analysis"] = pvt
        report["status"] = (
            "MEASURED_RECOVERY_READOUT_DIAGNOSTICS_NO_WRAPPER"
            if pvt["conclusion"] == "THREE_POINT_DIAGNOSTIC_CANDIDATE"
            else "BLOCKED_READOUT_SENSITIVITY_OR_PVT")
        _write_report(path, report)
        _event(folder, f"GATE {report['status']} "
               f"pvt={pvt['conclusion']}")
        return report
    except (OSError, ValueError, RuntimeError, TimeoutError, KeyError, TypeError) as error:
        report["status"] = "FAILED"
        report["blocked_at"] = stage
        report["failure"] = f"{type(error).__name__}: {error}"
        _write_report(path, report)
        _event(folder, f"SESSION_FAILED {stage} {report['failure']}")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items()
                      if key != "groups"}, indent=2, ensure_ascii=False))
    if result["status"] == "FAILED":
        raise SystemExit(1)
