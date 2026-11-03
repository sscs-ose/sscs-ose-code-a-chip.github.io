"""Measure bitline and held nodes together around sample-switch turnoff.

Two existing TT cases isolate the active differential shift and near-rail
no-row-drive shift. This reruns new decks without changing earlier evidence.
It is a schematic switch/timing diagnostic, not ADC or wrapper sign-off.
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
from scripts.run_wrapper_sample_hold_tt import SOURCE, OUTPUT as PRIOR_OUTPUT  # noqa: E402

PRIOR = PRIOR_OUTPUT / "measured.json"
OUTPUT = Path("results/sky130/wrapper_sample_hold_edge_tt")
CASES = ("mha_96_a", "mha_118_a")
TIMES = (("pre", "2.095n"), ("post", "2.15n"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _expected() -> list[str]:
    return [f"edge_{node}{side}_c{col}_{when}"
            for col in range(4) for side in ("blp", "bln")
            for node in ("", "h") for when, _ in TIMES]


def make_edge_deck(prior_deck: str) -> str:
    lines = prior_deck.splitlines()
    if (sum(line.startswith(".tran ") for line in lines) != 1 or
            any("edge_blp_c0_pre" in line for line in lines) or
            "VSAM SAM 0 PULSE(0 {VDD} 1.8n 5p 5p 0.3n 10n)" not in lines):
        raise ValueError("unexpected sample/hold source deck")
    measurements = []
    for col in range(4):
        for side in ("blp", "bln"):
            for prefix in ("", "h"):
                node = f"{prefix}{side}{col}".upper()
                for when, time_ns in TIMES:
                    measurements.append(
                        f".measure tran edge_{prefix}{side}_c{col}_{when} "
                        f"FIND V({node}) AT={time_ns}")
    index = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    lines[index:index] = measurements
    return "\n".join(lines) + "\n"


def _summarize(jobs: list[dict]) -> dict:
    details = []
    for job in jobs:
        if "measurements_v" not in job:
            continue
        values = job["measurements_v"]
        for col in range(4):
            def pair(prefix: str, when: str) -> tuple[float, float]:
                return (values[f"edge_{prefix}blp_c{col}_{when}"],
                        values[f"edge_{prefix}bln_c{col}_{when}"])
            bl_pre, bl_post = pair("", "pre"), pair("", "post")
            h_pre, h_post = pair("h", "pre"), pair("h", "post")
            diff = lambda voltages: voltages[1] - voltages[0]
            track_pre = (h_pre[0] - bl_pre[0], h_pre[1] - bl_pre[1])
            track_post = (h_post[0] - bl_post[0], h_post[1] - bl_post[1])
            details.append({
                "case": job["case"], "column": col,
                "bitline_pre_v": list(bl_pre), "hold_pre_v": list(h_pre),
                "bitline_post_v": list(bl_post), "hold_post_v": list(h_post),
                "tracking_delta_pre_v": list(track_pre),
                "tracking_delta_post_v": list(track_post),
                "differential_tracking_delta_pre_v": diff(h_pre) - diff(bl_pre),
                "differential_tracking_delta_post_v": diff(h_post) - diff(bl_post),
                "hold_step_v": [h_post[i] - h_pre[i] for i in range(2)],
                "bitline_step_v": [bl_post[i] - bl_pre[i] for i in range(2)],
            })
    if not details:
        return {}
    return {
        "maximum_abs_tracking_delta_pre_v": max(abs(value) for item in details
                                                 for value in item["tracking_delta_pre_v"]),
        "maximum_abs_tracking_delta_post_v": max(abs(value) for item in details
                                                  for value in item["tracking_delta_post_v"]),
        "maximum_abs_differential_tracking_delta_pre_v": max(
            abs(item["differential_tracking_delta_pre_v"]) for item in details),
        "maximum_abs_differential_tracking_delta_post_v": max(
            abs(item["differential_tracking_delta_post_v"]) for item in details),
        "details": details,
    }


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    _, _, model, pex, _ = _sources(root)
    old_path = root / PRIOR
    old = json.loads(old_path.read_text(encoding="utf-8"))
    source_path = root / SOURCE
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if (old.get("format") != "automx-cim-wrapper-sample-hold-tt-v1" or
            old.get("status") != "MEASURED_TT_SAMPLE_HOLD_DIAGNOSTIC" or
            old.get("completed_sims") != old.get("planned_sims") or
            old.get("planned_sims") != 3 or
            old.get("source_report_sha256") != _sha(source_path) or
            old.get("pex_sha256") != _sha(pex) or
            old.get("model_sha256") != _sha(model)):
        raise ValueError("complete matching sample/hold TT source required")
    old_jobs = {job["case"]: job for job in old["jobs"]}
    if len(old_jobs) != 3 or any(case not in old_jobs for case in CASES):
        raise ValueError("required active and no-row-drive source decks missing")
    folder = root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for case in CASES:
        old_job = old_jobs[case]
        old_deck = (root / old_job["deck"]).resolve()
        if (not old_deck.is_relative_to((root / PRIOR_OUTPUT).resolve()) or
                not old_deck.is_file() or _sha(old_deck) != old_job["deck_sha256"]):
            raise ValueError(f"source deck changed: {case}")
        deck = folder / f"{case}.spice"
        content = make_edge_deck(old_deck.read_text(encoding="utf-8"))
        if deck.exists() and deck.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"refusing changed edge deck: {deck}")
        deck.write_text(content, encoding="utf-8")
        jobs.append({"case": case, "deck": str(deck.relative_to(root)),
                     "deck_sha256": _sha(deck),
                     "log": str((folder / f"{case}.log").relative_to(root)),
                     "checkpoint": str((folder / f"{case}.receipt.json").relative_to(root))})
    if execute:
        ngspice = shutil.which("ngspice")
        if not ngspice:
            raise FileNotFoundError("ngspice not on PATH")
        version = subprocess.run([ngspice, "-v"], capture_output=True,
                                 text=True, timeout=15, check=False)
        if (version.stdout + version.stderr).strip() != source["ngspice_version"]:
            raise ValueError("ngspice version changed")
        for job in jobs:
            deck, log, checkpoint = (root / job[key] for key in
                                     ("deck", "log", "checkpoint"))
            saved = None
            if log.is_file() and checkpoint.is_file():
                try:
                    candidate = json.loads(checkpoint.read_text(encoding="utf-8"))
                    values = parse_measurements(log.read_text(
                        encoding="utf-8", errors="replace"), _expected())
                    if (candidate.get("status") == "PASS" and
                            candidate.get("deck_sha256") == job["deck_sha256"] and
                            candidate.get("log_sha256") == _sha(log) and
                            candidate.get("pex_sha256") == _sha(pex) and
                            candidate.get("model_sha256") == _sha(model) and
                            candidate.get("ngspice_version") == source["ngspice_version"] and
                            candidate.get("measurements_v") == values and
                            set(values) == set(_expected())):
                        saved = candidate
                except (OSError, ValueError, TypeError):
                    pass
            if saved is not None:
                job["measurements_v"] = saved["measurements_v"]
                job["log_sha256"] = saved["log_sha256"]
                job["reused_checkpoint"] = True
                print(f"edge: reused {job['case']}", flush=True)
                continue
            if log.exists() or checkpoint.exists():
                raise FileExistsError(f"inspect stale edge log/checkpoint: {log}")
            completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                       cwd=deck.parent, capture_output=True, text=True,
                                       timeout=timeout_s, check=False)
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if (completed.returncode or set(values) != set(_expected()) or
                    not all(math.isfinite(value) for value in values.values())):
                raise RuntimeError(f"incomplete edge measurement: {log}")
            receipt = {"status": "PASS", "deck_sha256": job["deck_sha256"],
                       "log_sha256": _sha(log), "pex_sha256": _sha(pex),
                       "model_sha256": _sha(model),
                       "ngspice_version": source["ngspice_version"],
                       "measurements_v": values}
            checkpoint.write_text(json.dumps(receipt, indent=2) + "\n",
                                  encoding="utf-8")
            job["measurements_v"] = values
            job["log_sha256"] = receipt["log_sha256"]
            print(f"edge: {job['case']}", flush=True)
    report = {
        "format": "automx-cim-wrapper-sample-hold-edge-tt-v1",
        "status": "MEASURED_TT_EDGE_DIAGNOSTIC" if execute else "PREPARED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_sample_hold_sha256": _sha(old_path),
        "pex_sha256": _sha(pex), "model_sha256": _sha(model),
        "script_sha256": _sha(Path(__file__)),
        "times_ns": {"pre": 2.095, "post": 2.15},
        "planned_sims": 2,
        "completed_sims": sum("measurements_v" in job for job in jobs),
        "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
        "summary": _summarize(jobs), "jobs": jobs,
        "not_signoff": "two selected TT schematic decks; ideal sample controls, no switch/layout PEX, ADC, noise or PVT",
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
    report = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in report.items() if key != "jobs"},
                     indent=2))
