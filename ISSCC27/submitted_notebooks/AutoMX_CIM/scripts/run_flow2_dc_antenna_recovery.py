#!/usr/bin/env python3
"""Resume verified core evidence; recover ADC DC and low-layer antenna routing.

One history, summary and downloadable folder. Native EDA runs only with
--run on the server. Prior complete physical/SPICE steps remain reusable.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_readout_closure as closure

common, core, adc, fanout = closure.common, closure.core, closure.adc, closure.fanout


def run(root, *, source_tag="dc_antenna_20261018_01", tag="dc_antenna_20261018_02",
        pdk_root=closure.acquisition.DEFAULT_PDK, openlane_source=fanout.notebook.DEFAULT_SOURCE,
        openlane_pdk=fanout.notebook.DEFAULT_PDK, execute=False, timeout_s=900,
        openlane_timeout_s=7200, include_fanout=True, startup_guards=False, progress_profile=False):
    root = Path(root).resolve()
    for name in (tag, source_tag):
        common.tag_ok(name)
    if tag == source_tag or len(tag) > 56 or timeout_s <= 0 or openlane_timeout_s <= 0:
        raise ValueError("distinct safe tags and positive timeouts required")
    if progress_profile and not startup_guards:
        raise ValueError("progress campaign requires observable startup and endpoint guards")
    report = {"format": "automx-cim-dc-antenna-recovery-v1", "tag": tag, "source_tag": source_tag,
        "status": "PREPARED", "branches": {}, "maximum_new_spice_jobs": 5,
        "planned_jobs": {"core": "reanalyze/reuse six completed TT jobs; no new stimulus",
            "ADC": "one TT modeled-resistor DC smoke plus two input-load and two conversion transients",
            "fanout_antenna": "fresh met2 global guides with met1 pin access in detailed routing" if include_fanout else "not requested"},
        "remaining_gates": {"full_readout": "PENDING_CONDITIONING_MUX_REFERENCE_DECODER_HANDSHAKE",
            "accuracy_holdout_noise_PVT": "PENDING_NEW_COMPLETE_READOUT_OPERATING_POINT",
            "wrapper_LIB_SPEF_STA": "PENDING", "stage6_v2": "PENDING", "stage8_macro_bound": "PENDING"},
        "not_signoff": "equivalent zero-free-charge capacitor network and isolated ADC/physical-core prototypes; no complete readout, ADC transfer/noise/PVT or full wrapper claim"}
    if startup_guards:
        report["planned_jobs"]["ADC"] = "one referenced native-model smoke, two observable startup loads, two startup conversions"
        if include_fanout:
            report["planned_jobs"]["fanout_antenna"] = "met1 global profile, five measured endpoint guards before/after fanout repair, <=3 logic sinks and bounded diode repair"
    if progress_profile:
        report["planned_jobs"]["ADC"] = "referenced native-model smoke, two fast-ramp loads and two conversions; intermediate raw checkpoints without restarting the solver"
        report["progress_profile"] = adc.progress.PROFILE
    if not execute:
        return report
    previous_path = root/common.BASE/source_tag/"summary.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    source_tags = previous.get("child_tags")
    if not source_tags or not all(k in source_tags for k in ("acquisition", "core", "adc_drc")):
        raise ValueError("source campaign must record its actual reused child_tags")
    for name in source_tags.values():
        common.tag_ok(name)
    tags = {k: source_tags[k] for k in ("acquisition", "core", "adc_drc")}
    tags.update(adc=tag+"_adc", fanout=tag+"_fanout")
    report["child_tags"] = tags
    store = common.Store(root, tag, {"source_tag": source_tag, "source_tags": source_tags,
        "mode": ("FAST_STARTUP_PARTIAL_RAW_FIVE_GUARDS_V4" if progress_profile else
                 "ZERO_SUPPLY_STARTUP_MEASURED_ANTENNA_GUARDS_V3" if startup_guards else
                 "NATIVE_DW_BRACED_MET2_GUIDES_MET1_PIN_ACCESS_V2"), "native_pdk": str(pdk_root),
        "openlane_source": str(openlane_source), "openlane_pdk": str(openlane_pdk),
        "include_fanout": include_fanout})
    items = []

    def branch(name, operation):
        store.note("BRANCH_START "+name)
        try:
            with (store.folder/"history.log").open("a", encoding="utf-8") as history:
                with redirect_stdout(closure._Tee(sys.stdout, history)):
                    result = operation()
        except Exception as error:
            result = {"status": "BLOCKED_BRANCH", "error": f"{type(error).__name__}: {error}"}
        report["branches"][name] = result
        store.note(f"BRANCH_END {name}: {result['status']}")
        common.save_summary(store.folder/"summary.json", report)
        return result

    try:
        store.note("SESSION_START; preserve old EDA; reanalyze matching raw; new ADC and routing profiles")
        front = branch("acquisition", lambda: core.recovery.verify_physical_source(root, tags["acquisition"])["report"])
        if front["status"] == "BANKED_ACQUISITION_PHYSICAL_PROTOTYPE":
            branch("core", lambda: core.run(root, pdk_root=pdk_root, tag=tags["core"],
                source_tag=tags["acquisition"], recipe=core.BANKED_RECIPE, waveform=True,
                execute=True, timeout_s=timeout_s))
        else:
            report["branches"]["core"] = {"status": "BLOCKED_FRONT_EVIDENCE", "completed_sims": 0}
        branch("adc_drc", lambda: closure.adc_physical.run(root, pdk_root=pdk_root,
            tag=tags["adc_drc"], execute=True, timeout_s=timeout_s))
        # Resolve the small independent physical branch first, so a slow ADC
        # cannot keep its final routing/antenna result hidden until timeout.
        if include_fanout:
            def route():
                existing = (root/"build/flow2_core_bound_fanout"/tags["fanout"]/"inputs.json").is_file()
                routing = {"guarded_routes": True} if startup_guards else {"met2_routes": True}
                return fanout.run(root, tag=tags["fanout"], source=Path(openlane_source),
                    pdk_root=Path(openlane_pdk), execute=not existing, audit_existing=existing,
                    timeout_s=openlane_timeout_s, **routing)
            branch("fanout", route)
        def analog():
            extra = {}
            if startup_guards:
                prior_adc = previous["branches"]["adc"]
                prior_model = common._verified(root, prior_adc["derived_native_model"])
                prior_log = common._verified(root, prior_adc["pdk_model_smoke"]["log"])
                reference = adc.dc.analyze_model(prior_log.read_text())
                extra = {"powerup": True, "model_reference": {
                    "model_sha256": common._sha(prior_model), "smoke": reference}}
                if progress_profile:
                    extra["progress_profile"] = True
            return adc.run(root, pdk_root=pdk_root, tag=tags["adc"], execute=True,
                timeout_s=timeout_s, conversions=True, dc_recovery=True, **extra)
        branch("adc", analog)
        r = report["branches"]
        report["completed_core_jobs_reused_or_reanalyzed"] = r["core"].get("completed_sims", 0)
        report["completed_ADC_transients"] = r["adc"].get("completed_sims", 0)
        report["ADC_model_smoke"] = r["adc"].get("pdk_model_smoke", {}).get("status", "NOT_COMPLETED")
        adc_ok = (r["adc"]["status"] == "MEASURED_ADC_WAVEFORM_PROTOTYPE"
            and r["adc"].get("conversion_gate") == "TWO_DIFFERENTIAL_CODES_WITH_FRESH_COMPLETION_NOT_FULL_TRANSFER"
            and r["adc"].get("active_input_load_gate") == "ON_COMMAND_OBSERVED")
        success = (r["core"]["status"] == "MEASURED_CORE_ACQUISITION_PROTOTYPE" and adc_ok
            and r["adc_drc"]["status"] == "ADC_NATIVE_GDS_DRC_PASS_ONLY"
            and (not include_fanout or r["fanout"]["status"] == "CORE_BOUND_FANOUT_PHYSICAL_PASS"))
        report["status"] = "MEASURED_DC_ANTENNA_PROTOTYPES_NOT_WRAPPER_SIGNOFF" if success else "COMPLETED_WITH_BLOCKERS"
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        store.note("SESSION_INTERRUPTED; completed checkpoints remain reusable")
        raise
    finally:
        for name, child in tags.items():
            for base in (common.BASE, common.BUILD, common.PHYSICAL, closure.acquisition.acq.BASE,
                         closure.acquisition.BUILD, closure.acquisition.PHYSICAL):
                items.extend(closure._files(root, base/child))
            if name == "fanout" and include_fanout:
                items.extend(closure._files(root, Path("build/flow2_core_bound_fanout")/child))
                items.extend(closure._files(root, fanout.core.DESIGN/"runs"/child))
        for result in report["branches"].values():
            sources = result.get("sources", [])
            if isinstance(sources, list):
                items.extend(sources)
        for name in ("setup.json", "setup.log"):
            p = root/"build/tools/ngspice-44.2"/name
            if p.is_file():
                items.append(core.acq._item(root, p))
        for relative in adc.original.adc.FILES.values():
            p = root/relative
            if p.is_file():
                items.append(core.acq._item(root, p))
        store.note("SESSION_END "+report["status"])
        common.save_summary(store.folder/"summary.json", report)
        output = common.bundle(root, tag, items)
        print(f"Download folder: {output.parent}", flush=True)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--source-tag", default="dc_antenna_20261018_01")
    p.add_argument("--tag", default="dc_antenna_20261018_02")
    p.add_argument("--pdk-root", type=Path, default=closure.acquisition.DEFAULT_PDK)
    p.add_argument("--openlane-source", type=Path, default=fanout.notebook.DEFAULT_SOURCE)
    p.add_argument("--openlane-pdk", type=Path, default=fanout.notebook.DEFAULT_PDK)
    p.add_argument("--timeout-s", type=int, default=900)
    p.add_argument("--openlane-timeout-s", type=int, default=7200)
    p.add_argument("--skip-fanout", action="store_true")
    p.add_argument("--run", action="store_true")
    a = p.parse_args()
    r = run(a.root, source_tag=a.source_tag, tag=a.tag, pdk_root=a.pdk_root,
        openlane_source=a.openlane_source, openlane_pdk=a.openlane_pdk, execute=a.run,
        timeout_s=a.timeout_s, openlane_timeout_s=a.openlane_timeout_s, include_fanout=not a.skip_fanout)
    print(json.dumps(r, indent=2))
    if a.run and r["status"] != "MEASURED_DC_ANTENNA_PROTOTYPES_NOT_WRAPPER_SIGNOFF":
        raise SystemExit(1)
