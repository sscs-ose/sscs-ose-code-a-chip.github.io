"""Local (mismatch) delay variation of SKY130 HD cells from the PDK's SPICE Monte-Carlo models.

N copies of each cell, every one with its own random mismatch (``.lib ... tt_mm``), are
driven by the same input ramp into the same load; the spread of their 50 %-50 % delays
gives the relative sigma of a cell's delay under local variation, per cell and edge.

    python scripts/mismatch_sigma.py [N] [cell ...]      -> data/mismatch/sigma.json
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

CELLS = {"inv_1": "A", "buf_1": "A", "nand2_1": "A", "nor2_1": "A", "and2_1": "A", "or2_1": "A",
         "xor2_1": "A", "xnor2_1": "A", "a21oi_1": "A1", "o21ai_0": "A1", "nand3_1": "A"}
SENSITISE = {"nand2_1": 1, "nand3_1": 1, "and2_1": 1, "nor2_1": 0, "or2_1": 0, "xor2_1": 0, "xnor2_1": 0,
             "a21oi_1": None, "o21ai_0": None}


def side_value(cell, pin):
    if cell in ("a21oi_1",):
        return {"A2": 1, "B1": 0}.get(pin, 0)
    if cell in ("o21ai_0",):
        return {"A2": 0, "B1": 1}.get(pin, 0)
    return SENSITISE.get(cell, 0)


def run(cell, pin, n, rising_in, corner="tt_mm", load_ff=5.0, slew_ps=60.0):
    pdk = Path(_env("GS_PDK_ROOT"))
    lib = pdk / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
    models = pdk / "libs.tech/ngspice/sky130.lib.spice"
    pins = _cell_pins(lib, cell)
    out = next(p for p in pins if p in ("Y", "X"))
    tr = slew_ps * 1e-12 / 0.6
    a, b = (0.0, VDD) if rising_in else (VDD, 0.0)
    L = [".option scale=1e-6", f'.lib "{models}" {corner}', f'.include "{lib}"', ".temp 25", f"Vdd vpwr 0 {VDD}",
         f"Vin in 0 PWL(0 {a} 200p {a} {200e-12 + tr:.4e} {b})"]
    for i in range(n):
        conn = []
        for p in pins:
            if p in ("VGND", "VNB"):
                conn.append("0")
            elif p in ("VPWR", "VPB"):
                conn.append("vpwr")
            elif p == out:
                conn.append(f"o{i}")
            elif p == pin:
                conn.append("in")
            else:
                conn.append("vpwr" if side_value(cell, p) else "0")
        L.append(f"X{i} {' '.join(conn)} sky130_fd_sc_hd__{cell}")
        L.append(f"C{i} o{i} 0 {load_ff * 1e-15:.3e}")
    with tempfile.TemporaryDirectory(prefix="gs_mm_") as td:
        td = Path(td)
        L += [".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=7", "tran 0.5p 2n", "linearize",
              f"wrdata {td}/w.txt " + " ".join(f"v(o{i})" for i in range(n)), "quit", ".endc", ".end"]
        (td / "d.sp").write_text("\n".join(L) + "\n")
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        r = subprocess.run([_env("GS_NGSPICE"), "-b", "d.sp"], cwd=td, capture_output=True, text=True)
        if not (td / "w.txt").exists():
            raise RuntimeError(r.stdout[-1500:])
        d = np.loadtxt(td / "w.txt", skiprows=1)
    t = d[:, 0]
    t_in = 200e-12 + tr / 2
    dl = []
    for i in range(n):
        v = d[:, 1 + i] - VDD / 2
        idx = np.nonzero(np.diff(np.sign(v)) != 0)[0]
        if len(idx):
            k = idx[0]
            dl.append((t[k] - v[k] * (t[k + 1] - t[k]) / (v[k + 1] - v[k]) - t_in) * 1e12)
    return np.array(dl)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    cells = sys.argv[2:] or list(CELLS)
    out = ROOT / "data/mismatch/sigma.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(out.read_text()) if out.exists() else {}
    for c in cells:
        row = {}
        for rising in (True, False):
            d = run(c, CELLS[c], n, rising)
            nom = run(c, CELLS[c], 1, rising, corner="tt")[0]
            row["in_rise" if rising else "in_fall"] = dict(n=len(d), mean_ps=float(d.mean()), sd_ps=float(d.std(ddof=1)),
                                                           rel_sigma=float(d.std(ddof=1) / d.mean()), nominal_ps=float(nom))
        row["rel_sigma"] = float(np.mean([row["in_rise"]["rel_sigma"], row["in_fall"]["rel_sigma"]]))
        res[c] = row
        out.write_text(json.dumps(res, indent=1))
        print(f"{c:9s} rel sigma {100 * row['rel_sigma']:5.2f} %   (rise {row['in_rise']['mean_ps']:6.1f} ps, "
              f"nominal {row['in_rise']['nominal_ps']:6.1f} ps)", flush=True)


if __name__ == "__main__":
    main()
