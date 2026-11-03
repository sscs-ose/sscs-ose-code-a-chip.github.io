#!/usr/bin/env python3
"""Recheck the selected S/H switch after its clock edge has fully completed.

The prior sweep sampled at 2.150 ns. With a 50 ps fall, its control is still
transitioning until 2.155 ns. This runner measures at 2.200 and 2.400 ns in
a new folder. Two inspected TT stimuli and an ideal control remain diagnostic.
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
from scripts.run_flow2_sample_hold_sweep import _expected as old_expected  # noqa: E402

SOURCE = Path("results/sky130/flow2_sample_hold_sweep")
OUTPUT = Path("results/sky130/flow2_sample_hold_settled_tt")
CASES = ("mha_96_a", "mha_118_a")
WIDTH_UM = 0.84
FALL_TIMES_PS = (5, 20, 50)
TARGET_V = 0.0008
FULL_OFF_NS = 2.200
LATE_NS = 2.400


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _expected() -> list[str]:
    return ([f"edge_{prefix}{side}_c{col}_{when}"
             for col in range(4) for side in ("blp", "bln")
             for prefix, when in (("", "pre"), ("h", "post"))] +
            [f"settled_{prefix}{side}_c{col}_{when}"
             for col in range(4) for side in ("blp", "bln")
             for prefix, when in (("", "full"), ("h", "full"),
                                  ("h", "late"))])


def make_settled_deck(source: str, *, fall_ps: int) -> str:
    """Add fully-off and held-node measurements to an unchanged sweep deck."""
    if fall_ps <= 0 or 2.105 + fall_ps / 1000 >= FULL_OFF_NS:
        raise ValueError("full-off sample must follow the entire falling edge")
    if (source.count(".tran ") != 1 or
            source.count(f"VSAM SAM 0 PULSE(0 {{VDD}} 1.8n 5p {fall_ps}p 0.3n 10n)") != 1 or
            "settled_hblp_c0_full" in source):
        raise ValueError("unexpected or already modified sweep deck")
    lines = source.splitlines()
    measures = [
        f".measure tran settled_{prefix}{side}_c{col}_{when} "
        f"FIND V({prefix}{side}{col}) AT={time_ns}"
        for col in range(4) for side in ("blp", "bln")
        for prefix, when, time_ns in (("", "full", "2.2n"),
                                      ("h", "full", "2.2n"),
                                      ("h", "late", "2.4n"))
    ]
    index = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    lines[index:index] = measures
    return "\n".join(lines) + "\n"


def _case_metrics(job: dict) -> dict:
    values = job["measurements_v"]
    capture_full, capture_late, remaining_edge, hold_drift = [], [], [], []
    tracking_full, held_peak = [], []
    for col in range(4):
        def pair(stem: str, when: str) -> tuple[float, float]:
            return (float(values[f"{stem}blp_c{col}_{when}"]),
                    float(values[f"{stem}bln_c{col}_{when}"]))
        bl_pre = pair("edge_", "pre")
        h_early = pair("edge_h", "post")
        bl_full = pair("settled_", "full")
        h_full = pair("settled_h", "full")
        h_late = pair("settled_h", "late")
        differential = lambda voltages: voltages[1] - voltages[0]
        capture_full.append(abs(differential(h_full) - differential(bl_pre)))
        capture_late.append(abs(differential(h_late) - differential(bl_pre)))
        remaining_edge.append(abs(differential(h_full) - differential(h_early)))
        hold_drift.append(abs(differential(h_late) - differential(h_full)))
        tracking_full.append(abs(differential(h_full) - differential(bl_full)))
        held_peak.extend((*h_full, *h_late))
    return {
        "case": job["case"], "width_um": job["width_um"],
        "fall_ps": job["fall_ps"],
        "turnoff_complete_ns": 2.105 + job["fall_ps"] / 1000,
        "maximum_capture_error_full_off_v": max(capture_full),
        "maximum_capture_error_late_v": max(capture_late),
        "maximum_remaining_edge_shift_after_2p15_v": max(remaining_edge),
        "maximum_held_differential_drift_v": max(hold_drift),
        "maximum_tracking_error_full_off_v": max(tracking_full),
        "held_node_maximum_v": max(held_peak),
    }


def _source_job(root: Path, item: dict, *, pex_sha: str, model_sha: str,
                version: str) -> Path:
    deck = root / item["deck"]
    log = root / item["log"]
    checkpoint = root / item["checkpoint"]
    if (not deck.is_file() or not log.is_file() or not checkpoint.is_file() or
            _sha(deck) != item.get("deck_sha256") or
            _sha(log) != item.get("log_sha256")):
        raise ValueError(f"prior sweep deck/log is missing or changed: {item['case']}")
    saved = json.loads(checkpoint.read_text(encoding="utf-8"))
    parsed = parse_measurements(log.read_text(
        encoding="utf-8", errors="replace"), old_expected())
    if (saved.get("status") != "PASS" or
            saved.get("deck_sha256") != item["deck_sha256"] or
            saved.get("log_sha256") != item["log_sha256"] or
            saved.get("pex_sha256") != pex_sha or
            saved.get("model_sha256") != model_sha or
            saved.get("ngspice_version") != version or
            set(parsed) != set(old_expected()) or
            parsed != item.get("measurements_v") or
            parsed != saved.get("measurements_v")):
        raise ValueError(f"prior sweep checkpoint mismatch: {item['case']}")
    return deck


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    _, holdout, model, pex, _ = _sources(root)
    pex_sha, model_sha = _sha(pex), _sha(model)
    prior_path = root / SOURCE / f"pex_{pex_sha[:12]}/measured.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    from scripts import run_flow2_sample_hold_sweep as sweep_source
    if (prior.get("format") != "automx-cim-flow2-sample-hold-sweep-v1" or
            prior.get("status") != "MEASURED_TT_SAMPLING_SWEEP_DIAGNOSTIC" or
            prior.get("planned_sims") != prior.get("completed_sims") or
            prior.get("planned_sims") != 18 or
            prior.get("pex_sha256") != pex_sha or
            prior.get("model_sha256") != model_sha or
            prior.get("script_sha256") != _sha(Path(sweep_source.__file__))):
        raise ValueError("complete matching prior sweep required")
    lookup = {(item["width_um"], item["fall_ps"], item["case"]): item
              for item in prior["jobs"]}
    folder = root / OUTPUT / f"pex_{pex_sha[:12]}"
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for fall in FALL_TIMES_PS:
        for name in CASES:
            key = (WIDTH_UM, fall, name)
            if key not in lookup:
                raise ValueError(f"missing prior sweep case: {key}")
            previous = lookup[key]
            old_deck = _source_job(root, previous, pex_sha=pex_sha,
                                   model_sha=model_sha,
                                   version=holdout["ngspice_version"])
            deck = folder / f"w0p84_f{fall}_{name}.spice"
            content = make_settled_deck(old_deck.read_text(encoding="utf-8"),
                                        fall_ps=fall)
            if deck.is_file() and deck.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"refusing changed settled deck: {deck}")
            deck.write_text(content, encoding="utf-8")
            jobs.append({"case": name, "width_um": WIDTH_UM, "fall_ps": fall,
                         "source_deck_sha256": _sha(old_deck),
                         "deck": str(deck.relative_to(root)),
                         "deck_sha256": _sha(deck),
                         "log": str((folder / f"w0p84_f{fall}_{name}.log").relative_to(root)),
                         "checkpoint": str((folder / f"w0p84_f{fall}_{name}.receipt.json").relative_to(root))})
    version = holdout["ngspice_version"]
    if execute:
        ngspice = shutil.which("ngspice")
        if not ngspice:
            raise FileNotFoundError("ngspice is not on PATH")
        observed = subprocess.run([ngspice, "-v"], capture_output=True,
                                  text=True, timeout=15, check=False)
        if (observed.stdout + observed.stderr).strip() != version:
            raise ValueError("ngspice version differs from prior sweep")
        for index, job in enumerate(jobs, 1):
            deck, log, checkpoint = (root / job[key] for key in
                                     ("deck", "log", "checkpoint"))
            saved = None
            if log.is_file() and checkpoint.is_file():
                try:
                    candidate = json.loads(checkpoint.read_text(encoding="utf-8"))
                    parsed = parse_measurements(log.read_text(
                        encoding="utf-8", errors="replace"), _expected())
                    if (candidate.get("status") == "PASS" and
                            candidate.get("deck_sha256") == job["deck_sha256"] and
                            candidate.get("log_sha256") == _sha(log) and
                            candidate.get("pex_sha256") == pex_sha and
                            candidate.get("model_sha256") == model_sha and
                            candidate.get("ngspice_version") == version and
                            set(parsed) == set(_expected()) and
                            parsed == candidate.get("measurements_v")):
                        saved = candidate
                except (OSError, ValueError, TypeError):
                    pass
            if saved is None:
                if log.exists() or checkpoint.exists():
                    raise FileExistsError(f"inspect stale settled log/checkpoint: {deck}")
                completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                           cwd=deck.parent, capture_output=True,
                                           text=True, timeout=timeout_s, check=False)
                parsed = parse_measurements(log.read_text(
                    encoding="utf-8", errors="replace") if log.is_file() else "",
                    _expected())
                if (completed.returncode or set(parsed) != set(_expected()) or
                        not all(math.isfinite(v) for v in parsed.values())):
                    raise RuntimeError(f"incomplete settled measurement: {log}")
                saved = {"status": "PASS", "deck_sha256": job["deck_sha256"],
                         "log_sha256": _sha(log), "pex_sha256": pex_sha,
                         "model_sha256": model_sha, "ngspice_version": version,
                         "measurements_v": parsed}
                checkpoint.write_text(json.dumps(saved, indent=2) + "\n",
                                      encoding="utf-8")
            job["measurements_v"] = saved["measurements_v"]
            job["log_sha256"] = saved["log_sha256"]
            print(f"S/H settled {index}/{len(jobs)}: {job['case']} "
                  f"fall={job['fall_ps']} ps", flush=True)
    points = [_case_metrics(job) for job in jobs if "measurements_v" in job]
    groups = []
    for fall in FALL_TIMES_PS:
        subset = [p for p in points if p["fall_ps"] == fall]
        if subset:
            groups.append({"width_um": WIDTH_UM, "fall_ps": fall,
                           "maximum_capture_error_full_off_v": max(
                               p["maximum_capture_error_full_off_v"] for p in subset),
                           "maximum_capture_error_late_v": max(
                               p["maximum_capture_error_late_v"] for p in subset),
                           "maximum_remaining_edge_shift_after_2p15_v": max(
                               p["maximum_remaining_edge_shift_after_2p15_v"] for p in subset),
                           "maximum_held_differential_drift_v": max(
                               p["maximum_held_differential_drift_v"] for p in subset),
                           "held_node_maximum_v": max(
                               p["held_node_maximum_v"] for p in subset)})
    eligible = [g for g in groups if
                max(g["maximum_capture_error_full_off_v"],
                    g["maximum_capture_error_late_v"]) <= TARGET_V]
    best = min(eligible, key=lambda x: max(x["maximum_capture_error_full_off_v"],
                                           x["maximum_capture_error_late_v"])) if eligible else None
    report = {
        "format": "automx-cim-flow2-sample-hold-settled-tt-v1",
        "status": "MEASURED_TT_SETTLED_HOLD_DIAGNOSTIC" if execute else "PREPARED",
        "conclusion": ("NOT_MEASURED" if not execute else
                       "SELECTED_CASE_SETTLED_TARGET_MET" if best else
                       "BLOCKED_SELECTED_CASE_SETTLED_ERROR"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "two previously inspected TT phase-A cases; W=0.84 um; ideal sampling controls and schematic TG; complete-edge/late-hold measurements only",
        "source_sweep_sha256": _sha(prior_path),
        "source_sweep_script_sha256": prior["script_sha256"],
        "pex_sha256": pex_sha, "model_sha256": model_sha,
        "script_sha256": _sha(Path(__file__)),
        "target_differential_error_v": TARGET_V,
        "turnoff_start_ns": 2.105,
        "times_ns": {"pre_edge": 2.095, "old_post": 2.150,
                     "full_off": FULL_OFF_NS, "late_hold": LATE_NS},
        "planned_sims": len(jobs),
        "completed_sims": sum("measurements_v" in job for job in jobs),
        "groups": groups, "best_settled_candidate": best,
        "points": points, "jobs": jobs,
        "not_signoff": "selected TT schematic cases only; no continuous aperture, real control driver, switch PEX, offset/noise, ADC, PVT or wrapper",
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
    print(json.dumps({key: value for key, value in result.items() if key not in
                      ("jobs", "points")}, indent=2))
