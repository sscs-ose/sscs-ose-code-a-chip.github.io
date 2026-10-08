"""Render a GDS to PNG with KLayout in batch mode.
usage: klayout -zz -r render_gds.py -rd gds=<in.gds> -rd png=<out.png> [-rd px=2000]
SPDX-License-Identifier: Apache-2.0
"""
import pya  # noqa: F401  (provided by KLayout)

gds = globals()["gds"]; png = globals()["png"]; px = int(globals().get("px", "2000"))
lv = pya.LayoutView()
lv.set_config("background-color", "#ffffff")
lv.set_config("grid-visible", "false")
lv.set_config("text-visible", "false")
lv.load_layout(gds, 0)
lv.max_hier()
# sky130: show wells/diff/poly/li/met1..met5 with KLayout's default palette,
# hide fill/marker layers so the placement stays readable.
# Optional -rd layers=68/20,69/20,... keeps only those layer/datatype pairs.
keep = {tuple(map(int, x.split("/"))) for x in globals().get("layers", "").split(",") if x}
# metal 1-5 in the colours of figures/layout_zoom.png (scripts/layout_zoom_figure.py)
METAL = {(68, 20): 0x2a78d6, (69, 20): 0xeda100, (70, 20): 0x4a3aa7, (71, 20): 0x898781, (72, 20): 0xc3c2b7}
it = lv.begin_layers()
while not it.at_end():
    p = it.current()
    hide = ((p.source_layer, p.source_datatype) not in keep) if keep else         (p.source_layer in (81, 235, 236) or p.source_datatype in (4, 5, 16))
    if hide:
        p.visible = False
        lv.set_layer_properties(it, p)
    elif (p.source_layer, p.source_datatype) in METAL:
        c = METAL[(p.source_layer, p.source_datatype)]
        p.fill_color, p.frame_color, p.dither_pattern = c, c, 2
        lv.set_layer_properties(it, p)
    it.next()
lv.zoom_fit()
lv.save_image(png, px, px)
print("wrote", png)
