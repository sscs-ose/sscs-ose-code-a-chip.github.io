#!/usr/bin/env python3
"""Check core, switch body and substrate connections in the prototype netlist.

This checks schematic connectivity only; GDS connectivity needs composite LVS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import prepare_flow2_wrapper_layout as layout  # noqa: E402
from scripts.run_flow2_remaining_measurements import _save, _sha  # noqa: E402


def inspect(root: str | Path) -> dict:
    root = Path(root).resolve()
    config_path = root / layout.CONFIG
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pilot = config["measurement"]
    pex_path = root / "physical/sky130/macro/automx_ternary_cim_4x4_core.pex.spice"
    pex_hash = _sha(pex_path) if pex_path.is_file() else None
    expected_pex = config["core"]["pex_sha256"]
    candidates = list((root / layout.OUTPUT).glob(f"pilot_*/{layout.FRONTEND}.spice"))
    if len(candidates) != 1:
        raise FileNotFoundError("expected one frozen readout schematic candidate")
    source_path = candidates[0]
    source = source_path.read_text(encoding="utf-8")
    lines = source.splitlines()
    pin_names = layout.core_pins()
    bitlines = pin_names[:8]
    failures = []
    if source != layout.schematic():
        failures.append("published readout schematic differs from the generator")
    devices = {}
    for line in lines:
        parts = line.split()
        if parts and parts[0][0] in "XC" and parts[0] not in devices:
            devices[parts[0]] = parts[1:]
        elif parts and parts[0][0] in "XC":
            failures.append(f"duplicate device {parts[0]}")
    core = devices.get("XCORE")
    if core != pin_names + [layout.CORE]:
        failures.append("XCORE pin order, VGND or VSUBS differs")
    for bitline in bitlines:
        hold = "H" + bitline
        expected = {
            f"XPRE_{bitline}": [bitline, "PREB", "VPWR", "VPWR",
                                "sky130_fd_pr__pfet_01v8", "W=1.68", "L=0.15"],
            f"XSHN_{bitline}": [bitline, "SAM", hold, "VGND",
                                "sky130_fd_pr__nfet_01v8", "W=3.36", "L=0.15"],
            f"XSHP_{bitline}": [bitline, "SAMB", hold, "VPWR",
                                "sky130_fd_pr__pfet_01v8", "W=3.36", "L=0.15"],
            f"C_{hold}": [hold, "VGND", "20f"],
        }
        for name, pins in expected.items():
            if devices.get(name) != pins:
                failures.append(f"{name} does not match the body/supply/hold contract")
    if len(devices) != 33:
        failures.append(f"expected 33 core/readout elements, found {len(devices)}")
    if pex_hash == expected_pex and layout.pex_pins(pex_path) != pin_names:
        failures.append("PEX core pin order differs from candidate wrapper")
    report = {
        "format": "automx-cim-flow2-readout-connectivity-audit-v1",
        "status": ("BLOCKED_SCHEMATIC_CONNECTIVITY" if failures else
                   "SCHEMATIC_CONNECTIVITY_PASS_PHYSICAL_PENDING"),
        "source_schematic_sha256": _sha(source_path),
        "prototype_config_sha256": _sha(config_path),
        "expected_core_pex_sha256": expected_pex,
        "available_core_pex_sha256": pex_hash,
        "core_pex_matches_prototype": pex_hash == expected_pex,
        "verified_schematic_elements": len(devices),
        "failures": failures,
        "pilot_ss_ff_capture_error_v": pilot["measured_ss_ff_worst_capture_error_v"],
        "not_signoff": "schematic S/B/VSUBS pin check only; composite GDS extraction/LVS, held-cap PEX, ADC and PVT are unmeasured",
    }
    if not report["core_pex_matches_prototype"] and not failures:
        report["status"] = "BLOCKED_LOCAL_CORE_PEX_PROVENANCE"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = inspect(args.root)
    _save(Path(args.root).resolve() / "results/sky130/flow2_readout/connectivity.json", result)
    print(json.dumps(result, indent=2))
