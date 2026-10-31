#!/usr/bin/env python3
"""Extract a PEX view from the verified SKY130 MIM3 hold-cap leaf GDS.

The result covers one capacitor leaf. It does not measure held-node retention
or certify the sampler, ADC or composite mixed-signal wrapper.
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
from scripts import run_flow2_hold_cap_leaf as leaf  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as precharge  # noqa: E402
from scripts import run_flow2_precharge_leaf_pex as precharge_pex  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

FORMAT = "automx-cim-flow2-hold-cap-mim3-pex-v1"
PINS = ("HOLD", "VGND")
DEFAULT_SOURCE_TAG = "hold_cap_mim3_20261017_02"
DEFAULT_TAG = "hold_cap_pex_20261017_01"


def _item(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": campaign._sha(path)}


def _verified_file(root: Path, item: object, name: str) -> Path:
    if not isinstance(item, dict) or not isinstance(item.get("path"), str):
        raise ValueError(f"leaf {name} is absent from the DRC/LVS receipt")
    path = (root / item["path"]).resolve()
    if (not path.is_relative_to(root) or not path.is_file() or
            campaign._sha(path) != item.get("sha256")):
        raise ValueError(f"leaf {name} file or SHA-256 differs")
    return path


def _source(root: Path, tag: str) -> tuple[Path, Path, dict]:
    receipt_path = root / leaf.OUTPUT / tag / "hold_cap_leaf.json"
    if not receipt_path.is_file():
        raise FileNotFoundError(f"hold-cap DRC/LVS receipt is required: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("format") != leaf.FORMAT or
            receipt.get("status") != "DRC_LVS_PASS_HOLD_CAP_LEAF_ONLY" or
            receipt.get("tag") != tag or receipt.get("cell") != leaf.CELL or
            receipt.get("recipe_sha256") != campaign._sha(root / leaf.RECIPE) or
            receipt.get("config_sha256") != campaign._sha(root / leaf.CONFIG) or
            receipt.get("magic_returncode") != 0 or
            receipt.get("magic_drc_violations") != 0 or
            receipt.get("klayout_returncode") != 0 or
            receipt.get("klayout_violations") != 0 or
            receipt.get("extract_returncode") != 0 or
            receipt.get("extracted_mim_device_count") != 1 or
            receipt.get("netgen_returncode") != 0 or
            receipt.get("netgen_match") is not True or
            set(receipt.get("extracted_pins", [])) != set(PINS)):
        raise ValueError("current, passing two-pin hold-cap DRC/LVS is required")
    files = {key: _verified_file(root, receipt.get(key), key) for key in
             ("gds", "lef", "magic_log", "klayout_log", "klayout_report",
              "extract_log", "reference_spice", "extracted_spice", "netgen_log")}
    if leaf._pins_from_lef(files["lef"]) != set(PINS):
        raise ValueError("published hold-cap LEF no longer has HOLD/VGND")
    if stage5.parse_spice_subckt_pins(files["extracted_spice"], leaf.CELL) != PINS:
        raise ValueError("published hold-cap LVS SPICE pin order changed")
    if files["reference_spice"].read_text(encoding="utf-8") != leaf.reference_spice():
        raise ValueError("hold-cap schematic reference changed")
    return files["gds"], receipt_path, receipt


def _canonicalize(raw: Path, output: Path) -> tuple[str, ...]:
    name = f"{leaf.CELL}_pex"
    actual = stage5.parse_spice_subckt_pins(raw, name)
    if len(actual) != 2 or set(actual) != set(PINS):
        raise ValueError(f"hold-cap PEX pin contract differs: {actual}")
    source = raw.read_text(encoding="utf-8")
    source, changed = re.subn(
        rf"(?im)^(\s*\.subckt\s+){re.escape(name)}(?=\s)",
        lambda match: match.group(1) + f"{name}_raw", source, count=1)
    if changed != 1:
        raise ValueError("hold-cap PEX top subcircuit is absent")
    source = re.sub(rf"(?im)^(\s*\.ends\s+){re.escape(name)}(?=\s|$)",
                    lambda match: match.group(1) + f"{name}_raw", source, count=1)
    source = re.sub(r"(?im)^\s*\.end\s*$", "", source)
    wrapper = (f"\n* Ordered HOLD VGND interface for the MIM3 hold leaf.\n"
               f".subckt {name} {' '.join(PINS)}\n"
               f"XPEX_RAW {' '.join(actual)} {name}_raw\n"
               f".ends {name}\n")
    output.write_text(source.rstrip() + "\n" + wrapper, encoding="utf-8")
    return actual


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        source_tag: str = DEFAULT_SOURCE_TAG, tag: str = DEFAULT_TAG,
        execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if (not precharge.TAG_RE.fullmatch(source_tag) or
            not precharge.TAG_RE.fullmatch(tag) or timeout_s <= 0 or
            source_tag == tag):
        raise ValueError("invalid hold-cap source/run tags or timeout")
    gds, lvs_path, lvs_receipt = _source(root, source_tag)
    pdk = precharge._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    magic = stage5._find_tool("magic")
    reasons = []
    if (not tech or not tech.is_file() or
            campaign._sha(tech) != lvs_receipt["magic_technology_sha256"]):
        reasons.append("Magic technology differs from the DRC/LVS run")
    if not magic:
        reasons.append("Magic executable is missing")
    folder = root / leaf.OUTPUT / tag
    receipt_path = folder / "hold_cap_pex.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": "one verified SKY130 MIM3 hold capacitor; RC extraction from published GDS",
        "tag": tag,
        "source_tag": source_tag,
        "cell": leaf.CELL,
        "gds_sha256": campaign._sha(gds),
        "lvs_receipt_sha256": campaign._sha(lvs_path),
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "script_sha256": campaign._sha(Path(__file__)),
        "magic_executable": magic,
        "missing_prerequisites": reasons,
        "not_signoff": "leaf PEX only; effective capacitance, retention, sampler, ADC, wrapper and PVT remain unmeasured",
    }
    if reasons or not execute:
        return report
    if receipt_path.is_file():
        saved = json.loads(receipt_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "source_tag", "cell", "gds_sha256", "lvs_receipt_sha256",
                    "magic_technology_sha256", "script_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"hold-cap PEX input changed; use a new tag: {receipt_path}")
        for key in ("magic_log", "raw_pex", "pex"):
            if saved.get(key):
                _verified_file(root, saved[key], key)
        return saved
    folder.mkdir(parents=True, exist_ok=True)
    build = root / "build/flow2_periphery_leaf" / tag / "hold_cap_pex"
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted hold-cap PEX build needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    raw = build / f"{leaf.CELL}.pex.raw.spice"
    canonical = build / f"{leaf.CELL}.pex.spice"
    name = f"{leaf.CELL}_pex"
    tcl = ("crashbackups stop\n"
           f"gds read {{{gds.as_posix()}}}\n"
           f"load {leaf.CELL}\nselect top cell\n"
           f"flatten {name}\nload {name}\nselect top cell\n"
           "extract do local\nextract do unique\nextract do resistance\n"
           "extresist threshold 100\nextresist mindelay 0\nextresist minres 10\n"
           "extract all\nputs \"AUTOMX_HOLD_CAP_PEX_EXTRACT_DONE\"\n"
           "ext2spice lvs\next2spice scale off\next2spice cthresh 0.1\n"
           "ext2spice extresist on\next2spice short resistor\n"
           "ext2spice subcircuit on\next2spice subcircuit top on\n"
           f"ext2spice -o {raw.name}\n"
           "puts \"AUTOMX_HOLD_CAP_PEX_DONE\"\nquit -noprompt\n")
    result = stage5._magic(magic, tech, build, tcl, timeout_s)
    log = folder / "hold_cap_pex_magic.log"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    report["magic_log"] = _item(root, log)
    report["magic_returncode"] = result.returncode
    output = result.stdout + result.stderr
    report["rc_nets_output"] = sum(int(n) for n in re.findall(
        r"(?m)^Nets output:\s*(\d+)", output))
    if (result.returncode or "AUTOMX_HOLD_CAP_PEX_EXTRACT_DONE" not in output or
            "AUTOMX_HOLD_CAP_PEX_DONE" not in output or
            not raw.is_file() or not raw.stat().st_size):
        report["status"] = "BLOCKED_MAGIC_PEX"
    else:
        report["raw_pex"] = _item(root, raw)
        try:
            actual = _canonicalize(raw, canonical)
            count = leaf._extracted_capacitor_count(raw)
            parasitics = precharge_pex._parasitic_counts(raw)
            if count != 1:
                raise ValueError(f"expected one MIM3 device in PEX, found {count}")
            report["raw_pins"] = list(actual)
            report["extracted_mim_device_count"] = count
            report["parasitic_elements"] = parasitics
            published = (root / "physical/sky130/wrapper_prototype/leaf_cells" /
                         tag / f"{leaf.CELL}.pex.spice")
            published.parent.mkdir(parents=True, exist_ok=True)
            if published.is_file() and campaign._sha(published) != campaign._sha(canonical):
                raise FileExistsError(f"published hold-cap PEX differs: {published}")
            if not published.is_file():
                shutil.copy2(canonical, published)
            report["pex"] = _item(root, published)
            report["status"] = ("MEASURED_HOLD_CAP_LEAF_PEX_ONLY"
                                if sum(parasitics.values()) else
                                "EXTRACTED_HOLD_CAP_DEVICE_NO_ADDITIONAL_RC")
        except (OSError, ValueError) as error:
            report["status"] = "BLOCKED_PEX_INTERFACE_OR_PARASITICS"
            report["error"] = str(error)
    campaign._save(receipt_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--source-tag", default=DEFAULT_SOURCE_TAG)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root,
                         source_tag=args.source_tag, tag=args.tag,
                         execute=args.run, timeout_s=args.timeout_s), indent=2))
