"""Supply ripple on the bandgap alone: 50 mV at f on VIN (2.5 V, tt, 27 C) -> ripple on VREF, in dB (PSRR of the reference)."""
import sys
from lib import *
def one(f, p=None):
    p = p or dict(BGR0)
    t1 = 4e-3; nc = 20 if f >= 1e4 else 5; te = t1 + nc / f
    body = (f"Vin vinx 0 PWL(0 0 1m 2.5)\nVr vin vinx SIN(0 0.05 {f} {t1})\nXbgr vin vref iref 0 bgr\nVir iref ird 0\n"
            "Xdio ird ird 0 0 sky130_fd_pr__nfet_g5v0d10v5 W=2 L=4 nf=1\n")
    ctl = f"tran {min(2e-8, 1/f/200)} {te} 0 {min(5e-6, 1/f/50)}\nmeas tran vpp pp v(vref) from={t1 + (nc-4)/f} to={te}"
    s = "* bgr psrr\n" + models("tt") + ".temp 27\n.option gmin=1e-15 reltol=1e-4\n" + bgr_subckt(p) + body + ".control\n" + ctl + "\n.endc\n.end\n"
    return 20 * np.log10(0.1 / spice(s, f"bgrps_{f:g}_{p.get('ncvr', 0)}")["vpp"])
fs = [1e3, 1e4, 3e4, 1e5, 3e5, 8.47e5]
if __name__ == "__main__":
    for n in [int(a) for a in sys.argv[1:]] or [BGR0.get("ncvr", 0)]:
        p = dict(BGR0, ncvr=n, Cvr_side=25)
        r = pmap(lambda f: one(f, p), fs)
        print(f"ncvr={n}:", "  ".join(f"{f:g} Hz {x:.1f} dB" for f, x in zip(fs, r)), flush=True)
