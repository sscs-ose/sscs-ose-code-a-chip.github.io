"""Build a 'shadow' of the routed chip netlist for a zero-delay activity simulation of its logic.

OpenSTA's statistical propagation of register activity through the chip's combinational logic is not
usable here: deep XOR/majority trees accumulate transition densities far beyond one per cycle. This
script instead keeps every combinational cell of the routed netlist and replaces
  * the Q output of each flip-flop by a hierarchical reference to the same register bit in the RTL
    simulation (the flow keeps register names: u_common.<rtl path>[bit]$_DFF...),
  * the data outputs of each SRAM macro by the read data of the corresponding RTL wrapper,
  * the chip's inputs by the corresponding RTL top-level ports, and the clock by a constant
    (clock-network and register clock-pin power come from OpenSTA's clock analysis instead).
Simulated next to the RTL testbench, the combinational nets then switch exactly as the routed logic
would without glitches, and a VCD of them gives OpenSTA a measured activity for every net.

usage: python3 shadow_netlist.py <6_final.v> <out.v> [<names to skip, one per line>]
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import re
import sys

RTL = "tb_trustedge_spi.dut"
# chip port -> RTL top-level port (asic/rtl/trustedge_asic_core.sv); unlisted inputs are tied to 0
PORTS = {"clk_i": None, "rst_ni": "rst_n", "spi_cs_ni": "spi_cs_n", "spi_sck_i": "spi_sck",
         "spi_mosi_i": "spi_mosi", "sig_valid_i": "sig_valid", "provision_enable_i": "provision_enable",
         "platform_ready_i": "sdm_transport_ready", "platform_error_i": "sdm_transport_error",
         "platform_id_i": "sdm_chip_id", "crypto_backend_enabled_i": "sdm_crypto_enabled",
         "crypto_backend_ready_i": "sdm_crypto_mem_ready", "crypto_backend_error_i": "sdm_crypto_mem_error"}
FLOP = re.compile(r"sky130_fd_sc_hd__(dfrtp|dfstp|dfxtp|edfxtp|dfrbp|dfsbp|dfbbp|sdf)\w*$")
WIDTH = {"16x256": 16, "12x256": 12, "12x512": 12, "12x640": 12, "12x768": 12, "24x128": 24, "24x256": 24, "8x768": 8}


def conn(body: str, pin: str) -> str | None:
    m = re.search(r"\." + pin + r"\s*\(\s*((?:\\\S+\s)|[^()]*?)\s*\)", body)
    return m[1].strip() if m else None


def main(src: str, dst: str, skip_file: str | None = None) -> None:
    skip = set(open(skip_file).read().split()) if skip_file else set()
    text = open(src).read()
    m = re.search(r"module\s+trustedge_asic_core\s*\(.*?\);(.*)endmodule", text, re.S)
    out = ["// shadow of the routed trustedge_asic_core (scripts/shadow_netlist.py); simulation only",
           "`timescale 1ns/1ps", "module shadow_chip;"]
    n_ff = n_ref = n_mac = 0
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
                rtl = PORTS.get(name, "")
                src_expr = "1'b0" if rtl is None else (f"{RTL}.{rtl}" if rtl else "0")
                out.append(f"assign {name} = {src_expr} ;")
            continue
        if kw in ("wire", "assign"):
            out.append(s + " ;")
            continue
        inst = re.match(r"(\S+)\s+(\\\S+\s|\S+)\s*\((.*)\)\s*$", s, re.S)
        if not inst:
            out.append(s + " ;")
            continue
        cell, name, body = inst[1], inst[2].strip(), inst[3]
        bare = name.lstrip("\\")
        if FLOP.match(cell):
            n_ff += 1
            q = conn(body, "Q")
            if q is None:
                continue
            base = re.sub(r"\$_\w+$", "", bare)
            if base.startswith("u_reset_sync."):
                ref = f"{RTL}.rst_n"
            elif base.startswith("u_common.") and base not in skip:
                ref = f"{RTL}.{base[len('u_common.'):]}"
                n_ref += 1
            else:
                ref = "1'b0"
            out.append(f"assign {q} = {ref} ;")
            continue
        if cell.startswith("sky130_sram_"):
            n_mac += 1
            dout = conn(body, "dout0")
            nets = [x.strip() for x in dout.strip("{}").split(",")] if dout and dout.startswith("{") else []
            wrapper = re.sub(r"\.g_\w+\.u_macro$", "", bare)[len("u_common."):]
            w = WIDTH[re.search(r"1rw_(\d+x\d+)", cell)[1]]
            for k, net in enumerate(reversed(nets)):          # concatenation lists the MSB first
                if net.startswith(("1'", "_unconnected")) or not net:
                    continue
                out.append(f"assign {net} = " + (f"{RTL}.{wrapper}.rdata[{k}];" if k < w else "1'b0;"))
            continue
        # the testbench models two library cells itself (reset branches): use renamed copies here
        out.append(re.sub(r"^sky130_fd_sc_hd__(and2_1|inv_1)\b", r"shadow_sky130_\1", s) + " ;")
    out.append("endmodule")
    open(dst, "w").write("\n".join(out) + "\n")
    print(f"flip-flops {n_ff}, referenced {n_ref}, macros {n_mac}, statements {len(out)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
