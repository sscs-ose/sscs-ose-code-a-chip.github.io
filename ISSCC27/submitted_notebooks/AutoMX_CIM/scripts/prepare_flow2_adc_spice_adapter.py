#!/usr/bin/env python3
"""Map the SAR ADC's 57 published LEF pins to its 81-port RC SPICE view.

The 24 extra RC ports each receive a distinct private node. This adapter is
for exploratory simulation and does not resolve physical LVS or analog loading.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import audit_flow2_adc_ip as adc  # noqa: E402
from scripts.run_flow2_remaining_measurements import _save, _sha  # noqa: E402

OUTPUT = Path("physical/sky130/wrapper_prototype/adc_ip")


def prepare(root: str | Path) -> dict:
    root = Path(root).resolve()
    audit_path = root / adc.RECEIPT
    if not audit_path.is_file():
        raise FileNotFoundError(f"run ADC IP audit first: {audit_path}")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") == "BLOCKED_IP_FILES":
        missing = ", ".join(audit.get("missing_files", []))
        raise FileNotFoundError(f"copy the pinned ADC IP files before preparing the adapter: {missing}")
    fresh = adc.inspect(root)
    keys = ("input_sha256", "gds_sha256", "lef_pin_count", "spice_pin_count",
            "spice_extra_pins", "lef_only_pins")
    if audit.get("status") != "AUDITED_INTERFACE_BLOCKED_INTEGRATION" or any(
            audit.get(key) != fresh.get(key) for key in keys):
        raise ValueError("ADC IP audit is missing, stale or inconsistent")
    lef_pins = adc._lef_pins((root / adc.FILES["lef"]).read_text(encoding="utf-8"))
    rc_pins = adc._spice_pins(root / adc.FILES["rc_spice"])
    if len(lef_pins) != 57 or len(rc_pins) != 81 or set(lef_pins) - set(rc_pins):
        raise ValueError("ADC pin contract changed")
    children = [name if name in lef_pins else f"__UNCONNECTED_{name.replace('[', '_').replace(']', '')}"
                for name in rc_pins]
    if len(children) != len(set(children)):
        raise ValueError("adapter would short ADC pins")
    lines = [
        "* Simulation adapter for the pinned SKY130 SAR ADC IP.",
        "* Include its original adc_top.gds.RC.noD.merge.postlayout.spice separately.",
        "* Private nodes correspond to test/internal RC pins absent from LEF.",
        "* No loading, common-mode, signal-range, timing or LVS claim is implied.",
        ".subckt adc_top_lef_interface " + " ".join(lef_pins),
        "XADC_POSTLAYOUT " + " ".join(children) + " adc_top_postlayout",
        ".ends adc_top_lef_interface",
        "",
    ]
    output = root / OUTPUT / "adc_top_lef_interface.spice"
    output.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    if output.is_file() and output.read_text(encoding="utf-8") != content:
        raise FileExistsError(f"existing ADC adapter differs: {output}")
    if not output.is_file():
        output.write_text(content, encoding="utf-8")
    report = {
        "format": "automx-cim-flow2-adc-spice-adapter-v1",
        "status": "SIMULATION_ADAPTER_PREPARED_NOT_SIGNOFF",
        "source_audit_sha256": _sha(audit_path),
        "rc_spice_sha256": _sha(root / adc.FILES["rc_spice"]),
        "lef_pin_count": len(lef_pins),
        "rc_pin_count": len(rc_pins),
        "private_unconnected_pin_count": len(rc_pins) - len(lef_pins),
        "adapter": output.relative_to(root).as_posix(),
        "adapter_sha256": _sha(output),
        "not_signoff": "simulation mapping only; physical pin agreement, ADC transfer, acquisition load and composite LVS remain unmeasured",
    }
    _save(root / "results/sky130/flow2_adc_ip/adapter.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root), indent=2))
