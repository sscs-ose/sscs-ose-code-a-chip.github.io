"""Small schematic-only screen for a separable passive-core transfer window.

The screen varies *external* bitline load and PWM unit width using the worst
Stage-4.6 TT cases. It is not a physical redesign, PEX validation or ADC PASS.
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

from automx_cim.characterization import build_characterization  # noqa: E402
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.physical.stage5 import CORE, core_pins, parse_spice_subckt_pins  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_core_pex_coverage import Case, make_deck  # noqa: E402


POINTS = ((200, 100), (400, 100), (400, 75), (800, 50))  # fF, ps/code unit
OUTPUT = Path("results/sky130/core_transfer_design_space")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def selected_cases(analysis: dict[str, object]) -> list[str]:
    # The first, fast screen asks only whether the four worst sum-pair
    # reversals can be removed. PEX zero-offset checks come after downselect.
    cases: set[str] = set()
    for column in analysis["columns"]:
        if not column["overlaps"]:
            raise ValueError(f"no selected overlap in column {column['column']}")
        pair = column["overlaps"][0]
        cases.add(pair["lower_sum_case"]["case"])
        cases.add(pair["higher_sum_case"]["case"])
    return sorted(cases)


def make_screen_deck(case: Case, model: Path, schematic: Path,
                     load_ff: int, pwm_unit_ps: int) -> str:
    """Preserve Stage-4.6 stimulus except explicit C/load and PWM width."""
    if not 50 <= load_ff <= 2000 or not 10 <= pwm_unit_ps <= 100:
        raise ValueError("unsupported diagnostic load/PWM width")
    # Use only the original four-argument API. Jupyter may still have the
    # pre-4.7 coverage module cached, whose make_deck lacks optional kwargs.
    # The baseline deck is identical in either version (200 fF, 100 ps/unit).
    lines = make_deck(case, model, schematic, ("tt", 1.8, 25)).splitlines()
    for col in range(4):
        for side in ("P", "N"):
            label = f"CBL{side}{col} "
            index = next(i for i, line in enumerate(lines) if line.startswith(label))
            expected = " 200f IC={VDD}"
            if lines[index].count(expected) != 1:
                raise ValueError(f"unexpected baseline bitline capacitance: {label}")
            lines[index] = lines[index].replace(expected, f" {load_ff}f IC={{VDD}}")
    for row, activation in enumerate(case.acts):
        for phase, magnitude in (("WLP", max(activation, 0)),
                                 ("WLN", max(-activation, 0))):
            if not magnitude:
                continue
            label = f"V{phase}{row} "
            index = next(i for i, line in enumerate(lines) if line.startswith(label))
            expected = f" {magnitude * 100}p 5n)"
            if lines[index].count(expected) != 1:
                raise ValueError(f"unexpected baseline PWM width: {label}")
            lines[index] = lines[index].replace(expected,
                                                f" {magnitude * pwm_unit_ps}p 5n)")
    xmacro = next(i for i, line in enumerate(lines) if line.startswith("XMACRO "))
    lines[xmacro] = lines[xmacro].rsplit(" ", 1)[0] + f" {CORE}"
    tran = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    lines[tran:tran] = [f".measure tran {kind}_c{col}_t21 FIND V({node}{col}) AT=2.1n"
                        for col in range(4)
                        for kind, node in (("diff", "DIFF"), ("blp", "BLP"), ("bln", "BLN"))]
    return "\n".join(lines) + "\n"


def _expected() -> list[str]:
    return [f"{kind}_c{col}_{time}" for col in range(4)
            for kind in ("diff", "blp", "bln") for time in ("t19", "t21")]


def summarize_point(analysis: dict[str, object],
                    measured: dict[str, dict[str, float]],
                    *, load_ff: int, pwm_unit_ps: int) -> dict[str, object]:
    pairs = []
    for column in analysis["columns"]:
        col = int(column["column"])
        pair = column["overlaps"][0]
        lower = pair["lower_sum_case"]["case"]
        higher = pair["higher_sum_case"]["case"]
        for time in ("t19", "t21"):
            low = measured[lower][f"diff_c{col}_{time}"]
            high = measured[higher][f"diff_c{col}_{time}"]
            pairs.append({"column": col, "time_ns": 1.9 if time == "t19" else 2.1,
                          "lower_case": lower, "higher_case": higher,
                          "lower_sum": pair["lower_sum"], "higher_sum": pair["higher_sum"],
                          "lower_diff_v": low, "higher_diff_v": high,
                          "reversal_v": low - high,
                          "lower_cm_v": (measured[lower][f"blp_c{col}_{time}"] +
                                         measured[lower][f"bln_c{col}_{time}"]) / 2,
                          "higher_cm_v": (measured[higher][f"blp_c{col}_{time}"] +
                                          measured[higher][f"bln_c{col}_{time}"]) / 2})
    ordered = all(item["reversal_v"] < 0 for item in pairs)
    return {"load_ff": load_ff, "pwm_unit_ps": pwm_unit_ps,
            "all_selected_pairs_ordered": ordered,
            "minimum_selected_ordering_margin_v": min(-item["reversal_v"] for item in pairs),
            "minimum_selected_nonzero_swing_abs_v": min(
                abs(voltage) for item in pairs
                for voltage in (item["lower_diff_v"], item["higher_diff_v"])),
            "pairs": pairs,
            "interpretation": "candidate for PEX/full-range recheck" if ordered
            else "selected schematic pairs still overlap; not a static-differential solution"}


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 180) -> dict[str, object]:
    root = Path(root).resolve()
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    build_characterization(root, config)
    diagnosis_path = root / "results/sky130/core_transfer_diagnostics/measured.json"
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    coverage_path = root / "results/receipts/physical/core_pex_coverage.json"
    summary_path = root / "results/receipts/physical/stage5_summary.json"
    if (diagnosis.get("format") != "automx-cim-core-transfer-diagnostic-v1" or
            diagnosis.get("status") != "MEASURED_DIAGNOSTIC" or
            diagnosis.get("completed_sims") != diagnosis.get("planned_sims") or
            diagnosis.get("coverage_receipt_sha256") != _digest(coverage_path) or
            diagnosis.get("stage5_summary_sha256") != _digest(summary_path)):
        raise ValueError("measured Stage-4.6 diagnostic is missing/stale")
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    if coverage.get("status") != "MEASURED_CORE_ONLY" or coverage.get("completed_jobs") != 101:
        raise ValueError("101-case TT passive-core coverage is required")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    schematic = Path(summary["views"]["spice"]["path"]).resolve()
    if (_digest(schematic) != summary["views"]["spice"]["sha256"] or
            parse_spice_subckt_pins(schematic, CORE) != core_pins()):
        raise ValueError("Stage-5 schematic view changed")
    manifest = json.loads((root / "generated/sky130/spice/stage4_manifest.json").read_text(encoding="utf-8"))
    model = Path(manifest["model_library"]).resolve()
    if _digest(model) != diagnosis["model_library_sha256"]:
        raise ValueError("PDK model library changed")
    cases = selected_cases(diagnosis["analysis"])
    jobs_by_name = {item["case"]: item for item in coverage["jobs"]}
    if any(case not in jobs_by_name for case in cases):
        raise ValueError("Stage-4.6 selected case missing from 101-case receipt")
    output_dir = root / OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    decks = []
    point_reports = []
    for load_ff, pwm_unit_ps in POINTS:
        measured = {}
        folder = output_dir / f"c{load_ff}ff_pwm{pwm_unit_ps}ps"
        folder.mkdir(parents=True, exist_ok=True)
        for name in cases:
            source = jobs_by_name[name]
            case = Case(name, tuple(int(x) for x in source["activation_x2"]),
                        tuple(tuple(int(x) for x in row) for row in source["ternary_weights"]))
            deck = folder / f"{name}.spice"
            deck.write_text(make_screen_deck(case, model, schematic, load_ff, pwm_unit_ps),
                            encoding="utf-8")
            log = folder / f"{name}.log"
            item = {"load_ff": load_ff, "pwm_unit_ps": pwm_unit_ps, "case": name,
                    "deck": str(deck.relative_to(root)), "deck_sha256": _digest(deck),
                    "log": str(log.relative_to(root))}
            decks.append(item)
            if execute and ngspice and not failures:
                if log.is_file():
                    log.unlink()
                try:
                    completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                               cwd=folder, text=True, capture_output=True,
                                               timeout=timeout_s, check=False)
                except subprocess.TimeoutExpired:
                    item["returncode"] = "TIMEOUT"
                    failures.append(f"{load_ff}fF/{pwm_unit_ps}ps/{name}: timeout; inspect {deck}")
                    continue
                item["returncode"] = completed.returncode
                content = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
                values = parse_measurements(content, _expected())
                if completed.returncode or len(values) != len(_expected()) or not all(
                        math.isfinite(value) for value in values.values()):
                    failures.append(f"{load_ff}fF/{pwm_unit_ps}ps/{name}: incomplete ngspice result; inspect {log}")
                else:
                    measured[name] = values
                    item["measurements"] = values
                    if (load_ff, pwm_unit_ps) == (200, 100):
                        baseline = next((entry.get("measurements") for entry in diagnosis["decks"]
                                         if entry["case"] == name and entry["view"] == "schematic"), None)
                        if not baseline:
                            failures.append(f"{name}: Stage-4.6 schematic baseline is missing")
                        else:
                            for col in range(4):
                                for stem, old in (("diff", "d"), ("blp", "p"), ("bln", "n")):
                                    deviation = abs(values[f"{stem}_c{col}_t19"] -
                                                    baseline[f"{old}_c{col}_p1900"])
                                    if deviation > 1e-3:
                                        failures.append(f"{name} c{col} {stem}: baseline mismatch "
                                                        f"{deviation:.6g} V")
        if execute and not failures:
            point_reports.append(summarize_point(diagnosis["analysis"], measured,
                                                 load_ff=load_ff, pwm_unit_ps=pwm_unit_ps))
    report = {"format": "automx-cim-core-transfer-design-space-v1",
              "status": "FAIL" if failures else "MEASURED_SCHEMATIC_SCREEN" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "four external C/PWM points, selected schematic cases only; no PEX/ADC/PVT PASS",
              "source_sha256": _digest(Path(__file__)),
              "diagnostic_sha256": _digest(diagnosis_path),
              "coverage_sha256": _digest(coverage_path),
              "stage5_summary_sha256": _digest(summary_path),
              "schematic_sha256": _digest(schematic), "model_sha256": _digest(model),
              "selected_cases": cases, "points": [{"load_ff": a, "pwm_unit_ps": b} for a, b in POINTS],
              "planned_sims": len(decks),
              "completed_sims": sum("measurements" in item for item in decks),
              "point_reports": point_reports, "decks": decks, "failures": failures}
    target = output_dir / ("measured.json" if execute else "prepared.json")
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
    print(json.dumps({key: value for key, value in result.items() if key != "decks"}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)
