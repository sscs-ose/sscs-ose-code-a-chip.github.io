#!/usr/bin/env python3
"""Offset and gain error to 1/STEPS LSB: fine input ramps around only the first (0 -> 1) and last (2^N-2 -> 2^N-1)
transitions, instead of a full ramp whose resolution is 1/hits LSB (at 4 hits, the 8-bit post-layout run's step).
Cases: schematic, unit-cell CDAC from layout, full core from layout.  Writes results/<N>bit/layout/endpoints.md.
Run inside IIC-OSIC-TOOLS:  python3 studies/endpoint_transitions.py 8
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec
from sargen import netlist as nl
from sargen.flow import simulate_codes

STEPS = 32          # ramp points per LSB
SPAN = 3            # LSB around each transition


def cases(bits):
    lay = Path(f"build/{bits}bit/layout")
    pins = nl.subckt_pins(lay / f"cdacu{bits}b_ref.spice", f"cdacu{bits}b")
    cdacu = dict(cdacsw=(nl.wrap_extraction(lay / f"pex/cdacu{bits}b_pex.spice", "cdacsw", pins), pins))
    from sargen.layout import core as core_layout
    return [("schematic", {}), ("unit-cell CDAC", cdacu), ("full core from layout", core_layout.extracted(bits, lay))]


def first_reach(vin, codes, k):
    hit = np.nonzero(np.asarray(codes) >= k)[0]
    return float("nan") if not len(hit) or hit[0] == 0 else 0.5 * (vin[hit[0]] + vin[hit[0] - 1])


def main(bits=8):
    spec = SarSpec(bits=bits)
    d = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    lsb, top = spec.lsb, 2**bits - 1
    out = Path(f"build/{bits}bit/studies/endpoints")
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    n = 2 * SPAN * STEPS
    for name, kw in cases(bits):
        if name in rows:
            continue
        t = {}
        for k, centre in ((1, 1 * lsb), (top, top * lsb)):           # ideal transitions (truncating ADC)
            v0 = centre - SPAN * lsb
            codes, vin, _ = simulate_codes(spec, d, "ramp", n, out / name.replace(" ", "_") / f"t{k}", 16,
                                           ramp=(v0, lsb / STEPS), **kw)
            t[k] = first_reach(vin, codes, k)
        off = (t[1] - lsb) / lsb
        gain = (t[top] - top * lsb) / lsb - off
        rows[name] = dict(t1=t[1], t_last=t[top], offset_lsb=off, gain_lsb=gain)
        out.mkdir(parents=True, exist_ok=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1))
        print(f"{name:24s} offset {off:+.3f} LSB  gain {gain:+.3f} LSB", flush=True)
    md = ["| case | offset [LSB] | gain error [LSB] |", "|---|---|---|"]
    md += [f"| {k} | {r['offset_lsb']:+.3f} | {r['gain_lsb']:+.3f} |" for k, r in rows.items()]
    md.append(f"\nTransition levels from ramps of {STEPS} points per LSB around the first and last transition "
              f"(resolution 1/{STEPS} LSB).")
    dst = Path(f"results/{bits}bit/layout/endpoints.md")
    dst.write_text("\n".join(md) + "\n")
    print(dst.read_text())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
