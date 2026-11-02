"""Insert (or refresh) the executable code cell of notebook Section 16: it re-plots the post-layout, POR and Monte Carlo
CSVs in layout/ and checks them against the specs. The cell is executed here and its outputs are stored in the notebook.
usage: python nb_v3_cell.py <submission folder>"""
import base64, contextlib, io, json, os, sys

CELL = r'''# Section 16 data: re-plots the v3 results stored in layout/ (produced by layout/scripts/run_all.sh: layout -> DRC/LVS ->
# C extraction -> post-layout simulation of LDO + POR + bandgap) and checks them against the specs of Section 1.
import os
import pandas as pd
import matplotlib.pyplot as plt

V3_SRC = ["", "https://raw.githubusercontent.com/sscs-ose/sscs-ose-code-a-chip.github.io/main/"
          "ISSCC27/submitted_notebooks/capless_ldo_por_rf_harvest_sky130/",
          "https://raw.githubusercontent.com/poggymacello/sscs-ose-code-a-chip.github.io/isscc27-capless-ldo-por/"
          "ISSCC27/submitted_notebooks/capless_ldo_por_rf_harvest_sky130/"]

def v3csv(rel):
    """layout/ next to the notebook if present (local run), else the copy on GitHub (Colab)"""
    for base in V3_SRC:
        try:
            if base or os.path.exists(rel):
                return pd.read_csv(base + rel)
        except Exception:
            pass
    raise FileNotFoundError(rel)

pvt = v3csv("layout/reports/postlayout_pvt_pex.csv")
por = v3csv("layout/reports/postlayout_por_pex.csv")
mc = v3csv("layout/reports/postlayout_mc_pex_27_2.5.csv").dropna(subset=["vout"])

fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
col = {-40: "tab:blue", 27: "tab:green", 125: "tab:red"}
for T, g in pvt.groupby("T"):
    ax[0].plot(g.index, g.under, "v", color=col[T], label=f"undershoot {T} °C")
    ax[0].plot(g.index, g.over, "^", color=col[T], mfc="none", label=f"overshoot {T} °C")
ax[0].axhline(300, color="k", ls="--", lw=1); ax[0].text(0, 305, "spec 300 mV", fontsize=8)
ax[0].set_xticks(range(0, len(pvt), 9)); ax[0].set_xticklabels(pvt.corner[::9])
ax[0].set_ylabel("ΔVOUT (mV)"); ax[0].set_title("Post-layout load step 0↔1 mA, 100 ns (45 PVT)")
ax[0].legend(fontsize=6, ncol=2)
lab = por.corner + "/" + por["T"].astype(str)
ax[1].plot(lab, por.von, "o-", label="V_on (release)"); ax[1].plot(lab, por.voff, "s-", label="V_off")
ax[1].axhspan(1.8, 2.2, color="0.9", label="V_on spec 2.0 V ± 10 %")
ax[1].tick_params(axis="x", rotation=90, labelsize=7); ax[1].set_ylabel("VIN (V)")
ax[1].set_title("Post-layout POR thresholds (with the real bandgap)"); ax[1].legend(fontsize=7)
ax[2].hist(mc.vout, bins=20, color="tab:purple")
ax[2].axvspan(1.164, 1.236, color="0.92", zorder=0, label="±3 %")
ax[2].set_xlabel("VOUT (V)"); ax[2].set_title(f"Post-layout Monte Carlo, tt 27 °C 2.5 V (n = {len(mc)}, untrimmed)")
ax[2].legend(fontsize=7)
plt.tight_layout(); plt.show()

checks = [
    ("Load step 0↔1 mA, 100 ns, PVT worst ≤ 300 mV", f"{max(pvt.under.max(), pvt.over.max()):.0f} mV",
     max(pvt.under.max(), pvt.over.max()) <= 300),
    ("VOUT 4 ms after power-up within ±3 % (45 PVT)", f"{pvt.vout.min():.4f} … {pvt.vout.max():.4f} V",
     pvt.vout.between(1.164, 1.236).all()),
    ("POR V_on 2.0 V ± 10 %", f"{por.von.min():.3f} … {por.von.max():.3f} V", por.von.between(1.8, 2.2).all()),
    ("POR hysteresis ≥ 150 mV", f"{por.hyst_mV.min():.0f} mV", por.hyst_mV.min() >= 150),
    ("Iq LDO + bandgap + POR (info; LDO-alone spec ≤ 10 µA)", f"{pvt.iq.min():.1f} … {pvt.iq.max():.1f} µA", None),
    ("Monte Carlo VOUT, untrimmed (info)", f"σ = {mc.vout.std() * 1e3:.1f} mV ({mc.vout.std() / 1.2 * 100:.2f} %)", None),
]
print(pd.DataFrame([(a, b, "—" if c is None else ("PASS" if c else "FAIL")) for a, b, c in checks],
                   columns=["post-layout check", "result", "status"]).to_string(index=False))
'''


def src(t):
    ls = t.rstrip("\n").split("\n")
    return [l + "\n" for l in ls[:-1]] + [ls[-1]]


def run_cell(folder):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    imgs = []
    plt.show = lambda: (imgs.append(_png(plt)), plt.close("all"))
    out = io.StringIO()
    cwd = os.getcwd(); os.chdir(folder)
    try:
        with contextlib.redirect_stdout(out):
            exec(compile(CELL, "v3_cell", "exec"), {"__name__": "__main__"})
    finally:
        os.chdir(cwd)
    outputs = [{"output_type": "display_data", "metadata": {},
                "data": {"image/png": b, "text/plain": ["<Figure size 1500x380 with 3 Axes>"]}} for b in imgs]
    outputs.append({"output_type": "stream", "name": "stdout", "text": src(out.getvalue()) + ["\n"]})
    return outputs


def _png(plt):
    buf = io.BytesIO(); plt.gcf().savefig(buf, format="png", dpi=80, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode()


if __name__ == "__main__":
    D = sys.argv[1]
    p = f"{D}/capless_ldo_por_rf_harvest_sky130.ipynb"
    nb = json.load(open(p, encoding="utf-8"))
    cells = nb["cells"]
    cells[:] = [c for c in cells if c.get("metadata", {}).get("id") != "v3-plots"]
    # Section 16 goes after Section 15 (end of the notebook), followed by its code cell
    i = [k for k, c in enumerate(cells) if c["cell_type"] == "markdown" and '<a name="v3"></a>' in "".join(c["source"])][0]
    cells.append(cells.pop(i))
    new = {"cell_type": "code", "execution_count": None, "metadata": {"id": "v3-plots"}, "outputs": run_cell(D),
           "source": src(CELL)}
    cells.append(new)
    json.dump(nb, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(p, "a", encoding="utf-8").write("\n")
    print("".join(new["outputs"][-1]["text"]))
