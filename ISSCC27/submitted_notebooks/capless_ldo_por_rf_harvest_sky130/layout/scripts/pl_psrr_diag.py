"""1 kHz PSRR of variant netlists (tt, 27 C, 2.5 V): which part of the extracted netlist costs the low-frequency gain."""
import sys
import postlayout as pl
from lib import *
pl.VIEWS.update({k: v for k, v in (a.split("=") for a in sys.argv[1:])})
names = [a.split("=")[0] for a in sys.argv[1:]]
for n, r in zip(names, pmap(lambda n: pl.psrr_tran(n, 1e3), names)): print(f"{n}: PSRR 1 kHz {r:.1f} dB", flush=True)
