"""Settled VREF and bandgap supply current 12 ms after a 1 ms power-up ramp at -40 C vs VIN (cold release check)."""
from lib import *
pts = [(c, v) for c in ("tt", "ss", "sf", "ff", "fs") for v in (1.8, 2.0, 2.2, 2.5, 3.3)]
for name, p in (("MSN gate on pd, 0.42/20", dict(BGR0)),):
    def one(a):
        c, v = a
        try: return bgr_tran(p, v, c, -40, t_hold=12e-3, tag_extra=f"hr_pd{p['Wsn']}x{p['Lsn']}")
        except Exception: return dict(vref=float("nan"), itot=float("nan"))
    r = pmap(one, pts)
    print(name + ":", "  ".join(f"{c}/{v}:{x['vref']:.3f}({x['itot']*1e9:.0f}nA)" for (c, v), x in zip(pts, r)), flush=True)
