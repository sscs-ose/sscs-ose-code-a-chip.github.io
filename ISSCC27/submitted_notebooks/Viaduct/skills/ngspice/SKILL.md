---
name: viaduct-ngspice
description: Simulate with ngspice through Viaduct - run a netlist or the open xschem schematic, get AC/transient metrics as JSON (gain, f3dB, peaking, GBW), Bode plots, and live waveform graphs on the schematic. Use whenever a circuit result is needed.
---

# ngspice through Viaduct

ngspice runs in batch mode in the container (SKY130 environment loaded). Each run
gets `runs/sim_<run_id>/`: netlist copy, `ngspice.log`, every `.raw`, `metrics.json`,
`bode.png` / `tran.png`.

## API

| Task | CLI | Python |
|---|---|---|
| simulate the open schematic, graphs on it | `python client.py -t xschem simulate --nodes out` | `vd.sim.xschem(["out"])` |
| simulate a netlist | `python client.py sim /foss/designs/.../tb.spice --nodes out` | `vd.sim.run(netlist, ["out"])` |
| operating point of every MOSFET | `python client.py sim-op [NETLIST]` (default: open schematic) | `vd.sim.op()` |
| sweep .param values (one process) | `python client.py sweep NETLIST --param L1=1e-10,2e-10 K=0.3,0.5 --node out` | `vd.sim.sweep(netlist, {"L1": [...]}, "out")` |

Result: `result.raw_files[i].plots[j].nodes[node]` with, for AC:
`dc_gain_db`, `dc_gain_vv`, `peak_db`, `f_peak_hz`, `peaking_db`, `f3db_hz`,
`ugf_hz`, `gbw_hz`, `phase_at_ugf_deg`; for transient: `min`, `max`, `final`,
`pk_pk`. `status` is COMPLETE only when ngspice exited 0, logged no errors and
wrote a .raw. Look at `local_images` (Bode plot) as well as the numbers.

## Rules

- The netlist's `.control` block decides the analyses; Viaduct only runs and parses.
  Without `.control`, `-r out.raw` is used.
- `phase_at_ugf_deg` is the phase at unity gain of this transfer function, not a phase
  margin (that needs a loop-gain testbench).
- `f3db_hz` is relative to the first (lowest) frequency point; start the sweep well
  below the pole.
- Check the bias before trusting AC numbers: `sim-op` lists Id, gm, gds, Vov, Vds, Vdsat,
  the `vds_margin` (|Vds| - Vdsat) and the region of every MOSFET; `warnings` names any device
  in triode or within 50 mV of it (e.g. a tail source starved by a low input common mode).
- Report `run_id` with every number.

## Worked example: five-transistor OTA

`examples/ota5t_xschem.py` builds it live (pin-name wiring, `check`), simulates, runs `sim-op`;
`examples/ota5t_sweep.py` sweeps L of pair and load in one run (`.param`-ized netlist);
`examples/ota5t_characterize.py` derives buffer / CMRR / swing testbenches from the same netlist:
slew and 1 % settling (measured against the real final value, not the ideal one), CMRR,
input common-mode range (all devices saturated, not just "output tracks input") and output swing.

## Sweep netlists

`sweep` needs the swept quantities as `.param` in the netlist (e.g. `L1 X T {L1}`
with `.param L1=0.3n`). It strips the netlist's own `.control`, then runs
`alterparam` + `reset` + `ac` for every combination and measures the node.
