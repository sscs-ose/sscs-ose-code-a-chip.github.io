#!/usr/bin/env python3
"""Compare a copied server evidence bundle without replacing local measurements."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_flow2_baseline import digest, read_json  # noqa: E402

DEFAULT_STAGING = Path("handoff/flow2_server_20261012")
RECEIPT = Path("results/receipts/flow2_staging_comparison.json")
REPORT = Path("docs/flow2_staging_comparison.md")
CORE = "automx_ternary_cim_4x4_core"
REQUIRED = (
    "generated/sky130/spice/stage4_manifest.json",
    f"generated/sky130/spice/macro/{CORE}.spice",
    "results/receipts/physical/stage5_summary.json",
    "results/receipts/physical/layout.json",
    "results/sky130/post49_partition_full_tt/calibration/measured.json",
    "results/sky130/post49_partition_full_tt/holdout/measured.json",
    "results/sky130/wrapper_load_full_tt/c820ff/measured.json",
    "results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json",
    "results/sky130/wrapper_sample_hold_tt/measured.json",
    "results/sky130/wrapper_sample_hold_tt/decomposition.json",
    "results/sky130/wrapper_sample_hold_edge_tt/measured.json",
    "configs/sky130_mha_tiny.json",
    f"physical/sky130/layout/generate_{CORE}.tcl",
    f"physical/sky130/macro/{CORE}.gds",
    f"physical/sky130/macro/{CORE}.lef",
    f"physical/sky130/macro/{CORE}.pex.spice",
)
READOUT_REPORTS = {
    "loaded TT": "results/sky130/wrapper_load_full_tt/c820ff/measured.json",
    "idle TT": "results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json",
    "sample/hold TT": "results/sky130/wrapper_sample_hold_tt/measured.json",
    "sample/hold edge TT": "results/sky130/wrapper_sample_hold_edge_tt/measured.json",
}


def compare(root: str | Path, staging: str | Path) -> dict:
    root = Path(root).resolve()
    staging = Path(staging)
    staging = (staging if staging.is_absolute() else root / staging).resolve()
    files = []
    for relative in REQUIRED:
        staged = staging / relative
        local = root / relative
        server_hash, local_hash = digest(staged), digest(local)
        data = read_json(staged) if staged.suffix == ".json" else None
        files.append({
            "path": relative, "staged_sha256": server_hash,
            "local_sha256": local_hash,
            "comparison": ("MISSING_STAGED" if not server_hash else
                           "NEW_LOCAL_INPUT" if not local_hash else
                           "MATCH" if server_hash == local_hash else "DIFFERENT"),
            "staged_status": data.get("status") if data else None,
            "staged_conclusion": data.get("conclusion") if data else None,
        })
    missing = [item["path"] for item in files if item["comparison"] == "MISSING_STAGED"]
    if not staging.is_dir():
        return {
            "format": "automx-cim-flow2-staging-comparison-v1",
            "status": "STAGING_MISSING",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "copied-evidence comparison; no SPICE/OpenLane run and no promotion",
            "staging_root": str(staging), "files": files,
            "missing_staged": missing, "staged_integrity_issues": [],
            "staged_holdout_common_mode_outliers": None,
            "staged_holdout_sha256": None,
            "local_holdout_sha256": digest(
                root / "results/sky130/post49_partition_full_tt/holdout/measured.json"),
        }
    stage5 = read_json(staging / "results/receipts/physical/stage5_summary.json") or {}
    stage4 = read_json(staging / "generated/sky130/spice/stage4_manifest.json") or {}
    layout = read_json(staging / "results/receipts/physical/layout.json") or {}
    calibration_path = staging / "results/sky130/post49_partition_full_tt/calibration/measured.json"
    calibration = read_json(calibration_path) or {}
    holdout = read_json(staging / "results/sky130/post49_partition_full_tt/holdout/measured.json") or {}
    integrity = []

    def check(label: str, path: str, expected: str | None) -> None:
        actual = digest(staging / path)
        if not expected or actual != expected:
            integrity.append({"label": label, "path": path,
                              "expected_sha256": expected, "actual_sha256": actual})

    if stage5.get("config_sha256") != stage4.get("config_sha256"):
        integrity.append({"label": "Stage-5/Stage-4 configuration",
                          "reason": "recorded hashes disagree"})
    check("Stage-5 contract", "physical/sky130/macro/macro_contract.json",
          stage5.get("contract_sha256"))
    check("Stage-5 layout generator",
          f"physical/sky130/layout/generate_{CORE}.tcl",
          layout.get("generator_sha256"))
    for view, path in {
        "gds": f"physical/sky130/macro/{CORE}.gds",
        "lef": f"physical/sky130/macro/{CORE}.lef",
        "extracted_spice": f"physical/sky130/macro/{CORE}.pex.spice",
        "spice": f"generated/sky130/spice/macro/{CORE}.spice",
    }.items():
        check(f"Stage-5 {view}", path,
              (stage5.get("views", {}).get(view) or {}).get("sha256"))
    check("2+2 holdout calibration",
          "results/sky130/post49_partition_full_tt/calibration/measured.json",
          holdout.get("calibration_sha256"))
    for filename, expected in stage5.get("receipts", {}).items():
        check(f"Stage-5 receipt {filename}",
              f"results/receipts/physical/{filename}", expected)
    current_config_sha = digest(staging / "configs/sky130_mha_tiny.json")
    historical_config_sha = stage5.get("config_sha256")
    source_drift = ([{"label": "current configuration versus Stage-4/5 historical input",
                      "path": "configs/sky130_mha_tiny.json",
                      "current_sha256": current_config_sha,
                      "measured_sha256": historical_config_sha}]
                    if current_config_sha != historical_config_sha else [])
    current_pex_sha = (stage5.get("views", {}).get("extracted_spice") or {}).get("sha256")
    for name, data in (("2+2 calibration", calibration), ("2+2 holdout", holdout)):
        if data.get("pex_sha256") != current_pex_sha:
            integrity.append({"label": name, "reason": "PEX differs from Stage-5 view"})
        check(f"{name} targeted source",
              "results/sky130/post49_row_partition/adjacent/measured.json",
              data.get("targeted_sha256"))
        for source_name, path in {
            "cell49": "results/sky130/core_candidate_full_tt/measured.json",
            "old_holdout": "results/sky130/post49_holdout_tt/measured.json",
            "calibration": "results/sky130/post49_calibration_tt/measured.json",
        }.items():
            check(f"{name} input {source_name}", path,
                  (data.get("input_report_sha256") or {}).get(source_name))
    for field in ("model_sha256", "ngspice_version", "partition",
                  "load_ff", "pwm_unit_ps"):
        if calibration.get(field) != holdout.get(field):
            integrity.append({"label": "2+2 reports", "reason": f"disagree on {field}"})
    readout = {name: read_json(staging / path) or {}
               for name, path in READOUT_REPORTS.items()}
    lineage = []
    for name, data in readout.items():
        if data.get("pex_sha256") != current_pex_sha:
            lineage.append({"report": name, "reason": "PEX differs from latest Stage-5 core",
                            "report_pex_sha256": data.get("pex_sha256"),
                            "latest_pex_sha256": current_pex_sha})
    links = (
        ("loaded TT calibration", readout["loaded TT"].get("source_calibration_sha256"),
         calibration_path),
        ("loaded TT holdout", readout["loaded TT"].get("source_holdout_sha256"),
         staging / "results/sky130/post49_partition_full_tt/holdout/measured.json"),
        ("idle TT loaded source", readout["idle TT"].get("previous_820ff_report_sha256"),
         staging / READOUT_REPORTS["loaded TT"]),
        ("sample/hold idle source", readout["sample/hold TT"].get("source_report_sha256"),
         staging / READOUT_REPORTS["idle TT"]),
        ("sample/hold edge source", readout["sample/hold edge TT"].get("source_sample_hold_sha256"),
         staging / READOUT_REPORTS["sample/hold TT"]),
    )
    for label, expected, path in links:
        actual = digest(path)
        if expected != actual:
            lineage.append({"report": label, "reason": "source report hash differs",
                            "report_source_sha256": expected, "staged_source_sha256": actual})
    for label, data, expected in (
        ("Stage 5", stage5, "PASS"),
        ("2+2 calibration", calibration, "MEASURED_2P2_LEVEL_SCREEN"),
        ("2+2 holdout", holdout, "MEASURED_2P2_HOLDOUT_TT"),
    ):
        if data.get("status") != expected:
            integrity.append({"label": label, "status": data.get("status"),
                              "expected_status": expected})
    for label, data in (("2+2 calibration", calibration), ("2+2 holdout", holdout)):
        if (not isinstance(data.get("planned_sims"), int) or
                data.get("planned_sims") != data.get("completed_sims") or
                data.get("failures")):
            integrity.append({"label": label, "reason": "incomplete measured jobs"})
    return {
        "format": "automx-cim-flow2-staging-comparison-v1",
        "status": ("STAGED_EVIDENCE_INCOMPLETE" if missing or integrity else
                   "STAGED_HISTORICAL_READOUT" if lineage else
                   "STAGED_EVIDENCE_READY_FOR_REVIEW"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "copied-evidence comparison; no SPICE/OpenLane run and no promotion",
        "staging_root": str(staging), "files": files,
        "missing_staged": missing, "staged_integrity_issues": integrity,
        "historical_source_drift": source_drift,
        "readout_lineage_issues": lineage,
        "staged_holdout_common_mode_outliers": (
            (holdout.get("analysis") or {}).get("common_mode_outside_training_samples")),
        "staged_holdout_sha256": digest(
            staging / "results/sky130/post49_partition_full_tt/holdout/measured.json"),
        "local_holdout_sha256": digest(
            root / "results/sky130/post49_partition_full_tt/holdout/measured.json"),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Flow 2 server evidence staging comparison",
        "",
        f"Status: {report['status']}. The local measured files were not changed.",
        f"Staging directory: {report['staging_root']}",
        "",
        "| Relative path | Staged versus local | Staged status | Staged conclusion |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["files"]:
        lines.append("| " + " | ".join(str(value or "") for value in (
            item["path"], item["comparison"], item["staged_status"],
            item["staged_conclusion"])) + " |")
    lines += ["", "## Internal staged-provenance checks", ""]
    if report["staged_integrity_issues"]:
        for issue in report["staged_integrity_issues"]:
            lines.append("- " + json.dumps(issue, ensure_ascii=False))
    else:
        lines.append("- No checked hash/status mismatch in the staged core and 2+2 reports.")
    lines += ["", "## Historical source and readout lineages", ""]
    for item in report.get("historical_source_drift", []):
        lines.append("- Source drift: " + json.dumps(item, ensure_ascii=False))
    for item in report.get("readout_lineage_issues", []):
        lines.append("- Readout lineage: " + json.dumps(item, ensure_ascii=False))
    if not report.get("historical_source_drift") and not report.get("readout_lineage_issues"):
        lines.append("- No checked source drift or readout lineage mismatch.")
    lines += [
        "",
        f"Staged 2+2 common-mode outliers: {report['staged_holdout_common_mode_outliers']}.",
        "A ready comparison is still diagnostic; review all changes before "
        "using staged data as the new checkout baseline.",
        "",
    ]
    return "\n".join(lines)


def run(root: str | Path, staging: str | Path = DEFAULT_STAGING) -> dict:
    root = Path(root).resolve()
    report = compare(root, staging)
    for relative, content in (
        (RECEIPT, json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
        (REPORT, markdown(report)),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    args = parser.parse_args()
    report = run(args.root, args.staging)
    print(json.dumps({
        "status": report["status"],
        "missing_staged": report["missing_staged"],
        "staged_integrity_issues": report["staged_integrity_issues"],
        "historical_source_drift": report.get("historical_source_drift", []),
        "readout_lineage_issues": report.get("readout_lineage_issues", []),
        "report": str(REPORT),
    }, indent=2))
