"""fig_models: SidecarCIM's gain over dense W6A4 on each of the 18 models,
against the excess kurtosis of the migrated weights (python/out/predictor.json,
fit points; the split from the frozen prospective rule). Linear axis; the two
points beyond it are drawn at the edge with their values. IEEE style, drawn
at double-column print size.
"""
import json
import os

import matplotlib.pyplot as plt

import plot_common as pc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "python", "out")
FS = 9.5
LIM = 1.3
NAME = {"gpt2": "GPT-2", "qwen2.5-0.5b": "Qwen2.5-0.5B",
        "smollm2-1.7b": "SmolLM2-1.7B", "tinystories-1m": "TinyStories-1M"}


def sig(q):
    if q["p"] >= 0.05:
        return "none"
    return "gain" if q["gain_over_W6A4_ppl"] > 0 else "loss"


def main():
    pc.style()
    pred = json.load(open(os.path.join(OUT, "predictor.json")))
    pts = pred["fit"]["points"]
    split = 8.88
    for k in ("w_kurtosis_mig",):
        ps = pred.get("prospective_score", {})
        if k in ps and "threshold" in ps[k]:
            split = ps[k]["threshold"]
    above = [q for q in pts if q["w_kurtosis_mig"] > split]
    below = [q for q in pts if q["w_kurtosis_mig"] <= split]
    fig, ax = plt.subplots(figsize=(7.16, 3.3))
    fig.subplots_adjust(left=0.08, right=0.99, top=0.97, bottom=0.15)
    x_lo, x_hi = 0.15, 70
    ax.axvspan(split, x_hi, color=pc.ACC, alpha=0.10, lw=0)
    ax.axvspan(x_lo, split, color="0.5", alpha=0.08, lw=0)
    ax.axhline(0, color="0.45", lw=0.7)
    ax.axvline(split, color=pc.ACC, lw=1.0, ls="--")
    ax.text(split * 1.06, -0.30,
            "Use SidecarCIM\nbetter on %d of %d models,\nworse on none"
            % (sum(sig(q) == "gain" for q in above), len(above)),
            color=pc.ACC, fontsize=FS, va="top", fontweight="bold")
    ax.text(x_lo * 1.25, LIM * 0.93,
            "Use W6A4\nbetter on %d of %d models"
            % (sum(sig(q) == "loss" for q in below), len(below)),
            color="0.25", fontsize=FS, va="top", fontweight="bold")
    ax.text(split * 0.95, LIM * 0.93, "split %.2f" % split,
            color=pc.ACC, fontsize=FS - 1, ha="right", va="top")
    LEAD = {"gpt2": (14, 0.93), "qwen2.5-0.5b": (14, 0.72)}
    for q in pts:
        x, y = q["w_kurtosis_mig"], q["gain_over_W6A4_ppl"]
        s = sig(q)
        yc = max(-LIM * 0.94, min(LIM * 0.94, y))
        clipped = yc != y
        kw = dict(gain=dict(marker="D", ms=7, color=pc.ACC, mfc=pc.ACC),
                  loss=dict(marker="o", ms=6, color="black", mfc="black"),
                  none=dict(marker="o", ms=6, color="0.35", mfc="white"))[s]
        if clipped:
            kw["marker"] = "^" if y > 0 else "v"
            kw["ms"] = 8
        ax.plot([x], [yc], ls="none", mew=1.1, zorder=3, **kw)
        if q.get("prospective"):
            ax.plot([x], [yc], ls="none", marker="o", ms=13, mfc="none",
                    mec="0.2", mew=0.8, zorder=2)
        nm = NAME.get(q["model"])
        if nm:
            lab = "%s %+.2f" % (nm, y)
            col = pc.ACC if s == "gain" else "black"
            if q["model"] in LEAD:
                ax.annotate(lab, (x, yc), xytext=LEAD[q["model"]],
                            fontsize=FS - 0.5, color=col, va="center",
                            arrowprops=dict(arrowstyle="-", color=col,
                                            lw=0.6, shrinkB=5))
            else:
                ax.text(x * (1.1 if y > 0 else 1.5), yc - (0.1 if y > 0 else 0),
                        lab, fontsize=FS - 0.5, ha="left", va="center",
                        color=col)
    h = [ax.plot([], [], ls="none", marker="D", ms=7, color=pc.ACC)[0],
         ax.plot([], [], ls="none", marker="o", ms=6, color="0.35",
                 mfc="white")[0],
         ax.plot([], [], ls="none", marker="o", ms=6, color="black")[0],
         ax.plot([], [], ls="none", marker="o", ms=13, mfc="none",
                 mec="0.2", mew=0.8)[0]]
    ax.legend(h, ["SidecarCIM better", "no significant difference",
                  "W6A4 better", "held-out model"],
              loc="lower left", bbox_to_anchor=(0.28, 0.02), fontsize=FS - 1,
              frameon=True,
              framealpha=0.9, edgecolor="0.8", handletextpad=0.3, ncol=2)
    ax.set_xscale("log")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(-LIM, LIM)
    ax.set_xlabel("Excess kurtosis of the migrated weights (heavier tails "
                  "to the right)", fontsize=FS)
    ax.set_ylabel("Gain over W6A4 (ppl)", fontsize=FS)
    ax.tick_params(labelsize=FS - 0.5)
    pc.save(fig, "fig_models")
    print("wrote fig_models", len(pts), "models, split", split)


if __name__ == "__main__":
    main()
