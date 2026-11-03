#!/usr/bin/env python3
"""Refine the selected-case TT switch-turnoff grid without repeating anchors.

This checks six new turnoff times for each of two already inspected patterns.
It combines them with the verified 2.065/2.105 ns sparse-grid anchors. A 10 ps
grid is not a continuous-aperture or ADC qualification.
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

from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_wrapper_input_loading_screen import _sources  # noqa: E402
from scripts import run_flow2_sample_hold_aperture_tt as sparse  # noqa: E402
from scripts import run_flow2_sample_hold_settled_tt as settled  # noqa: E402

OUTPUT = Path("results/sky130/flow2_sample_hold_refined_aperture_tt")
NEW_TIMES_NS = (2.045, 2.055, 2.075, 2.085, 2.095, 2.115)
ANCHORS_NS = (2.065, 2.105)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_sparse(root: Path, report: dict, *, pex_sha: str,
                     model_sha: str, version: str) -> list[dict]:
    if (report.get("format") != "automx-cim-flow2-sample-hold-aperture-tt-v1" or
            report.get("status") != "MEASURED_TT_SELECTED_CASE_APERTURE_DIAGNOSTIC" or
            report.get("planned_sims") != report.get("completed_sims") or
            report.get("planned_sims") != 10 or
            report.get("pex_sha256") != pex_sha or
            report.get("model_sha256") != model_sha or
            report.get("script_sha256") != _sha(Path(sparse.__file__))):
        raise ValueError("complete matching sparse aperture report required")
    if len(report.get("jobs", [])) != 10:
        raise ValueError("all sparse aperture jobs are required")
    observed = set()
    for item in report["jobs"]:
        key = (item["case"], item["turnoff_start_ns"])
        if (item["case"] not in sparse.CASES or
                item["turnoff_start_ns"] not in sparse.TURNOFF_NS or
                key in observed):
            raise ValueError(f"unexpected sparse aperture job: {key}")
        observed.add(key)
        deck, log, receipt = (root / item[name] for name in
                              ("deck", "log", "checkpoint"))
        if (not all(p.is_file() for p in (deck, log, receipt)) or
                _sha(deck) != item.get("deck_sha256") or
                _sha(log) != item.get("log_sha256")):
            raise ValueError(f"sparse job file missing or changed: {key}")
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        parsed = parse_measurements(log.read_text(
            encoding="utf-8", errors="replace"), sparse._expected())
        if (saved.get("status") != "PASS" or
                saved.get("deck_sha256") != item["deck_sha256"] or
                saved.get("log_sha256") != item["log_sha256"] or
                saved.get("pex_sha256") != pex_sha or
                saved.get("model_sha256") != model_sha or
                saved.get("ngspice_version") != version or
                set(parsed) != set(sparse._expected()) or
                parsed != saved.get("measurements_v") or
                parsed != item.get("measurements_v")):
            raise ValueError(f"sparse job checkpoint mismatch: {key}")
    return [sparse._metrics(j) for j in report["jobs"]
            if j["turnoff_start_ns"] in ANCHORS_NS]


def _grid(points: list[dict]) -> list[dict]:
    rows = []
    for when in sorted(set(NEW_TIMES_NS + ANCHORS_NS)):
        subset = [p for p in points if p["turnoff_start_ns"] == when]
        if len(subset) == len(sparse.CASES):
            error = max(p["maximum_capture_error_late_v"] for p in subset)
            rows.append({"turnoff_start_ns": when,
                         "maximum_capture_error_late_v": error,
                         "target_met_in_two_cases": error <= sparse.TARGET_V,
                         "maximum_held_node_v": max(p["maximum_held_node_v"]
                                                    for p in subset)})
    return rows


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    _, holdout, model, pex, _ = _sources(root)
    pex_sha, model_sha = _sha(pex), _sha(model)
    suffix = f"pex_{pex_sha[:12]}"
    sparse_path = root / sparse.OUTPUT / suffix / "measured.json"
    settled_path = root / settled.OUTPUT / suffix / "measured.json"
    prior = json.loads(sparse_path.read_text(encoding="utf-8"))
    source = json.loads(settled_path.read_text(encoding="utf-8"))
    version = holdout["ngspice_version"]
    anchors = _validate_sparse(root, prior, pex_sha=pex_sha,
                               model_sha=model_sha, version=version)
    if (len(anchors) != 2 * len(ANCHORS_NS) or
            prior.get("source_settled_sha256") != _sha(settled_path) or
            source.get("format") != "automx-cim-flow2-sample-hold-settled-tt-v1" or
            source.get("status") != "MEASURED_TT_SETTLED_HOLD_DIAGNOSTIC" or
            source.get("planned_sims") != source.get("completed_sims") or
            source.get("planned_sims") != 6 or
            source.get("script_sha256") != _sha(Path(settled.__file__)) or
            source.get("pex_sha256") != pex_sha or
            source.get("model_sha256") != model_sha):
        raise ValueError("sparse anchors and settled source do not match")
    source_jobs = {(j["case"], j["fall_ps"]): j for j in source["jobs"]
                   if j.get("width_um") == sparse.WIDTH_UM}
    folder = root / OUTPUT / suffix
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for when in NEW_TIMES_NS:
        for case in sparse.CASES:
            item = source_jobs.get((case, sparse.FALL_PS))
            if item is None:
                raise ValueError(f"missing validated settled source: {case}")
            original = sparse._source_deck(root, item, pex_sha=pex_sha,
                                           model_sha=model_sha, version=version)
            tag = f"off{when:.3f}_{case}".replace(".", "p")
            deck = folder / f"{tag}.spice"
            content = sparse.make_aperture_deck(
                original.read_text(encoding="utf-8"), turnoff_ns=when)
            if deck.is_file() and deck.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"refusing changed refined deck: {deck}")
            deck.write_text(content, encoding="utf-8")
            jobs.append({"case": case, "turnoff_start_ns": when,
                         "source_deck_sha256": _sha(original),
                         "deck": str(deck.relative_to(root)),
                         "deck_sha256": _sha(deck),
                         "log": str((folder / f"{tag}.log").relative_to(root)),
                         "checkpoint": str((folder / f"{tag}.receipt.json").relative_to(root))})
    if execute:
        ngspice = shutil.which("ngspice")
        if not ngspice:
            raise FileNotFoundError("ngspice is not on PATH")
        observed = subprocess.run([ngspice, "-v"], capture_output=True,
                                  text=True, timeout=15, check=False)
        if (observed.stdout + observed.stderr).strip() != version:
            raise ValueError("ngspice version differs from source evidence")
        for index, job in enumerate(jobs, 1):
            deck, log, receipt = (root / job[name] for name in
                                  ("deck", "log", "checkpoint"))
            saved = None
            if log.is_file() and receipt.is_file():
                try:
                    candidate = json.loads(receipt.read_text(encoding="utf-8"))
                    parsed = parse_measurements(log.read_text(
                        encoding="utf-8", errors="replace"), sparse._expected())
                    if (candidate.get("status") == "PASS" and
                            candidate.get("deck_sha256") == job["deck_sha256"] and
                            candidate.get("log_sha256") == _sha(log) and
                            candidate.get("pex_sha256") == pex_sha and
                            candidate.get("model_sha256") == model_sha and
                            candidate.get("ngspice_version") == version and
                            set(parsed) == set(sparse._expected()) and
                            parsed == candidate.get("measurements_v")):
                        saved = candidate
                except (OSError, ValueError, TypeError):
                    pass
            if saved is None:
                if log.exists() or receipt.exists():
                    raise FileExistsError(f"inspect stale refined log/checkpoint: {deck}")
                completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                           cwd=deck.parent, capture_output=True,
                                           text=True, timeout=timeout_s, check=False)
                parsed = parse_measurements(log.read_text(
                    encoding="utf-8", errors="replace") if log.is_file() else "",
                    sparse._expected())
                if (completed.returncode or set(parsed) != set(sparse._expected()) or
                        not all(math.isfinite(v) for v in parsed.values())):
                    raise RuntimeError(f"incomplete refined measurement: {log}")
                saved = {"status": "PASS", "deck_sha256": job["deck_sha256"],
                         "log_sha256": _sha(log), "pex_sha256": pex_sha,
                         "model_sha256": model_sha, "ngspice_version": version,
                         "measurements_v": parsed}
                receipt.write_text(json.dumps(saved, indent=2) + "\n",
                                   encoding="utf-8")
            job["measurements_v"] = saved["measurements_v"]
            job["log_sha256"] = saved["log_sha256"]
            print(f"S/H refined {index}/{len(jobs)}: {job['case']} "
                  f"off={job['turnoff_start_ns']:.3f} ns", flush=True)
    new_points = [sparse._metrics(j) for j in jobs if "measurements_v" in j]
    grid = _grid(anchors + new_points)
    report = {
        "format": "automx-cim-flow2-sample-hold-refined-aperture-tt-v1",
        "status": "MEASURED_TT_REFINED_APERTURE_DIAGNOSTIC" if execute else "PREPARED",
        "conclusion": "NO_CONTINUOUS_APERTURE_PROVEN" if execute else "NOT_MEASURED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "two inspected phase-A cases; six new 10 ps-grid times plus two verified anchors; schematic TG/ideal control",
        "source_sparse_sha256": _sha(sparse_path),
        "source_settled_sha256": _sha(settled_path),
        "pex_sha256": pex_sha, "model_sha256": model_sha,
        "script_sha256": _sha(Path(__file__)),
        "target_differential_error_v": sparse.TARGET_V,
        "new_turnoff_start_times_ns": list(NEW_TIMES_NS),
        "reused_anchor_times_ns": list(ANCHORS_NS),
        "planned_new_sims": len(jobs),
        "completed_new_sims": sum("measurements_v" in j for j in jobs),
        "grid": grid,
        "decision_margin_vs_time": None,
        "decision_margin_status": "UNAVAILABLE_NO_HELD_NODE_CALIBRATION",
        "recommended_aperture": None,
        "not_signoff": "10 ps discrete grid on two inspected TT cases; no continuous aperture, broad pattern set, real driver/switch PEX, ADC, offset/noise, PVT or wrapper",
        "anchors": anchors, "new_points": new_points, "jobs": jobs,
    }
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
    print(json.dumps({k: v for k, v in result.items() if k not in
                      ("jobs", "anchors", "new_points")}, indent=2))
