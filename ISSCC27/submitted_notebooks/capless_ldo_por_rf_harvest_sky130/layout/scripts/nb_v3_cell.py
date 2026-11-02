"""Insert (or refresh) the two executable code cells of notebook Section 16 and store their outputs:
  1. re-plot the post-layout PVT, POR, Monte Carlo and loop-gain data in layout/reports and check them against the specs
  2. re-simulate the extracted netlist (layout/reports/ldo_top_pexC.spice) with the notebook's ngspice setup
Run inside the container (needs ngspice + the PDK); the notebook helpers of Section 5 are loaded first, as in the notebook.
usage: python nb_v3_cell.py <submission folder>"""
import base64, contextlib, io, json, os, sys

CELL1 = r'''# Section 16, part 1: re-plots the v3 results stored in layout/reports (produced by layout/scripts/run_all.sh:
# layout -> DRC/LVS -> C extraction -> post-layout simulation of LDO + POR + bandgap) and checks them against the specs.
import os, urllib.request
import pandas as pd
import matplotlib.pyplot as plt

V3_SRC = ["https://raw.githubusercontent.com/sscs-ose/sscs-ose-code-a-chip.github.io/main/"
          "ISSCC27/submitted_notebooks/capless_ldo_por_rf_harvest_sky130/",
          "https://raw.githubusercontent.com/poggymacello/sscs-ose-code-a-chip.github.io/isscc27-capless-ldo-por/"
          "ISSCC27/submitted_notebooks/capless_ldo_por_rf_harvest_sky130/"]

def v3file(rel):
    """layout/... next to the notebook (local run), else downloaded from GitHub (Colab)"""
    if not os.path.exists(rel):
        os.makedirs(os.path.dirname(rel), exist_ok=True)
        for base in V3_SRC:
            try:
                urllib.request.urlretrieve(base + rel, rel); break
            except Exception:
                pass
    return rel

R = "layout/reports/"
pvt = pd.read_csv(v3file(R + "postlayout_pvt_pex.csv"))
por = pd.read_csv(v3file(R + "postlayout_por_pex.csv"))
mc = pd.read_csv(v3file(R + "postlayout_mc_pex_27_2.5.csv")).dropna(subset=["vout"])
lg = pd.read_csv(v3file(R + "postlayout_loop_pex.csv")).dropna(subset=["pm_deg"])

fig, ax = plt.subplots(1, 4, figsize=(19, 3.8))
col = {-40: "tab:blue", 27: "tab:green", 125: "tab:red"}
for T, g in pvt.groupby("T"):
    ax[0].plot(g.index, g.under, "v", color=col[T], label=f"undershoot {T} °C")
    ax[0].plot(g.index, g.over, "^", color=col[T], mfc="none", label=f"overshoot {T} °C")
ax[0].axhline(300, color="k", ls="--", lw=1); ax[0].text(0, 305, "spec 300 mV", fontsize=8)
ax[0].set_xticks(range(0, len(pvt), 9)); ax[0].set_xticklabels(pvt.corner[::9])
ax[0].set_ylabel("ΔVOUT (mV)"); ax[0].set_title("Load step 0↔1 mA, 100 ns (45 PVT)"); ax[0].legend(fontsize=6, ncol=2)
lab = por.corner + "/" + por["T"].astype(str)
ax[1].plot(lab, por.von, "o-", label="V_on (release)"); ax[1].plot(lab, por.voff, "s-", label="V_off")
ax[1].axhspan(1.8, 2.2, color="0.9", label="V_on spec 2.0 V ± 10 %")
ax[1].tick_params(axis="x", rotation=90, labelsize=7); ax[1].set_ylabel("VIN (V)")
ax[1].set_title("POR thresholds (real bandgap)"); ax[1].legend(fontsize=7)
ax[2].hist(mc.vout, bins=20, color="tab:purple"); ax[2].axvspan(1.164, 1.236, color="0.92", zorder=0, label="±3 %")
ax[2].set_xlabel("VOUT (V)"); ax[2].set_title(f"Monte Carlo tt 27 °C 2.5 V (n = {len(mc)}, untrimmed)"); ax[2].legend(fontsize=7)
for (il, cl), g in lg[~lg.doublet].groupby(["il_mA", "cl_pF"]):
    ax[3].plot(g.ugf_kHz, g.pm_deg, "o", label=f"{il:g} mA, {cl:g} pF")
dbl = lg[lg.doublet]
ax[3].plot(dbl.ugf_kHz, dbl.pm_deg, "kx", label="low-f doublet (−40 °C, 1 mA)")
ax[3].axhline(45, color="k", ls="--", lw=1); ax[3].set_xscale("log")
ax[3].set_xlabel("unity-gain frequency (kHz)"); ax[3].set_ylabel("phase margin (°)")
ax[3].set_title(f"Loop gain from the extracted netlist ({len(lg)} points)"); ax[3].legend(fontsize=7)
plt.tight_layout(); plt.show()

worst = max(pvt.under.max(), pvt.over.max())
checks = [
    ("Load step 0↔1 mA, 100 ns, PVT worst ≤ 300 mV", f"{worst:.0f} mV", worst <= 300),
    ("Phase margin ≥ 45° (PVT, 0/1 mA, 10/100 pF)", f"{lg.pm_deg.min():.0f}° (gain margin ≥ {lg.gm_dB.min():.0f} dB); "
     f"{int(lg.doublet.sum())} points with a low-f doublet", lg.pm_deg.min() >= 45),
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

CELL2 = r'''# Section 16, part 2: re-simulate the extracted (post-layout) netlist here, with the ngspice setup of Section 5.
# Power-up of LDO + POR + bandgap (VIN 0 -> 2.5 V in 1 ms), then the 0 -> 1 -> 0 mA load step, and the supply rejection
# at 100 kHz (50 mV ripple, amplitude fitted at the ripple frequency). tt, 27 °C. A few minutes on 2 cores.
import re
import numpy as np
PEX =os.path.abspath(v3file("layout/reports/ldo_top_pexC.spice"))

def models_v3(corner="tt"):
    """models() of Section 5 plus the native NMOS and pfet_01v8 (the PNP model reads its junction parameters)"""
    fn = os.path.join(SIMDIR, f"models_v3_{corner}.lib")
    with open(fn, "w") as f:
        f.write(f".param mc_mm_switch=0\n.param mc_pr_switch=0\n.include \"{NGS}/corners/{corner}/nonfet.spice\"\n")
        for d in ("nfet_g5v0d10v5", "pfet_g5v0d10v5", "pfet_01v8", "nfet_05v0_nvt"):
            f.write(f".include \"{REF}/sky130_fd_pr__{d}__{corner}.corner.spice\"\n"
                    f".include \"{REF}/sky130_fd_pr__{d}__mismatch.corner.spice\"\n")
        f.write(f".include \"{NGS}/all.spice\"\n.include \"{NGS}/r+c/res_typical__cap_typical.spice\"\n"
                f".include \"{NGS}/r+c/res_typical__cap_typical__lin.spice\"\n")
    return f".include \"{fn}\"\n"

def pex_run(job):
    T_ON = 4e-3
    vin = "Vin vin 0 PWL(0 0 1m 2.5)\n"
    if job == "load":
        t1, t2, te = T_ON, T_ON + 40e-6, T_ON + 80e-6
        extra = f"Il vout 0 PWL(0 0 {t1} 0 {t1 + 1e-7} 1m {t2} 1m {t2 + 1e-7} 0)\n"
        ctl = (f"tran 20n {te} 0 2u uic\nmeas tran vpre avg v(vout) from={t1 - 20e-6} to={t1}\n"
               f"meas tran vmin min v(vout) from={t1} to={t2}\nmeas tran vmax max v(vout) from={t2} to={te}\n"
               f"meas tran iq avg i(Vin) from={t1 - 20e-6} to={t1}\n")
    else:
        f0 = 1e5; te = T_ON + 20 / f0
        vin = f"Vin vinx 0 PWL(0 0 1m 2.5)\nVr vin vinx SIN(0 0.05 {f0} {T_ON})\n"; extra = ""
        ctl = f"tran 20n {te} 0 {1 / f0 / 50} uic\nlinearize v(vout)\nwrdata v3_psrr.dat v(vout)\n"   # as postlayout.py
    net = ("* Section 16 post-layout\n" + models_v3() + ".temp 27\n.option gmin=1e-14 reltol=1e-4 rshunt=1e13 method=gear\n"
           f".include \"{PEX}\"\n" + vin + "Xtop vin vout rstn 0 ldo_top\nCL vout 0 100p\nCrst rstn 0 50f\n" + extra +
           f".control\n{ctl}.endc\n.end\n")
    r = spice(net, f"v3_pex_{job}", timeout=3600)
    if job == "load":
        return dict(vout=r["vpre"], under=(r["vpre"] - r["vmin"]) * 1e3, over=(r["vmax"] - r["vpre"]) * 1e3, iq=-r["iq"] * 1e6)
    d = wrdata("v3_psrr"); d.columns = ["t", "v"]
    a = d[d.t >= te - 4 / f0]; w = 2 * np.pi * f0 * (a.t.values - T_ON)
    c = np.linalg.lstsq(np.column_stack([np.sin(w), np.cos(w), np.ones_like(w), a.t.values - te]), a.v.values, rcond=None)[0]
    return dict(psrr=20 * np.log10(0.05 / np.hypot(c[0], c[1])))

ld, ps = pmap(pex_run, ["load", "psrr"], workers=2)
ref = pvt[(pvt.corner == "tt") & (pvt["T"] == 27) & (pvt.vin == 2.5)].iloc[0]
ref_psrr = float(re.search(r"PSRR 100000 Hz: ([-0-9.]+) dB", open(v3file(R + "postlayout_tt_pex.txt")).read()).group(1))
print(pd.DataFrame([("VOUT before the step (V)", f"{ld['vout']:.4f}", f"{ref.vout:.4f}"),
                    ("load-step undershoot (mV)", f"{ld['under']:.0f}", f"{ref.under:.0f}"),
                    ("load-step overshoot (mV)", f"{ld['over']:.0f}", f"{ref.over:.0f}"),
                    ("Iq LDO + bandgap + POR (µA)", f"{ld['iq']:.2f}", f"{ref.iq:.2f}"),
                    ("PSRR at 100 kHz (dB)", f"{ps['psrr']:.1f}", f"{ref_psrr:.1f}")],
                   columns=["tt, 27 °C, 2.5 V, extracted netlist", "this run", "stored (run_all.sh)"]).to_string(index=False))
'''


def src(t):
    ls = t.rstrip("\n").split("\n")
    return [l + "\n" for l in ls[:-1]] + [ls[-1]]


def _png(plt):
    buf = io.BytesIO(); plt.gcf().savefig(buf, format="png", dpi=80, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode()


def run_cells(folder, codes):
    """execute the cells in one namespace that first holds the notebook's Section 5 helpers (as in the notebook)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd(); os.chdir(folder)
    ns = {"__name__": "__main__"}
    outs = []
    try:
        exec(open(os.path.join(here, "_nb_cell09_original.py"), encoding="utf-8").read(), ns)
        for code in codes:
            imgs = []
            plt.show = lambda: (imgs.append(_png(plt)), plt.close("all"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exec(compile(code, "v3_cell", "exec"), ns)
            o = [{"output_type": "display_data", "metadata": {},
                  "data": {"image/png": b, "text/plain": ["<Figure size 1900x380 with 4 Axes>"]}} for b in imgs]
            o.append({"output_type": "stream", "name": "stdout", "text": src(out.getvalue()) + ["\n"]})
            outs.append(o)
    finally:
        os.chdir(cwd)
    return outs


if __name__ == "__main__":
    D = sys.argv[1]
    p = f"{D}/capless_ldo_por_rf_harvest_sky130.ipynb"
    nb = json.load(open(p, encoding="utf-8"))
    cells = nb["cells"]
    cells[:] = [c for c in cells if not str(c.get("metadata", {}).get("id", "")).startswith("v3-")]
    # Section 16 goes after Section 15 (end of the notebook), followed by its code cells
    i = [k for k, c in enumerate(cells) if c["cell_type"] == "markdown" and '<a name="v3"></a>' in "".join(c["source"])][0]
    cells.append(cells.pop(i))
    outs = run_cells(D, [CELL1, CELL2])
    n0 = max([c.get("execution_count") or 0 for c in cells if c["cell_type"] == "code"])
    for k, (cid, code, o) in enumerate(zip(("v3-plots", "v3-pex-sim"), (CELL1, CELL2), outs)):
        cells.append({"cell_type": "code", "execution_count": n0 + 1 + k, "metadata": {"id": cid}, "outputs": o,
                      "source": src(code)})
    json.dump(nb, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(p, "a", encoding="utf-8").write("\n")
    for o in outs:
        print("".join(o[-1]["text"]))
