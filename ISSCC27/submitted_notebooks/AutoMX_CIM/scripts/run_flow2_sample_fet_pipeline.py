#!/usr/bin/env python3
"""Run sampler-leaf layout/LVS and export every produced artifact in one call."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import export_flow2_server_results as exporter  # noqa: E402
from scripts import run_flow2_sample_switch_fet_leaves as layout  # noqa: E402
from scripts import run_flow2_sample_switch_fet_lvs as lvs  # noqa: E402


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "sample_fet_20261017_03", execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    report: dict = {"format": "automx-cim-flow2-sample-fet-pipeline-v1",
                    "status": "READY_TO_RUN", "tag": tag,
                    "layout_status": None, "lvs_status": None,
                    "export_status": None,
                    "not_signoff": "isolated FET DRC/LVS only; connected TG, control driver, ADC and wrapper remain"}
    if not execute:
        ready = layout.run(root, pdk_root=pdk_root, tag=tag,
                           execute=False, timeout_s=timeout_s)
        report["layout_status"] = ready["status"]
        report["status"] = ("READY_TO_RUN" if ready["status"] == "READY_TO_RUN"
                            else "BLOCKED_PREREQUISITES")
        return report
    try:
        observed = layout.run(root, pdk_root=pdk_root, tag=tag,
                              execute=True, timeout_s=timeout_s)
        report["layout_status"] = observed["status"]
        if observed["status"] == "DRC_PASS_SAMPLE_FET_LEAVES_ONLY":
            checked = lvs.run(root, pdk_root=pdk_root, tag=tag,
                              execute=True, timeout_s=timeout_s)
            report["lvs_status"] = checked["status"]
            report["status"] = ("LEAF_DRC_LVS_PASS_PROTOTYPE_ONLY" if
                                checked["status"] == "LVS_PASS_SAMPLE_FET_LEAVES_ONLY"
                                else "BLOCKED_LEAF_LVS")
        else:
            report["status"] = "BLOCKED_LEAF_LAYOUT"
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        report["error"] = "KeyboardInterrupt"
    except Exception as error:
        report["status"] = "FAILED"
        report["error"] = f"{type(error).__name__}: {error}"
    # Export is unconditional: a blocked or interrupted run still has useful
    # Magic/Netgen logs and partial build files to inspect off-server.
    try:
        copied = exporter.export(root, tag=tag, include_measured_cap=True)
        report["export_status"] = copied["status"]
        report["exported_file_count"] = copied["file_count"]
        report["export_manifest"] = (
            f"server_results/flow2_sample_fet_{tag}_export.json")
    except Exception as error:
        report["export_status"] = "FAILED"
        report["export_error"] = f"{type(error).__name__}: {error}"
        report["status"] = "EXPORT_FAILED"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default="sample_fet_20261017_03")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    result = run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                 execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if args.run and result["status"] != "LEAF_DRC_LVS_PASS_PROTOTYPE_ONLY":
        raise SystemExit(1)
