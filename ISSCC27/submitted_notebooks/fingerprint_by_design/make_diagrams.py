"""Static explanatory figures for the notebook: signal chain, research workflow, annotated layout."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

def box(ax, x, y, w, h, text, fc, fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec="#333", lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

def arrow(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333"))

# 1. signal chain
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.set_xlim(0, 11); ax.set_ylim(0, 4.2); ax.axis("off")
C_DAC, C_LO, C_PA, C_SUP = "#cfe2ff", "#d7f5d0", "#ffd9c7", "#eee3ff"
box(ax, 0.1, 2.6, 1.4, 0.8, "data bits\n(124 lines)", "#f2f2f2")
box(ax, 1.9, 3.1, 1.6, 0.7, "I DAC\n31 current cells", C_DAC); box(ax, 1.9, 2.1, 1.6, 0.7, "Q DAC\n31 current cells", C_DAC)
box(ax, 3.9, 3.1, 1.5, 0.7, "I mixer\n(switching quad)", C_DAC); box(ax, 3.9, 2.1, 1.5, 0.7, "Q mixer\n(switching quad)", C_DAC)
box(ax, 5.8, 2.6, 1.3, 0.8, "shared load\n+ coupling", C_PA); box(ax, 7.4, 2.6, 1.3, 0.8, "PA\n(diff. pair)", C_PA)
box(ax, 9.0, 2.6, 1.4, 0.8, "output buffer\n-> 50 ohm", C_PA)
box(ax, 0.1, 0.9, 1.4, 0.8, "external LO\n200 MHz", "#f2f2f2"); box(ax, 1.9, 0.9, 1.4, 0.8, "LO input\nbuffer", C_LO)
box(ax, 3.6, 0.9, 1.3, 0.8, "RC-CR\n(I/Q split)", C_LO); box(ax, 5.2, 0.9, 1.4, 0.8, "limiters\n(inverters)", C_LO)
box(ax, 7.2, 0.15, 1.5, 0.75, "bandgap +\nbias reference", C_SUP); box(ax, 9.0, 0.15, 1.4, 0.75, "LDO\n3.3 V -> 1.8 V", C_SUP)
for (a, b) in (((1.5, 3.0), (1.9, 3.45)), ((1.5, 3.0), (1.9, 2.45)), ((3.5, 3.45), (3.9, 3.45)), ((3.5, 2.45), (3.9, 2.45)),
               ((5.4, 3.45), (5.8, 3.1)), ((5.4, 2.45), (5.8, 2.9)), ((7.1, 3.0), (7.4, 3.0)), ((8.7, 3.0), (9.0, 3.0)),
               ((1.5, 1.3), (1.9, 1.3)), ((3.3, 1.3), (3.6, 1.3)), ((4.9, 1.3), (5.2, 1.3))):
    arrow(ax, *a, *b)
arrow(ax, 5.9, 1.7, 4.65, 2.1); arrow(ax, 6.1, 1.7, 4.65, 3.1)
ax.text(5.5, 4.0, "transistor-level SKY130 transmitter core (everything except the LO source and data bits is on chip)",
        ha="center", fontsize=9, style="italic")
ax.text(9.7, 1.05, "supplies every block", ha="center", fontsize=8, color="#555")
fig.savefig("images/signal_chain.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 2. research workflow
fig, ax = plt.subplots(figsize=(11, 2.6))
ax.set_xlim(0, 11); ax.set_ylim(0, 2.6); ax.axis("off")
steps = [("1. Design + layout", "SKY130 transmitter,\nDRC / LVS / PEX", "#cfe2ff"),
         ("2. Virtual chips", "Monte Carlo mismatch:\nmany chips of one design", "#d7f5d0"),
         ("3. Fingerprint", "receiver measures each\nchip's DAC level pattern", "#ffd9c7"),
         ("4. Evaluate\npre-registered tests", "predictions and pass rules\nset before simulation", "#fff1b8"),
         ("5. Design change", "PA, DAC, LDO ...\nthen test again", "#eee3ff")]
for i, (t, s, c) in enumerate(steps):
    x = 0.1 + i * 2.18
    box(ax, x, 0.55, 1.95, 1.5, "", c)
    ax.text(x + 0.975, 1.73, t, ha="center", va="center", fontsize=9, weight="bold")
    ax.text(x + 0.975, 1.10, s, ha="center", va="center", fontsize=8)
    if i < 4:
        arrow(ax, x + 1.95, 1.3, x + 2.18, 1.3)
ax.plot([9.795, 9.795, 1.075], [0.52, 0.28, 0.28], color="#888", lw=1)
ax.annotate("", xy=(1.075, 0.52), xytext=(1.075, 0.28), arrowprops=dict(arrowstyle="->", lw=1, color="#888"))
ax.text(5.4, 0.02, "design changes go back into the loop - all before any silicon exists", ha="center", fontsize=8.5, color="#555")
fig.savefig("images/workflow.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 3. annotated layout. Boxes and labels are in layout micrometres; the render (KLayout, chip fitted to the image) is
# calibrated from its drawn-content bounding box and the chip's GDS bounding box, so the annotation follows the layout.
import gdstk
import numpy as np
img = plt.imread("images/chip_layout.png")
ys, xs = np.where((img[..., :3] < 0.97).any(axis=2))
px0, px1, py0, py1 = xs.min(), xs.max(), ys.min(), ys.max()
(X0, Y0), (X1, Y1) = gdstk.read_gds("../layout/tx_core.gds").top_level()[0].bounding_box()
(lx0, ly0), (lx1, ly1) = gdstk.read_gds("../layout/ldo_blk.gds").top_level()[0].bounding_box()
to_px = lambda x, y: (px0 + (x - X0) * (px1 - px0) / (X1 - X0), py0 + (Y1 - y) * (py1 - py0) / (Y1 - Y0))
ldo_top, ldo_w, ldo_h = -92.0, lx1 - lx0, ly1 - ly0           # placement as in tx_core._ldo_origin
fig, ax = plt.subplots(figsize=(12, 9))
ax.imshow(img); ax.axis("off")
labels = [((-78.9, 64.3, 404.8, -82.6), "transmitter core", "#1f6fd1"),
          ((-78.9, ldo_top + 2, -75.0 + ldo_w + 3.9, ldo_top - ldo_h - 3), "on-chip LDO: bandgap reference, error amplifier, "
           "5 V pass device, soft-start, decoupling", "#8a2be2")]
for (x0, y0, x1, y1), t, c in labels:
    (a0, b0), (a1, b1) = to_px(x0, y0), to_px(x1, y1)
    ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, fill=False, ec=c, lw=2.2, ls="--"))
    if b0 < 100:
        ax.text(a0 + 8, b0 - 8, t, color=c, fontsize=11, weight="bold", va="bottom")
    else:
        ax.text(a0 + 8, b1 + 10, t, color=c, fontsize=11, weight="bold", va="top")
blocks = [((-75.9, 36.1), "LO in"), ((-19.5, -35.1), "LO path\n(RC-CR + limiters)"), ((78.4, 30.2), "Q DAC + mixer"),
          ((146.6, -67.7), "I DAC + mixer"), ((102.1, -17.3), "bias ref."), ((232.7, -41.0), "output network + PA"),
          ((315.8, 42.0), "output\nbuffer")]
for (x, y), t in blocks:
    ax.text(*to_px(x, y), t, fontsize=9.5, color="black", bbox=dict(fc="white", ec="#999", alpha=0.85, pad=2))
fig.savefig("images/chip_layout_annotated.png", dpi=110, bbox_inches="tight"); plt.close(fig)
print("diagrams written")
