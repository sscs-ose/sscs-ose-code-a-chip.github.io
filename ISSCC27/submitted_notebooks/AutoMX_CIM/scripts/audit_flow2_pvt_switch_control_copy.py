#!/usr/bin/env python3
"""Verify a downloaded switch-control pilot without requiring the server PDK."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.spice import parse_measurements  # noqa: E402
from scripts import run_flow2_pvt_switch_control as control  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402


def _single_summary(folder: Path) -> Path:
    matches = sorted(folder.glob("*/summary.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one copied summary under {folder}; found {len(matches)}")
    return matches[0]


def _verify_job(job: dict, pilot: Path, summary: dict) -> None:
    deck, log, receipt = (pilot / Path(job[key]).name for key in
                          ("deck", "log", "checkpoint"))
    if not all(path.is_file() for path in (deck, log, receipt)):
        raise FileNotFoundError(f"copied deck/log/receipt incomplete: {job['case']}")
    if (campaign._sha(deck) != job.get("deck_sha256") or
            campaign._sha(log) != job.get("log_sha256")):
        raise ValueError(f"copied deck/log hash differs: {job['case']}")
    saved = campaign._read(receipt)
    parsed = parse_measurements(log.read_text(
        encoding="utf-8", errors="replace"), campaign._expected())
    if (saved.get("status") != "PASS" or
            saved.get("deck_sha256") != job["deck_sha256"] or
            saved.get("log_sha256") != job["log_sha256"] or
            saved.get("pex_sha256") != summary["pex_sha256"] or
            saved.get("model_sha256") != summary["model_sha256"] or
            saved.get("ngspice_version") != summary["ngspice_version"] or
            set(parsed) != set(campaign._expected()) or
            parsed != saved.get("measurements_v") or
            parsed != job.get("measurements_v")):
        raise ValueError(f"copied ngspice receipt differs: {job['case']}")
    if job.get("decomposition") is not None and job["decomposition"] != control._decompose(job):
        raise ValueError(f"copied differential decomposition differs: {job['case']}")


def audit(root: str | Path) -> dict:
    root = Path(root).resolve()
    current = _single_summary(root / "server_results/pvt_switch_control")
    previous = _single_summary(root / "server_results/pvt_switch_width")
    report = campaign._read(current)
    prior = campaign._read(previous)
    if (report.get("format") != control.FORMAT or
            report.get("status") not in control.TERMINAL or
            report.get("source_switch_width_sha256") != campaign._sha(previous) or
            report.get("script_sha256") != campaign._sha(Path(control.__file__)) or
            prior.get("status") != "BLOCKED_SWITCH_WIDTH_PILOT" or
            report.get("pex_sha256") != prior.get("pex_sha256") or
            report.get("model_sha256") != prior.get("model_sha256")):
        raise ValueError("copied control pilot source/provenance mismatch")
    baseline = report.get("reused_baseline_jobs", [])
    jobs = report.get("jobs", [])
    if (len(baseline) != 4 or len(jobs) != 26 or
            report.get("planned_new_sims") != 26 or
            report.get("completed_new_sims") != 26):
        raise ValueError("copied control pilot is incomplete")
    names = set(report["pilot_cases"])
    if len(names) != 3 or control.ZERO_CASE not in names:
        raise ValueError("copied pilot case matrix differs")
    for job in baseline:
        _verify_job(job, previous.parent / "pilot", report)
    for job in jobs:
        _verify_job(job, current.parent / "pilot", report)
    grid = control._grid(baseline + jobs, names)
    status, selected, diagnostic = control._decision(grid)
    if (report.get("grid") != grid or report["status"] != status or
            report.get("selected_control_variant") != selected or
            report.get("best_diagnostic_variant") != diagnostic):
        raise ValueError("copied pilot grid/conclusion differs from raw logs")
    result = {
        "format": "automx-cim-flow2-switch-control-copy-audit-v1",
        "status": "PASS_COPY_INTEGRITY",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_summary_sha256": campaign._sha(previous),
        "control_summary_sha256": campaign._sha(current),
        "control_status": status,
        "reused_baseline_jobs_verified": len(baseline),
        "new_jobs_verified": len(jobs),
        "selected_control_variant": selected,
        "best_diagnostic_variant": diagnostic,
        "grid": grid,
        "scope": "copied deck/log/receipt and analysis integrity only; no new SPICE or physical wrapper run",
    }
    target = (root / "results/sky130/flow2_copy_audits" /
              f"pvt_switch_control_{result['control_summary_sha256'][:12]}.json")
    campaign._save(target, result)
    result["audit_path"] = str(target.relative_to(root))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2, ensure_ascii=False))
