#!/usr/bin/env python3
"""Run banked acquisition/core, nonloading full-ADC probes and fanout repair.

One history/summary/download folder; successful stages reuse their frozen
evidence. Independent branches continue after failure. This campaign does
not relabel the intermediate prototype as a complete mixed-signal wrapper.
"""
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
from scripts import run_flow2_banked_acquisition as acquisition
from scripts import run_flow2_core_acquisition as core
from scripts import run_flow2_adc_waveform as adc
from scripts import run_flow2_adc_native_drc as adc_physical
from scripts import run_flow2_core_bound_fanout as fanout
from scripts.run_flow2_wrapper_integration import _Tee


def _files(root, relative):
    base = root/relative
    for p in base.rglob("*"):
        if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root):
            yield core.acq._item(root, p)


def run(root, *, pdk_root=acquisition.DEFAULT_PDK, tag="readout_closure_20261018_01",
        openlane_source=fanout.notebook.DEFAULT_SOURCE, openlane_pdk=fanout.notebook.DEFAULT_PDK,
        execute=False, timeout_s=900, openlane_timeout_s=7200, include_fanout=True, conversions=True,
        reuse_tag=None):
    root = Path(root).resolve()
    common.tag_ok(tag)
    if len(tag) > 56 or timeout_s <= 0 or openlane_timeout_s <= 0:
        raise ValueError("positive timeouts and a tag with room for child suffixes required")
    if reuse_tag is not None:
        common.tag_ok(reuse_tag)
        if len(reuse_tag) > 56 or reuse_tag == tag:
            raise ValueError("reuse tag must differ from the new campaign tag")
    report = {"format": "automx-cim-flow2-readout-closure-v1", "tag": tag, "status": "PREPARED",
        "planned_spice_jobs_maximum": 10 if conversions else 8, "branches": {},
        "jobs": {"banked_physical": "Magic/KLayout DRC, transistor LVS and RC PEX",
            "banked_core": "six schematic/PEX TT jobs, with stage waveforms",
            "adc": "two full-active input-load probes and two real conversion probes" if conversions else "two full-active ADC input-load probes",
            "adc_drc": "Magic/KLayout on the published ADC GDS using the native integration PDK",
            "fanout": "fresh core-bound OpenLane repair/audit" if include_fanout else "not requested"},
        "remaining_gates": {"complete_readout": "PENDING_ADC_CONDITIONING_REFERENCES_MUX_DECODER_AND_HANDSHAKE",
            "operating_point": "NOT_FROZEN_FOR_COMPLETE_READOUT", "fresh_mha_offset_noise_pvt": "PENDING_COMPLETE_SIGNAL_PATH",
            "wrapper_LIB_SPEF_STA": "PENDING_COMPLETE_PHYSICAL_WRAPPER", "stage6_v2_signoff": "PENDING",
            "stage8_macro_bound_mixed_signal": "PENDING_WRAPPER_GATES"},
        "not_signoff": "intermediate physical/ADC execution closure; new EDA/accuracy outcomes must be read from their receipts; no complete wrapper or system pass is inferred"}
    if not execute:
        return report
    identity = {"mode": "BANKED_READOUT_NONLOADING_ADC_V1", "native_pdk": str(pdk_root),
        "openlane_source": str(openlane_source), "openlane_pdk": str(openlane_pdk),
        "include_fanout": include_fanout, "conversions": conversions}
    if reuse_tag:
        identity["reuse_physical_and_core_tag"] = reuse_tag
    store = common.Store(root, tag, identity)
    child_tags = {"acquisition": tag+"_front", "core": tag+"_core", "adc": tag+"_adc", "adc_drc": tag+"_adcdrc", "fanout": tag+"_fanout"}
    if reuse_tag:
        child_tags.update({name: reuse_tag+suffix for name, suffix in
                          (("acquisition", "_front"), ("core", "_core"), ("adc_drc", "_adcdrc"))})
    report["child_tags"] = child_tags
    source_items = []
    def branch(name, operation):
        store.note(f"BRANCH_START {name}")
        try:
            with (store.folder/"history.log").open("a", encoding="utf-8") as history:
                with redirect_stdout(_Tee(sys.stdout, history)):
                    result = operation()
        except Exception as error:
            result = {"status": "BLOCKED_BRANCH", "error": f"{type(error).__name__}: {error}"}
        report["branches"][name] = result
        store.note(f"BRANCH_END {name}: {result['status']}")
        common.save_summary(store.folder/"summary.json", report)
        return result
    try:
        store.note("SESSION_START new banked routing, core waveforms, full ADC and independent fanout")
        def acquire():
            if reuse_tag:
                # Verify the existing leaves/DRC/LVS/PEX without rewriting the
                # source receipt that is frozen in the old core checkpoints.
                return core.recovery.verify_physical_source(root, child_tags["acquisition"])["report"]
            return acquisition.run(root, pdk_root=pdk_root,
                tag=child_tags["acquisition"], execute=True, timeout_s=timeout_s)
        front = branch("acquisition", acquire)
        if front["status"] == "BANKED_ACQUISITION_PHYSICAL_PROTOTYPE":
            branch("core", lambda: core.run(root, pdk_root=pdk_root, tag=child_tags["core"],
                source_tag=child_tags["acquisition"], recipe=core.BANKED_RECIPE, waveform=True,
                execute=True, timeout_s=timeout_s))
        else:
            report["branches"]["core"] = {"status": "SKIPPED_FRONT_PHYSICAL_GATE", "completed_sims": 0}
        branch("adc_drc", lambda: adc_physical.run(root, pdk_root=pdk_root,
            tag=child_tags["adc_drc"], execute=True, timeout_s=timeout_s))
        branch("adc", lambda: adc.run(root, pdk_root=pdk_root, tag=child_tags["adc"],
            execute=True, timeout_s=timeout_s, conversions=conversions))
        if include_fanout:
            def run_fanout():
                # A retry audits an already created run. It never overwrites
                # routed artifacts or starts a duplicate flow under that tag.
                build = root/"build/flow2_core_bound_fanout"/child_tags["fanout"]
                existing = (build/"inputs.json").is_file()
                return fanout.run(root, tag=child_tags["fanout"], source=Path(openlane_source),
                    pdk_root=Path(openlane_pdk), execute=not existing, audit_existing=existing,
                    timeout_s=openlane_timeout_s)
            branch("fanout", run_fanout)
        report["completed_spice_jobs"] = sum(j.get("completed_sims", 0) for j in report["branches"].values())
        success = (report["branches"]["core"]["status"] == "MEASURED_CORE_ACQUISITION_PROTOTYPE"
            and report["branches"]["adc"]["status"] == "MEASURED_ADC_WAVEFORM_PROTOTYPE"
            and report["branches"]["adc_drc"]["status"] == "ADC_NATIVE_GDS_DRC_PASS_ONLY"
            and (not include_fanout or report["branches"]["fanout"]["status"] == "CORE_BOUND_FANOUT_PHYSICAL_PASS"))
        report["status"] = "MEASURED_CLOSURE_PROTOTYPES_NOT_WRAPPER_SIGNOFF" if success else "COMPLETED_WITH_BLOCKERS"
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        store.note("SESSION_INTERRUPTED; successful native/ADC stages remain checkpointed")
        raise
    finally:
        for name in ("setup.log", "setup.json"):
            runtime_proof = root/"build/tools/ngspice-44.2"/name
            if runtime_proof.is_file():
                source_items.append(core.acq._item(root, runtime_proof))
        for name, child in child_tags.items():
            for base in (common.BASE, common.BUILD, common.PHYSICAL, acquisition.acq.BASE,
                         acquisition.BUILD, acquisition.PHYSICAL):
                source_items.extend(_files(root, base/child))
            if name == "fanout" and include_fanout:
                source_items.extend(_files(root, Path("build/flow2_core_bound_fanout")/child))
                source_items.extend(_files(root, fanout.core.DESIGN/"runs"/child))
        for name, result in report["branches"].items():
            source_items.extend(result.get("sources", []) if name != "acquisition" else [])
        if any((root/v).is_file() for v in adc.original.adc.FILES.values()):
            source_items.extend(core.acq._item(root, root/v) for v in adc.original.adc.FILES.values() if (root/v).is_file())
        store.note(f"SESSION_END {report['status']}")
        common.save_summary(store.folder/"summary.json", report)
        archive = common.bundle(root, tag, source_items)
        print(f"Download folder: {archive.parent}", flush=True)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--pdk-root", type=Path, default=acquisition.DEFAULT_PDK)
    p.add_argument("--tag", default="readout_closure_20261018_01")
    p.add_argument("--reuse-tag", help="reuse this campaign's front/core/ADC DRC; new ADC and fanout tags")
    p.add_argument("--openlane-source", type=Path, default=fanout.notebook.DEFAULT_SOURCE)
    p.add_argument("--openlane-pdk", type=Path, default=fanout.notebook.DEFAULT_PDK)
    p.add_argument("--run", action="store_true")
    p.add_argument("--skip-fanout", action="store_true")
    p.add_argument("--load-only", action="store_true")
    p.add_argument("--timeout-s", type=int, default=900)
    p.add_argument("--openlane-timeout-s", type=int, default=7200)
    a = p.parse_args()
    result = run(a.root, pdk_root=a.pdk_root, tag=a.tag, openlane_source=a.openlane_source,
        openlane_pdk=a.openlane_pdk, execute=a.run, timeout_s=a.timeout_s,
        openlane_timeout_s=a.openlane_timeout_s, include_fanout=not a.skip_fanout, conversions=not a.load_only,
        reuse_tag=a.reuse_tag)
    print(json.dumps(result, indent=2))
    if a.run and result["status"] != "MEASURED_CLOSURE_PROTOTYPES_NOT_WRAPPER_SIGNOFF":
        raise SystemExit(1)
