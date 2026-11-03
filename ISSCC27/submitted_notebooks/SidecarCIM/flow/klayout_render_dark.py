# klayout -b -r klayout_render_dark.py -rd gds=... -rd lyp=... -rd out=<prefix>
# Dark-background renders of a final layout: no text labels, fill / decap / tap
# cells hidden. Writes <out>_dark.png (whole die) and <out>_dark_z<k>.png
# (80 um crops at a few positions across the core).
import re
import pya

gds, lyp, out = gds, lyp, out  # noqa: F821  (-rd variables)
W = 2400


def view():
    lv = pya.LayoutView()
    lv.load_layout(gds, True)
    lv.load_layer_props(lyp)
    lv.max_hier()
    lv.set_config("background-color", "#000000")
    lv.set_config("text-visible", "false")
    lv.set_config("grid-visible", "false")
    lv.set_config("grid-show-ruler", "false")
    cv = lv.active_cellview()
    ly = cv.layout()
    for ci in ly.each_cell():
        if re.search(r"__(fill|decap|tap|tapvpwr)|fill_|decap_|tap_", ci.name) \
                and ci.name != cv.cell.name:
            lv.hide_cell(ci.cell_index(), 0)
    it = lv.begin_layers()
    while not it.at_end():
        n = (it.current().name or "").lower()
        if "fill" in n or "text" in n or "label" in n:
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


lv, cv = view()
save(lv, out + "_dark.png")
bb = cv.cell.dbbox()
for k, (fx, fy) in enumerate(((0.25, 0.25), (0.5, 0.5), (0.75, 0.75),
                              (0.25, 0.75), (0.75, 0.25))):
    cx, cy = bb.left + bb.width() * fx, bb.bottom + bb.height() * fy
    save(lv, out + "_dark_z%d.png" % k, pya.DBox(cx - 40, cy - 40, cx + 40, cy + 40))
