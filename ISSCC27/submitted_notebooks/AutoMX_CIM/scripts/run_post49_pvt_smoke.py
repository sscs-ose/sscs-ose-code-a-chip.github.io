"""Small TT/SS/FF passive-core PEX smoke screen at the frozen operating point.

Select the worst adjacent-level pair from each of four columns in the
117-case TT set plus an idle-zero case. PREPARED does not run ngspice;
MEASURED_PVT_SMOKE is diagnostic only, not a supported-PVT or ADC PASS.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_core_candidate_full_tt import (  # noqa: E402
    LOAD_FF, PWM_UNIT_PS, _checkpoint, _digest, _expected, _provenance, _read,
)
from scripts.run_core_pex_coverage import Case, make_deck  # noqa: E402
from scripts.run_post49_decoder_diagnostic import run as check_decoder_inputs  # noqa: E402

OUTPUT = Path("results/sky130/post49_pvt_smoke")


def model_sections(text: str) -> set[str]:
    """Only declared .lib sections, not model names or include filenames."""
    return {name.lower() for name in re.findall(
        r"(?im)^\s*\.lib\s+(tt|ss|ff)\s*(?:\*.*)?$", text)}


def select_worst_cases(jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Pick extremal cases that define each column's narrowest pooled gap."""
    if not jobs:
        raise ValueError("no measured TT jobs")
    chosen: dict[str, dict] = {}
    pairs = []
    for col in range(4):
        levels: dict[int, list[tuple[float, dict, str]]] = {}
        for job in jobs:
            total = int(job["integer_sums"][col])
            for time in ("t19", "t21"):
                value = float(job["measurements_v"][f"diff_c{col}_{time}"])
                if not math.isfinite(value):
                    raise ValueError("non-finite TT measurement")
                levels.setdefault(total, []).append((value, job, time))
        sums = sorted(levels)
        if len(sums) < 2:
            raise ValueError(f"column {col}: fewer than two measured levels")
        intervals = [(total, max(levels[total], key=lambda item: item[0]),
                      min(levels[total], key=lambda item: item[0])) for total in sums]
        gaps = [(higher[2][0] - lower[1][0], lower, higher)
                for lower, higher in zip(intervals, intervals[1:])]
        gap, lower, higher = min(gaps, key=lambda item: item[0])
        if gap <= 0:
            raise ValueError(f"column {col}: pooled TT levels overlap")
        chosen[lower[1][1]["case"]] = lower[1][1]
        chosen[higher[2][1]["case"]] = higher[2][1]
        pairs.append({"column": col, "lower_sum": lower[0], "higher_sum": higher[0],
                      "lower_case": lower[1][1]["case"],
                      "higher_case": higher[2][1]["case"],
                      "tt_pooled_gap_v": gap})
    zero = next((job for job in jobs if job["case"] == "zero"), None)
    if zero is None or any(int(value) != 0 for value in zero["integer_sums"]):
        raise ValueError("idle-zero case missing or malformed")
    chosen["zero"] = zero
    return list(chosen.values()), pairs


def make_smoke_deck(case: Case, model: Path, pex: Path,
                    point: tuple[str, float, int]) -> str:
    lines = make_deck(case, model, pex, point,
                      load_ff=LOAD_FF, pwm_unit_ps=PWM_UNIT_PS).splitlines()
    tran = next(index for index, line in enumerate(lines) if line.startswith(".tran "))
    lines[tran:tran] = [f".measure tran {kind}_c{col}_t21 FIND V({node}{col}) AT=2.1n"
                        for col in range(4)
                        for kind, node in (("diff", "DIFF"), ("blp", "BLP"),
                                           ("bln", "BLN"))]
    return "\n".join(lines) + "\n"


def summarize_point(jobs: list[dict], pairs: list[dict]) -> dict:
    by_name = {job["case"]: job["measurements_v"] for job in jobs}
    if set(by_name) != {job["case"] for job in jobs}:
        raise ValueError("duplicate measured case")
    report = []
    for pair in pairs:
        col = pair["column"]
        values = []
        for time in ("t19", "t21"):
            lower = float(by_name[pair["lower_case"]][f"diff_c{col}_{time}"])
            higher = float(by_name[pair["higher_case"]][f"diff_c{col}_{time}"])
            values.append(higher - lower)
        report.append({**pair, "gap_at_1p9_v": values[0],
                       "gap_at_2p1_v": values[1],
                       "ordered_at_both_samples": all(value > 0 for value in values)})
    zero = by_name["zero"]
    return {"pairs": report,
            "all_selected_pairs_ordered": all(x["ordered_at_both_samples"] for x in report),
            "minimum_selected_gap_v": min(min(x["gap_at_1p9_v"], x["gap_at_2p1_v"])
                                          for x in report),
            "maximum_idle_zero_abs_v": max(abs(float(zero[f"diff_c{col}_{time}"]))
                                           for col in range(4) for time in ("t19", "t21"))}


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    diagnostic = check_decoder_inputs(root)  # Validates 4.9/4.10 source/hash chain.
    spec = _read(root / "configs/sky130_post49_requirements.json")
    points = spec["pvt_plan"]["first_screen_matrix"]
    if (len(points) != 3 or
            {point["corner"] for point in points} != {"tt", "ss", "ff"} or
            any(point["vdd_v"] != 1.8 or point["temperature_c"] != 25
                for point in points)):
        raise ValueError("first-screen matrix is not TT/SS/FF at 1.8 V/25 C")
    _, _, model, pex = _provenance(root)
    available = model_sections(model.read_text(encoding="utf-8", errors="replace"))
    missing = sorted({point["corner"] for point in points} - available)
    if missing:
        raise ValueError(f"model library lacks .lib sections: {', '.join(missing)}")
    training = _read(root / "results/sky130/core_candidate_full_tt/measured.json")
    holdout = _read(root / "results/sky130/post49_holdout_tt/measured.json")
    selected, pairs = select_worst_cases(training["jobs"] + holdout["jobs"])
    folder = root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = ""
    if ngspice:
        response = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                  timeout=15, check=False)
        version = (response.stdout + response.stderr).strip()
    jobs = []
    for point in points:
        pvt = (point["corner"], point["vdd_v"], point["temperature_c"])
        point_dir = folder / point["corner"]
        point_dir.mkdir(parents=True, exist_ok=True)
        for source in selected:
            case = Case(source["case"], tuple(source["activation_x2"]),
                        tuple(tuple(row) for row in source["ternary_weights"]))
            deck = point_dir / f"{case.name}.spice"
            deck.write_text(make_smoke_deck(case, model, pex, pvt), encoding="utf-8")
            jobs.append({"case": case.name, "point": point,
                         "deck": str(deck.relative_to(root)),
                         "deck_sha256": _digest(deck),
                         "log": str((point_dir / f"{case.name}.log").relative_to(root)),
                         "checkpoint": str((point_dir / f"{case.name}.receipt.json").relative_to(root))})
    baseline = {job["case"]: job["measurements_v"] for job in training["jobs"] + holdout["jobs"]}
    for index, job in enumerate(jobs if execute and not failures else [], start=1):
        deck, log, checkpoint = (root / job[key] for key in ("deck", "log", "checkpoint"))
        saved = _checkpoint(checkpoint, deck_sha256=job["deck_sha256"],
                            pex_sha256=_digest(pex), model_sha256=_digest(model),
                            ngspice_version=version, log=log)
        if saved:
            values = saved["measurements_v"]
            job["reused_checkpoint"] = True
        else:
            if log.is_file():
                log.unlink()
            try:
                result = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                        cwd=deck.parent, text=True, capture_output=True,
                                        timeout=timeout_s, check=False)
            except subprocess.TimeoutExpired:
                failures.append(f"{job['point']['corner']}/{job['case']}: timeout")
                break
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if result.returncode or set(values) != set(_expected()) or not all(
                    math.isfinite(value) for value in values.values()):
                failures.append(f"{job['point']['corner']}/{job['case']}: incomplete ngspice result")
                break
            checkpoint.write_text(json.dumps({
                "status": "PASS", "deck_sha256": job["deck_sha256"],
                "pex_sha256": _digest(pex), "model_sha256": _digest(model),
                "ngspice_version": version, "log_sha256": _digest(log),
                "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        if job["point"]["corner"] == "tt":
            prior = baseline[job["case"]]
            if any(abs(values[key] - float(prior[key])) > 0.001 for key in _expected()):
                failures.append(f"TT replay differs by >1 mV: {job['case']}")
                break
        job["measurements_v"] = values
        print(f"PVT smoke: {index}/{len(jobs)} {job['point']['corner']} {job['case']}", flush=True)
    completed = sum("measurements_v" in job for job in jobs)
    summaries = {}
    if execute and not failures and completed == len(jobs):
        for point in points:
            corner = point["corner"]
            summaries[corner] = summarize_point([job for job in jobs
                                                 if job["point"]["corner"] == corner], pairs)
    report = {"format": "automx-cim-post49-pvt-smoke-v1",
              "status": "FAIL" if failures else "MEASURED_PVT_SMOKE" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "cell49_sha256": diagnostic["cell49_sha256"],
              "old_holdout_sha256": diagnostic["holdout_sha256"],
              "requirements_sha256": diagnostic["requirements_sha256"],
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "model_sections_present": sorted(available),
              "point_matrix": points, "selected_case_names": [job["case"] for job in selected],
              "selected_pairs": pairs, "planned_sims": len(jobs), "completed_sims": completed,
              "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
              "summaries": summaries, "failures": failures, "jobs": jobs,
              "not_signoff": "Selected passive-core PEX cases only; no converter/mismatch/noise/full-PVT or wrapper proof"}
    target = folder / ("measured.json" if execute else "prepared.json")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items() if key != "jobs"}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)
