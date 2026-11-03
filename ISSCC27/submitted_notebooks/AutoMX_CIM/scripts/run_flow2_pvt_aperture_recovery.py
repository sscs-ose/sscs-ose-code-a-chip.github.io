#!/usr/bin/env python3
"""Find a sparse three-corner sampling candidate after the failed PVT smoke.

The first stage screens four already inspected training patterns at SS/FF.
Only a common passing point triggers the eight-pattern TT/SS/FF check.
This does not calibrate a corner decoder or approve a physical wrapper.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_recovery_pvt_diagnostic as pvt  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery as recovery  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402

OUTPUT = campaign.OUTPUT / "pvt_aperture_recovery"
TIMES_NS = (2.065, 2.085, 2.100, 2.115, 2.145)
CORNER_POINTS = tuple(point for point in campaign.PVT_POINTS if point[0] != "tt")
FORMAT = "automx-cim-flow2-pvt-aperture-recovery-v1"
TERMINAL = {"BLOCKED_SPARSE_PILOT_APERTURE", "BLOCKED_FULL_APERTURE",
            "CAPTURE_CANDIDATE_PENDING_CORNER_DECODER"}


def _source(root: Path) -> tuple[dict, dict, dict, list[dict], list, str]:
    _, inputs, training, decoder, recovery_sha = pvt._source(root)
    pvt_sha = campaign._sha(Path(pvt.__file__))
    source_path = (root / pvt.OUTPUT /
                   f"recovery_{recovery_sha[:12]}_runner_{pvt_sha[:12]}" /
                   "summary.json")
    source = campaign._read(source_path)
    selected = campaign._pvt_cases(training, decoder)
    if (source.get("format") != "automx-cim-flow2-recovery-pvt-diagnostic-v1" or
            source.get("status") != "MEASURED_PVT_DIAGNOSTIC_CM_GATE_BLOCKED" or
            source.get("source_recovery_sha256") != recovery_sha or
            source.get("script_sha256") != pvt_sha or
            source.get("pex_sha256") != inputs["pex_sha"] or
            source.get("model_sha256") != inputs["model_sha"] or
            source.get("frozen_decoder_sha256") != decoder["frozen_decoder_sha256"] or
            source.get("selected_training_cases") != sorted(case.name for case in selected) or
            source.get("pvt_analysis", {}).get("conclusion") !=
            "BLOCKED_FROZEN_TT_THRESHOLD_OR_CAPTURE_AT_PVT"):
        raise ValueError("complete, linked failed PVT diagnostic required")
    names = {case.name for case in selected}
    tt = [job for job in training if job["case"] in names]
    if len(tt) != 8 or {job["case"] for job in tt} != names:
        raise ValueError("eight selected TT training cases required")
    pvt._verify_completed(root, source, inputs, tt, decoder)
    return source, inputs, decoder, tt, selected, campaign._sha(source_path)


def _pilot_names(jobs: list[dict]) -> list[str]:
    """Use the worst capture case in each phase/corner; fill to four."""
    by_key = {(job["case"], job["point"]["corner"]): job for job in jobs}
    names = {case for case, _ in by_key}
    if len(jobs) != 16 or len(by_key) != 16 or len(names) != 8:
        raise ValueError("eight distinct SS/FF source cases required")
    scores = {name: max(campaign._metrics(by_key[name, corner])[
        "maximum_capture_error_late_v"] for corner in ("ss", "ff"))
        for name in names}
    chosen = set()
    for phase in ("a", "b"):
        for corner in ("ss", "ff"):
            candidates = [name for name in names if name.endswith("_" + phase)]
            chosen.add(max(candidates, key=lambda name: (
                campaign._metrics(by_key[name, corner])[
                    "maximum_capture_error_late_v"], name)))
    for name in sorted(names, key=lambda item: (-scores[item], item)):
        if len(chosen) == 4:
            break
        chosen.add(name)
    if len(chosen) != 4 or not any(x.endswith("_a") for x in chosen) or not any(
            x.endswith("_b") for x in chosen):
        raise ValueError("pilot must contain four cases across both phases")
    return sorted(chosen)


def _point_summary(jobs: list[dict], names: set[str], time_ns: float,
                   budget_v: float, corners: tuple[str, ...]) -> dict:
    subset = [job for job in jobs if job["case"] in names and
              job["turnoff_start_ns"] == time_ns and
              job["point"]["corner"] in corners]
    expected = {(name, corner) for name in names for corner in corners}
    observed = {(job["case"], job["point"]["corner"]) for job in subset}
    if len(subset) != len(expected) or observed != expected or any(
            "measurements_v" not in job for job in subset):
        raise ValueError(f"incomplete aperture grid at {time_ns:.3f} ns")
    errors = [campaign._metrics(job)["maximum_capture_error_late_v"]
              for job in subset]
    return {"turnoff_start_ns": time_ns, "case_count": len(names),
            "corners": list(corners), "maximum_capture_error_late_v": max(errors),
            "cases_exceeding_budget": sum(error > budget_v for error in errors),
            "capture_target_met": all(error <= budget_v for error in errors),
            "maximum_held_node_v": max(campaign._metrics(job)[
                "maximum_held_node_v"] for job in subset)}


def _select_time(grid: list[dict]) -> float | None:
    passing = [point for point in grid if point["capture_target_met"]]
    if not passing:
        return None
    return min(passing, key=lambda point: (
        point["maximum_capture_error_late_v"],
        abs(point["turnoff_start_ns"] - 2.100)))["turnoff_start_ns"]


def _save(path: Path, report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    campaign._save(path, report)


def _verified_own_jobs(root: Path, report: dict, inputs: dict) -> None:
    for name in ("pilot", "full"):
        jobs = report.get("groups", {}).get(name, {}).get("jobs", [])
        if jobs:
            fake = {"groups": {name: {"jobs": jobs}},
                    "pex_sha256": inputs["pex_sha"],
                    "model_sha256": inputs["model_sha"],
                    "ngspice_version": inputs["version"]}
            stage6._verified_jobs(root, fake, name)


def _verified_terminal(root: Path, report: dict, inputs: dict,
                       source: dict, tt: list[dict]) -> None:
    _verified_own_jobs(root, report, inputs)
    groups = report.get("groups", {})
    pilot = groups.get("pilot", {})
    pilot_new = pilot.get("jobs", [])
    if (pilot.get("status") != "MEASURED" or len(pilot_new) != 32 or
            pilot.get("planned_sims") != 32 or
            pilot.get("completed_sims") != 32):
        raise ValueError("complete 32-job pilot required")
    pilot_names = set(report["pilot_cases"])
    reused = [job for job in source["jobs"] if job["case"] in pilot_names]
    pilot_grid = [_point_summary(pilot_new + reused, pilot_names, time_ns,
                  recovery.BUDGET_V, ("ss", "ff")) for time_ns in TIMES_NS]
    candidate = _select_time(pilot_grid)
    if (report.get("pilot_grid") != pilot_grid or
            report.get("selected_turnoff_start_ns") != candidate):
        raise ValueError("pilot aperture analysis differs from measured jobs")
    if candidate is None:
        if report["status"] != "BLOCKED_SPARSE_PILOT_APERTURE" or groups.get("full"):
            raise ValueError("pilot blocker cannot claim a full PVT screen")
        return
    full = groups.get("full", {})
    full_new = full.get("jobs", [])
    expected_new = 0 if candidate == 2.100 else 16
    if (full.get("status") != "MEASURED" or
            full.get("planned_sims") != expected_new or
            full.get("completed_sims") != expected_new or
            len(full_new) != expected_new):
        raise ValueError("complete eight-case three-corner grid required")
    full_jobs = full_new + [job for job in pilot_new + source["jobs"] + tt
                            if job["turnoff_start_ns"] == candidate]
    full_grid = _point_summary(full_jobs, set(report["all_cases"]), candidate,
                               recovery.BUDGET_V, ("tt", "ss", "ff"))
    expected_status = ("CAPTURE_CANDIDATE_PENDING_CORNER_DECODER"
                       if full_grid["capture_target_met"] else
                       "BLOCKED_FULL_APERTURE")
    if report.get("full_grid") != full_grid or report["status"] != expected_status:
        raise ValueError("full aperture conclusion differs from measured jobs")


def _measure_group(root: Path, path: Path, report: dict, name: str,
                   jobs: list[dict], inputs: dict, executable: str,
                   timeout_s: int) -> None:
    group = {"planned_sims": len(jobs), "completed_sims": 0,
             "jobs": jobs, "status": "RUNNING"}
    report["groups"][name] = group
    _save(path, report)
    recovery._event(path.parent, f"START {name} {len(jobs)} jobs")
    for index, job in enumerate(jobs, 1):
        campaign._measure(root, job, executable=executable,
                          version=inputs["version"], pex_sha=inputs["pex_sha"],
                          model_sha=inputs["model_sha"], timeout_s=timeout_s)
        group["completed_sims"] = index
        _save(path, report)
        recovery._event(path.parent, f"DONE {name} {index}/{len(jobs)} "
                        f"{job['case']} {job['point']['corner']} "
                        f"off={job['turnoff_start_ns']:.3f} "
                        f"log_sha256={job['log_sha256']}")
        if index == 1 or index % 8 == 0 or index == len(jobs):
            print(f"PVT aperture {name}: {index}/{len(jobs)} "
                  f"{job['case']} {job['point']['corner']}", flush=True)
    group["status"] = "MEASURED"
    _save(path, report)


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    source, inputs, decoder, tt, selected, source_sha = _source(root)
    script_sha = campaign._sha(Path(__file__))
    folder = root / OUTPUT / f"pvt_{source_sha[:12]}_runner_{script_sha[:12]}"
    path = folder / "summary.json"
    pilot_names = _pilot_names(source["jobs"])
    all_names = {case.name for case in selected}
    if path.is_file():
        previous = campaign._read(path)
        if (previous.get("format") != FORMAT or
                previous.get("source_pvt_sha256") != source_sha or
                previous.get("script_sha256") != script_sha or
                previous.get("pex_sha256") != inputs["pex_sha"] or
                previous.get("model_sha256") != inputs["model_sha"] or
                previous.get("frozen_tt_decoder_sha256") != decoder[
                    "frozen_decoder_sha256"] or
                previous.get("pilot_cases") != pilot_names or
                previous.get("times_ns") != list(TIMES_NS)):
            raise FileExistsError(f"existing PVT aperture run differs: {path}")
        if previous["status"] in TERMINAL:
            _verified_terminal(root, previous, inputs, source, tt)
            return previous
        if not execute:
            return previous
    report = {"format": FORMAT, "status": "RUNNING" if execute else "PREPARED",
              "source_pvt_sha256": source_sha, "script_sha256": script_sha,
              "pex_sha256": inputs["pex_sha"],
              "model_sha256": inputs["model_sha"],
              "ngspice_version": inputs["version"],
              "frozen_tt_decoder_sha256": decoder["frozen_decoder_sha256"],
              "budget_v": recovery.BUDGET_V, "times_ns": list(TIMES_NS),
              "pilot_cases": pilot_names, "all_cases": sorted(all_names),
              "source_pvt_jobs_reused": 16,
              "new_spice_job_upper_bound": 48,
              "groups": {}, "pilot_grid": [], "full_grid": None,
              "selected_turnoff_start_ns": None,
              "summary_path": str(path.relative_to(root)),
              "history_path": str((folder / "history.log").relative_to(root)),
              "not_signoff": "sparse TT/SS/FF schematic TG with ideal control and reused training cases; no corner-calibrated decoder, independent MHA holdout, 27-point PVT, physical switch/control PEX, ADC or wrapper"}
    _save(path, report)
    if not execute:
        return report
    recovery._event(folder, f"SESSION_START source_pvt={source_sha} "
                    f"pex={inputs['pex_sha']} runner={script_sha} timeout_s={timeout_s}")
    try:
        executable = campaign._ngspice(inputs["version"])
        by_case = {case.name: case for case in selected}
        existing = {(job["case"], job["point"]["corner"], 2.100): job
                    for job in tt + source["jobs"]}
        pilot_new = [campaign._job(root, "pilot", by_case[name], off_ns=time_ns,
                    model=inputs["model"], pex=inputs["pex"], point=point,
                    job_base=folder.relative_to(root))
                    for time_ns in TIMES_NS if time_ns != 2.100
                    for point in CORNER_POINTS for name in pilot_names]
        _measure_group(root, path, report, "pilot", pilot_new,
                       inputs, executable, timeout_s)
        pilot_jobs = pilot_new + [existing[name, corner, 2.100]
                                  for name in pilot_names for corner in ("ss", "ff")]
        report["pilot_grid"] = [_point_summary(pilot_jobs, set(pilot_names),
                                time_ns, recovery.BUDGET_V, ("ss", "ff"))
                                for time_ns in TIMES_NS]
        candidate = _select_time(report["pilot_grid"])
        report["selected_turnoff_start_ns"] = candidate
        _save(path, report)
        if candidate is None:
            report["status"] = "BLOCKED_SPARSE_PILOT_APERTURE"
            _save(path, report)
            recovery._event(folder, "STOP no shared SS/FF pilot point meets 0.8mV")
            return report
        recovery._event(folder, f"PILOT_CANDIDATE turnoff={candidate:.3f} ns")
        pilot_lookup = {(job["case"], job["point"]["corner"],
                         job["turnoff_start_ns"]): job for job in pilot_jobs}
        full_new = [campaign._job(root, "full", case, off_ns=candidate,
                    model=inputs["model"], pex=inputs["pex"], point=point,
                    job_base=folder.relative_to(root))
                    for point in campaign.PVT_POINTS for case in selected
                    if (case.name, point[0], candidate) not in existing and
                       (case.name, point[0], candidate) not in pilot_lookup]
        _measure_group(root, path, report, "full", full_new,
                       inputs, executable, timeout_s)
        full_jobs = [*full_new, *(job for job in pilot_new + source["jobs"] + tt
                                   if job["turnoff_start_ns"] == candidate)]
        report["full_grid"] = _point_summary(full_jobs, all_names, candidate,
                    recovery.BUDGET_V, ("tt", "ss", "ff"))
        report["status"] = ("CAPTURE_CANDIDATE_PENDING_CORNER_DECODER"
                            if report["full_grid"]["capture_target_met"] else
                            "BLOCKED_FULL_APERTURE")
        _save(path, report)
        recovery._event(folder, f"COMPLETE status={report['status']} "
                        f"turnoff={candidate:.3f} ns")
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
                      if key != "groups"}, indent=2, ensure_ascii=False))
    if result["status"] == "FAILED":
        raise SystemExit(1)
