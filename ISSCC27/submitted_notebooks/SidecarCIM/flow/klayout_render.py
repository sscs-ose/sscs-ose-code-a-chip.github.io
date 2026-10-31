# klayout -b -r klayout_render.py -rd gds=... -rd lyp=... -rd out=<prefix> [-rd regions=file]
# Writes <out>_full.png, <out>_nofill.png, <out>_zoom.png with the sky130A layer properties.
import re
import pya

gds, lyp, out = gds, lyp, out  # noqa: F821  (-rd variables)
W = 2400


def view(hide_fill, upper_hidden=False, text="true"):
    lv = pya.LayoutView()
    lv.load_layout(gds, True)
    lv.load_layer_props(lyp)
    lv.max_hier()
    lv.set_config("background-color", "#ffffff")
    lv.set_config("text-visible", text)
    lv.set_config("text-font", "0")
    lv.set_config("grid-visible", "false")
    lv.set_config("grid-show-ruler", "false")
    cv = lv.active_cellview()
    ly = cv.layout()
    if hide_fill:
        for ci in ly.each_cell():
            if re.search(r"__(fill|decap|tap|tapvpwr)|fill_|decap_|tap_", ci.name) and ci.name != cv.cell.name:
                lv.hide_cell(ci.cell_index(), 0)
    if upper_hidden:
        it = lv.begin_layers()
        while not it.at_end():
            n = it.current().name or ""
            if re.match(r"(met[345]|via[34]|met2\.pin)", n) or "fill" in n.lower():
                it.current().visible = False
            it.next()
    return lv, cv


def save(lv, path, box=None):
    lv.resize(W, W)
    if box:
        lv.zoom_box(box)
    else:
        lv.zoom_fit()
    lv.save_image(path, W, W)
    print("wrote", path)


lv, cv = view(False)
save(lv, out + "_full.png")
lv, cv = view(True, False, "false")
save(lv, out + "_nofill.png")
lv, cv = view(True, True, "false")
bb = cv.cell.dbbox()
# 30 um crop around 1/3 of the core
cx, cy = bb.left + bb.width() * 0.4, bb.bottom + bb.height() * 0.4
save(lv, out + "_zoom.png", pya.DBox(cx - 15, cy - 15, cx + 15, cy + 15))
