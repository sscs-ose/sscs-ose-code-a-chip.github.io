#!/usr/bin/env python3
"""Signoff table and images of the current layout blocks: build/<N>bit/layout -> results/<N>bit/layout."""

import json
import shutil
import sys
from pathlib import Path

BLOCKS = [("cdac_unit", "CDAC unit cell (MIM cap + its own switches)"),
          ("cdac_unit_2x3", "unit-cell abutment test (2 x 3)"),
          ("cdacu{n}b", "{n}-bit CDAC (common-centroid, dummy-cap ring)"),
          ("strongarm", "StrongARM comparator"),
          ("topsw", "top-plate sampling switch (guard rings)"),
          ("sar_logic", "SAR logic (LibreLane, sky130_fd_sc_hd)"),
          ("sar{n}b_core", "{n}-bit SAR ADC core (all blocks routed)")]


def main(n=4):
    src, dst = Path(f"build/{n}bit/layout"), Path(f"results/{n}bit/layout")
    dst.mkdir(parents=True, exist_ok=True)
    md = ["| block | size [um] | area [um^2] | KLayout DRC (incl. capm.10) | magic DRC | LVS |", "|---|---|---|---|---|---|"]
    for cell, label in BLOCKS:
        cell, label = cell.format(n=n), label.format(n=n)
        j = src / f"{cell}.json"
        if not j.exists():
            continue
        d = json.loads(j.read_text())
        w, h = d.get("width", 0), d.get("height", 0)
        lvs = d.get("lvs", {})
        md.append(f"| {label} | {w:.2f} x {h:.2f} | {w * h:.0f} | {d.get('drc_klayout', {}).get('total', '-')} | "
                  f"{d.get('drc_magic', {}).get('total', '-')} | "
                  f"{'match' if lvs.get('match') else 'FAIL'} ({'/'.join(lvs.get('devices', []))} {'block instances' if cell.endswith('_core') else 'devices'}) |")
        for ext in (".png", ".gds"):
            if (src / f"{cell}{ext}").exists():
                shutil.copy2(src / f"{cell}{ext}", dst / f"{cell}{ext}")
    (dst / "signoff.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
