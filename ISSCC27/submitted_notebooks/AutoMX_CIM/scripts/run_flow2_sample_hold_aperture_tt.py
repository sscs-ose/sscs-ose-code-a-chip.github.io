#!/usr/bin/env python3
"""Sweep ideal sample-switch turnoff on two inspected TT core-PEX cases.

This is a sparse selected-case aperture diagnostic, not a continuous aperture
proof or a held-node decoder/ADC qualification. Every source deck and checkpoint
must match the completed settled-edge run; outputs use a separate namespace.
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
from scripts import run_flow2_sample_hold_settled_tt as settled_source  # noqa: E402

SOURCE = Path("results/sky130/flow2_sample_hold_settled_tt")
OUTPUT = Path("results/sky130/flow2_sample_hold_aperture_tt")
CASES = ("mha_96_a", "mha_118_a")
TURNOFF_NS = (2.025, 2.065, 2.105, 2.145, 2.185)
WIDTH_UM = 0.84
FALL_PS = 5
TARGET_V = 0.0008
LATE_NS = 2.4


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _expected() -> list[str]:
    return [f"aper_{prefix}{side}_c{col}_{when}"
            for col in range(4) for side in ("blp", "bln")
            for prefix, when in (("", "pre"), ("h", "pre"),
                                 ("", "full"), ("h", "full"),
                                 ("h", "late"))]


def make_aperture_deck(source: str, *, turnoff_ns: float) -> str:
    """Move only pulse width and measurements in the validated 5 ps source."""
    if (not math.isfinite(turnoff_ns) or turnoff_ns < 1.9 or
            turnoff_ns + 0.035 >= LATE_NS):
        raise ValueError("turnoff must leave valid pre/full/late sample times")
    lines = source.splitlines()
    prior_measures = [line for line in lines if line.startswith(
        (".measure tran edge_", ".measure tran settled_"))]
    # The settled runner parses 40 required measurements, while its source
    # sweep deck also carries 16 extra edge probes. All 56 are replaced here.
    if (len(prior_measures) != 56 or
            source.count(".tran ") != 1):
        raise ValueError("expected unchanged settled-edge source measurements")
    width_ns = turnoff_ns - 1.805  # pulse rises at 1.800 ns, reaches high at 1.805 ns
    for control, initial, final in (("VSAM SAM 0", "0", "{VDD}"),
                                    ("VSAMB SAMB 0", "{VDD}", "0")):
        old = f"{control} PULSE({initial} {final} 1.8n 5p 5p 0.3n 10n)"
        new = f"{control} PULSE({initial} {final} 1.8n 5p 5p {width_ns:.3f}n 10n)"
        if lines.count(old) != 1:
            raise ValueError(f"unexpected sampling control: {control}")
        lines[lines.index(old)] = new
    lines = [line for line in lines if not line.startswith(
        (".measure tran edge_", ".measure tran settled_"))]
    sampling = (("", "pre", turnoff_ns - 0.010),
                ("h", "pre", turnoff_ns - 0.010),
                ("", "full", turnoff_ns + 0.035),
                ("h", "full", turnoff_ns + 0.035),
                ("h", "late", LATE_NS))
    new_measures = [
        f".measure tran aper_{prefix}{side}_c{col}_{when} "
        f"FIND V({prefix}{side}{col}) AT={time_ns:.3f}n"
        for col in range(4) for side in ("blp", "bln")
        for prefix, when, time_ns in sampling
    ]
    index = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    lines[index:index] = new_measures
    return "\n".join(lines) + "\n"


def _metrics(job: dict) -> dict:
    values = job["measurements_v"]
    columns = []
    for col in range(4):
        def pair(prefix: str, when: str) -> tuple[float, float]:
            return (float(values[f"aper_{prefix}blp_c{col}_{when}"]),
                    float(values[f"aper_{prefix}bln_c{col}_{when}"]))
        bl_pre, h_pre = pair("", "pre"), pair("h", "pre")
        bl_full, h_full, h_late = (pair("", "full"), pair("h", "full"),
                                  pair("h", "late"))
        diff = lambda p: p[1] - p[0]
        cm = lambda p: (p[0] + p[1]) / 2
        columns.append({
            "column": col,
            "bitline_pre_vdiff_v": diff(bl_pre),
            "bitline_pre_vcm_v": cm(bl_pre),
            "held_pre_vdiff_v": diff(h_pre),
            "held_full_vdiff_v": diff(h_full),
            "held_full_vcm_v": cm(h_full),
            "held_late_vdiff_v": diff(h_late),
            "held_late_vcm_v": cm(h_late),
            "capture_error_full_v": abs(diff(h_full) - diff(bl_pre)),
            "capture_error_late_v": abs(diff(h_late) - diff(bl_pre)),
            "hold_drift_v": abs(diff(h_late) - diff(h_full)),
            "bitline_change_during_turnoff_v": abs(diff(bl_full) - diff(bl_pre)),
            "held_node_maximum_v": max(*h_pre, *h_full, *h_late),
        })
    return {"case": job["case"], "turnoff_start_ns": job["turnoff_start_ns"],
            "turnoff_complete_ns": job["turnoff_start_ns"] + FALL_PS / 1000,
            "maximum_capture_error_late_v": max(c["capture_error_late_v"] for c in columns),
            "maximum_held_node_v": max(c["held_node_maximum_v"] for c in columns),
            "columns": columns}


def _source_deck(root: Path, item: dict, *, pex_sha: str,
                 model_sha: str, version: str) -> Path:
    deck, log, receipt = (root / item[name] for name in
                          ("deck", "log", "checkpoint"))
    if (not all(path.is_file() for path in (deck, log, receipt)) or
            _sha(deck) != item.get("deck_sha256") or
            _sha(log) != item.get("log_sha256")):
        raise ValueError(f"settled source files missing or changed: {item['case']}")
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    parsed = parse_measurements(log.read_text(encoding="utf-8", errors="replace"),
                                settled_source._expected())
    if (saved.get("status") != "PASS" or
            saved.get("deck_sha256") != item["deck_sha256"] or
            saved.get("log_sha256") != item["log_sha256"] or
            saved.get("pex_sha256") != pex_sha or
            saved.get("model_sha256") != model_sha or
            saved.get("ngspice_version") != version or
            set(parsed) != set(settled_source._expected()) or
            parsed != saved.get("measurements_v") or
            parsed != item.get("measurements_v")):
        raise ValueError(f"settled source checkpoint mismatch: {item['case']}")
    return deck


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    _, holdout, model, pex, _ = _sources(root)
    pex_sha, model_sha = _sha(pex), _sha(model)
    source_path = root / SOURCE / f"pex_{pex_sha[:12]}/measured.json"
    prior = json.loads(source_path.read_text(encoding="utf-8"))
    if (prior.get("format") != "automx-cim-flow2-sample-hold-settled-tt-v1" or
            prior.get("status") != "MEASURED_TT_SETTLED_HOLD_DIAGNOSTIC" or
            prior.get("conclusion") != "SELECTED_CASE_SETTLED_TARGET_MET" or
            prior.get("planned_sims") != prior.get("completed_sims") or
            prior.get("planned_sims") != 6 or
            prior.get("pex_sha256") != pex_sha or
            prior.get("model_sha256") != model_sha or
            prior.get("best_settled_candidate", {}).get("width_um") != WIDTH_UM or
            prior.get("best_settled_candidate", {}).get("fall_ps") != FALL_PS or
            prior.get("best_settled_candidate", {}).get(
                "maximum_capture_error_late_v", float("inf")) > TARGET_V or
            prior.get("script_sha256") != _sha(Path(settled_source.__file__))):
        raise ValueError("complete, matching settled-edge source required")
    source_jobs = {(j["case"], j["fall_ps"]): j for j in prior["jobs"]
                   if j.get("width_um") == WIDTH_UM}
    folder = root / OUTPUT / f"pex_{pex_sha[:12]}"
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for turnoff in TURNOFF_NS:
        for case in CASES:
            item = source_jobs.get((case, FALL_PS))
            if item is None:
                raise ValueError(f"missing 5 ps settled source for {case}")
            original = _source_deck(root, item, pex_sha=pex_sha,
                                    model_sha=model_sha,
                                    version=holdout["ngspice_version"])
            tag = f"off{turnoff:.3f}_{case}".replace(".", "p")
            deck = folder / f"{tag}.spice"
            content = make_aperture_deck(original.read_text(encoding="utf-8"),
                                         turnoff_ns=turnoff)
            if deck.is_file() and deck.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"refusing changed aperture deck: {deck}")
            deck.write_text(content, encoding="utf-8")
            jobs.append({"case": case, "turnoff_start_ns": turnoff,
                         "source_deck_sha256": _sha(original),
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
            raise ValueError("ngspice version differs from settled source")
        for index, job in enumerate(jobs, 1):
            deck, log, receipt = (root / job[name] for name in
                                  ("deck", "log", "checkpoint"))
            saved = None
            if log.is_file() and receipt.is_file():
                try:
                    candidate = json.loads(receipt.read_text(encoding="utf-8"))
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
                if log.exists() or receipt.exists():
                    raise FileExistsError(f"inspect stale aperture log/checkpoint: {deck}")
                completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                           cwd=deck.parent, capture_output=True,
                                           text=True, timeout=timeout_s, check=False)
                parsed = parse_measurements(log.read_text(
                    encoding="utf-8", errors="replace") if log.is_file() else "",
                    _expected())
                if (completed.returncode or set(parsed) != set(_expected()) or
                        not all(math.isfinite(v) for v in parsed.values())):
                    raise RuntimeError(f"incomplete aperture measurement: {log}")
                saved = {"status": "PASS", "deck_sha256": job["deck_sha256"],
                         "log_sha256": _sha(log), "pex_sha256": pex_sha,
                         "model_sha256": model_sha, "ngspice_version": version,
                         "measurements_v": parsed}
                receipt.write_text(json.dumps(saved, indent=2) + "\n",
                                   encoding="utf-8")
            job["measurements_v"] = saved["measurements_v"]
            job["log_sha256"] = saved["log_sha256"]
            print(f"S/H aperture {index}/{len(jobs)}: {job['case']} "
                  f"off={job['turnoff_start_ns']:.3f} ns", flush=True)
    points = [_metrics(job) for job in jobs if "measurements_v" in job]
    grid = []
    for turnoff in TURNOFF_NS:
        subset = [p for p in points if p["turnoff_start_ns"] == turnoff]
        if subset:
            maximum = max(p["maximum_capture_error_late_v"] for p in subset)
            grid.append({"turnoff_start_ns": turnoff,
                         "maximum_capture_error_late_v": maximum,
                         "target_met_in_two_cases": len(subset) == len(CASES) and
                                                    maximum <= TARGET_V,
                         "maximum_held_node_v": max(p["maximum_held_node_v"]
                                                    for p in subset)})
    slopes = []
    for case in CASES:
        sequence = [p for p in points if p["case"] == case]
        for left, right in zip(sequence, sequence[1:]):
            for col in range(4):
                a, b = left["columns"][col], right["columns"][col]
                dt = right["turnoff_start_ns"] - left["turnoff_start_ns"]
                slopes.append({"case": case, "column": col,
                               "from_ns": left["turnoff_start_ns"],
                               "to_ns": right["turnoff_start_ns"],
                               "held_vdiff_slope_v_per_ns":
                               (b["held_late_vdiff_v"] - a["held_late_vdiff_v"]) / dt})
    report = {
        "format": "automx-cim-flow2-sample-hold-aperture-tt-v1",
        "status": "MEASURED_TT_SELECTED_CASE_APERTURE_DIAGNOSTIC" if execute else "PREPARED",
        "conclusion": "NO_CONTINUOUS_APERTURE_PROVEN" if execute else "NOT_MEASURED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "two previously inspected phase-A cases, five discrete turnoff times, W=0.84 um/5 ps; schematic TG and ideal controls",
        "source_settled_sha256": _sha(source_path),
        "source_settled_script_sha256": prior["script_sha256"],
        "pex_sha256": pex_sha, "model_sha256": model_sha,
        "script_sha256": _sha(Path(__file__)),
        "target_differential_error_v": TARGET_V,
        "turnoff_start_times_ns": list(TURNOFF_NS),
        "measure_offsets_ns": {"pre": -0.010, "full": 0.035,
                               "late_absolute": LATE_NS},
        "planned_sims": len(jobs),
        "completed_sims": sum("measurements_v" in j for j in jobs),
        "grid": grid, "settling_slopes": slopes,
        "decision_margin_vs_time": None,
        "decision_margin_status": "UNAVAILABLE_NO_HELD_NODE_CALIBRATION",
        "recommended_aperture": None,
        "not_signoff": "sparse selected-case TT grid only; no continuous aperture, zero-state coverage, held-node decoder, real control driver, switch PEX, offset/noise, ADC, PVT or wrapper",
        "points": points, "jobs": jobs,
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
                      ("jobs", "points", "settling_slopes")}, indent=2))
