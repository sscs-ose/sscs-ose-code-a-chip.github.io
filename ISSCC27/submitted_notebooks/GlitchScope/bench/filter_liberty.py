"""Write a Liberty containing only an allowed subset of cells (for ABC mapping)."""
import re, sys
src, dst, cells = sys.argv[1], sys.argv[2], set(sys.argv[3].split(","))
text = open(src).read()
out, i = [], 0
for m in re.finditer(r'\n\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', text):
    if m.start() < i:
        continue
    out.append(text[i:m.start()])
    depth, j = 0, m.end() - 1
    while True:
        c = text[j]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: break
        j += 1
    name = m.group(1).replace("sky130_fd_sc_hd__", "")
    if name in cells:
        out.append(text[m.start():j + 1])
    i = j + 1
out.append(text[i:])
open(dst, "w").write("".join(out))
print("kept", sum(1 for _ in re.finditer(r'\n\s*cell\s*\(', "".join(out))), "cells")
