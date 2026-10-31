"""Separate OpenLane GDS *prototype* path; never creates sign-off receipts.

The input must be a physically built wrapper GDS/LEF containing a real
sense/ADC, not renamed passive-core views or the Stage-7 digital model.
This script only binds that hard macro to the existing controller and runs
OpenLane 1 after an explicit --run. It cannot manufacture an ADC layout.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automx_cim.openlane import locate_openlane_flow

WRAPPER = "automx_ternary_cim_4x4"
TOP = "automx_cim_tile_controller"
DESIGN = Path("openlane/automx_cim_tile_controller")
GDS = Path(f"physical/sky130/wrapper/{WRAPPER}.gds")
LEF = Path(f"physical/sky130/wrapper/{WRAPPER}.lef")
LIB = Path(f"physical/sky130/wrapper/{WRAPPER}.lib")
PROTOTYPE_MANIFEST = Path("physical/sky130/wrapper/prototype_manifest.json")
CONFIG = DESIGN / "config.prototype.json"
PLACEMENT = DESIGN / "macro_placement.prototype.cfg"
RECEIPT = Path("results/receipts/stage8_prototype_gds.json")
TWO_READ_RECEIPT = Path("results/receipts/stage7_2p2_regression.json")
EXPECTED_PINS = {
    "clk_i", "rst_ni", "cfg_valid_i", "cfg_ready_o", "eval_valid_i",
    "eval_ready_o", "result_valid_o", "result_ready_i", "VPWR", "VGND",
    *(f"cfg_row_i[{i}]" for i in range(2)),
    *(f"cfg_wpos_i[{i}]" for i in range(4)),
    *(f"cfg_wneg_i[{i}]" for i in range(4)),
    *(f"act_x2_i[{i}]" for i in range(20)),
    *(f"result_acc_o[{i}]" for i in range(48)),
}
REQUIRED_BLOCKS = {"passive_core", "precharge", "weight_latches",
                   "signed_pwm", "sample_hold", "analog_mux", "adc", "decode_control",
                   "two_phase_control", "signed_partial_accumulation"}
REQUIRED_TWO_READ_SOURCES = {
    "rtl/automx_cim_tile_controller.sv",
    "rtl/automx_ternary_cim_4x4_2p2_model.sv",
    "scripts/run_stage7_2p2_regression.py",
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _gds_hierarchy(path: Path) -> dict[str, set[str]]:
    """Read GDSII structures and SREF/AREF edges without trusting text matches."""
    data = path.read_bytes()
    if len(data) < 8 or data[:4] != b"\x00\x06\x00\x02":
        raise ValueError("not a plain GDSII stream with HEADER record")
    graph: dict[str, set[str]] = {}
    current: str | None = None
    in_structure = False
    in_reference = False
    ended = False
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError("truncated GDSII record")
        length = int.from_bytes(data[offset:offset + 2], "big")
        if length < 4 or length % 2 or offset + length > len(data):
            raise ValueError("invalid GDSII record length")
        kind, datatype = data[offset + 2:offset + 4]
        payload = data[offset + 4:offset + length]
        if kind == 0x05:  # BGNSTR
            if in_structure:
                raise ValueError("nested GDSII structure")
            in_structure, current = True, None
        elif kind == 0x06 and datatype == 0x06:  # STRNAME
            if not in_structure or current is not None:
                raise ValueError("GDSII structure name outside BGNSTR")
            current = payload.rstrip(b"\0").decode("ascii")
            if not current or current in graph:
                raise ValueError("empty or duplicate GDSII structure name")
            graph[current] = set()
        elif kind in (0x0A, 0x0B):  # SREF / AREF
            if current is None:
                raise ValueError("GDSII reference outside structure")
            in_reference = True
        elif kind == 0x12 and datatype == 0x06 and in_reference:  # SNAME
            graph[current].add(payload.rstrip(b"\0").decode("ascii"))
        elif kind == 0x11:  # ENDEL
            in_reference = False
        elif kind == 0x07:  # ENDSTR
            if current is None:
                raise ValueError("GDSII ENDSTR without STRNAME")
            current, in_structure, in_reference = None, False, False
        elif kind == 0x04:  # ENDLIB
            if in_structure:
                raise ValueError("GDSII ENDLIB inside structure")
            ended = True
        offset += length
    if not ended or in_structure or not graph:
        raise ValueError("incomplete GDSII structure library")
    return graph


def _gds_structures(path: Path) -> set[str]:
    return set(_gds_hierarchy(path))


def _gds_reaches(graph: dict[str, set[str]], source: str, target: str) -> bool:
    pending = [source]
    seen: set[str] = set()
    while pending:
        name = pending.pop()
        if name == target:
            return True
        if name in seen:
            continue
        seen.add(name)
        pending.extend(graph.get(name, ()))
    return False


def _lef_macro(path: Path) -> tuple[float, float, set[str]]:
    content = path.read_text(encoding="utf-8", errors="replace")
    block = re.search(rf"(?ims)^\s*MACRO\s+{WRAPPER}\s*$"
                      rf"(.*?)^\s*END\s+{WRAPPER}\s*$", content)
    if block is None:
        raise ValueError(f"LEF does not define MACRO {WRAPPER}")
    body = block.group(1)
    sizes = re.findall(r"(?im)^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", body)
    if len(sizes) != 1:
        raise ValueError("LEF must contain one macro SIZE")
    width, height = map(float, sizes[0])
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("invalid LEF macro dimensions")
    pins = set(re.findall(r"(?im)^\s*PIN\s+([^\s]+)", body))
    if pins != EXPECTED_PINS:
        raise ValueError(f"LEF/RTL pin mismatch: missing={sorted(EXPECTED_PINS - pins)}; "
                         f"extra={sorted(pins - EXPECTED_PINS)}")
    return width, height, pins


def _flow() -> str | None:
    return locate_openlane_flow()


def inspect(root: str | Path, *, require_tool: bool = True) -> dict:
    root = Path(root).resolve()
    reasons = []
    core = root / "physical/sky130/macro/automx_ternary_cim_4x4_core.gds"
    if not core.is_file() or not core.stat().st_size:
        reasons.append("passive-core GDS missing; copy the genuine Stage-5 artifact")
    summary = root / "results/receipts/physical/stage5_summary.json"
    try:
        stage5 = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stage5 = {}
    if stage5.get("status") != "PASS":
        reasons.append("Stage-5 passive-core summary is not PASS")
    logical_path = root / TWO_READ_RECEIPT
    try:
        logical = json.loads(logical_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logical = {}
    if not isinstance(logical, dict):
        logical = {}
    if (logical.get("format") != "automx-cim-stage7-2p2-v1" or
            logical.get("status") != "PASS_LOGICAL_2P2" or
            logical.get("phase_a_reads") != 16 or
            logical.get("phase_b_reads") != 16):
        reasons.append("two-read 2+2 logical regression is missing or not PASS_LOGICAL_2P2")
    else:
        sources = logical.get("sources", {})
        if not isinstance(sources, dict) or not REQUIRED_TWO_READ_SOURCES.issubset(sources):
            reasons.append("two-read logical regression source inventory is incomplete")
        else:
            for relative, digest in sources.items():
                if not isinstance(relative, str) or not isinstance(digest, str):
                    reasons.append("two-read logical regression has invalid source hashes")
                    continue
                source = (root / relative).resolve()
                if (not source.is_relative_to(root) or not source.is_file() or
                        _sha(source) != digest):
                    reasons.append(f"two-read logical source changed: {relative}")
    gds, lef = root / GDS, root / LEF
    structures = set()
    hierarchy: dict[str, set[str]] = {}
    size = None
    if not gds.is_file() or not gds.stat().st_size:
        reasons.append(f"real clocked wrapper GDS missing: {GDS}")
    else:
        try:
            hierarchy = _gds_hierarchy(gds)
            structures = set(hierarchy)
            if WRAPPER not in structures:
                reasons.append(f"GDS has no {WRAPPER} structure")
            if gds.read_bytes() == core.read_bytes():
                reasons.append("wrapper GDS is a byte-for-byte passive-core copy")
        except (OSError, UnicodeError, ValueError) as error:
            reasons.append(f"invalid wrapper GDS: {error}")
    if not lef.is_file() or not lef.stat().st_size:
        reasons.append(f"real clocked wrapper LEF missing: {LEF}")
    else:
        try:
            width, height, _ = _lef_macro(lef)
            size = [width, height]
        except (OSError, ValueError) as error:
            reasons.append(f"invalid wrapper LEF: {error}")
    manifest_path = root / PROTOTYPE_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    if not isinstance(manifest, dict):
        manifest = {}
    if (manifest.get("format") != "automx-cim-wrapper-prototype-manifest-v1" or
            manifest.get("module") != WRAPPER or
            manifest.get("evidence_level") != "UNVERIFIED_PROTOTYPE" or
            manifest.get("read_architecture") != "two_plus_two_adjacent" or
            not isinstance(manifest.get("adc_structure"), str) or
            not manifest.get("adc_structure") or
            not isinstance(manifest.get("blocks"), list) or
            not REQUIRED_BLOCKS.issubset(set(manifest.get("blocks", [])))):
        reasons.append(f"prototype block manifest missing/incomplete: {PROTOTYPE_MANIFEST}")
    else:
        if (gds.is_file() and lef.is_file() and
                (manifest.get("wrapper_gds_sha256") != _sha(gds) or
                 manifest.get("wrapper_lef_sha256") != _sha(lef))):
            reasons.append("prototype manifest does not match actual wrapper GDS/LEF")
        if core.is_file() and manifest.get("passive_core_gds_sha256") != _sha(core):
            reasons.append("prototype manifest does not match Stage-5 passive-core GDS")
        if logical_path.is_file() and manifest.get("logical_regression_sha256") != _sha(logical_path):
            reasons.append("prototype manifest does not match two-read logical regression")
        if structures and (not _gds_reaches(hierarchy, WRAPPER, "automx_ternary_cim_4x4_core") or
                           not _gds_reaches(hierarchy, WRAPPER, manifest["adc_structure"])):
            reasons.append("wrapper GDS hierarchy lacks passive core or declared ADC structure")
    flow = _flow() if require_tool else None
    if require_tool and not flow:
        reasons.append("OpenLane 1 flow.tcl not executable via PATH, OPENLANE_ROOT or OPENLANE_FLOW_TCL")
    return {"status": "READY_FOR_EXPERIMENTAL_OPENLANE" if not reasons else "BLOCKED",
            "reasons": reasons, "wrapper_size_um": size, "flow_tcl": flow,
            "scope": "GDS prototype only; no ADC/PVT/STA/DRC/LVS sign-off"}


def _write_config(root: Path, size: list[float]) -> tuple[Path, Path]:
    design = root / DESIGN
    base = json.loads((design / "config.json").read_text(encoding="utf-8"))
    if base.get("DESIGN_NAME") != TOP:
        raise ValueError("wrong OpenLane top module")
    # This file is separate from the sign-off config and placement.
    width, height = size
    anchor = 120.0
    base["DIE_AREA"] = f"0 0 {math.ceil(width + 2 * anchor)} {math.ceil(height + 2 * anchor)}"
    base["MACRO_PLACEMENT_CFG"] = "dir::macro_placement.prototype.cfg"
    if not (root / LIB).is_file():
        base.pop("EXTRA_LIBS", None)
    placement = design / "macro_placement.prototype.cfg"
    config = design / "config.prototype.json"
    for target, content in ((placement, f"macro_i {anchor:g} {anchor:g} N\n"),
                            (config, json.dumps(base, indent=2) + "\n")):
        if target.exists() and target.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"refusing to overwrite a different prototype file: {target}")
        if not target.exists():
            target.write_text(content, encoding="utf-8")
    return config, placement


def run(root: str | Path, *, execute: bool = False, tag: str = "stage8_prototype",
        timeout_s: int = 7200) -> dict:
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", tag) or timeout_s <= 0:
        raise ValueError("safe tag and positive timeout_s required")
    inspection = inspect(root, require_tool=execute)
    report = {"format": "automx-cim-stage8-prototype-gds-v1",
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "status": inspection["status"] if not execute else "BLOCKED",
              "scope": inspection["scope"], "reasons": inspection["reasons"],
              "tag": tag, "final_gds": None, "final_gds_sha256": None,
              "flow_returncode": None, "flow_log": None}
    if execute and not inspection["reasons"]:
        design = root / DESIGN
        run_path = design / "runs" / tag
        if run_path.exists():
            raise FileExistsError(f"refusing to reuse existing OpenLane tag: {run_path}")
        config, placement = _write_config(root, inspection["wrapper_size_um"])
        log = root / "build/stage8_prototype_gds" / tag / "openlane.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        command = [inspection["flow_tcl"], "-design", str(design),
                   "-config_file", str(config), "-tag", tag]
        try:
            with log.open("w", encoding="utf-8") as stream:
                process = subprocess.run(command, cwd=root, stdout=stream,
                                         stderr=subprocess.STDOUT, timeout=timeout_s,
                                         check=False)
            code = process.returncode
        except subprocess.TimeoutExpired:
            code = None
            report["reasons"].append(f"OpenLane timeout after {timeout_s}s")
        final = run_path / "results/final/gds" / f"{TOP}.gds"
        report.update(flow_returncode=code, flow_log=str(log.relative_to(root)),
                      prototype_config_sha256=_sha(config),
                      prototype_placement_sha256=_sha(placement),
                      wrapper_gds_sha256=_sha(root / GDS),
                      wrapper_lef_sha256=_sha(root / LEF))
        if code == 0 and final.is_file() and final.stat().st_size:
            try:
                if TOP not in _gds_structures(final):
                    raise ValueError("final GDS lacks top-level structure")
            except (OSError, UnicodeError, ValueError) as error:
                report["reasons"].append(f"invalid OpenLane final GDS: {error}")
            else:
                report["status"] = "PROTOTYPE_GDS_GENERATED_UNVERIFIED"
                report["final_gds"] = str(final.relative_to(root))
                report["final_gds_sha256"] = _sha(final)
        elif code is not None:
            report["reasons"].append("OpenLane failed or produced no nonempty final GDS")
        if report["status"] != "PROTOTYPE_GDS_GENERATED_UNVERIFIED":
            report["status"] = "FAIL"
    receipt = root / RECEIPT
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run", action="store_true", help="run OpenLane after real wrapper GDS/LEF are present")
    parser.add_argument("--tag", default="stage8_prototype")
    parser.add_argument("--timeout-s", type=int, default=7200)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, tag=args.tag, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if args.run and result["status"] != "PROTOTYPE_GDS_GENERATED_UNVERIFIED":
        raise SystemExit(1)
