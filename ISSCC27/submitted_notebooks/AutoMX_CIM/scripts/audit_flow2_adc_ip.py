#!/usr/bin/env python3
"""Audit a pinned third-party SAR ADC's actual views before wrapper integration.

This is a structural audit, not electrical validation or an approval to use the
ADC with AutoMX-CIM's 20 fF held nodes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_flow2_remaining_measurements import _save, _sha  # noqa: E402
from scripts.run_stage8_prototype_gds import _gds_hierarchy  # noqa: E402

PINNED_COMMIT = "892272208df28b6c7620101e129a9d8dd95ebab7"
IP = Path("third_party/SKY130_SAR_ADC1")
FILES = {
    "gds_gz": IP / "gds/adc_top.gds.gz",
    "lef": IP / "lef/adc_top.lef",
    "rc_spice": IP / "spice/adc_top.gds.RC.noD.merge.postlayout.spice",
    "verilog": IP / "verilog/gl/adc_top.v",
    "readme": IP / "README.md",
    "license": IP / "LICENSE",
}
EXPECTED_SHA256 = {
    "gds_gz": "f9671dc0b0c6068184e899a1ff97d53c40b80e8f8321c689bb7dc9c816cbf8da",
    "lef": "e17ebbe5b0b4c3392aa456fe07363be924fab2eea881930be2a6566f8bd178bd",
    "rc_spice": "17b96ca317dfbb1edbacfb4754eed42b9917c97870444423727fb73450b66d65",
    "verilog": "c4c178e183c25ca9bfbbb25b937875a1948a469c653112f978db07854d2ccf33",
    "readme": "18f966d311b0d508dae080a6705dfc8079d52e4541a2e97f59bef931edf865a1",
    "license": "1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6",
}
RECEIPT = Path("results/sky130/flow2_adc_ip/audit.json")


def _lef_pins(lef: str) -> list[str]:
    return [parts[1] for line in lef.splitlines()
            if len(parts := line.strip().split()) == 2 and parts[0] == "PIN"]


def _spice_pins(path: Path) -> list[str]:
    header: list[str] = []
    recording = False
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            stripped = line.strip()
            if not recording:
                if re.match(r"(?i)^\.subckt\s+adc_top_postlayout\s+", stripped):
                    header.extend(stripped.split()[2:])
                    recording = True
            elif stripped.startswith("+"):
                header.extend(stripped[1:].split())
            else:
                break
    if not header or len(set(header)) != len(header):
        raise ValueError("ADC RC SPICE has no unique adc_top_postlayout pin list")
    return header


def inspect(root: str | Path) -> dict:
    root = Path(root).resolve()
    inputs = {name: root / rel for name, rel in FILES.items()}
    missing = [rel.as_posix() for name, rel in FILES.items() if not inputs[name].is_file()]
    report = {
        "format": "automx-cim-flow2-adc-ip-audit-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_IP_FILES" if missing else "AUDITED_INTERFACE_BLOCKED_INTEGRATION",
        "source_url": "https://github.com/efabless/SKY130_SAR-ADC1",
        "pinned_commit": PINNED_COMMIT,
        "missing_files": missing,
        "not_signoff": "third-party view inventory only; no interface adaptation, AutoMX transfer/noise/PVT, composite DRC/LVS/PEX/STA or Liberty/SPEF",
    }
    if missing:
        return report
    report["input_sha256"] = {key: _sha(path) for key, path in inputs.items()}
    report["pinned_content_matches"] = report["input_sha256"] == EXPECTED_SHA256
    if not report["pinned_content_matches"]:
        report["status"] = "BLOCKED_IP_REVISION"
        return report
    lef = inputs["lef"].read_text(encoding="utf-8", errors="replace")
    macro = re.search(r"(?m)^MACRO\s+(\S+)\s*$", lef)
    size = re.search(r"(?m)^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", lef)
    pins_lef = _lef_pins(lef)
    pins_spice = _spice_pins(inputs["rc_spice"])
    if not macro or macro.group(1) != "adc_top" or not size:
        raise ValueError("ADC LEF macro or dimensions differ")
    if len(set(pins_lef)) != len(pins_lef):
        raise ValueError("ADC LEF has duplicate pins")
    report["lef_size_um"] = [float(size.group(1)), float(size.group(2))]
    report["lef_area_um2"] = report["lef_size_um"][0] * report["lef_size_um"][1]
    report["lef_pin_count"] = len(pins_lef)
    report["spice_pin_count"] = len(pins_spice)
    report["spice_extra_pins"] = sorted(set(pins_spice) - set(pins_lef))
    report["lef_only_pins"] = sorted(set(pins_lef) - set(pins_spice))
    report["power_pins"] = [pin for pin in ("VDD", "VSS") if pin in pins_lef]
    # The GDS is kept compressed in source control and expanded only temporarily.
    with TemporaryDirectory(prefix="automx_adc_audit_") as temporary:
        plain = Path(temporary) / "adc_top.gds"
        with gzip.open(inputs["gds_gz"], "rb") as source, plain.open("wb") as target:
            shutil.copyfileobj(source, target)
        graph = _gds_hierarchy(plain)
        report["gds_top_present"] = "adc_top" in graph
        report["gds_structure_count"] = len(graph)
        report["gds_unresolved_refs"] = sorted(set().union(*graph.values()) - set(graph))
        report["gds_sha256"] = _sha(plain)
    report["published_views"] = ["GDS", "LEF", "RC_SPICE", "gate_level_VERILOG"]
    report["missing_wrapper_views"] = ["LIB", "SPEF"]
    report["integration_blockers"] = [
        "LEF and RC SPICE pin lists differ; define and verify a pin adapter",
        "ADC input loading and common-mode compatibility with 20 fF held nodes are unmeasured",
        "conversion throughput requires a new clocked schedule",
        "one 423x403 um ADC cannot fit the existing 500x500 um core-bound floorplan alongside the core and logic",
        "third-party ADC PDK/extraction revision must be checked against the integration PDK",
        "analog channel selection, decoder calibration, reference and composite signoff are missing",
    ]
    if (report["lef_only_pins"] or not report["gds_top_present"] or
            report["gds_unresolved_refs"] or
            len(report["power_pins"]) != 2):
        report["status"] = "BLOCKED_IP_VIEW_INCONSISTENCY"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = inspect(args.root)
    _save(Path(args.root).resolve() / RECEIPT, result)
    print(json.dumps(result, indent=2))
