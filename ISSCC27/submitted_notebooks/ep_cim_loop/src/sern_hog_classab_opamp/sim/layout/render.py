#!/usr/bin/env python3
"""GDS → PNG (KLayout LayoutView, 화면 없이). 사용: render.py <gds> <png> [폭px]"""
import sys
import klayout.lay as lay, klayout.db as db
COL = {(64, 20): 0x80c080, (65, 20): 0x40a040, (65, 44): 0x206020, (66, 20): 0xd03030, (66, 13): 0xff9900,
       (67, 20): 0x9090ff, (68, 20): 0x3060ff, (69, 20): 0xc040c0, (70, 20): 0x00b0b0, (71, 20): 0xb0b000,
       (89, 44): 0x705000, (86, 20): 0xffcc00}
v = lay.LayoutView()
v.load_layout(sys.argv[1], True)
v.max_hier()
it = v.begin_layers()
while not it.at_end():
    lp = it.current()
    key = (lp.source_layer, lp.source_datatype)
    if key in COL:
        lp.fill_color = lp.frame_color = COL[key]; lp.dither_pattern = 1 if key[0] < 69 else 3; lp.visible = True
    else:
        lp.visible = False
    v.set_layer_properties(it, lp)
    it.next()
v.set_config("background-color", "#ffffff")
v.zoom_fit()
w = int(sys.argv[3]) if len(sys.argv) > 3 else 700
bb = v.active_cellview().cell.dbbox()
h = int(w * bb.height() / bb.width())
v.save_image(sys.argv[2], w, h)
print("wrote", sys.argv[2], w, h)
