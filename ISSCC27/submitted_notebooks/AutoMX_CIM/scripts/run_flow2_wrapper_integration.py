#!/usr/bin/env python3
"""Run core/acquisition physical integration and ADC input probing independently."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_core_acquisition as core
from scripts import run_flow2_adc_input_load as adc
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK


class _Tee:
    def __init__(self, console, history):
        self.console, self.history = console, history

    def write(self, value):
        self.console.write(value)
        self.history.write(value)
        return len(value)

    def flush(self):
        self.console.flush()
        self.history.flush()


def run(root: Path, *, pdk_root: Path = DEFAULT_PDK, tag="wrapper_integration_20261018_01",
        source_tag="physical_next_20261018_03_acq", execute=False, timeout_s=900,
        recover=False) -> dict:
    root = Path(root).resolve()
    common.tag_ok(tag)
    if len(tag) > 59:
        raise ValueError("campaign tag must leave room for child suffixes")
    if recover:
        from scripts import run_flow2_adc_input_recovery as adc_module
    else:
        adc_module = adc
    branches = (("core_acquisition", core, tag + "_core"), ("adc_input", adc_module, tag + "_adc"))
    report = {"format": "automx-cim-flow2-wrapper-integration-campaign-v1", "tag": tag,
              "status": "PREPARED", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "variant": "SHIELDED_CORE_AND_EXACT_R_ADC_RECOVERY" if recover else "ORIGINAL_INTEGRATION",
              "planned_spice_jobs_maximum": 8, "branches": {},
              "not_signoff": "prototype integration campaign; no complete sense/ADC clocked wrapper, LIB/SPEF/STA or Stage-6 v2/Stage-8 macro-bound pass is implied"}
    folder = root / common.BASE / tag
    source_items = []
    if execute:
        folder.mkdir(parents=True, exist_ok=True)
    def note(message):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        print(line, flush=True)
        if execute:
            with (folder / "history.log").open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
    try:
        note("SESSION_START core/acquisition physical branch + complete ADC RC input branch")
        for name, module, child_tag in branches:
            note(f"BRANCH_START {name}: {child_tag}")
            arguments = {"pdk_root": pdk_root, "tag": child_tag, "execute": execute, "timeout_s": timeout_s}
            if name == "core_acquisition":
                arguments["source_tag"] = source_tag
                if recover:
                    arguments["recipe"] = core.SHIELDED_RECIPE
            try:
                # Keep native phase progress in the same campaign history as
                # the branch events, while still showing it on the console.
                if execute:
                    with (folder / "history.log").open("a", encoding="utf-8") as history:
                        with redirect_stdout(_Tee(sys.stdout, history)):
                            result = module.run(root, **arguments)
                else:
                    result = module.run(root, **arguments)
            except Exception as error:
                result = {"status": "BLOCKED_BRANCH", "error": f"{type(error).__name__}: {error}", "tag": child_tag}
            report["branches"][name] = result
            if execute:
                for base in (common.BASE, common.BUILD, common.PHYSICAL):
                    source_items.extend(core.acq._item(root, p) for p in (root / base / child_tag).rglob("*") if p.is_file())
                # Preserve both imported physical views/proofs and the pinned ADC sources.
                source_items.extend(result.get("sources", []))
                if result.get("source_rc_spice"):
                    source_items.extend(core.acq._item(root, root / p) for p in adc.adc.FILES.values() if (root / p).is_file())
                common.save_summary(folder / "summary.json", report)
            note(f"BRANCH_END {name}: {result['status']}")
        if execute:
            expected_adc = ("MEASURED_ADC_EQUIVALENT_R_INPUT_CHARGE_DIAGNOSTIC" if recover
                            else "MEASURED_ADC_INPUT_CHARGE_DIAGNOSTIC")
            success = (report["branches"]["core_acquisition"]["status"] == "MEASURED_CORE_ACQUISITION_PROTOTYPE"
                       and report["branches"]["adc_input"]["status"] == expected_adc)
            report["status"] = "MEASURED_INTEGRATION_PILOT_NOT_SIGNOFF" if success else "PARTIAL_INTEGRATION_PILOT"
            report["completed_spice_jobs"] = sum(r.get("completed_sims", 0) for r in report["branches"].values())
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        note("SESSION_INTERRUPTED; completed tool stages remain checkpointed")
        raise
    finally:
        if execute:
            # Also include a child interrupted before module.run could return.
            # Its own finally block has already saved partial logs/summary.
            for _, _, child_tag in branches:
                for base in (common.BASE, common.BUILD, common.PHYSICAL):
                    source_items.extend(core.acq._item(root, p) for p in (root / base / child_tag).rglob("*") if p.is_file())
            note(f"SESSION_END {report['status']}")
            common.save_summary(folder / "summary.json", report)
            archive = common.bundle(root, tag, source_items)
            print(f"Download folder: {archive.parent}", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK)
    parser.add_argument("--tag", default="wrapper_integration_20261018_01")
    parser.add_argument("--source-tag", default="physical_next_20261018_03_acq")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--recover", action="store_true", help="new tag: ground shield plus exact ADC resistor reduction and live logs")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    output = run(args.root, pdk_root=args.pdk_root, tag=args.tag, source_tag=args.source_tag,
                 execute=args.run, timeout_s=args.timeout_s, recover=args.recover)
    print(json.dumps(output, indent=2))
    if args.run and output["status"] != "MEASURED_INTEGRATION_PILOT_NOT_SIGNOFF":
        raise SystemExit(1)
