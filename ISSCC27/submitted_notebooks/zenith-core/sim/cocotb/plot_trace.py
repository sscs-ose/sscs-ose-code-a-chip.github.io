import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "cocotb" / "cocotb_trace.json"
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "build" / "cocotb" / "cocotb_trace.png"

data = json.load(open(src, encoding="utf-8"))
tr = data["trace"]
cyc = [t["cycle"] for t in tr]
n = 70
cyc = cyc[:n]
tr = tr[:n]

fig, ax = plt.subplots(4, 1, figsize=(11, 8.5), sharex=True,
                       gridspec_kw={"height_ratios": [1, 1, 2.2, 1]})

ax[0].step(cyc, [t["state"] for t in tr], where="post", color="#1f77b4")
ax[0].set_yticks(range(6))
ax[0].set_yticklabels(data["states"])
ax[0].set_ylabel("state")

ax[1].step(cyc, [t["pc"] for t in tr], where="post", color="#2ca02c")
ax[1].set_ylabel("pc")
ax[1].set_yticks(range(0, 10))
for i, name in enumerate(data["program"][:9]):
    c0 = next((t["cycle"] for t in tr if t["pc"] == i), None)
    if c0 is not None:
        ax[1].annotate(name, (c0, i), xytext=(3, 3), textcoords="offset points", fontsize=7)

palette = ["#d62728", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf"]
for r in range(1, 7):
    ax[2].step(cyc, [t["regs"][r] for t in tr], where="post", label=f"r{r}",
               color=palette[r - 1], linewidth=1.4)
ax[2].set_ylabel("registers")
ax[2].legend(ncol=6, fontsize=8, loc="center right")

ax[3].step(cyc, [t["gpio"] for t in tr], where="post", color="black")
ax[3].set_ylabel("gpio_out")
ax[3].set_xlabel("clock cycle")

for a in ax:
    a.grid(alpha=0.25)
fig.suptitle("cpu_core driven and sampled from cocotb", y=0.995)
fig.tight_layout()
fig.savefig(dst, dpi=140)
print(dst)
