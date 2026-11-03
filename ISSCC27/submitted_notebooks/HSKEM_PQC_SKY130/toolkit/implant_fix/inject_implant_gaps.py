"""Add sub-rule implant gaps to a copy of an OpenRAM macro GDS, away from every device, to test implant_fix.py.

    klayout -b -rd in_gds=IN.gds -rd out_gds=OUT.gds -r inject_implant_gaps.py

In the macro's top cell, 20 um right of its bounding box, three pairs of 1 x 1 um boxes are placed 0.20 um apart
on psdm and nsdm and 0.15 um apart on npc (the minimum spacings are 0.38, 0.38 and 0.27 um): three implant-spacing
violations that no transistor or tap is under, and that the fix has to close without touching anything else.
The positions are printed.
SPDX-License-Identifier: Apache-2.0
"""
import pya

ly = pya.Layout()
ly.read(in_gds)                                     # noqa: F821 (set by klayout -rd)
macros = [c for c in ly.each_cell() if c.name.startswith("sky130_sram_")
          and not any(ly.cell(p).name.startswith("sky130_sram_") for p in c.each_parent_cell())]
top = macros[0]
bb = top.dbbox()
x0, y0 = bb.right + 20.0, bb.bottom
L = {"psdm": ((94, 20), 0.20), "nsdm": ((93, 44), 0.20), "npc": ((95, 20), 0.15)}
for i, (name, (lay, gap)) in enumerate(L.items()):
    y = y0 + 5.0 * i
    li = ly.layer(*lay)
    top.shapes(li).insert(pya.DBox(x0, y, x0 + 1.0, y + 1.0))
    top.shapes(li).insert(pya.DBox(x0 + 1.0 + gap, y, x0 + 2.0 + gap, y + 1.0))
    print(f"{name}: gap {gap} um at x={x0 + 1.0:.2f}..{x0 + 1.0 + gap:.2f}, y={y:.2f}..{y + 1.0:.2f}")
ly.write(out_gds)                                   # noqa: F821
print("injected into", top.name)
