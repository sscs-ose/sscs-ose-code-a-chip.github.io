#!/usr/bin/env python3
"""주석 그림에서 '떠 있어 보인' 곳 확대 — li1·컨택·비아까지 그려 실제 연결을 보인다.
(a) vbnc 핀 (casn 게이트)  (b) vbp 레인 (Iref 두 행 + Ipbias 게이트)  (c) s1_out 레인 위끝 (pls 게이트)
사용: ../.venv/bin/python fig_zoom_pins.py → out/zoom_pins.png"""
import json, os
import klayout.db as kdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, Patch
from matplotlib.collections import PatchCollection

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
MAROON = "#500000"
LAY = [((65, 20), "diff", "#5aa05a", 0.45), ((66, 20), "poly", "#c43c3c", 0.55), ((67, 20), "li1", "#40b0e0", 0.55),
       ((66, 44), "licon", "#202020", 0.9), ((67, 44), "mcon", "#202020", 0.9), ((68, 20), "met1", "#3060c8", 0.30),
       ((68, 44), "via1", "#000000", 1.0), ((69, 20), "met2", "#a050b0", 0.45)]

ly = kdb.Layout(); ly.read(os.path.join(HERE, "out", "hog.gds")); top = ly.cell("hog")
shapes = {}
for li in ly.layer_indexes():
    info = ly.get_info(li); key = (info.layer, info.datatype)
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        s = it.shape()
        if s.is_box() or s.is_polygon():
            b = s.dbbox().transformed(it.dtrans()); shapes.setdefault(key, []).append((b.left, b.bottom, b.width(), b.height()))
        it.next()
d = json.load(open(os.path.join(HERE, "out", "hog.json")))
sp = d["spans"]


def panel(ax, win, title, marks):
    for key, name, col, a in LAY:
        ps = [Rectangle((x, y), w, h) for x, y, w, h in shapes.get(key, [])
              if x < win[2] and x + w > win[0] and y < win[3] and y + h > win[1]]
        ax.add_collection(PatchCollection(ps, facecolor=col, edgecolor="none", alpha=a))
    for (x, y, t, dx, dy) in marks:
        ax.annotate(t, xy=(x, y), xytext=(x + dx, y + dy), fontsize=12, color=MAROON, weight="bold",
                    arrowprops=dict(arrowstyle="-|>", color=MAROON, lw=1.6))
    ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3]); ax.set_aspect("equal"); ax.set_title(title, fontsize=13.5, loc="left")
    ax.set_xticks([]); ax.set_yticks([])


fig, axs = plt.subplots(1, 3, figsize=(16, 7.2), dpi=130, gridspec_kw=dict(width_ratios=[1, 1.15, 1]))
yv = sum(sp["vbnc"]) / 2
panel(axs[0], (-4.3, yv - 3.2, 1.0, yv + 1.6), "(a) 빨간 원 = vbnc 핀 (casn 캐스코드 게이트)",
      [(-3.3, yv, "via1 + met2 = 핀", -0.6, -2.4), (-2.3, yv, "li1 띠", 0.0, 1.0), (-1.0, yv - 1.2, "casn 게이트 (poly)", 0.5, -1.6)])
yb = sp["vbp"]
panel(axs[1], (-4.3, yb[0] - 1.0, 2.0, yb[1] + 1.0), "(b) 왼쪽 긴 노란 선 = vbp 레인 (Iref·Ipbias 게이트)",
      [(-3.3, yb[0] + 0.18, "Iref 행 a 게이트", 0.9, 0.9), (-3.3, (yb[0] + yb[1]) / 2 - 1.3, "Iref 행 b 게이트", 0.9, 0.9), (-3.3, yb[1] - 0.18, "Ipbias 게이트", 0.9, -1.2)])
ys = sp["s1_out"][1]
panel(axs[2], (-1.5, ys - 4.2, 4.3, ys + 1.0), "(c) 오른쪽 위 노란 선 = s1_out 레인 위끝",
      [(1.5, ys - 0.18, "pls 게이트 (li1 → via1)", -2.6, -2.2)])
fig.legend(handles=[Patch(fc=c, alpha=min(1, a + 0.2), label=n) for _, n, c, a in LAY], loc="lower center", ncol=8, fontsize=11.5, frameon=False)
fig.suptitle("주석 그림에서는 li1·컨택을 빼고 그려 끊긴 듯 보였던 곳 — 실제로는 게이트 버스(poly) → li1 → mcon → met1 → via1 → met2 로 이어진다 (LVS MATCH)",
             fontsize=12.5, y=0.98)
fig.tight_layout(rect=(0, 0.06, 1, 0.95))
out = os.path.join(HERE, "out", "zoom_pins.png"); fig.savefig(out, facecolor="white"); print("wrote", out)
