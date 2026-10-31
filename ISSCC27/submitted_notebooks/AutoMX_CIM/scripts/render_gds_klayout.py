"""Render the core-bound top GDS with KLayout's hidden GUI view.

For KLayout 0.26.2, run with
`xvfb-run -a klayout -z -x -r scripts/render_gds_klayout.py` on Linux.
AUTOMX_GDS and AUTOMX_PNG must be absolute paths in that environment.
"""

import os
from pathlib import Path

import pya


gds = Path(os.environ["AUTOMX_GDS"])
png = Path(os.environ["AUTOMX_PNG"])
if not gds.is_file() or gds.stat().st_size == 0:
    raise RuntimeError("GDS missing or empty: " + str(gds))
png.parent.mkdir(parents=True, exist_ok=True)

application = pya.Application.instance()
window = application.main_window()
if window is None:
    raise RuntimeError("KLayout image export requires -z with a display; -b is unsupported")
window.load_layout(str(gds), 1)
view = window.current_view()
if view is None:
    raise RuntimeError("KLayout did not create a layout view for " + str(gds))
cellview = view.active_cellview()
layout = cellview.layout()
top = layout.cell("automx_cim_core_bound_demo")
if top is None:
    raise RuntimeError("Top cell automx_cim_core_bound_demo missing from " + str(gds))
box = top.dbbox()
if box.empty():
    raise RuntimeError("Top cell has no layout geometry in " + str(gds))

cellview.cell = top
view.add_missing_layers()
view.max_hier()
view.show_all_cells()
margin = 0.02 * max(box.width(), box.height())
view.zoom_box(pya.DBox(box.left - margin, box.bottom - margin,
                       box.right + margin, box.top + margin))
view.save_image(str(png), 2400, 2400)
if not png.is_file() or png.stat().st_size == 0:
    raise RuntimeError("KLayout did not produce a PNG: " + str(png))
with png.open("rb") as image:
    if image.read(8) != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("KLayout output is not a PNG: " + str(png))
print("Rendered " + str(png))
