#!/usr/bin/env python3
"""Probe input charge using the complete pinned SAR ADC RC netlist.

Two short TT reset/start probes at different input common modes. External
ideal supply/VCM/control are intentional testbench boundaries. No transistor,
DAC, RC network or internal test port is dropped or replaced with an ideal ADC.
This is not a conversion, accuracy or physical pin-adapter signoff.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_flow2_adc_ip as adc
from scripts import flow2_integration_common as common
from scripts import run_flow2_acquisition_layout as acq
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK
from automx_cim.spice import parse_measurements

REFERENCE_HOLD_FF = 39.93533333333333
INPUT_STEP_V = .01
MEASURES = ("charge_p_c", "charge_n_c", "input_p_v", "input_n_v", "supply_charge_c")


def input_switches(path: Path) -> dict:
    """Identify MOS devices touching the physical input's resistive component.

    This traces the unmodified netlist to locate scalar diagnostic probes. It
    does not reduce or flatten away the rest of the ADC electrical network.
    """
    parent = {}
    def find(node):
        parent.setdefault(node, node)
        while node != parent[node]:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        f = line.split()
        if len(f) >= 4 and f[0].lower().startswith("r"):
            parent[find(f[1])] = find(f[2])
    targets = {name: find(name) for name in ("inp_analog", "inn_analog")}
    devices = {name: [] for name in targets}
    counts = {"mos": 0, "mim": 0, "resistors": 0, "capacitors": 0}
    for line in lines:
        f = line.split()
        if not f or f[0][0] in "*.+":
            continue
        if f[0][0].lower() in "rc":
            counts["resistors" if f[0][0].lower() == "r" else "capacitors"] += 1
        if f[0][0].lower() != "x":
            continue
        index = next((i for i, value in enumerate(f) if value.startswith("sky130_fd_pr__")), None)
        if index is None:
            raise ValueError("unknown primitive in flat ADC RC view")
        if "__cap_" in f[index]:
            counts["mim"] += 1
            continue
        counts["mos"] += 1
        if index != 5:
            raise ValueError("ADC MOS port order is not D G S B")
        for name, component in targets.items():
            if find(f[1]) == component or find(f[3]) == component:
                devices[name].append({"name": f[0], "gate": f[2], "primitive": f[index]})
    if any(len(group) != 8 for group in devices.values()):
        raise ValueError("pinned ADC input should have four NFET/four PFET sampling devices per side")
    for group in devices.values():
        if sum("__nfet_" in d["primitive"] for d in group) != 4:
            raise ValueError("ADC sampling switch polarity differs")
    return {"input_switches": devices, "full_netlist_counts": counts}


def deck(model: Path, rc: Path, pins: list[str], probes: dict, cm: float) -> str:
    mapping = {"VDD": "VPWR", "VSS": "0", "rst_n": "RST_N", "start_conversion_in": "START",
               "clk_vcm": "CLK_VCM", "inp_analog": "AINP", "inn_analog": "AINN", "vcm": "VCM"}
    nodes = [mapping[p] if p in mapping else "0" if p.startswith("config_") else f"ADC_PORT_{i}"
             for i, p in enumerate(pins)]
    # Every extra RC port retains its own distinct node; test/internal ports
    # absent from LEF must not accidentally short together or to supply.
    lines = [f".title complete ADC RC input-charge probe CM={cm:g} V",
             f'.lib "{model.as_posix()}" tt', f'.include "{rc.as_posix()}"',
             ".temp 25", ".option method=gear reltol=1e-4 abstol=1e-13",
             "VVDD VPWR 0 1.8", "VVCM VCM 0 .9", "VCLK CLK_VCM 0 0",
             "VRST RST_N 0 PWL(0 0 2n 0 2.05n 1.8 30n 1.8)",
             "VSTART START 0 PWL(0 0 16n 0 16.05n 1.8 26n 1.8 26.05n 0 30n 0)",
             f"XADC {' '.join(nodes)} adc_top_postlayout"]
    for name, sign in (("P", -1), ("N", 1)):
        initial, final = cm + sign * .001, cm + sign * .001 + INPUT_STEP_V
        lines.append(f"VIN{name} AIN{name} 0 PWL(0 {initial:.9g} 8n {initial:.9g} 10n {final:.9g} 30n {final:.9g})")
        lines += [f".measure tran charge_{name.lower()}_c INTEG I(VIN{name}) FROM=7.9n TO=20n",
                  f".measure tran input_{name.lower()}_v FIND V(AIN{name}) AT=20n"]
    # Check whether sampling devices are commanded into their complementary
    # on state; do not interpret an inactive/reset load as the active DAC load.
    for side, entries in probes["input_switches"].items():
        for index, device in enumerate(entries):
            kind = "n" if "__nfet_" in device["primitive"] else "p"
            operation = "MAX" if kind == "n" else "MIN"
            lines.append(f".measure tran gate_{side}_{index}_{kind} {operation} V(xadc.{device['gate']}) FROM=8n TO=12n")
    # Simultaneous command-state witness, rather than combining gate maxima
    # at unrelated times. All 16 switch controls must cross their on rails.
    terms = []
    for entries in probes["input_switches"].values():
        for d in entries:
            value = f"V(xadc.{d['gate']})"
            terms.append(f"({value}-1.62)" if "__nfet_" in d["primitive"] else f"(0.18-{value})")
    witness = terms[0]
    for term in terms[1:]:
        witness = f"min({witness},{term})"
    lines += [f"BSTATE ADC_SAMPLE_ON 0 V={witness}",
              ".measure tran sampling_command_margin_v MAX V(ADC_SAMPLE_ON) FROM=8n TO=12n",
              ".measure tran supply_charge_c INTEG I(VVDD) FROM=7.9n TO=20n"]
    # Do not retain a transient vector for every one of the hundreds of
    # thousands of internal RC nodes. All devices still participate in the
    # solver; only the signals needed by the measurements are saved.
    saved = ["v(AINP)", "v(AINN)", "i(VINP)", "i(VINN)", "i(VVDD)", "v(ADC_SAMPLE_ON)"]
    saved += [f"v(xadc.{d['gate']})" for group in probes["input_switches"].values() for d in group]
    lines += [".save " + " ".join(dict.fromkeys(saved)), ".tran 100p 30n", ".end", ""]
    return "\n".join(lines)


def analyze(log: str, cm: float, probes: dict) -> dict:
    expected = (*MEASURES, "sampling_command_margin_v", *(f"gate_{side}_{i}_{'n' if '__nfet_' in d['primitive'] else 'p'}"
        for side, group in probes["input_switches"].items() for i, d in enumerate(group)))
    if re.search(r"(?im)^\s*(error\b|fatal\b)", log):
        raise ValueError("ADC simulator/measurement error; inspect the saved raw log")
    values = parse_measurements(log, expected)
    if set(values) != set(expected) or not all(math.isfinite(v) for v in values.values()):
        raise ValueError("ADC input charge/probe measurements are incomplete/nonfinite")
    for side, sign in (("p", -1), ("n", 1)):
        if abs(values[f"input_{side}_v"] - (cm + sign * .001 + INPUT_STEP_V)) > 1e-5:
            raise ValueError("ADC input stimulus validation failed")
    on = values["sampling_command_margin_v"] >= 0
    return {"raw_measurements": values, "input_common_mode_v": cm,
            "sampling_command_on_witnessed": on,
            "charge_per_input_c": {s: values[f"charge_{s}_c"] for s in ("p", "n")},
            "apparent_charge_over_step_ff": {s: abs(values[f"charge_{s}_c"]) / INPUT_STEP_V * 1e15 for s in ("p", "n")},
            "differential_charge_over_reference_hold_cap_v": (values["charge_n_c"] - values["charge_p_c"]) / (REFERENCE_HOLD_FF * 1e-15),
            "interpretation": "driven-input charge including kickback; Q/dV is not a deembedded capacitance or an actual held-node droop",
            "conversion_verified": False}


def run(root: Path, *, pdk_root: Path = DEFAULT_PDK, tag="adc_load_20261018_01", execute=False, timeout_s=900) -> dict:
    root, pdk = Path(root).resolve(), Path(pdk_root).expanduser().resolve()
    common.tag_ok(tag)
    if timeout_s <= 0:
        raise ValueError("positive timeout required")
    report = {"format": "automx-cim-flow2-adc-input-load-v1", "tag": tag, "status": "PREPARED",
              "planned_sims": 2, "completed_sims": 0, "jobs": [],
              "not_signoff": "complete ADC RC under ideal external VCM/supplies and reset/start controls; no completed conversion, held-node co-simulation, ADC transfer/PVT/noise or physical adapter/LIB/SPEF proof"}
    store, items = None, []
    try:
        paths = {k: root / v for k, v in adc.FILES.items()}
        if any(not p.is_file() or common._sha(p) != adc.EXPECTED_SHA256[k] for k, p in paths.items()):
            raise ValueError("copy the pinned third_party/SKY130_SAR_ADC1 files; ADC RC/GDS/LEF revision must match")
        rc, model = paths["rc_spice"], pdk / "libs.tech/ngspice/sky130.lib.spice"
        probes = input_switches(rc)
        pins = adc._spice_pins(rc)
        if len(pins) != 81:
            raise ValueError("ADC RC top must have 81 ports")
        items = [acq._item(root, p) for p in paths.values()]
        ngspice = acq.stage5._find_tool("ngspice")
        if not ngspice or not model.is_file():
            raise ValueError("ngspice and the native SKY130 model library are required")
        version = acq.stage5._tool_version("ngspice", ngspice)
        identity = {"inputs": items, "model": common._sha(model), "ngspice": version}
        report.update(probes)
        report["source_rc_spice"] = acq._item(root, rc)
        report["reference_hold_capacitance_ff"] = REFERENCE_HOLD_FF
        report["model_sha256"] = identity["model"]
        report["ngspice_version"] = version
        report["analysis_runner_sha256"] = common._sha(Path(__file__))
        if not execute:
            return report
        store = common.Store(root, tag, identity)
        store.note("START full ADC RC; two short TT input-charge probes, not two conversions")
        for cm, name in ((.9, "tt_cm0900"), (1.62, "tt_cm1620")):
            text = deck(model, rc, pins, probes, cm)
            command = [ngspice, "-b", "adc.spice"]
            def simulate(work, content=text):
                (work / "adc.spice").write_text(content, encoding="utf-8")
                return acq.stage5._run(command, work, timeout_s)
            result, _ = store.step(name, command, tcl=text, executor=simulate)
            entry = {"case": name, "returncode": result.returncode}
            report["jobs"].append(entry)
            if result.returncode:
                raise RuntimeError(f"complete ADC RC probe failed/timed out: {name}; no internal shunts or reduced ADC substituted")
            entry.update(analyze(result.stdout + result.stderr, cm, probes))
            report["completed_sims"] += 1
        report["status"] = "MEASURED_ADC_INPUT_CHARGE_DIAGNOSTIC"
        report["active_sampling_observed_in_both_cases"] = all(j["sampling_command_on_witnessed"] for j in report["jobs"])
        report["active_input_load_gate"] = ("COMMAND_ON_OBSERVED_SHORT_PROBE_ONLY"
            if report["active_sampling_observed_in_both_cases"] else "PENDING_ACTIVE_SAMPLING_WINDOW")
        report["conversion_gate"] = "NOT_MEASURED"
    except FileExistsError:
        raise
    except (Exception, KeyboardInterrupt) as error:
        report["status"] = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "BLOCKED_ADC_INPUT_LOAD"
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
    parser.add_argument("--tag", default="adc_load_20261018_01")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    result = run(args.root, pdk_root=args.pdk_root, tag=args.tag, execute=args.run, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if args.run and result["status"] != "MEASURED_ADC_INPUT_CHARGE_DIAGNOSTIC":
        raise SystemExit(1)
