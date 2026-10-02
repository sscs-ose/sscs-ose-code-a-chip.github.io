"""The routed macro-store NTT at three scales, rendered from its released GDS with KLayout.

(a) the whole block, (b) the edge of the SRAM macro with the address-pin buffers of Appendix B.4,
(c) a few standard cells at transistor scale. Writes figures/layout_zoom.png and figures/pdf/layout_zoom.pdf.
usage: python3 scripts/layout_zoom_figure.py [gds]   (needs the klayout Python module)
SPDX-License-Identifier: Apache-2.0
"""
import pathlib
import sys

import klayout.db as db
import klayout.lay as lay
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plotstyle as ps  # noqa: E402

GDS = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "results/asic/ntt_opt_pipe_macro_20ns/6_final.gds")
TMP = pathlib.Path("/tmp/layout_zoom"); TMP.mkdir(exist_ok=True)

# SKY130 layer/datatype -> colour, drawn bottom-up
NWELL, DIFF, POLY, LICON, LI1, MCON, MET1, VIA, MET2, VIA2, MET3, MET4 = (
    (64, 20), (65, 20), (66, 20), (66, 44), (67, 20), (67, 44), (68, 20), (68, 44), (69, 20), (69, 44),
    (70, 20), (71, 20))
COL = {NWELL: "#efe9d8", DIFF: "#1baf7a", POLY: "#e34948", LICON: "#0b0b0b", LI1: "#e87ba4", MCON: "#0b0b0b",
       MET1: "#2a78d6", VIA: "#0b0b0b", MET2: "#eda100", VIA2: "#0b0b0b", MET3: "#4a3aa7", MET4: "#898781"}

lv = lay.LayoutView()
for k, v in (("background-color", "#ffffff"), ("grid-visible", "false"), ("text-visible", "false")):
    lv.set_config(k, v)
lv.load_layout(GDS, 0)
lv.max_hier()
top = lv.cellview(0).layout().top_cell()

macro, bufs, flops = None, [], []
for inst in top.each_inst():
    n, b = inst.cell.name, inst.dbbox()
    if "sky130_sram" in n:
        macro = b
    elif n.startswith("sky130_fd_sc_hd__buf_12"):
        bufs.append(b)
    elif n.startswith("sky130_fd_sc_hd__df"):
        flops.append(b)
die = top.dbbox()
assert macro is not None, "no SRAM macro in this layout"
near = [b for b in bufs if b.enlarged(25, 25).overlaps(macro)]


def render(name, box, layers, px=1400, alpha=False):
    it = lv.begin_layers()
    while not it.at_end():
        p = it.current()
        key = (p.source_layer, p.source_datatype)
        p.visible = key in layers
        if key in layers:
            c = int(COL[key][1:], 16)
            p.fill_color, p.frame_color = c, c
            p.dither_pattern = 0 if key in (NWELL, DIFF, POLY, LICON, MCON, VIA, VIA2) else 2
            p.transparent = alpha
        lv.set_layer_properties(it, p)
        it.next()
    lv.zoom_box(box)
    h = max(200, int(px * box.height() / box.width()))
    path = TMP / f"{name}.png"
    lv.save_image(str(path), px, h)
    return plt.imread(str(path))


# (b): the macro edge that faces the address-pin buffers; (c): a flip-flop and its neighbours, far from the macro
edge = [b for b in near if b.top <= macro.bottom + 1] or near
bb = edge[0].dup()
for b in edge:
    bb += b
cx, cy = bb.center().x, (bb.center().y + macro.bottom) / 2
hw = max(bb.width() / 2 + 10, 45)
box_b = db.DBox(cx - hw, cy - hw / 2.2, cx + hw, cy + hw / 2.2)
near = [b for b in near if b.overlaps(box_b)]
logic = [b for b in flops if not b.overlaps(macro.enlarged(20, 20))]
mx = sorted(b.center().x for b in logic)[len(logic) // 2]
my = sorted(b.center().y for b in logic)[len(logic) // 2]
c = min(logic, key=lambda b: (b.center() - db.DPoint(mx, my)).length()).center()
box_c = db.DBox(c.x - 9, c.y - 5.5, c.x + 9, c.y + 5.5)

img_a = render("a", die, {MET1, MET2, MET3, MET4}, px=1600)
img_b = render("b", box_b, {LI1, MET1, VIA, MET2, VIA2, MET3})
img_c = render("c", box_c, {NWELL, DIFF, POLY, LICON, LI1, MCON, MET1})

ps.apply()
fig = plt.figure(figsize=(12.5, 6.4))
gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.05], hspace=0.45, wspace=0.18)
ax_a, ax_b, ax_c = fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1])
for ax, img, box in ((ax_a, img_a, die), (ax_b, img_b, box_b), (ax_c, img_c, box_c)):
    ax.imshow(img, extent=(box.left, box.right, box.bottom, box.top), interpolation="lanczos")
    ax.set_xlabel("x [µm]"); ax.set_ylabel("y [µm]"); ax.grid(False)
ax_a.add_patch(Rectangle((macro.left, macro.bottom), macro.width(), macro.height(), fill=False,
                         ec=ps.SERIES[1], lw=2))
ax_a.annotate("SRAM macro, 16 × 256 bit", (macro.left, macro.top), xytext=(4, -4), textcoords="offset points",
              ha="left", va="top", fontsize=9, color=ps.INK,
              bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none", alpha=0.85))
for box, tag in ((box_b, "b"), (box_c, "c")):
    ax_a.add_patch(Rectangle((box.left, box.bottom), box.width(), box.height(), fill=False, ec=ps.INK, lw=1.4))
    ax_a.annotate(f"({tag})", (box.right, box.top), xytext=(3, 2), textcoords="offset points", fontsize=9)
for b in near:
    ax_b.add_patch(Rectangle((b.left, b.bottom), b.width(), b.height(), fill=False, ec=ps.CRITICAL, lw=1.6))
ax_b.add_patch(Rectangle((macro.left, macro.bottom), macro.width(), macro.height(), fill=False,
                         ec=ps.SERIES[1], lw=2))
ax_b.set_xlim(box_b.left, box_b.right); ax_b.set_ylim(box_b.bottom, box_b.top)
ax_a.set_title(f"(a) Whole block, {die.width():.0f} µm square, metal 1–4",
               fontsize=10, loc="left")
ax_b.set_title(f"(b) Bottom edge of the macro: address-pin drivers (red) at the halo",
               fontsize=10, loc="left")
ax_c.set_title("(c) Logic cells: diffusion (green), poly (red), local interconnect (pink), metal 1",
               fontsize=10, loc="left")
fig.text(0.01, 0.005, "Rendered from the released, hash-checked GDS of this design point, not an illustration. "
         "Layer colours chosen for legibility.", fontsize=8.5, color=ps.MUTED)
out = ROOT / "figures/layout_zoom.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
ps.save_pdf(fig, "layout_zoom")
print("wrote", out, "| macro", macro, "| buffers near macro:", len(near), "| die", die)
