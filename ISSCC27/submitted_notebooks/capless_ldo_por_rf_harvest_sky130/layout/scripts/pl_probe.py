"""Probe VREF / st / pg / VOUT of ldo_top during power-up (no load).  usage: python pl_probe.py view corner temp vin"""
import sys
from postlayout import *
view, c, T, v = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
N = {"pex": dict(vref="xtop.ldo_MN2/G", vr="xtop.bgr_Rf/R2", st="xtop.bgr_MSN/D", pg="xtop.bgr_MS2/D"),
     "sch": dict(vref="xtop.vref", vr="xtop.bgr_vr", st="xtop.bgr_st", pg="xtop.bgr_pg")}[view]
ts = (0.6e-3, 1e-3, 2e-3, 4e-3, 8e-3, 15.9e-3)
ctl = "".join(f"meas tran {k}{j} find v({n}) at={t}\n" for j, t in enumerate(ts) for k, n in dict(N, vout="vout").items())
r = top_tb(view, c, T, v, "", ctl, 16e-3, f"probe_{view}_{c}_{T:g}_{v}")
for j, t in enumerate(ts):
    print(f"t={t*1e3:.1f} ms:", {k: round(r[f"{k}{j}"], 3) for k in list(N) + ["vout"]})
