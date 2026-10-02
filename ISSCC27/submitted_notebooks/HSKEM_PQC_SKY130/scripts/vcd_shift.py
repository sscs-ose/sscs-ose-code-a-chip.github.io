"""Shift a VCD so that its first time stamp becomes 0 (OpenSTA measures activity from time 0).

A VCD started with $dumpvars in the middle of a simulation (tb/decaps_vcd_window.sv) begins at a
large time stamp; without the shift, OpenSTA would spread the window's toggles over the whole
simulated time before it.
usage: python3 vcd_shift.py in.vcd out.vcd
SPDX-License-Identifier: Apache-2.0
"""
import sys


def main(src: str, dst: str) -> None:
    t0 = None
    with open(src) as fi, open(dst, "w") as fo:
        for line in fi:
            if line[0] == "#":
                t = int(line[1:])
                if t0 is None:
                    t0 = t
                fo.write(f"#{t - t0}\n")
            else:
                fo.write(line)
    print("shifted by", t0)


if __name__ == "__main__":
    main(*sys.argv[1:3])
