"""Calibrate M2 for additional SKY130 HD cells, then refit the model.

    python scripts/calibrate_cells.py nand3_1,a22oi_1 [--quick]
"""
import sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file
from glitchscope.spice import pulse_sweep as ps
cells = sys.argv[1].split(","); quick = "--quick" in sys.argv
lib = parse_liberty_file(ps._env("GS_LIB"))
ps.ensure_cells(lib, cells)
for c in cells:
    print(c, "->", ps.CELLS[c])
kw = dict(slews_ps=(20, 100), loads_ff=(2.0,)) if quick else {}
rows = ps.sweep(cells, **kw)
out = ROOT / "data/m2" / f"pulse_sweep_{'_'.join(cells)}.csv"
ps.write_csv(rows, out)
print(f"wrote {len(rows)} rows -> {out.name}")
subprocess.run([sys.executable, str(ROOT / "scripts/fit_m2.py")], check=True, stdout=subprocess.DEVNULL)
print("m2_model.json refitted")
