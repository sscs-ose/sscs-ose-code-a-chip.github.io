"""Close the sub-rule implant gaps inside the OpenRAM SRAM macros of a GDS (mask-preparation step).

usage: klayout -b -rd in_gds=IN.gds -rd out_gds=OUT.gds -r scripts/implant_fix.py

The SKY130 FEOL deck flags implant gaps narrower than the minimum spacing (nsdm/psdm 0.38 um, npc
0.27 um) and notes that such gaps "should be manually merged". The OpenRAM bitcell arrays and their
periphery leave many of them between abutted cells. For every macro top cell (a sky130_sram_* cell not
instantiated by another one) this script
  * closes every psdm gap narrower than 0.38 um (grow/shrink by half the rule; a gap that remains,
    such as two shapes meeting corner to corner, is bridged with a box of at least 0.38 x 0.38 um);
  * closes the nsdm gaps the same way, gives way where psdm now lies, and drops the field slivers
    narrower than 0.38 um that this leaves;
  * closes every npc gap narrower than 0.27 um.
The three layers are flattened into the macro top cell; no other layer and no cell outside the macros
is touched (scripts/verify_untouched.py proves it). Nothing is written unless every check below is
zero: no implant change on diffusion or tap (so no transistor or tap changes type), no implant
removed from poly, no change on a poly resistor, no new nsdm/psdm overlap, and no width or spacing
violation left on the three layers. Field poly (wordlines between bitcells) that lies in a closed gap
receives the implant of its neighbours, which is reported.
SPDX-License-Identifier: Apache-2.0
"""
import sys

import pya

IMPL = {"nsdm": (93, 44), "psdm": (94, 20), "npc": (95, 20)}
AUX = {"diff": (65, 20), "tap": (65, 44), "poly": (66, 20),
       "poly_rs": (66, 13), "rpm": (86, 20), "urpm": (79, 20)}     # poly-resistor markers

ly = pya.Layout()
ly.read(in_gds)                                     # noqa: F821 (set by klayout -rd)
dbu = ly.dbu
um2 = lambda r: r.area() * dbu * dbu
li = {k: ly.layer(*v) for k, v in {**IMPL, **AUX}.items()}
SD, NPC = round(0.38 / dbu), round(0.27 / dbu)
E = pya.Region.Euclidian

is_m = lambda c: c.name.startswith("sky130_sram_")
macros = [c for c in ly.each_cell() if is_m(c) and not any(is_m(ly.cell(p)) for p in c.each_parent_cell())]
tops = {m.cell_index() for m in macros}
sub = set(tops)
for m in macros:
    sub.update(m.called_cells())
for ci in sub - tops:                               # the subtrees must not be shared with other cells
    for p in ly.cell(ci).each_parent_cell():
        if p not in sub:
            sys.exit(f"ABORT: {ly.cell(ci).name} is also used by {ly.cell(p).name}")
print("macros:", [m.name for m in macros], "| cells in macro subtrees:", len(sub))


def close(reg, d):
    """Fill every gap narrower than d and leave no neck narrower than d."""
    reg = reg.sized(d // 2).sized(-(d // 2)).merged()
    for _ in range(6):
        ep = reg.space_check(d, False, E) + reg.width_check(d, False, E)
        if ep.is_empty():
            break
        bridges = pya.Region()
        for e in ep.each():
            bb = e.bbox(); c = bb.center()
            w, h = max(bb.width(), d), max(bb.height(), d)
            bridges.insert(pya.Box(c.x - w // 2, c.y - h // 2, c.x + (w + 1) // 2, c.y + (h + 1) // 2))
        reg = (reg + bridges).merged().sized(d // 2).sized(-(d // 2)).merged()
    return reg


def open_(reg, d):
    """Remove the parts narrower than d."""
    return reg.sized(-(d // 2)).sized(d // 2).merged() & reg


new, bad = {}, 0
for m in macros:
    R = {k: pya.Region(m.begin_shapes_rec(li[k])).merged() for k in li}
    R["polyres"] = R["poly_rs"] + R["rpm"] + R["urpm"]
    psdm_new = close(R["psdm"], SD)
    nsdm_new = R["nsdm"]
    for _ in range(4):
        nsdm_new = open_(close(nsdm_new, SD) - psdm_new, SD)
        if nsdm_new.space_check(SD, False, E).is_empty() and nsdm_new.width_check(SD, False, E).is_empty():
            break
    npc_new = close(R["npc"], NPC)
    changed = (nsdm_new ^ R["nsdm"]) + (psdm_new ^ R["psdm"])
    removed = (R["nsdm"] - nsdm_new) + (R["psdm"] - psdm_new)
    chk = {
        "implant_changed_on_diff_tap_um2": um2((R["diff"] + R["tap"]) & changed),
        "implant_removed_from_poly_um2": um2(R["poly"] & removed),
        "implant_changed_on_poly_resistor_um2": um2(R["polyres"] & changed),
        "npc_added_on_gate_um2": um2((npc_new - R["npc"]) & R["diff"] & R["poly"]),
        "nsdm_psdm_overlap_added_um2": um2((nsdm_new & psdm_new) - (R["nsdm"] & R["psdm"])),
        "nsdm_width": nsdm_new.width_check(SD, False, E).count(),
        "nsdm_space": nsdm_new.space_check(SD, False, E).count(),
        "psdm_width": psdm_new.width_check(SD, False, E).count(),
        "psdm_space": psdm_new.space_check(SD, False, E).count(),
        "npc_width": npc_new.width_check(NPC, False, E).count(),
        "npc_space": npc_new.space_check(NPC, False, E).count(),
    }
    bad += sum(1 for v in chk.values() if v > 0)
    extra = f"implant added on field poly {um2(R['poly'] & changed - R['diff']):.1f} um2"
    print(f"{m.name}: added nsdm {um2(nsdm_new - R['nsdm']):.2f} psdm {um2(psdm_new - R['psdm']):.2f} "
          f"npc {um2(npc_new - R['npc']):.2f} um2, removed nsdm {um2(R['nsdm'] - nsdm_new):.2f} um2 | "
          + " ".join(f"{k}={v:.4g}" for k, v in chk.items()) + " | " + extra)
    new[m.cell_index()] = {"nsdm": nsdm_new, "psdm": psdm_new, "npc": npc_new}

if bad:
    sys.exit(f"ABORT: {bad} check(s) non-zero; nothing written")
for ci in sub:
    for k in IMPL:
        ly.cell(ci).shapes(li[k]).clear()
for ci, regs in new.items():
    for k, r in regs.items():
        ly.cell(ci).shapes(li[k]).insert(r)
ly.write(out_gds)                                   # noqa: F821
print("written", out_gds)                           # noqa: F821
