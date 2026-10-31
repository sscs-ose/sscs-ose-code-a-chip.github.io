#!/usr/bin/env python3
"""Run an isolated PVT smoke after Flow-2 recovery fails only its CM gate.

This diagnostic reuses eight TT training jobs and measures 16 SS/FF jobs.
It never upgrades the failed MHA holdout or creates a Stage-6 model.
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
from scripts import run_flow2_recovery as recovery  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402

OUTPUT = campaign.OUTPUT / "recovery_pvt_diagnostic"
REQUIRED_RECOVERY_STATUS = "BLOCKED_NEW_TT_HOLDOUT"


def _source(root: Path) -> tuple[dict, dict, list[dict], dict, str]:
    original, inputs, old_jobs, original_sha = recovery._source(root)
    recovery_sha = campaign._sha(Path(recovery.__file__))
    path = (root / recovery.OUTPUT /
            f"source_{original_sha[:12]}_runner_{recovery_sha[:12]}" /
            "summary.json")
    report = campaign._read(path)
    if (report.get("format") != "automx-cim-flow2-recovery-v1" or
            report.get("status") != REQUIRED_RECOVERY_STATUS or
            report.get("blocked_at") != "fresh_validation" or
            report.get("script_sha256") != recovery_sha or
            report.get("source_campaign_sha256") != original_sha or
            report.get("pex_sha256") != inputs["pex_sha"] or
            report.get("model_sha256") != inputs["model_sha"] or
            report.get("ngspice_version") != inputs["version"] or
            report.get("sample_turnoff_start_ns") != 2.100 or
            report.get("error_budget_v") != recovery.BUDGET_V or
            "pvt_smoke" in report.get("groups", {})):
        raise ValueError("current CM-blocked recovery summary required")
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    extension, validation = recovery._cohorts(config, old_jobs)
    if report.get("cohort_reservation") != {
            "training": recovery._reservation(extension),
            "validation": recovery._reservation(validation)}:
        raise ValueError("recovery cohort reservation changed")
    for name in ("training_extension", "fresh_validation"):
        group = report["groups"][name]
        if (group.get("status") != "MEASURED_TT_DIAGNOSTIC" or
                group.get("completed_sims") != 64 or
                group.get("planned_sims") != 64 or
                len(group.get("jobs", [])) != 64):
            raise ValueError(f"incomplete measured recovery group: {name}")
        stage6._verified_jobs(root, report, name)
    added = report["groups"]["training_extension"]["jobs"]
    held = report["groups"]["fresh_validation"]["jobs"]
    _verify_vectors(added, recovery._phases(extension))
    _verify_vectors(held, recovery._phases(validation))
    training = old_jobs + added
    decoder = campaign._train(training, recovery.BUDGET_V)
    if (not decoder["training_margin_candidate"] or
            decoder != report["groups"]["training_extension"]["analysis"] or
            decoder["frozen_decoder_sha256"] != report["frozen_decoder_sha256"]):
        raise ValueError("recovery training decoder cannot be reproduced")
    validation_result = campaign._decode_holdout(
        held, validation, decoder, recovery.BUDGET_V)
    sensitivity = campaign._sensitivity(
        held, decoder,
        campaign._read(root / "configs/sky130_post49_requirements.json"))
    if (validation_result != report["groups"]["fresh_validation"]["analysis"] or
            sensitivity != report["offline_sensitivity"] or
            not _cm_only_failure(validation_result, sensitivity)):
        raise ValueError("recovery failure is not CM-only or cannot be reproduced")
    if any(job.get("turnoff_start_ns") != 2.100 for job in training + held):
        raise ValueError("sample time changed")
    return report, inputs, training, decoder, campaign._sha(path)


def _verify_vectors(jobs: list[dict], cases: list) -> None:
    expected = {case.name: campaign._vectors(case) for case in cases}
    if len(jobs) != len(expected) or {job["case"] for job in jobs} != set(expected):
        raise ValueError("measured MHA vectors differ from reservation")
    for job in jobs:
        if {key: job[key] for key in ("case", "activation_x2",
                                       "ternary_weights", "integer_sums")} != expected[job["case"]]:
            raise ValueError(f"measured MHA stimulus changed: {job['case']}")


def _cm_only_failure(validation: dict, sensitivity: dict) -> bool:
    return (validation.get("tt_holdout_candidate") is False and
            validation.get("partial_decode_mismatches") == 0 and
            validation.get("combined_decode_mismatches") == 0 and
            validation.get("below_error_budget_samples") == 0 and
            validation.get("common_mode_outside_training_samples", 0) > 0 and
            sensitivity.get("conclusion") == "NO_ERRORS_AT_INJECTED_BUDGET_EXTREMES")


def _cm_summary(jobs: list[dict]) -> list[dict]:
    points = []
    for corner, vdd, temperature in campaign.PVT_POINTS:
        subset = [job for job in jobs if job["point"] == {
            "corner": corner, "vdd_v": vdd, "temperature_c": temperature}]
        values = [campaign._held(job, col)[1] for job in subset for col in range(4)]
        zero = [campaign._held(job, col)[1] for job in subset for col in range(4)
                if int(job["integer_sums"][col]) == 0]
        if len(subset) != 8 or not zero:
            raise ValueError(f"eight PVT cases with a zero state required at {corner}")
        points.append({"corner": corner, "vdd_v": vdd,
                       "temperature_c": temperature,
                       "held_common_mode_min_v": min(values),
                       "held_common_mode_max_v": max(values),
                       "zero_state_common_mode_max_v": max(zero),
                       "samples_above_nominal_vdd": sum(value > vdd for value in values),
                       "sample_count": len(values)})
    return points


def _save(path: Path, report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    campaign._save(path, report)


def _verify_completed(root: Path, report: dict, inputs: dict,
                      reused_tt: list[dict], decoder: dict) -> None:
    jobs = report.get("jobs", [])
    if (len(jobs) != 16 or report.get("new_simulations_completed") != 16 or
            report.get("new_simulations_planned") != 16):
        raise ValueError("PVT diagnostic completion count changed")
    fake = {"groups": {"pvt_smoke": {"jobs": jobs}},
            "pex_sha256": inputs["pex_sha"],
            "model_sha256": inputs["model_sha"],
            "ngspice_version": inputs["version"]}
    stage6._verified_jobs(root, fake, "pvt_smoke")
    if (report.get("pvt_analysis") != campaign._pvt_result(
            reused_tt + jobs, decoder, recovery.BUDGET_V) or
            report.get("common_mode_by_corner") != _cm_summary(reused_tt + jobs)):
        raise ValueError("PVT diagnostic changed after measurement")


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    recovery_report, inputs, training, decoder, recovery_sha = _source(root)
    script_sha = campaign._sha(Path(__file__))
    folder = root / OUTPUT / f"recovery_{recovery_sha[:12]}_runner_{script_sha[:12]}"
    path = folder / "summary.json"
    selected = campaign._pvt_cases(training, decoder)
    names = {case.name for case in selected}
    reused_tt = [job for job in training if job["case"] in names]
    if len(reused_tt) != 8 or {job["case"] for job in reused_tt} != names:
        raise ValueError("eight verified TT training checkpoints required")
    if path.is_file():
        previous = campaign._read(path)
        if (previous.get("source_recovery_sha256") != recovery_sha or
                previous.get("script_sha256") != script_sha or
                previous.get("selected_training_cases") != sorted(names)):
            raise FileExistsError(f"existing PVT diagnostic differs: {path}")
        if previous.get("status") == "MEASURED_PVT_DIAGNOSTIC_CM_GATE_BLOCKED":
            _verify_completed(root, previous, inputs, reused_tt, decoder)
            return previous
        if not execute:
            return previous
    report = {"format": "automx-cim-flow2-recovery-pvt-diagnostic-v1",
              "status": "RUNNING" if execute else "PREPARED",
              "source_recovery_sha256": recovery_sha,
              "source_recovery_status": recovery_report["status"],
              "script_sha256": script_sha,
              "pex_sha256": inputs["pex_sha"],
              "model_sha256": inputs["model_sha"],
              "ngspice_version": inputs["version"],
              "frozen_decoder_sha256": decoder["frozen_decoder_sha256"],
              "selected_training_cases": sorted(names),
              "reused_tt_checkpoints": [job["checkpoint"] for job in reused_tt],
              "new_simulations_planned": 16,
              "new_simulations_completed": 0,
              "jobs": [], "pvt_analysis": None, "common_mode_by_corner": None,
              "summary_path": str(path.relative_to(root)),
              "history_path": str((folder / "history.log").relative_to(root)),
              "not_signoff": "diagnostic while independent TT validation remains CM-blocked; nominal VDD/25C TT/SS/FF only, schematic TG/ideal control; no physical ADC, transistor noise, full PVT or wrapper"}
    _save(path, report)
    if not execute:
        return report
    recovery._event(folder, f"SESSION_START recovery={recovery_sha} pex={inputs['pex_sha']} "
                    f"runner={script_sha} timeout_s={timeout_s}")
    try:
        executable = campaign._ngspice(inputs["version"])
        jobs = [campaign._job(root, "pvt_smoke", case, off_ns=2.100,
                              model=inputs["model"], pex=inputs["pex"],
                              point=point, job_base=folder.relative_to(root))
                for point in campaign.PVT_POINTS if point[0] != "tt"
                for case in selected]
        report["jobs"] = jobs
        _save(path, report)
        for index, job in enumerate(jobs, 1):
            campaign._measure(root, job, executable=executable,
                              version=inputs["version"], pex_sha=inputs["pex_sha"],
                              model_sha=inputs["model_sha"], timeout_s=timeout_s)
            report["new_simulations_completed"] = index
            _save(path, report)
            recovery._event(folder, f"DONE {index}/16 {job['case']} "
                            f"corner={job['point']['corner']} log_sha256={job['log_sha256']}")
            if index == 1 or index % 4 == 0 or index == 16:
                print(f"PVT diagnostic: {index}/16 {job['case']} "
                      f"{job['point']['corner']}", flush=True)
        report["pvt_analysis"] = campaign._pvt_result(
            reused_tt + jobs, decoder, recovery.BUDGET_V)
        report["common_mode_by_corner"] = _cm_summary(reused_tt + jobs)
        report["status"] = "MEASURED_PVT_DIAGNOSTIC_CM_GATE_BLOCKED"
        _save(path, report)
        recovery._event(folder, f"COMPLETE PVT_DIAGNOSTIC "
                        f"conclusion={report['pvt_analysis']['conclusion']}; "
                        "TT holdout CM gate remains blocked")
        return report
    except (OSError, ValueError, RuntimeError, TimeoutError, KeyError, TypeError) as error:
        report["status"] = "FAILED"
        report["failure"] = f"{type(error).__name__}: {error}"
        _save(path, report)
        recovery._event(folder, f"SESSION_FAILED {report['failure']}")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items()
                      if key != "jobs"}, indent=2, ensure_ascii=False))
    if result["status"] == "FAILED":
        raise SystemExit(1)
