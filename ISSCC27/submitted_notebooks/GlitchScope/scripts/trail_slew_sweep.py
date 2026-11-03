"""Does the slew of a pulse's *trailing* edge move the rejection threshold?

M2's threshold r_filter was calibrated on input pulses whose two edges have the same slew.
Inside deep logic the two edges of a pulse often come from different paths (or from a
rising and a falling output of an unbalanced gate) with very different slews.  A slow
trailing edge starts to turn the gate back before its 50 % point, so the pulse must be
wider to get through.  This sweep measures that, per cell arc, with ngspice: the 50 %-to-50 %
input width at which the output just crosses VDD/2, for a leading slew s1 and trailing
slews s2 = s1, s1 + 80 ps, s1 + 260 ps.  The slope

    alpha = d w_threshold / d (s2 - s1)

is the fraction of the trailing slew by which the trailing edge acts early.  M2 uses it as
w_eff = w - alpha (s2 - s1) (``trail_slew_alpha`` in m2_model.json, per cell and output polarity).

    python scripts/trail_slew_sweep.py <liberty>     -> data/m2/trail_slew_sweep.json
"""
import itertools
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.spice.pulse_sweep import (CELLS, LIB_SLEW_FRAC, VDD, _cell_pins, _env,  # noqa: E402
                                           cell_spice_lib, ensure_cells)

M2_CELLS = ["inv_1", "buf_1", "nand2_1", "nor2_1", "and2_1", "or2_1", "xor2_1", "xnor2_1",
            "a21oi_1", "o21ai_0", "nand3_1", "a22oi_1"]
WIDTHS = np.geomspace(4, 900, 70)          # ps, 50 %-to-50 % input width
DSLEW = (0.0, 80.0, 260.0)


def deck(cell, pol, s1, s2, load, outfile):
    pdk = Path(_env("GS_PDK_ROOT"))
    lib = cell_spice_lib()
    inp, out, side, _ = CELLS[cell]
    pins = _cell_pins(lib, cell)
    tr1, tr2 = s1 / LIB_SLEW_FRAC, s2 / LIB_SLEW_FRAC              # full ramp times, ps
    v0, sgn = (0.0, 1.0) if pol == "pos" else (VDD, -1.0)
    t0 = 400.0
    L = [".option scale=1e-6", f'.lib "{pdk / "libs.tech/ngspice/sky130.lib.spice"}" tt', f'.include "{lib}"',
         ".temp 25", f"Vdd vpwr 0 {VDD}"]
    for i, w in enumerate(WIDTHS):
        a0, a1 = t0 - tr1 / 2, t0 + tr1 / 2
        b0, b1 = t0 + w - tr2 / 2, t0 + w + tr2 / 2
        ts = np.unique(np.concatenate([[0, a0, a1, b0, b1], np.linspace(a0, b1, 60)]))
        x = np.minimum(np.clip((ts - a0) / tr1, 0, 1), np.clip((b1 - ts) / tr2, 0, 1))
        v = v0 + sgn * VDD * x
        L.append(f"Vin{i} a{i} 0 PWL(" + " ".join(f"{t:.3f}p {y:.4f}" for t, y in zip(ts, v)) + ")")
        conn = []
        for p in pins:
            conn.append({"VGND": "0", "VNB": "0", "VPWR": "vpwr", "VPB": "vpwr"}.get(p) or
                        (f"a{i}" if p == inp else f"y{i}" if p == out else ("vpwr" if side[p] else "0")))
        L.append(f"X{i} {' '.join(conn)} sky130_fd_sc_hd__{cell}")
        L.append(f"C{i} y{i} 0 {load}f")
    tstop = t0 + WIDTHS[-1] + tr2 + 1500
    L += [".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=6", f"tran 0.5p {tstop:.0f}p",
          "linearize", f"wrdata {outfile} " + " ".join(f"v(y{i})" for i in range(len(WIDTHS))), "quit", ".endc", ".end"]
    return "\n".join(L) + "\n"


def threshold(cell, pol, s1, s2, load):
    with tempfile.TemporaryDirectory(prefix="gs_ts_") as td:
        td = Path(td)
        (td / "d.sp").write_text(deck(cell, pol, s1, s2, load, td / "w.txt"))
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\nset num_threads=1\n")
        r = subprocess.run([_env("GS_NGSPICE"), "-b", "d.sp"], cwd=td, capture_output=True, text=True)
        if not (td / "w.txt").exists():
            raise RuntimeError(r.stdout[-1500:])
        d = np.loadtxt(td / "w.txt", skiprows=1)
    v = d[:, 1:]
    peak = np.abs(v - v[0]).max(axis=0) / VDD
    k = np.nonzero(peak >= 0.5)[0]
    if not len(k) or k[0] == 0:
        return None
    i = k[0]                                     # interpolate the 0.5 crossing of peak(w) in log w
    lw = np.interp(0.5, [peak[i - 1], peak[i]], np.log([WIDTHS[i - 1], WIDTHS[i]]))
    return float(np.exp(lw))


def run(args):
    cell, pol, s1, load = args
    ws = [threshold(cell, pol, s1, s1 + ds, load) for ds in DSLEW]
    ok = [(ds, w) for ds, w in zip(DSLEW, ws) if w is not None]
    alpha = float(np.polyfit([a for a, _ in ok], [b for _, b in ok], 1)[0]) if len(ok) >= 2 else None
    inv = CELLS[cell][3]
    out_pol = ("negative" if pol == "pos" else "positive") if inv else ("positive" if pol == "pos" else "negative")
    return dict(cell=cell, input_pulse=pol, out_polarity=out_pol, slew_ps=s1, load_ff=load,
                w_threshold_ps=ws, alpha=alpha)


def main():
    lib = sys.argv[1]
    from glitchscope.liberty import parse_liberty_file
    ensure_cells(parse_liberty_file(lib), M2_CELLS)
    jobs = list(itertools.product(M2_CELLS, ("pos", "neg"), (40.0, 120.0), (2.0, 10.0)))
    rows = []
    with ThreadPoolExecutor(2) as ex:
        for r in ex.map(run, jobs):
            rows.append(r)
            print(f"{r['cell']:8s} out {r['out_polarity']:8s} slew {r['slew_ps']:5.0f} load {r['load_ff']:4.0f}: "
                  f"w_th {[round(w, 1) if w else None for w in r['w_threshold_ps']]}  alpha "
                  f"{r['alpha'] and round(r['alpha'], 3)}", flush=True)
    summ = {}
    for cell in M2_CELLS:
        for pol in ("positive", "negative"):
            a = [r["alpha"] for r in rows if r["cell"] == cell and r["out_polarity"] == pol and r["alpha"] is not None]
            if a:
                summ.setdefault(cell, {})[pol] = float(np.median(a))
    allv = [r["alpha"] for r in rows if r["alpha"] is not None]
    print("median alpha per cell / output polarity:", json.dumps(summ))
    print(f"all arcs: median {np.median(allv):.3f}, range {min(allv):.3f}-{max(allv):.3f}")
    (ROOT / "data/m2/trail_slew_sweep.json").write_text(json.dumps(dict(rows=rows, alpha=summ), indent=1))


if __name__ == "__main__":
    main()
