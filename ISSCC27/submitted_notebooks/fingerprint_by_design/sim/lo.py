"""LO quadrature generator: RC-CR network, per-chip I/Q gain and phase error.

I path: series R, shunt C (low-pass, -45 deg); Q path: series C, shunt R
(high-pass, +45 deg). Poly resistors (res_high_po) and MIM caps carry SKY130
per-instance mismatch, so each chip gets its own gain/phase imbalance. AC
analysis at FC is enough (linear network).
"""
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from spice import CORNER, PDK_LIB, SEED0, mc_control, parse_blocks, run_netlist

FC = 200e6
R_L = 5.0                 # res_high_po_0p35 length (um) -> ~6 kohm
C_W = C_L = 7.8           # MIM cap (um)


def netlist(temp, n_chips, seed0=None):
    seed0 = SEED0 if seed0 is None else seed0
    lines = [f"* RC-CR quadrature T={temp}",
             f'.lib "{PDK_LIB}" {CORNER}',
             f".temp {temp}",
             "Vs s 0 dc 0 ac 1",
             "Rs s in 50",
             f"XRi in vi 0 sky130_fd_pr__res_high_po_0p35 L={R_L} mult=1 m=1",
             f"XCi vi 0 sky130_fd_pr__cap_mim_m3_1 W={C_W} L={C_L} MF=1 m=1",
             f"XCq in vq sky130_fd_pr__cap_mim_m3_1 W={C_W} L={C_L} MF=1 m=1",
             f"XRq vq 0 0 sky130_fd_pr__res_high_po_0p35 L={R_L} mult=1 m=1",
             "Cli vi 0 5f",
             "Clq vq 0 5f"]
    body = (f"  ac lin 1 {FC} {FC}\n"
            "  print vm(vi) vp(vi) vm(vq) vp(vq)\n")
    return "\n".join(lines) + mc_control(n_chips, body, seed0) + ".end\n"


def parse(stdout):
    """-> {chip: array[4] = |vi|, ang(vi) rad, |vq|, ang(vq) rad}"""
    res = {}
    for chip, txt in parse_blocks(stdout).items():
        v = dict(re.findall(r"(v[mp]\(v[iq]\))\s*=\s*(\S+)", txt))
        res[chip] = np.array([float(v[k]) for k in
                              ("vm(vi)", "vp(vi)", "vm(vq)", "vp(vq)")])
    return res


def run(temp, n_chips, seed0=None):
    return temp, parse(run_netlist(netlist(temp, n_chips, seed0)))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    temps = [float(t) for t in sys.argv[2].split(",")] if len(sys.argv) > 2 else [27]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    with ProcessPoolExecutor(max_workers=min(len(temps), 8)) as ex:
        results = dict(ex.map(run, temps, [n] * len(temps)))
    chips = sorted(results[temps[0]])
    data = np.stack([np.stack([results[t][c] for c in chips]) for t in temps])
    gain_db = 20 * np.log10(data[..., 2] / data[..., 0])
    phase_err = np.degrees(data[..., 3] - data[..., 1]) - 90
    print("shape (T, chip, 4):", data.shape, "nan:", np.isnan(data).sum())
    print("IQ gain imbalance dB  mean per T:", gain_db.mean(1).round(3),
          " chip sigma:", gain_db.std(1).round(3))
    print("IQ phase error deg    mean per T:", phase_err.mean(1).round(3),
          " chip sigma:", phase_err.std(1).round(3))
    if out:
        np.savez(out, data=data, temps=np.array(temps), chips=np.array(chips))
