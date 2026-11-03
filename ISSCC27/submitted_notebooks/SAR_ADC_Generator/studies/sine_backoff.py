#!/usr/bin/env python3
"""Separate clipping from distortion in the sine test: the standard test sine is 0.99 of full scale, so an offset of
a code or two pushes its peaks past the last code. Re-runs only the sine (schematic and full core from layout) at
-0.5 dBFS and compares with the full-scale numbers in build/<N>bit/postlayout/prepost.json.
Writes results/<N>bit/layout/sine_backoff.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/sine_backoff.py 8
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, metrics
from sargen.flow import simulate_codes
from sargen.layout import core as core_layout
from sargen.sweep import _coprime_cycles

AMP_DBFS = -0.5


def main(bits=8, fft_n=128):
    base = Path(f"build/{bits}bit")
    spec = SarSpec(bits=bits)
    design = json.loads((base / "design.json").read_text())
    full = json.loads((base / "postlayout" / "prepost.json").read_text())
    ver = base / "studies" / "top_switch_verify" / "rows.json"   # schematic of the current switch, same test
    if ver.exists() and "tt +27C 1.80V" in json.loads(ver.read_text()):
        full["schematic"] = json.loads(ver.read_text())["tt +27C 1.80V"]
    cyc = _coprime_cycles(fft_n)
    f_in = metrics.coherent_tone(spec.fs, fft_n, cyc)
    amp = spec.vref / 2 * 10 ** (AMP_DBFS / 20)
    out = base / "studies" / "sine_backoff"
    saved = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}   # restartable
    rows = []
    for name in ("schematic", "full core from layout"):
        if name not in saved:
            kw = core_layout.extracted(bits, base / "layout") if name != "schematic" else {}
            codes, _, _ = simulate_codes(spec, design, "sine", fft_n, out / name.replace(" ", "_"), 32, sine=(amp, f_in), **kw)
            f = metrics.fft_metrics(codes, spec.bits, cyc)
            clip = int(np.sum((codes == 0) | (codes == 2**bits - 1)))
            saved[name] = [f["enob"], f["sfdr_db"], clip, float(codes.mean() - (2**bits - 1) / 2)]
            (out / "rows.json").write_text(json.dumps(saved, indent=1))
        rows.append((name, full[name]["enob"], *saved[name]))
        print(rows[-1], flush=True)
    md = [f"{bits}-bit, {fft_n}-point coherent FFT at {f_in / 1e6:.2f} MHz. Full scale = 0.99 of the input range "
          f"(prepost.json); backed off = {AMP_DBFS:g} dBFS.", "",
          "| case | ENOB full scale | ENOB at -0.5 dBFS | SFDR at -0.5 dBFS [dB] | samples at the end codes | mean code - mid-scale |",
          "|---|---|---|---|---|---|"]
    md += [f"| {n} | {a:.2f} | {b:.2f} | {s:.1f} | {c} | {m:+.2f} |" for n, a, b, s, c, m in rows]
    dst = Path(f"results/{bits}bit/layout/sine_backoff.md")
    dst.write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
