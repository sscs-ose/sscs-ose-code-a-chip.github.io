#!/usr/bin/env python3
"""Verify the leakage-aware top-plate switch (sargen/sizing.py) by transient simulation at the corners that broke or
stress the old LVT switch: hot fast (ff / fs, 125 C) for leakage, cold slow (ss / sf, -40 C) for settling, and tt.
Re-sizes the design from the cached PDK characterization (only the switch differs), keeps the previous design as
design_lvt.json, and saves every point as it finishes (restartable).
Writes results/<N>bit/sweeps/top_switch_verify.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/top_switch_verify.py 8 [hits]
"""
import dataclasses, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, sweep
from sargen.characterize import characterize_pdk
from sargen.sizing import size_sar

CORNERS = [("fs", 125, 1.0), ("ff", 125, 1.0), ("ss", -40, 1.0), ("sf", -40, 1.0), ("tt", 27, 1.0)]


def main(bits=8, hits=4):
    base = Path(f"build/{bits}bit")
    spec = SarSpec(bits=bits)
    old = json.loads((base / "design.json").read_text())
    if not (base / "design_lvt.json").exists() and "top_flavor" not in old["sw"]:
        shutil.copy(base / "design.json", base / "design_lvt.json")
    d = size_sar(spec, characterize_pdk(spec, Path("build/char")))
    (base / "design.json").write_text(json.dumps(d, indent=1))
    sw = d["sw"]
    print(f"{bits} bit: top switch {sw['top_flavor']} {sw['top_wn']}/{sw['top_wp']} um", flush=True)
    out = base / "studies" / "top_switch_verify"
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    for c, t, s in CORNERS:
        sp = dataclasses.replace(spec, corner=c, temp=float(t), vdd=spec.vdd * s, vref=spec.vref * s)
        key = f"{c} {t:+d}C {sp.vdd:.2f}V"
        if key not in rows:
            rows[key] = sweep.evaluate(sp, d, out / key.replace(" ", "_"), hits=hits, fft_n=128)
            (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
        r = rows[key]
        print(f"{key}: ENOB {r['enob']:.2f} DNL {r['dnl_t']:.3f} INL {r['inl_t']:.3f} offset {r['offset_lsb']:+.2f} "
              f"gain {r['gain_lsb']:+.2f} {r['p_uw']:.0f} uW", flush=True)
    md = [f"Top-plate switch {sw['top_flavor']} ({sw['top_wn']}/{sw['top_wp']} um), {bits}-bit schematic, {hits} hits per code.", "",
          "| PVT point | ENOB | DNL [LSB] | INL [LSB] | offset [LSB] | gain [LSB] | power [uW] |", "|---|---|---|---|---|---|---|"]
    md += [f"| {k} | {r['enob']:.2f} | {r['dnl_t']:.3f} | {r['inl_t']:.3f} | {r['offset_lsb']:+.2f} | {r['gain_lsb']:+.2f} "
           f"| {r['p_uw']:.0f} |" for k, r in rows.items()]
    dst = Path(f"results/{bits}bit/sweeps/top_switch_verify.md"); dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8, int(sys.argv[2]) if len(sys.argv) > 2 else 4)
