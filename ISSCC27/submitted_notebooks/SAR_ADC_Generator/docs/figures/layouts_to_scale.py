"""Generated SAR ADC cores at 4/6/8 bits, drawn to one scale, 8-bit blocks labelled -> docs/layouts_to_scale.png"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread

sz = {int(k): v for k, v in json.load(open("build/figures/sizes.json")).items()}
K = 0.052                                                    # inch per micron, same for every core
W8, H8 = sz[8][:2]; W6, H6 = sz[6][:2]; W4, H4 = sz[4][:2]
mx, gap, top = 0.25, 0.75, 0.95
FW = mx + W8 * K + gap + W6 * K + mx
FH = top + max(H8 * K, H6 * K + 0.55 + H4 * K) + 0.35
fig = plt.figure(figsize=(FW, FH))

def place(b, x_in, y_in, title):
    w, h = sz[b][:2]
    ax = fig.add_axes([x_in / FW, y_in / FH, w * K / FW, h * K / FH])
    ax.imshow(imread(f"build/figures/core{b}.png"), extent=[0, w, h, 0], interpolation="lanczos")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#9aa3af")
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=6)
    return ax

base = 0.35
a8 = place(8, mx, base + (FH - top - base - H8 * K), f"8-bit core   {W8:.0f} × {H8:.0f} µm")
a6 = place(6, mx + W8 * K + gap, base + H4 * K + 0.55, f"6-bit   {W6:.0f} × {H6:.0f} µm")
a4 = place(4, mx + W8 * K + gap, base, f"4-bit   {W4:.0f} × {H4:.0f} µm")

box = dict(boxstyle="round,pad=0.35", fc="white", ec="#1d2330", lw=1, alpha=0.92)
arr = dict(arrowstyle="-|>", color="#1d2330", lw=1.4)
a8.annotate("capacitor array (CDAC)\n256 unit capacitors, ring of dummies", (53, 37), ha="center", va="center",
            fontsize=11, bbox=box)
a8.annotate("SAR logic (digital,\nstandard cells)", (139.5, 62), xytext=(139.5, 30), ha="center", fontsize=10.5,
            bbox=box, arrowprops=arr)
a8.annotate("comparator", (60, 86), xytext=(98, 84), ha="left", va="center", fontsize=10.5, bbox=box, arrowprops=arr)
a8.annotate("top-plate\nswitch", (16, 87), xytext=(26, 66), ha="center", fontsize=10.5, bbox=box, arrowprops=arr)
a8.plot([W8 - 32, W8 - 12], [H8 - 3, H8 - 3], color="#1d2330", lw=3)
a8.text(W8 - 22, H8 - 5, "20 µm", ha="center", va="bottom", fontsize=10, fontweight="bold",
        bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
fig.text(mx / FW, 1 - 0.32 / FH, "The generated SAR ADC cores, drawn to the same scale", fontsize=15, fontweight="bold")
fig.text(mx / FW, 1 - 0.58 / FH, "SKY130, placed and routed by code from PDK cells; every block and core DRC clean and LVS matched",
         fontsize=11, color="#4b5563")
fig.savefig("docs/layouts_to_scale.png", dpi=95, facecolor="white")
from PIL import Image                       # layout colours fit a small palette: ~4x smaller file
Image.open("docs/layouts_to_scale.png").convert("RGB").quantize(colors=128, dither=Image.Dither.NONE).save(
    "docs/layouts_to_scale.png", optimize=True)
print("saved", FW, FH)
