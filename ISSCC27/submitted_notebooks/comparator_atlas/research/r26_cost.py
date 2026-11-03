"""r26: energy per comparison (TT) and decision memory (TT, priors +-1/+-5 mV) of a scaled design.

  python -B r26_cost.py <bits> <k>   # writes out/r26/memory_energy_<design>.json and out/r26/memory_<design>.json
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

if len(sys.argv) > 2:  # read before the imports below slice sys.argv; workers inherit the environment
    os.environ["R26_SPEC"] = f"{sys.argv[1]} {sys.argv[2]}"
import r24_probe as P  # noqa: E402
import r26_scale as S  # noqa: E402

_b, _k = os.environ.get("R26_SPEC", "6 1.5").split()
BITS, K = int(_b), float(_k)
DESIGN = S.register(BITS, K)


def main():
    S.OUT.mkdir(parents=True, exist_ok=True)
    P.R.OUT = S.OUT
    P.energy(DESIGN, BITS)
    jobs = [(DESIGN, "tt", 1.8, 27.0, p, v, 0, BITS, 0.5, 16) for v in P.FIXES for p in P.PRIORS]
    with ProcessPoolExecutor(12) as ex:
        mem = {}
        for j, b in zip(jobs, ex.map(P._thr_variant, jobs)):
            mem.setdefault(j[5], {})[f"{j[4]:g}"] = b
    res = {v: {"threshold_mv": m, **P._fit(m)} for v, m in mem.items()}
    (S.OUT / f"memory_{DESIGN}.json").write_text(json.dumps(res, indent=1))
    print({v: round(m["decision_uv"], 2) for v, m in res.items()}, flush=True)


if __name__ == "__main__":
    sys.exit(main())
