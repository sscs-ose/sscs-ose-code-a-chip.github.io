#!/usr/bin/env python3
"""Real sources instead of ideal ones (schematic, fixed design): every external source reaches the tile through a
TinyTapeout analog pin, at most 500 Ohm and 5 pF (tinytapeout.com/specs/analog).  Vref and Vcm get an on-chip
decap behind that resistance; the input carries the pad path.  Which decap keeps the converter linear?
Writes results/<N>bit/sweeps/source_impedance.md.  Run inside IIC-OSIC-TOOLS:
    python3 studies/source_impedance.py 4 [hits]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, sweep

R_PIN, C_PIN = 500.0, 5e-12


def cases(c_total):
    """(label, ext) pairs; decaps scaled to the CDAC's total capacitance."""
    out = [("ideal sources", {}), ("input through the pin", {"vin": (R_PIN, C_PIN)})]
    for k in (10, 100):
        dec = k * c_total
        out.append((f"vref, vcm decap {k} x C_DAC ({dec * 1e12:.0f} pF)",
                    {"vref": (R_PIN, dec), "vcm": (R_PIN, dec)}))
    out.append((f"all three (decap 100 x C_DAC)", {"vin": (R_PIN, C_PIN), "vref": (R_PIN, 100 * c_total),
                                                   "vcm": (R_PIN, 100 * c_total)}))
    return out


def main(bits=4, hits=16):
    base = Path(f"build/{bits}bit")
    d = json.loads((base / "design.json").read_text())
    out = base / "studies" / "source_impedance"
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    for label, ext in cases(d["cu"]["c_total"]):
        if label in rows:
            continue
        r = sweep.evaluate(SarSpec(bits=bits), d, out / str(len(rows)), hits=hits, fft_n=128, ext=ext)
        rows[label] = r
        out.mkdir(parents=True, exist_ok=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
        print(f"{label:40s} ENOB {r['enob']:.2f} DNL {r['dnl_t']:.3f} INL {r['inl_t']:.3f} "
              f"offset {r['offset_lsb']:+.2f} gain {r['gain_lsb']:+.2f}", flush=True)
    md = ["| sources | ENOB | DNL [LSB] | INL [LSB] | offset [LSB] | gain [LSB] | power [uW] |", "|---|---|---|---|---|---|---|"]
    for label, r in rows.items():
        md.append(f"| {label} | {r['enob']:.2f} | {r['dnl_t']:.3f} | {r['inl_t']:.3f} | {r['offset_lsb']:+.2f} "
                  f"| {r['gain_lsb']:+.2f} | {r['p_uw']:.1f} |")
    md.append(f"\nEach source through {R_PIN:.0f} Ohm (TinyTapeout analog pin); input pin {C_PIN * 1e12:.0f} pF; "
              f"{hits} hits per code.")
    dst = Path(f"results/{bits}bit/sweeps/source_impedance.md")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(md) + "\n")
    print(dst.read_text())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4, int(sys.argv[2]) if len(sys.argv) > 2 else 16)
