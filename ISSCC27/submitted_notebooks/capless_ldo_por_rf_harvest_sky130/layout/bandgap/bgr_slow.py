"""Bandgap alone on a slow VIN ramp (0 -> 3.3 V in 10 ms, then 3 ms hold): VIN at which VREF first exceeds 1.1 V,
and the settled VREF (checks that the start-up circuit also releases).
usage: python bgr_slow.py [nsu:Lsu:Wsn:Lsn ...]   (default: BGR0)"""
import sys
from lib import *
def ramp(c, T, p):
    body = ("Vin vin 0 PWL(0 0 10m 3.3)\nXbgr vin vref iref 0 bgr\nVir iref ird 0\n"
            "Xdio ird ird 0 0 sky130_fd_pr__nfet_g5v0d10v5 W=2 L=4 nf=1\n")
    ctl = "tran 2u 13m 0 5u\nmeas tran ts when v(vref)=1.1 rise=1\nmeas tran vend find v(vref) at=12.9m"
    s = "* slow\n" + models(c) + f".temp {T}\n.option gmin=1e-15 reltol=1e-4\n" + bgr_subckt(p) + body + ".control\n" + ctl + "\n.endc\n.end\n"
    r = spice(s, f"bgslow_{c}_{T}_{p['nsu']}_{p['Lsu']}_{p['Wsn']}_{p['Lsn']}")
    return r.get("ts", float("nan")) / 10e-3 * 3.3, r["vend"]
pts = [(c, T) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125)]
sets = sys.argv[1:] or [f"{BGR0['nsu']}:{BGR0['Lsu']}:{BGR0['Wsn']}:{BGR0['Lsn']}"]
for a in sets:
    n, L, W, Ls = a.split(":")
    p = dict(BGR0, nsu=int(n), Lsu=float(L), Wsn=float(W), Lsn=float(Ls))
    r = pmap(lambda x: ramp(*x, p), pts)
    von = [v for v, _ in r]
    bad = [f"{c}/{T}:{e:.3f}" for (c, T), (_, e) in zip(pts, r) if not 1.17 < e < 1.23]
    print(f"{a}: start VIN max {np.nanmax(von) if not np.isnan(von).any() else float('nan'):.3f} V "
          f"({' '.join(f'{c}{T}:{v:.2f}' for (c, T), v in zip(pts, von) if T == 125)})  settled bad {bad}", flush=True)
