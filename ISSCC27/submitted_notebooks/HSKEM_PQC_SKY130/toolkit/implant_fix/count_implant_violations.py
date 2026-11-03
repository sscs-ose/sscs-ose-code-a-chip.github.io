"""Count the implant width and spacing violations of the macro top cells (what implant_fix.py closes).

    klayout -b -rd gds=IN.gds -r count_implant_violations.py

Prints, per macro and layer (nsdm, psdm: 0.38 um; npc: 0.27 um), the number of spacing and width markers, and
their positions when there are fewer than ten.
SPDX-License-Identifier: Apache-2.0
"""
import pya

ly = pya.Layout()
ly.read(gds)                                        # noqa: F821 (set by klayout -rd)
dbu = ly.dbu
E = pya.Region.Euclidian
RULE = {"nsdm": ((93, 44), 0.38), "psdm": ((94, 20), 0.38), "npc": ((95, 20), 0.27)}
for c in ly.each_cell():
    if c.name.startswith("sky130_sram_") and not any(ly.cell(p).name.startswith("sky130_sram_") for p in c.each_parent_cell()):
        for k, (lay, d) in RULE.items():
            r = pya.Region(c.begin_shapes_rec(ly.layer(*lay))).merged()
            sp, wd = r.space_check(round(d / dbu), False, E), r.width_check(round(d / dbu), False, E)
            where = [f"({e.bbox().center().x * dbu:.2f},{e.bbox().center().y * dbu:.2f})" for e in sp.each()][:9] if sp.count() < 10 else []
            print(f"{c.name} {k}: space {sp.count()} width {wd.count()} {' '.join(where)}")
