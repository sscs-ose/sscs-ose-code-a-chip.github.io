"""Screen the 800 fF/50 ps candidate over the 101 existing TT PEX patterns.

This is an evidence-preserving passive-core diagnostic, not ADC, noise, PVT,
wrapper or Stage-8 sign-off. It never overwrites Stage-4.5/4.8 receipts.
Completed per-case simulations may be reused only when deck, PEX, model,
ngspice version, log and measurement hashes still match.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.characterization import build_characterization  # noqa: E402
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.physical.stage5 import CORE, core_pins, parse_spice_subckt_pins  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_core_candidate_pex import make_pex_deck  # noqa: E402
from scripts.run_core_pex_coverage import Case  # noqa: E402

LOAD_FF = 800
PWM_UNIT_PS = 50
OUTPUT = Path("results/sky130/core_candidate_full_tt")
SAMPLE_TIMES = ("t19", "t21")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _expected() -> list[str]:
    return [f"diff_c{col}_t09" for col in range(4)] + [
        f"{kind}_c{col}_{time}" for time in SAMPLE_TIMES
        for col in range(4) for kind in ("diff", "blp", "bln")]


def selected_candidate(report: dict[str, object]) -> dict[str, object]:
    """The chosen point must actually have been measured and ordered in 4.8."""
    if (report.get("format") != "automx-cim-core-candidate-pex-v1" or
            report.get("status") != "MEASURED_PEX_SCREEN" or
            report.get("failures") or report.get("planned_sims") != 22 or
            report.get("completed_sims") != 22):
        raise ValueError("a complete measured Stage-4.8 PEX report is required")
    matches = [point for point in report.get("point_reports", [])
               if point.get("load_ff") == LOAD_FF and
               point.get("pwm_unit_ps") == PWM_UNIT_PS]
    if len(matches) != 1:
        raise ValueError("800 fF/50 ps was not measured in Stage-4.8")
    point = matches[0]
    transfer = point.get("selected_level_transfer", {})
    if (not point.get("all_selected_pairs_ordered") or
            point.get("polarity_mismatch_columns_at_two_times") != 0 or
            any(transfer.get(time, {}).get("adjacent_selected_level_overlap_count") != [0] * 4
                for time in ("1.9", "2.1"))):
        raise ValueError("800 fF/50 ps did not clear the selected Stage-4.8 screen")
    return point


def _provenance(root: Path) -> tuple[dict[str, object], dict[str, object], Path, Path]:
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    build_characterization(root, config)  # Revalidate Stage-4/5 source and receipt hashes.
    coverage_path = root / "results/receipts/physical/core_pex_coverage.json"
    candidate_path = root / "results/sky130/core_candidate_pex/measured.json"
    stage5_path = root / "results/receipts/physical/stage5_summary.json"
    coverage, candidate, stage5 = map(_read, (coverage_path, candidate_path, stage5_path))
    jobs = coverage.get("jobs", [])
    if (coverage.get("format") != "automx-cim-passive-core-pex-coverage-v1" or
            coverage.get("status") != "MEASURED_CORE_ONLY" or
            coverage.get("failures") or coverage.get("job_count") != 101 or
            coverage.get("completed_jobs") != 101 or len(jobs) != 101 or
            coverage.get("points") != [{"corner": "tt", "vdd_v": 1.8,
                                        "temperature_c": 25}] or
            len({job["case"] for job in jobs}) != 101 or
            any(not re.fullmatch(r"[A-Za-z0-9_]+", str(job["case"])) for job in jobs) or
            candidate.get("coverage_sha256") != _digest(coverage_path) or
            candidate.get("stage5_summary_sha256") != _digest(stage5_path)):
        raise ValueError("Stage-4.5/4.8 TT evidence is incomplete or stale")
    selected_candidate(candidate)
    if candidate.get("script_sha256") != _digest(root / "scripts/run_core_candidate_pex.py"):
        raise ValueError("Stage-4.8 generator changed after its measured report")
    pex = Path(stage5["views"]["extracted_spice"]["path"]).resolve()
    if (not pex.is_file() or _digest(pex) != stage5["views"]["extracted_spice"]["sha256"] or
            candidate.get("pex_sha256") != _digest(pex) or
            coverage.get("pex_sha256") != _digest(pex) or
            parse_spice_subckt_pins(pex, f"{CORE}_pex") != core_pins()):
        raise ValueError("Stage-5 PEX view changed")
    manifest = _read(root / "generated/sky130/spice/stage4_manifest.json")
    model = Path(manifest["model_library"]).resolve()
    if (not model.is_file() or candidate.get("model_sha256") != _digest(model) or
            coverage.get("model_library_sha256") != _digest(model)):
        raise ValueError("PDK model library changed")
    selected = set(candidate.get("selected_cases", []))
    by_case = {(item["load_ff"], item["pwm_unit_ps"], item["case"]): item
               for item in candidate.get("decks", [])}
    if len(selected) != 11 or not selected.issubset({job["case"] for job in jobs}) or any(
            (LOAD_FF, PWM_UNIT_PS, name) not in by_case or
            set(by_case[(LOAD_FF, PWM_UNIT_PS, name)].get("measurements", {})) !=
            set(_expected()) - {f"diff_c{col}_t09" for col in range(4)}
            for name in selected):
        raise ValueError("Stage-4.8 selected cases/decks are incomplete")
    for item in candidate["decks"]:
        deck = (root / item["deck"]).resolve()
        if not deck.is_relative_to(root) or not deck.is_file() or _digest(deck) != item["deck_sha256"]:
            raise ValueError(f"Stage-4.8 deck changed: {item['case']}")
    return coverage, candidate, model, pex


def analyze_transfer(jobs: list[dict[str, object]]) -> dict[str, object]:
    """Check measured level ranges, active zero and aperture at 1.9/2.1 ns.

    A positive gap is necessary for a static monotone scalar decoder on this
    *measured set*, but is never an ADC or unmeasured-pattern guarantee.
    """
    if not jobs or any("measurements_v" not in job for job in jobs):
        raise ValueError("all candidate jobs must have finite measurements")
    reports = {}
    for label, times in (("1.9", ("t19",)), ("2.1", ("t21",)),
                         ("1.9_to_2.1_pooled", SAMPLE_TIMES)):
        columns = []
        for col in range(4):
            levels: dict[int, list[float]] = {}
            active_zeros = []
            idle_zeros = []
            polarity_mismatches = 0
            for job in jobs:
                total = int(job["integer_sums"][col])
                activity = sum(abs(int(job["activation_x2"][row]) *
                                   int(job["ternary_weights"][row][col]))
                               for row in range(4))
                for time in times:
                    value = float(job["measurements_v"][f"diff_c{col}_{time}"])
                    if not math.isfinite(value):
                        raise ValueError(f"non-finite c{col} {time} in {job['case']}")
                    levels.setdefault(total, []).append(value)
                    if total == 0:
                        (active_zeros if activity else idle_zeros).append(abs(value))
                    elif value * total <= 0:
                        polarity_mismatches += 1
            ordered = sorted(levels)
            intervals = [{"sum": total, "min_diff_v": min(levels[total]),
                          "max_diff_v": max(levels[total]), "sample_count": len(levels[total])}
                         for total in ordered]
            gaps = [{"lower_sum": lower["sum"], "higher_sum": higher["sum"],
                     "gap_v": higher["min_diff_v"] - lower["max_diff_v"]}
                    for lower, higher in zip(intervals, intervals[1:])]
            columns.append({"column": col, "measured_sum_levels": len(ordered),
                            "min_adjacent_gap_v": min((gap["gap_v"] for gap in gaps), default=None),
                            "overlap_count": sum(gap["gap_v"] <= 0 for gap in gaps),
                            "worst_gap": min(gaps, key=lambda gap: gap["gap_v"]) if gaps else None,
                            "max_active_zero_abs_v": max(active_zeros, default=None),
                            "max_idle_zero_abs_v": max(idle_zeros, default=None),
                            "min_nonzero_abs_v": min((abs(x) for total, values in levels.items()
                                                       if total for x in values), default=None),
                            "polarity_mismatch_count": polarity_mismatches,
                            "intervals": intervals})
        reports[label] = {"all_measured_levels_ordered": all(
            column["overlap_count"] == 0 for column in columns),
            "columns": columns}
    shifts = [abs(float(job["measurements_v"][f"diff_c{col}_t21"]) -
                  float(job["measurements_v"][f"diff_c{col}_t19"]))
              for job in jobs for col in range(4)]
    all_ordered = all(sample["all_measured_levels_ordered"] and all(
        column["polarity_mismatch_count"] == 0 for column in sample["columns"])
        for sample in reports.values())
    return {"transfer_observation": "ORDERED_IN_MEASURED_SET" if all_ordered
            else "OVERLAP_OR_POLARITY_OBSERVED",
            "samples": reports, "max_1p9_to_2p1_shift_abs_v": max(shifts),
            "scope_warning": "101 TT passive-core PEX patterns only; no decoder/noise/PVT/ADC PASS"}


def _checkpoint(path: Path, *, deck_sha256: str, pex_sha256: str,
                model_sha256: str, ngspice_version: str, log: Path) -> dict[str, object] | None:
    if not path.is_file() or not log.is_file():
        return None
    try:
        receipt = _read(path)
        if (receipt.get("status") != "PASS" or
                receipt.get("deck_sha256") != deck_sha256 or
                receipt.get("pex_sha256") != pex_sha256 or
                receipt.get("model_sha256") != model_sha256 or
                receipt.get("ngspice_version") != ngspice_version or
                receipt.get("log_sha256") != _digest(log)):
            return None
        values = receipt.get("measurements_v", {})
        if set(values) != set(_expected()) or not all(math.isfinite(float(x)) for x in values.values()):
            return None
        return receipt
    except (OSError, ValueError, TypeError):
        return None


def _matches_selected(values: dict[str, float], selected_deck: dict[str, object] | None) -> bool:
    if selected_deck is None:
        return True
    return all(key in values and abs(values[key] - float(old)) <= 1e-3
               for key, old in selected_deck["measurements"].items())


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 180) -> dict[str, object]:
    root = Path(root).resolve()
    coverage, candidate, model, pex = _provenance(root)
    folder = root / OUTPUT / f"c{LOAD_FF}ff_pwm{PWM_UNIT_PS}ps"
    folder.mkdir(parents=True, exist_ok=True)
    selected = {(item["load_ff"], item["pwm_unit_ps"], item["case"]): item
                for item in candidate["decks"]}
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    version = ""
    if ngspice:
        response = subprocess.run([ngspice, "-v"], text=True, capture_output=True,
                                  timeout=15, check=False)
        version = (response.stdout + response.stderr).strip()
    jobs = []
    for source in coverage["jobs"]:
        name = str(source["case"])
        case = Case(name, tuple(int(x) for x in source["activation_x2"]),
                    tuple(tuple(int(x) for x in row) for row in source["ternary_weights"]))
        if list(case.sums) != [int(value) for value in source["integer_sums"]]:
            raise ValueError(f"Stage-4.5 integer sums changed: {name}")
        deck = folder / f"{name}.spice"
        deck.write_text(make_pex_deck(case, model, pex, LOAD_FF, PWM_UNIT_PS), encoding="utf-8")
        digest = _digest(deck)
        matched = selected.get((LOAD_FF, PWM_UNIT_PS, name))
        if matched and digest != matched["deck_sha256"]:
            raise ValueError(f"selected Stage-4.8 deck differs at {name}")
        log = folder / f"{name}.log"
        checkpoint = folder / f"{name}.receipt.json"
        jobs.append({"case": name, "activation_x2": list(case.acts),
                     "ternary_weights": [list(row) for row in case.weights],
                     "integer_sums": list(case.sums),
                     "deck": str(deck.relative_to(root)), "deck_sha256": digest,
                     "log": str(log.relative_to(root)),
                     "checkpoint": str(checkpoint.relative_to(root))})
    for index, job in enumerate(jobs if execute and not failures else [], start=1):
        name = job["case"]
        deck, log, checkpoint = (root / job[key] for key in ("deck", "log", "checkpoint"))
        reused = _checkpoint(checkpoint, deck_sha256=job["deck_sha256"],
                             pex_sha256=_digest(pex), model_sha256=_digest(model),
                             ngspice_version=version, log=log)
        if reused:
            if not _matches_selected(reused["measurements_v"],
                                     selected.get((LOAD_FF, PWM_UNIT_PS, name))):
                failures.append(f"{name}: checkpoint differs from Stage-4.8 by >1 mV")
                break
            job["measurements_v"] = reused["measurements_v"]
            job["reused_checkpoint"] = True
            if index == 1 or index % 10 == 0 or index == len(jobs):
                print(f"Candidate TT PEX: {index}/{len(jobs)} cases complete ({name}, checkpoint)", flush=True)
            continue
        if log.is_file():
            log.unlink()  # Never parse stale output after a changed deck or failed run.
        try:
            result = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                    cwd=folder, text=True, capture_output=True,
                                    timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired:
            failures.append(f"{name}: ngspice timeout after {timeout_s}s")
            break
        output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        values = parse_measurements(output, _expected())
        if (result.returncode or len(values) != len(_expected()) or
                not all(math.isfinite(value) for value in values.values())):
            failures.append(f"{name}: ngspice exit {result.returncode}, incomplete measures; see {log}")
            break
        matched = selected.get((LOAD_FF, PWM_UNIT_PS, name))
        if not _matches_selected(values, matched):
            failures.append(f"{name}: Stage-4.8 sample differs by >1 mV")
            break
        job["measurements_v"] = values
        checkpoint.write_text(json.dumps({
            "status": "PASS", "deck_sha256": job["deck_sha256"],
            "pex_sha256": _digest(pex), "model_sha256": _digest(model),
            "ngspice_version": version, "log_sha256": _digest(log),
            "measurements_v": values}, indent=2) + "\n", encoding="utf-8")
        if index == 1 or index % 10 == 0 or index == len(jobs):
            print(f"Candidate TT PEX: {index}/{len(jobs)} cases complete ({name})", flush=True)
    completed = sum("measurements_v" in job for job in jobs)
    analysis = analyze_transfer(jobs) if execute and not failures and completed == 101 else None
    report = {"format": "automx-cim-core-candidate-full-tt-v1",
              "status": "FAIL" if failures else "MEASURED_TT_CANDIDATE_SCREEN" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "101-case 800 fF/50 ps TT passive-core PEX screen; not ADC/noise/PVT sign-off",
              "load_ff": LOAD_FF, "pwm_unit_ps": PWM_UNIT_PS,
              "stage4p5_sha256": _digest(root / "results/receipts/physical/core_pex_coverage.json"),
              "stage4p8_sha256": _digest(root / "results/sky130/core_candidate_pex/measured.json"),
              "stage5_summary_sha256": _digest(root / "results/receipts/physical/stage5_summary.json"),
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "ngspice_version": version or None,
              "planned_sims": len(jobs), "completed_sims": completed,
              "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
              "analysis": analysis, "failures": failures, "jobs": jobs}
    target = root / OUTPUT / ("measured.json" if execute else "prepared.json")
    report["report_path"] = str(target.relative_to(root))
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=180)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items() if key != "jobs"}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)
