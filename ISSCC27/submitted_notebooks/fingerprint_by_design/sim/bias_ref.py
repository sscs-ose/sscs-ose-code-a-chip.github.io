"""On-chip bias reference: beta-multiplier (constant-gm) self-biased current
reference with start-up, replacing the ideal 10/10/100 uA sources.

Core:  M1 nmos (n1 diode), M2 nmos (K=4x M1, source resistor Rs to ground),
       M3/M4 pmos mirror (M4 diode on pg).  I_core ~ 2/(un Cox (W/L)1 Rs^2) (1-1/sqrt K)^2
Start-up: weak long PMOS pulls 'st' high when the core is off; Ms3 then pulls pg
       low until current flows and M1's gate (n1) turns Ms2 on, which drops 'st'.
Outputs: PMOS mirror branches from pg sourcing 1x (10 uA) into the I and Q DAC
       reference diodes and 10x (100 uA) into the PA bias diode.
"""
import re
import sys

import numpy as np

from spice import PDK_LIB, mc_control, run_netlist

NF, PF = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"
W1, LN = 2.0, 1.0            # M1; M2 = 4 x W1
WP, LP = 2.0, 1.0            # pmos mirror unit
RS_L = 6.45                  # xhigh_po_1p41 length (um) for Rs: 10 uA at 27 C (tt), tuned
# n-diffusion Rs: positive tempco (+19.5% over -40..85 C) partly cancels the falling
# mobility; the xhigh-poly Rs (-16%) roughly doubled the current over temperature
RS_TYPE = "nd"
RS_ND_W, RS_ND_L = 1.0, 80.0


def rs_line(rs_l=None):
    if RS_TYPE == "nd":
        return f"XRs nr 0 0 sky130_fd_pr__res_generic_nd W={RS_ND_W} L={rs_l or RS_ND_L}"
    return f"XRs nr 0 0 sky130_fd_pr__res_xhigh_po_1p41 L={rs_l or RS_L} mult=1 m=1"


def core(rs_l=None, outs=(("bi", 1), ("bq", 1), ("bpa", 10)), p="bias_"):
    """subcircuit body lines; outputs source current into the given nodes. Internal
    nodes carry the prefix p so they cannot collide with the host netlist (an
    unprefixed 'pg' once shorted the reference to the PA gate node)."""
    n1, pg, nr, st = (p + x for x in ("n1", "pg", "nr", "st"))
    lines = [f"X{p}M1 {n1} {n1} 0 0 {NF} W={W1} L={LN}",
             f"X{p}M2 {pg} {n1} {nr} 0 {NF} W={4 * W1} L={LN}",
             rs_line(rs_l).replace("XRs nr", f"X{p}Rs {nr}"),
             f"X{p}M3 {n1} {pg} vdd vdd {PF} W={WP} L={LP}",
             f"X{p}M4 {pg} {pg} vdd vdd {PF} W={WP} L={LP}",
             f"X{p}Ms1 {st} 0 vdd vdd {PF} W=0.42 L=10",
             f"X{p}Ms2 {st} {n1} 0 0 {NF} W=1 L=0.5",
             f"X{p}Ms3 {pg} {st} 0 0 {NF} W=1 L=0.5"]
    for node, mult in outs:
        # an xN branch is one N-finger device of N x WP total width (per-finger width WP, so it
        # mirrors like N unit devices; a single wide finger mirrored ~15% low)
        lines.append(f"X{p}Mo_{node} {node} {pg} vdd vdd {PF} W={WP * mult} L={LP} nf={mult}")
    return lines


def testbench(temp, rs_l, corner="tt", n_chips=0, tran=False):
    """outputs drive the same diode-connected NMOS loads as in the transmitter."""
    lines = [f"* bias reference T={temp}", f'.lib "{PDK_LIB}" {corner}', f".temp {temp}",
             ("Vdd vdd 0 pwl(0 0 1u 1.8)" if tran else "Vdd vdd 0 1.8"),
             *core(rs_l),
             "Vmi bi bi2 0", f"XLi bi2 bi2 0 0 {NF} W=0.5 L=1.0",
             "Vmq bq bq2 0", f"XLq bq2 bq2 0 0 {NF} W=0.5 L=1.0",
             "Vmp bpa bpa2 0", f"XLp bpa2 bpa2 0 0 {NF} W=1 L=0.5"]
    meas = "  print i(Vmi) i(Vmq) i(Vmp)\n"
    if n_chips:
        return "\n".join(lines) + mc_control(n_chips, "  op\n" + meas) + ".end\n"
    ctrl = ("  tran 1n 5u\n  print i(Vmi)[length(i(Vmi))-1]\n" if tran else "  op\n" + meas)
    return "\n".join(lines) + "\n.control\n" + ctrl + ".endc\n.end\n"


def currents(out):
    v = dict(re.findall(r"(i\(vm[iqp]\))\s*=\s*(\S+)", out))
    return np.array([float(v[k]) for k in ("i(vmi)", "i(vmq)", "i(vmp)")])


if __name__ == "__main__":
    if sys.argv[1:2] == ["tune"]:
        for rs_l in (60, 70, 80, 90, 100):
            print(f"Rs L={rs_l}: I(27C) = {currents(run_netlist(testbench(27, rs_l))) * 1e6} uA")
