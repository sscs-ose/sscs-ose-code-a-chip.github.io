"""Key frames of a zoom into the signed-off GDS, from the whole die down to standard cells of the NTT engine.
usage: klayout -zz -r render_zoom_frames.py -rd gds=<in.gds> -rd out=<dir> -rd x=<um> -rd y=<um>
SPDX-License-Identifier: Apache-2.0
"""
import pya  # noqa: F401  (provided by KLayout)

gds, out = globals()["gds"], globals()["out"]
cx, cy = float(globals()["x"]), float(globals()["y"])
N, W, H, DIE, END = 16, 2560, 1440, 3351.0, 14.0
lv = pya.LayoutView()
lv.set_config("background-color", "#101014")
lv.set_config("grid-visible", "false")
lv.set_config("text-visible", "false")
lv.load_layout(gds, 0)
lv.max_hier()
HIDE = {81, 235, 236, 64, 78, 93, 94, 122, 125}   # markers and the well and implant layers, which would cover the die
METAL = {(68, 20): 0x2a78d6, (69, 20): 0xeda100, (70, 20): 0x8a7be0, (71, 20): 0x9a9890, (72, 20): 0xc9c8bd}
it = lv.begin_layers()
while not it.at_end():
    p = it.current()
    if p.source_layer in HIDE or p.source_datatype not in (20, 44, 0):
        p.visible = False
        lv.set_layer_properties(it, p)
    elif (p.source_layer, p.source_datatype) in METAL:
        c = METAL[(p.source_layer, p.source_datatype)]
        p.fill_color, p.frame_color, p.dither_pattern = c, c, 2
        lv.set_layer_properties(it, p)
    it.next()
for k in range(N):
    h = DIE * 1.05 * (END / (DIE * 1.05)) ** (k / (N - 1))
    w = h * W / H
    px = cx + (DIE / 2 - cx) * h / (DIE * 1.05)      # a fixed point of the zoom, so that key frames overlap
    py = cy + (DIE / 2 - cy) * h / (DIE * 1.05)
    lv.zoom_box(pya.DBox(px - w / 2, py - h / 2, px + w / 2, py + h / 2))
    lv.save_image(f"{out}/k{k:02d}.png", W, H)
    print("frame", k, round(h, 1), flush=True)
