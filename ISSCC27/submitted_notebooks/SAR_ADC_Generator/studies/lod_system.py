#!/usr/bin/env python3
"""The whole ADC with the drawn devices: offset and gain error to 1/32 LSB (endpoint ramps, as in
studies/endpoint_transitions.py) for the schematic and for the comparator, top-plate switch and unit-cell switches as
drawn (sargen.layout.lod), before and after the end dummies, with and without the length-of-diffusion stress.
Tight solver tolerances throughout (studies/lod_matching.py: the default ones bias a regenerative latch by ~1 mV);
one schematic run at the default tolerances shows how much of the offset was numerical.
Writes results/<N>bit/layout/lod_system.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/lod_system.py 8
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec
from sargen.flow import simulate_codes
from endpoint_transitions import SPAN, STEPS, first_reach
from lod_matching import TIGHT_SYS as TIGHT


def main(bits=8):
    spec = SarSpec(bits=bits)
    base = Path(f"build/{bits}bit")
    d = json.loads((base / "design.json").read_text())
    lod = {v: json.loads((base / "layout" / f).read_text()) for v, f in (("before", "lod_before.json"), ("after", "lod.json"))}
    nolod = {v: dict(x, strongarm=[dict(f, sa=0, sb=0) for f in x["strongarm"]],
                     topsw=[dict(f, sa=0, sb=0) for f in x["topsw"]], unit={k: (0, 0) for k in x["unit"]})
             for v, x in lod.items()}
    cases = [("schematic, default tolerances", {}), ("schematic", dict(options=TIGHT)),
             ("as drawn before, stress off", dict(lod=nolod["before"], options=TIGHT)),
             ("as drawn before, with LOD", dict(lod=lod["before"], options=TIGHT)),
             ("as drawn after, stress off", dict(lod=nolod["after"], options=TIGHT)),
             ("as drawn after, with LOD", dict(lod=lod["after"], options=TIGHT))]
    lsb, top = spec.lsb, 2**bits - 1
    out = base / "studies" / "lod_system"
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    n = 2 * SPAN * STEPS
    for name, kw in cases:
        if name in rows:
            continue
        t = {}
        for k, centre in ((1, 1 * lsb), (top, top * lsb)):
            codes, vin, _ = simulate_codes(spec, d, "ramp", n, out / name.replace(" ", "_").replace(",", "") / f"t{k}",
                                           16, ramp=(centre - SPAN * lsb, lsb / STEPS), **kw)
            t[k] = first_reach(vin, codes, k)
        off = (t[1] - lsb) / lsb
        rows[name] = dict(offset_lsb=off, gain_lsb=(t[top] - top * lsb) / lsb - off)
        out.mkdir(parents=True, exist_ok=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1))
        print(f"{name:32s} offset {off:+.3f} LSB  gain {rows[name]['gain_lsb']:+.3f} LSB", flush=True)
    md = [f"{bits}-bit schematic testbench; comparator, top-plate switch and CDAC unit switches as drawn where noted.", "",
          "| case | offset [LSB] | gain error [LSB] |", "|---|---|---|"]
    md += [f"| {k} | {r['offset_lsb']:+.3f} | {r['gain_lsb']:+.3f} |" for k, r in rows.items()]
    md.append(f"\nEndpoint ramps of {STEPS} points per LSB (resolution 1/{STEPS} LSB).")
    dst = Path(f"results/{bits}bit/layout/lod_system.md")
    dst.write_text("\n".join(md) + "\n")
    print(dst.read_text())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
