"""Energy of one SKY130 dfxtp_1 flip-flop per clock cycle in ngspice: idle (D constant) and with a
D/Q toggle, for the PDK's schematic netlist and the parasitic-extracted one, next to Liberty.

    python scripts/flop_energy.py        -> data/pdk/pex/flop_energy.json
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.spice.pulse_sweep import LIB_SLEW_FRAC, VDD, _cell_pins, _env, cell_spice_lib  # noqa: E402

P, SLEW, QLOAD = 4000.0, 40.0, 2.0
D = [0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0]          # D per cycle (changes in the low clock phase)


def run(cells):
    if cells == "pex":
        os.environ["GS_CELL_SPICE"] = "data/pdk/pex/sky130_fd_sc_hd_pex.spice"
    else:
        os.environ.pop("GS_CELL_SPICE", None)
    lib, pdk = cell_spice_lib(), Path(_env("GS_PDK_ROOT"))
    tr = SLEW / LIB_SLEW_FRAC
    pins = _cell_pins(lib, "dfxtp_1")
    m = {"CLK": "clk", "D": "d", "Q": "q", "VGND": "0", "VNB": "0", "VPWR": "vff", "VPB": "vff"}
    pw, v = [(0, 0)], 0
    for k, x in enumerate(D):
        t = k * P + 0.1 * P
        if x != v:
            pw += [(t, v), (t + tr, x)]
            v = x
    with tempfile.TemporaryDirectory(prefix="gs_ff_") as td:
        td = Path(td)
        L = [".option scale=1e-6", f'.lib "{pdk / "libs.tech/ngspice/sky130.lib.spice"}" tt', f'.include "{lib}"',
             ".temp 25", f"Vff vff 0 {VDD}", f"Vclk clk 0 PULSE(0 {VDD} {P / 2}p {tr}p {tr}p {P / 2 - tr}p {P}p)",
             f"Vd d 0 PWL({' '.join(f'{t}p {x * VDD}' for t, x in pw)})",
             f"X1 {' '.join(m[p] for p in pins)} sky130_fd_sc_hd__dfxtp_1", f"Cq q 0 {QLOAD}f",
             ".control", "set wr_singlescale", "set wr_vecnames", f"tran 1p {len(D) * P}p 0 1p", "linearize",
             f"wrdata {td}/w.txt i(Vff)", "quit", ".endc", ".end"]
        (td / "d.sp").write_text("\n".join(L) + "\n")
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        subprocess.run([_env("GS_NGSPICE"), "-b", "d.sp"], cwd=td, capture_output=True)
        d = np.loadtxt(td / "w.txt", skiprows=1)
    t, p = d[:, 0] * 1e12, -d[:, 1] * VDD
    E = [float(np.trapezoid(p[(t >= k * P) & (t < (k + 1) * P)], t[(t >= k * P) & (t < (k + 1) * P)] * 1e-12)) * 1e15
         for k in range(1, len(D))]
    idle = [e for k, e in enumerate(E, 1) if D[k] == D[k - 1]]
    tog = [e for k, e in enumerate(E, 1) if D[k] != D[k - 1]]
    return dict(idle_fJ=float(np.mean(idle)), toggle_fJ=float(np.mean(tog)))


def main():
    from glitchscope.liberty import parse_liberty_file
    from glitchscope.seqpower import FlopEnergy        # the Liberty numbers GlitchScope itself uses
    out = {c: run(c) for c in ("schematic", "pex")}
    lib = parse_liberty_file(_env("GS_LIB"))
    fe = FlopEnergy(_env("GS_LIB"), lib, {"sky130_fd_sc_hd__dfxtp_1"})
    cell = "sky130_fd_sc_hd__dfxtp_1"
    out["liberty_clock_internal_fJ"] = fe._e(cell, "CLK", "rise_power", SLEW) + fe._e(cell, "CLK", "fall_power", SLEW)
    out["clk_pin_cap_ff"] = lib.cells[cell].pin_capacitance.get("CLK")
    (ROOT / "data/pdk/pex/flop_energy.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
