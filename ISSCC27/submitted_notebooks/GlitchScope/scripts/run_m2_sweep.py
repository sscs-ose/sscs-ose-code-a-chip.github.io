"""Run the full M2 SPICE pulse-survival sweep -> data/m2/pulse_sweep.csv"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from glitchscope.spice.pulse_sweep import sweep, write_csv, CELLS
t = time.time()
cells = sys.argv[1].split(",") if len(sys.argv) > 1 else list(CELLS)
rows = sweep(cells)
out = Path(__file__).resolve().parents[1] / "data/m2" / (sys.argv[2] if len(sys.argv) > 2 else "pulse_sweep.csv")
write_csv(rows, out)
print(f"M2_SWEEP_DONE rows={len(rows)} secs={time.time()-t:.0f} -> {out}")
