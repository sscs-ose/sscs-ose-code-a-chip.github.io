"""Count the accesses of an OpenRAM macro in a gate-level VCD window.

The macro's behavioural model registers chip select, write enable and address on the rising edge of its
clock; every rising edge inside the window is one cycle of the macro: a write, a read of a new address,
a read of the address accessed before, or (chip select inactive) an idle cycle.
usage: python3 vcd_macro_accesses.py <window.vcd> <instance name, e.g. u_macro> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import sys


def main(vcd: str, inst: str, out: str) -> None:
    ids, scope, want = {}, [], {"clk0", "csb0_reg", "web0_reg", "addr0_reg"}
    with open(vcd) as f:
        for line in f:                                      # header: find the model's registers
            s = line.split()
            if not s:
                continue
            if s[0] == "$scope":
                scope.append(s[2])
            elif s[0] == "$upscope":
                scope.pop()
            elif s[0] == "$var" and scope and inst in scope[-1] and s[4] in want:
                ids[s[3]] = s[4]
            elif s[0] == "$enddefinitions":
                break
        if set(ids.values()) != want:
            raise SystemExit(f"{inst}: found {sorted(ids.values())} in the VCD, need {sorted(want)}")
        val = {k: None for k in want}
        n = {"cycles": 0, "writes": 0, "reads_new_address": 0, "reads_same_address": 0, "idle": 0}
        prev_addr, rose = None, False

        def close_step():
            nonlocal prev_addr
            n["cycles"] += 1
            if val["csb0_reg"] != "0":
                n["idle"] += 1
            elif val["web0_reg"] == "0":
                n["writes"] += 1
                prev_addr = val["addr0_reg"]
            else:
                n["reads_new_address" if val["addr0_reg"] != prev_addr else "reads_same_address"] += 1
                prev_addr = val["addr0_reg"]

        for line in f:
            s = line.strip()
            if not s or s.startswith("$"):
                continue
            if s[0] == "#":
                if rose:
                    close_step()
                rose = False
                continue
            if s[0] in "bB":
                v, i = s[1:].split()
            else:
                v, i = s[0], s[1:]
            k = ids.get(i)
            if k is None:
                continue
            if k == "clk0" and val["clk0"] == "0" and v == "1":
                rose = True
            val[k] = v
        if rose:
            close_step()
    json.dump(n, open(out, "w"), indent=1)
    print(n)


if __name__ == "__main__":
    main(*sys.argv[1:4])
