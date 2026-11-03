"""Fit the M2 pulse-survival model from data/m2/pulse_sweep.csv.

Per condition (cell, polarity, slew, load):
  t_pd_ref : SPICE leading-edge delay of the wide reference pulse
  E_full   : SPICE supply energy of the wide reference pulse (full output cycle)
  r        : w_in / t_pd_ref
  r_filter : r at which the output peak excursion first reaches 50 % VDD
  r_full   : r at which the output peak excursion reaches 95 % VDD
  S_E(r)   : E(w) / E_full
Writes data/m2/m2_conditions.csv and data/m2/m2_model.json; prints a compact table.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.spice.pulse_sweep import CELLS
df = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "data/m2").glob("pulse_sweep*.csv"))])
# key the model by OUTPUT pulse polarity (what the event simulator sees)
inv = (df.inverting.fillna(df.cell.map(lambda c: int(CELLS.get(c, (0, 0, 0, 0))[3]))).astype(bool)
       if "inverting" in df else df.cell.map(lambda c: CELLS[c][3]))
df["polarity"] = [("positive" if (p == "pos") != i else "negative") for p, i in zip(df.polarity, inv)]
keys = ["cell", "polarity", "slew_ps", "load_ff"]
W_REF = df.w_set_ps.max()


def first_cross(x, y, level):
    """x where y first rises through level (linear interpolation)."""
    for i in range(1, len(y)):
        if y[i - 1] < level <= y[i]:
            return float(x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1]))
    return float("nan") if y[0] < level else float(x[0])


cond_rows, curves = [], []
for k, g in df.groupby(keys):
    g = g.sort_values("w_set_ps")
    ref = g[g.w_set_ps == W_REF].iloc[0]
    sw = g[g.w_set_ps < W_REF].copy()
    sw["r"] = sw.w_in_ps / ref.t_pd_ps
    sw["S_E"] = sw.energy_fJ / ref.energy_fJ
    r_f = first_cross(sw.r.values, sw.peak_frac.values, 0.5)
    r_i = first_cross(sw.r.values, sw.peak_frac.values, 0.95)
    s_e_at_f = float(np.interp(r_f, sw.r, sw.S_E)) if np.isfinite(r_f) else float("nan")
    cond_rows.append(dict(zip(keys, k), t_pd_ref_ps=ref.t_pd_ps, E_full_fJ=ref.energy_fJ,
                          w_filter_ps=r_f * ref.t_pd_ps, r_filter=r_f, r_full=r_i,
                          S_E_at_filter=s_e_at_f,
                          slew_over_tpd=k[2] / ref.t_pd_ps))
    curves.append(sw.assign(**dict(zip(keys, k))))

cdf = pd.DataFrame(cond_rows)
cdf.to_csv(ROOT / "data/m2/m2_conditions.csv", index=False)
pd.concat(curves).to_csv(ROOT / "data/m2/m2_curves.csv", index=False)

# Cell/polarity-level model: r_filter = a + b * (slew/t_pd)   (least squares)
model = {"description": "M2 CALIBRATED_EXPLORATORY: SPICE-native pulse survival, "
                        "r = w_in/t_pd(SPICE), ngspice + SKY130A tt 25C 1.8V",
         "cells": {}}
for (cell, pol), g in cdf.groupby(["cell", "polarity"]):
    A = np.vstack([np.ones(len(g)), g.slew_over_tpd]).T
    for name in ("r_filter", "r_full"):
        coef, *_ = np.linalg.lstsq(A, g[name].values, rcond=None)
        pred = A @ coef
        model["cells"].setdefault(cell, {}).setdefault(pol, {})[name] = {
            "a": round(float(coef[0]), 4), "b": round(float(coef[1]), 4),
            "max_abs_resid": round(float(np.max(np.abs(pred - g[name].values))), 4)}
RGRID = np.round(np.arange(0.0, 3.01, 0.05), 2)
allc = pd.concat(curves)
for (cell, pol), g in allc.groupby(["cell", "polarity"]):
    per = [np.interp(RGRID, gg.sort_values("r").r, gg.sort_values("r").S_E, left=np.nan, right=1.0)
           for _, gg in g.groupby(["slew_ps", "load_ff"])]
    med = np.nanmedian(np.vstack(per), axis=0)
    first = np.flatnonzero(~np.isnan(med))[0]
    med[:first] = med[first]
    model["cells"][cell][pol]["S_E_curve"] = {"r": RGRID.tolist(), "S": np.round(med, 4).tolist()}
(ROOT / "data/m2/m2_model.json").write_text(json.dumps(model, indent=1))
(ROOT / "glitchscope/data/m2_model.json").write_text(json.dumps(model, indent=1))

pd.set_option("display.width", 200)
print(cdf.groupby(["cell", "polarity"])[["r_filter", "r_full", "S_E_at_filter"]].median().round(2).to_string())
print("max fit residual r_filter:", max(v[p]["r_filter"]["max_abs_resid"] for v in model["cells"].values() for p in v))
