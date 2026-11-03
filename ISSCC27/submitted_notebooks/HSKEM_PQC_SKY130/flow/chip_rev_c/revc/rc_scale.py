"""Scale the wire resistance and capacitance of a SPEF file (coupling included), for the RC sensitivity of the sign-off STA.
usage: rc_scale.py <in.spef> <out.spef> <R factor> <C factor>
SPDX-License-Identifier: Apache-2.0"""
import sys

src, dst, fr, fc = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
sec = None
with open(src) as f, open(dst, "w") as g:
    for line in f:
        if line.startswith("*D_NET"):
            p = line.split()
            g.write(f"*D_NET {p[1]} {float(p[2]) * fc:.6g}\n")
            sec = None
            continue
        if line.startswith("*CAP"):
            sec = "c"
        elif line.startswith("*RES"):
            sec = "r"
        elif line.startswith(("*CONN", "*END")):
            sec = None
        elif sec and line[:1].isdigit():
            p = line.split()
            p[-1] = f"{float(p[-1]) * (fc if sec == 'c' else fr):.6g}"
            g.write(" ".join(p) + "\n")
            continue
        g.write(line)
