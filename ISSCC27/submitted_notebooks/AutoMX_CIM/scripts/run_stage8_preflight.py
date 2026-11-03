"""Fail-closed gate for macro-bound SKY130 top-level implementation.

The passive 4x4 core's GDS/LEF/PEX cannot substitute for the missing clocked
wrapper GDS/LEF/Liberty/SPEF and wrapper DRC/LVS/timing sign-off.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automx_cim.openlane import locate_openlane_flow
from scripts.run_stage8_prototype_gds import _gds_hierarchy, _gds_reaches, _lef_macro

WRAPPER = "automx_ternary_cim_4x4"
REQUIRED_VIEWS = {ext: f"physical/sky130/wrapper/{WRAPPER}.{ext}"
                  for ext in ("gds", "lef", "lib", "spef")}
TWO_READ_RECEIPT = "results/receipts/stage7_2p2_regression.json"
TWO_READ_SOURCES = {
    "rtl/automx_cim_tile_controller.sv",
    "rtl/automx_ternary_cim_4x4_2p2_model.sv",
    "scripts/run_stage7_2p2_regression.py",
}


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _placement(path: Path) -> tuple[float, float, str] | None:
    """Accept one actual macro instance, not an empty/comment-only template."""
    if not path.is_file():
        return None
    lines = [line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines()]
    entries = [line.split() for line in lines if line]
    if len(entries) != 1 or len(entries[0]) != 4 or entries[0][0] != "macro_i":
        return None
    try:
        x, y = map(float, entries[0][1:3])
    except ValueError:
        return None
    orientation = entries[0][3]
    if not all(math.isfinite(value) and value >= 0 for value in (x, y)) or orientation not in {
        "N", "S", "E", "W", "FN", "FS", "FE", "FW"
    }:
        return None
    return x, y, orientation


def _lef_size(path: Path) -> tuple[float, float] | None:
    if not path.is_file():
        return None
    match = re.search(r"(?im)^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;",
                      path.read_text(encoding="utf-8"))
    if not match:
        return None
    width, height = map(float, match.groups())
    return (width, height) if width > 0 and height > 0 else None


def preflight(root: str | Path, require_tool: bool = True) -> dict[str, object]:
    root = Path(root).resolve()
    reasons: list[str] = []
    contract = _read(root / "physical/sky130/macro/macro_contract.json")
    if not contract or contract.get("digital_wrapper", {}).get("module") != WRAPPER:
        reasons.append("wrapper contract missing or module name mismatch")
    # This frozen contract is part of Stage-5 provenance. Do not edit its
    # PENDING_PERIPHERY status merely to bypass the wrapper evidence gate.
    stage5 = _read(root / "results/receipts/physical/stage5_summary.json")
    if not stage5 or stage5.get("status") != "PASS":
        reasons.append("Stage-5 physical-core summary is not PASS")
    else:
        core_gds = root / "physical/sky130/macro/automx_ternary_cim_4x4_core.gds"
        stage5_views = stage5.get("views")
        core_view = stage5_views.get("gds") if isinstance(stage5_views, dict) else None
        if (not core_gds.is_file() or not isinstance(core_view, dict) or
                core_view.get("sha256") != _hash(core_gds)):
            reasons.append("passive-core GDS missing or differs from Stage-5 summary")
    stage7 = _read(root / "results/receipts/stage7_regression.json")
    controller = root / "rtl/automx_cim_tile_controller.sv"
    if not stage7 or stage7.get("status") != "PASS":
        reasons.append("Stage-7 Verilator regression is not PASS")
    elif not controller.is_file() or stage7.get("sources", {}).get("rtl/automx_cim_tile_controller.sv") != _hash(controller):
        reasons.append("Stage-7 controller changed after regression")
    else:
        for relative, digest in stage7.get("sources", {}).items():
            source = (root / relative).resolve()
            if not source.is_relative_to(root) or not source.is_file() or _hash(source) != digest:
                reasons.append(f"Stage-7 source changed after regression: {relative}")
        manifest = root / "results/receipts/mha_tiny_schedule_manifest.json"
        if not manifest.is_file() or stage7.get("stage2_manifest_sha256") != _hash(manifest):
            reasons.append("Stage-2 schedule changed after Stage-7 regression")
    stress_path = root / "results/receipts/stage7_stress.json"
    stress = _read(stress_path)
    if not stress or stress.get("status") != "PASS" or stress.get("scenario_count") != 4:
        reasons.append("Stage-7 zero/extreme/cancellation/E8M0 stress regression is not PASS")
    else:
        if not stage7 or stress.get("baseline_receipt_sha256") != _hash(root / "results/receipts/stage7_regression.json"):
            reasons.append("Stage-7 stress receipt is not linked to current baseline regression")
        for relative, digest in stress.get("sources", {}).items():
            source = (root / relative).resolve()
            if not source.is_relative_to(root) or not source.is_file() or _hash(source) != digest:
                reasons.append(f"Stage-7 stress source changed: {relative}")
        scenarios = stress.get("scenarios")
        required = {"zero_low_scale", "extreme_high_scale", "signed_cancellation", "mixed_codes"}
        if not isinstance(scenarios, dict) or set(scenarios) != required:
            reasons.append("Stage-7 stress scenario set is incomplete")
        else:
            for name, item in scenarios.items():
                if not isinstance(item, dict) or item.get("status") != "PASS":
                    reasons.append(f"Stage-7 stress scenario {name} is not PASS")
                    continue
                for field, filename in (("vectors_sha256", "vectors.json"),
                                        ("testbench_sha256", "tb_stage7.sv")):
                    artifact = root / "build/stage7_stress" / name / filename
                    if not artifact.is_file() or item.get(field) != _hash(artifact):
                        reasons.append(f"Stage-7 stress {name} {filename} changed")

    two_read_path = root / TWO_READ_RECEIPT
    two_read = _read(two_read_path)
    if (not two_read or two_read.get("format") != "automx-cim-stage7-2p2-v1" or
            two_read.get("status") != "PASS_LOGICAL_2P2" or
            two_read.get("phase_a_reads") != 16 or
            two_read.get("phase_b_reads") != 16):
        reasons.append("two-read 2+2 logical regression is not PASS_LOGICAL_2P2")
    else:
        sources = two_read.get("sources", {})
        if not isinstance(sources, dict) or not TWO_READ_SOURCES.issubset(sources):
            reasons.append("two-read 2+2 source inventory is incomplete")
        else:
            for relative, digest in sources.items():
                if not isinstance(relative, str) or not isinstance(digest, str):
                    reasons.append("two-read 2+2 source inventory has invalid hash entries")
                    continue
                source = (root / relative).resolve()
                if not source.is_relative_to(root) or not source.is_file() or _hash(source) != digest:
                    reasons.append(f"two-read 2+2 source changed: {relative}")

    paths = {name: root / relative for name, relative in REQUIRED_VIEWS.items()}
    for name, path in paths.items():
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append(f"clocked wrapper {name.upper()} missing: {path.relative_to(root)}")
    if paths["gds"].is_file() and paths["gds"].stat().st_size:
        try:
            hierarchy = _gds_hierarchy(paths["gds"])
            for name in (WRAPPER, "automx_ternary_cim_4x4_core"):
                if name not in hierarchy:
                    reasons.append(f"clocked wrapper GDS lacks {name} structure")
            if not _gds_reaches(hierarchy, WRAPPER, "automx_ternary_cim_4x4_core"):
                reasons.append("clocked wrapper GDS does not reference passive core")
            core_gds = root / "physical/sky130/macro/automx_ternary_cim_4x4_core.gds"
            if core_gds.is_file() and paths["gds"].read_bytes() == core_gds.read_bytes():
                reasons.append("clocked wrapper GDS is a passive-core copy")
        except (OSError, UnicodeError, ValueError) as error:
            reasons.append(f"clocked wrapper GDS invalid: {error}")
    if paths["lef"].is_file() and paths["lef"].stat().st_size:
        try:
            _lef_macro(paths["lef"])
        except (OSError, ValueError) as error:
            reasons.append(f"clocked wrapper LEF invalid: {error}")
    blackbox = root / "rtl/automx_ternary_cim_4x4_blackbox.sv"
    if not blackbox.is_file() or f"module {WRAPPER} (" not in blackbox.read_text(encoding="utf-8"):
        reasons.append("clocked wrapper RTL blackbox missing or mismatched")
    signoff_path = root / "results/receipts/wrapper_signoff.json"
    signoff = _read(signoff_path)
    if not signoff or signoff.get("status") != "PASS" or signoff.get("module") != WRAPPER:
        reasons.append("wrapper_signoff.json is not PASS (DRC/LVS/post-layout/STA/ADC/PVT required)")
    else:
        if signoff.get("read_architecture") != "two_plus_two_adjacent":
            reasons.append("wrapper sign-off does not identify the two-read 2+2 architecture")
        if two_read and signoff.get("two_read_logical_receipt_sha256") != _hash(two_read_path):
            reasons.append("wrapper sign-off is not linked to the current two-read regression")
        if signoff.get("pvt") != {"corner": "tt", "vdd_v": 1.8, "temperature_c": 25}:
            reasons.append("wrapper sign-off does not identify the frozen TT/1.8V/25C point")
        for name, path in paths.items():
            if path.is_file() and signoff.get("views", {}).get(name, {}).get("sha256") != _hash(path):
                reasons.append(f"wrapper {name.upper()} hash differs from sign-off")
        required_checks = ("magic_drc", "klayout_drc", "netgen_lvs", "post_layout",
                           "sta", "adc_transfer", "pvt_matrix")
        for name in required_checks:
            check = signoff.get("checks", {}).get(name)
            if not isinstance(check, dict) or check.get("status") != "PASS":
                reasons.append(f"wrapper {name} sign-off is not PASS")
                continue
            relative = check.get("receipt")
            evidence = (root / relative).resolve() if isinstance(relative, str) else None
            if evidence is None or not evidence.is_relative_to(root) or not evidence.is_file():
                reasons.append(f"wrapper {name} evidence receipt missing or outside project")
            elif check.get("sha256") != _hash(evidence) or (_read(evidence) or {}).get("status") != "PASS":
                reasons.append(f"wrapper {name} evidence hash/status mismatch")
        if stage5 and signoff.get("core_stage5_summary_sha256") != _hash(root / "results/receipts/physical/stage5_summary.json"):
            reasons.append("wrapper sign-off is not linked to current physical core")

    config_path = root / "openlane/automx_cim_tile_controller/config.json"
    config = _read(config_path)
    if not config or config.get("DESIGN_NAME") != "automx_cim_tile_controller":
        reasons.append("macro-bound OpenLane config missing or wrong top module")
    elif not all(key in config for key in ("VERILOG_FILES_BLACKBOX", "EXTRA_LEFS", "EXTRA_GDS_FILES", "EXTRA_LIBS")):
        reasons.append("macro-bound OpenLane config lacks blackbox/LEF/GDS/Liberty binding")
    if config and config.get("DESIGN_NAME") == "automx_cim_tile_controller":
        placement = config.get("MACRO_PLACEMENT_CFG")
        placement_point = None
        if not isinstance(placement, str) or not placement.startswith("dir::"):
            reasons.append("OpenLane manual macro placement config is not set")
        else:
            placement_path = (config_path.parent / placement.removeprefix("dir::")).resolve()
            if not placement_path.is_relative_to(root):
                reasons.append("OpenLane macro placement file escapes project")
            else:
                placement_point = _placement(placement_path)
                if placement_point is None:
                    reasons.append("OpenLane placement must contain one valid macro_i x y orientation record")
        die_area = None
        try:
            die_area = tuple(float(value) for value in str(config.get("DIE_AREA", "")).split())
        except ValueError:
            pass
        if (die_area is None or len(die_area) != 4 or
                not all(math.isfinite(value) for value in die_area) or
                die_area[0] >= die_area[2] or die_area[1] >= die_area[3]):
            reasons.append("OpenLane DIE_AREA is missing or invalid")
        elif config.get("DIE_AREA") == "0 0 1200 1200":
            reasons.append("OpenLane DIE_AREA is still the unchecked placeholder")
        if placement_point and die_area and len(die_area) == 4 and paths["lef"].is_file():
            size = _lef_size(paths["lef"])
            if size is None:
                reasons.append("clocked wrapper LEF SIZE missing or invalid")
            else:
                x, y, orientation = placement_point
                width, height = size if orientation in ("N", "S", "FN", "FS") else size[::-1]
                if (x < die_area[0] or y < die_area[1] or
                        x + width > die_area[2] or y + height > die_area[3]):
                    reasons.append("clocked wrapper placement lies outside DIE_AREA")
    flow = locate_openlane_flow() if require_tool else None
    if require_tool and not flow:
        reasons.append("OpenLane flow.tcl not executable via PATH, OPENLANE_ROOT or OPENLANE_FLOW_TCL")
    receipt = {
        "format": "automx-cim-stage8-preflight-v1",
        "status": "PASS" if not reasons else "BLOCKED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "module": WRAPPER, "reasons": reasons,
        "core_stage5_summary_sha256": _hash(root / "results/receipts/physical/stage5_summary.json") if stage5 else None,
        "stage7_receipt_sha256": _hash(root / "results/receipts/stage7_regression.json") if stage7 else None,
        "stage7_stress_sha256": _hash(stress_path) if stress else None,
        "stage7_2p2_sha256": _hash(two_read_path) if two_read else None,
        "wrapper_signoff_sha256": _hash(signoff_path) if signoff else None,
        "view_sha256": {name: _hash(path) for name, path in paths.items() if path.is_file() and path.stat().st_size},
        "openlane_config_sha256": _hash(config_path) if config else None,
        "flow_tcl": flow,
    }
    output = root / "results/receipts/stage8_preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = preflight(args.root)
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)
