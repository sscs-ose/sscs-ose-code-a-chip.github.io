#!/usr/bin/env python3
"""Extract and LVS-check the D/G/S precharge leaf against a body-tied PFET.

This is an electrical diagnostic for one device. Passing it would not prove
the complete readout slice, sampler, ADC, timing or mixed-signal wrapper.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as leaf  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

OUTPUT = Path("results/sky130/flow2_periphery_leaf")


def reference_spice(*, guarded: bool = False) -> str:
    """Four-terminal guarded leaf exposes B; its parent ties B and S to VPWR."""
    if guarded:
        return ("* One 1.68 um PFET. Parent readout ties S and B to VPWR.\n"
                f".subckt {leaf.CELL} D G S B\n"
                "XPRE D G S B sky130_fd_pr__pfet_01v8 W=1.68 L=0.15\n"
                f".ends {leaf.CELL}\n")
    return (f"* One 1.68 um precharge PFET; S and body are VPWR in the slice.\n"
            f".subckt {leaf.CELL} D G S\n"
            "XPRE D G S S sky130_fd_pr__pfet_01v8 W=1.68 L=0.15\n"
            f".ends {leaf.CELL}\n")


def _read_verified_leaf(root: Path, tag: str, *, guarded: bool = False) -> tuple[dict, Path]:
    folder = root / OUTPUT / tag
    audit_path = folder / "view_audit.json"
    if not audit_path.is_file():
        raise FileNotFoundError(f"validated leaf view audit is missing: {audit_path}")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected_pins = leaf.GUARDED_PINS if guarded else leaf.LEAF_PINS
    if (audit.get("status") != "DRC_PASS_PRECHARGE_LEAF_ONLY" or
            audit.get("tag") != tag or audit.get("cell") != leaf.CELL or
            (guarded and audit.get("format") !=
             "automx-cim-flow2-precharge-leaf-layout-guarded-v1") or
            audit.get("magic_returncode") != 0 or
            audit.get("magic_drc_violations") != 0 or
            audit.get("gds_structure_present") is not True or
            set(audit.get("lef_pins", [])) != expected_pins):
        raise ValueError("precharge leaf view audit is not a DRC-zero pin-matched result")
    source_receipt = folder / "receipt.json"
    log = root / audit["log"]
    if (not source_receipt.is_file() or
            campaign._sha(source_receipt) != audit.get("source_receipt_sha256") or
            not log.is_file() or campaign._sha(log) != audit.get("magic_log_sha256")):
        raise ValueError("precharge leaf source receipt or Magic log changed")
    paths = {}
    for key in ("gds", "lef"):
        item = audit.get(key)
        path = (root / item["path"]).resolve() if isinstance(item, dict) else None
        if (path is None or not path.is_relative_to(root) or not path.is_file() or
                campaign._sha(path) != item.get("sha256")):
            raise ValueError(f"precharge leaf {key.upper()} hash mismatch")
        paths[key] = path
    hierarchy = leaf._gds_hierarchy(paths["gds"])
    _, _, pins = leaf._leaf_lef(paths["lef"], expected_pins)
    if leaf.CELL not in hierarchy or pins != expected_pins:
        raise ValueError("precharge leaf GDS/LEF interface changed")
    return audit, paths["gds"]


def _marker_extract(text: str) -> bool:
    return f"AUTOMX_PRECHARGE_LVS_EXTRACT_DONE={leaf.CELL}" in text


def _netgen_match(text: str) -> bool:
    low = text.lower()
    return ("match uniquely" in low or "circuits match" in low) and "not equivalent" not in low


def _netgen_compare(netgen: str, extracted: Path, reference: Path, setup: Path,
                    build: Path, folder: Path, root: Path, timeout_s: int,
                    report: dict, *, suffix: str = "") -> None:
    log = folder / f"electrical_netgen{suffix}.log"
    result = stage5._run(
        [netgen, "-batch", "lvs", f"{extracted} {leaf.CELL}",
         f"{reference} {leaf.CELL}", str(setup), str(log)], build, timeout_s)
    output = (log.read_text(encoding="utf-8", errors="replace")
              if log.is_file() else result.stdout + result.stderr)
    if not log.is_file():
        log.write_text(output, encoding="utf-8")
    report["netgen_log"] = {"path": str(log.relative_to(root)).replace("\\", "/"),
                            "sha256": campaign._sha(log)}
    report["netgen_returncode"] = result.returncode
    report["netgen_match"] = _netgen_match(output)
    if "Strange token in ext:" in output or "netgen::readnet" in output:
        report["status"] = "BLOCKED_NETGEN_PARSE"
    elif result.returncode == 0 and report["netgen_match"]:
        report["status"] = "LVS_PASS_PRECHARGE_LEAF_ONLY"
    else:
        report["status"] = "BLOCKED_LVS_MISMATCH"


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "precharge_leaf_20261017_01", execute: bool = False,
        recheck_netgen: bool = False, guarded: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if (not leaf.TAG_RE.fullmatch(tag) or timeout_s <= 0 or
            (execute and recheck_netgen) or (guarded and recheck_netgen)):
        raise ValueError("invalid tag or timeout")
    audit, gds = _read_verified_leaf(root, tag, guarded=guarded)
    expected_pins = leaf.GUARDED_PINS if guarded else leaf.LEAF_PINS
    pdk = leaf._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    setup = pdk / "libs.tech/netgen/sky130A_setup.tcl" if pdk else None
    magic, netgen = stage5._find_tool("magic"), stage5._find_tool("netgen")
    reasons = []
    if not tech or not tech.is_file() or campaign._sha(tech) != audit.get("magic_technology_sha256"):
        reasons.append("Magic technology is missing or differs from the leaf layout run")
    if not setup or not setup.is_file():
        reasons.append("SKY130A Netgen setup is missing")
    if not magic:
        reasons.append("Magic executable is missing")
    if not netgen:
        reasons.append("Netgen executable is missing")
    folder = root / OUTPUT / tag
    result_path = folder / "electrical_lvs.json"
    report = {
        "format": ("automx-cim-flow2-precharge-leaf-lvs-guarded-v1" if guarded
                   else "automx-cim-flow2-precharge-leaf-lvs-v1"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": ("one precharge PFET, D/G/S/B interface; parent ties S and B to VPWR"
                  if guarded else "one precharge PFET, D/G/S interface; reference ties bulk to S=VPWR"),
        "tag": tag,
        "cell": leaf.CELL,
        "view_audit_sha256": campaign._sha(folder / "view_audit.json"),
        "gds_sha256": campaign._sha(gds),
        "reference_sha256": sha256(reference_spice(guarded=guarded).encode()).hexdigest(),
        "pdk_root": str(pdk) if pdk else None,
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "netgen_setup_sha256": campaign._sha(setup) if setup and setup.is_file() else None,
        "magic_executable": magic,
        "netgen_executable": netgen,
        "missing_prerequisites": reasons,
        "not_signoff": "one PFET LVS only; no hold capacitor, transmission gate, ADC, wrapper PEX/timing/PVT",
    }
    if reasons or (not execute and not recheck_netgen):
        return report
    build = root / "build/flow2_periphery_leaf" / tag / "electrical_lvs"
    reference = build / f"{leaf.CELL}.reference.spice"
    if recheck_netgen:
        if not result_path.is_file():
            raise FileNotFoundError(f"existing LVS receipt is required: {result_path}")
        previous = json.loads(result_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "cell", "view_audit_sha256", "gds_sha256",
                    "reference_sha256", "magic_technology_sha256", "netgen_setup_sha256"):
            if previous.get(key) != report[key]:
                raise FileExistsError(f"existing LVS receipt differs: {result_path}")
        raw_item = previous.get("extracted_spice", {})
        original = (root / raw_item.get("path", "")).resolve()
        if (not original.is_relative_to(build) or not original.is_file() or
                campaign._sha(original) != raw_item.get("sha256") or
                not reference.is_file() or campaign._sha(reference) != report["reference_sha256"]):
            raise ValueError("existing extracted/reference SPICE differs from LVS receipt")
        corrected = build / f"{leaf.CELL}.lvs.spice"
        if corrected.is_file() and campaign._sha(corrected) != campaign._sha(original):
            raise FileExistsError(f"corrected LVS input differs: {corrected}")
        if not corrected.is_file():
            shutil.copy2(original, corrected)
        recheck_path = folder / "electrical_lvs_recheck.json"
        if recheck_path.is_file():
            saved = json.loads(recheck_path.read_text(encoding="utf-8"))
            if (saved.get("source_lvs_receipt_sha256") != campaign._sha(result_path) or
                    saved.get("renamed_extracted_sha256") != campaign._sha(corrected)):
                raise FileExistsError(f"existing Netgen recheck differs: {recheck_path}")
            return saved
        checked = {**report,
                   "format": "automx-cim-flow2-precharge-leaf-lvs-recheck-v1",
                   "source_lvs_receipt_sha256": campaign._sha(result_path),
                   "renamed_extracted_path": str(corrected.relative_to(root)).replace("\\", "/"),
                   "renamed_extracted_sha256": campaign._sha(corrected)}
        _netgen_compare(netgen, corrected, reference, setup, build, folder,
                        root, timeout_s, checked, suffix="_recheck")
        campaign._save(recheck_path, checked)
        return checked
    if result_path.is_file():
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "cell", "view_audit_sha256", "gds_sha256",
                    "reference_sha256", "magic_technology_sha256", "netgen_setup_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"existing LVS receipt differs: {result_path}")
        for key in ("extract_log", "netgen_log"):
            value = saved.get(key)
            if value:
                path = root / value["path"]
                if not path.is_file() or campaign._sha(path) != value["sha256"]:
                    raise FileExistsError(f"LVS log differs from receipt: {path}")
        return saved
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted LVS build needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    reference.write_bytes(reference_spice(guarded=guarded).encode("utf-8"))
    # Netgen 1.5.133 interprets a basename containing '.ext' as Magic .ext,
    # even when the final suffix is '.spice'. Use the Stage-5 naming pattern.
    extracted = build / f"{leaf.CELL}.lvs.spice"
    tcl = ("crashbackups stop\n"
           f"gds read {{{gds.as_posix()}}}\n"
           f"load {leaf.CELL}\n"
           "select top cell\nextract do local\nextract all\n"
           "ext2spice lvs\next2spice scale off\next2spice subcircuit on\n"
           f"ext2spice -o {extracted.name}\n"
           f"puts \"AUTOMX_PRECHARGE_LVS_EXTRACT_DONE={leaf.CELL}\"\n"
           "quit -noprompt\n")
    magic_result = stage5._magic(magic, tech, build, tcl, timeout_s)
    extract_log = folder / "electrical_extract.log"
    extract_log.write_text(magic_result.stdout + magic_result.stderr, encoding="utf-8")
    report["extract_log"] = {"path": str(extract_log.relative_to(root)).replace("\\", "/"),
                             "sha256": campaign._sha(extract_log)}
    report["magic_returncode"] = magic_result.returncode
    if (magic_result.returncode or not _marker_extract(magic_result.stdout + magic_result.stderr)
            or not extracted.is_file() or not extracted.stat().st_size):
        report["status"] = "BLOCKED_MAGIC_EXTRACTION"
    else:
        try:
            pins = stage5.parse_spice_subckt_pins(extracted, leaf.CELL)
            device_count = stage5._spice_device_count(
                extracted, leaf.CELL, "sky130_fd_pr__pfet_01v8")
        except (OSError, ValueError) as error:
            report["status"] = "BLOCKED_EXTRACTED_INTERFACE"
            report["error"] = str(error)
        else:
            report["extracted_pins"] = list(pins)
            report["extracted_pfet_count"] = device_count
            report["extracted_spice"] = {"path": str(extracted.relative_to(root)).replace("\\", "/"),
                                         "sha256": campaign._sha(extracted)}
            if set(pins) != expected_pins or len(pins) != len(expected_pins) or device_count != 1:
                report["status"] = "BLOCKED_EXTRACTED_INTERFACE"
            else:
                _netgen_compare(netgen, extracted, reference, setup, build,
                                folder, root, timeout_s, report)
    campaign._save(result_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default="precharge_leaf_20261017_01")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--recheck-netgen", action="store_true",
                        help="compare an existing extraction under a Netgen-safe filename")
    parser.add_argument("--guarded", action="store_true",
                        help="check four-terminal D/G/S/B guarded leaf; use a new tag")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         execute=args.run, recheck_netgen=args.recheck_netgen,
                         guarded=args.guarded,
                         timeout_s=args.timeout_s), indent=2))
