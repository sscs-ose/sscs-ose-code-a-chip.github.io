"""Register toggles of the routed chip over the decapsulation window, from the shadow VCD.

The shadow of scripts/shadow_netlist.py drives the Q output of every flip-flop of the routed netlist (from
the RTL register it mirrors, or from its own register for the few the RTL cannot name), so the shadow VCD
holds every flip-flop's output over the window. This script counts the value changes of each Q net after
the window's first sample, and reports per block (the first level below u_common) the flip-flops, the
toggles and the flip-flops that never toggle: the input of scripts/clock_gating_whatif.py and of the
"registers that never change" figure of the notebook.

usage: python3 shadow_toggles.py <6_final.v> <shadow VCD> <out.json> [<toggles_by_block.json>]
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import collections
import json
import re
import sys

FLOP = re.compile(r"sky130_fd_sc_hd__(dfrtp|dfstp|dfxtp|edfxtp|dfrbp|dfsbp|dfbbp|sdf)\w*$")


def flop_q_nets(netlist: str) -> dict[str, str]:
    """Q net (as declared in the shadow, without the leading backslash) -> flip-flop instance."""
    text = open(netlist).read()
    body = re.search(r"module\s+trustedge_asic_core\s*\(.*?\);(.*)endmodule", text, re.S)[1]
    out = {}
    for stmt in body.split(";"):
        m = re.match(r"\s*(\S+)\s+(\\\S+\s|\S+)\s*\((.*)\)\s*$", stmt, re.S)
        if not m or not FLOP.match(m[1]):
            continue
        q = re.search(r"\.Q\s*\(\s*((?:\\\S+\s)|[^()]*?)\s*\)", m[3])
        if q:
            out[q[1].strip().lstrip("\\")] = m[2].strip().lstrip("\\")
    return out


def block_of(inst: str) -> str:
    """The key of scripts/clock_gating_whatif.py: the first level below u_common."""
    return inst.split(".")[1] if inst.startswith("u_common.") else "(top level)"


def block_label(inst: str) -> str:
    """The grouping of results/fullchip/blocks.csv: registers directly below u_common form one group."""
    parts = inst.split(".")
    if inst.startswith("u_common.") and len(parts) > 2:
        return parts[1]
    return "(top-level registers)"


def main(netlist: str, vcd: str, out: str, by_block: str | None = None) -> None:
    q2inst = flop_q_nets(netlist)
    code_of = {}                       # VCD identifier code -> Q net
    changes = collections.Counter()
    last = {}
    in_defs, started = True, False
    with open(vcd, encoding="utf-8", errors="replace") as f:
        for line in f:
            if in_defs:
                if line.startswith("$var"):
                    w = line.split()               # $var wire 1 <code> <name> [range] $end
                    name = w[4].lstrip("\\") + (w[5] if len(w) > 6 and w[5].startswith("[") else "")
                    if w[2] == "1" and name in q2inst:
                        code_of[w[3]] = name
                elif line.startswith("$enddefinitions"):
                    in_defs = False
                continue
            c = line[0]
            if c == "#":
                started = started or line.strip() != "#0"
                continue
            if c in "01xzXZ" and len(line) > 1:
                code = line[1:].strip()
                if code in code_of:
                    if code in last and last[code] != c and started:
                        changes[code] += 1
                    last[code] = c
    per = collections.defaultdict(lambda: {"flip_flops": 0, "toggles": 0, "never_toggling": 0})
    gate = collections.defaultdict(lambda: {"flops": 0, "toggles": 0})
    seen = set(code_of.values())
    for code, net in code_of.items():
        b = per[block_label(q2inst[net])]
        b["flip_flops"] += 1
        b["toggles"] += changes[code]
        b["never_toggling"] += changes[code] == 0
        g = gate[block_of(q2inst[net])]
        g["flops"] += 1
        g["toggles"] += changes[code]
    res = {"flip_flops_in_netlist": len(q2inst), "flip_flops_in_vcd": len(seen),
           "never_toggling": sum(v["never_toggling"] for v in per.values()),
           "blocks": dict(sorted(per.items()))}
    open(out, "w").write(json.dumps(res, indent=1) + "\n")
    if by_block:                       # the input format of scripts/clock_gating_whatif.py
        json.dump(dict(gate), open(by_block, "w"), indent=1)
    print(f"flip-flops: netlist {len(q2inst)}, traced {len(seen)}, never toggling {res['never_toggling']}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
