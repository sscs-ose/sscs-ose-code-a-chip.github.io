#!/usr/bin/env python3
"""The extracted comparator before / after the matching rework (end dummies on the latch rows, latch halves pulled
in to the axis): systematic offset (no mismatch, tight tolerances), clock-to-output delay at +-1 mV, and the offset
spread with SKY130 mismatch (Monte Carlo on the extraction).
Inputs: build/diag/sa_v1/<N>/strongarm_pex.spice (before), build/<N>bit/layout/pex/strongarm_pex.spice (after).
Writes results/<N>bit/layout/comparator_layout_ab.md.  Run:  python3 studies/comparator_layout_ab.py 8
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, netlist as nl
from sargen.characterize import comparator_offset_mc
from lod_matching import comparator


def main(bits=8, n_inst=24):
    spec = SarSpec(bits=bits)
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    out = Path(f"build/{bits}bit/studies/comparator_layout_ab")
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    for name, path in (("before", Path(f"build/diag/sa_v1/{bits}/strongarm_pex.spice")),
                       ("after", Path(f"build/{bits}bit/layout/pex/strongarm_pex.spice"))):
        if name in rows:
            continue
        sub = nl.load_strongarm_extraction(path)
        off, dl = comparator(spec, sub, out / name)
        mc = comparator_offset_mc(spec, design, out / f"{name}_mc", n_inst=n_inst, n_jobs=4, cmp_subckt=sub)
        rows[name] = dict(offset=off, delay=dl, sigma=mc["sigma"], mean=mc["mean"], n=mc["n"])
        out.mkdir(parents=True, exist_ok=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
        print(name, rows[name], flush=True)
    md = [f"{bits}-bit comparator, layout extraction (Magic, parasitic C).", "",
          "| layout | systematic offset [uV] | delay at offset +-1 mV [ps] | Monte Carlo sigma [mV] (n) | MC mean [mV] |",
          "|---|---|---|---|---|"]
    for k, r in rows.items():
        md.append(f"| {k} | {r['offset'] * 1e6:+.0f} | {r['delay'][0] * 1e12:.0f} / {r['delay'][1] * 1e12:.0f} | "
                  f"{r['sigma'] * 1e3:.2f} ({r['n']}) | {r['mean'] * 1e3:+.2f} |")
    md.append(f"\nSizing target sigma {design['cmp']['sigma_os_target'] * 1e3:.2f} mV.")
    dst = Path(f"results/{bits}bit/layout/comparator_layout_ab.md")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
