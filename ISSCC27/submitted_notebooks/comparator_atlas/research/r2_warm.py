"""Warm the R2 SPICE cache for a design by evaluating a slice of conditions (no outputs written)."""
import sys
from dataclasses import replace

import r2_prospective as r2

design, start, stop = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
inputs = r2.FIT_INPUTS if sys.argv[4] == "a" else r2.HELD_INPUTS
points = [replace(p, design_name=design) for p in r2.cases("full")]
for i in range(start, stop, 1 if stop > start else -1):
    ev = r2.Evidence(r2.Simulator(r2.CACHE, workers=2))
    cal = ev.calibration(points[i])
    code = r2.chosen_code(cal)
    if code is not None:
        ev.observations(points[i], {"local_boundary": code}, inputs, r2.DEADLINES)
    print("warm", design, i + 1, r2.case_id(points[i]), flush=True)
