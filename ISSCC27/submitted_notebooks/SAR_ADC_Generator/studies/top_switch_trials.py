#!/usr/bin/env python3
"""Transient trials of top-plate switch candidates (flavour and width) at the corners that decide them: fs / 125 C
(hot leakage) and ss / -40 C (cold kick recovery at the start of sampling).  Starts from the sized design in
build/<N>bit/design_lvt.json (only the top switch changes); every point is saved as it finishes (restartable).
Run inside IIC-OSIC-TOOLS:  python3 studies/top_switch_trials.py 8 mixl:47.3 lvtp7:81.2 [--hits 4]
"""
import argparse, copy, dataclasses, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, sweep

CORNERS = [("fs", 125, 1.0), ("ss", -40, 1.0)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("bits", type=int); ap.add_argument("cands", nargs="+")
    ap.add_argument("--hits", type=int, default=4); a = ap.parse_args()
    base = Path(f"build/{a.bits}bit"); spec = SarSpec(bits=a.bits)
    d0 = json.loads((base / "design_lvt.json").read_text())
    out = base / "studies" / "top_switch_trials"; out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((out / "rows.json").read_text()) if (out / "rows.json").exists() else {}
    for cand in a.cands:
        fl, wn = cand.split(":"); wn = float(wn)
        d = copy.deepcopy(d0); d["sw"].update(top_flavor=fl, top_wn=wn, top_wp=2 * wn)
        for c, t, s in CORNERS:
            sp = dataclasses.replace(spec, corner=c, temp=float(t), vdd=spec.vdd * s, vref=spec.vref * s)
            key = f"{fl} {wn:g}um {c} {t:+d}C"
            if key not in rows:
                rows[key] = sweep.evaluate(sp, d, out / key.replace(" ", "_"), hits=a.hits, fft_n=128)
                (out / "rows.json").write_text(json.dumps(rows, indent=1, default=float))
            r = rows[key]
            print(f"{key:28s} ENOB {r['enob']:.2f} DNL {r['dnl_t']:.3f} INL {r['inl_t']:.3f} offset {r['offset_lsb']:+.2f} "
                  f"gain {r['gain_lsb']:+.2f} {r['p_uw']:.0f} uW", flush=True)


if __name__ == "__main__":
    main()
