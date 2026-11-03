"""Glitch *generation* inside a gate: two inputs switch in opposite directions, the one that
opens the output first leading by a skew D.  The logical output pulse is D wide; this script
finds, with ngspice on the SKY130 transistor models, the smallest D at which the output really
crosses VDD/2, normalises it by the gate's own delay for the leading edge and compares it with
the M2 rejection threshold r_filter, which is calibrated on pulses *propagating* through the gate.

    python scripts/generation_sweep.py        -> data/m2/generation_sweep.json
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.spice.pulse_sweep import _env, _cell_pins, VDD  # noqa: E402

# cell: (initial (first, second), output pulse polarity); 'first' opens the output, 'second' closes it
CASES = {"nor2_1": ((1, 0), "positive"), "or2_1": ((1, 0), "negative"),
         "nand2_1": ((0, 1), "negative"), "and2_1": ((0, 1), "positive")}
SKEWS = np.round(np.concatenate([np.arange(0, 100, 4), np.arange(100, 400, 15)]), 1)   # ps


def deck(cell, first, second, init, slew_ps, load_ff, outfile):
    pdk = Path(_env("GS_PDK_ROOT"))
    lib = pdk / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
    pins = _cell_pins(lib, cell)
    out = next(p for p in pins if p in ("Y", "X"))
    tr = slew_ps * 1e-12 / 0.6
    v1, v2 = init
    L = [".option scale=1e-6", f'.lib "{pdk / "libs.tech/ngspice/sky130.lib.spice"}" tt', f'.include "{lib}"',
         ".temp 25", f"Vdd vpwr 0 {VDD}"]
    insts = [("ref", None)] + [(f"s{i}", float(d)) for i, d in enumerate(SKEWS)]
    for name, d in insts:
        t1 = 300e-12
        a, b = v1 * VDD, (1 - v1) * VDD
        L.append(f"Vf{name} f{name} 0 PWL(0 {a} {t1:.4e} {a} {t1 + tr:.4e} {b})")
        if d is None:                      # reference: second input stays put -> nominal delay of the first edge
            L.append(f"Vs{name} s{name} 0 {v2 * VDD}")
        else:
            t2 = t1 + d * 1e-12
            a2, b2 = v2 * VDD, (1 - v2) * VDD
            L.append(f"Vs{name} s{name} 0 PWL(0 {a2} {t2:.4e} {a2} {t2 + tr:.4e} {b2})")
        conn = []
        for p in pins:
            conn.append({"VGND": "0", "VNB": "0", "VPWR": "vpwr", "VPB": "vpwr"}.get(p) or
                        (f"o{name}" if p == out else f"f{name}" if p == first else f"s{name}"))
        L.append(f"X{name} {' '.join(conn)} sky130_fd_sc_hd__{cell}")
        L.append(f"C{name} o{name} 0 {load_ff * 1e-15:.3e}")
    L += [".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=7", "tran 0.5p 1.5n", "linearize",
          f"wrdata {outfile} " + " ".join(f"v(o{n})" for n, _ in insts), "quit", ".endc", ".end"]
    return "\n".join(L) + "\n", insts, 300e-12 + tr / 2


def run(cell, first, second, slew_ps, load_ff):
    init, pol = CASES[cell]
    with tempfile.TemporaryDirectory(prefix="gs_gen_") as td:
        td = Path(td)
        txt, insts, t50 = deck(cell, first, second, init, slew_ps, load_ff, td / "w.txt")
        (td / "d.sp").write_text(txt)
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        r = subprocess.run([_env("GS_NGSPICE"), "-b", "d.sp"], cwd=td, capture_output=True, text=True)
        if not (td / "w.txt").exists():
            raise RuntimeError(r.stdout[-1500:])
        dat = np.loadtxt(td / "w.txt", skiprows=1)
    t, v = dat[:, 0], dat[:, 1:]
    rising = pol == "positive"
    ref = v[:, 0] - VDD / 2
    k = np.nonzero(np.diff(np.sign(ref)) != 0)[0][0]
    delay = (t[k] - ref[k] * (t[k + 1] - t[k]) / (ref[k + 1] - ref[k]) - t50) * 1e12
    peak = [(v[:, i].max() if rising else VDD - v[:, i].min()) / VDD for i in range(1, v.shape[1])]
    cross = [p > 0.5 for p in peak]
    full = [p > 0.9 for p in peak]
    d_cross = next((float(s) for s, c in zip(SKEWS, cross) if c), None)
    d_full = next((float(s) for s, c in zip(SKEWS, full) if c), None)
    return dict(cell=cell, first=first, slew_ps=slew_ps, load_ff=load_ff, polarity=pol, delay_ps=delay,
                skew_cross_ps=d_cross, skew_full_ps=d_full,
                r_gen=d_cross / delay if d_cross is not None else None,
                r_gen_full=d_full / delay if d_full is not None else None,
                peaks=[round(p, 3) for p in peak])


def main():
    from glitchscope.m2model import M2Model
    m2 = M2Model()
    rows = []
    for cell in CASES:
        for first, second in (("A", "B"), ("B", "A")):
            for slew in (40.0, 120.0):
                for load in (2.0, 10.0):
                    r = run(cell, first, second, slew, load)
                    cal = m2.cells.get(cell, {}).get(r["polarity"], {}).get("r_filter")
                    x = slew / r["delay_ps"]
                    r["r_filter_m2"] = min(2.5, max(0.3, cal["a"] + cal["b"] * x)) if cal else None
                    rows.append(r)
                    print(f"{cell:8s} {first} first slew {slew:5.0f} load {load:4.0f}  delay {r['delay_ps']:6.1f} ps  "
                          f"crosses at skew {r['skew_cross_ps']} ps -> r_gen {r['r_gen'] and round(r['r_gen'], 2)}  "
                          f"(M2 r_filter {r['r_filter_m2'] and round(r['r_filter_m2'], 2)})", flush=True)
    (ROOT / "data/m2/generation_sweep.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
