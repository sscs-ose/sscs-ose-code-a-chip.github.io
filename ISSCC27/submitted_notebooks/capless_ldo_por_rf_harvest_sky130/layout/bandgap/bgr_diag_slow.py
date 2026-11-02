"""Node voltages of the bandgap alone during a slow VIN ramp (0 -> 3.3 V in 10 ms).  usage: python bgr_diag_slow.py corner temp [gnd]"""
import sys
from lib import *
c, T = sys.argv[1], float(sys.argv[2])
p = dict(BGR0)
if len(sys.argv) > 3 and sys.argv[3] == "gnd": p.update(msn_gnd=True, Wsn=0.42, Lsn=20)
nodes = ["vref", "xbgr.st", "xbgr.pg", "xbgr.pd", "xbgr.ng", "xbgr.ea", "xbgr.eb", "xbgr.e3", "xbgr.ncas", "xbgr.su1"]
body = ("Vin vin 0 PWL(0 0 10m 3.3)\nXbgr vin vref iref 0 bgr\nVir iref ird 0\n"
        "Xdio ird ird 0 0 sky130_fd_pr__nfet_g5v0d10v5 W=2 L=4 nf=1\n")
ts = tuple(x * 1e-3 for x in (3, 4, 4.5, 5, 5.5, 6, 6.5, 7, 9.9))
ctl = "tran 2u 10m 0 5u\n" + "".join(f"meas tran n{j}_{k} find v({n}) at={t}\n" for j, t in enumerate(ts) for k, n in enumerate(nodes)) + \
      "".join(f"meas tran i{j} find i(Vin) at={t}\n" for j, t in enumerate(ts))
s = "* d\n" + models(c) + f".temp {T}\n.option gmin=1e-15 reltol=1e-4\n" + bgr_subckt(p) + body + ".control\n" + ctl + "\n.endc\n.end\n"
r = spice(s, f"bgdiag_{c}_{T:g}_{p.get('msn_gnd', 0)}")
for j, t in enumerate(ts):
    print(f"VIN {t / 10e-3 * 3.3:.2f} V:", {n.replace('xbgr.', ''): round(r[f'n{j}_{k}'], 3) for k, n in enumerate(nodes)}, f"I {-r[f'i{j}']*1e9:.1f} nA")
