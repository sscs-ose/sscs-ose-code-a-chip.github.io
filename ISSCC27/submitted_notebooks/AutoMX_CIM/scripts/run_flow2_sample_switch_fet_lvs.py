#!/usr/bin/env python3
"""Extract and Netgen-check each guarded sampler FET against its schematic.

Passing this check proves two isolated D/G/S/B leaves only. The connected
transmission gate, body ties and wrapper need separate composite extraction.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as precharge  # noqa: E402
from scripts import run_flow2_sample_switch_fet_leaves as leaves  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

FORMAT = "automx-cim-flow2-sample-switch-fet-lvs-v1"


def reference_spice(kind: str) -> str:
    if kind not in leaves.CELLS:
        raise ValueError("unknown sampler FET")
    cell = leaves.CELLS[kind]
    return (f"* One guarded 3.36-um {kind}; parent must wire body B.\n"
            f".subckt {cell} D G S B\n"
            f"XSW D G S B sky130_fd_pr__{kind}_01v8 W=3.36 L=0.15\n"
            f".ends {cell}\n")


def _verified_layout(root: Path, tag: str) -> tuple[dict, Path]:
    path = root / leaves.OUTPUT / tag / "sample_fet_layout.json"
    if not path.is_file():
        raise FileNotFoundError(f"sampler leaf layout receipt missing: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if (report.get("format") != leaves.FORMAT or report.get("tag") != tag or
            report.get("status") != "DRC_PASS_SAMPLE_FET_LEAVES_ONLY" or
            set(report.get("leaves", {})) != set(leaves.CELLS)):
        raise ValueError("both sampler leaves must have zero-DRC GDS/LEF views")
    expected = {"config_sha256": campaign._sha(root / leaves.CONFIG),
                "recipe_sha256": campaign._sha(root / leaves.RECIPE),
                "script_sha256": campaign._sha(root / "scripts/run_flow2_sample_switch_fet_leaves.py")}
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("sampler layout inputs changed")
    for kind, cell in leaves.CELLS.items():
        item = report["leaves"][kind]
        if (item.get("status") != "DRC_PASS_SAMPLE_FET_LEAF_ONLY" or
                item.get("cell") != cell or item.get("magic_returncode") != 0 or
                item.get("magic_drc_violations") != 0 or
                set(item.get("pins", [])) != leaves.PINS):
            raise ValueError(f"{kind} DRC/port contract is incomplete")
        for key in ("log", "gds", "lef"):
            entry = item.get(key)
            if not isinstance(entry, dict):
                raise ValueError(f"{kind} {key} is absent")
            source = (root / entry.get("path", "")).resolve()
            if (not source.is_relative_to(root) or not source.is_file() or
                    campaign._sha(source) != entry.get("sha256")):
                raise ValueError(f"{kind} {key} changed")
        gds = root / item["gds"]["path"]
        lef = root / item["lef"]["path"]
        if cell not in leaves._gds_hierarchy(gds) or set(leaves._lef_interface(lef, cell)["pins"]) != leaves.PINS:
            raise ValueError(f"{kind} GDS/LEF no longer match")
    return report, path


def _netgen_match(log: str) -> bool:
    low = log.lower()
    return (("match uniquely" in low or "circuits match" in low) and
            "not equivalent" not in low and "strange token" not in low)


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "sample_fet_20261017_01", execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not precharge.TAG_RE.fullmatch(tag) or timeout_s <= 0:
        raise ValueError("invalid sampler tag or timeout")
    layout, layout_path = _verified_layout(root, tag)
    pdk = precharge._pdk(root, Path(pdk_root) if pdk_root else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    setup = pdk / "libs.tech/netgen/sky130A_setup.tcl" if pdk else None
    magic, netgen = stage5._find_tool("magic"), stage5._find_tool("netgen")
    missing = []
    if not tech or not tech.is_file() or campaign._sha(tech) != layout.get("magic_technology_sha256"):
        missing.append("Magic technology missing or differs from layout run")
    if not setup or not setup.is_file():
        missing.append("SKY130A Netgen setup missing")
    if not magic:
        missing.append("Magic executable missing")
    if not netgen:
        missing.append("Netgen executable missing")
    folder = root / leaves.OUTPUT / tag
    receipt = folder / "sample_fet_lvs.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if missing else "READY_TO_RUN",
        "tag": tag,
        "scope": "two isolated guarded 3.36-um sampler transistors, D/G/S/B",
        "layout_receipt_sha256": campaign._sha(layout_path),
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "netgen_setup_sha256": campaign._sha(setup) if setup and setup.is_file() else None,
        "script_sha256": campaign._sha(Path(__file__)),
        "pdk_root": str(pdk) if pdk else None,
        "missing_prerequisites": missing,
        "leaves": {},
        "not_signoff": "isolated FET LVS only; no connected TG, S/B/VSUBS integration, physical driver, ADC, composite PEX or wrapper",
    }
    if missing or not execute:
        return report
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        for key in ("format", "tag", "layout_receipt_sha256", "magic_technology_sha256",
                    "netgen_setup_sha256", "script_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"sampler LVS inputs changed: {receipt}")
        for item in saved.get("leaves", {}).values():
            for key in ("reference", "extracted", "extract_log", "netgen_log"):
                entry = item.get(key)
                if entry:
                    source = (root / entry["path"]).resolve()
                    if (not source.is_relative_to(root) or not source.is_file() or
                            campaign._sha(source) != entry["sha256"]):
                        raise FileExistsError(f"sampler LVS {key} differs: {source}")
        return saved
    for kind, cell in leaves.CELLS.items():
        build = root / "build/flow2_periphery_leaf" / tag / f"{kind}_lvs"
        if build.exists() and any(build.iterdir()):
            raise FileExistsError(f"interrupted {kind} LVS needs inspection: {build}")
        build.mkdir(parents=True, exist_ok=True)
        source_gds = root / layout["leaves"][kind]["gds"]["path"]
        reference = build / f"{cell}.reference.spice"
        reference.write_text(reference_spice(kind), encoding="utf-8")
        extracted = build / f"{cell}.lvs.spice"
        tcl = ("crashbackups stop\n"
               f"gds read {{{source_gds.as_posix()}}}\n"
               f"load {cell}\nselect top cell\nextract do local\nextract all\n"
               "ext2spice lvs\next2spice scale off\next2spice subcircuit on\n"
               f"ext2spice -o {extracted.name}\n"
               f"puts \"AUTOMX_SAMPLE_FET_EXTRACT_DONE={cell}\"\n"
               "quit -noprompt\n")
        observed = stage5._magic(magic, tech, build, tcl, timeout_s)
        extract_log = folder / f"{kind}_extract.log"
        extract_log.write_text(observed.stdout + observed.stderr, encoding="utf-8")
        item = {"cell": cell, "kind": kind,
                "reference": leaves._item(root, reference),
                "extract_log": leaves._item(root, extract_log),
                "magic_returncode": observed.returncode}
        report["leaves"][kind] = item
        if (observed.returncode != 0 or
                f"AUTOMX_SAMPLE_FET_EXTRACT_DONE={cell}" not in observed.stdout + observed.stderr or
                not extracted.is_file() or extracted.stat().st_size == 0):
            item["status"] = "BLOCKED_MAGIC_EXTRACTION"
            continue
        item["extracted"] = leaves._item(root, extracted)
        try:
            pins = stage5.parse_spice_subckt_pins(extracted, cell)
            count = stage5._spice_device_count(extracted, cell, f"sky130_fd_pr__{kind}_01v8")
        except (OSError, ValueError) as error:
            item["status"] = "BLOCKED_EXTRACTED_INTERFACE"
            item["error"] = str(error)
            continue
        item["extracted_pins"] = list(pins)
        item["extracted_device_count"] = count
        if len(pins) != 4 or set(pins) != leaves.PINS or count != 1:
            item["status"] = "BLOCKED_EXTRACTED_INTERFACE"
            continue
        netgen_log = folder / f"{kind}_netgen.log"
        compared = stage5._run(
            [netgen, "-batch", "lvs", f"{extracted} {cell}",
             f"{reference} {cell}", str(setup), str(netgen_log)], build, timeout_s)
        log = (netgen_log.read_text(encoding="utf-8", errors="replace")
               if netgen_log.is_file() else compared.stdout + compared.stderr)
        if not netgen_log.is_file():
            netgen_log.write_text(log, encoding="utf-8")
        item["netgen_log"] = leaves._item(root, netgen_log)
        item["netgen_returncode"] = compared.returncode
        item["netgen_match"] = _netgen_match(log)
        item["status"] = ("LVS_PASS_SAMPLE_FET_LEAF_ONLY" if
                          compared.returncode == 0 and item["netgen_match"] else
                          "BLOCKED_LVS_MISMATCH")
    report["status"] = ("LVS_PASS_SAMPLE_FET_LEAVES_ONLY" if
                        len(report["leaves"]) == 2 and
                        all(item["status"] == "LVS_PASS_SAMPLE_FET_LEAF_ONLY"
                            for item in report["leaves"].values()) else
                        "BLOCKED_SAMPLE_FET_LEAF_LVS")
    campaign._save(receipt, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default="sample_fet_20261017_01")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         execute=args.run, timeout_s=args.timeout_s), indent=2))
