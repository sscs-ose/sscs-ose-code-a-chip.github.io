"""r25: energy per comparison (TT) and decision memory (TT, priors +-1/+-5 mV) of the 5b + equalize trim.

  python -B r25_cost.py   # writes out/r25/memory_energy_eq5_l100.json and out/r25/memory_eq5_l100.json
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import r24_probe as P
import r25_trim5 as T

DESIGN = T.register(1.0)
BITS = 5


def main():
    P.R.OUT = T.OUT
    P.energy(DESIGN, BITS)
    jobs = [(DESIGN, "tt", 1.8, 27.0, p, v, 0, BITS, 0.5, 16) for v in P.FIXES for p in P.PRIORS]
    with ProcessPoolExecutor(12) as ex:
        mem = {}
        for j, b in zip(jobs, ex.map(P._thr_variant, jobs)):
            mem.setdefault(j[5], {})[f"{j[4]:g}"] = b
    res = {v: {"threshold_mv": m, **P._fit(m)} for v, m in mem.items()}
    (T.OUT / f"memory_{DESIGN}.json").write_text(json.dumps(res, indent=1))
    print({v: round(m["decision_uv"], 2) for v, m in res.items()}, flush=True)


if __name__ == "__main__":
    sys.exit(main())
