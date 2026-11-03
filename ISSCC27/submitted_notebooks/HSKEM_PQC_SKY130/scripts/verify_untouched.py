"""Prove that scripts/implant_fix.py changed nothing but the implant layers inside the SRAM macros.

usage: klayout -b -rd a=ORIGINAL.gds -rd b=FIXED.gds -r scripts/verify_untouched.py

Checks that both files hold the same cells with identical instance lists, and that every (cell, layer)
pair is identical shape for shape, except nsdm/psdm/npc inside the OpenRAM macro subtrees. It also
counts the vpp layer (82/64): when it is empty, the deck's vpp.5 rule cannot fire and need not be run.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib

import pya

IMPL = {(93, 44), (94, 20), (95, 20)}
A, B = pya.Layout(), pya.Layout()
A.read(a)                                           # noqa: F821 (set by klayout -rd)
B.read(b)                                           # noqa: F821


def shapes_sig(cell, li):
    if li is None:
        return ""
    h = hashlib.sha1()
    for s in sorted(str(s) for s in cell.shapes(li).each()):
        h.update(s.encode())
    return h.hexdigest() if not cell.shapes(li).is_empty() else ""


def insts_sig(ly, cell):
    return sorted(f"{ly.cell(i.cell_index).name}|{i.cplx_trans}|{i.na}x{i.nb}|{i.da}|{i.db}" for i in cell.each_inst())


names_a = {c.name for c in A.each_cell()}
assert names_a == {c.name for c in B.each_cell()}, "the two files hold different cells"
macro_cells = set()
for c in A.each_cell():
    if c.name.startswith("sky130_sram_") and not any(A.cell(p).name.startswith("sky130_sram_") for p in c.each_parent_cell()):
        macro_cells.add(c.name)
        macro_cells.update(A.cell(i).name for i in c.called_cells())
layers = {(A.get_info(i).layer, A.get_info(i).datatype) for i in A.layer_indexes()} | \
         {(B.get_info(i).layer, B.get_info(i).datatype) for i in B.layer_indexes()}
diffs, pairs = [], 0
for ca in A.each_cell():
    cb = B.cell(ca.name)
    if insts_sig(A, ca) != insts_sig(B, cb):
        diffs.append((ca.name, "instances"))
    for (l, d) in layers:
        if (l, d) in IMPL and ca.name in macro_cells:
            continue
        pairs += 1
        if shapes_sig(ca, A.find_layer(l, d)) != shapes_sig(cb, B.find_layer(l, d)):
            diffs.append((ca.name, f"{l}/{d}"))
vpp, n_vpp = A.find_layer(82, 64), 0
if vpp is not None:
    it = A.top_cell().begin_shapes_rec(vpp)
    while not it.at_end():
        n_vpp += 1
        it.next()
print(f"cells {len(names_a)}, macro-subtree cells {len(macro_cells)}, (cell, layer) pairs compared {pairs}, "
      f"differences {len(diffs)}")
for x in diffs[:20]:
    print("  DIFF", x)
print("vpp 82/64 shapes:", n_vpp)
print("RESULT:", "UNTOUCHED OK" if not diffs else "CHECK FAILED")
