"""Analyze measured core transfer and compare targeted schematic/PEX stimuli.

This is a diagnostic for the passive 4x4 core, not an ADC or Stage-8 receipt.
Preparing decks never rewrites the 101-case coverage receipt or Stage-5 views.
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
from scripts.run_core_pex_coverage import Case, make_deck  # noqa: E402


SAMPLE_PS = (500, 700, 900, 1100, 1300, 1500, 1700, 1800, 1900, 2000, 2100)
OUTPUT = Path("results/sky130/core_transfer_diagnostics")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _number(job: dict[str, object], key: str) -> float:
    value = float(job["measurements_v"][key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key} in {job['case']}")
    return value


def analyze_jobs(jobs: list[dict[str, object]]) -> dict[str, object]:
    """Find same-column signed-sum overlaps at the measured 1.9 ns sample."""
    if not jobs:
        raise ValueError("no measured jobs")
    names = [str(job["case"]) for job in jobs]
    if len(set(names)) != len(names):
        raise ValueError("case names must be unique")
    columns = []
    chosen = set()
    if "zero" in names:
        chosen.add("zero")
    for col in range(4):
        levels: dict[int, list[dict[str, object]]] = {}
        zero_cases = []
        for job in jobs:
            total = int(job["integer_sums"][col])
            voltage = _number(job, f"diff_c{col}_t19")
            blp = _number(job, f"blp_c{col}_t19")
            bln = _number(job, f"bln_c{col}_t19")
            entry = {"case": str(job["case"]), "sum": total,
                     "activity": sum(abs(int(job["activation_x2"][row]) *
                                         int(job["ternary_weights"][row][col]))
                                     for row in range(4)),
                     "diff_v": voltage, "common_mode_v": (blp + bln) / 2}
            levels.setdefault(total, []).append(entry)
            if total == 0:
                zero_cases.append(entry)
        if not zero_cases:
            raise ValueError(f"column {col} has no measured zero case")
        worst_zero = min(zero_cases, key=lambda item: (-abs(item["diff_v"]), item["case"]))
        chosen.add(worst_zero["case"])
        ordered = sorted(levels)
        overlaps = []
        for lower, higher in zip(ordered, ordered[1:]):
            lower_max = sorted(levels[lower], key=lambda item: (-item["diff_v"], item["case"]))[0]
            higher_min = sorted(levels[higher], key=lambda item: (item["diff_v"], item["case"]))[0]
            reversal = lower_max["diff_v"] - higher_min["diff_v"]
            if reversal >= 0:
                overlaps.append({"lower_sum": lower, "higher_sum": higher,
                                 "reversal_v": reversal,
                                 "lower_sum_case": lower_max, "higher_sum_case": higher_min})
        overlaps.sort(key=lambda item: (-item["reversal_v"], item["lower_sum"]))
        if overlaps:
            chosen.update((overlaps[0]["lower_sum_case"]["case"],
                           overlaps[0]["higher_sum_case"]["case"]))
        columns.append({"column": col, "measured_sum_levels": len(ordered),
                        "zero_diff_range_v": [min(x["diff_v"] for x in zero_cases),
                                              max(x["diff_v"] for x in zero_cases)],
                        "worst_zero_case": worst_zero,
                        "adjacent_measured_level_overlap_count": len(overlaps),
                        "overlaps": overlaps})
    return {"status": "OVERLAP_OBSERVED" if any(c["overlaps"] for c in columns)
            else "NO_OVERLAP_IN_MEASURED_CASES",
            "sample_time_ns": 1.9, "scope": "101-case passive-core TT sample; not an ADC decision",
            "columns": columns, "selected_cases": sorted(chosen)}


def make_targeted_deck(case: Case, model: Path, netlist: Path, *, extracted: bool,
                       sample_ps: tuple[int, ...] = SAMPLE_PS) -> str:
    """Identical drivers/load for schematic and PEX; add BLP/BLN/diff samples."""
    deck = make_deck(case, model, netlist, ("tt", 1.8, 25))
    lines = deck.splitlines()
    top = f"{CORE}_pex" if extracted else CORE
    xmacro = next(i for i, line in enumerate(lines) if line.startswith("XMACRO "))
    lines[xmacro] = lines[xmacro].rsplit(" ", 1)[0] + f" {top}"
    tran = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    extra = []
    for ps in sample_ps:
        if not 0 <= ps <= 3000:
            raise ValueError(f"sample {ps} ps outside transient interval")
        for col in range(4):
            extra.extend((f".measure tran d_c{col}_p{ps} FIND V(DIFF{col}) AT={ps}p",
                          f".measure tran p_c{col}_p{ps} FIND V(BLP{col}) AT={ps}p",
                          f".measure tran n_c{col}_p{ps} FIND V(BLN{col}) AT={ps}p"))
    lines[tran:tran] = extra
    return "\n".join(lines) + "\n"


def _expected(sample_ps: tuple[int, ...]) -> list[str]:
    return [f"{kind}_c{col}_p{ps}" for ps in sample_ps for col in range(4)
            for kind in ("d", "p", "n")]


def _safe_deck(root: Path, relative: str, digest: str) -> None:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or _digest(path) != digest:
        raise ValueError(f"coverage stimulus deck missing/changed: {relative}")


def _selected_time_comparison(analysis: dict[str, object],
                              measured: dict[str, dict[str, dict[str, float]]]) -> list[dict[str, object]]:
    comparisons = []
    for column in analysis["columns"]:
        col = column["column"]
        if not column["overlaps"]:
            continue
        pair = column["overlaps"][0]
        low = pair["lower_sum_case"]["case"]
        high = pair["higher_sum_case"]["case"]
        for view in ("schematic", "pex"):
            data_low, data_high = measured[low][view], measured[high][view]
            samples = []
            for ps in SAMPLE_PS:
                lv, hv = data_low[f"d_c{col}_p{ps}"], data_high[f"d_c{col}_p{ps}"]
                samples.append({"time_ns": ps / 1000, "lower_sum_diff_v": lv,
                                "higher_sum_diff_v": hv, "reversal_v": lv - hv,
                                "lower_sum_cm_v": (data_low[f"p_c{col}_p{ps}"] +
                                                   data_low[f"n_c{col}_p{ps}"]) / 2,
                                "higher_sum_cm_v": (data_high[f"p_c{col}_p{ps}"] +
                                                    data_high[f"n_c{col}_p{ps}"]) / 2})
            comparisons.append({"column": col, "view": view, "lower_case": low,
                                "higher_case": high, "samples": samples})
    return comparisons


def _validated_checkpoint(root: Path, current: dict[str, object],
                          previous: dict[str, object]) -> dict[str, float] | None:
    """Accept only the same deck with complete measurements in its saved log."""
    for field in ("case", "view", "deck", "deck_sha256", "log"):
        if current.get(field) != previous.get(field):
            return None
    if previous.get("returncode") != 0 or not isinstance(previous.get("measurements"), dict):
        return None
    log = root / str(current["log"])
    if not log.is_file() or not log.stat().st_size:
        return None
    if previous.get("log_sha256") and previous["log_sha256"] != _digest(log):
        return None
    expected = _expected(SAMPLE_PS)
    parsed = parse_measurements(log.read_text(encoding="utf-8", errors="replace"), expected)
    recorded = previous["measurements"]
    if any(name not in parsed or name not in recorded or
           not math.isfinite(parsed[name]) or parsed[name] != recorded[name]
           for name in expected):
        return None
    return {name: parsed[name] for name in expected}


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict[str, object]:
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    root = Path(root).resolve()
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    build_characterization(root, config)  # Stage-4/5 PASS receipts and hashes.
    coverage_path = root / "results/receipts/physical/core_pex_coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    jobs = coverage.get("jobs", [])
    if (coverage.get("format") != "automx-cim-passive-core-pex-coverage-v1" or
            coverage.get("status") != "MEASURED_CORE_ONLY" or coverage.get("failures") or
            coverage.get("job_count") != len(jobs) or
            coverage.get("completed_jobs") != len(jobs) or
            len(jobs) != 101 or coverage.get("points") !=
            [{"corner": "tt", "vdd_v": 1.8, "temperature_c": 25}]):
        raise ValueError("a completed 101-case TT core-coverage receipt is required")
    for job in jobs:
        if not re.fullmatch(r"[A-Za-z0-9_]+", str(job["case"])):
            raise ValueError(f"unsafe case name: {job['case']}")
        _safe_deck(root, str(job["deck"]), str(job["deck_sha256"]))
    summary_path = root / "results/receipts/physical/stage5_summary.json"
    if coverage.get("stage5_summary_sha256") != _digest(summary_path):
        raise ValueError("coverage does not match the current Stage-5 summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    views = {name: Path(summary["views"][name]["path"]).resolve()
             for name in ("spice", "extracted_spice")}
    for name, path in views.items():
        if _digest(path) != summary["views"][name]["sha256"]:
            raise ValueError(f"Stage-5 {name} view changed")
    if parse_spice_subckt_pins(views["spice"], CORE) != core_pins():
        raise ValueError("schematic pin order changed")
    if parse_spice_subckt_pins(views["extracted_spice"], f"{CORE}_pex") != core_pins():
        raise ValueError("PEX pin order changed")
    manifest = json.loads((root / "generated/sky130/spice/stage4_manifest.json").read_text(encoding="utf-8"))
    model = Path(manifest["model_library"]).resolve()
    if (coverage.get("pex_sha256") != _digest(views["extracted_spice"]) or
            coverage.get("model_library_sha256") != _digest(model)):
        raise ValueError("coverage PEX/PDK provenance changed")

    analysis = analyze_jobs(jobs)
    job_by_case = {job["case"]: job for job in jobs}
    output_dir = root / OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    decks = []
    measured: dict[str, dict[str, dict[str, float]]] = {}
    for case_name in analysis["selected_cases"]:
        item = job_by_case[case_name]
        case = Case(case_name, tuple(int(x) for x in item["activation_x2"]),
                    tuple(tuple(int(x) for x in row) for row in item["ternary_weights"]))
        measured[case_name] = {}
        for view in ("schematic", "pex"):
            deck = output_dir / f"{case_name}_{view}.spice"
            deck.write_text(make_targeted_deck(case, model,
                                               views["spice" if view == "schematic" else "extracted_spice"],
                                               extracted=view == "pex"), encoding="utf-8")
            log = deck.with_suffix(".log")
            entry = {"case": case_name, "view": view,
                     "deck": str(deck.relative_to(root)), "deck_sha256": _digest(deck),
                     "log": str(log.relative_to(root))}
            decks.append(entry)

    target = output_dir / ("measured.json" if execute else "prepared.json")
    current_views = {name: _digest(path) for name, path in views.items()}
    current_model = _digest(model)
    old = {}
    if execute and target.is_file():
        try:
            old = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old = {}
    old_entries = {}
    old_analysis = old.get("analysis") if isinstance(old.get("analysis"), dict) else {}
    if (old.get("format") == "automx-cim-core-transfer-diagnostic-v1" and
            old.get("views_sha256") == current_views and
            old.get("model_library_sha256") == current_model and
            old.get("sample_times_ps") == list(SAMPLE_PS) and
            old_analysis.get("selected_cases") == analysis["selected_cases"] and
            isinstance(old.get("decks"), list)):
        old_entries = {(entry.get("case"), entry.get("view")): entry
                       for entry in old["decks"] if isinstance(entry, dict)}
        if len(old_entries) != len(old["decks"]):
            old_entries = {}
    reused = 0
    for entry in decks:
        previous = old_entries.get((entry["case"], entry["view"]))
        values = _validated_checkpoint(root, entry, previous) if previous else None
        if values is not None:
            entry["measurements"] = values
            entry["returncode"] = 0
            entry["log_sha256"] = _digest(root / entry["log"])
            reused += 1

    def write_report(status: str, comparisons: list[dict[str, object]]) -> dict[str, object]:
        report = {"format": "automx-cim-core-transfer-diagnostic-v1",
                  "status": status,
                  "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                  "scope": "selected schematic/PEX same-stimulus TT samples; no wrapper/ADC/PVT PASS",
                  "script_sha256": _digest(Path(__file__)),
                  "coverage_receipt_sha256": _digest(coverage_path),
                  "stage5_summary_sha256": _digest(summary_path),
                  "views_sha256": current_views,
                  "model_library_sha256": current_model,
                  "sample_times_ps": list(SAMPLE_PS),
                  "analysis": analysis, "planned_sims": len(decks),
                  "completed_sims": sum("measurements" in entry for entry in decks),
                  "reused_checkpoints": reused,
                  "decks": decks, "selected_pair_time_comparison": comparisons,
                  "failures": failures,
                  "report_path": str(target.relative_to(root))}
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        return report

    if execute:
        print(f"Validated transfer checkpoints: {reused}/{len(decks)}", flush=True)
        write_report("IN_PROGRESS", [])
    for entry in decks:
        if not execute or not ngspice or failures:
            break
        case_name = entry["case"]
        view = entry["view"]
        deck = root / entry["deck"]
        log = root / entry["log"]
        if "measurements" not in entry:
            if log.is_file():
                log.unlink()  # The current job had no validated checkpoint.
            try:
                completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                           cwd=output_dir, text=True, capture_output=True,
                                           timeout=timeout_s, check=False)
            except subprocess.TimeoutExpired:
                entry["returncode"] = "TIMEOUT"
                failures.append(f"{case_name}/{view}: timeout after {timeout_s}s; "
                                f"inspect {log} and {deck}")
                break
            entry["returncode"] = completed.returncode
            content = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(content, _expected(SAMPLE_PS))
            if completed.returncode or not log.is_file() or len(values) != len(_expected(SAMPLE_PS)) or not all(
                    math.isfinite(x) for x in values.values()):
                failures.append(f"{case_name}/{view}: ngspice exit {completed.returncode}; inspect {log}")
                break
            entry["measurements"] = values
            entry["log_sha256"] = _digest(log)
            write_report("IN_PROGRESS", [])
            completed_count = sum("measurements" in item for item in decks)
            if completed_count == len(decks) or completed_count % 4 == 0:
                print(f"Transfer diagnostic: {completed_count}/{len(decks)} "
                      f"({case_name}/{view})", flush=True)
        values = entry["measurements"]
        measured[case_name][view] = values
        if view == "pex":
            item = job_by_case[case_name]
            for col in range(4):
                for prefix, baseline in (("d", "diff"), ("p", "blp"), ("n", "bln")):
                    observed = values[f"{prefix}_c{col}_p1900"]
                    original = _number(item, f"{baseline}_c{col}_t19")
                    if abs(observed - original) > 1e-3:
                        failures.append(f"{case_name} c{col} {prefix}: reproduced PEX sample "
                                        f"differs by {abs(observed-original):.6g} V")
    comparisons = (_selected_time_comparison(analysis, measured)
                   if execute and not failures else [])
    return write_report("FAIL" if failures else "MEASURED_DIAGNOSTIC" if execute else "PREPARED",
                        comparisons)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true", help="execute selected ngspice simulations")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("decks", "selected_pair_time_comparison")}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)
