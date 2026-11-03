"""Where on the die is glitch energy burnt?  Placed-and-routed 16x16 multiplier, before and after GlitchScope's fix.

Reads the routed DEF of each layout (section 10/11 flow), and GlitchScope's per-cell glitch energy on the same
netlist (``glitchscope.flow --no-attribution``, 40 random cycles), and writes one compact file the notebook draws.

    python scripts/layout_glitch_map.py <liberty>      -> data/layout/glitch_map.json
"""
import csv
import gzip
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = {"v0": "bench/layout/mul16_v0.v", "r_milp": "data/glitchfix/mul16_r/best_milp.v"}
CYCLES, PERIOD = 40, 15000


def placements(def_gz):
    sizes = json.loads((ROOT / "data/layout/cell_sizes.json").read_text())
    txt = gzip.open(def_gz, "rt").read()
    die = [int(v) / 1000 for v in re.search(r"DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \)", txt).groups()]
    comp = txt[txt.index("\nCOMPONENTS"):txt.index("END COMPONENTS")]
    out = []
    for name, cell, x, y in re.findall(r"- (\S+) (sky130_fd_sc_hd__\w+) .*?PLACED \( (-?\d+) (-?\d+) \)", comp):
        w, h = sizes.get(cell, (0.46, 2.72))
        kind = ("ff" if "dfxtp" in cell else "clk" if "clkbuf" in cell or "clkinv" in cell else
                "fill" if re.search(r"fill|tap|decap|diode", cell) else "logic")
        out.append((name.replace("\\", ""), round(int(x) / 1000, 2), round(int(y) / 1000, 2), w, h, kind))
    return die, out


def glitch_per_cell(lib, netlist):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([sys.executable, "-m", "glitchscope.flow", "--netlist", str(ROOT / netlist), "--random-vectors",
                        str(CYCLES), "--period-ps", str(PERIOD), "--lib", lib, "--no-attribution", "--out", td],
                       check=True, cwd=ROOT, capture_output=True)
        summ = json.loads((Path(td) / "summary.json").read_text())
        with open(Path(td) / "glitch_cells.csv") as f:
            return {r["cell"]: float(r["consumed_glitch_fJ"]) / CYCLES for r in csv.DictReader(f)}, summ


def main():
    lib = sys.argv[1]
    res = {}
    for tag, net in DESIGNS.items():
        die, cells = placements(ROOT / f"data/layout/{tag}/6_final.def.gz")
        e, summ = glitch_per_cell(lib, net)
        rows = [[x, y, w, h, k, round(e.get(n, 0.0), 2)] for n, x, y, w, h, k in cells if k != "fill"]
        res[tag] = dict(die=die, cells=rows, flops=sum(r[4] == "ff" for r in rows),
                        glitch_pJ=round(sum(r[5] for r in rows) / 1e3, 2), summary_keys=sorted(summ)[:0])
        print(tag, "die", die[2:], "cells", len(rows), "flops", res[tag]["flops"], "glitch pJ/cycle", res[tag]["glitch_pJ"])
    (ROOT / "data/layout/glitch_map.json").write_text(json.dumps(res, separators=(",", ":")))


if __name__ == "__main__":
    main()
