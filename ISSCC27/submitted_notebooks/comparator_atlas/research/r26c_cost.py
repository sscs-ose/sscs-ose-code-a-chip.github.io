"""r26c: energy per comparison (TT) and decision memory (TT, priors +-1/+-5 mV) of a unit-equalizer e-design
(r24_probe path: its equalize() is wrapped so Xeq_k gets m=2^k and the clkb inverter m=INV_M).

  python -B r26c_cost.py <bits> <k> [inv_m]   # writes out/r26b/memory_energy_<design>.json, memory_<design>.json
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

if len(sys.argv) > 2:  # read before the imports below slice sys.argv; workers inherit the environment
    os.environ["R26C_SPEC"] = " ".join(sys.argv[1:4])
import r24_probe as P  # noqa: E402
import r26c_eqscale as E  # noqa: E402

_spec = os.environ.get("R26C_SPEC", "5 1.5").split()
BITS, K, INV = int(_spec[0]), float(_spec[1]), int(_spec[2]) if len(_spec) > 2 else 4
DESIGN = E.register(BITS, K, INV)
_equalize = P.equalize


def equalize(h):
    text = _equalize(h)
    text = E._EQ.sub(lambda mt: f"{mt.group(1)}\n+ m={1 << int(mt.group(2))}", text)
    return E._INV.sub(lambda mt: f"{mt.group(1)}\n+ m={E.INV_M}", text)


P.equalize = equalize
P.N.circuit_text = E.circuit_text


def main():
    E.OUT.mkdir(parents=True, exist_ok=True)
    h = P.variant_header(DESIGN, "tt", 1.8, 27.0, "equalize")
    assert "+ m=16" in h and f"+ m={E.INV_M}" in h, h[-2000:]
    P.R.OUT = E.OUT
    P.energy(DESIGN, BITS)
    jobs = [(DESIGN, "tt", 1.8, 27.0, p, "equalize", 0, BITS, 0.5, 16) for p in P.PRIORS]
    with ProcessPoolExecutor(4) as ex:
        mem = {f"{j[4]:g}": b for j, b in zip(jobs, ex.map(P._thr_variant, jobs))}
    res = {"equalize": {"threshold_mv": mem, **P._fit(mem)}}
    (E.OUT / f"memory_{DESIGN}{E.tag()}.json").write_text(json.dumps(res, indent=1))
    print({v: round(m["decision_uv"], 2) for v, m in res.items()}, flush=True)


if __name__ == "__main__":
    sys.exit(main())
