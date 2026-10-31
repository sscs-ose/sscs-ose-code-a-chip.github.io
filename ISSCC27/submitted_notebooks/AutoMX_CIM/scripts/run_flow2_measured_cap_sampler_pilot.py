#!/usr/bin/env python3
"""Recheck the frozen 3.36-um sampler using the measured hold-cap load.

The eight hold capacitors are equivalent ideal capacitors sized from the
isolated leaf's TT charge-ramp result. This is a fast circuit screen, not a
composite PEX or a physical substrate-contact check.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.spice import parse_measurements  # noqa: E402
from scripts import run_flow2_hold_cap_tt as charge  # noqa: E402
from scripts import run_flow2_pvt_switch_control as control  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery as recovery  # noqa: E402

FORMAT = "automx-cim-flow2-measured-cap-sampler-pilot-v1"
SOURCE = Path("results/sky130/flow2_periphery_leaf/hold_cap_charge_tt_20261017_02/hold_cap_charge_tt_recovery.json")
OUTPUT = campaign.OUTPUT / "measured_cap_sampler_pilot"
CORRECT_STATUS = "MEASURED_HOLD_CAP_TT_SUBSTRATE_REFERENCED_DIAGNOSTIC"
VARIANT = "simultaneous_50ps"
HOLD_RE = re.compile(r"^C(HBL[PN][0-3]) \1 0 20f IC=\{VDD\}$")


def _verified_cap(root: Path) -> tuple[dict, str]:
    path = root / SOURCE
    if not path.is_file():
        raise FileNotFoundError(f"copy the measured hold-cap receipt from the server: {path}")
    report = campaign._read(path)
    if (report.get("format") != "automx-cim-flow2-hold-cap-tt-substrate-recovery-v1" or
            report.get("status") != CORRECT_STATUS or
            report.get("returncode") != 0 or
            report.get("substrate_reference_ohms") != 1_000_000_000 or
            report.get("original_pex_sha256") !=
            "d79fabf9b5a0a6d173437354a0abdddd91cf56ae08e1338f894d682e999f634f"):
        raise ValueError("complete, linked hold-cap TT recovery is required")
    view, pex_receipt, leaf_receipt = charge._source(
        root, "hold_cap_mim3_20261017_02", "hold_cap_pex_20261017_01")
    failed = root / "results/sky130/flow2_periphery_leaf/hold_cap_charge_tt_20261017_01/hold_cap_charge_tt.json"
    if (report.get("original_pex_sha256") != campaign._sha(view) or
            report.get("pex_receipt_sha256") != campaign._sha(pex_receipt) or
            report.get("leaf_receipt_sha256") != campaign._sha(leaf_receipt) or
            not failed.is_file() or
            report.get("source_failed_receipt_sha256") != campaign._sha(failed)):
        raise ValueError("hold-cap recovery provenance changed")
    for name in ("derived_pex", "deck", "log"):
        charge._verified_file(root, report.get(name), name)
    log = root / report["log"]["path"]
    parsed = parse_measurements(log.read_text(encoding="utf-8", errors="replace"),
                                expected=charge.MEASURES)
    if (parsed != report.get("pex_measurements") or
            not 1.75 <= parsed.get("v_after", 0) - parsed.get("v_before", 0) <= 1.85):
        raise ValueError("hold-cap recovery measurements differ from ngspice log")
    cap_ff = report.get("pex_effective_capacitance_ff")
    schematic_ff = report.get("schematic_effective_capacitance_ff")
    parasitic_ff = report.get("pex_minus_schematic_ff")
    if (not all(isinstance(v, (int, float)) and math.isfinite(v)
                for v in (cap_ff, schematic_ff, parasitic_ff)) or
            not 35 <= cap_ff <= 45 or
            not math.isclose(cap_ff - schematic_ff, parasitic_ff, abs_tol=1e-9) or
            not math.isclose(cap_ff,
                             abs(parsed["charge_c"]) /
                             (parsed["v_after"] - parsed["v_before"]) * 1e15,
                             abs_tol=1e-9)):
        raise ValueError("hold-cap charge result is incomplete or out of range")
    return report, campaign._sha(path)


def replace_hold_capacitance(source: str, cap_ff: float) -> str:
    """Change exactly eight initialized 20-fF held-node capacitors."""
    if not math.isfinite(cap_ff) or cap_ff <= 0:
        raise ValueError("positive measured capacitance required")
    lines = source.splitlines()
    indices = [i for i, line in enumerate(lines)
               if line.startswith(("CHBLP", "CHBLN"))]
    expected = {f"HBL{side}{col}" for side in ("P", "N") for col in range(4)}
    if (len(indices) != 8 or
            {HOLD_RE.fullmatch(lines[i]).group(1) for i in indices
             if HOLD_RE.fullmatch(lines[i])} != expected or
            sum(line.startswith(".tran ") for line in lines) != 1):
        raise ValueError("unexpected 20-fF sample/hold deck; refusing substitution")
    for i in indices:
        lines[i] = lines[i].replace(" 20f IC={VDD}", f" {cap_ff:.9g}f IC={{VDD}}")
    lines[0] = lines[0] + " | equivalent measured MIM3 hold load"
    return "\n".join(lines) + "\n"


def _save(path: Path, report: dict) -> None:
    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    campaign._save(path, report)


def run(root: str | Path, *, execute: bool = False,
        timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("timeout must be positive")
    cap, cap_receipt_sha = _verified_cap(root)
    inputs, cases, worst, _, _ = control._source(root)
    names = [*worst, control.ZERO_CASE]
    if len(names) != 3 or len(set(names)) != 3 or any(name not in cases for name in names):
        raise ValueError("two distinct worst cases and one zero case required")
    cap_ff = float(cap["pex_effective_capacitance_ff"])
    script_sha = campaign._sha(Path(__file__))
    folder = root / OUTPUT / f"cap_{cap_receipt_sha[:12]}_runner_{script_sha[:12]}"
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for point in campaign.PVT_POINTS:
        for name in names:
            case = cases[name]
            tag = f"{name}_{point[0]}"
            deck = folder / f"{tag}.spice"
            source = control._deck(case, inputs["model"], inputs["pex"], VARIANT, point)
            content = replace_hold_capacitance(source, cap_ff)
            if deck.is_file() and deck.read_text(encoding="utf-8") != content:
                raise FileExistsError(f"measured-cap deck changed: {deck}")
            deck.write_text(content, encoding="utf-8")
            jobs.append({**campaign._vectors(case),
                         "phase": name.rsplit("_", 1)[-1],
                         "variant": VARIANT,
                         "switch_width_um": control.WIDTH_UM,
                         "turnoff_start_ns": control.OFF_NS,
                         "point": {"corner": point[0], "vdd_v": point[1],
                                   "temperature_c": point[2]},
                         "deck": deck.relative_to(root).as_posix(),
                         "deck_sha256": campaign._sha(deck),
                         "log": (folder / f"{tag}.log").relative_to(root).as_posix(),
                         "checkpoint": (folder / f"{tag}.receipt.json").relative_to(root).as_posix()})
    summary = folder / "summary.json"
    report = {"format": FORMAT,
              "status": "PREPARED", "conclusion": "NOT_MEASURED",
              "source_cap_receipt": SOURCE.as_posix(),
              "source_cap_receipt_sha256": cap_receipt_sha,
              "source_cap_pex_sha256": cap["original_pex_sha256"],
              "script_sha256": script_sha,
              "core_pex_sha256": inputs["pex_sha"],
              "model_sha256": inputs["model_sha"],
              "ngspice_version": inputs["version"],
              "hold_capacitance_ff": cap_ff,
              "historical_ideal_capacitance_ff": 20,
              "sampler_switch_width_um": control.WIDTH_UM,
              "control_variant": VARIANT,
              "pilot_cases": names,
              "corners": [point[0] for point in campaign.PVT_POINTS],
              "capture_budget_v": recovery.BUDGET_V,
              "planned_sims": len(jobs), "completed_sims": 0,
              "reused_checkpoints": 0,
              "jobs": jobs, "summary": {},
              "summary_path": summary.relative_to(root).as_posix(),
              "history_path": (folder / "history.log").relative_to(root).as_posix(),
              "not_signoff": "equivalent ideal held-node capacitance from one TT leaf charge test; schematic TG and ideal controls; no physical sampler/driver, composite PEX, substrate tie, ADC input, independent holdout, noise or full PVT"}
    if summary.is_file():
        previous = campaign._read(summary)
        keys = ("format", "source_cap_receipt_sha256", "source_cap_pex_sha256",
                "script_sha256", "core_pex_sha256", "model_sha256",
                "ngspice_version", "hold_capacitance_ff", "pilot_cases", "corners")
        if any(previous.get(key) != report[key] for key in keys) or len(previous.get("jobs", [])) != 9:
            raise FileExistsError(f"previous measured-cap pilot differs: {summary}")
    if not execute:
        return previous if summary.is_file() else report
    report["status"] = "RUNNING"
    _save(summary, report)
    recovery._event(folder, f"SESSION_START cap_receipt={cap_receipt_sha} "
                    f"cap_ff={cap_ff:.9g} core_pex={inputs['pex_sha']} "
                    f"runner={script_sha} timeout_s={timeout_s}")
    try:
        executable = campaign._ngspice(inputs["version"])
        for index, job in enumerate(jobs, 1):
            checkpoint = root / job["checkpoint"]
            reused = checkpoint.is_file()
            campaign._measure(root, job, executable=executable,
                              version=inputs["version"],
                              pex_sha=inputs["pex_sha"],
                              model_sha=inputs["model_sha"],
                              timeout_s=timeout_s)
            job["decomposition"] = control._decompose(job)
            report["completed_sims"] = index
            report["reused_checkpoints"] += int(reused and
                                                   not job.get("archived_stale_artifacts"))
            _save(summary, report)
            recovery._event(folder, f"DONE {index}/{len(jobs)} {job['case']} "
                            f"{job['point']['corner']} capture="
                            f"{job['decomposition']['maximum_capture_error_late_v']:.6g}V "
                            f"log_sha256={job['log_sha256']}")
            print(f"Measured-cap sampler: {index}/{len(jobs)} "
                  f"{job['case']} {job['point']['corner']}", flush=True)
        metrics = [job["decomposition"] for job in jobs]
        report["summary"] = {
            "maximum_pre_turnoff_tracking_error_abs_v": max(
                item["maximum_pre_turnoff_tracking_error_abs_v"] for item in metrics),
            "maximum_turnoff_differential_step_abs_v": max(
                item["maximum_turnoff_differential_step_abs_v"] for item in metrics),
            "maximum_post_turnoff_drift_abs_v": max(
                item["maximum_post_turnoff_drift_abs_v"] for item in metrics),
            "maximum_capture_error_late_v": max(
                item["maximum_capture_error_late_v"] for item in metrics),
            "cases_exceeding_capture_budget": sum(
                item["maximum_capture_error_late_v"] > recovery.BUDGET_V
                for item in metrics),
        }
        report["status"] = "MEASURED_EQUIVALENT_CAP_PILOT"
        report["conclusion"] = ("SELECTED_CASE_CAPTURE_TARGET_MET"
                                if report["summary"]["cases_exceeding_capture_budget"] == 0
                                else "CAPTURE_BUDGET_EXCEEDED")
        _save(summary, report)
        recovery._event(folder, f"COMPLETE {report['conclusion']}")
        return report
    except (OSError, ValueError, RuntimeError, TimeoutError, KeyError, TypeError) as error:
        report["status"] = "FAILED"
        report["failure"] = f"{type(error).__name__}: {error}"
        _save(summary, report)
        recovery._event(folder, f"SESSION_FAILED {report['failure']}")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps({key: value for key, value in result.items() if key != "jobs"},
                     indent=2, ensure_ascii=False))
    if result["status"] == "FAILED":
        raise SystemExit(1)
