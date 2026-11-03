#!/usr/bin/env python3
"""Screen transmission-gate width after the SS/FF aperture pilot failed.

Keep the 20 fF hold node and 2.100 ns turnoff. Test the worst SS and FF
training cases first; expand to eight TT/SS/FF cases only if both pass.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_pvt_aperture_recovery as aperture  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery as recovery  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402

OUTPUT = campaign.OUTPUT / "pvt_switch_width"
FORMAT = "automx-cim-flow2-pvt-switch-width-v1"
WIDTHS_UM = (1.68, 3.36, 6.72)
OFF_NS = 2.100
TERMINAL = {"BLOCKED_SWITCH_WIDTH_PILOT", "BLOCKED_SWITCH_WIDTH_FULL",
            "SWITCH_WIDTH_CANDIDATE_PENDING_DECODER_AND_NOISE"}


def _source(root: Path) -> tuple[dict, dict, list, list[str], str]:
    pvt_report, inputs, _, tt, selected, pvt_sha = aperture._source(root)
    script_sha = campaign._sha(Path(aperture.__file__))
    path = (root / aperture.OUTPUT /
            f"pvt_{pvt_sha[:12]}_runner_{script_sha[:12]}" / "summary.json")
    report = campaign._read(path)
    if (report.get("format") != aperture.FORMAT or
            report.get("status") != "BLOCKED_SPARSE_PILOT_APERTURE" or
            report.get("source_pvt_sha256") != pvt_sha or
            report.get("script_sha256") != script_sha or
            report.get("pex_sha256") != inputs["pex_sha"] or
            report.get("model_sha256") != inputs["model_sha"]):
        raise ValueError("linked completed aperture failure required")
    aperture._verified_terminal(root, report, inputs, pvt_report, tt)
    cases = {case.name: case for case in selected}
    pilot = report["pilot_cases"]
    by_corner = {(job["case"], job["point"]["corner"]): job
                 for job in pvt_report["jobs"] if job["case"] in pilot}
    worst = [max(pilot, key=lambda name: campaign._metrics(
             by_corner[name, corner])["maximum_capture_error_late_v"])
             for corner in ("ss", "ff")]
    if len(set(worst)) != 2 or any(name not in cases for name in worst):
        raise ValueError("distinct SS and FF worst-case pilot stimuli required")
    return inputs, cases, selected, worst, campaign._sha(path)


def _deck(case, model: Path, pex: Path, width_um: float,
          point: tuple[str, float, int]) -> str:
    if width_um not in WIDTHS_UM:
        raise ValueError("unsupported width")
    lines = campaign._spice(case, model, pex, off_ns=OFF_NS, point=point).splitlines()
    switches = [i for i, line in enumerate(lines)
                if line.startswith(("XSHN_", "XSHP_"))]
    holds = [line for line in lines if line.startswith(("CHBLP", "CHBLN"))]
    if len(switches) != 16 or len(holds) != 8:
        raise ValueError("unexpected sample/hold topology")
    if any(" W=0.84 L=0.15" not in lines[i] for i in switches):
        raise ValueError("unexpected source transmission-gate size")
    if any(" 20f IC={VDD}" not in line for line in holds):
        raise ValueError("hold capacitance changed")
    for i in switches:
        lines[i] = lines[i].replace(" W=0.84 L=0.15",
                                    f" W={width_um:g} L=0.15")
    return "\n".join(lines) + "\n"


def _job(root: Path, folder: Path, group: str, case, width_um: float,
         point: tuple[str, float, int], inputs: dict) -> dict:
    base = folder / group
    base.mkdir(parents=True, exist_ok=True)
    tag = f"{case.name}_w{width_um:g}_off2p100_{point[0]}".replace(".", "p")
    deck = base / f"{tag}.spice"
    content = _deck(case, inputs["model"], inputs["pex"], width_um, point)
    if deck.is_file() and deck.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"changed switch-width deck: {deck}")
    deck.write_text(content, encoding="utf-8")
    return {**campaign._vectors(case), "phase": case.name.rsplit("_", 1)[-1],
            "switch_width_um": width_um, "turnoff_start_ns": OFF_NS,
            "point": {"corner": point[0], "vdd_v": point[1],
                      "temperature_c": point[2]},
            "deck": str(deck.relative_to(root)),
            "deck_sha256": campaign._sha(deck),
            "log": str((base / f"{tag}.log").relative_to(root)),
            "checkpoint": str((base / f"{tag}.receipt.json").relative_to(root))}


def _grid(jobs: list[dict], widths: tuple[float, ...], names: set[str],
          corners: tuple[str, ...]) -> list[dict]:
    points = []
    for width in widths:
        subset = [job for job in jobs if job["switch_width_um"] == width]
        point = aperture._point_summary(subset, names, OFF_NS,
                                        recovery.BUDGET_V, corners)
        point["switch_width_um"] = width
        points.append(point)
    return points


def _select(grid: list[dict]) -> float | None:
    passing = [point for point in grid if point["capture_target_met"]]
    return (min(passing, key=lambda point: (point[
            "maximum_capture_error_late_v"], point["switch_width_um"]))[
                "switch_width_um"] if passing else None)


def _save(path: Path, report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    campaign._save(path, report)


def _verify_group(root: Path, group: dict, name: str,
                  inputs: dict, count: int) -> list[dict]:
    jobs = group.get("jobs", [])
    if (group.get("status") != "MEASURED" or len(jobs) != count or
            group.get("planned_sims") != count or
            group.get("completed_sims") != count):
        raise ValueError(f"incomplete {name} jobs")
    if jobs:
        fake = {"groups": {name: {"jobs": jobs}},
                "pex_sha256": inputs["pex_sha"],
                "model_sha256": inputs["model_sha"],
                "ngspice_version": inputs["version"]}
        stage6._verified_jobs(root, fake, name)
    return jobs


def _verify_terminal(root: Path, report: dict, inputs: dict) -> None:
    pilot_names = set(report["pilot_cases"])
    pilot_jobs = _verify_group(root, report["groups"].get("pilot", {}),
                               "pilot", inputs, 12)
    grid = _grid(pilot_jobs, WIDTHS_UM, pilot_names, ("ss", "ff"))
    candidate = _select(grid)
    if (grid != report.get("pilot_grid") or
            candidate != report.get("selected_switch_width_um")):
        raise ValueError("switch-width pilot summary differs from jobs")
    if candidate is None:
        if report["status"] != "BLOCKED_SWITCH_WIDTH_PILOT" or report[
                "groups"].get("full"):
            raise ValueError("pilot blocker cannot claim full-grid result")
        return
    full_jobs = _verify_group(root, report["groups"].get("full", {}),
                              "full", inputs, 20)
    full = _grid(full_jobs + [job for job in pilot_jobs if
                 job["switch_width_um"] == candidate], (candidate,),
                 set(report["all_cases"]), ("tt", "ss", "ff"))[0]
    expected = ("SWITCH_WIDTH_CANDIDATE_PENDING_DECODER_AND_NOISE"
                if full["capture_target_met"] else "BLOCKED_SWITCH_WIDTH_FULL")
    if report.get("full_grid") != full or report["status"] != expected:
        raise ValueError("switch-width full summary differs from jobs")


def _measure_group(root: Path, path: Path, report: dict, name: str,
                   jobs: list[dict], inputs: dict, executable: str,
                   timeout_s: int) -> None:
    group = {"status": "RUNNING", "planned_sims": len(jobs),
             "completed_sims": 0, "jobs": jobs}
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
                        f"W={job['switch_width_um']:g}um "
                        f"log_sha256={job['log_sha256']}")
        if index == 1 or index % 4 == 0 or index == len(jobs):
            print(f"PVT switch width {name}: {index}/{len(jobs)} "
                  f"{job['case']} {job['point']['corner']}", flush=True)
    group["status"] = "MEASURED"
    _save(path, report)


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    inputs, cases, selected, pilot_names, source_sha = _source(root)
    script_sha = campaign._sha(Path(__file__))
    folder = root / OUTPUT / f"source_{source_sha[:12]}_runner_{script_sha[:12]}"
    path = folder / "summary.json"
    if path.is_file():
        previous = campaign._read(path)
        if (previous.get("format") != FORMAT or
                previous.get("source_aperture_sha256") != source_sha or
                previous.get("script_sha256") != script_sha or
                previous.get("pex_sha256") != inputs["pex_sha"] or
                previous.get("model_sha256") != inputs["model_sha"] or
                previous.get("pilot_cases") != pilot_names or
                previous.get("widths_um") != list(WIDTHS_UM)):
            raise FileExistsError(f"existing width run differs: {path}")
        if previous["status"] in TERMINAL:
            _verify_terminal(root, previous, inputs)
            return previous
        if not execute:
            return previous
    report = {"format": FORMAT,
              "status": "RUNNING" if execute else "PREPARED",
              "source_aperture_sha256": source_sha,
              "script_sha256": script_sha,
              "pex_sha256": inputs["pex_sha"],
              "model_sha256": inputs["model_sha"],
              "ngspice_version": inputs["version"],
              "budget_v": recovery.BUDGET_V,
              "hold_capacitance_ff": 20,
              "turnoff_start_ns": OFF_NS,
              "widths_um": list(WIDTHS_UM),
              "pilot_cases": pilot_names,
              "all_cases": sorted(cases),
              "new_spice_job_upper_bound": 32,
              "groups": {}, "pilot_grid": [], "full_grid": None,
              "selected_switch_width_um": None,
              "summary_path": str(path.relative_to(root)),
              "history_path": str((folder / "history.log").relative_to(root)),
              "not_signoff": "sparse width screen with schematic SKY130 TG, ideal control and 20 fF hold; no switch/control PEX, transistor noise, corner-calibrated decoder, independent holdout, full PVT or wrapper"}
    _save(path, report)
    if not execute:
        return report
    recovery._event(folder, f"SESSION_START aperture={source_sha} "
                    f"pex={inputs['pex_sha']} runner={script_sha} timeout_s={timeout_s}")
    try:
        executable = campaign._ngspice(inputs["version"])
        pilot = [_job(root, folder, "pilot", cases[name], width, point, inputs)
                 for width in WIDTHS_UM
                 for point in campaign.PVT_POINTS if point[0] != "tt"
                 for name in pilot_names]
        _measure_group(root, path, report, "pilot", pilot,
                       inputs, executable, timeout_s)
        report["pilot_grid"] = _grid(pilot, WIDTHS_UM, set(pilot_names),
                                      ("ss", "ff"))
        width = _select(report["pilot_grid"])
        report["selected_switch_width_um"] = width
        _save(path, report)
        if width is None:
            report["status"] = "BLOCKED_SWITCH_WIDTH_PILOT"
            _save(path, report)
            recovery._event(folder, "STOP no width meets 0.8mV in pilot")
            return report
        recovery._event(folder, f"PILOT_CANDIDATE W={width:g}um")
        full = [_job(root, folder, "full", case, width, point, inputs)
                for point in campaign.PVT_POINTS for case in selected
                if not (case.name in pilot_names and point[0] != "tt")]
        _measure_group(root, path, report, "full", full,
                       inputs, executable, timeout_s)
        report["full_grid"] = _grid(full + [job for job in pilot if
            job["switch_width_um"] == width], (width,), set(cases),
            ("tt", "ss", "ff"))[0]
        report["status"] = (
            "SWITCH_WIDTH_CANDIDATE_PENDING_DECODER_AND_NOISE"
            if report["full_grid"]["capture_target_met"] else
            "BLOCKED_SWITCH_WIDTH_FULL")
        _save(path, report)
        recovery._event(folder, f"COMPLETE status={report['status']} W={width:g}um")
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
