"""Scale the timing arcs of an OpenRAM Liberty view, for bounding a corner STA.

    scale_macro_lib.py <in.lib> <out.lib> <factor> [--keep-hold]

Multiplies the values of cell_rise/cell_fall (clock-to-output delay) and of the setup constraints
(setup_rising: rise_constraint/fall_constraint) by <factor>. Output transitions, hold constraints and
everything else are unchanged. It is a what-if tool: how slow could the macro arcs get before a path through
a macro becomes the worst path of the chip.
SPDX-License-Identifier: Apache-2.0
"""
import re
import sys

src, dst, k = sys.argv[1], sys.argv[2], float(sys.argv[3])
text = open(src).read()
parts = re.split(r"(?=\btiming\s*\(\s*\)\s*\{)", text)
VALUES = re.compile(r'values\s*\(((?:[^()]|\n)*?)\)\s*;', re.S)


def scale_block(block, tables):
    out, pos = [], 0
    for m in re.finditer(r"\b(" + "|".join(tables) + r")\s*\([^)]*\)\s*\{", block):
        out.append(block[pos:m.end()])
        end = block.index("}", m.end())
        body = block[m.end():end]
        body = VALUES.sub(lambda v: "values(" + re.sub(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?",
                          lambda n: f"{float(n[0]) * k:.4f}", v[1]) + ");", body)
        out.append(body)
        pos = end
    out.append(block[pos:])
    return "".join(out)


res, n = [], 0
for p in parts:
    t = re.search(r"timing_type\s*:\s*(\w+)", p)
    kind = t[1] if t else ""
    if kind in ("falling_edge", "rising_edge"):
        p, n = scale_block(p, ["cell_rise", "cell_fall"]), n + 1
    elif kind == "setup_rising":
        p, n = scale_block(p, ["rise_constraint", "fall_constraint"]), n + 1
    res.append(p)
open(dst, "w").write("".join(res))
print(f"{src}: scaled {n} timing groups by {k}")
