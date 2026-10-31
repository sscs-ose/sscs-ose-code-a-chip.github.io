#!/usr/bin/env python3
""""""
import re, sys
lines = open(sys.argv[1], errors="replace").read().split("\n")
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 4
scale = float(lines[0].split()[1])
i, out = 1, []
while i < len(lines):
    name = lines[i].strip()
    if not name or i + 1 >= len(lines): i += 1; continue
    m = re.match(r"^(\d+) (\d+) \d+ ", lines[i + 1])
    if not m: i += 1; continue
    n = int(m.group(1)); i += 2
    cap = []
    while i < len(lines) and not re.match(r"^[pe] \d+ \d+", lines[i]) and not (i + 1 < len(lines) and re.match(r"^\d+ \d+ \d+ ", lines[i + 1])):
        if lines[i].startswith('"'): cap.append(lines[i].strip('"'))
        i += 1
    boxes = []
    while i < len(lines) and re.match(r"^[pe] \d+ \d+", lines[i]):
        k = int(lines[i].split()[2]); pts = [tuple(map(int, lines[i + 1 + j].split()[:2])) for j in range(k)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        boxes.append((min(xs) / scale, min(ys) / scale, max(xs) / scale, max(ys) / scale)); i += 1 + k
    if n: out.append((name, n, cap[:1], boxes))
for name, n, cap, boxes in out:
    print(f"{name} ({n}) {cap[0] if cap else ''}")
    for b in boxes[:mx]: print("    [%.3f %.3f %.3f %.3f]" % b)
