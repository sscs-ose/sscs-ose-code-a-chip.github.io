#!/usr/bin/env python3
"""Top-plate switch device flavour vs. PVT (fixed 4-bit design, schematic): which threshold combination keeps
linearity at hot, leaky corners and still settles cold?  Writes results/4bit/sweeps/top_switch_leakage.md.

Flavours (sargen.pdk.TG_FLAVORS): lvt (LVT N + LVT P, the sized design), std (SVT N + SVT P),
mix (SVT N + LVT P), mixp (LVT N + SVT P).  Each point is a full ramp + FFT transient (~3-6 min).
Run inside IIC-OSIC-TOOLS:  python3 studies/top_switch_leakage.py
"""
import copy, dataclasses, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, sweep

CORNERS = [("fs", 125, 1.0), ("ff", 125, 1.0), ("tt", 27, 1.0), ("ss", -40, 1.0), ("ss", -40, 0.9)]


def main(flavours=("lvt", "std", "mix", "mixp")):
    base = Path("build/4bit")
    d0 = json.loads((base / "design.json").read_text())
    out = base / "studies" / "top_switch"
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    for fl in flavours:
        d = copy.deepcopy(d0)
        d["sw"]["top_flavor"] = fl
        for c, t, s in CORNERS:
            key = f"{fl} {c} {t:+d}C {s * 1.8:.2f}V"
            if key in rows:
                continue
            b = SarSpec(bits=4, fs=10e6)
            sp = dataclasses.replace(b, corner=c, temp=float(t), vdd=b.vdd * s, vref=b.vref * s)
            r = sweep.evaluate(sp, d, out / key.replace(" ", "_"), hits=16, fft_n=128)
            rows[key] = r
            out.mkdir(parents=True, exist_ok=True)
            (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
            print(f"{key:28s} ENOB {r['enob']:.2f} DNL {r['dnl_t']:.3f} offset {r['offset_lsb']:+.2f}", flush=True)
    write_md(rows)


def write_md(rows):
    md = ["| top-plate switch | corner | ENOB | DNL [LSB] | INL [LSB] | offset [LSB] | gain [LSB] | power [uW] |",
          "|---|---|---|---|---|---|---|---|"]
    for k, r in rows.items():
        fl, corner = k.split(" ", 1)
        md.append(f"| {fl} | {corner} | {r['enob']:.2f} | {r['dnl_t']:.3f} | {r['inl_t']:.3f} | {r['offset_lsb']:+.2f} | "
                  f"{r['gain_lsb']:+.2f} | {r['p_uw']:.1f} |")
    p = Path("results/4bit/sweeps/top_switch_leakage.md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
