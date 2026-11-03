"""r26e: TT energy per comparison of the segmented trim g5_k<100k> (r24_probe path, as r26c_cost.py): the equalizer
gets each segment's unit count (Xeq_0 m 1, Xeq_1 m 2, Xeq_2..8 m 4) and the clkb inverter m INV_M. The ideal
decoder draws nothing from VDD, so this is the trim and equalizer energy only.

  python -B r26e_cost.py <k>   # writes out/r26b/memory_energy_g5_k<100k>.json
"""
import os
import sys

if len(sys.argv) > 1:  # workers inherit the environment, not argv
    os.environ["R26E_K"] = sys.argv[1]
import r26e_seg as G  # noqa: E402
import r24_probe as P  # noqa: E402

K = float(os.environ.get("R26E_K", "1.75"))
DESIGN = G.register(K)
_equalize = P.equalize


def equalize(h):
    text = _equalize(h)
    text = G._EQ.sub(lambda mt: f"{mt.group(1)}\n+ m={G.units('Xeq_' + mt.group(2))}", text)
    return G._INV.sub(lambda mt: f"{mt.group(1)}\n+ m={G.E.INV_M}", text)


P.equalize = equalize
P.N.circuit_text = G.circuit_text


def main():
    h = P.variant_header(DESIGN, "tt", 1.8, 27.0, "equalize")
    G._check_circuit(h)
    assert h.count("Xeq_") == 9 and f"+ m={G.E.INV_M}" in h, h[-2000:]
    P.R.OUT = G.OUT
    P.energy(DESIGN, 5)


if __name__ == "__main__":
    sys.exit(main())
