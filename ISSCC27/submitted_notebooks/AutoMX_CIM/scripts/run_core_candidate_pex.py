"""PEX recheck of schematic-small-swing candidates; never ADC sign-off.

Requires the measured 101-case TT receipt and completed Stage-4.6/4.7
diagnostics. Only the candidate C/PWM settings and selected cases are run.
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
from scripts.run_core_pex_coverage import Case  # noqa: E402
from scripts.run_core_transfer_design_space import make_screen_deck, summarize_point  # noqa: E402
from scripts.run_core_transfer_diagnostics import analyze_jobs  # noqa: E402


OUTPUT = Path("results/sky130/core_candidate_pex")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def candidate_points(screen: dict[str, object]) -> list[tuple[int, int]]:
    """Downselect ordered schematic points; do not treat them as sign-off."""
    reports = screen.get("point_reports", [])
    if not reports or screen.get("status") != "MEASURED_SCHEMATIC_SCREEN":
        raise ValueError("a measured schematic design-space screen is required")
    ranked = sorted((point for point in reports if point.get("all_selected_pairs_ordered")
                     and float(point.get("minimum_selected_ordering_margin_v", 0)) > 0),
                    key=lambda point: (-float(point["minimum_selected_ordering_margin_v"]),
                                       int(point["load_ff"]), int(point["pwm_unit_ps"])))
    if not ranked:
        raise ValueError("no ordered schematic candidate; redesign before PEX recheck")
    return [(int(item["load_ff"]), int(item["pwm_unit_ps"])) for item in ranked[:2]]


def make_pex_deck(case: Case, model: Path, pex: Path,
                  load_ff: int, pwm_unit_ps: int) -> str:
    """Reuse the Stage-4.7 stimulus, substituting only the PEX subcircuit."""
    lines = make_screen_deck(case, model, pex, load_ff, pwm_unit_ps).splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith("XMACRO "))
    if not lines[index].endswith(f" {CORE}"):
        raise ValueError("unexpected schematic subcircuit in candidate deck")
    lines[index] += "_pex"
    return "\n".join(lines) + "\n"


def _expected() -> list[str]:
    return [f"{kind}_c{col}_{time}" for col in range(4)
            for kind in ("diff", "blp", "bln") for time in ("t19", "t21")]


def summarize_candidate(analysis: dict[str, object],
                        coverage_jobs: dict[str, dict[str, object]],
                        measured: dict[str, dict[str, float]],
                        *, load_ff: int, pwm_unit_ps: int) -> dict[str, object]:
    """Selected-case ordering and active-zero checks at both sample times."""
    pairs = summarize_point(analysis, measured, load_ff=load_ff,
                            pwm_unit_ps=pwm_unit_ps)
    samples = {}
    zero_offsets = []
    nonzero_swings = []
    polarity_mismatches = 0
    for time in ("t19", "t21"):
        jobs = []
        for name, values in measured.items():
            source = coverage_jobs[name]
            sums = source["integer_sums"]
            normalized = {}
            for col in range(4):
                diff = values[f"diff_c{col}_{time}"]
                if int(sums[col]) == 0:
                    zero_offsets.append(abs(diff))
                else:
                    nonzero_swings.append(abs(diff))
                    polarity_mismatches += int(diff * int(sums[col]) <= 0)
                for stem in ("diff", "blp", "bln"):
                    normalized[f"{stem}_c{col}_t19"] = values[f"{stem}_c{col}_{time}"]
            jobs.append({"case": name, "integer_sums": sums,
                         "activation_x2": source["activation_x2"],
                         "ternary_weights": source["ternary_weights"],
                         "measurements_v": normalized})
        analyzed = analyze_jobs(jobs)
        samples["1.9" if time == "t19" else "2.1"] = {
            "status": analyzed["status"],
            "adjacent_selected_level_overlap_count": [
                column["adjacent_measured_level_overlap_count"]
                for column in analyzed["columns"]],
            "columns": analyzed["columns"]}
    if not zero_offsets or not nonzero_swings:
        raise ValueError("selected cases lack zero or nonzero measurements")
    return {**pairs, "max_selected_zero_offset_abs_v": max(zero_offsets),
            "min_selected_nonzero_swing_abs_v_all_cases": min(nonzero_swings),
            "polarity_mismatch_columns_at_two_times": polarity_mismatches,
            "selected_level_transfer": samples,
            "scope_warning": "selected PEX cases only; no ADC/noise/PVT/full-range PASS"}


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 180) -> dict[str, object]:
    root = Path(root).resolve()
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    build_characterization(root, config)
    coverage_path = root / "results/receipts/physical/core_pex_coverage.json"
    diagnosis_path = root / "results/sky130/core_transfer_diagnostics/measured.json"
    screen_path = root / "results/sky130/core_transfer_design_space/measured.json"
    summary_path = root / "results/receipts/physical/stage5_summary.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    if (coverage.get("status") != "MEASURED_CORE_ONLY" or
            coverage.get("completed_jobs") != coverage.get("job_count") or
            coverage.get("job_count") != 101 or
            diagnosis.get("status") != "MEASURED_DIAGNOSTIC" or
            diagnosis.get("coverage_receipt_sha256") != _digest(coverage_path) or
            screen.get("format") != "automx-cim-core-transfer-design-space-v1" or
            screen.get("diagnostic_sha256") != _digest(diagnosis_path) or
            screen.get("coverage_sha256") != _digest(coverage_path) or
            screen.get("stage5_summary_sha256") != _digest(summary_path) or
            screen.get("completed_sims") != screen.get("planned_sims")):
        raise ValueError("Stage-4.5/4.6/4.7 measured provenance is missing or stale")
    points = candidate_points(screen)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    pex = Path(summary["views"]["extracted_spice"]["path"]).resolve()
    if (_digest(pex) != summary["views"]["extracted_spice"]["sha256"] or
            parse_spice_subckt_pins(pex, f"{CORE}_pex") != core_pins() or
            coverage.get("pex_sha256") != _digest(pex)):
        raise ValueError("Stage-5 PEX view changed")
    manifest = json.loads((root / "generated/sky130/spice/stage4_manifest.json").read_text(encoding="utf-8"))
    model = Path(manifest["model_library"]).resolve()
    if _digest(model) != screen.get("model_sha256"):
        raise ValueError("PDK model library changed")
    coverage_jobs = {str(job["case"]): job for job in coverage["jobs"]}
    cases = list(diagnosis["analysis"]["selected_cases"])
    if any(name not in coverage_jobs for name in cases) or "zero" not in cases:
        raise ValueError("Stage-4.6 selected cases are incomplete")
    output_dir = root / OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    ngspice = shutil.which("ngspice") if execute else None
    failures = ["ngspice not on PATH"] if execute and not ngspice else []
    decks = []
    point_reports = []
    for load_ff, pwm_unit_ps in points:
        folder = output_dir / f"c{load_ff}ff_pwm{pwm_unit_ps}ps"
        folder.mkdir(parents=True, exist_ok=True)
        measured = {}
        for name in cases:
            source = coverage_jobs[name]
            case = Case(name, tuple(int(x) for x in source["activation_x2"]),
                        tuple(tuple(int(x) for x in row) for row in source["ternary_weights"]))
            deck = folder / f"{name}.spice"
            deck.write_text(make_pex_deck(case, model, pex, load_ff, pwm_unit_ps),
                            encoding="utf-8")
            log = folder / f"{name}.log"
            entry = {"load_ff": load_ff, "pwm_unit_ps": pwm_unit_ps,
                     "case": name, "deck": str(deck.relative_to(root)),
                     "deck_sha256": _digest(deck), "log": str(log.relative_to(root))}
            decks.append(entry)
            if execute and ngspice and not failures:
                if log.is_file():
                    log.unlink()
                try:
                    completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                               cwd=folder, text=True, capture_output=True,
                                               timeout=timeout_s, check=False)
                except subprocess.TimeoutExpired:
                    entry["returncode"] = "TIMEOUT"
                    failures.append(f"{load_ff}fF/{pwm_unit_ps}ps/{name}: timeout; inspect {deck}")
                    continue
                entry["returncode"] = completed.returncode
                output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
                values = parse_measurements(output, _expected())
                if completed.returncode or len(values) != len(_expected()) or not all(
                        math.isfinite(value) for value in values.values()):
                    failures.append(f"{load_ff}fF/{pwm_unit_ps}ps/{name}: incomplete ngspice result; inspect {log}")
                else:
                    measured[name] = values
                    entry["measurements"] = values
        if execute and not failures:
            point_reports.append(summarize_candidate(diagnosis["analysis"], coverage_jobs,
                                                     measured, load_ff=load_ff,
                                                     pwm_unit_ps=pwm_unit_ps))
    report = {"format": "automx-cim-core-candidate-pex-v1",
              "status": "FAIL" if failures else "MEASURED_PEX_SCREEN" if execute else "PREPARED",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "two candidate load/PWM points on selected TT PEX cases; no ADC/noise/PVT/full-range PASS",
              "script_sha256": _digest(Path(__file__)),
              "coverage_sha256": _digest(coverage_path),
              "diagnostic_sha256": _digest(diagnosis_path),
              "schematic_screen_sha256": _digest(screen_path),
              "stage5_summary_sha256": _digest(summary_path),
              "pex_sha256": _digest(pex), "model_sha256": _digest(model),
              "candidate_points": [{"load_ff": a, "pwm_unit_ps": b} for a, b in points],
              "selected_cases": cases, "planned_sims": len(decks),
              "completed_sims": sum("measurements" in entry for entry in decks),
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
