"""What clock gating of idle blocks would save on the chip during a decapsulation (projection).

Inputs (from the private layout database, see fullchip_power.sh):
  * per-instance power of every flip-flop and clock buffer at the typical corner (OpenROAD report_power);
  * the instances each clock buffer drives (a buffer belongs to a block when all its loads do);
  * the register toggles of each block in the decapsulation window (shadow VCD).
A block whose registers do not toggle at all during the window could have its clock stopped by one
integrated clock-gating cell; its flip-flops' clock-pin power and the power of the clock buffers that
serve only that block would then disappear. The lower estimate keeps every clock buffer shared between
blocks; the upper estimate assigns the shared tree to the blocks in proportion to their flip-flops.
usage: python3 clock_gating_whatif.py <flop_clk_power.txt> <clkbuf_loads.tsv> <toggles_by_block.json> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import collections
import json
import re
import sys


def block_of(inst: str) -> str:
    inst = inst.lstrip("\\")
    return inst.split(".")[1] if inst.startswith("u_common.") else "(top level)"


def main(pwr_file: str, loads_file: str, tog_file: str, out: str) -> None:
    power = {}
    for line in open(pwr_file):
        s = line.split()
        if len(s) == 5:
            try:
                power[s[4]] = float(s[3])
            except ValueError:
                pass
    loads = {}
    for line in open(loads_file):
        name, _, rest = line.rstrip("\n").partition("\t")
        loads[name] = rest.split()
    # owner of each clock buffer: the block of all its loads, resolved bottom-up through the tree
    owner: dict[str, str] = {}

    def own(buf: str, depth: int = 0) -> str:
        if buf in owner:
            return owner[buf]
        blocks = set()
        for ld in loads.get(buf, []):
            blocks.add(own(ld, depth + 1) if ld in loads and depth < 64 else block_of(ld))
        owner[buf] = blocks.pop() if len(blocks) == 1 else "(shared clock tree)"
        return owner[buf]

    for b in loads:
        own(b)
    flop_p, buf_p = collections.Counter(), collections.Counter()
    for inst, p in power.items():
        if inst in loads:
            buf_p[owner[inst]] += p
        else:
            flop_p[block_of(inst)] += p
    tog = json.load(open(tog_file))
    blocks = sorted(set(flop_p) | set(buf_p), key=lambda b: -(flop_p[b] + buf_p[b]))
    rows = {b: {"flops_mw": flop_p[b] * 1e3, "own_clock_buffers_mw": buf_p[b] * 1e3,
                "register_toggles": tog.get(b, {}).get("toggles"), "flops": tog.get(b, {}).get("flops")}
            for b in blocks}
    idle = [b for b in blocks if tog.get(b, {}).get("toggles") == 0 and tog[b]["flops"] > 10]
    saved = sum(flop_p[b] + buf_p[b] for b in idle)
    total = sum(flop_p.values()) + sum(buf_p.values())
    # with gating, clock-tree synthesis builds one subtree per gated domain, so the shared tree would
    # also split; the upper estimate shares it out in proportion to the flip-flops served
    n_ff = sum(v["flops"] for b, v in tog.items() if b in flop_p)
    idle_ff = sum(tog[b]["flops"] for b in idle)
    shared = buf_p["(shared clock tree)"]
    upper = saved + shared * idle_ff / n_ff
    res = {"clock_and_register_power_mw": total * 1e3, "blocks": rows, "idle_blocks": idle,
           "idle_flip_flops": idle_ff, "flip_flops": n_ff, "shared_clock_tree_mw": shared * 1e3,
           "saved_by_gating_idle_blocks_mw": saved * 1e3, "saved_fraction": saved / total,
           "saved_upper_estimate_mw": upper * 1e3, "saved_upper_fraction": upper / total,
           "note": "projection: one clock-gating cell per idle block; leakage of the gated flip-flops and the "
                   "shared upper clock tree remain"}
    json.dump(res, open(out, "w"), indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "blocks"}, indent=1))
    for b in blocks[:16]:
        print(f"{b:32s} flops {rows[b]['flops_mw']:7.2f} mW  own buffers {rows[b]['own_clock_buffers_mw']:6.2f} mW  toggles {rows[b]['register_toggles']}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
