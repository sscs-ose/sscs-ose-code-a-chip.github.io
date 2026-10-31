#!/usr/bin/env python3
"""Prepare a hash-linked analog front-end schematic for wrapper layout.

This is a transistor-level *candidate* around the Stage-5 passive core, not
the clocked wrapper or an LVS reference for a finished ADC.  In particular,
the hold capacitors are schematic 20 fF elements until laid out and extracted.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_flow2_pvt_switch_control as control  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

CORE = "automx_ternary_cim_4x4_core_pex"
FRONTEND = "automx_cim_readout_slice_candidate"
OUTPUT = Path("physical/sky130/wrapper_prototype")
CONFIG = Path("configs/flow2_readout_prototype.json")


def core_pins() -> list[str]:
    bitlines = [f"BL{side}{col}" for col in range(4) for side in ("P", "N")]
    wordlines = [f"WL{side}{row}" for row in range(4) for side in ("P", "N")]
    weights = [f"W{side}_{row}_{col}" for row in range(4)
               for col in range(4) for side in ("POS", "NEG")]
    return bitlines + wordlines + weights + ["VGND", "VSUBS"]


def pex_pins(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"(?im)^\.subckt\s+{CORE}\s+([^\n]*(?:\n\+[^\n]*)*)", text)
    if not match:
        raise ValueError(f"{CORE} subcircuit is missing: {path}")
    return match.group(1).replace("\n+", " ").split()


def schematic() -> str:
    pins = core_pins()
    bitlines, controls = pins[:8], pins[8:48]
    held = ["H" + name for name in bitlines]
    ports = bitlines + held + controls + ["PREB", "SAM", "SAMB", "VPWR", "VGND", "VSUBS"]
    lines = [
        "* AutoMX-CIM physical readout topology candidate; NOT sign-off.",
        "* External testbench must include the matching Stage-5 core PEX and SKY130 models.",
        "* 20 fF hold capacitors and ideal control pins require physical realization.",
        "* The 800 fF bitline test load belongs to the simulation fixture, not this cell.",
        f".subckt {FRONTEND} " + " ".join(ports),
        "XCORE " + " ".join(pins) + f" {CORE}",
    ]
    for bitline, hold in zip(bitlines, held):
        lines.extend((
            f"XPRE_{bitline} {bitline} PREB VPWR VPWR sky130_fd_pr__pfet_01v8 W=1.68 L=0.15",
            f"XSHN_{bitline} {bitline} SAM {hold} VGND sky130_fd_pr__nfet_01v8 W=3.36 L=0.15",
            f"XSHP_{bitline} {bitline} SAMB {hold} VPWR sky130_fd_pr__pfet_01v8 W=3.36 L=0.15",
            f"C_{hold} {hold} VGND 20f",
        ))
    lines.extend((f".ends {FRONTEND}", ""))
    return "\n".join(lines)


def _read(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return result


def _pilot(root: Path) -> tuple[dict, Path, str]:
    server = sorted((root / campaign.OUTPUT / "pvt_switch_control").glob("*/summary.json"))
    if len(server) == 1:
        report = control.run(root, execute=False)
        if report.get("status") != "BLOCKED_SWITCH_CONTROL_PILOT":
            raise ValueError("unexpected switch-control result; inspect before layout")
        return report, server[0], "SERVER_VERIFIED"
    if server:
        raise ValueError("multiple server pilot summaries; select one explicitly")
    from scripts.audit_flow2_pvt_switch_control_copy import audit  # noqa: E402
    receipt = audit(root)
    path = sorted((root / "server_results/pvt_switch_control").glob("*/summary.json"))[0]
    if receipt["control_status"] != "BLOCKED_SWITCH_CONTROL_PILOT":
        raise ValueError("copied pilot result differs from expected blocker")
    return _read(path), path, "COPIED_LOGS_VERIFIED"


def prepare(root: str | Path) -> dict:
    root = Path(root).resolve()
    pilot, summary_path, evidence_level = _pilot(root)
    config_path = root / CONFIG
    config = _read(config_path)
    readout = config.get("readout", {})
    measurement = config.get("measurement", {})
    if (config.get("format") != "automx-cim-flow2-readout-prototype-config-v1" or
            config.get("status") != "FROZEN_FOR_LAYOUT_EXPERIMENT_ONLY" or
            config.get("signoff_gate") != "SEPARATE_AND_BLOCKED" or
            config.get("read_architecture") != "two_plus_two_adjacent" or
            config.get("operating_point") != {"corner": "tt", "vdd_v": 1.8,
                                               "temperature_c": 25} or
            config.get("core", {}).get("pex_sha256") != pilot["pex_sha256"] or
            measurement.get("switch_control_summary_sha256") != campaign._sha(summary_path) or
            measurement.get("ss_ff_capture_gate") != "FAIL" or
            measurement.get("frozen_max_capture_error_v") != pilot["capture_budget_v"] or
            readout.get("differential_columns") != 4 or
            readout.get("sample_switch_width_um") != 3.36 or
            readout.get("sample_switch_length_um") != 0.15 or
            readout.get("hold_capacitance_ff") != 20 or
            readout.get("precharge_pfet_width_um") != 1.68 or
            readout.get("precharge_pfet_length_um") != 0.15 or
            readout.get("control_variant") != "simultaneous_50ps" or
            readout.get("turnoff_start_ns") != 2.1 or
            readout.get("control_fall_ps") != 50 or
            readout.get("nmos_off_delay_ps") != 0 or
            readout.get("pmos_off_delay_ps") != 0 or
            readout.get("held_measure_time_ns") != 2.4):
        raise ValueError("frozen prototype config is inconsistent with the measured pilot")
    diagnostic = pilot.get("best_diagnostic_variant")
    if diagnostic != "simultaneous_50ps" or pilot.get("selected_control_variant") is not None:
        raise ValueError("pilot selection changed; review the analog topology")
    observed = next(item["maximum_capture_error_late_v"] for item in pilot["grid"]
                    if item["variant"] == diagnostic)
    if (abs(measurement.get("measured_ss_ff_worst_capture_error_v", 0) - observed) > 1e-8 or
            config.get("nominal_bitline_test_load_ff") != 800 or
            config.get("decoder", {}).get("status") != "NOT_FROZEN_FOR_HELD_NODE_PVT"):
        raise ValueError("prototype measurement or decoder status differs from source")
    pex = root / "physical/sky130/macro/automx_ternary_cim_4x4_core.pex.spice"
    actual_pex = campaign._sha(pex) if pex.is_file() else None
    if actual_pex == pilot["pex_sha256"] and pex_pins(pex) != core_pins():
        raise ValueError("current PEX pin order differs from front-end schematic")
    source_matched = actual_pex == pilot["pex_sha256"]
    spec = {
        "format": "automx-cim-wrapper-layout-preparation-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READY_FOR_READOUT_SLICE_LAYOUT_EXPERIMENT" if source_matched
                  else "BLOCKED_CURRENT_CORE_PEX_MISMATCH",
        "evidence_level": evidence_level,
        "source_pilot_summary_sha256": campaign._sha(summary_path),
        "prototype_config_sha256": campaign._sha(config_path),
        "prototype_config": CONFIG.as_posix(),
        "source_pilot_status": pilot["status"],
        "required_pex_sha256": pilot["pex_sha256"],
        "available_pex_sha256": actual_pex,
        "core_subckt": CORE,
        "front_end_subckt": FRONTEND,
        "core_pins": core_pins(),
        "readout": {
            "columns": 4, "differential_nodes": 8,
            "precharge_pfets": 8, "sample_hold_nfets": 8,
            "sample_hold_pfets": 8, "ideal_hold_capacitors": 8,
            "hold_capacitance_ff": readout["hold_capacitance_ff"],
            "sample_switch_width_um": readout["sample_switch_width_um"],
            "precharge_width_um": readout["precharge_pfet_width_um"],
            "prototype_control_variant": diagnostic,
            "nominal_turnoff_start_ns": readout["turnoff_start_ns"],
            "prototype_control_fall_ps": readout["control_fall_ps"],
            "worst_measured_ss_ff_capture_error_v": observed,
            "frozen_capture_budget_v": pilot["capture_budget_v"],
        },
        "required_next_blocks": ["physical hold capacitors", "control drivers",
                                 "sense/ADC and references", "decoder",
                                 "weight/wordline storage and drive",
                                 "clocked handshake interface"],
        "required_actual_checks": ["Magic DRC", "KLayout DRC", "Netgen LVS",
                                   "PEX", "post-layout transfer", "STA",
                                   "offset/noise", "PVT"],
        "not_signoff": "candidate front-end connectivity only; SS/FF capture exceeds 0.8 mV, and no layout, ADC or wrapper views exist",
    }
    folder = (root / OUTPUT / f"pilot_{spec['source_pilot_summary_sha256'][:12]}"
              f"_cfg_{spec['prototype_config_sha256'][:12]}")
    folder.mkdir(parents=True, exist_ok=True)
    netlist = folder / f"{FRONTEND}.spice"
    content = schematic()
    if netlist.is_file() and netlist.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"schematic differs: {netlist}")
    netlist.write_text(content, encoding="utf-8")
    spec["schematic_sha256"] = sha256(content.encode()).hexdigest()
    spec["schematic_path"] = str(netlist.relative_to(root)).replace("\\", "/")
    manifest = folder / "manifest.json"
    if manifest.is_file():
        previous = _read(manifest)
        if {k: v for k, v in previous.items() if k != "timestamp_utc"} != {
                k: v for k, v in spec.items() if k != "timestamp_utc"}:
            raise FileExistsError(f"layout source manifest differs: {manifest}")
        spec = previous
    else:
        manifest.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    spec["manifest_path"] = str(manifest.relative_to(root)).replace("\\", "/")
    return spec


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = prepare(args.root)
    print(json.dumps({k: v for k, v in result.items() if k != "core_pins"}, indent=2))
