---
name: viaduct-optimizer
description: Size circuits and the T-coil with Viaduct - .param sweeps in one ngspice process, picking the widest bandwidth under a peaking limit, matching the layout's FastHenry inductance to a target, and the full T-coil bandwidth-extension closed loop. Use for any "find values that maximise/meet" task.
---

# Optimizer patterns

## Sweeps

`vd.sim.sweep(netlist, params={...})` runs the full grid, or `cases=[{label, ...}]`
runs explicit points, all in one ngspice process (`alterparam` + `reset` + `ac`).
Each point returns `dc_gain_db`, `f3db_hz`, `peaking_db`, `gbw_hz`, ... ; `points.csv`
and (for <= 8 cases) `compare.png` land in `runs/sweep_<id>/`. Swept names must be
`.param`s in the netlist, so put component values in the schematic as `{NAME}` and
declare `.param NAME=...` in the code block.

Typical selection:

```python
r = vd.sim.sweep(netlist, cases=cases).check().result
ok = [p for p in r["points"] if p["f3db_hz"] and p["peaking_db"] <= 1.0]
best = max(ok, key=lambda p: p["f3db_hz"])
```

Cost: about 0.07 s per point for a small SKY130 testbench (150 points in 10 s, 13 Oct 2026). Prefer a coarse
grid, then refine around the best point.

## Matching layout to a target (EM in the loop)

1. From the ideal optimum compute the target series inductance
   `L_series = L1 + L2 + 2M = 2L(1 + k)` for a symmetric coil.
2. Move one geometry knob in KLayout (`set_pcell_params`, e.g. `area`) and run
   `vd.em.fasthenry(...)` at the design frequency for each value; pick the closest.
3. Final multi-frequency EM run; `annotate` the PCell; screenshot.
4. Back-annotate `spice_model` (L1, R1, L2, R2, K) into the schematic's params and
   re-simulate. Try both orientations (P1 or P2 at the driver): the coil is asymmetric.

## T-coil closed loop (design note 6.2)

`python examples/tcoil_amp_closed_loop.py [--cl 150f] [--peaking-db 1.0]` does all of
it live (schematic, optimizer, layout sizing, EM, annotation, back-annotation, graphs)
and writes `runs/closedloop_<id>/report.md` with every run ID. Constant-resistance
T-coil rule of thumb for the starting point: `L_series ~ R^2 C_L`, `k ~ 0.3-0.5`,
`C_B ~ C_L (1 - k) / (4 (1 + k))`.
