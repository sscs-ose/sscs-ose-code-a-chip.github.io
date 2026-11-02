"""Screen the size of one bandgap device on the extracted netlist: only that instance is pointed at a W/L variant
(its parasitics barely change). Power-up at the cold and hot corners; VOUT and supply current 4 ms after power-up.
usage: python pl_swap.py <instance> W:L ...      e.g. python pl_swap.py Xbgr_MS2 1:1 1:4"""
import sys, re
import postlayout as pl
from lib import *
src = open(pl.VIEWS["pex"]).read()
inst = sys.argv[1]
line = [l for l in src.split("\n") if l.startswith(inst + " ")][0]
cell = line.split()[-1]
pts = [(c, T, v) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 125) for v in (1.8, 2.5, 3.3)]
for a in sys.argv[2:]:
    W, L = (float(x) for x in a.split(":"))
    path = f"mag/pexrun/ldo_top_pexC_{inst}_{W:g}x{L:g}.spice"
    var = f".subckt var_{inst} B D S G\nX0 S G D B sky130_fd_pr__nfet_g5v0d10v5 w={W:g} l={L:g}\n.ends\n"
    open(path, "w").write(var + src.replace(line, line.replace(cell, f"var_{inst}")))
    pl.VIEWS[a] = path
    def one(x):
        c, T, v = x
        try:
            r = pl.top_tb(a, c, T, v, "", "meas tran vo find v(vout) at=3.99m\nmeas tran iq avg i(Vin) from=3.9m to=4m",
                          4e-3, f"swp_{inst}_{W:g}x{L:g}_{c}_{T}_{v}")
            return r["vo"], -r["iq"] * 1e6
        except Exception: return float("nan"), float("nan")
    r = pmap(one, pts)
    bad = [f"{c}/{T}/{v}:{vo:.3f}" for (c, T, v), (vo, i) in zip(pts, r) if not 1.164 < vo < 1.236]
    cold = max(i for (c, T, v), (vo, i) in zip(pts, r) if T == -40)
    hot = max(i for (c, T, v), (vo, i) in zip(pts, r) if T == 125)
    print(f"{inst} {a}: VOUT bad {bad}  Iq max cold {cold:.2f} uA, hot {hot:.2f} uA", flush=True)
