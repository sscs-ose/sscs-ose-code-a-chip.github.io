"""Re-characterise the calibrated SKY130 HD cells with ngspice, state-dependent arcs
included, and write a Liberty file with those timing tables.

    python scripts/charlib.py [cell ...]     -> data/charlib/<cell>.json, bench/basic_cells_spice.lib
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file  # noqa: E402
from glitchscope.spice.charlib import characterise, write_liberty  # noqa: E402

CELLS = ["inv_1", "buf_1", "nand2_1", "nor2_1", "and2_1", "or2_1", "xor2_1", "xnor2_1", "a21oi_1", "o21ai_0"]


def main():
    src = ROOT / "bench/basic_cells.lib"
    lib = parse_liberty_file(src)
    out = ROOT / "data/charlib"
    out.mkdir(parents=True, exist_ok=True)
    chars = {}
    for c in sys.argv[1:] or CELLS:
        p = out / f"{c}.json"
        if p.exists():
            d = json.loads(p.read_text())
        else:
            t = time.time()
            ch = characterise(lib, c)
            d = dict(outpin=ch["outpin"], index_1=list(ch["index_1"]), index_2=list(ch["index_2"]),
                     arcs={pin: [dict(state=s, sense=se, tables={k: np.asarray(v).tolist() for k, v in tb.items()})
                                 for s, se, tb in lst] for pin, lst in ch["arcs"].items()})
            p.write_text(json.dumps(d))
            print(f"{c}: {sum(len(v) for v in d['arcs'].values())} arcs in {time.time() - t:.0f} s", flush=True)
    for c in CELLS:
        p = out / f"{c}.json"
        if p.exists():
            d = json.loads(p.read_text())
            chars[c] = dict(outpin=d["outpin"], index_1=d["index_1"], index_2=d["index_2"],
                            arcs={pin: [(a["state"], a["sense"], {k: np.asarray(v) for k, v in a["tables"].items()})
                                        for a in lst] for pin, lst in d["arcs"].items()})
    write_liberty(src, chars, ROOT / "bench/basic_cells_spice.lib")
    print("wrote bench/basic_cells_spice.lib with", len(chars), "re-characterised cells")


if __name__ == "__main__":
    main()
