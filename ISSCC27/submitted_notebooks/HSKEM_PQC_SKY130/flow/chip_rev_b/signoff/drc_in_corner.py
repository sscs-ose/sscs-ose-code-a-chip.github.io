"""Exit 0 when every violation of a TritonRoute DRC report lies inside the ekPKE-corner box and there are at most N.
usage: drc_in_corner.py <report> [max=20]      box (um): x 640-760, y 1660-1780 (the known ekPKE top-right corner)
SPDX-License-Identifier: Apache-2.0"""
import re, sys
BOX = (640.0, 1660.0, 760.0, 1780.0)
rep = open(sys.argv[1]).read(); mx = int(sys.argv[2]) if len(sys.argv) > 2 else 20
b = [tuple(map(float, m)) for m in re.findall(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)", rep)]
out = [v for v in b if not (BOX[0] <= v[0] and v[2] <= BOX[2] and BOX[1] <= v[1] and v[3] <= BOX[3])]
print(f"violations {len(b)}, outside corner box {len(out)}")
sys.exit(0 if not out and len(b) <= mx else 1)
