#!/usr/bin/env python3
"""Gated SS/FF switch-control pilot on the failed 3.36 um sample/hold.

Two previously inspected worst cases and one all-zero case are measured.
Only the ideal control turnoff ordering and slew change. This is a circuit
diagnostic, not a physical switch/control, ADC, or mixed-signal sign-off.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.spice import parse_measurements  # noqa: E402
from scripts import run_flow2_pvt_switch_width as width  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery as recovery  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402

FORMAT = "automx-cim-flow2-pvt-switch-control-v1"
OUTPUT = campaign.OUTPUT / "pvt_switch_control"
WIDTH_UM = 3.36
OFF_NS = 2.100
PRE_NS = 2.090
LATE_NS = 2.400
ZERO_CASE = "idle_all_a"
# (name, edge slew ps, NMOS-off delay ps, PMOS-off delay ps)
VARIANTS = (
    ("simultaneous_5ps", 5, 0, 0),
    ("simultaneous_20ps", 20, 0, 0),
    ("simultaneous_50ps", 50, 0, 0),
    ("nmos_first_10ps_20ps", 20, 0, 10),
    ("pmos_first_10ps_20ps", 20, 10, 0),
)
TERMINAL = {"BLOCKED_SWITCH_CONTROL_PILOT",
            "CAPTURE_CONTROL_CANDIDATE_PENDING_VALIDATION"}


def _source(root: Path) -> tuple[dict, dict, list[str], dict, Path]:
    inputs, cases, _, worst, aperture_sha = width._source(root)
    path = (root / width.OUTPUT /
            f"source_{aperture_sha[:12]}_runner_{campaign._sha(Path(width.__file__))[:12]}" /
            "summary.json")
    if not path.is_file():
        raise FileNotFoundError(f"completed switch-width pilot required: {path}")
    report = campaign._read(path)
    if (report.get("format") != width.FORMAT or
            report.get("status") != "BLOCKED_SWITCH_WIDTH_PILOT" or
            report.get("source_aperture_sha256") != aperture_sha or
            report.get("script_sha256") != campaign._sha(Path(width.__file__)) or
            report.get("pex_sha256") != inputs["pex_sha"] or
            report.get("model_sha256") != inputs["model_sha"] or
            report.get("ngspice_version") != inputs["version"] or
            report.get("pilot_cases") != worst):
        raise ValueError("linked, completed switch-width pilot required")
    width._verify_terminal(root, report, inputs)
    if (ZERO_CASE not in cases or any(cases[ZERO_CASE].sums) or
            ZERO_CASE in worst or len(worst) != 2):
        raise ValueError("distinct worst cases and all-zero control required")
    return inputs, cases, worst, report, path


def _variant(name: str) -> tuple[str, int, int, int]:
    matches = [variant for variant in VARIANTS if variant[0] == name]
    if len(matches) != 1:
        raise ValueError(f"unsupported control variant: {name}")
    return matches[0]


def _full_time_ns(name: str) -> float:
    _, slew_ps, n_delay_ps, p_delay_ps = _variant(name)
    if name == VARIANTS[0][0]:
        return 2.135  # same probe as the existing 3.36 um pilot
    return round(OFF_NS + (max(n_delay_ps, p_delay_ps) + slew_ps + 15) / 1000, 3)


def _deck(case, model: Path, pex: Path, name: str,
          point: tuple[str, float, int]) -> str:
    """Alter only the two ideal control pulses and their full-off probes."""
    _, slew_ps, n_delay_ps, p_delay_ps = _variant(name)
    source = width._deck(case, model, pex, WIDTH_UM, point)
    lines = source.splitlines()
    if (source.count(" W=3.36 L=0.15") != 16 or
            source.count(" 20f IC={VDD}") != 8):
        raise ValueError("unexpected switch or hold topology")
    expected = {
        "VSAM SAM 0": "VSAM SAM 0 PULSE(0 {VDD} 1.8n 5p 5p 0.295n 10n)",
        "VSAMB SAMB 0": "VSAMB SAMB 0 PULSE({VDD} 0 1.8n 5p 5p 0.295n 10n)",
    }
    for prefix, old in expected.items():
        if lines.count(old) != 1 or sum(line.startswith(prefix + " ") for line in lines) != 1:
            raise ValueError(f"unexpected ideal control source: {prefix}")
    n_width_ns = OFF_NS - 1.805 + n_delay_ps / 1000
    p_width_ns = OFF_NS - 1.805 + p_delay_ps / 1000
    replacements = {
        expected["VSAM SAM 0"]:
            f"VSAM SAM 0 PULSE(0 {{VDD}} 1.8n 5p {slew_ps}p {n_width_ns:.3f}n 10n)",
        expected["VSAMB SAMB 0"]:
            f"VSAMB SAMB 0 PULSE({{VDD}} 0 1.8n 5p {slew_ps}p {p_width_ns:.3f}n 10n)",
    }
    lines = [replacements.get(line, line) for line in lines]
    probes = [i for i, line in enumerate(lines)
              if line.startswith(".measure tran aper_") and "_full " in line]
    if len(probes) != 16 or any(" AT=2.135n" not in lines[i] for i in probes):
        raise ValueError("unexpected full-off measurements")
    full_ns = _full_time_ns(name)
    for i in probes:
        lines[i] = lines[i].replace(" AT=2.135n", f" AT={full_ns:.3f}n")
    if not PRE_NS < OFF_NS < full_ns < LATE_NS:
        raise ValueError("invalid measurement ordering")
    return "\n".join(lines) + "\n"


def _decompose(job: dict) -> dict:
    """Keep signed errors so acquisition lag and turnoff motion stay distinct."""
    values = job["measurements_v"]
    columns = []
    for column in range(4):
        def differential(prefix: str, when: str) -> float:
            return (float(values[f"aper_{prefix}bln_c{column}_{when}"]) -
                    float(values[f"aper_{prefix}blp_c{column}_{when}"]))

        bitline_pre = differential("", "pre")
        held_pre = differential("h", "pre")
        held_full = differential("h", "full")
        held_late = differential("h", "late")
        tracking = held_pre - bitline_pre
        turnoff = held_full - held_pre
        drift = held_late - held_full
        capture = held_late - bitline_pre
        if (not all(math.isfinite(value) for value in
                    (tracking, turnoff, drift, capture)) or
                abs(tracking + turnoff + drift - capture) > 1e-9):
            raise ValueError(f"invalid capture decomposition: {job['case']} c{column}")
        columns.append({"column": column,
                        "bitline_pre_differential_v": bitline_pre,
                        "held_pre_differential_v": held_pre,
                        "held_full_differential_v": held_full,
                        "held_late_differential_v": held_late,
                        "pre_turnoff_tracking_error_v": tracking,
                        "turnoff_differential_step_v": turnoff,
                        "post_turnoff_drift_v": drift,
                        "late_capture_error_v": capture})
    metric = campaign._metrics(job)
    capture_max = max(abs(c["late_capture_error_v"]) for c in columns)
    if abs(capture_max - metric["maximum_capture_error_late_v"]) > 1e-9:
        raise ValueError("capture decomposition disagrees with existing metric")
    return {"columns": columns,
            "maximum_pre_turnoff_tracking_error_abs_v": max(
                abs(c["pre_turnoff_tracking_error_v"]) for c in columns),
            "maximum_turnoff_differential_step_abs_v": max(
                abs(c["turnoff_differential_step_v"]) for c in columns),
            "maximum_post_turnoff_drift_abs_v": max(
                abs(c["post_turnoff_drift_v"]) for c in columns),
            "maximum_capture_error_late_v": capture_max,
            "maximum_held_node_v": metric["maximum_held_node_v"]}


def _job(root: Path, folder: Path, case, name: str,
         point: tuple[str, float, int], inputs: dict) -> dict:
    group = folder / "pilot"
    group.mkdir(parents=True, exist_ok=True)
    tag = f"{case.name}_{name}_{point[0]}"
    deck = group / f"{tag}.spice"
    content = _deck(case, inputs["model"], inputs["pex"], name, point)
    if deck.is_file() and deck.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"changed switch-control deck: {deck}")
    deck.write_text(content, encoding="utf-8")
    return {**campaign._vectors(case), "phase": case.name.rsplit("_", 1)[-1],
            "variant": name, "switch_width_um": WIDTH_UM,
            "turnoff_start_ns": OFF_NS,
            "pre_measure_time_ns": PRE_NS,
            "full_measure_time_ns": _full_time_ns(name),
            "late_measure_time_ns": LATE_NS,
            "point": {"corner": point[0], "vdd_v": point[1],
                      "temperature_c": point[2]},
            "deck": str(deck.relative_to(root)),
            "deck_sha256": campaign._sha(deck),
            "log": str((group / f"{tag}.log").relative_to(root)),
            "checkpoint": str((group / f"{tag}.receipt.json").relative_to(root))}


def _grid(jobs: list[dict], names: set[str]) -> list[dict]:
    expected = {(variant[0], name, corner)
                for variant in VARIANTS for name in names for corner in ("ss", "ff")}
    observed = [(job["variant"], job["case"], job["point"]["corner"])
                for job in jobs]
    if (len(names) != 3 or len(observed) != len(expected) or
            set(observed) != expected or len(set(observed)) != len(observed)):
        raise ValueError("incomplete switch-control pilot matrix")
    points = []
    for variant in VARIANTS:
        subset = [job for job in jobs if job["variant"] == variant[0]]
        metrics = [_decompose(job) for job in subset]
        errors = [item["maximum_capture_error_late_v"] for item in metrics]
        points.append({"variant": variant[0], "slew_ps": variant[1],
                       "nmos_off_delay_ps": variant[2],
                       "pmos_off_delay_ps": variant[3],
                       "case_count": len(names), "corners": ["ss", "ff"],
                       "maximum_pre_turnoff_tracking_error_abs_v": max(
                           item["maximum_pre_turnoff_tracking_error_abs_v"]
                           for item in metrics),
                       "maximum_turnoff_differential_step_abs_v": max(
                           item["maximum_turnoff_differential_step_abs_v"]
                           for item in metrics),
                       "maximum_capture_error_late_v": max(errors),
                       "cases_exceeding_budget": sum(
                           error > recovery.BUDGET_V for error in errors),
                       "maximum_held_node_v": max(
                           item["maximum_held_node_v"] for item in metrics),
                       "capture_target_met": all(
                           error <= recovery.BUDGET_V for error in errors)})
    return points


def _decision(grid: list[dict]) -> tuple[str, str | None, str]:
    best = min(grid, key=lambda point: (point["maximum_capture_error_late_v"],
                                        point["variant"]))
    passing = [point for point in grid if point["capture_target_met"]]
    selected = (min(passing, key=lambda point: (
        point["maximum_capture_error_late_v"], point["variant"]))["variant"]
        if passing else None)
    status = ("CAPTURE_CONTROL_CANDIDATE_PENDING_VALIDATION" if selected
              else "BLOCKED_SWITCH_CONTROL_PILOT")
    return status, selected, best["variant"]


def _verified_jobs(root: Path, jobs: list[dict], inputs: dict) -> None:
    fake = {"groups": {"pilot": {"jobs": jobs}},
            "pex_sha256": inputs["pex_sha"],
            "model_sha256": inputs["model_sha"],
            "ngspice_version": inputs["version"]}
    stage6._verified_jobs(root, fake, "pilot")


def _verified_terminal(root: Path, report: dict, inputs: dict,
                       baseline: list[dict], planned: list[dict],
                       names: set[str]) -> None:
    actual = report.get("jobs", [])
    identity = ("case", "activation_x2", "ternary_weights", "integer_sums",
                "phase", "variant", "switch_width_um", "turnoff_start_ns",
                "pre_measure_time_ns", "full_measure_time_ns",
                "late_measure_time_ns", "point", "deck", "deck_sha256",
                "log", "checkpoint")
    if (report.get("planned_new_sims") != 26 or
            report.get("completed_new_sims") != 26 or len(actual) != 26 or
            len(report.get("reused_baseline_jobs", [])) != 4 or
            report.get("reused_baseline_jobs") != baseline or
            [{key: job.get(key) for key in identity} for job in actual] !=
            [{key: job.get(key) for key in identity} for job in planned]):
        raise ValueError("incomplete switch-control pilot evidence")
    _verified_jobs(root, actual, inputs)
    if any(job.get("decomposition") != _decompose(job) for job in actual):
        raise ValueError("switch-control decomposition differs from raw measurements")
    full = baseline + actual
    grid = _grid(full, names)
    status, selected, diagnostic = _decision(grid)
    if (report.get("grid") != grid or report.get("status") != status or
            report.get("selected_control_variant") != selected or
            report.get("best_diagnostic_variant") != diagnostic):
        raise ValueError("switch-control pilot conclusion differs from jobs")


def _valid_checkpoint(root: Path, job: dict, inputs: dict) -> bool:
    deck, log, receipt = (root / job[key] for key in
                          ("deck", "log", "checkpoint"))
    if not all(path.is_file() for path in (deck, log, receipt)):
        return False
    try:
        saved = campaign._read(receipt)
        measured = parse_measurements(log.read_text(
            encoding="utf-8", errors="replace"), campaign._expected())
        return (saved.get("status") == "PASS" and
                saved.get("deck_sha256") == job["deck_sha256"] == campaign._sha(deck) and
                saved.get("log_sha256") == campaign._sha(log) and
                saved.get("pex_sha256") == inputs["pex_sha"] and
                saved.get("model_sha256") == inputs["model_sha"] and
                saved.get("ngspice_version") == inputs["version"] and
                set(measured) == set(campaign._expected()) and
                measured == saved.get("measurements_v"))
    except (OSError, ValueError, TypeError):
        return False


def _save(path: Path, report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    campaign._save(path, report)


def run(root: str | Path, *, execute: bool = False,
        timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    inputs, cases, worst, source, source_path = _source(root)
    source_sha = campaign._sha(source_path)
    script_sha = campaign._sha(Path(__file__))
    folder = root / OUTPUT / f"source_{source_sha[:12]}_runner_{script_sha[:12]}"
    path = folder / "summary.json"
    names = [*worst, ZERO_CASE]
    baseline = [{**job, "variant": VARIANTS[0][0],
                 "pre_measure_time_ns": PRE_NS,
                 "full_measure_time_ns": _full_time_ns(VARIANTS[0][0]),
                 "late_measure_time_ns": LATE_NS,
                 "decomposition": _decompose(job)}
                for job in source["groups"]["pilot"]["jobs"]
                if job["switch_width_um"] == WIDTH_UM]
    if (len(baseline) != 4 or
            {(job["case"], job["point"]["corner"]) for job in baseline} !=
            {(name, corner) for name in worst for corner in ("ss", "ff")}):
        raise ValueError("four verified 3.36 um baseline jobs required")
    jobs = [_job(root, folder, cases[name], variant[0], point, inputs)
            for variant in VARIANTS
            for point in campaign.PVT_POINTS if point[0] != "tt"
            for name in names if variant[0] != VARIANTS[0][0] or name == ZERO_CASE]
    if len(jobs) != 26:
        raise ValueError("expected 26 new pilot jobs")
    if path.is_file():
        report = campaign._read(path)
        if (report.get("format") != FORMAT or
                report.get("source_switch_width_sha256") != source_sha or
                report.get("script_sha256") != script_sha or
                report.get("pex_sha256") != inputs["pex_sha"] or
                report.get("model_sha256") != inputs["model_sha"] or
                report.get("ngspice_version") != inputs["version"] or
                report.get("pilot_cases") != names or
                report.get("variants") != [list(v) for v in VARIANTS] or
                report.get("reused_baseline_jobs") != baseline):
            raise FileExistsError(f"existing switch-control run differs: {path}")
        if report["status"] in TERMINAL:
            _verified_terminal(root, report, inputs, baseline, jobs, set(names))
            return report
        if not execute:
            return report
    else:
        report = {"format": FORMAT, "status": "PREPARED",
                  "source_switch_width_sha256": source_sha,
                  "source_aperture_sha256": source["source_aperture_sha256"],
                  "script_sha256": script_sha,
                  "pex_sha256": inputs["pex_sha"],
                  "model_sha256": inputs["model_sha"],
                  "ngspice_version": inputs["version"],
                  "switch_width_um": WIDTH_UM, "hold_capacitance_ff": 20,
                  "turnoff_start_ns": OFF_NS,
                  "capture_budget_v": recovery.BUDGET_V,
                  "pilot_cases": names,
                  "variants": [list(v) for v in VARIANTS],
                  "reused_baseline_jobs": baseline,
                  "planned_new_sims": len(jobs),
                  "completed_new_sims": 0, "reused_new_checkpoints": 0,
                  "jobs": jobs, "grid": [],
                  "selected_control_variant": None,
                  "best_diagnostic_variant": None,
                  "summary_path": str(path.relative_to(root)),
                  "history_path": str((folder / "history.log").relative_to(root)),
                  "not_signoff": "three-case SS/FF pilot with ideal clock sources and schematic TG; no switch/control PEX, physical driver, transistor noise, full decoder/PVT/holdout or wrapper"}
        _save(path, report)
    if not execute:
        return report
    report["status"] = "RUNNING"
    report["jobs"] = jobs
    report["completed_new_sims"] = 0
    report["reused_new_checkpoints"] = 0
    report.pop("failure", None)
    _save(path, report)
    recovery._event(folder, f"SESSION_START source={source_sha} runner={script_sha} "
                    f"pex={inputs['pex_sha']} timeout_s={timeout_s}")
    try:
        executable = campaign._ngspice(inputs["version"])
        for index, job in enumerate(jobs, 1):
            reused = _valid_checkpoint(root, job, inputs)
            campaign._measure(root, job, executable=executable,
                              version=inputs["version"],
                              pex_sha=inputs["pex_sha"],
                              model_sha=inputs["model_sha"],
                              timeout_s=timeout_s)
            job["decomposition"] = _decompose(job)
            report["completed_new_sims"] = index
            report["reused_new_checkpoints"] += int(reused)
            _save(path, report)
            recovery._event(folder, f"{'REUSE' if reused else 'DONE'} {index}/{len(jobs)} "
                            f"{job['case']} {job['point']['corner']} {job['variant']} "
                            f"capture={job['decomposition']['maximum_capture_error_late_v']:.6g}V "
                            f"log_sha256={job['log_sha256']}")
            if index == 1 or index % 5 == 0 or index == len(jobs):
                print(f"Switch-control pilot: {index}/{len(jobs)} "
                      f"{job['case']} {job['point']['corner']} {job['variant']}",
                      flush=True)
        report["grid"] = _grid(baseline + jobs, set(names))
        status, selected, diagnostic = _decision(report["grid"])
        report["status"] = status
        report["selected_control_variant"] = selected
        report["best_diagnostic_variant"] = diagnostic
        _save(path, report)
        recovery._event(folder, f"COMPLETE {status}; best_diagnostic={diagnostic}; "
                        f"selected={selected}")
        return report
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        _save(path, report)
        recovery._event(folder, "SESSION_INTERRUPTED; valid checkpoints remain resumable")
        raise
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
                      if key not in ("jobs", "reused_baseline_jobs")},
                     indent=2, ensure_ascii=False))
    if result["status"] == "FAILED":
        raise SystemExit(1)
