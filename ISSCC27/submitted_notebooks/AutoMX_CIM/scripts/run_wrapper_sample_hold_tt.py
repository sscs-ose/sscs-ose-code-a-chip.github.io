"""TT PEX diagnostic of a candidate transmission-gate sample/hold.

Three already inspected MHA phase-A cases are used deliberately: two with no
row drive and one active comparison. This is front-end feasibility work, not
an independent decoder holdout, a laid-out S/H, or ADC/wrapper sign-off.
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
from scripts.run_core_candidate_pex import make_pex_deck  # noqa: E402
from scripts.run_wrapper_input_loading_screen import _case, _sources  # noqa: E402

SOURCE = Path("results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json")
OUTPUT = Path("results/sky130/wrapper_sample_hold_tt")
ZERO_CASES = ("mha_118_a", "mha_119_a")
BITLINE_FF = 800
HOLD_FF = 20
PWM_UNIT_PS = 50


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _expected() -> list[str]:
    return [f"h{side}_c{col}_{when}" for col in range(4)
            for side in ("blp", "bln") for when in ("t215", "t24")]


def make_sample_hold_deck(case, model: Path, pex: Path) -> str:
    """Add explicit SKY130 TG switches and 20 fF holds to an 800 fF PEX deck."""
    lines = make_pex_deck(case, model, pex, BITLINE_FF, PWM_UNIT_PS).splitlines()
    if sum(line.startswith(".tran ") for line in lines) != 1:
        raise ValueError("unexpected core PEX transient deck")
    lines[0] = f".title AutoMX candidate sample hold {case.name}"
    block = [
        "* Candidate S/H; 800 fF fixed BL + 20 fF hold while connected.",
        "* Both controls are ideal here; their physical pulse generator is absent.",
        "VSAM SAM 0 PULSE(0 {VDD} 1.8n 5p 5p 0.3n 10n)",
        "VSAMB SAMB 0 PULSE({VDD} 0 1.8n 5p 5p 0.3n 10n)",
    ]
    for col in range(4):
        for side in ("BLP", "BLN"):
            bl = f"{side}{col}"
            hold = f"H{side}{col}"
            # SKY130 primitive terminal order is drain, gate, source, body.
            block.extend((
                f"XSHN_{side}{col} {bl} SAM {hold} 0 sky130_fd_pr__nfet_01v8 W=1.68 L=0.15",
                f"XSHP_{side}{col} {bl} SAMB {hold} VPWR sky130_fd_pr__pfet_01v8 W=1.68 L=0.15",
                f"C{hold} {hold} 0 {HOLD_FF}f IC={{VDD}}",
            ))
            key = side.lower()
            for when, time_ns in (("t215", "2.15n"), ("t24", "2.4n")):
                block.append(f".measure tran h{key}_c{col}_{when} FIND V({hold}) AT={time_ns}")
    index = next(i for i, line in enumerate(lines) if line.startswith(".tran "))
    lines[index:index] = block
    return "\n".join(lines) + "\n"


def _summary(jobs: list[dict]) -> dict:
    drifts = []
    input_errors = []
    ranges = []
    for job in jobs:
        if "measurements_v" not in job:
            continue
        values = job["measurements_v"]
        source = job["source_measurements_v"]
        for col in range(4):
            held = {}
            for when in ("t215", "t24"):
                p = values[f"hblp_c{col}_{when}"]
                n = values[f"hbln_c{col}_{when}"]
                held[when] = (p, n)
                ranges.extend((p, n))
            p0, n0 = held["t215"]
            p1, n1 = held["t24"]
            drifts.append(abs((n1 - p1) - (n0 - p0)))
            input_errors.extend((abs(p0 - source[f"blp_c{col}_t21"]),
                                 abs(n0 - source[f"bln_c{col}_t21"])))
    return ({"maximum_held_differential_drift_v": max(drifts),
             "maximum_hold_vs_original_820ff_bitline_v": max(input_errors),
             "held_node_min_v": min(ranges), "held_node_max_v": max(ranges)}
            if drifts else {})


def run(root: str | Path, *, execute: bool = False, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    _, _, model, pex, _ = _sources(root)
    source_path = root / SOURCE
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if (source.get("format") != "automx-cim-wrapper-idle-augmented-tt-v1" or
            source.get("status") != "MEASURED_TT_IDLE_AUGMENTATION_DIAGNOSTIC" or
            source.get("load_ff") != BITLINE_FF + HOLD_FF or
            source.get("pwm_unit_ps") != PWM_UNIT_PS or
            source.get("completed_new_sims") != 74 or
            source.get("pex_sha256") != _sha(pex) or
            source.get("model_sha256") != _sha(model)):
        raise ValueError("complete matching 820 fF source report required")
    lookup = {job["case"]: job for job in source["jobs"]["fresh_holdout"]}
    if len(lookup) != 64 or any(name not in lookup for name in ZERO_CASES):
        raise ValueError("required near-rail source cases are missing")
    active = next((name for rank in range(96, 118)
                   if (name := f"mha_{rank}_a") in lookup and
                   _case(lookup[name]).acts[:2] != (0, 0)), None)
    if active is None:
        raise ValueError("no active phase-A comparison case")
    folder = root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for name in (active, *ZERO_CASES):
        original = lookup[name]
        case = _case(original)
        if name in ZERO_CASES and case.acts[:2] != (0, 0):
            raise ValueError(f"expected no-row-drive case: {name}")
        deck = folder / f"{name}.spice"
        content = make_sample_hold_deck(case, model, pex)
        if deck.exists() and deck.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"refusing changed S/H deck: {deck}")
        deck.write_text(content, encoding="utf-8")
        jobs.append({
            "case": name, "no_row_drive": case.acts[:2] == (0, 0),
            "deck": str(deck.relative_to(root)), "deck_sha256": _sha(deck),
            "log": str((folder / f"{name}.log").relative_to(root)),
            "checkpoint": str((folder / f"{name}.receipt.json").relative_to(root)),
            "source_measurements_v": original["measurements_v"],
        })
    if execute:
        ngspice = shutil.which("ngspice")
        if not ngspice:
            raise FileNotFoundError("ngspice not on PATH")
        version = subprocess.run([ngspice, "-v"], text=True,
                                 capture_output=True, timeout=15, check=False)
        if (version.stdout + version.stderr).strip() != source["ngspice_version"]:
            raise ValueError("ngspice version differs from 820 fF source run")
        for job in jobs:
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
                            candidate.get("pex_sha256") == _sha(pex) and
                            candidate.get("model_sha256") == _sha(model) and
                            candidate.get("ngspice_version") == source["ngspice_version"] and
                            candidate.get("log_sha256") == _sha(log) and
                            set(parsed) == set(_expected()) and
                            candidate.get("measurements_v") == parsed):
                        saved = candidate
                except (OSError, ValueError, TypeError):
                    pass
            if saved is not None:
                job["measurements_v"] = saved["measurements_v"]
                job["log_sha256"] = saved["log_sha256"]
                job["reused_checkpoint"] = True
                print(f"sample_hold: reused {job['case']}", flush=True)
                continue
            if log.exists() or checkpoint.exists():
                raise FileExistsError(f"inspect stale log/checkpoint before rerun: {log}")
            completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                       cwd=deck.parent, text=True, capture_output=True,
                                       timeout=timeout_s, check=False)
            output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            values = parse_measurements(output, _expected())
            if (completed.returncode or set(values) != set(_expected()) or
                    not all(math.isfinite(value) for value in values.values())):
                raise RuntimeError(f"incomplete S/H simulation: {log}")
            job["measurements_v"] = values
            job["log_sha256"] = _sha(log)
            checkpoint.write_text(json.dumps({
                "status": "PASS", "deck_sha256": job["deck_sha256"],
                "pex_sha256": _sha(pex), "model_sha256": _sha(model),
                "ngspice_version": source["ngspice_version"],
                "log_sha256": job["log_sha256"], "measurements_v": values,
            }, indent=2) + "\n", encoding="utf-8")
            print(f"sample_hold: {job['case']}", flush=True)
    report = {
        "format": "automx-cim-wrapper-sample-hold-tt-v1",
        "status": "MEASURED_TT_SAMPLE_HOLD_DIAGNOSTIC" if execute else "PREPARED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_report_sha256": _sha(source_path),
        "pex_sha256": _sha(pex), "model_sha256": _sha(model),
        "script_sha256": _sha(Path(__file__)),
        "bitline_capacitance_ff": BITLINE_FF,
        "sample_hold_capacitance_ff": HOLD_FF,
        "switch": "sky130_fd_pr__nfet_01v8 + sky130_fd_pr__pfet_01v8 transmission gate",
        "sampling_window_ns": [1.8, 2.1],
        "planned_sims": len(jobs), "completed_sims": sum(
            "measurements_v" in job for job in jobs),
        "reused_checkpoints": sum(job.get("reused_checkpoint", False) for job in jobs),
        "summary": _summary(jobs), "jobs": jobs,
        "not_signoff": "ideal sampling control and schematic candidate only; no switch/layout PEX, ADC, noise, PVT or full wrapper",
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
