"""Measure additional passive 4x4-core PEX stimuli without claiming ADC sign-off.

The default invocation generates ngspice decks and a PREPARED receipt. Add
--run to execute one TT point, or --full-pvt --run for the proposed 27-point
screen. All output is kept separate from the signed-off Stage-5 receipts.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
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

from automx_cim.attention import run_stage1  # noqa: E402
from automx_cim.characterization import build_characterization  # noqa: E402
from automx_cim.circuit.sky130 import E2M1_MAGNITUDES_X2  # noqa: E402
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.mxfp4 import encode_mxfp4  # noqa: E402
from automx_cim.physical.stage5 import CORE, core_pins, parse_spice_subckt_pins  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402


@dataclass(frozen=True)
class Case:
    name: str
    acts: tuple[int, int, int, int]
    weights: tuple[tuple[int, int, int, int], ...]

    @property
    def sums(self) -> tuple[int, int, int, int]:
        return tuple(sum(self.acts[row] * self.weights[row][col] for row in range(4))
                     for col in range(4))


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _matrix(active: int, rotation: int) -> tuple[tuple[int, int, int, int], ...]:
    roles = ("plus", "minus", "alternating", "zero")
    def weight(row: int, col: int) -> int:
        if row >= active:
            return 0
        role = roles[(col + rotation) % 4]
        if role == "plus":
            return 1
        if role == "minus":
            return -1
        if role == "alternating":
            return 1 if row % 2 == 0 else -1
        return 0
    return tuple(tuple(weight(row, col) for col in range(4)) for row in range(4))


def sweep_cases() -> list[Case]:
    """Compact full-code/active-row diagnostic, including both PWM phases."""
    cases = [Case("zero", (0, 0, 0, 0), _matrix(4, 0))]
    for code in E2M1_MAGNITUDES_X2:
        if code == 0:
            continue
        for active in range(1, 5):
            for phase in ("positive", "negative", "alternating"):
                acts = tuple((code if phase == "positive" else -code if phase == "negative"
                              else code if row % 2 == 0 else -code)
                             if row < active else 0 for row in range(4))
                rotation = (active + E2M1_MAGNITUDES_X2.index(code) +
                            ("positive", "negative", "alternating").index(phase)) % 4
                cases.append(Case(f"code{code}_n{active}_{phase}", acts,
                                  _matrix(active, rotation)))
    return cases


def mha_cases(config: Sky130MHAConfig, limit: int = 16) -> list[Case]:
    """Select common and extreme physical calls from the deterministic MHA."""
    if limit < 0:
        raise ValueError("MHA pattern limit must be nonnegative")
    if limit == 0:
        return []
    stage1 = run_stage1(config)
    histogram: Counter[tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]] = Counter()
    for projection in ("WQ", "WK", "WV", "WO"):
        tokens = stage1.input_x if projection != "WO" else stage1.quantized.context
        weights = stage1.payloads[projection].ternary
        for token in tokens:
            act = encode_mxfp4(token).signed_magnitude_x2().reshape(32)
            for row_group in range(8):
                rows = tuple(int(v) for v in act[4 * row_group:4 * row_group + 4])
                for col_group in range(8):
                    columns = tuple(tuple(int(weights[4 * row_group + r, 4 * col_group + c])
                                          for c in range(4)) for r in range(4))
                    histogram[(rows, columns)] += 1
    def extremes(key: tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]) -> tuple[int, int]:
        acts, weights = key
        return (max(abs(value) for value in acts),
                max(abs(sum(acts[row] * weights[row][col] for row in range(4)))
                    for col in range(4)))
    ranked = sorted(histogram, key=lambda key: (-histogram[key], -extremes(key)[0],
                                                -extremes(key)[1], key))
    selected = []
    for key in (max(histogram, key=lambda item: extremes(item)[0]),
                max(histogram, key=lambda item: extremes(item)[1]), *ranked):
        if key not in selected:
            selected.append(key)
        if len(selected) >= limit:
            break
    return [Case(f"mha_{index:02d}", key[0], key[1])
            for index, key in enumerate(selected)]


def pvt_points(full: bool) -> list[tuple[str, float, int]]:
    if not full:
        return [("tt", 1.8, 25)]
    return [(corner, vdd, temperature) for corner in ("tt", "ss", "ff")
            for vdd in (1.62, 1.8, 1.98) for temperature in (-40, 25, 125)]


def summarize_jobs(jobs: list[dict[str, object]]) -> list[dict[str, object]]:
    """Report passive-core transfer diagnostics, not converter accuracy."""
    grouped: dict[tuple[str, float, int], list[dict[str, object]]] = {}
    for job in jobs:
        point = job["point"]
        key = (str(point["corner"]), float(point["vdd_v"]), int(point["temperature_c"]))
        grouped.setdefault(key, []).append(job)
    reports = []
    for (corner, vdd, temperature), group in grouped.items():
        measured = [job for job in group if "measurements_v" in job]
        zero_offsets = []
        nonzero_swings = []
        sample_shifts = []
        polarity_mismatches = 0
        for job in measured:
            measures = job["measurements_v"]
            polarity_mismatches += len(job["polarity_mismatches"])
            for col, total in enumerate(job["integer_sums"]):
                late = abs(measures[f"diff_c{col}_t19"])
                (nonzero_swings if total else zero_offsets).append(late)
                sample_shifts.append(abs(measures[f"diff_c{col}_t19"] -
                                          measures[f"diff_c{col}_t09"]))
        reports.append({"point": {"corner": corner, "vdd_v": vdd,
                                   "temperature_c": temperature},
                        "planned_cases": len(group), "measured_cases": len(measured),
                        "polarity_mismatch_columns": polarity_mismatches,
                        "max_zero_offset_abs_v": max(zero_offsets, default=None),
                        "min_nonzero_swing_abs_v": min(nonzero_swings, default=None),
                        "max_early_late_shift_abs_v": max(sample_shifts, default=None)})
    return reports


def make_deck(case: Case, model: Path, pex: Path,
              point: tuple[str, float, int], *, load_ff: int = 200,
              pwm_unit_ps: int = 100) -> str:
    """Use Stage-5 core pin order and external precharge, with a late sample."""
    if len(case.acts) != 4 or len(case.weights) != 4 or any(len(row) != 4 for row in case.weights):
        raise ValueError("one 4x4 physical case is required")
    if any(abs(value) not in E2M1_MAGNITUDES_X2 for value in case.acts):
        raise ValueError("activation is not a signed E2M1 x2 code")
    if any(value not in (-1, 0, 1) for row in case.weights for value in row):
        raise ValueError("non-ternary weight")
    corner, vdd, temperature = point
    if corner not in ("tt", "ss", "ff") or not 1.0 < vdd < 2.1 or not -100 <= temperature <= 150:
        raise ValueError("unsupported PVT point")
    if not 50 <= load_ff <= 2000 or not 10 <= pwm_unit_ps <= 100:
        raise ValueError("unsupported diagnostic load/PWM width")
    lines = [f".title AutoMX passive-core PEX coverage {case.name}",
             f'.lib "{model.as_posix()}" {corner}',
             f'.include "{pex.as_posix()}"',
             f".param VDD={vdd}", f".temp {temperature}",
             ".option method=gear reltol=1e-4 abstol=1e-12",
             "VVDD VPWR 0 {VDD}",
             "VPRE PREB 0 DC 0 PULSE(0 {VDD} 0.4n 5p 5p 1.8n 4n)"]
    nodes: dict[str, str] = {}
    for col in range(4):
        blp, bln = f"BLP{col}", f"BLN{col}"
        nodes[blp], nodes[bln] = blp, bln
        lines += [f"XPREP{col} {blp} PREB VPWR VPWR sky130_fd_pr__pfet_01v8 W=1.68 L=0.15",
                  f"XPREN{col} {bln} PREB VPWR VPWR sky130_fd_pr__pfet_01v8 W=1.68 L=0.15",
                  f"CBLP{col} {blp} 0 {load_ff}f IC={{VDD}}",
                  f"CBLN{col} {bln} 0 {load_ff}f IC={{VDD}}",
                  f"BDIFF{col} DIFF{col} 0 V=V({bln})-V({blp})"]
    for row, value in enumerate(case.acts):
        for phase, magnitude in (("WLP", max(value, 0)), ("WLN", max(-value, 0))):
            node = f"{phase}{row}"
            nodes[node] = node
            drive = (f"DC 0 PULSE(0 {{VDD}} 0.5n 5p 5p {magnitude * pwm_unit_ps}p 5n)"
                     if magnitude else "0")
            lines.append(f"V{node} {node} 0 {drive}")
    for row in range(4):
        for col in range(4):
            for prefix, enabled in (("WPOS", case.weights[row][col] > 0),
                                    ("WNEG", case.weights[row][col] < 0)):
                pin = f"{prefix}_{row}_{col}"
                nodes[pin] = pin
                lines.append(f"V{pin} {pin} 0 {'{VDD}' if enabled else '0'}")
    nodes["VGND"] = "0"
    nodes["VSUBS"] = "0"
    lines.append("XMACRO " + " ".join(nodes[pin] for pin in core_pins()) + f" {CORE}_pex")
    for col in range(4):
        lines += [f".measure tran diff_c{col}_t09 FIND V(DIFF{col}) AT=0.9n",
                  f".measure tran diff_c{col}_t19 FIND V(DIFF{col}) AT=1.9n",
                  f".measure tran blp_c{col}_t19 FIND V(BLP{col}) AT=1.9n",
                  f".measure tran bln_c{col}_t19 FIND V(BLN{col}) AT=1.9n"]
    lines += [".tran 5p 3n", ".end", ""]
    return "\n".join(lines)


def _expected_measurements() -> tuple[str, ...]:
    return tuple(f"{stem}_c{col}_{time}" for col in range(4)
                 for stem, time in (("diff", "t09"), ("diff", "t19"),
                                    ("blp", "t19"), ("bln", "t19")))


def _validated_checkpoint(root: Path, current: dict[str, object],
                          previous: dict[str, object]) -> dict[str, float] | None:
    """Reuse only a finished job with identical deck metadata and log content."""
    fields = ("point", "case", "activation_x2", "ternary_weights",
              "integer_sums", "deck", "deck_sha256", "log")
    if any(json.loads(json.dumps(current.get(key))) != previous.get(key)
           for key in fields):
        return None
    if previous.get("returncode") != 0 or not isinstance(previous.get("measurements_v"), dict):
        return None
    log = root / str(current["log"])
    if not log.is_file() or not log.stat().st_size:
        return None
    if previous.get("log_sha256") and previous["log_sha256"] != _digest(log):
        return None
    measured = parse_measurements(log.read_text(encoding="utf-8", errors="replace"),
                                  _expected_measurements())
    recorded = previous["measurements_v"]
    if (any(name not in measured or name not in recorded or
            not math.isfinite(measured[name]) or measured[name] != recorded[name]
            for name in _expected_measurements())):
        return None
    return {name: measured[name] for name in _expected_measurements()}


def run(root: Path, *, execute: bool = False, full_pvt: bool = False,
        mha_pattern_limit: int = 16, timeout_s: int = 600) -> dict[str, object]:
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    root = root.resolve()
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    # This validates all Stage-4/5 receipts, hashes and PEX provenance.
    build_characterization(root, config)
    pex_receipt = json.loads((root / "results/receipts/physical/pex.json").read_text(encoding="utf-8"))
    pex = Path(pex_receipt["extracted_spice"]).resolve()
    if parse_spice_subckt_pins(pex, f"{CORE}_pex") != core_pins():
        raise ValueError("PEX top-level pin order differs from Stage-5 contract")
    manifest = json.loads((root / "generated/sky130/spice/stage4_manifest.json").read_text(encoding="utf-8"))
    model = Path(manifest["model_library"]).resolve()
    cases = sweep_cases() + mha_cases(config, mha_pattern_limit)
    points = pvt_points(full_pvt)
    base = root / "results/sky130/core_pex_coverage"
    jobs = []
    for corner, vdd, temperature in points:
        point = (corner, vdd, temperature)
        point_name = f"{corner}_{round(vdd * 1000)}mv_{temperature}c"
        folder = base / point_name
        folder.mkdir(parents=True, exist_ok=True)
        for case in cases:
            deck = folder / f"{case.name}.spice"
            deck.write_text(make_deck(case, model, pex, point), encoding="utf-8")
            jobs.append({"point": {"corner": corner, "vdd_v": vdd, "temperature_c": temperature},
                         "case": case.name, "activation_x2": case.acts,
                         "ternary_weights": case.weights, "integer_sums": case.sums,
                         "deck": str(deck.relative_to(root)), "deck_sha256": _digest(deck),
                         "log": str((folder / f"{case.name}.log").relative_to(root))})
    target = root / "results/receipts/physical/core_pex_coverage.json"
    lineage = {
        "config_sha256": config.sha256,
        "pex_sha256": _digest(pex),
        "model_library_sha256": _digest(model),
        "points": [{"corner": c, "vdd_v": v, "temperature_c": t}
                   for c, v, t in points],
        "case_count": len(cases), "job_count": len(jobs),
    }
    previous = {}
    if execute and target.is_file():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = {}
    # A Stage-5 summary can change only because of a fresh timestamp. The
    # simulator inputs are the PEX, model and generated deck hashes above.
    # Reusing an old job additionally requires the measured ngspice log itself.
    old_jobs = {}
    if (previous.get("format") == "automx-cim-passive-core-pex-coverage-v1" and
            all(previous.get(key) == value for key, value in lineage.items()) and
            isinstance(previous.get("jobs"), list)):
        old_jobs = {entry.get("deck"): entry for entry in previous["jobs"]
                    if isinstance(entry, dict) and isinstance(entry.get("deck"), str)}
        if len(old_jobs) != len(previous["jobs"]):
            old_jobs = {}
    reused = 0
    for job in jobs:
        old = old_jobs.get(job["deck"])
        measurements = (_validated_checkpoint(root, job, old) if old else None)
        if measurements is not None:
            job["measurements_v"] = measurements
            job["polarity_mismatches"] = [
                col for col, total in enumerate(job["integer_sums"])
                if total and measurements[f"diff_c{col}_t19"] * total <= 0]
            job["returncode"] = 0
            job["log_sha256"] = _digest(root / job["log"])
            reused += 1

    failures = []
    ngspice = shutil.which("ngspice") if execute else None
    if execute and not ngspice:
        failures.append("ngspice not on PATH")

    def write_receipt(status: str) -> dict[str, object]:
        receipt = {
            "format": "automx-cim-passive-core-pex-coverage-v1",
            "status": status,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "passive-core PEX transfer screen; no clocked wrapper, ADC, noise, STA or Liberty claim",
            "sample_time_ns": {"early": 0.9, "late": 1.9},
            **lineage,
            "stage5_summary_sha256": _digest(root / "results/receipts/physical/stage5_summary.json"),
            "completed_jobs": sum("measurements_v" in job for job in jobs),
            "reused_checkpoints": reused,
            "point_summary": summarize_jobs(jobs), "failures": failures,
            "jobs": jobs,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        return receipt

    if execute:
        print(f"Validated PEX checkpoints: {reused}/{len(jobs)}", flush=True)
        write_receipt("IN_PROGRESS")
    if execute and ngspice:
        for job in jobs:
            if "measurements_v" in job:
                continue
            deck = root / job["deck"]
            log = root / job["log"]
            if log.is_file():
                log.unlink()  # a failed rerun must not read an old ngspice result
            try:
                completed = subprocess.run([ngspice, "-b", "-o", str(log), str(deck)],
                                           cwd=deck.parent, text=True, capture_output=True,
                                           timeout=timeout_s, check=False)
                job["returncode"] = completed.returncode
                text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else completed.stdout + completed.stderr
                expected = _expected_measurements()
                measures = parse_measurements(text, expected)
                if completed.returncode or not log.is_file() or any(name not in measures or not math.isfinite(measures[name])
                                               for name in expected):
                    failures.append(f"{job['point']} {job['case']}: ngspice exit {completed.returncode}, missing/invalid measures")
                else:
                    job["measurements_v"] = measures
                    job["polarity_mismatches"] = [col for col, total in enumerate(job["integer_sums"])
                                                  if total and measures[f"diff_c{col}_t19"] * total <= 0]
                    job["log_sha256"] = _digest(log)
                    write_receipt("IN_PROGRESS")
                    completed_count = sum("measurements_v" in item for item in jobs)
                    if completed_count == len(jobs) or completed_count % 10 == 0:
                        print(f"PEX coverage: {completed_count}/{len(jobs)} "
                              f"({job['case']})", flush=True)
            except subprocess.TimeoutExpired:
                job["returncode"] = "TIMEOUT"
                failures.append(f"{job['point']} {job['case']}: timeout after {timeout_s}s; "
                                f"inspect {job['log']}")
            if failures:
                break  # keep the first failing deck/log and do not mask it with later jobs
    return write_receipt("FAIL" if failures else "MEASURED_CORE_ONLY" if execute else "PREPARED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true", help="execute ngspice, not only prepare decks")
    parser.add_argument("--full-pvt", action="store_true", help="proposed 3x3x3 PVT screen")
    parser.add_argument("--mha-patterns", type=int, default=16)
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, full_pvt=args.full_pvt,
                 mha_pattern_limit=args.mha_patterns, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items() if key != "jobs"}, indent=2))
    if result["status"] == "FAIL":
        raise SystemExit(1)
