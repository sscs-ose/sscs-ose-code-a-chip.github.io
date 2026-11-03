#!/usr/bin/env python3
"""Confirm the NMOS-only top-plate switch in the full 8-bit converter (schematic) at the corners where the transmission
gate fails (ff / fs, 125 C) and where settling is tightest (ss, -40 C, 1.62 V).  Switch: one LVT NMOS, W = 2 x the
sized top_wn (studies/top_switch_screen.py).  Restartable: rows saved in build/8bit/studies/top_nmos/rows.json.
Writes results/8bit/sweeps/top_switch_nmos.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/top_switch_nmos8.py
"""
import copy, dataclasses, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, sweep

CORNERS = (("ff", 125, 1.0), ("fs", 125, 1.0), ("ss", -40, 0.9))


def main(hits=4):
    d = json.loads(Path("build/8bit/design.json").read_text())
    d = copy.deepcopy(d); d["sw"]["top_flavor"] = "nlvt"; d["sw"]["top_wn"] = 2 * d["sw"]["top_wn"]
    out = Path("build/8bit/studies/top_nmos"); out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    for c, t, s in CORNERS:
        b = SarSpec(bits=8)
        sp = dataclasses.replace(b, corner=c, temp=float(t), vdd=b.vdd * s, vref=b.vref * s)
        key = f"{c} {t:+d}C {sp.vdd:.2f}V"
        if key not in rows:
            rows[key] = sweep.evaluate(sp, d, out / key.replace(" ", "_"), hits=hits, fft_n=128)
            (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
        r = rows[key]
        print(f"{key}: ENOB {r['enob']:.2f} DNL {r['dnl_t']:.3f} INL {r['inl_t']:.3f} offset {r['offset_lsb']:+.2f} "
              f"gain {r['gain_lsb']:+.2f} {r['p_uw']:.0f} uW", flush=True)
    tg = json.loads(Path("build/8bit/studies/coverage/rows.json").read_text())
    md = ["| corner | switch | ENOB | DNL [LSB] | INL [LSB] | offset [LSB] | gain [LSB] |", "|---|---|---|---|---|---|---|"]
    for key, r in rows.items():
        if key in tg:
            g = tg[key]
            md.append(f"| {key} | LVT transmission gate (sized) | {g['enob']:.2f} | {g['dnl_t']:.3f} | {g['inl_t']:.3f} | "
                      f"{g['offset_lsb']:+.2f} | {g['gain_lsb']:+.2f} |")
        md.append(f"| {key} | LVT NMOS only, 2 W_n | {r['enob']:.2f} | {r['dnl_t']:.3f} | {r['inl_t']:.3f} | "
                  f"{r['offset_lsb']:+.2f} | {r['gain_lsb']:+.2f} |")
    md.append(f"\nSchematic, fixed 8-bit design except the top-plate switch; {hits} hits per code.")
    dst = Path("results/8bit/sweeps/top_switch_nmos.md"); dst.write_text("\n".join(md) + "\n")
    print(dst.read_text())


if __name__ == "__main__":
    main()
