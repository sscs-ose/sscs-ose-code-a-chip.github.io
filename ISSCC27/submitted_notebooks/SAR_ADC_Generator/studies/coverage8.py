#!/usr/bin/env python3
"""8-bit robustness of the fixed design (schematic): ENOB / SFDR vs. input frequency up to ~fs/2, and the worst PVT
corners of the 4-bit sweep (cold slow, hot fast, hot fs leakage, cold sf, low supply).  Restartable: every point is
saved to build/8bit/studies/coverage/rows.json as it finishes and skipped on a rerun.
Writes results/8bit/sweeps/coverage8.md.  Run:  python3 studies/coverage8.py [hits]
"""
import dataclasses, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, metrics, sweep
from sargen.flow import simulate_codes

FFT_N = 128
FIN_CYCLES = (3, 13, 31, 47, 59, 63)                       # coherent, coprime with 128: 0.023 ... 0.492 fs
CORNERS = (("ss", -40, 1.0), ("ff", 125, 1.0), ("fs", 125, 1.0), ("sf", -40, 1.0), ("tt", 27, 0.9))


def main(hits=4):
    spec = SarSpec(bits=8)
    d = json.loads(Path("build/8bit/design.json").read_text())
    out = Path("build/8bit/studies/coverage")
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}

    def save(key, r):
        rows[key] = r
        (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))

    for c in FIN_CYCLES:
        key = f"fin {c / FFT_N:.3f} fs"
        if key not in rows:
            f_in = metrics.coherent_tone(spec.fs, FFT_N, c)
            codes, _, _ = simulate_codes(spec, d, "sine", FFT_N, out / f"fin_{c}", 32, sine=(spec.vref / 2 * 0.99, f_in))
            f = metrics.fft_metrics(codes, spec.bits, c)
            save(key, dict(f_in=f_in, enob=f["enob"], sndr_db=f["sndr_db"], sfdr_db=f["sfdr_db"]))
        print(f"{key}: ENOB {rows[key]['enob']:.2f} SFDR {rows[key]['sfdr_db']:.1f} dB", flush=True)
    for c, t, s in CORNERS:
        sp = dataclasses.replace(spec, corner=c, temp=float(t), vdd=spec.vdd * s, vref=spec.vref * s)
        key = f"{c} {t:+d}C {sp.vdd:.2f}V"
        if key not in rows:
            save(key, sweep.evaluate(sp, d, out / key.replace(" ", "_"), hits=hits, fft_n=FFT_N))
        r = rows[key]
        print(f"{key}: ENOB {r['enob']:.2f} DNL {r['dnl_t']:.3f} INL {r['inl_t']:.3f} offset {r['offset_lsb']:+.2f} "
              f"gain {r['gain_lsb']:+.2f} {r['p_uw']:.0f} uW", flush=True)
    md = ["| input frequency | ENOB | SNDR [dB] | SFDR [dB] |", "|---|---|---|---|"]
    md += [f"| {k[4:]} ({r['f_in'] / 1e6:.2f} MHz) | {r['enob']:.2f} | {r['sndr_db']:.1f} | {r['sfdr_db']:.1f} |"
           for k, r in rows.items() if k.startswith("fin")]
    md += ["", "| PVT point | ENOB | DNL [LSB] | INL [LSB] | offset [LSB] | gain [LSB] | power [uW] |",
           "|---|---|---|---|---|---|---|"]
    md += [f"| {k} | {r['enob']:.2f} | {r['dnl_t']:.3f} | {r['inl_t']:.3f} | {r['offset_lsb']:+.2f} | "
           f"{r['gain_lsb']:+.2f} | {r['p_uw']:.0f} |" for k, r in rows.items() if not k.startswith("fin")]
    md.append(f"\nSchematic, fixed 8-bit design at 10 MS/s; PVT points use {hits} hits per code "
              f"(DNL/INL/offset/gain resolved to 1/{hits} LSB), FFT {FFT_N} points.")
    dst = Path("results/8bit/sweeps/coverage8.md")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(md) + "\n")
    print(dst.read_text())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
