#!/usr/bin/env python3
"""The routed, extracted core across PVT: the same corners as the schematic sweep (run_sweep.py pvt), with the
full-core extraction in place of CDAC, comparator, top-plate switch and SAR logic.

    python3 studies/postlayout_pvt.py --bits 4     (needs run_layout.py core --bits 4 --pex)
Writes build/<N>bit/postlayout/pvt/ and results/<N>bit/layout/pvt_core.md next to the schematic pvt table.
"""
import argparse, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, sweep
from sargen.layout import core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, default=4)
    ap.add_argument("--hits", type=int, default=16)
    a = ap.parse_args()
    base = Path(f"build/{a.bits}bit")
    kw = core.extracted(a.bits, base / "layout")
    if kw is None:
        sys.exit(f"no core extraction: run  python run_layout.py core --bits {a.bits} --pex")
    design = json.loads((base / "design.json").read_text())
    out = base / "postlayout" / "pvt"
    rows, md = sweep.pvt(SarSpec(bits=a.bits), design, out, hits=a.hits, fft_n=128, **kw)
    dst = Path(f"results/{a.bits}bit/layout")
    dst.mkdir(parents=True, exist_ok=True)
    for src, name in ((out / f"pvt_{a.bits}b.md", "pvt_core.md"), (out / f"pvt_{a.bits}b.png", "pvt_core.png")):
        if src.exists():
            shutil.copy2(src, dst / name)


if __name__ == "__main__":
    main()
