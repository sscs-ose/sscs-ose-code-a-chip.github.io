#!/usr/bin/env python3
"""Run physical MIM3 hold-cap leaf DRC and LVS on the SKY130 server.

This is one layout component. It cannot certify the full sample/hold or ADC.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as precharge  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts.run_stage8_prototype_gds import _gds_hierarchy  # noqa: E402

CELL = "automx_cim_hold_cap_mim3_approx20ff"
RECIPE = Path("physical/sky130/wrapper_prototype/generate_hold_cap_mim3_leaf.tcl")
CONFIG = Path("configs/flow2_readout_prototype.json")
OUTPUT = Path("results/sky130/flow2_periphery_leaf")
PINS = {"HOLD", "VGND"}
FORMAT = "automx-cim-flow2-hold-cap-mim3-leaf-v1"


def reference_spice() -> str:
    return ("* MIM3 geometry candidate; extracted capacitance must be measured.\n"
            f".subckt {CELL} HOLD VGND\n"
            "XCAP HOLD VGND sky130_fd_pr__cap_mim_m3_1 W=4.20 L=4.20\n"
            f".ends {CELL}\n")


def _item(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(),
            "sha256": campaign._sha(path)}


def _pins_from_lef(path: Path) -> set[str]:
    data = path.read_text(encoding="utf-8", errors="replace")
    macros = re.findall(r"(?im)^\s*MACRO\s+(\S+)\s*$", data)
    if macros != [CELL] or not re.search(rf"(?im)^\s*END\s+{CELL}\s*$", data):
        raise ValueError("hold capacitor LEF macro differs")
    found = re.findall(r"(?im)^\s*PIN\s+(\S+)\s*$", data)
    if len(found) != 2 or set(found) != PINS:
        raise ValueError(f"hold capacitor LEF pins differ: {found}")
    return set(found)


def _netgen_match(output: str) -> bool:
    low = output.lower()
    return ("netlists match uniquely." in low and
            "cell pin lists are equivalent." in low and
            "circuits match uniquely." in low and
            "not equivalent" not in low and
            "strange token in ext:" not in low)


def _extracted_capacitor_count(path: Path) -> int:
    """Count extracted MIM devices, excluding comments and model definitions."""
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
               if line.lstrip().lower().startswith("x") and
               "sky130_fd_pr__cap_mim_m3_1" in line.lower())


def _previous(root: Path, receipt: Path, expected: dict) -> dict:
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    for key in ("format", "tag", "cell", "recipe_sha256", "config_sha256",
                "magic_technology_sha256", "netgen_setup_sha256"):
        if saved.get(key) != expected[key]:
            raise FileExistsError(f"hold-cap inputs changed; use a new tag: {receipt}")
    for key in ("magic_log", "gds", "lef", "extract_log", "extracted_spice",
                "reference_spice", "netgen_log", "klayout_log", "klayout_report"):
        item = saved.get(key)
        if item:
            path = (root / item["path"]).resolve()
            if not path.is_relative_to(root) or not path.is_file() or campaign._sha(path) != item["sha256"]:
                raise FileExistsError(f"hold-cap evidence changed: {key}")
    return saved


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "hold_cap_mim3_20261017_01", execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not precharge.TAG_RE.fullmatch(tag) or timeout_s <= 0:
        raise ValueError("invalid tag or timeout")
    recipe, config = root / RECIPE, root / CONFIG
    if not recipe.is_file() or not config.is_file():
        raise FileNotFoundError("hold-cap recipe or prototype config is missing")
    prototype = json.loads(config.read_text(encoding="utf-8"))
    if prototype["readout"]["hold_capacitance_ff"] != 20:
        raise ValueError("prototype hold-cap target changed")
    pdk = precharge._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    setup = pdk / "libs.tech/netgen/sky130A_setup.tcl" if pdk else None
    magic = stage5._find_tool("magic")
    netgen = stage5._find_tool("netgen")
    klayout = stage5._find_tool("klayout")
    reasons = []
    if not tech or not tech.is_file():
        reasons.append("SKY130A Magic technology is missing")
    if not setup or not setup.is_file():
        reasons.append("SKY130A Netgen setup is missing")
    if not magic:
        reasons.append("Magic is missing")
    if not netgen:
        reasons.append("Netgen is missing")
    if not klayout:
        reasons.append("KLayout is missing")
    folder = root / OUTPUT / tag
    receipt = folder / "hold_cap_leaf.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": "one SKY130 MIM3 physical hold capacitor candidate, not wrapper signoff",
        "tag": tag,
        "cell": CELL,
        "pin_contract": ["HOLD", "VGND"],
        "target_capacitance_ff": 20,
        "nominal_pdk_formula_ff": 4.2 * 4.2 + 2 * (4.2 + 4.2) * 0.17,
        "drawn_width_um": 4.2,
        "drawn_length_um": 4.2,
        "recipe_sha256": campaign._sha(recipe),
        "config_sha256": campaign._sha(config),
        "pdk_root": str(pdk) if pdk else None,
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "netgen_setup_sha256": campaign._sha(setup) if setup and setup.is_file() else None,
        "missing_prerequisites": reasons,
        "not_signoff": "one cap leaf only; extracted capacitance, sampler, driver, ADC, composite LVS/PEX and timing remain pending",
    }
    if reasons or not execute:
        return report
    if receipt.is_file():
        return _previous(root, receipt, report)
    build = root / "build/flow2_periphery_leaf" / tag / "hold_cap"
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted hold-cap build needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    magic_result = stage5._magic(magic, tech, build, recipe.read_text(encoding="utf-8"), timeout_s)
    text = magic_result.stdout + magic_result.stderr
    magic_log = folder / "hold_cap_magic.log"
    magic_log.write_text(text, encoding="utf-8")
    report["magic_log"] = _item(root, magic_log)
    report["magic_returncode"] = magic_result.returncode
    markers = re.findall(r"(?m)^AUTOMX_HOLD_CAP_DRC=(\d+)\s*$", text)
    report["magic_drc_violations"] = int(markers[0]) if len(markers) == 1 else None
    generated_gds, generated_lef = build / f"{CELL}.gds", build / f"{CELL}.lef"
    if (magic_result.returncode or len(markers) != 1 or
            f"AUTOMX_HOLD_CAP_DONE={CELL}" not in text or
            not generated_gds.is_file() or not generated_lef.is_file()):
        report["status"] = "BLOCKED_MAGIC_GENERATION"
    elif report["magic_drc_violations"] != 0:
        report["status"] = "BLOCKED_MAGIC_DRC"
    else:
        try:
            _pins_from_lef(generated_lef)
            if CELL not in _gds_hierarchy(generated_gds):
                raise ValueError("hold capacitor GDS structure missing")
            view_dir = root / "physical/sky130/wrapper_prototype/leaf_cells" / tag
            view_dir.mkdir(parents=True, exist_ok=True)
            for key, generated in (("gds", generated_gds), ("lef", generated_lef)):
                dest = view_dir / generated.name
                if dest.is_file() and campaign._sha(dest) != campaign._sha(generated):
                    raise FileExistsError(f"hold-cap view changed: {dest}")
                if not dest.is_file():
                    shutil.copy2(generated, dest)
                report[key] = _item(root, dest)
            report["status"] = "DRC_PASS_HOLD_CAP_LEAF_ONLY"
        except (OSError, ValueError) as error:
            report["status"] = "BLOCKED_VIEW_INTERFACE"
            report["view_error"] = str(error)

    if report["status"] == "DRC_PASS_HOLD_CAP_LEAF_ONLY":
        try:
            deck = stage5._klayout_deck(pdk)
            report["klayout_deck_sha256"] = campaign._sha(deck)
            report_xml = folder / "hold_cap_klayout.xml"
            kr = stage5._run([klayout, "-b", "-r", str(deck), "-rd",
                              f"input={generated_gds}", "-rd", f"report={report_xml}"],
                             build, timeout_s) if klayout else None
            klog = folder / "hold_cap_klayout.log"
            klog.write_text(kr.stdout + kr.stderr if kr else "KLayout unavailable\n", encoding="utf-8")
            report["klayout_log"] = _item(root, klog)
            report["klayout_returncode"] = kr.returncode if kr else None
            if report_xml.is_file():
                report["klayout_report"] = _item(root, report_xml)
                report["klayout_violations"] = len(re.findall(
                    r"<item>", report_xml.read_text(encoding="utf-8", errors="replace")))
            if not kr or kr.returncode != 0 or report.get("klayout_violations") != 0:
                report["status"] = "BLOCKED_KLAYOUT_DRC"
        except (OSError, ValueError) as error:
            report["status"] = "BLOCKED_KLAYOUT_DRC"
            report["klayout_error"] = str(error)

    if report["magic_drc_violations"] == 0 and report.get("gds"):
        reference = build / f"{CELL}.reference.spice"
        extracted = build / f"{CELL}.lvs.spice"
        reference.write_text(reference_spice(), encoding="utf-8")
        report["reference_spice"] = _item(root, reference)
        tcl = ("crashbackups stop\n"
               f"gds read {{{generated_gds.as_posix()}}}\n"
               f"load {CELL}\nselect top cell\nextract do local\nextract all\n"
               "ext2spice lvs\next2spice scale off\next2spice subcircuit on\n"
               f"ext2spice -o {extracted.name}\n"
               f"puts \"AUTOMX_HOLD_CAP_EXTRACT_DONE={CELL}\"\nquit -noprompt\n")
        er = stage5._magic(magic, tech, build, tcl, timeout_s)
        elog = folder / "hold_cap_extract.log"
        elog.write_text(er.stdout + er.stderr, encoding="utf-8")
        report["extract_log"] = _item(root, elog)
        report["extract_returncode"] = er.returncode
        if (er.returncode or f"AUTOMX_HOLD_CAP_EXTRACT_DONE={CELL}" not in er.stdout + er.stderr
                or not extracted.is_file() or not extracted.stat().st_size):
            report["status"] = "BLOCKED_MAGIC_EXTRACTION"
        else:
            report["extracted_spice"] = _item(root, extracted)
            try:
                pins = stage5.parse_spice_subckt_pins(extracted, CELL)
                if set(pins) != PINS or len(pins) != 2:
                    raise ValueError(f"extracted hold-cap pins differ: {pins}")
                cap_count = _extracted_capacitor_count(extracted)
                if cap_count != 1:
                    raise ValueError(f"expected one extracted MIM3 device, found {cap_count}")
                report["extracted_pins"] = list(pins)
                report["extracted_mim_device_count"] = cap_count
                nlog = folder / "hold_cap_netgen.log"
                nr = stage5._run([netgen, "-batch", "lvs", f"{extracted} {CELL}",
                                  f"{reference} {CELL}", str(setup), str(nlog)],
                                 build, timeout_s)
                output = nlog.read_text(encoding="utf-8", errors="replace") if nlog.is_file() else nr.stdout + nr.stderr
                if not nlog.is_file():
                    nlog.write_text(output, encoding="utf-8")
                report["netgen_log"] = _item(root, nlog)
                report["netgen_returncode"] = nr.returncode
                report["netgen_match"] = _netgen_match(output)
                if nr.returncode != 0 or not report["netgen_match"]:
                    report["status"] = "BLOCKED_LVS_MISMATCH"
                elif report["status"] == "DRC_PASS_HOLD_CAP_LEAF_ONLY":
                    report["status"] = "DRC_LVS_PASS_HOLD_CAP_LEAF_ONLY"
            except (OSError, ValueError) as error:
                report["status"] = "BLOCKED_EXTRACTED_INTERFACE"
                report["lvs_error"] = str(error)
    campaign._save(receipt, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default="hold_cap_mim3_20261017_01")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         execute=args.run, timeout_s=args.timeout_s), indent=2))
