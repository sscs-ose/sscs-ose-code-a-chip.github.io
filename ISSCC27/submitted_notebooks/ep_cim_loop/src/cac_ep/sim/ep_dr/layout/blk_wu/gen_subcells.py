#!/usr/bin/env python3
"""부품 셀 하나씩 GDS·CDL (Pegasus 단독 DRC·LVS 용) → out/<셀>.gds·.cdl.
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_subcells.py [셀 …]"""
import os, sys, json
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import klayout.db as pya   # noqa: E402
import wu_cells as W       # noqa: E402

OUT = os.path.join(H, "out")
os.makedirs(OUT, exist_ok=True)
JOBS = {"wu_sa": W.build_sa, "wu_pre": W.build_pre, "wu_dlat": W.build_dlat, "wu_tg3": W.build_tg3,
        "wu_rbank": W.build_rbank, "wu_mim10": lambda ly: W.build_mim(ly, "wu_mim10", 10.0),
        "wu_mim20": lambda ly: W.build_mim(ly, "wu_mim20", 20.0)}
sel = sys.argv[1:] or list(JOBS)
summ = {}
for name in sel:
    ly = pya.Layout(); ly.dbu = 0.001
    C, info = JOBS[name](ly)
    ly.write(os.path.join(OUT, name + ".gds"))
    open(os.path.join(OUT, name + ".cdl"), "w").write("\n".join(info["cdl"]) + "\n")
    bb = C.c.bbox()
    bad = C.shorts()
    summ[name] = dict(w=bb.width() / 1000, h=bb.height() / 1000, shorts=bad)
    extra = ""
    if "rows" in info:
        extra = " | " + ", ".join(f"{r['name']} {r['y1'] - r['y0']:.2f}" for r in info["rows"]) + f" | bands {info['bands']}"
    if "c_ff" in info:
        extra = f" | w {info['w']} C {info['c_ff']} fF"
    if "r_seg" in info:
        extra = f" | seg {info['r_seg']:.1f} Ω L {info['r_l']}"
    print(f"{name}: {bb.width() / 1000:.3f} × {bb.height() / 1000:.3f} µm, shorts {bad or 'none'}{extra}")
json.dump(summ, open(os.path.join(OUT, "subcells.json"), "w"), indent=1)
