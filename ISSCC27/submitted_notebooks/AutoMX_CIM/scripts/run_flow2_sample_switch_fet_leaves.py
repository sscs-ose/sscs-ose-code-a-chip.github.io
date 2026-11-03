#!/usr/bin/env python3
"""Generate and Magic-DRC both guarded 3.36-um sampler transistor leaves.

These two device leaves are layout experiments. They are not a connected
transmission gate, a sampler, ADC interface or wrapper signoff.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
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

FORMAT = "automx-cim-flow2-sample-switch-fet-leaves-v1"
RECIPE = Path("physical/sky130/wrapper_prototype/generate_sample_switch_fet_leaf.tcl")
CONFIG = Path("configs/flow2_readout_prototype.json")
OUTPUT = Path("results/sky130/flow2_periphery_leaf")
CELLS = {"nfet": "automx_cim_sample_nfet_3p36",
         "pfet": "automx_cim_sample_pfet_3p36"}
PINS = {"D", "G", "S", "B"}


def _item(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(),
            "sha256": campaign._sha(path)}


def _lef_interface(path: Path, cell: str) -> dict:
    source = path.read_text(encoding="utf-8", errors="replace")
    macros = re.findall(r"(?im)^\s*MACRO\s+(\S+)\s*$", source)
    block = re.search(rf"(?ims)^\s*MACRO\s+{re.escape(cell)}\s*$"
                      rf"(.*?)^\s*END\s+{re.escape(cell)}\s*$", source)
    if macros != [cell] or block is None:
        raise ValueError("sample FET LEF macro differs")
    pins = re.findall(r"(?im)^\s*PIN\s+(\S+)\s*$", block.group(1))
    size = re.findall(r"(?im)^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;",
                      block.group(1))
    if len(pins) != 4 or set(pins) != PINS or len(size) != 1:
        raise ValueError(f"sample FET LEF pin/size contract differs: {pins}")
    width, height = map(float, size[0])
    if not all(math.isfinite(n) and n > 0 for n in (width, height)):
        raise ValueError("sample FET LEF has invalid dimensions")
    for pin in PINS:
        section = re.search(rf"(?ims)^\s*PIN\s+{pin}\s*$(.*?)^\s*END\s+{pin}\s*$",
                            block.group(1))
        if section is None or not re.search(r"(?im)^\s*LAYER\s+met1\s*;", section.group(1)):
            raise ValueError(f"sample FET {pin} has no metal1 port")
    return {"pins": sorted(pins), "size_um": [width, height]}


def _recipe_text(kind: str, cell: str, body: str) -> str:
    if kind not in CELLS or CELLS[kind] != cell:
        raise ValueError("unknown sampler FET")
    return f"set FET_KIND {kind}\nset CELL {cell}\n" + body


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "sample_fet_20261017_01", execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not precharge.TAG_RE.fullmatch(tag) or timeout_s <= 0:
        raise ValueError("invalid sampler leaf tag or timeout")
    config_path, recipe_path = root / CONFIG, root / RECIPE
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if (config.get("status") != "FROZEN_FOR_LAYOUT_EXPERIMENT_ONLY" or
            config.get("readout", {}).get("sample_switch_width_um") != 3.36):
        raise ValueError("sampler leaf does not match the frozen prototype")
    recipe = recipe_path.read_text(encoding="utf-8")
    pdk = precharge._pdk(root, Path(pdk_root) if pdk_root else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    magic = stage5._find_tool("magic")
    missing = []
    if not tech or not tech.is_file():
        missing.append("SKY130A Magic technology missing")
    if not magic:
        missing.append("Magic executable missing")
    folder = root / OUTPUT / tag
    receipt = folder / "sample_fet_layout.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if missing else "READY_TO_RUN",
        "tag": tag,
        "scope": "separate guarded 3.36-um NFET/PFET sampler device leaves",
        "config_sha256": campaign._sha(config_path),
        "recipe_sha256": campaign._sha(recipe_path),
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "script_sha256": campaign._sha(Path(__file__)),
        "pdk_root": str(pdk) if pdk else None,
        "magic_executable": magic,
        "missing_prerequisites": missing,
        "leaves": {},
        "not_signoff": "separate DRC-only transistor leaves; TG routing, leaf LVS/PEX, actual control driver, MIM integration, ADC and composite wrapper still pending",
    }
    if missing or not execute:
        return report
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        for key in ("format", "tag", "config_sha256", "recipe_sha256",
                    "magic_technology_sha256", "script_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"sample FET leaf inputs changed: {receipt}")
        for leaf in saved.get("leaves", {}).values():
            for key in ("log", "gds", "lef"):
                item = leaf.get(key)
                if item:
                    path = (root / item["path"]).resolve()
                    if (not path.is_relative_to(root) or not path.is_file() or
                            campaign._sha(path) != item["sha256"]):
                        raise FileExistsError(f"existing sample FET {key} differs: {path}")
        return saved
    folder.mkdir(parents=True, exist_ok=True)
    for kind, cell in CELLS.items():
        build = root / "build/flow2_periphery_leaf" / tag / kind
        if build.exists() and any(build.iterdir()):
            raise FileExistsError(f"interrupted sampler {kind} build: {build}")
        build.mkdir(parents=True, exist_ok=True)
        observed = stage5._magic(magic, tech, build,
                                 _recipe_text(kind, cell, recipe), timeout_s)
        log = folder / f"{kind}_magic.log"
        log.write_text(observed.stdout + observed.stderr, encoding="utf-8")
        entry = {"cell": cell, "kind": kind, "log": _item(root, log),
                 "magic_returncode": observed.returncode}
        report["leaves"][kind] = entry
        counts = re.findall(r"(?m)^AUTOMX_SAMPLE_FET_DRC=(\d+)\s*$",
                            observed.stdout + observed.stderr)
        entry["magic_drc_violations"] = int(counts[0]) if len(counts) == 1 else None
        gds, lef = build / f"{cell}.gds", build / f"{cell}.lef"
        if (observed.returncode != 0 or len(counts) != 1 or
                f"AUTOMX_SAMPLE_FET_DONE={cell}" not in observed.stdout + observed.stderr or
                not gds.is_file() or not lef.is_file()):
            entry["status"] = "BLOCKED_MAGIC_GENERATION"
            continue
        if entry["magic_drc_violations"] != 0:
            entry["status"] = "BLOCKED_MAGIC_DRC"
            continue
        try:
            interface = _lef_interface(lef, cell)
            if cell not in _gds_hierarchy(gds):
                raise ValueError("sample FET GDS structure missing")
            view_dir = root / "physical/sky130/wrapper_prototype/leaf_cells" / tag / kind
            view_dir.mkdir(parents=True, exist_ok=True)
            for key, source in (("gds", gds), ("lef", lef)):
                target = view_dir / source.name
                if target.is_file() and campaign._sha(target) != campaign._sha(source):
                    raise FileExistsError(f"sample FET view differs: {target}")
                if not target.is_file():
                    shutil.copy2(source, target)
                entry[key] = _item(root, target)
            entry.update(interface)
            entry["status"] = "DRC_PASS_SAMPLE_FET_LEAF_ONLY"
        except (OSError, ValueError) as error:
            entry["status"] = "BLOCKED_VIEW_INTERFACE"
            entry["view_error"] = str(error)
    report["status"] = ("DRC_PASS_SAMPLE_FET_LEAVES_ONLY" if
                        all(item["status"] == "DRC_PASS_SAMPLE_FET_LEAF_ONLY"
                            for item in report["leaves"].values()) and
                        len(report["leaves"]) == 2 else
                        "BLOCKED_SAMPLE_FET_LEAF_LAYOUT")
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
    print(json.dumps(run(args.root, pdk_root=args.pdk_root,
                         tag=args.tag, execute=args.run,
                         timeout_s=args.timeout_s), indent=2))
