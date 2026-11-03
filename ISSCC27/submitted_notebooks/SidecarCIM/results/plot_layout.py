"""fig_layout: the final SidecarCIM layout (KLayout render, cells colored by
RTL module, results/gds/<SC>_modules.png) with block labels, a scale bar and
the die size from the LibreLane sign-off (results/signoff/<SC>/metrics.json).
The render is only brightened; no shape is added to the layout itself.
"""
import json
import os

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image, ImageEnhance

import plot_common as pc

HERE = os.path.dirname(os.path.abspath(__file__))
SC = "sidecarcim_top_ff_pipe_s3"
FS = 10.0


def main():
    pc.style()
    im = Image.open(os.path.join(HERE, "gds", SC + "_modules.png")).convert("RGB")
    im = im.crop((0, 0, im.width, im.width))           # the die; legend below
    im = ImageEnhance.Brightness(im).enhance(1.55)
    im = ImageEnhance.Color(im).enhance(1.35)
    met = json.load(open(os.path.join(HERE, "signoff", SC, "metrics.json")))
    x0, y0, x1, y1 = (float(v) for v in met["design__die__bbox"].split())
    W, H = x1 - x0, y1 - y0                            # um
    area = {}
    for ln in open(os.path.join(HERE, "area_breakdown.csv")):
        f = ln.strip().split(",")
        if f[0] == SC:
            area[f[1]] = float(f[3])
    # the die outline in the render (gray frame), measured on the 2400 px image
    fx0, fx1 = 78, 2322
    px_per_um = (fx1 - fx0) / W

    fig, ax = plt.subplots(figsize=(7.16, 7.6))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.995, bottom=0.075)
    ax.imshow(im)
    ax.set_axis_off()
    box = dict(boxstyle="round,pad=0.35", fc="black", ec="white", lw=0.8,
               alpha=0.82)
    ax.text(820, 1650, "Dense 4-bit array\n%.1f %% of cell area"
            % area["dense_dcim_core"], color="#9DB8FF", fontsize=FS + 3,
            ha="center", va="center", bbox=box)
    ax.text(1960, 1480, "Sidecar\n%.1f %%" % area["sidecar"],
            color="#FF8A8A", fontsize=FS + 3, ha="center", va="center",
            bbox=box)
    # scale bar, bottom left inside the frame
    L = 100 * px_per_um
    yb = 2235
    ax.plot([140, 140 + L], [yb, yb], color="white", lw=4,
            solid_capstyle="butt")
    ax.text(140 + L / 2, yb - 30, "100 µm", color="white", fontsize=FS + 1,
            ha="center", va="bottom")
    ax.text(fx1, 34, "die %.3f mm × %.3f mm" % (W / 1000, H / 1000),
            color="white", fontsize=FS, ha="right", va="center")
    h = [Patch(fc="#3d6bff", ec="none"), Patch(fc="#ff4b4b", ec="none"),
         Patch(fc="#33dd66", ec="none")]
    fig.legend(h, ["dense 4-bit array %.1f %%" % area["dense_dcim_core"],
                   "sidecar %.1f %%" % area["sidecar"],
                   "merge logic %.1f %%" % area["top_merge_logic"]],
               loc="lower center", ncol=3, frameon=False, fontsize=FS,
               handlelength=1.4, columnspacing=2.0)
    png = os.path.join(HERE, "fig_layout_tmp.png")
    fig.savefig(png, dpi=200)
    plt.close(fig)
    # JPEG: the render is noise-like and would be several MB as PNG
    Image.open(png).convert("RGB").save(os.path.join(HERE, "fig_layout.jpg"),
                                        quality=82, optimize=True, progressive=True)
    os.remove(png)
    print("wrote fig_layout", round(W, 1), round(H, 1), round(px_per_um, 3))


if __name__ == "__main__":
    main()
