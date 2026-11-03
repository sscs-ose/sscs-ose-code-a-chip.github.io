#!/usr/bin/env python3
"""Recover the ADC load probe with exact passive-node reduction and live logs.

All 34,187 MOS, 115 MIM and 14,054 explicit capacitors remain in the solver.
Only unobserved, memoryless resistor junctions are eliminated. The original
IP and the old timeout receipt are read only; no measured values are reused
as a new simulation result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_adc_input_load as original
from scripts import reduce_flow2_adc_resistors as reducer
from scripts import flow2_live_spice as live
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK


def run(root: Path, *, pdk_root: Path = DEFAULT_PDK, tag="adc_input_recovery_20261018_01",
        execute=False, timeout_s=900) -> dict:
    root, pdk = Path(root).resolve(), Path(pdk_root).expanduser().resolve()
    common.tag_ok(tag)
    if timeout_s <= 0:
        raise ValueError("positive timeout required")
    report = {"format": "automx-cim-flow2-adc-equivalent-r-input-recovery-v1", "tag": tag,
              "status": "PREPARED", "planned_sims": 2, "completed_sims": 0, "jobs": [],
              "not_signoff": "full active ADC with an exactly reduced passive R network; ideal external VCM/supplies/controls; input-charge diagnostic only, conversion, full PVT/noise, physical ADC adapter and wrapper views remain pending"}
    store, items = None, []
    try:
        paths = {k: root / relative for k, relative in original.adc.FILES.items()}
        if any(not path.is_file() or common._sha(path) != original.adc.EXPECTED_SHA256[k] for k, path in paths.items()):
            raise ValueError("the pinned ADC source files are missing or changed")
        rc = paths["rc_spice"]
        items = [original.acq._item(root, p) for p in paths.values()]
        model = pdk / "libs.tech/ngspice/sky130.lib.spice"
        tool = original.acq.stage5._find_tool("ngspice")
        if not tool or not model.is_file():
            raise ValueError("ngspice and the native SKY130 model library are required")
        pins = original.adc._spice_pins(rc)
        probes = original.input_switches(rc)
        # Preserve the pinned source's CRLF bytes; read_text() normalizes them
        # and would invalidate the provenance/preserved-card fingerprint.
        text, reduction = reducer.reduce_text(rc.read_bytes().decode("utf-8"))
        if reduction["source_sha256"] != original.adc.EXPECTED_SHA256["rc_spice"]:
            raise ValueError("unexpected ADC line-ending/encoding change")
        report["reduction"] = reduction
        report["source_rc_spice"] = original.acq._item(root, rc)
        report["full_netlist_counts"] = probes["full_netlist_counts"]
        report["input_switches"] = probes["input_switches"]
        identity = {"inputs": items, "model": common._sha(model),
                    "ngspice": original.acq.stage5._tool_version("ngspice", tool),
                    "equivalent_rc_sha256": reduction["equivalent_sha256"]}
        report["model_sha256"] = identity["model"]
        report["analysis_runner_sha256"] = common._sha(Path(__file__))
        if not execute:
            return report
        store = common.Store(root, tag, identity)
        derived = store.build / "adc_top.equivalent_r.spice"
        if derived.is_file() and common._sha(derived) != reduction["equivalent_sha256"]:
            raise FileExistsError("equivalent R netlist changed; use a fresh tag")
        if not derived.is_file():
            derived.write_bytes(text.encode("utf-8"))
        if original.adc._spice_pins(derived) != pins:
            raise ValueError("ADC top port order changed during resistor reduction")
        derived_probes = original.input_switches(derived)
        if derived_probes["input_switches"] != probes["input_switches"]:
            raise ValueError("input sampler devices/probe nodes changed during reduction")
        for key in ("mos", "mim", "capacitors"):
            if derived_probes["full_netlist_counts"][key] != probes["full_netlist_counts"][key]:
                raise ValueError(f"ADC {key} count changed")
        report["equivalent_rc_spice"] = original.acq._item(root, derived)
        report["equivalent_netlist_counts"] = derived_probes["full_netlist_counts"]
        common._save(store.folder / "resistor_reduction.json", reduction)
        store.note(f"Exact passive R reduction: {probes['full_netlist_counts']['resistors']} -> "
                   f"{derived_probes['full_netlist_counts']['resistors']} R; all MOS/MIM/C retained")
        for cm, name in ((.9, "tt_cm0900"), (1.62, "tt_cm1620")):
            content = original.deck(model, derived, pins, probes, cm)
            # The actual simulator deck is part of the checkpoint, so a later
            # parser-only repair can reuse these exact logs without SPICE reruns.
            command = [tool, "-b", "adc.spice"]
            def simulate(work, deck=content):
                (work / "adc.spice").write_text(deck, encoding="utf-8")
                return live.run(command, work, timeout_s)
            result, work = store.step(name, command, tcl=content, executor=simulate)
            entry = {"case": name, "returncode": result.returncode,
                     "live_log": original.acq._item(root, work / "ngspice.live.log"),
                     "process_observations": original.acq._item(root, work / "process.jsonl")}
            report["jobs"].append(entry)
            if result.returncode:
                raise RuntimeError(f"ADC equivalent-R probe exited {result.returncode}: {name}; inspect direct log and process observations")
            entry.update(original.analyze(result.stdout + result.stderr, cm, probes))
            report["completed_sims"] += 1
        report["status"] = "MEASURED_ADC_EQUIVALENT_R_INPUT_CHARGE_DIAGNOSTIC"
        report["active_sampling_observed_in_both_cases"] = all(j["sampling_command_on_witnessed"] for j in report["jobs"])
        report["active_input_load_gate"] = ("COMMAND_ON_OBSERVED_SHORT_PROBE_ONLY" if report["active_sampling_observed_in_both_cases"]
                                             else "PENDING_ACTIVE_SAMPLING_WINDOW")
        report["conversion_gate"] = "NOT_MEASURED"
    except FileExistsError:
        raise
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_ADC_EQUIVALENT_R_INPUT_LOAD"
        report["error"] = f"{type(error).__name__}: {error}"
        if isinstance(error, KeyboardInterrupt):
            raise
    finally:
        if execute and sys.exc_info()[0] is not FileExistsError:
            if store:
                if report.get("error"):
                    store.note(report["error"])
                store.note(f"END {report['status']}: {report['completed_sims']}/2")
            common.save_summary(root / common.BASE / tag / "summary.json", report)
            common.bundle(root, tag, items)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK)
    parser.add_argument("--tag", default="adc_input_recovery_20261018_01")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    result = run(args.root, pdk_root=args.pdk_root, tag=args.tag, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if args.run and result["status"] != "MEASURED_ADC_EQUIVALENT_R_INPUT_CHARGE_DIAGNOSTIC":
        raise SystemExit(1)
