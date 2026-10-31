"""Experimental OpenLane bridge: digital 2+2 control plus real passive core.

This exposes the analog bitlines, PWM row controls and ADC handshake at the
top boundary. It checks hard-macro binding and top-level routing/DRC/LVS,
not an on-chip ADC or the clocked wrapper required by Stage 8 sign-off.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

TOP = "automx_cim_core_bound_demo"
CORE = "automx_ternary_cim_4x4_core"
DESIGN = Path("openlane") / TOP
CORE_GDS = Path(f"physical/sky130/macro/{CORE}.gds")
CORE_LEF = Path(f"physical/sky130/macro/{CORE}.lef")
SUMMARY = Path("results/receipts/physical/stage5_summary.json")
RECEIPT = Path("results/receipts/stage8_core_bound_demo.json")
SOURCES = (
    Path("rtl/automx_cim_2p2_periphery_ctrl.sv"),
    Path("rtl/automx_cim_core_bound_demo.sv"),
    Path(f"rtl/{CORE}_openlane_blackbox.sv"),
)
STAGE5_BLACKBOX = Path(f"rtl/{CORE}_blackbox.sv")
INPUTS = (*SOURCES, STAGE5_BLACKBOX, CORE_GDS, CORE_LEF, SUMMARY,
          DESIGN / "config.json", DESIGN / "macro_placement.cfg",
          Path("physical/sky130/layout/generate_automx_ternary_cim_4x4_core.tcl"),
          Path("scripts/run_stage8_core_bound_demo.py"))


def core_pins() -> tuple[str, ...]:
    pins = [name for col in range(4) for name in (f"BLP{col}", f"BLN{col}")]
    pins += [name for row in range(4) for name in (f"WLP{row}", f"WLN{row}")]
    pins += [name for row in range(4) for col in range(4)
             for name in (f"WPOS_{row}_{col}", f"WNEG_{row}_{col}")]
    return tuple(pins + ["VGND", "VSUBS"])


INTEGRATION_PINS = set(core_pins()) - {"VSUBS"}
TOP_CHECK_METRICS = ("tritonRoute_violations", "Magic_violations",
                     "klayout_violations", "lvs_total_errors")


def locate_openlane_flow() -> str | None:
    override = os.environ.get("OPENLANE_FLOW_TCL")
    if override:
        path = Path(override).expanduser().resolve()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    found = shutil.which("flow.tcl")
    if found:
        return found
    base = os.environ.get("OPENLANE_ROOT")
    if base:
        path = Path(base).expanduser().resolve() / "flow.tcl"
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def _gds_hierarchy(path: Path) -> dict[str, set[str]]:
    """Read GDSII structure references to check physical macro binding."""
    data = path.read_bytes()
    if len(data) < 8 or data[:4] != b"\x00\x06\x00\x02":
        raise ValueError("not a plain GDSII stream")
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
        if kind == 0x05:
            if in_structure:
                raise ValueError("nested GDSII structure")
            in_structure, current = True, None
        elif kind == 0x06 and datatype == 0x06:
            if not in_structure or current is not None:
                raise ValueError("GDSII name outside structure")
            current = payload.rstrip(b"\0").decode("ascii")
            if not current or current in graph:
                raise ValueError("empty or duplicate GDSII structure")
            graph[current] = set()
        elif kind in (0x0A, 0x0B):
            if current is None:
                raise ValueError("GDSII reference outside structure")
            in_reference = True
        elif kind == 0x12 and datatype == 0x06 and in_reference:
            graph[current].add(payload.rstrip(b"\0").decode("ascii"))
        elif kind == 0x11:
            in_reference = False
        elif kind == 0x07:
            if current is None:
                raise ValueError("GDSII ENDSTR without name")
            current, in_structure, in_reference = None, False, False
        elif kind == 0x04:
            if in_structure:
                raise ValueError("GDSII ENDLIB inside structure")
            ended = True
        offset += length
    if not ended or in_structure or not graph:
        raise ValueError("incomplete GDSII library")
    return graph


def _gds_reaches(graph: dict[str, set[str]], source: str, target: str) -> bool:
    pending = [source]
    visited: set[str] = set()
    while pending:
        name = pending.pop()
        if name == target:
            return True
        if name not in visited:
            visited.add(name)
            pending.extend(graph.get(name, ()))
    return False


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _lef_pins_and_size(path: Path) -> tuple[set[str], tuple[float, float]]:
    body = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"(?ms)^MACRO {CORE}\s*$(.*?)^END {CORE}\s*$", body)
    if match is None:
        raise ValueError("core LEF macro name missing")
    pins = set(re.findall(r"(?m)^\s*PIN\s+(\S+)", match.group(1)))
    size = re.search(r"(?m)^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;",
                     match.group(1))
    if size is None:
        raise ValueError("core LEF size missing")
    width, height = float(size[1]), float(size[2])
    if not (math.isfinite(width) and math.isfinite(height) and
            width > 0 and height > 0):
        raise ValueError("core LEF size invalid")
    return pins, (width, height)


def _lef_has_ground_met4_landing(path: Path) -> bool:
    """Require a dedicated M4 pad with the other ground bars obstructed."""
    body = path.read_text(encoding="utf-8", errors="replace")
    pin = re.search(r"(?ms)^\s*PIN VGND\s*$(.*?)^\s*END VGND\s*$", body)
    if pin is None:
        return False
    layers = re.findall(r"(?ms)^\s*LAYER (\S+)\s*;(.*?)(?=^\s*LAYER |^\s*END(?:\s|$))",
                        pin.group(1))
    if any(layer == "met5" for layer, _ in layers):
        return False
    rect_pattern = r"RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;"
    pin_m4 = [tuple(map(float, rect)) for layer, geometry in layers
              if layer == "met4" for rect in re.findall(rect_pattern, geometry)]
    if pin_m4 != [(3.0, 10.4, 4.6, 12.5)]:
        return False
    obs = re.search(r"(?ms)^  OBS[ \t]*$(.*?)^  END[ \t]*$", body)
    if obs is None:
        return False
    obs_m4 = re.search(r"(?ms)^\s*LAYER met4 ;(.*?)(?=^\s*LAYER |^\s*END(?:\s|$)|\Z)",
                       obs.group(1))
    if obs_m4 is None:
        return False
    rects = {tuple(map(float, rect)) for rect in re.findall(rect_pattern, obs_m4.group(1))}
    return rects == {
        (2.9, 31.95, 30.25, 32.45),
        (2.9, 21.45, 30.25, 21.95),
        (2.9, 10.95, 3.0, 11.45),
        (4.6, 10.95, 30.25, 11.45),
        (2.9, 0.45, 30.25, 0.95),
    }


def inspect(root: str | Path, *, require_tool: bool = False) -> dict:
    root = Path(root).resolve()
    reasons: list[str] = []
    stage5_path = root / SUMMARY
    try:
        summary = json.loads(stage5_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {}
    if summary.get("status") != "PASS" or summary.get("macro") != CORE:
        reasons.append("measured Stage-5 passive-core receipt missing or invalid")
    generator = root / "physical/sky130/layout/generate_automx_ternary_cim_4x4_core.tcl"
    try:
        layout_receipt = json.loads((root / "results/receipts/physical/layout.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        layout_receipt = {}
    if (not generator.is_file() or layout_receipt.get("status") != "PASS" or
            layout_receipt.get("generator_sha256") != _sha(generator)):
        reasons.append("Stage-5 layout was not regenerated with the current generator")
    abstraction = layout_receipt.get("lef_abstraction") or {}
    if (abstraction.get("mode") != "single_vgnd_met4_landing_v2" or
            abstraction.get("rect_um") != [3.0, 10.4, 4.6, 12.5]):
        reasons.append("Stage-5 LEF lacks the dedicated VGND landing abstraction receipt")
    core_lef_path = root / CORE_LEF
    if core_lef_path.is_file() and layout_receipt.get("lef_sha256") != _sha(core_lef_path):
        reasons.append("Stage-5 layout receipt and delivered LEF hash differ")
    for relative in INPUTS:
        if not (root / relative).is_file():
            reasons.append(f"missing input: {relative}")
    for key, relative in (("gds", CORE_GDS), ("lef", CORE_LEF),
                          ("blackbox_rtl", STAGE5_BLACKBOX)):
        path = root / relative
        if path.is_file() and summary.get("views", {}).get(key, {}).get("sha256") != _sha(path):
            reasons.append(f"Stage-5 hash mismatch: {relative}")
    if (root / CORE_GDS).is_file():
        try:
            if CORE not in _gds_hierarchy(root / CORE_GDS):
                reasons.append("Stage-5 GDS lacks core structure")
        except (OSError, UnicodeError, ValueError) as error:
            reasons.append(f"invalid core GDS: {error}")
    size = None
    if (root / CORE_LEF).is_file():
        try:
            pins, size = _lef_pins_and_size(root / CORE_LEF)
            if pins != INTEGRATION_PINS:
                reasons.append("core LEF pins differ from the expected 49-pin OpenLane view")
            if not _lef_has_ground_met4_landing(root / CORE_LEF):
                reasons.append("core LEF VGND lacks the widened met4 landing pad")
        except (OSError, ValueError) as error:
            reasons.append(f"invalid core LEF: {error}")
    if (root / SOURCES[1]).is_file():
        bridge = (root / SOURCES[1]).read_text(encoding="utf-8")
        connections = set(re.findall(r"\.([A-Za-z][A-Za-z_0-9]*)\s*\(", bridge))
        if not INTEGRATION_PINS.issubset(connections) or "VSUBS" in connections:
            reasons.append("bridge does not explicitly connect all core pins")
    if (root / SOURCES[2]).is_file():
        integration_blackbox = (root / SOURCES[2]).read_text(encoding="utf-8")
        header = re.search(rf"(?s)\bmodule\s+{CORE}\s*\((.*?)\);",
                           integration_blackbox)
        declared = (set(re.findall(
            r"\b(?:BL[PN][0-3]|WL[PN][0-3]|W(?:POS|NEG)_[0-3]_[0-3]|VGND|VSUBS)\b",
            header.group(1))) if header else set())
        if declared != INTEGRATION_PINS:
            reasons.append("OpenLane blackbox does not match the 49 LEF pins")
    if (root / SOURCES[1]).is_file() and "automx_cim_2p2_periphery_ctrl ctrl_i" not in bridge:
        reasons.append("bridge lacks real two-phase digital controller")
    config_path = root / DESIGN / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    if (config.get("DESIGN_NAME") != TOP or
            "core_bound_demo.sv" not in str(config.get("VERILOG_FILES")) or
            CORE not in str(config.get("EXTRA_LEFS")) or
            CORE not in str(config.get("EXTRA_GDS_FILES")) or
            "core_openlane_blackbox.sv" not in str(config.get("VERILOG_FILES_BLACKBOX")) or
            config.get("EXTRA_LIBS") or config.get("RUN_LVS") != 1 or
            config.get("FP_PDN_CFG") or
            config.get("FP_PDN_MACRO_HOOKS") != "core_i VPWR VGND ^$ VGND" or
            config.get("LVS_INSERT_POWER_PINS") != 0 or
            config.get("QUIT_ON_LVS_ERROR") != 1 or
            config.get("RUN_MAGIC_DRC") != 1 or
            config.get("MAGIC_DRC_USE_GDS") != 1 or
            config.get("MAGIC_EXT_USE_GDS") != 0 or
            config.get("QUIT_ON_MAGIC_DRC") != 1 or
            config.get("QUIT_ON_TR_DRC") != 1 or
            config.get("RUN_KLAYOUT_DRC") != 1):
        reasons.append("OpenLane top-check config missing or does not enable LVS, Magic GDS DRC and KLayout DRC")
    placement = root / DESIGN / "macro_placement.cfg"
    if placement.is_file() and not re.fullmatch(r"core_i\s+[\d.]+\s+[\d.]+\s+N\s*",
                                                 placement.read_text(encoding="utf-8")):
        reasons.append("core placement does not name core_i")
    flow = locate_openlane_flow() if require_tool else None
    if require_tool and not flow:
        reasons.append("OpenLane 1 flow.tcl not executable via PATH or OPENLANE_FLOW_TCL")
    return {
        "status": "READY_CORE_BOUND_EXPERIMENT" if not reasons else "BLOCKED",
        "reasons": reasons, "core_size_um": size, "flow_tcl": flow,
        "scope": "real Stage-5 passive core plus synthesized two-phase control; attempt top-level LVS without OpenLane power-pin insertion; external analog phase engine, sample/hold and ADC",
    }


def _snapshot(root: Path, tag: str) -> Path:
    target = root / "build/stage8_core_bound" / tag / "inputs.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    content = {str(relative).replace("\\", "/"): _sha(root / relative)
               for relative in INPUTS}
    if target.exists():
        if json.loads(target.read_text(encoding="utf-8")) != content:
            raise FileExistsError(f"input snapshot differs; use a new run tag: {target}")
        return target
    target.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    return target


def _top_metric_reasons(metrics: dict[str, str]) -> list[str]:
    """Reject missing checks: OpenLane uses -1 for a step without results."""
    reasons: list[str] = []
    if metrics.get("flow_status", "").lower().replace(" ", "_") != "flow_completed":
        reasons.append("OpenLane metrics do not report flow_completed")
    for key in TOP_CHECK_METRICS:
        try:
            number = float(metrics[key])
        except (KeyError, ValueError):
            reasons.append(f"OpenLane {key} is missing or not numeric")
        else:
            if not math.isfinite(number) or number != 0:
                reasons.append(f"OpenLane {key} is not zero: {metrics[key]}")
    return reasons


def _pdn_ground_reasons(def_path: Path, pdn_log: Path, core_lef: Path) -> list[str]:
    """Require a real met4/via4/met5 connection at the macro VGND pad."""
    reasons: list[str] = []
    try:
        body = def_path.read_text(encoding="utf-8", errors="replace")
        special = re.search(r"(?ms)^SPECIALNETS\s+\d+\s*;(.*?)^END SPECIALNETS\s*$", body)
        ground = (re.search(r"(?ms)^\s*- VGND\b(.*?)(?=^\s*- \S+\b|\Z)",
                            special.group(1)) if special else None)
        units = re.search(r"(?m)^UNITS DISTANCE MICRONS\s+(\d+)\s*;", body)
        instance = re.search(r"(?m)^\s*-\s+core_i\s+\S+\s+\+\s+FIXED\s+"
                             r"\(\s*(\d+)\s+(\d+)\s*\)\s+N\s*;", body)
        lef = core_lef.read_text(encoding="utf-8", errors="replace")
        macro = re.search(rf"(?ms)^MACRO {re.escape(CORE)}\s*$"
                          rf"(.*?)^END {re.escape(CORE)}\s*$", lef)
        origin = (re.search(r"(?m)^\s*ORIGIN\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;",
                            macro.group(1)) if macro else None)
        if ground is None or units is None or instance is None or origin is None:
            reasons.append("macro VGND PDN via cannot be located from DEF/LEF")
        else:
            # The sole VGND met4 pin is RECT 3.000 10.400 4.600 12.500;
            # its center is (3.8, 11.45) in the macro LEF coordinate frame.
            dbu = int(units.group(1))
            x = int(instance.group(1)) + round((3.8 + float(origin.group(1))) * dbu)
            y = int(instance.group(2)) + round((11.45 + float(origin.group(2))) * dbu)
            via = re.search(rf"\(\s*{x}\s+{y}\s*\)\s+(\S+)", ground.group(1))
            via_definition = (re.search(rf"(?m)^\s*-\s+{re.escape(via.group(1))}"
                                        r"\s+\+([^\n]*)", body) if via else None)
            if (via_definition is None or
                    re.search(r"\+\s+LAYERS\s+met4\s+via4\s+met5\b",
                              via_definition.group(1)) is None):
                reasons.append(f"VGND SPECIALNETS lacks a met4/via4/met5 via at core_i pad ({x}, {y})")
    except OSError:
        reasons.append("floorplan DEF or macro LEF missing; PDN via not checked")
    try:
        pdn_text = pdn_log.read_text(encoding="utf-8", errors="replace")
        if "PDN-0110" in pdn_text:
            reasons.append("OpenROAD PDN-0110 reports a missing power-grid via")
    except OSError:
        reasons.append("PDN log missing; via insertion not checked")
    return reasons


def _audit(root: Path, tag: str, reasons: list[str], metrics_out: dict[str, str]) -> Path | None:
    snapshot = root / "build/stage8_core_bound" / tag / "inputs.json"
    try:
        recorded = json.loads(snapshot.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        reasons.append("frozen input snapshot missing or invalid")
        return None
    expected = {str(relative).replace("\\", "/"): _sha(root / relative)
                for relative in INPUTS}
    if recorded != expected:
        reasons.append("OpenLane inputs changed since the frozen snapshot")
    run_dir = root / DESIGN / "runs" / tag
    reasons.extend(_pdn_ground_reasons(
        run_dir / "results/floorplan" / f"{TOP}.def",
        run_dir / "logs/floorplan/7-pdn.log", root / CORE_LEF))
    metrics = run_dir / "reports/metrics.csv"
    try:
        with metrics.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1:
            reasons.append("OpenLane metrics must contain exactly one data row")
        else:
            metrics_out.update({str(key): str(value).strip() for key, value in rows[0].items()
                                if key is not None and value is not None})
            reasons.extend(_top_metric_reasons(metrics_out))
    except (OSError, ValueError, csv.Error):
        reasons.append("OpenLane completed metrics missing or invalid")
    final = run_dir / "results/final/gds" / f"{TOP}.gds"
    if not final.is_file() or not final.stat().st_size:
        reasons.append("nonempty OpenLane final GDS missing")
        return None
    try:
        graph = _gds_hierarchy(final)
        if not _gds_reaches(graph, TOP, CORE):
            reasons.append("final GDS top does not reach the passive-core structure")
    except (OSError, UnicodeError, ValueError) as error:
        reasons.append(f"final GDS invalid: {error}")
    return final


def run(root: str | Path, *, execute: bool = False, audit_existing: bool = False,
        tag: str = "stage8_core_bound", timeout_s: int = 7200) -> dict:
    root = Path(root).resolve()
    if execute and audit_existing:
        raise ValueError("--run and --audit-existing are exclusive")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", tag) or timeout_s <= 0:
        raise ValueError("safe tag and positive timeout required")
    check = inspect(root, require_tool=execute)
    report = {
        "format": "automx-cim-stage8-core-bound-demo-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": check["status"], "scope": check["scope"],
        "reasons": list(check["reasons"]), "tag": tag,
        "top_lvs": "NOT_VERIFIED",
        "top_check_metrics": {},
        "run_dir": str((DESIGN / "runs" / tag).as_posix()),
        "observed_gds": None, "observed_gds_sha256": None,
        "final_gds": None, "final_gds_sha256": None,
        "not_signoff": "top-level LEF macro-connectivity LVS and GDS DRC cover the external-analog core bridge only; no composite device-level LVS/PEX, on-chip precharge, sample/hold, ADC, clocked wrapper GDS/LIB/SPEF or PVT; Stage-5 and OpenLane PDK revisions differ",
    }
    if not report["reasons"] and not audit_existing:
        snapshot = _snapshot(root, tag)
        report["input_snapshot"] = str(snapshot.relative_to(root))
        report["input_snapshot_sha256"] = _sha(snapshot)
    if execute and not report["reasons"]:
        run_dir = root / DESIGN / "runs" / tag
        if run_dir.exists():
            raise FileExistsError(f"OpenLane tag already exists: {run_dir}")
        log = root / "build/stage8_core_bound" / tag / "openlane.log"
        with log.open("w", encoding="utf-8") as stream:
            try:
                process = subprocess.run(
                    [check["flow_tcl"], "-design", str(root / DESIGN), "-tag", tag],
                    cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                    timeout=timeout_s, check=False)
                report["flow_returncode"] = process.returncode
            except subprocess.TimeoutExpired:
                report["reasons"].append(f"OpenLane timed out after {timeout_s}s")
        report["flow_log"] = str(log.relative_to(root))
        if report.get("flow_returncode") != 0:
            report["reasons"].append("OpenLane exited nonzero or timed out")
    if audit_existing or execute:
        if not check["reasons"]:
            metrics: dict[str, str] = {}
            final = _audit(root, tag, report["reasons"], metrics)
            report["top_check_metrics"] = {key: metrics.get(key) for key in
                                           ("flow_status", *TOP_CHECK_METRICS)}
            if final is not None:
                report["observed_gds"] = str(final.relative_to(root))
                report["observed_gds_sha256"] = _sha(final)
            if final is not None and not report["reasons"]:
                report["status"] = "CORE_BOUND_TOP_DRC_LVS_PASS_EXTERNAL_ANALOG"
                report["top_lvs"] = "PASS_LEF_MACRO_CONNECTIVITY"
                report["final_gds"] = report["observed_gds"]
                report["final_gds_sha256"] = report["observed_gds_sha256"]
        if report["status"] != "CORE_BOUND_TOP_DRC_LVS_PASS_EXTERNAL_ANALOG":
            report["status"] = "BLOCKED" if check["reasons"] else "FAIL"
    receipt = root / RECEIPT
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--audit-existing", action="store_true")
    parser.add_argument("--tag", default="stage8_core_bound")
    parser.add_argument("--timeout-s", type=int, default=7200)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, audit_existing=args.audit_existing,
                 tag=args.tag, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if (args.run or args.audit_existing) and result["status"] != "CORE_BOUND_TOP_DRC_LVS_PASS_EXTERNAL_ANALOG":
        raise SystemExit(1)
