"""Attribute the full-chip registers and SRAM macros to the HSKEM blocks.

After flattening, ORFS keeps hierarchical names for flip-flops
(u_common.<block>.<register>) and for the SRAM macros, while combinational
cells get generic names. This script therefore reports, per block, the exact
flip-flop count and flip-flop cell area, and the SRAM macros it owns with their
capacity and placed area. Combinational logic is not attributed.

Only these counts are published (results/fullchip/blocks.csv); the full-chip
netlist itself is not part of the submission, because it contains a
synthesis-time test credential of the demonstration board.

usage: fullchip_blocks.py <6_final.v of the full chip> <liberty>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import collections
import csv
import gzip
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INST = re.compile(r"^\s*(\S+)\s+\\?(\S+)\s*\(")
SRAM = re.compile(r"sky130_sram_1rw_(\d+)x(\d+)")


def liberty_areas(lib: pathlib.Path) -> dict[str, float]:
    areas, cell = {}, None
    for ln in lib.read_text(errors="replace").splitlines():
        m = re.match(r'\s*cell\s*\(\s*"?([\w]+)"?\s*\)', ln)
        if m:
            cell = m.group(1)
        m = re.match(r"\s*area\s*:\s*([\d.]+)", ln)
        if m and cell and cell not in areas:
            areas[cell] = float(m.group(1))
    return areas


def macro_areas() -> dict[str, float]:
    """Placed area of each SRAM master, from the committed full-chip cell table."""
    out = {}
    with gzip.open(ROOT / "results/fullchip/cells.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            if r["is_macro"] == "1":
                out[r["master"]] = (float(r["x1"]) - float(r["x0"])) * (float(r["y1"]) - float(r["y0"]))
    return out


def main() -> None:
    netlist, lib = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    area, marea = liberty_areas(lib), macro_areas()
    rows = collections.defaultdict(lambda: collections.Counter())
    for ln in netlist.open(errors="replace"):
        m = INST.match(ln)
        if not m or not m.group(2).startswith("u_common."):
            continue
        master, name = m.group(1), m.group(2)
        parts = name.split(".")
        block = re.sub(r"\[.*", "", parts[1]) if len(parts) > 2 else "(top-level registers)"
        s = SRAM.match(master)
        if s:
            rows[block]["sram_macros"] += 1
            rows[block]["sram_bits"] += int(s.group(1)) * int(s.group(2))
            rows[block]["sram_area_um2"] += marea[master]
        elif re.match(r"sky130_fd_sc_hd__(df|edf|sdf|dl)", master):     # flip-flops and latches
            rows[block]["flops"] += 1
            rows[block]["flop_area_um2"] += area[master]
    out = ROOT / "results/fullchip/blocks.csv"
    cols = ["flops", "flop_area_um2", "sram_macros", "sram_bits", "sram_area_um2"]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block"] + cols)
        for b, c in sorted(rows.items(), key=lambda kv: -kv[1]["flops"]):
            w.writerow([b] + [round(c[k], 2) for k in cols])
    print(out.read_text())


if __name__ == "__main__":
    main()
