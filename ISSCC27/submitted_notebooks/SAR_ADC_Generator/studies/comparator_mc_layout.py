#!/usr/bin/env python3
"""Comparator offset Monte Carlo, schematic vs. layout extraction (PDK mismatch models on every device; the
extraction's fingers each draw their own mismatch).  The mean is the layout's systematic offset, sigma its random
offset.  Writes results/comparator_mc_layout.md.  Run inside IIC-OSIC-TOOLS:
    python3 studies/comparator_mc_layout.py [bits ...]
(needs build/<N>bit/layout/pex/strongarm_pex.spice from `run_layout.py comparator --bits N --pex`)
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec
from sargen.characterize import comparator_offset_mc
from sargen.netlist import load_strongarm_extraction


def main(bits=(4, 6, 8)):
    rows = []
    for b in bits:
        spec, base = SarSpec(bits=b), Path(f"build/{b}bit")
        d = json.loads((base / "design.json").read_text())
        out = base / "studies" / "cmp_mc_layout"
        res = {}
        for case, sub in (("schematic", None),
                          ("layout (C extraction)", load_strongarm_extraction(base / "layout/pex/strongarm_pex.spice"))):
            r = comparator_offset_mc(spec, d, out / case.split()[0], cmp_subckt=sub)
            res[case] = {k: v for k, v in r.items() if k != "offsets"}
            print(f"{b} bit {case:22s} mean {r['mean'] * 1e3:+.2f} mV sigma {r['sigma'] * 1e3:.2f} mV (n={r['n']})",
                  flush=True)
        rows.append((b, spec, d, res))
        (out / "summary.json").write_text(json.dumps(res, indent=1))
    md = ["| bits | case | mean offset [mV] | sigma [mV] | sigma, sizing target [mV] | 3 sigma [LSB] | n |",
          "|---|---|---|---|---|---|---|"]
    for b, spec, d, res in rows:
        for case, r in res.items():
            md.append(f"| {b} | {case} | {r['mean'] * 1e3:+.2f} | {r['sigma'] * 1e3:.2f} "
                      f"| {d['cmp']['sigma_os_target'] * 1e3:.2f} | {3 * r['sigma'] / spec.lsb:.2f} | {r['n']} |")
    out = Path("results/comparator_mc_layout.md")
    out.write_text("\n".join(md) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main(tuple(int(a) for a in sys.argv[1:]) or (4, 6, 8))
