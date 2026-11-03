#!/usr/bin/env python3
"""Audit the copied 2+2 input range and historical sample/hold edge evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_flow2_baseline import digest, read_json
from scripts.compare_flow2_staging import compare

RECEIPT = Path("results/receipts/flow2_readout_gate.json")
REPORT = Path("docs/flow2_readout_gate.md")
HOLDOUT = Path("results/sky130/post49_partition_full_tt/holdout/measured.json")
SAMPLE = Path("results/sky130/wrapper_sample_hold_tt/measured.json")
DECOMP = Path("results/sky130/wrapper_sample_hold_tt/decomposition.json")
EDGE = Path("results/sky130/wrapper_sample_hold_edge_tt/measured.json")


def bitline_range(report: dict) -> dict:
    """Use measured t19/t21 BL nodes, without reusing decoder outcomes."""
    jobs = report.get("jobs", [])
    if len(jobs) != 64 or report.get("completed_sims") != 64:
        raise ValueError("2+2 holdout needs all 64 measured phase jobs")
    values = []
    common_modes = []
    for job in jobs:
        measured = job.get("measurements_v", {})
        for col in range(4):
            for when in ("t19", "t21"):
                p = float(measured[f"blp_c{col}_{when}"])
                n = float(measured[f"bln_c{col}_{when}"])
                if not math.isfinite(p) or not math.isfinite(n):
                    raise ValueError("non-finite bitline voltage")
                values.extend((p, n))
                common_modes.append((p + n) / 2)
    return {"node_samples": len(values), "minimum_v": min(values),
            "maximum_v": max(values),
            "common_mode_minimum_v": min(common_modes),
            "common_mode_maximum_v": max(common_modes)}


def inspect(root: str | Path, evidence_root: str | Path) -> dict:
    root = Path(root).resolve()
    evidence = Path(evidence_root)
    evidence = (evidence if evidence.is_absolute() else root / evidence).resolve()
    staged = compare(root, evidence)
    issues = []
    fatal = bool(staged["missing_staged"] or staged["staged_integrity_issues"])
    if fatal:
        issues.append("staged Stage-5/2+2 evidence is incomplete")
    for item in staged.get("readout_lineage_issues", []):
        if item["report"] in ("idle TT loaded source", "sample/hold idle source",
                              "sample/hold edge source"):
            issues.append(f"historical readout chain broken: {item['report']}")
            fatal = True
    holdout = read_json(evidence / HOLDOUT) or {}
    sample = read_json(evidence / SAMPLE) or {}
    decomp = read_json(evidence / DECOMP) or {}
    edge = read_json(evidence / EDGE) or {}
    for label, data, expected in (
        ("2+2 holdout", holdout, "MEASURED_2P2_HOLDOUT_TT"),
        ("sample/hold", sample, "MEASURED_TT_SAMPLE_HOLD_DIAGNOSTIC"),
        ("decomposition", decomp, "DIAGNOSTIC_ONLY"),
        ("edge", edge, "MEASURED_TT_EDGE_DIAGNOSTIC"),
    ):
        if data.get("status") != expected:
            issues.append(f"{label}: missing or unexpected status")
            fatal = True
    if decomp.get("source_measured_sha256") != digest(evidence / SAMPLE):
        issues.append("sample/hold decomposition source hash differs")
        fatal = True
    if edge.get("source_sample_hold_sha256") != digest(evidence / SAMPLE):
        issues.append("edge source hash differs from sample/hold measurement")
        fatal = True
    for label, data, expected in (("sample/hold", sample, 3), ("edge", edge, 2)):
        if data.get("planned_sims") != expected or data.get("completed_sims") != expected:
            issues.append(f"{label}: selected TT cases incomplete")
            fatal = True
    try:
        bl = bitline_range(holdout)
    except (ValueError, KeyError, TypeError) as error:
        issues.append(f"2+2 bitline range unavailable: {error}")
        fatal = True
        bl = None
    target = 0.0008
    acquisition = (decomp.get("summary") or {}).get(
        "maximum_abs_differential_acquisition_delta_v")
    pre = (edge.get("summary") or {}).get(
        "maximum_abs_differential_tracking_delta_pre_v")
    post = (edge.get("summary") or {}).get(
        "maximum_abs_differential_tracking_delta_post_v")
    held_max = (sample.get("summary") or {}).get("held_node_max_v")
    try:
        acquisition, pre, post, held_max = map(float,
                                               (acquisition, pre, post, held_max))
        if not all(math.isfinite(v) for v in (acquisition, pre, post, held_max)):
            raise ValueError("non-finite summary")
    except (TypeError, ValueError):
        issues.append("sample/hold or edge summary is incomplete")
        fatal = True
        acquisition = pre = post = held_max = None
    current_pex_sha = next((item["staged_sha256"] for item in staged["files"]
                            if item["path"].endswith(".pex.spice")), None)
    historical_pex_sha = sample.get("pex_sha256")
    same_pex = bool(current_pex_sha and historical_pex_sha == current_pex_sha)
    if not same_pex:
        issues.append("historical sample/hold PEX differs from latest Stage-5 PEX")
    if acquisition is not None and acquisition > target:
        issues.append("selected-case differential acquisition exceeds 0.8 mV budget")
    return {
        "format": "automx-cim-flow2-readout-gate-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_EVIDENCE" if fatal else
                  "BLOCKED_READOUT_REMEASUREMENT" if issues else
                  "MEASURED_SELECTED_CASE_DIAGNOSTIC",
        "scope": "copied evidence only; 2+2 bitline range uses latest PEX, S/H and edge use historical PEX; no new simulation",
        "evidence_root": str(evidence),
        "input_sha256": {str(path): digest(evidence / path)
                         for path in (HOLDOUT, SAMPLE, DECOMP, EDGE)},
        "current_pex_sha256": current_pex_sha,
        "historical_sample_hold_pex_sha256": historical_pex_sha,
        "same_pex": same_pex,
        "current_2p2_holdout_bitline_range": bl,
        "historical_selected_case_sample_hold": {
            "target_differential_error_v": target,
            "maximum_differential_acquisition_error_v": acquisition,
            "acquisition_error_over_budget": (
                acquisition / target if acquisition is not None else None),
            "maximum_pre_edge_differential_tracking_v": pre,
            "maximum_post_edge_differential_tracking_v": post,
            "held_node_maximum_v": held_max,
            "held_node_excess_over_1p8v_v": (
                max(0.0, held_max - 1.8) if held_max is not None else None),
        },
        "issues": issues,
        "next_actions": [
            "Measure two selected sample/hold cases against the latest Stage-5 PEX in a new result namespace.",
            "Sweep switch size and turnoff behavior; measure pre-edge acquisition and post-edge differential shift.",
            "Only after a plausible candidate, sweep a continuous aperture and calibrate actual held nodes before a new untouched MHA cohort.",
        ],
        "not_signoff": "historical TT schematic samples and current passive-core bitline range; no physical S/H, ADC, PVT or wrapper verification",
    }


def markdown(report: dict) -> str:
    b = report["current_2p2_holdout_bitline_range"] or {}
    s = report["historical_selected_case_sample_hold"]
    lines = ["# Flow 2 readout gate", "",
             f"Status: **{report['status']}**. No SPICE run was performed.",
             f"Evidence root: `{report['evidence_root']}`.", "",
             "| Quantity | Value | Evidence |", "| --- | ---: | --- |",
             f"| 2+2 BL range at 1.9/2.1 ns | {b.get('minimum_v')}–{b.get('maximum_v')} V | latest staged 64-job TT holdout |",
             f"| S/H differential acquisition error | {s['maximum_differential_acquisition_error_v']} V | historical three-case TT schematic |",
             f"| Error / 0.8 mV target | {s['acquisition_error_over_budget']}× | historical selected cases |",
             f"| Pre/post edge differential tracking | {s['maximum_pre_edge_differential_tracking_v']} / {s['maximum_post_edge_differential_tracking_v']} V | historical two-case TT schematic |",
             f"| Held-node peak | {s['held_node_maximum_v']} V | historical three-case TT schematic |",
             "", "## Provenance and next actions", "",
             f"- Latest core PEX: `{report['current_pex_sha256']}`.",
             f"- Historical S/H PEX: `{report['historical_sample_hold_pex_sha256']}`."]
    lines.extend(f"- Gate: {issue}." for issue in report["issues"])
    lines.extend(f"- Next: {step}" for step in report["next_actions"])
    lines += ["", "The edge data suggest clock feedthrough or charge injection; that is an inference from the two measured cases, not a proven mechanism or a wrapper sign-off.", ""]
    return "\n".join(lines)


def run(root: str | Path, evidence_root: str | Path = "server_results") -> dict:
    root = Path(root).resolve()
    report = inspect(root, evidence_root)
    for relative, content in ((RECEIPT, json.dumps(report, indent=2) + "\n"),
                              (REPORT, markdown(report))):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--evidence-root", type=Path, default=Path("server_results"))
    args = parser.parse_args()
    result = run(args.root, args.evidence_root)
    print(json.dumps({key: result[key] for key in (
        "status", "same_pex", "current_2p2_holdout_bitline_range",
        "historical_selected_case_sample_hold", "issues")}, indent=2))
