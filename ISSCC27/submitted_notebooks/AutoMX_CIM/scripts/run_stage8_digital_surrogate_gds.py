"""Explore RTL-to-GDS for the *digital-only* 2+2 surrogate.

This intentionally does not consume or create the passive-core/ADC wrapper
views. Its GDS is a useful OpenLane smoke test, never a mixed-signal macro,
Stage-8 macro-bound result, or substitute for cell 5.1c.

Use --audit-existing --tag TAG to record a completed manual Docker run. This
checks the frozen digital inputs, OpenLane completion metric and GDS structure
without invoking the host flow.tcl again.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automx_cim.openlane import locate_openlane_flow
from scripts.run_stage8_prototype_gds import _gds_structures

TOP = "automx_cim_tile_controller"
DESIGN = Path("openlane/automx_cim_tile_controller")
CONFIG = DESIGN / "config.digital_surrogate.json"
RECEIPT = Path("results/receipts/stage8_digital_surrogate_gds.json")
SOURCES = (
    "rtl/automx_cim_tile_controller.sv",
    "rtl/automx_ternary_cim_4x4_2p2_model.sv",
    "rtl/automx_ternary_cim_4x4_2p2_synth.sv",
)
LOGICAL_RECEIPT = Path("results/receipts/stage7_2p2_regression.json")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _flow() -> str | None:
    return locate_openlane_flow()


def inspect(root: str | Path, *, require_tool: bool = False) -> dict:
    root = Path(root).resolve()
    reasons = []
    try:
        logical = json.loads((root / LOGICAL_RECEIPT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logical = {}
    if (not isinstance(logical, dict) or
            logical.get("format") != "automx-cim-stage7-2p2-v1" or
            logical.get("status") != "PASS_LOGICAL_2P2" or
            logical.get("phase_a_reads") != 16 or
            logical.get("phase_b_reads") != 16):
        reasons.append("cell 5.1b two-read logical receipt is missing or stale")
    else:
        hashes = logical.get("sources")
        for relative in SOURCES[:2]:
            path = root / relative
            if (not isinstance(hashes, dict) or not path.is_file() or
                    hashes.get(relative) != _sha(path)):
                reasons.append(f"cell 5.1b source changed: {relative}")
    for relative in SOURCES:
        if not (root / relative).is_file():
            reasons.append(f"digital source missing: {relative}")
    base = root / DESIGN / "config.json"
    try:
        config = json.loads(base.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    if not isinstance(config, dict) or config.get("DESIGN_NAME") != TOP:
        reasons.append("OpenLane base config missing or wrong top module")
    flow = _flow() if require_tool else None
    if require_tool and not flow:
        reasons.append("OpenLane 1 flow.tcl not executable via PATH, OPENLANE_ROOT or OPENLANE_FLOW_TCL")
    return {
        "status": "READY_DIGITAL_ONLY" if not reasons else "BLOCKED",
        "reasons": reasons,
        "flow_tcl": flow,
        "scope": "synthesized ideal 2+2 RTL only; no passive core, analog wires, sense/ADC or PVT",
    }


def _config_contents(root: Path) -> str:
    base = json.loads((root / DESIGN / "config.json").read_text(encoding="utf-8"))
    # Do not carry any mixed-signal macro view into this digital-only run.
    for key in ("VERILOG_FILES_BLACKBOX", "EXTRA_LEFS", "EXTRA_GDS_FILES",
                "EXTRA_LIBS", "MACRO_PLACEMENT_CFG"):
        base.pop(key, None)
    base["VERILOG_FILES"] = [f"dir::../../{source}" for source in SOURCES]
    base["FP_SIZING"] = "absolute"
    base["DIE_AREA"] = "0 0 1200 1200"  # Exploratory, not a wrapper floorplan.
    base["FP_CORE_UTIL"] = 30
    return json.dumps(base, indent=2) + "\n"


def _prepare_config(root: Path) -> Path:
    path = root / CONFIG
    contents = _config_contents(root)
    if path.exists() and path.read_text(encoding="utf-8") != contents:
        raise FileExistsError(f"refusing to overwrite a different digital-only config: {path}")
    if not path.exists():
        path.write_text(contents, encoding="utf-8")
    return path


def _completed_gds(root: Path, tag: str, reasons: list[str]) -> Path | None:
    run_dir = root / DESIGN / "runs" / tag
    final = run_dir / "results/final/gds" / f"{TOP}.gds"
    if not final.is_file() or not final.stat().st_size:
        reasons.append("OpenLane final digital-only GDS missing or empty")
        return None
    metrics = run_dir / "reports/metrics.csv"
    try:
        with metrics.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1 or str(rows[0].get("flow_status", "")).lower().replace(" ", "_") != "flow_completed":
            reasons.append("OpenLane metrics do not report flow_completed")
    except (OSError, ValueError, csv.Error) as error:
        reasons.append(f"OpenLane metrics missing or invalid: {error}")
    try:
        structures = _gds_structures(final)
        if TOP not in structures:
            reasons.append("final GDS lacks controller top structure")
        if "automx_ternary_cim_4x4_core" in structures or "adc_top" in structures:
            reasons.append("digital-only GDS unexpectedly contains analog macro")
    except (OSError, UnicodeError, ValueError) as error:
        reasons.append(f"invalid digital-only GDS: {error}")
    return final


def _check_manual_source_age(root: Path, tag: str, reasons: list[str]) -> None:
    """Reject an old manual GDS when current RTL/config postdates synthesis.

    A manual run has no cryptographic input snapshot. This is a conservative
    freshness check, not proof that current files were the exact run inputs.
    """
    synthesis = root / DESIGN / "runs" / tag / "logs/synthesis/1-synthesis.log"
    if not synthesis.is_file():
        reasons.append("OpenLane synthesis log missing; manual input provenance unavailable")
        return
    synthesis_mtime = synthesis.stat().st_mtime_ns
    for relative in (*SOURCES, str(CONFIG)):
        source = root / relative
        if source.is_file() and source.stat().st_mtime_ns > synthesis_mtime:
            reasons.append(f"digital input changed after OpenLane synthesis: {relative}")


def run(root: str | Path, *, execute: bool = False,
        audit_existing: bool = False, tag: str = "stage8_digital_surrogate",
        timeout_s: int = 7200) -> dict:
    root = Path(root).resolve()
    if execute and audit_existing:
        raise ValueError("execute and audit_existing are mutually exclusive")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", tag) or timeout_s <= 0:
        raise ValueError("safe tag and positive timeout_s required")
    check = inspect(root, require_tool=execute)
    report = {
        "format": "automx-cim-stage8-digital-surrogate-gds-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": check["status"] if not (execute or audit_existing) else "BLOCKED",
        "scope": check["scope"], "reasons": list(check["reasons"]),
        "excluded_blocks": ["passive_core", "precharge", "signed_pwm", "sample_hold",
                            "sense_adc", "reference_calibration"],
        "tag": tag, "audit_existing": audit_existing,
        "flow_returncode": None, "flow_log": None,
        "final_gds": None, "final_gds_sha256": None,
    }
    if execute and not report["reasons"]:
        run_dir = root / DESIGN / "runs" / tag
        if run_dir.exists():
            raise FileExistsError(f"refusing to reuse OpenLane tag: {run_dir}")
        config = _prepare_config(root)
        source_hashes = {name: _sha(root / name) for name in SOURCES}
        log = root / "build/stage8_digital_surrogate" / tag / "openlane.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        command = [check["flow_tcl"], "-design", str(root / DESIGN),
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
        report.update(flow_returncode=code, flow_log=str(log.relative_to(root)),
                      config_sha256=_sha(config),
                      logical_receipt_sha256=_sha(root / LOGICAL_RECEIPT),
                      source_sha256=source_hashes)
        if any(_sha(root / name) != digest for name, digest in source_hashes.items()):
            report["reasons"].append("digital RTL changed while OpenLane was running")
        if code == 0:
            final = _completed_gds(root, tag, report["reasons"])
            if final is not None and not report["reasons"]:
                report["status"] = "DIGITAL_SURROGATE_GDS_UNVERIFIED"
                report["final_gds"] = str(final.relative_to(root))
                report["final_gds_sha256"] = _sha(final)
        elif code is not None:
            report["reasons"].append("OpenLane failed or produced no nonempty final GDS")
        if report["status"] != "DIGITAL_SURROGATE_GDS_UNVERIFIED":
            report["status"] = "FAIL"
    if audit_existing:
        config = root / CONFIG
        try:
            if not config.is_file() or config.read_text(encoding="utf-8") != _config_contents(root):
                report["reasons"].append("digital-only config missing or differs from generated input")
        except (OSError, ValueError, KeyError) as error:
            report["reasons"].append(f"digital-only config invalid: {error}")
        if not (root / DESIGN / "runs" / tag).is_dir():
            report["reasons"].append("OpenLane run tag does not exist")
        else:
            _check_manual_source_age(root, tag, report["reasons"])
        if not report["reasons"]:
            final = _completed_gds(root, tag, report["reasons"])
            if final is not None and not report["reasons"]:
                report.update(status="DIGITAL_SURROGATE_GDS_UNVERIFIED",
                              final_gds=str(final.relative_to(root)),
                              final_gds_sha256=_sha(final), config_sha256=_sha(config),
                              logical_receipt_sha256=_sha(root / LOGICAL_RECEIPT),
                              current_source_sha256={name: _sha(root / name) for name in SOURCES},
                              source_provenance="filesystem_mtime_only_unverified")
    receipt = root / RECEIPT
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--audit-existing", action="store_true",
                      help="verify a completed Docker OpenLane run without rerunning it")
    parser.add_argument("--tag", default="stage8_digital_surrogate")
    parser.add_argument("--timeout-s", type=int, default=7200)
    args = parser.parse_args()
    result = run(args.root, execute=args.run, audit_existing=args.audit_existing,
                 tag=args.tag, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2))
    if (args.run or args.audit_existing) and result["status"] != "DIGITAL_SURROGATE_GDS_UNVERIFIED":
        raise SystemExit(1)
