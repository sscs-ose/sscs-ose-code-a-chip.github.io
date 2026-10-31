# klayout -b -r klayout_full.py -rd gds=.. -rd out=<png> [-rd cells=<cells.txt> -rd legend=<legend.txt>]
# Black-background full-chip render: only met1..met5 (+ vias), stipple + transparency, fill/decap/tap removed.
# Optional module overlay: cells.txt lines "x0 y0 x1 y1 class" (um) drawn as translucent boxes; legend.txt "class|label|rgb".
import re
import pya

gds, out = gds, out  # noqa: F821
try:
    cells
except NameError:
    cells = None
try:
    legend
except NameError:
    legend = None
W = 2400
ly = pya.Layout()
ly.read(gds)
top = ly.top_cell()
for inst in list(top.each_inst()):
    if re.search(r"fill_|decap_|tap_|tapvpwr", inst.cell.name):
        inst.delete()
SRC = [("met1", 68, 20, 0x2A50C8, 1), ("met2", 69, 20, 0xA040A8, 1), ("met3", 70, 20, 0x18A0A0, 1),
       ("met4", 71, 20, 0xC07818, 1), ("met5", 72, 20, 0xC0A818, 1)]
ly2 = pya.Layout()
ly2.dbu = ly.dbu
t2 = ly2.create_cell("TOP")
bb = top.bbox()
lv = pya.LayoutView()
lv.show_layout(ly2, False)
lv.set_config("background-color", "#000000")
lv.set_config("grid-visible", "false")
lv.set_config("text-visible", "false")
lv.set_config("cell-box-visible", "false")
n = 1
props = []
for name, l, d, rgb, _ in SRC:
    li = ly.find_layer(l, d)
    if li is None:
        continue
    r = pya.Region(top.begin_shapes_rec(li))
    r.merge()
    i2 = ly2.layer(n, 0)
    t2.shapes(i2).insert(r)
    props.append((n, rgb))
    n += 1
# die outline
i2 = ly2.layer(99, 0)
t2.shapes(i2).insert(pya.Path([pya.Point(bb.left, bb.bottom), pya.Point(bb.right, bb.bottom), pya.Point(bb.right, bb.top), pya.Point(bb.left, bb.top), pya.Point(bb.left, bb.bottom)], int(1.5 / ly.dbu)))
if cells:
    cols = {}
    if legend:
        for l in open(legend):
            k, lab, rgb = l.strip().split("|")
            cols[k] = int(rgb, 16)
    li = {}
    for k in cols:
        li[k] = ly2.layer(100 + len(li), 0)
    for l in open(cells):
        p = l.split()
        if len(p) < 5 or p[4] not in li:
            continue
        x0, y0, x1, y1 = [int(float(v) / ly.dbu) for v in p[:4]]
        t2.shapes(li[p[4]]).insert(pya.Box(x0, y0, x1, y1))
lv.clear_layers()


def addlayer(src, rgb, dither, transparent=True, frame=None):
    lp = pya.LayerProperties()
    lp.source = src
    lp.fill_color = 0xFF000000 | rgb
    lp.frame_color = 0xFF000000 | (rgb if frame is None else frame)
    lp.dither_pattern = dither
    lp.transparent = transparent
    lp.width = 0
    lp.visible = True
    lv.insert_layer(lv.end_layers(), lp)


for k, rgb in props:
    addlayer("%d/0@1" % k, rgb, 6 if not cells else 6)
if cells:
    for k, (key, rgb) in enumerate(cols.items()):
        addlayer("%d/0@1" % (100 + k), rgb, 4, True, rgb)
addlayer("99/0@1", 0x909090, 0, False)
lv.max_hier()
lv.resize(W, W)
lv.zoom_fit()
lv.save_image(out, W, W)
print("wrote", out)
