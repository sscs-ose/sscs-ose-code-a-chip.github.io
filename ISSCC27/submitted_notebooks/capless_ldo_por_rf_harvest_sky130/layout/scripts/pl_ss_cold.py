"""Small-step (1 mA -> 1.1 mA, 16 ms after power-up) recovery at the cold points where the extracted loop gain shows a sharp resonance
near 250 Hz: if that resonance were a closed-loop problem it would show as ringing here."""
import postlayout as pl
from lib import *
pl.T_ON = 16e-3          # step after the cold start-up has settled
pts = [("tt", -40, 2.5, 1e-3), ("ff", -40, 2.5, 1e-3), ("tt", 27, 2.5, 1e-3)]
for (c, T, v, il), r in zip(pts, pmap(lambda a: pl.small_step("pex", a[0], a[1], a[2], il=a[3], di=100e-6), pts)):
    print(f"{c}/{T}/{v} V at {il*1e3:g} mA: dip {r['dip_mV']:.2f} mV, recovery overshoot {r['overshoot_pct']:.1f} %", flush=True)
