"""KLayout batch script that records basic facts about the generated GDSII."""

from __future__ import annotations

import json

import pya


layout = pya.Layout()
layout.read(in_gds)  # noqa: F821 - supplied by KLayout through -rd

top_cells = list(layout.top_cells())
if len(top_cells) != 1:
    raise RuntimeError(f"expected one top cell, found {len(top_cells)}")

top = top_cells[0]
bbox = top.bbox()
dbu = layout.dbu
summary = {
    "top_cell": top.name,
    "cell_count": layout.cells(),
    "layer_count": len(list(layout.layer_indexes())),
    "dbu_microns": dbu,
    "bbox_microns": {
        "left": bbox.left * dbu,
        "bottom": bbox.bottom * dbu,
        "right": bbox.right * dbu,
        "top": bbox.top * dbu,
    },
}

with open(out_json, "w", encoding="utf-8") as handle:  # noqa: F821
    json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
