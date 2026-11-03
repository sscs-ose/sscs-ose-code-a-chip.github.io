#!/usr/bin/env python3
"""Make gate-level sim stimulus from an RTL testbench VCD: inputs sampled at each rising clk edge.
Usage: gl_stim.py rtl.vcd outprefix   -> outprefix.hex (inputs/edge), outprefix.exp (y/edge), outprefix.info
Top-level ports only: clk rst load_en load_addr load_row start x_in ; outputs y busy valid."""
import sys

src, pre = sys.argv[1], sys.argv[2]
MAXE = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
lines = open(src).read().split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("$enddefinitions")) + 1
ids, widths, depth = {}, {}, 0
for l in lines[:i]:
    if l.startswith("$scope"):
        depth += 1
    elif l.startswith("$upscope"):
        depth -= 1
    elif l.startswith("$var") and depth == 1:
        p = l.split()
        ids[p[4]] = p[3]
        widths[p[4]] = int(p[2])
import os
IN = os.environ.get("GL_IN", "rst load_en load_addr load_row start x_in").split()
OUT = ["y", "busy", "valid"]
inv = {v: k for k, v in ids.items()}
state = {n: "x" * widths[n] for n in IN + OUT + ["clk"]}
ins, outs = [], []


def val(n):
    s = state[n]
    return s


def apply(tok):
    if tok[0] in "bB":
        v, ident = tok.split()
        n = inv.get(ident)
        if n in state:
            state[n] = v[1:].rjust(widths[n], v[1:2] if v[1:2] in "xz" else "0")
    else:
        n = inv.get(tok[1:])
        if n in state:
            state[n] = tok[0]


def snap():
    return {n: state[n] for n in IN + OUT}


pending, cur = [], None
prev_clk = "0"
last_out = None
for l in lines[i:]:
    l = l.strip()
    if not l or l.startswith("$"):
        if l.startswith("$dumpvars") or l == "$end":
            continue
        continue
    if l[0] == "#":
        if cur is not None:
            before = snap()
            clk0 = state["clk"]
            for t in pending:
                apply(t)
            if clk0 != "1" and state["clk"] == "1":
                ins.append(before)           # inputs as sampled at this edge
                if len(ins) > 1:
                    outs.append(before)      # outputs after previous edge
        cur, pending = int(l[1:]), []
    else:
        pending.append(l)


ins, outs = ins[:MAXE], outs[:MAXE - 1]


def bits_to_int(s):
    return int(s.replace("x", "0").replace("z", "0"), 2)


def hexw(b):
    return (b + 3) // 4


with open(pre + ".hex", "w") as f:
    for s in ins:
        w = 0
        for n in IN:
            w = (w << widths[n]) | bits_to_int(s[n])
        f.write("%x\n" % w)
with open(pre + ".exp", "w") as f:
    for s in outs:
        f.write("%s %s %s\n" % (s["y"], s["busy"], s["valid"]))
open(pre + ".info", "w").write(" ".join("%s=%d" % (n, widths[n]) for n in IN + OUT) + " edges=%d\n" % len(ins))
print("edges", len(ins))
