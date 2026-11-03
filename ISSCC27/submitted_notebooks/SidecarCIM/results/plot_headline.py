"""fig_headline: SidecarCIM against the dense arrays it competes with.

x = energy per 32x8 MVM from results/ppa.csv (one flow, 30 ns, clock-gated
flip-flop storage, post-layout estimates). y = perplexity increase over FP32
on the full WikiText-2 test split (ppa_data.circuits()), bars = paired SE.
One panel per model, a plain scatter; the label gives SidecarCIM against
W6A4 (ppa_data.derived()). W4A4 is
off scale (+9.0 / +7.8 ppl) and named in the caption. IEEE style, drawn at
double-column print size.
"""
import plot_common as pc
import ppa_data as pd
import matplotlib.pyplot as plt

FS = 9.0
DENSE, SC = "black", pc.ACC
MODELS = (("g", "GPT-2", "(a) GPT-2"), ("q", "Qwen", "(b) Qwen2.5-0.5B"))


def main():
    pc.style()
    cs = {c["key"]: c for c in pd.circuits()}
    w6, w7, w8, sc = (cs[k] for k in (
        "dcim_w6a4_ff", "dcim_w7a4_ff", "dcim_w8a4_ff", pd.HEAD))
    dv = pd.derived()
    E = "energy_per_dot_pj_est"

    def x(c):
        return c["ppa"][E]

    fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.75), sharey=True)
    for ax, (idx, key, sub) in zip(axs, MODELS):
        dense = [(w6, "W6A4"), (w7, "W7A4"), (w8, "W8A4")]
        for c, name in dense:
            ax.errorbar([x(c)], [c[idx][0]], yerr=[c[idx][1]], fmt="o",
                        color=DENSE, mfc="white", mew=1.0, ms=6, capsize=2,
                        elinewidth=0.8, zorder=4)
            ax.annotate(name, (x(c), c[idx][0]), xytext=(0, 8),
                        textcoords="offset points", ha="center",
                        va="bottom", fontsize=FS)
        ax.errorbar([x(sc)], [sc[idx][0]], yerr=[sc[idx][1]], fmt="D",
                    color=SC, ms=7, capsize=2, elinewidth=0.8, zorder=6)
        ax.annotate("SidecarCIM", (x(sc), sc[idx][0]), xytext=(0, -11),
                    textcoords="offset points", ha="center", va="top",
                    fontsize=FS, color=SC)
        ax.annotate("%.2f ppl lower than W6A4\nat %+.0f %% energy" % (
            dv[("vs_w6", key)]["dppl"], dv["sc_over_w6_energy"]),
            (x(sc), sc[idx][0]), xytext=(-38, -27), textcoords="offset points",
            ha="left", va="top", fontsize=FS, color=SC, linespacing=1.1)
        ax.set_xlim(1150, 1700)
        ax.set_ylim(1.0, 2.65)
        ax.set_xlabel("Energy per MVM (pJ)\n" + sub, fontsize=FS,
                      linespacing=1.9)
        ax.tick_params(labelsize=FS)
    axs[0].set_ylabel("Perplexity increase over FP32", fontsize=FS)
    fig.tight_layout(w_pad=1.2)
    pc.save(fig, "fig_headline")


if __name__ == "__main__":
    main()
