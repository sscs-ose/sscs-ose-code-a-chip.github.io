"""Cut a VCD to its $dumpon ... $dumpoff window.

OpenSTA's VCD reader does not accept $dumpon/$dumpoff blocks. This keeps the
header, turns the values listed in the $dumpon block into the initial values
at the window start, keeps every change inside the window and stops at the
closing $dumpoff, so the activity used for power covers exactly that window.

usage: python vcd_window.py in.vcd[.gz] out.vcd
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import gzip
import sys


def main(src: str, dst: str) -> None:
    opener = gzip.open if src.endswith(".gz") else open
    with opener(src, "rt") as fi, open(dst, "w") as fo:
        in_header, state, last_time, block = True, "pre", "#0", None
        for line in fi:
            s = line.strip()
            if in_header:
                fo.write(line)
                if s.startswith("$enddefinitions"):
                    in_header = False
                continue
            if block:                       # inside $dumpoff/$dumpon/$dumpvars/$dumpall
                if s == "$end":
                    block = None
                elif block == "$dumpon" and state == "window":
                    fo.write(line)
                continue
            if s.startswith("#"):
                last_time = s
                if state == "window":
                    fo.write(line)
                continue
            if s in ("$dumpon", "$dumpoff", "$dumpvars", "$dumpall"):
                if s == "$dumpon" and state == "pre":
                    state = "window"
                    fo.write(last_time + "\n")
                elif s == "$dumpoff" and state == "window":
                    fo.write(last_time + "\n")
                    return
                block = s
                continue
            if state == "window":
                fo.write(line)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
