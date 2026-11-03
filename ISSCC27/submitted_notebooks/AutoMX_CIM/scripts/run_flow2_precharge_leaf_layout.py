#!/usr/bin/env python3
"""Build and DRC-check the first SKY130 precharge layout leaf on the server.

Only a one-PFET layout cell is generated. A DRC pass here is not wrapper LVS,
PEX, timing, ADC or a sign-off view for the clocked CIM macro.
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
from scripts import prepare_flow2_wrapper_layout as layout  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts.run_stage8_prototype_gds import _gds_hierarchy  # noqa: E402

CELL = "automx_cim_precharge_pfet_1p68"
RECIPE = Path("physical/sky130/wrapper_prototype/generate_precharge_leaf.tcl")
GUARDED_RECIPE = Path("physical/sky130/wrapper_prototype/generate_precharge_leaf_guarded.tcl")
OUTPUT = Path("results/sky130/flow2_periphery_leaf")
TAG_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
LEAF_PINS = {"D", "S", "G"}
GUARDED_PINS = LEAF_PINS | {"B"}


def _leaf_lef(path: Path, expected_pins: set[str] = LEAF_PINS) -> tuple[float, float, set[str]]:
    """Validate the precharge leaf, not the unrelated clocked wrapper macro."""
    content = path.read_text(encoding="utf-8", errors="replace")
    macros = re.findall(r"(?im)^[ \t]*MACRO[ \t]+([^\s]+)[ \t]*$", content)
    if macros != [CELL]:
        raise ValueError(f"LEF macro mismatch: expected {CELL}, found {macros}")
    block = re.search(rf"(?ims)^[ \t]*MACRO[ \t]+{re.escape(CELL)}[ \t]*$"
                      rf"(.*?)^[ \t]*END[ \t]+{re.escape(CELL)}[ \t]*$", content)
    if block is None:
        raise ValueError(f"LEF MACRO {CELL} has no matching END")
    sizes = re.findall(r"(?im)^[ \t]*SIZE[ \t]+([\d.]+)[ \t]+BY[ \t]+([\d.]+)[ \t]*;",
                       block.group(1))
    if len(sizes) != 1:
        raise ValueError("leaf LEF must contain exactly one SIZE")
    width, height = map(float, sizes[0])
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("invalid leaf LEF dimensions")
    pin_list = re.findall(r"(?im)^[ \t]*PIN[ \t]+([^\s]+)[ \t]*$", block.group(1))
    pins = set(pin_list)
    if len(pin_list) != len(expected_pins) or pins != expected_pins:
        raise ValueError(f"leaf LEF pins differ: expected {sorted(expected_pins)}, found {pin_list}")
    return width, height, pins


def _publish_views(root: Path, tag: str, build: Path, report: dict,
                   expected_pins: set[str] = LEAF_PINS) -> None:
    gds, lef = build / f"{CELL}.gds", build / f"{CELL}.lef"
    if any(not path.is_file() or path.stat().st_size == 0 for path in (gds, lef)):
        raise FileNotFoundError(f"leaf GDS/LEF missing or empty in {build}")
    hierarchy = _gds_hierarchy(gds)
    width, height, pins = _leaf_lef(lef, expected_pins)
    if CELL not in hierarchy:
        raise ValueError(f"GDS does not define structure {CELL}")
    view_dir = root / "physical/sky130/wrapper_prototype/leaf_cells" / tag
    for original in (gds, lef):
        target = view_dir / original.name
        if target.is_file() and campaign._sha(target) != campaign._sha(original):
            raise FileExistsError(f"leaf view changed: {target}")
    view_dir.mkdir(parents=True, exist_ok=True)
    for key, original in (("gds", gds), ("lef", lef)):
        target = view_dir / original.name
        if not target.is_file():
            shutil.copy2(original, target)
        report[key] = {"path": str(target.relative_to(root)).replace("\\", "/"),
                       "sha256": campaign._sha(target)}
    report["gds_structure_present"] = True
    report["lef_pins"] = sorted(pins)
    report["lef_size_um"] = [width, height]
    report["status"] = "DRC_PASS_PRECHARGE_LEAF_ONLY"


def _pdk(root: Path, supplied: Path | None) -> Path | None:
    if supplied is not None:
        return supplied.expanduser().resolve()
    preflight = root / "results/receipts/physical/preflight.json"
    if preflight.is_file():
        value = json.loads(preflight.read_text(encoding="utf-8")).get("pdk")
        if isinstance(value, str) and value:
            return Path(value).expanduser().resolve()
    return None


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = "precharge_leaf_01", execute: bool = False,
        audit_existing: bool = False, guarded: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if not TAG_RE.fullmatch(tag) or timeout_s <= 0 or (execute and audit_existing):
        raise ValueError("invalid leaf tag or timeout")
    source = layout.prepare(root)
    recipe = root / (GUARDED_RECIPE if guarded else RECIPE)
    expected_pins = GUARDED_PINS if guarded else LEAF_PINS
    if not recipe.is_file():
        raise FileNotFoundError(recipe)
    config = root / layout.CONFIG
    pdk = _pdk(root, Path(pdk_root) if pdk_root is not None else None)
    tech = pdk / "libs.tech/magic/sky130A.tech" if pdk else None
    magic = shutil.which("magic")
    source_ready = source["status"] == "READY_FOR_READOUT_SLICE_LAYOUT_EXPERIMENT"
    prerequisites = []
    if not source_ready:
        prerequisites.append("measured core PEX is not current")
    if not tech or not tech.is_file():
        prerequisites.append("SKY130A Magic technology is unavailable")
    if not magic:
        prerequisites.append("magic is not on PATH")
    folder = root / OUTPUT / tag
    receipt = folder / "receipt.json"
    report = {
        "format": ("automx-cim-flow2-precharge-leaf-layout-guarded-v1" if guarded
                   else "automx-cim-flow2-precharge-leaf-layout-v1"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if prerequisites else "READY_TO_RUN",
        "scope": ("one guarded 1.68 um PFET with a separate n-well B port; no sampler, ADC, wrapper or composite sign-off"
                  if guarded else "one 1.68 um PFET precharge physical leaf; no sampler, ADC, wrapper or composite sign-off"),
        "tag": tag,
        "cell": CELL,
        **({"interface_pins": sorted(expected_pins)} if guarded else {}),
        "source_manifest_sha256": campaign._sha(root / source["manifest_path"]),
        "prototype_config_sha256": campaign._sha(config),
        "layout_recipe_sha256": campaign._sha(recipe),
        "pdk_root": str(pdk) if pdk else None,
        "magic_technology_sha256": campaign._sha(tech) if tech and tech.is_file() else None,
        "magic_executable": magic,
        "missing_prerequisites": prerequisites,
        "log": str((folder / "magic_generate.log").relative_to(root)).replace("\\", "/"),
        "gds": None,
        "lef": None,
        "not_signoff": "single device DRC bring-up only; LVS/PEX and all wrapper checks remain pending",
    }
    if prerequisites or (not execute and not audit_existing):
        return report
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        for key in ("format", "cell", "tag", "source_manifest_sha256",
                    "prototype_config_sha256", "layout_recipe_sha256",
                    "magic_technology_sha256", "pdk_root"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"existing leaf receipt differs: {receipt}")
        old_log = root / saved["log"]
        if (not old_log.is_file() or
                campaign._sha(old_log) != saved.get("magic_log_sha256")):
            raise FileExistsError(f"leaf log differs from receipt: {old_log}")
        if audit_existing:
            if (saved.get("magic_returncode") != 0 or
                    saved.get("magic_drc_violations") != 0 or
                    f"AUTOMX_PRECHARGE_LEAF_DONE={CELL}" not in old_log.read_text(encoding="utf-8")):
                raise ValueError("cannot audit a leaf without completed Magic and zero DRC")
            audit = {**report, "source_receipt_sha256": campaign._sha(receipt),
                     "source_receipt_status": saved.get("status"),
                     "magic_returncode": 0, "magic_drc_violations": 0,
                     "magic_log_sha256": saved["magic_log_sha256"]}
            try:
                _publish_views(root, tag, root / "build/flow2_periphery_leaf" / tag,
                               audit, expected_pins)
            except FileNotFoundError as error:
                audit["view_error"] = str(error)
                audit["status"] = "BLOCKED_MISSING_VIEWS"
            except (OSError, ValueError, UnicodeError) as error:
                audit["view_error"] = str(error)
                audit["status"] = "BLOCKED_VIEW_INTERFACE"
            campaign._save(folder / "view_audit.json", audit)
            return audit
        if saved.get("status") == "DRC_PASS_PRECHARGE_LEAF_ONLY":
            for key in ("gds", "lef"):
                item = saved.get(key)
                path = (root / item["path"]).resolve() if isinstance(item, dict) else None
                if (path is None or not path.is_relative_to(root) or
                        not path.is_file() or campaign._sha(path) != item.get("sha256")):
                    raise FileExistsError(f"leaf {key.upper()} differs from receipt")
        return saved
    if audit_existing:
        raise FileNotFoundError(f"leaf receipt required for view audit: {receipt}")
    build = root / "build/flow2_periphery_leaf" / tag
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"nonempty interrupted leaf build needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    completed = stage5._magic(magic, tech, build,
                              recipe.read_text(encoding="utf-8"), timeout_s)
    log = folder / "magic_generate.log"
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    report["magic_returncode"] = completed.returncode
    report["magic_log_sha256"] = campaign._sha(log)
    marker = re.findall(r"(?m)^AUTOMX_PRECHARGE_LEAF_DRC=(\d+)\s*$",
                        completed.stdout + completed.stderr)
    done = f"AUTOMX_PRECHARGE_LEAF_DONE={CELL}" in completed.stdout + completed.stderr
    report["magic_drc_violations"] = int(marker[0]) if len(marker) == 1 else None
    if completed.returncode or not done or len(marker) != 1:
        report["status"] = "BLOCKED_MAGIC_GENERATION"
    elif report["magic_drc_violations"] != 0:
        report["status"] = "BLOCKED_MAGIC_DRC"
    else:
        try:
            _publish_views(root, tag, build, report, expected_pins)
        except FileNotFoundError as error:
            report["view_error"] = str(error)
            report["status"] = "BLOCKED_MISSING_VIEWS"
        except (OSError, ValueError, UnicodeError) as error:
            report["view_error"] = str(error)
            report["status"] = "BLOCKED_VIEW_INTERFACE"
    campaign._save(receipt, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default="precharge_leaf_01")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--audit-existing", action="store_true",
                        help="recheck and publish views from an existing DRC-zero run")
    parser.add_argument("--guarded", action="store_true",
                        help="draw a guarded four-terminal D/G/S/B leaf; use a new tag")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         execute=args.run, audit_existing=args.audit_existing,
                         guarded=args.guarded,
                         timeout_s=args.timeout_s), indent=2))
