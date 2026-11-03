#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Animate one SAR conversion, driven by the trace the RTL actually produced.

  iverilog -g2012 -o trace rtl/sar_sequencer.v rtl/tb_trace.v
  ./trace -pvin=1.1340 > anim/trace.txt
  python3 anim/make_gif.py anim/trace.txt anim/sar_conversion.gif
"""
import sys, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle

trace, out = sys.argv[1], sys.argv[2]
vin = vref = None; N = 8; rows = []; code = None
for line in open(trace):
    if line.startswith("#"):
        if m := re.match(r"# vin ([\d.]+) vref ([\d.]+) n (\d+)", line):
            vin, vref, N = float(m[1]), float(m[2]), int(m[3])
        if m := re.match(r"# code (\d+)", line): code = int(m[1])
        continue
    p = line.split()
    if len(p) == 5: rows.append((int(p[0]), float(p[1]), int(p[2]), int(p[3]), float(p[4])))
assert vin and rows, "trace did not parse"
LSB = vref / (1 << N)

# the search bracket after each trial
lo, hi, brackets, bits = 0.0, vref, [], []
for t, dac, cmp_, bit, _ in rows:
    brackets.append((lo, hi, dac))
    if bit: lo = dac
    else:   hi = dac
    bits.append(bit)

FPT = 3                                  # frames per trial
FRAMES = len(rows) * FPT + 10            # + hold at the end

fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.2, 4.6),
                               gridspec_kw={"width_ratios": [1.65, 1]})
fig.patch.set_facecolor("white")

def draw(fr):
    axL.clear(); axR.clear()
    k = min(fr // FPT, len(rows) - 1)          # trial index
    sub = fr - k * FPT                          # 0 = settle, 1 = compare, 2 = decided
    done = fr >= len(rows) * FPT

    # ---------------- left: the binary search
    lo_, hi_, dac = brackets[k]
    axL.add_patch(Rectangle((-0.6, lo_), len(rows) + 0.1, hi_ - lo_,
                            facecolor="#dbeafe", edgecolor="none", zorder=0))
    axL.axhline(vin, color="#111827", lw=2, zorder=4)
    axL.text(len(rows) - 0.45, vin + 0.035, f"V$_{{in}}$ = {vin:.4f} V",
             fontsize=9, ha="right", color="#111827", zorder=5)

    shown = k + 1 if (done or sub >= 1) else k
    xs = list(range(shown)); ys = [rows[i][1] for i in xs]
    if xs:
        axL.step(xs, ys, where="mid", color="#2563eb", lw=1.6, zorder=3)
        for i in xs:
            axL.plot(i, rows[i][1], "o", ms=7, zorder=5,
                     color="#2563eb" if rows[i][3] else "#dc2626")
    if not done and sub >= 1:
        axL.plot(k, dac, "o", ms=14, mfc="none", mec="#f59e0b", mew=2.5, zorder=6)
        verdict = "V$_{in}$ > DAC  →  bit = 1" if rows[k][2] else "V$_{in}$ < DAC  →  bit = 0"
        axL.text(k, dac - 0.10, verdict, fontsize=9, ha="center",
                 color="#2563eb" if rows[k][2] else "#dc2626", zorder=6)

    axL.set_xlim(-0.6, len(rows) - 0.4); axL.set_ylim(-0.05, vref + 0.05)
    axL.set_xticks(range(len(rows)))
    axL.set_xticklabels([f"{i}\n{1<<(N-1-i)}C" for i in range(len(rows))], fontsize=8)
    axL.set_xlabel("bit trial   (MSB first)", fontsize=9)
    axL.set_ylabel("voltage (V)", fontsize=9)
    axL.set_title("the DAC halves the remaining range each trial", fontsize=10, pad=8)
    axL.grid(alpha=0.25, lw=0.6)

    # ---------------- right: the code register
    axR.set_xlim(0, len(rows)); axR.set_ylim(0, 3.4); axR.axis("off")
    axR.set_title("code register", fontsize=10, pad=8)
    nshown = k + 1 if (done or sub >= 2) else k
    for i in range(len(rows)):
        filled = i < nshown
        axR.add_patch(Rectangle((i + .08, 1.75), .84, .8, lw=1.4,
                                edgecolor="#374151",
                                facecolor=("#2563eb" if bits[i] else "#f3f4f6") if filled else "white"))
        axR.text(i + .5, 2.15, str(bits[i]) if filled else "?", ha="center", va="center",
                 fontsize=15, fontweight="bold",
                 color="white" if (filled and bits[i]) else "#111827")
        axR.text(i + .5, 1.52, f"{1<<(N-1-i)}", ha="center", fontsize=7.5, color="#6b7280")
    val = sum(b << (N - 1 - i) for i, b in enumerate(bits[:nshown]))
    label = "code" if done else "code so far"
    axR.text(len(rows)/2, .95, f"{label} = {val}", ha="center", fontsize=13,
             fontweight="bold", color="#111827" if done else "#6b7280")
    axR.text(len(rows)/2, .45,
             (f"{val} x {LSB*1000:.2f} mV = {val*LSB:.4f} V" if done else
              f"{N-nshown} bit{'s' if N-nshown!=1 else ''} still undecided") if nshown
             else "sampling...", ha="center", fontsize=9, color="#374151")
    if done:
        axR.text(len(rows)/2, .05, f"error {abs(val*LSB-vin)/LSB:.2f} LSB",
                 ha="center", fontsize=9, color="#059669", fontweight="bold")

    fig.suptitle("8-bit SAR ADC  ·  one conversion, traced from the RTL",
                 fontsize=12, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

ani = FuncAnimation(fig, draw, frames=FRAMES, interval=380)
ani.save(out, writer=PillowWriter(fps=2.6))
print(f"wrote {out}  ({FRAMES} frames, code={code}, {len(rows)} trials)")
