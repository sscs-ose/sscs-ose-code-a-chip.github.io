"""Build 'real_chip': the routed chip netlist with real flip-flops, for a gate-level run next to the shadow.

shadow_netlist.py replaces every flip-flop output by the RTL simulation's register. This script keeps the routed
netlist's own flip-flops (zero-delay behavioural models with the cell's function, rtl/real_ff.v), the routed
clock tree and every combinational cell, and keeps the shadow's treatment of the two things a netlist alone cannot
supply: the chip's inputs (the RTL testbench's signals) and the data outputs of the SRAM macros (the RTL wrapper's
read data, with unknown bits read as 0: the RTL simulation leaves never-written words and registers unknown, a real
chip holds some value there). At the start of the window the flip-flops are loaded from the shadow's registers (the RTL state), the
clock of the real netlist is released, and from then on it runs on its own. A comparison of every flip-flop with the
shadow's, every cycle, tests that the routed netlist computes what the RTL computes.

usage: python3 real_netlist.py <6_final.v> <out.v> <state names out>
Both netlists are simulated in the same run (shadow_netlist.py's output compiled next to this one); the controller is
tb/real_chip_window.sv. Simulation only.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import re
import sys

from shadow_netlist import FLOP, PORTS, RTL, WIDTH, conn

SHADOW = "shadow_chip"
KIND = {"dfrtp": ("RESET_B", "rf_dfrtp"), "dfstp": ("SET_B", "rf_dfstp"), "dfxtp": (None, "rf_dfxtp"),
        "edfxtp": ("DE", "rf_edfxtp")}


def main(src: str, dst: str, names_out: str) -> None:
    text = open(src).read()
    m = re.search(r"module\s+trustedge_asic_core\s*\(.*?\);(.*)endmodule", text, re.S)
    out = ["// real flip-flops in the routed netlist (scripts/real_netlist.py); simulation only", "`timescale 1ns/1ps",
           "module real_chip;", "reg load = 1'b0, run = 1'b0;",
           f"wire real_clk = run & {RTL.split('.')[0]}.clk;"]
    flops, outs, macro_in = [], [], []
    for stmt in m[1].split(";"):
        s = stmt.strip()
        if not s:
            continue
        kw = s.split()[0]
        if kw in ("input", "output", "inout"):
            decl = re.match(r"(input|output|inout)\s*(\[[^\]]+\])?\s*(\S+)", s)
            rng, name = decl[2] or "", decl[3]
            out.append(f"wire {rng} {name} ;")
            if kw == "input":
                if name == "clk_i":
                    out.append("assign clk_i = real_clk ;")
                else:
                    rtl = PORTS.get(name, "")
                    out.append(f"assign {name} = " + (f"{RTL}.{rtl}" if rtl else "0") + " ;")
            elif kw == "output":
                outs.append((name, rng))
            continue
        if kw in ("wire", "assign"):
            out.append(s + " ;")
            continue
        inst = re.match(r"(\S+)\s+(\\S+\s|\S+)\s*\((.*)\)\s*$", s, re.S)
        if not inst:
            out.append(s + " ;")
            continue
        cell, iname, body = inst[1], inst[2].strip() + " ", inst[3]
        fm = FLOP.match(cell)
        if fm:
            kind = re.match(r"sky130_fd_sc_hd__(dfrtp|dfstp|dfxtp|edfxtp)", cell)
            if not kind:
                sys.exit(f"flip-flop type without a model: {cell}")
            ctl, mod = KIND[kind[1]]
            q, d, clk = conn(body, "Q"), conn(body, "D"), conn(body, "CLK")
            extra = f", .{ctl}({conn(body, ctl)} )" if ctl else ""      # (a space ends an escaped identifier)
            out.append(f"{mod} {iname}(.CLK({clk} ), .D({d} ){extra}, .Q({q} ), .LOAD(load), .LV({SHADOW}.{q} ));")
            flops.append(q)
            continue
        if cell.startswith("sky130_sram_"):
            w = WIDTH[re.search(r"1rw_(\d+x\d+)", cell)[1]]
            dout = conn(body, "dout0")
            nets = [x.strip() for x in dout.strip("{}").split(",")] if dout and dout.startswith("{") else []
            wrapper = re.sub(r"(\.g_\w+)?\.u_macro$", "", iname.strip().lstrip("\\"))[len("u_common."):]
            for k, net in enumerate(reversed(nets)):
                if net.startswith(("1'", "_unconnected")) or not net:
                    continue
                out.append(f"assign {net} = " + (f"({RTL}.{wrapper}.rdata[{k}] === 1'b1);" if k < w else "1'b0;"))   # x reads as 0
            for pin in ("csb0", "web0", "addr0", "din0", "wmask0", "spare_wen0"):
                c = conn(body, pin)
                if c:
                    macro_in += [x.strip() for x in c.strip("{}").split(",") if x.strip() and not x.strip().startswith("1'")]
            continue
        out.append(re.sub(r"^sky130_fd_sc_hd__(and2_1|inv_1)\b", r"shadow_sky130_\1", s) + " ;")
    names = flops
    out.append(f"localparam NFF = {len(flops)};")
    out.append("wire [NFF-1:0] q_real = {" + ", ".join(f"{q} " for q in flops) + "};")
    out.append(f"wire [NFF-1:0] q_shadow = {{" + ", ".join(f"{SHADOW}.{q} " for q in flops) + "};")
    cmp_nets = [f"{n}" for n, _ in outs] + sorted(set(macro_in))
    out.append("wire [" + str(len(cmp_nets) - 1) + ":0] p_real = {" + ", ".join(f"{n} " for n in cmp_nets) + "};")
    out.append("wire [" + str(len(cmp_nets) - 1) + ":0] p_shadow = {" + ", ".join(f"{SHADOW}.{n} " for n in cmp_nets) + "};")
    out.append(f"localparam NPIN = {len(cmp_nets)};")
    out.append("endmodule")
    open(dst, "w").write("\n".join(out) + "\n")
    open(names_out, "w").write("\n".join(q.strip() for q in names) + "\n")
    open(names_out + ".pins", "w").write("\n".join(n.strip() for n in cmp_nets) + "\n")   # compared pins, MSB first
    print(f"real flip-flops {len(flops)}, compared pins {len(cmp_nets)}, statements {len(out)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
