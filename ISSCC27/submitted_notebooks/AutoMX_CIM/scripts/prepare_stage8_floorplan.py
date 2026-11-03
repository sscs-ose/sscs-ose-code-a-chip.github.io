"""Prepare a macro-bound OpenLane floorplan from the *real wrapper* LEF.

Preview is read-only. --apply updates the active placement and config only
after validating the clocked wrapper LEF. This is a floorplan candidate,
not PDN/IO/route/STA sign-off or evidence that the wrapper is implemented.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_stage8_preflight import WRAPPER

CONFIG = Path("openlane/automx_cim_tile_controller/config.json")
LEF = Path(f"physical/sky130/wrapper/{WRAPPER}.lef")
PLACEMENT = Path("openlane/automx_cim_tile_controller/macro_placement.cfg")
PROVENANCE = Path("openlane/automx_cim_tile_controller/floorplan_candidate.json")


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _lef_size_for_wrapper(path: Path) -> tuple[float, float]:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"real clocked-wrapper LEF is required: {path}")
    content = path.read_text(encoding="utf-8", errors="replace")
    block = re.search(rf"(?ims)^\s*MACRO\s+{re.escape(WRAPPER)}\s*$"
                      rf"(.*?)^\s*END\s+{re.escape(WRAPPER)}\s*$", content)
    if block is None:
        raise ValueError(f"LEF does not define MACRO {WRAPPER}")
    size = re.findall(r"(?im)^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;",
                      block.group(1))
    if len(size) != 1:
        raise ValueError("wrapper LEF must contain exactly one SIZE")
    width, height = map(float, size[0])
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("wrapper LEF SIZE must be finite and positive")
    return width, height


def plan(root: str | Path, *, halo_um: float = 20.0,
         border_um: float = 100.0, apply: bool = False) -> dict:
    """Derive candidate N-placement/die; apply only with explicit flag."""
    root = Path(root).resolve()
    if not all(math.isfinite(value) and value > 0 for value in
               (halo_um, border_um)):
        raise ValueError("positive finite halo_um and border_um required")
    lef = root / LEF
    width, height = _lef_size_for_wrapper(lef)
    config_path = root / CONFIG
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("DESIGN_NAME") != "automx_cim_tile_controller":
        raise ValueError("wrong OpenLane top-level config")
    anchor = border_um + halo_um
    # Round the die outward; retain enough room on all sides for initial
    # top-level routing. The final floorplan still requires PDN/IO review.
    die_width = math.ceil(width + 2 * anchor)
    die_height = math.ceil(height + 2 * anchor)
    die_area = f"0 0 {die_width} {die_height}"
    placement = f"macro_i {anchor:g} {anchor:g} N\n"
    result = {
        "format": "automx-cim-stage8-floorplan-candidate-v1",
        "status": "APPLIED_CANDIDATE" if apply else "PREVIEW_ONLY",
        "scope": "geometry only; PDN, pin access, routing, STA and sign-off unverified",
        "wrapper_lef": str(LEF).replace("\\", "/"),
        "wrapper_lef_sha256": _sha256(lef),
        "wrapper_size_um": {"width": width, "height": height},
        "halo_um": halo_um, "border_um": border_um,
        "placement": placement.strip(), "die_area": die_area,
        "required_review": ["power-grid connection", "pin access and top-level IO",
                            "macro halo/routing congestion", "post-route STA/DRC/LVS"],
    }
    if apply:
        placement_path = root / PLACEMENT
        placement_path.parent.mkdir(parents=True, exist_ok=True)
        # Refuse to overwrite a different manually tuned placement. Reruns
        # with identical output are safe and deterministic.
        if placement_path.exists() and placement_path.read_text(encoding="utf-8") != placement:
            raise FileExistsError(f"refusing to replace existing placement: {placement_path}")
        if config.get("MACRO_PLACEMENT_CFG") not in (None, "dir::macro_placement.cfg"):
            raise ValueError("refusing to replace manually configured MACRO_PLACEMENT_CFG")
        if config.get("DIE_AREA") not in (None, "0 0 1200 1200", die_area):
            raise ValueError("refusing to replace manually configured DIE_AREA")
        config["MACRO_PLACEMENT_CFG"] = "dir::macro_placement.cfg"
        config["DIE_AREA"] = die_area
        placement_path.write_text(placement, encoding="utf-8")
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        result["config_sha256"] = _sha256(config_path)
        result["placement_sha256"] = _sha256(placement_path)
        (root / PROVENANCE).write_text(json.dumps(result, indent=2) + "\n",
                                       encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--halo-um", type=float, default=20.0)
    parser.add_argument("--border-um", type=float, default=100.0)
    parser.add_argument("--apply", action="store_true",
                        help="write candidate placement and update OpenLane config")
    args = parser.parse_args()
    print(json.dumps(plan(args.root, halo_um=args.halo_um,
                          border_um=args.border_um, apply=args.apply), indent=2))
