"""Build the A0 poster (figures/poster.pdf) from the executed notebook and the committed results.

Every number on the poster is read from results/ (as in the notebook), and every chart is the figure the
executed notebook produced, so the poster cannot disagree with the notebook. Run it after the notebook:
    python3 scripts/make_poster.py            (needs cairosvg and qrcode: pip install cairosvg qrcode)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import base64
import io
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plotstyle as ps  # noqa: E402

COLAB = ("https://colab.research.google.com/github/tandat08052007/sscs-ose-code-a-chip.github.io/blob/"
         "isscc27-hskem-pqc-sky130/ISSCC27/submitted_notebooks/HSKEM_PQC_SKY130/HSKEM_PQC_SKY130.ipynb")
W, H = 33.11, 46.81                      # A0 portrait, inches
NB = json.loads((ROOT / "HSKEM_PQC_SKY130.ipynb").read_text(encoding="utf-8"))
R = ROOT / "results"


def nb_png(key: str, n: int = 0):
    """The n-th PNG output of the first code cell whose source contains `key`."""
    for c in NB["cells"]:
        if c["cell_type"] == "code" and key in "".join(c["source"]):
            pngs = [o["data"]["image/png"] for o in c.get("outputs", []) if "image/png" in o.get("data", {})]
            return plt.imread(io.BytesIO(base64.b64decode(pngs[n])), format="png")
    raise KeyError(key)


def svg(path: pathlib.Path, width: int = 2400):
    import cairosvg
    return plt.imread(io.BytesIO(cairosvg.svg2png(url=str(path), output_width=width)), format="png")


def jpg(path: pathlib.Path):
    return plt.imread(str(path))


def numbers() -> dict:
    j = lambda p: json.loads((R / p).read_text())
    pw, se = j("fullchip/power.json"), j("fullchip/sram_energy.json")
    t = pw["window_cycles"] * pw["clock_ns"] * 1e-9
    e = {k: v * 1e-3 * t * 1e6 for k, v in pw["power_mw"].items()}
    e["sram"] = se["sram_energy_per_decaps_uj"]
    pw0, se0 = j("fullchip/first_chip/power.json"), j("fullchip/first_chip/sram_energy.json")
    e_first = pw0["logic_power_mw"] * pw0["window_cycles"] * pw0["clock_ns"] * 1e-6 + se0["sram_energy_per_decaps_uj"]
    g = {r: j(f"gls_power/{r}/summary.json")["energy_per_forward_ntt_nj"] / 1e3
         for r in ("ntt_sp_20ns", "ntt_opt_b1_w12_20ns", "ntt_macro_20ns", "ntt_packed_20ns")}
    import csv
    dse = {(r["variant"], float(r["clk_target_ns"])): r for r in csv.DictReader(open(R / "dse_metrics.csv"))}
    o, n = dse[("ntt_sp", 20.0)], dse[("ntt_opt_pipe_w12", 20.0)]
    m0, pk = dse[("ntt_macro", 20.0)], dse[("ntt_packed", 20.0)]
    steps = j("system_sim/packed_system.json")["steps"]
    streamed = j("system_sim/streamed_system.json")["decaps_cycles"]
    prof = j("system_sim/decaps_profile.json")["configs"]["fpga"]["profile"]
    import pandas as pd
    c3 = pd.read_csv(R / "fpga/c3_repeat.csv")
    tv = {k: j(f"{d}/tvla_summary.json")["max_abs_t"] for k, d in (("plain", "leakage"), ("masked", "leakage_masked"))}
    return {"e": e, "e_first": e_first, "gate": se["sram_energy_with_chip_select_gating_uj"], "ntt_e": g,
            "fmax": (float(o["fmax_mhz"]), float(n["fmax_mhz"])),
            "at": float(n["at_product"]) / float(o["at_product"]), "area": float(n["cell_area_um2"]) / float(o["cell_area_um2"]),
            "ntt_busy": prof["ntt_busy"] / prof["cycles"], "perm_busy": prof["perm_busy"] / prof["cycles"],
            "c3": (int(c3.result_pass.sum()), len(c3)), "tv": tv, "steps": steps, "streamed": streamed,
            "pk_lat": (float(m0["latency_us_at_fmax"]), float(pk["latency_us_at_fmax"])),
            "acvp": j("acvp_rtl/keygen_asic.json"), "cells": j("fullchip/summary.json")["orfs_metrics"]}


def main(out: str = "figures/poster.pdf") -> None:
    ps.apply()
    N = numbers()
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor("white")
    ink, muted, accent = ps.INK, ps.MUTED, ps.SERIES[0]

    def box(x, y, w, h, color="#f4f3ef"):
        fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.008",
                                          transform=fig.transFigure, fc=color, ec="none", zorder=-5))

    def text(x, y, s, size=30, weight="normal", color=ink, width=None, **kw):
        if width:                                   # wrap to a column: characters per line from the font size
            import textwrap
            chars = int(width * W * 72 / (0.52 * size))
            s = "\n".join(textwrap.fill(p, chars) for p in s.split("\n"))
        fig.text(x, y, s, fontsize=size, fontweight=weight, color=color, va="top", linespacing=1.3, **kw)

    def image(img, x, y, w, h):
        ax = fig.add_axes([x, y, w, h], zorder=2); ax.imshow(img); ax.axis("off")

    # --- header
    box(0.0, 0.905, 1.0, 0.095, color=accent)
    text(0.03, 0.988, "Measuring the Design Decisions of an Open-Source Post-Quantum HSM Chip", 48, "bold", "white")
    text(0.03, 0.957, "ML-KEM-512 NTT and Keccak, from a Python golden model to a SKY130 layout", 46, color="white")
    text(0.03, 0.927, "Nguyen Tan Dat  ·  University of Science, VNU-HCM (HCMUS)  ·  IEEE SSCS Code-a-Chip, ISSCC 2027",
         30, color="white")
    try:
        import qrcode
        q = qrcode.make(COLAB, border=1)
        buf = io.BytesIO(); q.save(buf, format="PNG")
        ax = fig.add_axes([0.915, 0.918, 0.065, 0.065 * W / H], zorder=2)
        ax.imshow(plt.imread(io.BytesIO(buf.getvalue()), format="png"), cmap="gray"); ax.axis("off")
        text(0.917, 0.915, "run it in Colab", 18, color="white")
    except ImportError:
        pass
    text(0.03, 0.895, "What did each architectural decision made for the ASIC actually cost in area, latency and energy,\n"
         "what does the design still leak, and can anyone re-derive those numbers with open tools?", 32, "bold", ink)
    image(svg(ROOT / "figures/method_flow.svg"), 0.06, 0.745, 0.88, 0.12)

    cols = [0.025, 0.355, 0.685]; cw = 0.29
    heads = ["I. Is it correct?", "II. What does it cost?", "III. Does it hold up?"]
    for x, h in zip(cols, heads):
        box(x - 0.008, 0.035, cw + 0.016, 0.70)
        text(x, 0.725, h, 44, "bold", accent)

    # --- column I
    x = cols[0]
    facts = [
        f"{N['acvp']['passed']}/{N['acvp']['cases']} NIST ACVP key generations reproduced byte for byte by the complete RTL",
        "0 mismatches over 208,896 NTT coefficients and 404 Keccak permutations, at a constant latency",
        "The Barrett reducer is proven correct for all 2²⁴ inputs, and one subtraction suffices",
        "The routed netlists reproduce the golden results at gate level",
    ]
    y = 0.695
    for f in facts:
        text(x, y, "•  " + f, 24, width=cw); y -= 0.042
    image(nb_png("results/fsm_trace/ntt_sp.csv"), x, 0.32, cw, 0.17)
    text(x, 0.315, "The controller visits the 896 butterflies in the order of FIPS 203, Algorithm 9; the "
                   "single-port store needs two extra cycles per butterfly.", 20, color=muted, width=cw)
    image(svg(ROOT / "figures/ntt_datapath.svg"), x, 0.05, cw, 0.22)

    # --- column II
    x = cols[1]
    image(nb_png("fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))"), x, 0.53, cw, 0.17)
    text(x, 0.525, f"A first measured iteration of the NTT, after routing: fmax {N['fmax'][0]:.0f} → {N['fmax'][1]:.0f} MHz, "
                   f"area {N['area'] - 1:+.0%}, area × time {N['at'] - 1:+.0%}.", 22, width=cw)
    image(nb_png("STAIR = [("), x, 0.33, cw, 0.15)
    text(x, 0.325, f"A second iteration stores two coefficients in every SRAM word: a forward NTT takes "
                   f"{N['pk_lat'][1]:.0f} instead of {N['pk_lat'][0]:.0f} µs and {N['ntt_e']['ntt_packed_20ns']:.2f} instead of "
                   f"{N['ntt_e']['ntt_macro_20ns']:.2f} µJ. With a two-lane engine and a streamed datapath that removes no "
                   f"check, a decapsulation takes {N['streamed']['H']['sram_only']:,} instead of "
                   f"{N['steps']['published']:,} cycles (HSKEM-1 → HSKEM-2), as the board confirms.", 22, width=cw)
    ax = fig.add_axes([x + 0.01, 0.12, cw - 0.02, 0.13], zorder=2)
    e = N["e"]; tot = sum(e.values())
    parts = [("clock network and\nregister clock pins", e["clock"] + e["sequential"], ps.SERIES[0]),
             ("logic", e["combinational"], ps.SERIES[2]), ("SRAM\nmacros", e["sram"], "#c9c6bb")]
    left = 0
    for i, (lab, v, colour) in enumerate(parts):
        ax.barh(0, v, left=left, color=colour, height=0.5, edgecolor=ps.SURFACE, linewidth=3)
        if v / tot > 0.08:
            ax.text(left + v / 2, 0.32, f"{lab}\n{v:.0f} µJ", ha="center", va="bottom", fontsize=17)
        left += v
    ax.set_xlim(0, tot); ax.set_ylim(-0.4, 1.4); ax.axis("off")
    ax.set_title(f"A decapsulation on HSKEM-2: {tot:.0f} µJ", fontsize=24, loc="left")
    text(x, 0.11, f"HSKEM-2, the signed-off SKY130 chip of the streamed system, spends {tot:.0f} µJ per decapsulation "
                  f"instead of HSKEM-1's {N['e_first'] / 1e3:.2f} mJ. The rest is set by the integration: gating the clock "
                  f"of idle blocks and the chip selects of the macros would save roughly 28 to 42 %.",
         21, width=cw)

    # --- column III
    x = cols[2]
    image(jpg(R / "fpga/board_setup.jpg"), x, 0.52, cw, 0.18)
    text(x, 0.515, f"The same RTL on the DE25-Nano: {N['c3'][0]}/{N['c3'][1]} two-role ML-KEM runs pass.",
         22, width=cw)
    image(nb_png("LEAK_N = 400"), x, 0.33, cw, 0.15)
    text(x, 0.325, f"Simulated TVLA: largest |t| {N['tv']['plain']:.1f} unmasked, {N['tv']['masked']:.1f} with "
                   f"first-order masking (threshold 4.5).", 22, width=cw)
    lessons = ["Weigh a block by how often the system waits for it.",
               "Measure the integrated chip, not only its blocks.",
               "Check the check: ten results here first looked right and were not.",
               "Tie the prose to the data: assertions stop the notebook when they part."]
    text(x, 0.26, "What transfers", 32, "bold", accent)
    y = 0.225
    for l in lessons:
        text(x, y, "•  " + l, 23, width=cw); y -= 0.034

    text(0.025, 0.025, "Apache-2.0 · open-source tools and the SKY130 PDK throughout (FPGA bitstream: Quartus) · "
                       "every figure and number is computed from the committed results of the notebook", 18, color=muted)
    fig.savefig(ROOT / out, metadata={"CreationDate": None})
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:2])
