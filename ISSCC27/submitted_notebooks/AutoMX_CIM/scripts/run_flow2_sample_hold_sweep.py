#!/usr/bin/env python3
"""Sweep two inspected S/H stimuli on the current Stage-5 PEX, in a new namespace.

This is a small schematic TT feasibility screen. It never rewrites the older
820 fF, idle, sample/hold, or edge measurements and cannot sign off an ADC.
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

from automx_cim.spice import parse_measurements
from scripts.run_wrapper_input_loading_screen import _case, _sources
from scripts.run_wrapper_sample_hold_tt import make_sample_hold_deck
from scripts.flow2_stimulus_catalog import load_stimuli

OUTPUT = Path("results/sky130/flow2_sample_hold_sweep")
CASES = ("mha_96_a", "mha_118_a")
TARGET_V = 0.0008
TIMES = (("pre", "2.095n"), ("post", "2.15n"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _expected() -> list[str]:
    return [f"edge_{prefix}{side}_c{col}_{when}"
            for col in range(4) for side in ("blp", "bln")
            for prefix in ("", "h") for when, _ in TIMES]


def make_sweep_deck(case, model: Path, pex: Path, *,
                    width_um: float, fall_ps: int) -> str:
    """Change only the TG size and turnoff slew of the recorded S/H candidate."""
    if not math.isfinite(width_um) or width_um <= 0 or fall_ps <= 0:
        raise ValueError("switch width and turnoff time must be positive")
    source = make_sample_hold_deck(case, model, pex)
    old_width = " W=1.68 L=0.15"
    lines = source.splitlines()
    switch_indices = [i for i, line in enumerate(lines)
                      if line.startswith(("XSHN_", "XSHP_"))]
    if (len(switch_indices) != 16 or
            any(lines[i].count(old_width) != 1 for i in switch_indices)):
        raise ValueError("unexpected number of S/H transistors")
    for i in switch_indices:
        lines[i] = lines[i].replace(old_width, f" W={width_um:g} L=0.15")
    source = "\n".join(lines) + "\n"
    for control, initial, final in (("VSAM SAM 0", "0", "{VDD}"),
                                    ("VSAMB SAMB 0", "{VDD}", "0")):
        old = f"{control} PULSE({initial} {final} 1.8n 5p 5p 0.3n 10n)"
        new = f"{control} PULSE({initial} {final} 1.8n 5p {fall_ps}p 0.3n 10n)"
        if source.count(old) != 1:
            raise ValueError(f"unexpected sampling control {control}")
        source = source.replace(old, new)
    lines = source.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    measurements = [
        f".measure tran edge_{prefix}{side}_c{col}_{when} "
        f"FIND V({prefix}{side}{col}) AT={time_ns}"
        for col in range(4) for side in ("blp", "bln")
        for prefix in ("", "h") for when, time_ns in TIMES
    ]
    lines[index:index] = measurements
    return "\n".join(lines) + "\n"


def _metrics(jobs: list[dict]) -> list[dict]:
    points = []
    for job in jobs:
        values = job.get("measurements_v")
        if not values:
            continue
        capture, pre_tracking, post_tracking, held_peak = [], [], [], []
        for col in range(4):
            def pair(prefix: str, when: str) -> tuple[float, float]:
                return (float(values[f"edge_{prefix}blp_c{col}_{when}"]),
                        float(values[f"edge_{prefix}bln_c{col}_{when}"]))
            bl_pre, bl_post = pair("", "pre"), pair("", "post")
            h_pre, h_post = pair("h", "pre"), pair("h", "post")
            differential = lambda pair_: pair_[1] - pair_[0]
            capture.append(abs(differential(h_post) - differential(bl_pre)))
            pre_tracking.append(abs(differential(h_pre) - differential(bl_pre)))
            post_tracking.append(abs(differential(h_post) - differential(bl_post)))
            held_peak.extend(h_post)
        points.append({"case": job["case"], "width_um": job["width_um"],
                       "fall_ps": job["fall_ps"],
                       "maximum_capture_error_v": max(capture),
                       "maximum_pre_edge_tracking_error_v": max(pre_tracking),
                       "maximum_post_edge_tracking_error_v": max(post_tracking),
                       "held_node_maximum_v": max(held_peak)})
    return points


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600,
        widths_um: tuple[float, ...] = (0.42, 0.84, 1.68),
        fall_times_ps: tuple[int, ...] = (5, 20, 50)) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0 or not widths_um or not fall_times_ps:
        raise ValueError("positive timeout and nonempty sweep required")
    calibration, holdout, model, pex, _ = _sources(root)
    source, stimulus_provenance = load_stimuli(root, model_sha256=_sha(model))
    stimuli = {item["case"]: _case(item)
               for item in source["jobs"]["fresh_holdout"]
               if item["case"] in CASES}
    if set(stimuli) != set(CASES):
        raise ValueError("selected inspected stimuli are missing")
    folder = root / OUTPUT / f"pex_{_sha(pex)[:12]}"
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for width in widths_um:
        for fall in fall_times_ps:
            for name in CASES:
                tag = f"w{width:g}_f{fall}_{name}".replace(".", "p")
                deck = folder / f"{tag}.spice"
                content = make_sweep_deck(stimuli[name], model, pex,
                                          width_um=width, fall_ps=fall)
                if deck.is_file() and deck.read_text(encoding="utf-8") != content:
                    raise FileExistsError(f"refusing changed sweep deck: {deck}")
                deck.write_text(content, encoding="utf-8")
                jobs.append({"case": name, "width_um": width, "fall_ps": fall,
                             "deck": str(deck.relative_to(root)),
                             "deck_sha256": _sha(deck),
                             "log": str((folder / f"{tag}.log").relative_to(root)),
                             "checkpoint": str((folder / f"{tag}.receipt.json").relative_to(root))})
    version = holdout["ngspice_version"]
    if execute:
        ngspice = shutil.which("ngspice")
        if not ngspice:
            raise FileNotFoundError("ngspice is not on PATH")
        observed = subprocess.run([ngspice, "-v"], capture_output=True,
                                  text=True, timeout=15, check=False)
        if (observed.stdout + observed.stderr).strip() != version:
            raise ValueError("ngspice version differs from 2+2 evidence")
        for index, job in enumerate(jobs, 1):
            deck, log, checkpoint = (root / job[key] for key in
                                     ("deck", "log", "checkpoint"))
            saved = None
            if log.is_file() and checkpoint.is_file():
                try:
                    item = json.loads(checkpoint.read_text(encoding="utf-8"))
                    parsed = parse_measurements(log.read_text(
                        encoding="utf-8", errors="replace"), _expected())
                    if (item.get("status") == "PASS" and
                            item.get("deck_sha256") == job["deck_sha256"] and
                            item.get("log_sha256") == _sha(log) and
                            item.get("pex_sha256") == _sha(pex) and
                            item.get("model_sha256") == _sha(model) and
                            item.get("ngspice_version") == version and
                            set(parsed) == set(_expected()) and
                            item.get("measurements_v") == parsed):
                        saved = item
                except (OSError, ValueError, TypeError):
                    pass
            if saved is None:
                if log.exists() or checkpoint.exists():
                    raise FileExistsError(f"inspect stale sweep log/checkpoint: {deck}")
                completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                           cwd=deck.parent, capture_output=True,
                                           text=True, timeout=timeout_s, check=False)
                parsed = parse_measurements(log.read_text(
                    encoding="utf-8", errors="replace") if log.is_file() else "",
                    _expected())
                if (completed.returncode or set(parsed) != set(_expected()) or
                        not all(math.isfinite(v) for v in parsed.values())):
                    raise RuntimeError(f"incomplete sweep measurement: {log}")
                saved = {"status": "PASS", "deck_sha256": job["deck_sha256"],
                         "log_sha256": _sha(log), "pex_sha256": _sha(pex),
                         "model_sha256": _sha(model), "ngspice_version": version,
                         "measurements_v": parsed}
                checkpoint.write_text(json.dumps(saved, indent=2) + "\n",
                                      encoding="utf-8")
            job["measurements_v"] = saved["measurements_v"]
            job["log_sha256"] = saved["log_sha256"]
            print(f"S/H sweep {index}/{len(jobs)}: {job['case']} "
                  f"W={job['width_um']} um fall={job['fall_ps']} ps", flush=True)
    points = _metrics(jobs)
    groups = []
    for width in widths_um:
        for fall in fall_times_ps:
            subset = [p for p in points if p["width_um"] == width and
                      p["fall_ps"] == fall]
            if subset:
                groups.append({"width_um": width, "fall_ps": fall,
                               "maximum_capture_error_v": max(
                                   p["maximum_capture_error_v"] for p in subset),
                               "maximum_post_edge_tracking_error_v": max(
                                   p["maximum_post_edge_tracking_error_v"] for p in subset),
                               "held_node_maximum_v": max(
                                   p["held_node_maximum_v"] for p in subset)})
    candidate = min(groups, key=lambda x: x["maximum_capture_error_v"]) if groups else None
    report = {
        "format": "automx-cim-flow2-sample-hold-sweep-v1",
        "status": "MEASURED_TT_SAMPLING_SWEEP_DIAGNOSTIC" if execute else "PREPARED",
        "conclusion": ("NOT_MEASURED" if not execute else
                       "SELECTED_CASE_TARGET_MET" if candidate and
                       candidate["maximum_capture_error_v"] <= TARGET_V else
                       "BLOCKED_SELECTED_CASE_ACQUISITION"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "two deterministic MHA phase-A stimuli on latest passive-core PEX; schematic TG and ideal controls only",
        "source_stimulus_catalog": stimulus_provenance,
        "current_calibration_sha256": _sha(root / "results/sky130/post49_partition_full_tt/calibration/measured.json"),
        "current_holdout_sha256": _sha(root / "results/sky130/post49_partition_full_tt/holdout/measured.json"),
        "pex_sha256": _sha(pex), "model_sha256": _sha(model),
        "script_sha256": _sha(Path(__file__)),
        "target_differential_error_v": TARGET_V,
        "widths_um": list(widths_um), "fall_times_ps": list(fall_times_ps),
        "times_ns": {"pre": 2.095, "post": 2.15},
        "planned_sims": len(jobs),
        "completed_sims": sum("measurements_v" in job for job in jobs),
        "groups": groups, "best_selected_case_candidate": candidate,
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
    parser.add_argument("--widths-um", type=float, nargs="+", default=[0.42, 0.84, 1.68])
    parser.add_argument("--fall-times-ps", type=int, nargs="+", default=[5, 20, 50])
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s,
                 widths_um=tuple(args.widths_um),
                 fall_times_ps=tuple(args.fall_times_ps))
    print(json.dumps({key: value for key, value in result.items() if key not in
                      ("jobs", "points")}, indent=2))
