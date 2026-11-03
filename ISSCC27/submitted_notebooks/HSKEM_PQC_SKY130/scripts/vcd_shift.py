"""Shift a VCD so that its first time stamp becomes 0 (OpenSTA measures activity from time 0), and optionally
stretch its time axis to the chip's clock.

A VCD started with $dumpvars in the middle of a simulation (tb/decaps_vcd_window.sv) begins at a
large time stamp; without the shift, OpenSTA would spread the window's toggles over the whole
simulated time before it. OpenSTA also turns the toggles into transitions per second of VCD time, so a
testbench whose clock differs from the chip's clock must be stretched: the system testbench runs a 10 ns
clock, the chip's constraints a 40 ns one, hence a factor of 4 (scripts/fullchip_power.sh). Without it the
data-dependent part of the power is that of a chip clocked four times faster.
usage: python3 vcd_shift.py in.vcd out.vcd [time factor, default 1]
SPDX-License-Identifier: Apache-2.0
"""
import sys


def main(src: str, dst: str, factor: str = "1") -> None:
    k = int(factor)
    t0 = None
    with open(src) as fi, open(dst, "w") as fo:
        for line in fi:
            if line[0] == "#":
                t = int(line[1:])
                if t0 is None:
                    t0 = t
                fo.write(f"#{(t - t0) * k}\n")
            else:
                fo.write(line)
    print("shifted by", t0, "and stretched by", k)


if __name__ == "__main__":
    main(*sys.argv[1:4])
