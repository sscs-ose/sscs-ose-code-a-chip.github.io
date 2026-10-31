#!/usr/bin/env python3
"""Run acquisition physical checks and the independent core-bound fanout flow.

One append-only campaign history and one summary link all per-stage artifacts.
Both branches export automatically, including failure logs. No wrapper or
Stage-6/8 signoff is inferred from these prototype checks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_acquisition_layout as acquisition
from scripts import run_flow2_core_bound_fanout as fanout
from scripts.collect_flow2_physical_diagnostics import collect
from scripts.run_flow2_remaining_measurements import _save

DEFAULT_PDK = Path("/home/nam/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A")


def run(root: Path, *, tag: str = "physical_next_20261018_01", pdk_root: Path = DEFAULT_PDK,
        openlane_pdk: Path = fanout.notebook.DEFAULT_PDK,
        openlane_source: Path = fanout.notebook.DEFAULT_SOURCE,
        execute: bool = False, skip_fanout: bool = False, timeout_s: int = 900,
        openlane_timeout_s: int = 7200) -> dict:
    root = root.resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", tag) or timeout_s <= 0 or openlane_timeout_s <= 0:
        raise ValueError("safe campaign tag and positive timeouts required")
    folder = root / "results/sky130/flow2_physical_next" / tag
    destination = root / "server_results/results/sky130/flow2_physical_next" / tag
    report = {"format": "automx-cim-flow2-physical-next-v1", "tag": tag,
              "status": "PREPARATION_ONLY", "branches": {},
              "wrapper_gate": "PENDING_CORE_ADC_REFERENCES_DECODER_LIB_SPEF_STA",
              "stage6_v2_gate": "PENDING_MEASURED_COMPLETE_READOUT_AND_FRESH_MHA_HOLDOUT"}
    if execute:
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / "summary.json").is_file():
            raise FileExistsError("campaign summary already exists; inspect it and use a new campaign tag")

    def note(message):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        print(line, flush=True)
        if execute:
            with (folder / "history.log").open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")

    jobs = [("acquisition", lambda: acquisition.run(root, pdk_root=pdk_root,
                tag=tag + "_acq", execute=execute, timeout_s=timeout_s))]
    if not skip_fanout:
        jobs.append(("core_bound_fanout", lambda: fanout.run(root, tag=tag + "_fanout",
                source=openlane_source, pdk_root=openlane_pdk, execute=execute,
                timeout_s=openlane_timeout_s)))
    try:
        for name, operation in jobs:
            note(f"START {name}")
            try:
                result = operation()
            except Exception as error:
                result = {"status": "FAILED", "error": f"{type(error).__name__}: {error}"}
            report["branches"][name] = result
            note(f"END {name}: {result['status']}")
            if execute:
                _save(folder / "summary.json", report)
        if execute:
            report["status"] = ("MEASURED_NEXT_PHYSICAL_PROTOTYPES" if
                report["branches"]["acquisition"]["status"] == "ACQUISITION_DRC_LVS_RC_PEX_MEASURED_PROTOTYPE"
                and (skip_fanout or report["branches"]["core_bound_fanout"]["status"] == "CORE_BOUND_FANOUT_PHYSICAL_PASS")
                else "COMPLETED_WITH_BLOCKERS")
        note(f"CAMPAIGN {report['status']}")
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        note("INTERRUPTED; partial build/log artifacts are retained")
        raise
    finally:
        if execute:
            _save(folder / "summary.json", report)
            destination.mkdir(parents=True, exist_ok=True)
            for file in folder.iterdir():
                if file.is_file():
                    shutil.copy2(file, destination / file.name)
            try:
                diagnostics = collect(root, tag=tag)
                print(f"Diagnostics ZIP: {diagnostics['archive']['path']}", flush=True)
            except Exception as error:
                # A transfer failure must not hide the measured branch statuses.
                _save(destination / "diagnostics_export_error.json", {
                    "status": "EXPORT_FAILED", "error": f"{type(error).__name__}: {error}"})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", default="physical_next_20261018_01")
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK)
    parser.add_argument("--openlane-pdk", type=Path, default=fanout.notebook.DEFAULT_PDK)
    parser.add_argument("--openlane-source", type=Path, default=fanout.notebook.DEFAULT_SOURCE)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--skip-fanout", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--openlane-timeout-s", type=int, default=7200)
    args = parser.parse_args()
    result = run(args.root, tag=args.tag, pdk_root=args.pdk_root,
                 openlane_pdk=args.openlane_pdk, openlane_source=args.openlane_source,
                 execute=args.run, skip_fanout=args.skip_fanout,
                 timeout_s=args.timeout_s, openlane_timeout_s=args.openlane_timeout_s)
    print(json.dumps(result, indent=2))
    if args.run and result["status"] != "MEASURED_NEXT_PHYSICAL_PROTOTYPES":
        raise SystemExit(1)
