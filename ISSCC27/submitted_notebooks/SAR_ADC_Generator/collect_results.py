#!/usr/bin/env python3
"""Copy the small result files of long runs (6/8-bit flows, sweeps, SPICE MC) from build/ to results/
and make the resolution-scaling table and plot. results/ is committed so the notebook can show them."""

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

B, R = Path("build"), Path("results")
FLOW_FILES = ["summary.json", "report.md", "sizing.md", "waveforms.png", "transfer.png", "fft.png",
              "inl_dnl_histogram.png", "inl_dnl_transitions.png", "comparator_offset.png", "mc_linearity.png"]


def main():
    R.mkdir(exist_ok=True)
    rows = []
    for n in range(4, 9):
        src = B / f"{n}bit"
        if not (src / "summary.json").exists():
            continue
        dst = R / f"{n}bit"
        dst.mkdir(exist_ok=True)
        for f in FLOW_FILES:
            if (src / f).exists():
                shutil.copy2(src / f, dst / f)
        sw = src / "sweeps"
        if sw.exists():
            (dst / "sweeps").mkdir(exist_ok=True)
            for f in sw.iterdir():
                if f.is_file() and f.suffix in (".json", ".md", ".png"):
                    shutil.copy2(f, dst / "sweeps" / f.name)
        s = json.loads((src / "summary.json").read_text())
        d = json.loads((src / "design.json").read_text())
        rows.append(dict(bits=n, fs=s["spec"]["fs"], enob=s["dynamic"]["enob"],
                         ideal_enob=s["dynamic"]["ideal_model_enob"], sndr=s["dynamic"]["sndr_db"],
                         dnl=s["static"].get("dnl_t_max", s["static"]["dnl_max"]),
                         inl=s["static"].get("inl_t_max", s["static"]["inl_max"]),
                         missing=s["static"]["missing_codes"], offset=s["static"]["offset_lsb"],
                         p_uw=s["power"]["p_total"] * 1e6, e_pj=s["power"]["energy_per_conv"] * 1e12,
                         fom_fj=s["power"]["walden_fom_J"] * 1e15, ctot_ff=d["cu"]["c_total"] * 1e15,
                         cu_ff=d["cu"]["c"] * 1e15, w_in=d["cmp"]["w_in"],
                         mc_dnl_p99=s["mc"]["dnl_p99"], runtime_min=s["runtime_s"] / 60))
    if not rows:
        print("no results found in build/")
        return
    (R / "scaling.json").write_text(json.dumps(rows, indent=1))
    keys = list(rows[0])
    md = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    md += ["| " + " | ".join(f"{r[k]:.3g}" if isinstance(r[k], float) else str(r[k]) for k in keys) + " |"
           for r in rows]
    (R / "scaling.md").write_text("\n".join(md) + "\n")

    n = [r["bits"] for r in rows]
    from sargen.plots import BLUE, GREEN, INK, MUTED, ORANGE, _fig, _save, _style
    fig, ax = _fig(10.5, 7.6, "One generator, 4 to 8 bits",
                   "The same code sized and simulated each resolution at transistor level (before layout). ENOB follows "
                   "N; capacitance and power grow about 2x per bit once capacitor matching sets the unit capacitor.",
                   nrows=2, ncols=2)
    _style(ax)
    ax[0, 0].plot(n, [r["ideal_enob"] for r in rows], "--", color=MUTED, label="ideal quantizer")
    ax[0, 0].plot(n, [r["enob"] for r in rows], "o-", color=BLUE, lw=2, label="transistor level")
    ax[0, 0].set_ylabel("ENOB [bit]")
    ax[0, 0].legend(loc="upper left")
    ax[0, 1].semilogy(n, [r["ctot_ff"] for r in rows], "o-", color=BLUE, lw=2, label="array capacitance [fF]")
    ax[0, 1].semilogy(n, [r["p_uw"] for r in rows], "s-", color=ORANGE, lw=2, label="power [µW]")
    ax[0, 1].legend(loc="upper left")
    ax[1, 0].plot(n, [r["dnl"] for r in rows], "o-", color=BLUE, lw=2, label="max |DNL|, nominal")
    ax[1, 0].plot(n, [r["inl"] for r in rows], "s-", color=GREEN, lw=2, label="max |INL|, nominal")
    ax[1, 0].plot(n, [r["mc_dnl_p99"] for r in rows], "^--", color=ORANGE, lw=1.5, label="DNL, 99 % of chips (MC)")
    ax[1, 0].axhline(0.5, color=MUTED, ls=":", lw=1)
    ax[1, 0].text(n[0], 0.51, "target 0.5 LSB", fontsize=9, color=MUTED, va="bottom")
    ax[1, 0].set_ylabel("[LSB]")
    ax[1, 0].legend(loc="upper left", bbox_to_anchor=(0, 0.95))
    ax[1, 1].plot(n, [r["fom_fj"] for r in rows], "o-", color=BLUE, lw=2)
    ax[1, 1].set_ylabel("Walden FoM [fJ/conv-step]")
    for a in ax.flat:
        a.set_xlabel("resolution N [bit]")
        a.set_xticks(n)
    _save(fig, R / "scaling.png")
    print((R / "scaling.md").read_text())


if __name__ == "__main__":
    main()
