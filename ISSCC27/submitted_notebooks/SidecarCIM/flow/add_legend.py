#!/usr/bin/env python3
"""add_legend.py in.png out.png legend.txt [title] : black strip with colour legend + um scale note under the render."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
img = plt.imread(sys.argv[1])
fig = plt.figure(figsize=(8, 8.5), dpi=300, facecolor="black")
ax = fig.add_axes([0, 0.05, 1, 0.95])
ax.imshow(img)
ax.axis("off")
ax2 = fig.add_axes([0, 0, 1, 0.05])
ax2.set_facecolor("black")
ax2.axis("off")
ax2.set_xlim(0, 1)
ax2.set_ylim(0, 1)
items = [l.strip().split("|") for l in open(sys.argv[3])]
items = [i for i in items if i[0] != "other" or len(sys.argv) > 5]
x = 0.03
for k, lab, rgb in items:
    ax2.add_patch(Rectangle((x, 0.35), 0.025, 0.3, fc="#" + rgb, ec="none"))
    ax2.text(x + 0.032, 0.5, lab, color="white", fontsize=8, va="center")
    x += 0.30
if len(sys.argv) > 4:
    ax2.text(0.99, 0.12, sys.argv[4], color="#999999", fontsize=5.5, va="bottom", ha="right")
fig.savefig(sys.argv[2], facecolor="black")
print("wrote", sys.argv[2])
