"""Add to the shadow's skip file every register the shadow reads at a wrong place of an RTL vector or array.

Synthesis changes the shape of some RTL registers, so the netlist's flip-flop name[k] is not bit or word k of the RTL
signal name:
  * an unpacked array (reg [7:0] x [0:N-1]) becomes one bit vector: the netlist's x[k] is bit k, the RTL's x[k] is word k
    (iverilog: "returning 'bx for out of bounds array access" for k >= N, and silently the word's lowest bit otherwise);
  * a state register that synthesis re-encodes as one-hot (FSM extraction): the netlist's st[k] is state k, the RTL's st[k]
    is bit k of the binary code (iverilog -Wselect-range: "Constant bit select [k] is after vector st[2:0]", and no warning
    for the bits that lie inside the narrower vector).
For every register named in such a warning, the whole register (every flip-flop that shares its RTL path) is listed in the
skip file, so that shadow_netlist.py (mode self) simulates it from its own D input instead.
usage: python3 shadow_oob_skip.py <iverilog log> <shadow.v> <skip file>      prints the number of names added
SPDX-License-Identifier: Apache-2.0
"""
import re
import sys

log, shadow, skip = sys.argv[1:4]
lines = open(shadow).read().split("\n")
text = open(log).read()
bad = {int(m[1]) for m in re.finditer(
    r"shadow\.v:(\d+): warning: (?:returning 'bx for out of bounds array access|Constant bit select \[\d+\] is after vector)", text)}
RHS = re.compile(r"=\s*tb_trustedge_spi\.dut\.(\S+?)(?:\[\d+\])?\s*;")
paths = set()
for n in bad:
    m = RHS.search(lines[n - 1])
    if m:
        paths.add(m[1])
names = set()
for line in lines:
    m = RHS.search(line)
    if m and m[1] in paths:
        names.add("u_common." + re.search(r"=\s*tb_trustedge_spi\.dut\.(\S+)\s*;", line)[1])
old = set(open(skip).read().split())
open(skip, "w").write("\n".join(sorted(old | names)) + "\n")
print(len(names - old))
