"""Extract the NTT controller state per clock cycle from a VCD.

The VCD window starts at the cycle in which the testbench raises `start`
(see tb/tb_ntt.sv, VCD_OUT). The state register `st` of the design under test
is sampled at every rising clock edge; the first <keep> cycles are written as
CSV with the state names of rtl/kyber_ntt_engine.sv.

usage: fsm_trace.py <vcd> <out.csv> <keep>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys

STATES = {0: "IDLE", 1: "FETCH", 2: "CAPTURE", 3: "REDUCE", 4: "EXEC", 5: "WRITE", 6: "SCALE_FETCH",
          7: "SCALE_CAPTURE", 8: "SCALE_REDUCE", 9: "SCALE_EXEC", 10: "SCALE_WRITE", 11: "DONE",
          12: "CAPTURE_B", 13: "WRITE_B"}


def main() -> None:
    vcd, out, keep = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
    ids, scope = {}, []
    lines = vcd.read_text().splitlines()
    for ln in lines:                                   # header: identifier codes of dut.clk and dut.st
        if ln.startswith("$scope"):
            scope.append(ln.split()[2])
        elif ln.startswith("$upscope"):
            scope.pop()
        elif ln.startswith("$var") and scope[-1:] == ["dut"]:
            f = ln.split()
            if f[4] in ("clk", "st", "len", "j"):
                ids[f[3]] = f[4]
        elif ln.startswith("$enddefinitions"):
            break
    val = {"clk": 0, "st": 0, "len": 0, "j": 0}
    prev = dict(val)             # values at the end of the previous time step
    rows, t = [], 0
    for ln in lines:
        if ln.startswith("#"):
            t = int(ln[1:])
            prev = dict(val)     # changes within one time step appear in arbitrary order
            continue
        m = re.match(r"^b([01xz]+)\s+(\S+)$", ln) or re.match(r"^([01xz])(\S+)$", ln)
        if not m or m.group(2) not in ids:
            continue
        name, bits = ids[m.group(2)], m.group(1)
        new = int(bits.replace("x", "0").replace("z", "0"), 2)
        if name == "clk" and new == 1 and prev["clk"] == 0:
            # rising edge: sample the registers as they were during the cycle that just ended
            rows.append({"cycle": len(rows), "time_ns": t / 1000, "state": STATES.get(prev["st"], prev["st"]),
                         "len": prev["len"], "j": prev["j"]})
        val[name] = new
        if len(rows) >= keep:
            break
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cycle", "time_ns", "state", "len", "j"])
        w.writeheader()
        w.writerows(rows)
    print(out.name, [r["state"] for r in rows[:16]])


if __name__ == "__main__":
    main()
