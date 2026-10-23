"""Classify the Magic DRC markers of a chip: inside an OpenRAM macro or not, and, outside, the standard-cell master
under each marker. usage: classify_magic_drc.py <drc_boxes.txt> <6_final.def> <out.json> [lef dir]
SPDX-License-Identifier: Apache-2.0
"""
import collections, json, pathlib, re, sys

boxes, deff, out = sys.argv[1:4]
lefdir = pathlib.Path(sys.argv[4] if len(sys.argv) > 4 else "/mnt/d/TKVM_ATTT_2026_test/codeachip/flow/macros")
U = 0.005                                    # Magic internal unit for SKY130 GDS reads (2 units per 0.01 um lambda)
size = {}
for f in lefdir.glob("sky130_sram_*.lef"):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", f.read_text())
    size[f.name.split(".")[0]] = (float(m[1]), float(m[2]))
macros, cells = [], collections.defaultdict(list)
dbu = 1000
for line in open(deff):
    if line.startswith("UNITS DISTANCE MICRONS"):
        dbu = int(line.split()[3])
    m = re.match(r"\s+- (\S+) (\S+) .*?\( (-?\d+) (-?\d+) \) (\S+)", line)
    if not m:
        continue
    master, x, y, o = m[2], int(m[3]) / dbu, int(m[4]) / dbu, m[5]
    if master in size:
        w, h = size[master]
        if o in ("E", "W", "FE", "FW"):
            w, h = h, w
        macros.append((x, y, x + w, y + h, master))
    elif not master.startswith(("sky130_fd_sc_hd__fill", "sky130_fd_sc_hd__decap", "sky130_fd_sc_hd__tapvpwrvgnd")):
        cells[(int(x // 20), int(y // 20))].append((x, y, master))
ins, outr, under = collections.Counter(), collections.Counter(), collections.Counter()
mx = 0.0
for line in open(boxes):
    why, b = line.rstrip("\n").split("\t")
    a = [float(v) * U for v in b.split()]
    cx, cy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    mx = max(mx, a[2], a[3])
    if any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1, _ in macros):
        ins[why] += 1
        continue
    outr[why] += 1
    best = None
    for gx in (int(cx // 20) - 1, int(cx // 20)):
        for gy in (int(cy // 20) - 1, int(cy // 20)):
            for x, y, mst in cells.get((gx, gy), []):
                if x <= cx and y <= cy and cx - x < 15 and cy - y < 3:
                    d = (cx - x) + (cy - y)
                    if best is None or d < best[0]:
                        best = (d, mst)
    under[(why, best[1] if best else None)] += 1
res = {"tool": "Magic 8.3.629, SKY130 deck drc(full), euclidean; GDS after the implant fix",
       "marker_boxes": sum(ins.values()) + sum(outr.values()),
       "inside_openram_macros": sum(ins.values()), "outside_macros": sum(outr.values()),
       "inside_by_rule": dict(ins.most_common()), "outside_by_rule": dict(outr.most_common()),
       "outside_by_rule_and_cell": {f"{w} | {c}": n for (w, c), n in under.most_common()},
       "macros": len(macros), "max_coordinate_um": round(mx, 1)}
pathlib.Path(out).write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps({k: v for k, v in res.items() if k != "inside_by_rule"}, indent=1))
