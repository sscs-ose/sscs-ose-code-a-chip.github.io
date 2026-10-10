"""Activity of the flip-flop pins of the routed chip from the shadow VCD (plan item 1.4).

OpenSTA's read_vcd annotates the pins of the cells that exist in the VCD's scope. The shadow of scripts/shadow_netlist.py
replaces every flip-flop by an assignment from the RTL register it mirrors, so the flip-flops' own pins (D, Q, RESET_B,
SET_B, DE) are left without activity (about 119,000 pins of HSKEM-2) although the nets they connect to are in the VCD.
This script measures, for every net that a flip-flop data, output, enable or asynchronous set/reset pin connects to,
the transition density (transitions per ns of VCD time) and the duty (fraction of the window at 1), and writes them as
a table that flop_pin_activity.tcl applies to those pins with set_power_activity. Clock pins are left to OpenSTA's clock
analysis, as before.

usage: python3 flop_pin_activity.py <6_final.v> <shadow VCD (time-stretched)> <out.tsv>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import re
import sys

FLOP = re.compile(r"sky130_fd_sc_hd__(dfrtp|dfstp|dfxtp|edfxtp|dfrbp|dfsbp|dfbbp|sdf)\w*$")
PINS = ("D", "Q", "Q_N", "RESET_B", "SET_B", "DE")


def flop_pin_nets(netlist: str) -> set[str]:
    text = open(netlist).read()
    body = re.search(r"module\s+trustedge_asic_core\s*\(.*?\);(.*)endmodule", text, re.S)[1]
    nets = set()
    for stmt in body.split(";"):
        m = re.match(r"\s*(\S+)\s+(\\\S+\s|\S+)\s*\((.*)\)\s*$", stmt, re.S)
        if not m or not FLOP.match(m[1]):
            continue
        for pin, net in re.findall(r"\.(\w+)\s*\(\s*((?:\\\S+\s)|[^()]*?)\s*\)", m[3]):
            if pin in PINS and net.strip():
                nets.add(net.strip().lstrip("\\"))
    return nets


def main(netlist: str, vcd: str, out: str) -> None:
    want = flop_pin_nets(netlist)
    code_of: dict[str, list[str]] = {}
    val, since, high, tog = {}, {}, {}, {}
    t0 = t = None
    in_defs = True
    with open(vcd, encoding="utf-8", errors="replace") as f:
        for line in f:
            if in_defs:
                if line.startswith("$var"):
                    w = line.split()
                    name = w[4].lstrip("\\") + (w[5] if len(w) > 6 and w[5].startswith("[") else "")
                    if w[2] == "1" and name in want:
                        code_of.setdefault(w[3], []).append(name)
                elif line.startswith("$enddefinitions"):
                    in_defs = False
                continue
            c = line[0]
            if c == "#":
                t = int(line[1:])
                if t0 is None:
                    t0 = t
                continue
            if c in "01xzXZ" and len(line) > 1:
                code = line[1:].strip()
                if code not in code_of:
                    continue
                v = c if c in "01" else "x"
                old = val.get(code)
                if old == "1":
                    high[code] = high.get(code, 0) + t - since[code]
                if old is not None and old != v and old in "01" and v in "01" and t != t0:
                    tog[code] = tog.get(code, 0) + 1
                val[code], since[code] = v, t
    t_end = t
    for code, v in val.items():
        if v == "1":
            high[code] = high.get(code, 0) + t_end - since[code]
    span = t_end - t0
    ts = 1e-3                                   # VCD time unit in ns (the shadow VCD uses 1 ps)
    n = 0
    with open(out, "w") as fo:
        fo.write(f"# window {span * ts:.3f} ns; density in transitions per ns; duty = fraction of the window at 1\n")
        for code, names in code_of.items():
            d = tog.get(code, 0) / (span * ts)
            u = high.get(code, 0) / span
            for nm in names:
                fo.write(f"{nm}\t{d:.6e}\t{u:.6f}\n"); n += 1
    print(f"{len(want)} flip-flop pin nets, {n} found in the VCD, window {span * ts:.1f} ns")


if __name__ == "__main__":
    main(*sys.argv[1:4])
