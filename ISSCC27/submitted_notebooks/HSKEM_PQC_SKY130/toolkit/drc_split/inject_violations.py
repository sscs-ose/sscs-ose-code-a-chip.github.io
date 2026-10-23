"""Add a few deliberate BEOL and off-grid violations to a copy of a GDS, outside its die, for testing a DRC
setup (the equivalence check of run_split_drc.sh --full).

    klayout -b -rd in_gds=IN.gds -rd out_gds=OUT.gds -r inject_violations.py

The shapes go into the top cell, 20 um right of its bounding box: li1 and met1 to met5 lines narrower than
their minimum width and pairs closer than their minimum spacing, a mcon and a via without enclosure, and a
met1 box off the 5 nm manufacturing grid.
SPDX-License-Identifier: Apache-2.0
"""
import pya

ly = pya.Layout()
ly.read(in_gds)                                    # noqa: F821 (set by klayout -rd)
top = ly.top_cell()
bb = top.dbbox()
x0, y0 = bb.right + 20.0, bb.bottom + 5.0
L = {"li1": (67, 20), "mcon": (67, 44), "met1": (68, 20), "via": (68, 44), "met2": (69, 20),
     "met3": (70, 20), "met4": (71, 20), "met5": (72, 20)}
# layer: (too-narrow width, legal width, too-small spacing), in um
RULES = {"li1": (0.10, 0.30, 0.10), "met1": (0.10, 0.30, 0.10), "met2": (0.10, 0.30, 0.10),
         "met3": (0.20, 0.50, 0.20), "met4": (0.20, 0.50, 0.20), "met5": (1.00, 2.00, 1.00)}


def box(layer, x1, y1, x2, y2):
    top.shapes(ly.layer(*L[layer])).insert(pya.DBox(x1, y1, x2, y2))


y = y0
for layer, (narrow, legal, gap) in RULES.items():
    box(layer, x0, y, x0 + 10.0, y + narrow)                       # width violation
    box(layer, x0 + 15.0, y, x0 + 25.0, y + legal)                 # spacing violation between these two
    box(layer, x0 + 15.0, y + legal + gap, x0 + 25.0, y + 2 * legal + gap)
    y += 2 * legal + gap + 5.0
box("mcon", x0, y, x0 + 0.17, y + 0.17)                            # mcon with no li1 or met1 around it
box("via", x0 + 5.0, y, x0 + 5.15, y + 0.15)                       # via with no met1 or met2 around it
box("met1", x0 + 10.0025, y, x0 + 12.0, y + 1.0)                   # off the 5 nm grid
ly.write(out_gds)                                  # noqa: F821
print("injected into", top.name, "at x >=", round(x0, 3))
