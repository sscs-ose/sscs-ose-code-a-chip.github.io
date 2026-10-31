"""fig_models: SidecarCIM's gain over dense W6A4 on each of the 18 models,
against the excess kurtosis of the migrated weights (python/out/predictor.json,
fit points; the 8.88 split from the frozen prospective rule). IEEE style,
drawn at double-column print size.
"""
import json
import os

import matplotlib.pyplot as plt

import plot_common as pc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "python", "out")
FS = 9.0


def main():
    pc.style()
    pred = json.load(open(os.path.join(OUT, "predictor.json")))
    pts = pred["fit"]["points"]
    split = pred["prospective_score"]["w_kurtosis_mig"]["threshold"] \
        if "w_kurtosis_mig" in pred.get("prospective_score", {}) else 8.88
    fig, ax = plt.subplots(figsize=(7.16, 2.9))
    fig.subplots_adjust(left=0.085, right=0.99, top=0.97, bottom=0.17)
    ax.axhline(0, color="0.55", lw=0.6)
    ax.axvline(split, color=pc.ACC, lw=0.8, ls="--")
    ax.text(split * 1.04, -6.5, "split %.2f" % split, color=pc.ACC,
            fontsize=FS - 0.5, va="center")
    for q in pts:
        x, y = q["w_kurtosis_mig"], q["gain_over_W6A4_ppl"]
        s = "none" if q["p"] >= 0.05 else ("gain" if y > 0 else "loss")
        kw = dict(gain=dict(marker="D", ms=6, color=pc.ACC, mfc=pc.ACC),
                  loss=dict(marker="o", ms=5.5, color="black", mfc="black"),
                  none=dict(marker="o", ms=5.5, color="0.35", mfc="white"))[s]
        ax.plot([x], [y], ls="none", mew=1.1, zorder=3, **kw)
        if q.get("prospective"):
            ax.plot([x], [y], ls="none", marker="o", ms=11, mfc="none",
                    mec="0.25", mew=0.7, zorder=2)
    # legend by proxy
    h = [ax.plot([], [], ls="none", marker="D", ms=6, color=pc.ACC)[0],
         ax.plot([], [], ls="none", marker="o", ms=5.5, color="0.35",
                 mfc="white")[0],
         ax.plot([], [], ls="none", marker="o", ms=5.5, color="black")[0],
         ax.plot([], [], ls="none", marker="o", ms=11, mfc="none",
                 mec="0.25", mew=0.7)[0]]
    ax.legend(h, ["SidecarCIM better (p < 0.05)", "no significant difference",
                  "W6A4 better (p < 0.05)", "held-out model"],
              loc="upper left", fontsize=FS - 0.5, frameon=False,
              handletextpad=0.3, borderaxespad=0.3)
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.5, linscale=1.0)
    ax.set_yticks([-8, -4, -2, -1, -0.5, 0, 0.5, 1, 2, 4])
    ax.set_yticklabels(["-8", "-4", "-2", "-1", "-0.5", "0", "0.5", "1",
                        "2", "4"])
    ax.set_ylim(-11, 7)
    ax.set_xlabel("Excess kurtosis of the migrated weights", fontsize=FS)
    ax.set_ylabel("Gain over W6A4 (ppl, symlog)", fontsize=FS)
    ax.tick_params(labelsize=FS - 0.5)
    pc.save(fig, "fig_models") if hasattr(pc, "save") else (
        fig.savefig(os.path.join(HERE, "fig_models.png"), dpi=300),
        fig.savefig(os.path.join(HERE, "fig_models.pdf")))
    print("wrote fig_models", len(pts), "models, split", split)


if __name__ == "__main__":
    main()
