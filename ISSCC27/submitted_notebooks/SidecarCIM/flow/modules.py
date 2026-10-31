#!/usr/bin/env python3
"""Classify placed cells of a final run by module and write overlay inputs.
usage: modules.py <run_dir> <insts.txt> <cells_out.txt> <legend_out.txt> [area_breakdown design]
Classes: dense (u_dense), side (u_side), merge (combinational cone driving y), other (I/O buffers, clock, glue).
Flattened instance names are anonymous, so the module comes from net names (u_dense.* / u_side.* survive in the
netlist): cells touching such nets are seeded, the merge cone is traced back from the y ports, remaining cells
take the majority label of their neighbours (a few rounds)."""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

run, insts, cells_out, legend_out = sys.argv[1:5]
design = sys.argv[5] if len(sys.argv) > 5 else "sidecarcim_top_ff"
nl = next(Path(run, "final", "nl").glob("*.nl.v")).read_text()
OUTP = {"X", "Y", "Q", "Q_N", "COUT", "SUM", "HI", "LO", "GCLK"}
cell_re = re.compile(r"^\s*(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\((.*?)\);", re.S | re.M)
pin_re = re.compile(r"\.(\w+)\(([^)]*)\)")
cells = {}
for m in cell_re.finditer(nl):
    typ, name, body = m.groups()
    if re.search(r"fill|tap|decap|phy|ANTENNA", typ, re.I):
        continue
    pins = {p: n.strip() for p, n in pin_re.findall(body)}
    cells[name] = (typ, pins)
net_cells = defaultdict(list)
driver = {}
for c, (typ, pins) in cells.items():
    for p, n in pins.items():
        net_cells[n].append(c)
        if p in OUTP:
            driver[n] = c


def netlab(n):
    n = n.strip().lstrip(chr(92))
    if n.startswith("u_dense."):
        return "dense"
    if n.startswith("u_side."):
        return "side"
    return None


lab = {}
for c, (typ, pins) in cells.items():
    cnt = Counter(netlab(n) for n in pins.values() if netlab(n))
    if cnt:
        lab[c] = cnt.most_common(1)[0][0]
# merge cone: back from y ports through combinational cells
seq = re.compile(r"__(df|dl|sdf|edf)")
merge = set()
stack = [driver[n] for n in driver if n.lstrip(chr(92)).startswith("y[")]
while stack:
    c = stack.pop()
    if c in merge or seq.search(cells[c][0]):
        continue
    merge.add(c)
    for p, n in cells[c][1].items():
        if p not in OUTP and n in driver:
            stack.append(driver[n])
for c in merge:
    lab[c] = "merge"
# neighbour majority for the rest (skip huge nets such as clock / reset)
for _ in range(12):
    new = {}
    for c, (typ, pins) in cells.items():
        if c in lab:
            continue
        cnt = Counter()
        for p, n in pins.items():
            if len(net_cells[n]) > 40:
                continue
            for o in net_cells[n]:
                if o != c and lab.get(o) in ("dense", "side"):
                    cnt[lab[o]] += 1
        if cnt:
            new[c] = cnt.most_common(1)[0][0]
    if not new:
        break
    lab.update(new)
area = Counter()
n_out = 0
with open(cells_out, "w") as f:
    for l in open(insts):
        p = l.split()
        name = p[0]
        k = lab.get(name)
        if k is None:
            k = "other"
        a = (float(p[3]) - float(p[1])) * (float(p[4]) - float(p[2]))
        area[k] += a
        f.write("%s %s %s %s %s\n" % (p[1], p[2], p[3], p[4], k))
        n_out += 1
tot = sum(area.values())
print("classified placed-cell area share:", {k: round(100 * v / tot, 1) for k, v in area.items()}, "cells", n_out)
# legend: synthesis-level area % per module from results/area_breakdown.csv
import csv
pct = {}
try:
    for r in csv.DictReader(open(Path(__file__).resolve().parents[1] / "results" / "area_breakdown.csv")):
        if r["design"] == design:
            pct[r["module"]] = float(r["pct_of_total"])
except Exception:
    pass
lg = {"dense": ("dense array (u_dense) %s" % ("%.1f%%" % pct["dense_dcim_core"] if "dense_dcim_core" in pct else ""), "3070FF"),
      "side": ("sidecar (u_side) %s" % ("%.1f%%" % pct["sidecar"] if "sidecar" in pct else ""), "FF4040"),
      "merge": ("merge logic %s" % ("%.1f%%" % pct["top_merge_logic"] if "top_merge_logic" in pct else ""), "30FF60"),
      "other": ("I/O buffers, clock, glue", "909090")}
with open(legend_out, "w") as f:
    for k, (labl, rgb) in lg.items():
        f.write("%s|%s|%s\n" % (k, labl, rgb))
