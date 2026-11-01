# Compact clock timestep convergence

**Reviewed and accepted as timestep-consistency evidence for the compact tt PV cold-start bench; no electrical design acceptance.** One new 4 ms / 12.5 ns transient was compared with the accepted compact-placement 4 ms / 25 ns transient. All four requested differences, `abs(coarse−fine)/abs(fine)`, are below **1%**. This qualifies the measured observables under this timestep comparison; it does not establish electrical design or application acceptance.

| Observable, exact 2.4–4 ms window | Saved 25 ns | New 12.5 ns | Absolute relative difference to fine |
|---|---:|---:|---:|
| Clock frequency, Hz | 5954.456439 | 5954.900207 | 0.00745215% |
| Analog clock power, nW | 43.670458 | 43.672419 | 0.00448987% |
| First FF + feedback power, nW | 2.584443 | 2.583378 | 0.04121354% |
| Whole clock + first FF power, nW | 46.254901 | 46.255797 | 0.00193734% |

The unchanged full-data audit interpolates signal crossings relative to instantaneous vdd/2 and integrates power over exactly 2.4–4 ms, with linear interpolation at the boundaries and trapezoidal integration of all adaptive samples. Power is integrated from vdd × measured current. Fine-run energies over that interval are **69.875870 pJ** analog, **4.133405 pJ** receiver and **74.009275 pJ** whole. Separate internal bias-reference power is unavailable.

| Behavior | Saved 25 ns | New 12.5 ns |
|---|---:|---:|
| Time-averaged rail, V | 1.743184113 | 1.743216874 |
| Rail minimum–maximum, V | 1.51654003–1.82072441 | 1.51673804–1.82072471 |
| Steady clock rises / Q rises / Q falls | 9 / 5 / 4 | 9 / 5 / 4 |
| Sustained Q/clock frequency ratio, >=0.4 ms | 0.500000000654 | 0.499999999015 |
| Clock rises between every successive sustained Q rise | 2 | 2 |
| Existing unchanged bench criterion | true | true |

Complete crossing arrays and the original sample-index bench evaluation are retained in `metrics.json`. The existing bench still requires at least five steady clock rises and three steady Q rises, full swing and divide-by-two frequency within its existing tolerance. No criterion was relaxed.

The fine transient contains **328249 rows and eight finite columns**, starts at exactly zero, has nondecreasing time and reaches exactly **0.004 s**. The saved coarse transient has **169690 rows**, also satisfying the same completion checks. Neither log contains an abort, `doAnalyses:` or timestep-too-small marker. Fine execution returned **zero in 70.198615 s**, within the unchanged 180 s timeout. The known PDK `m=xx` hierarchy warning remains. Fine maximum observed time difference is 12.50000000036 ns, consistent with output decimal precision. Completion is established from full data and logs as well as exit status.

Only the two timestep fields on the single `tran` line changed:

```diff
-tran 2.5e-08 0.004 0 2.5e-08
+tran 1.25e-08 0.004 0 1.25e-08
```

`source_25ns.spice`, `clock.spice` and `deck.diff` retain the exact transformation. Before simulation, the runner checked every saved 25 ns input/output hash against accepted compact-placement metrics, the top-level PDK library hash, the receiver and initialization files, and exact reversal of the timestep-only substitution. `input_checks.json` records these checks, the runner/helper hashes and their UTC checkpoint before the simulator start. The fine execution record, log and input/output hashes are retained. Source deck SHA-256 is `0f1d3db20d2ee27191b068083270e5138cdfc04326a1e34aa23d5137e44afff9`; fine deck SHA-256 is `9ce3fe5d28860b620a134d1867d76844f95981e3858bb694516ef26b28fd8cab`.

All models, topology, compact layout and extracted RC, startup, load and solver settings are unchanged: tt / 26.85 °C; three fitted PV cells at assumed 150 µm²/cell; 1 µs dark then 100 µs optical ramp; 2 pF storage and 2 fF output load; real SKY130 DFF and feedback; Gear2, reltol 1e-6, abstol 1e-15; zero-supply operating point without UIC or seeded voltages. No physical evidence was regenerated.

Executed from the repository root:

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -u examples/microrobot/results/clock_compact_convergence/run_convergence.py
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python examples/microrobot/results/clock_compact_convergence/run_convergence.py --audit-only
```

The first command requires a fresh `local_runs/clock_layout/compact_x_v1/extracted_12p5ns` directory and invokes ngspice exactly once. The second command refreshes the full-data evidence without invoking a simulator. The saved coarse transient is reused. `sha256.json` covers compact evidence except itself and Python caches; full raw transient hashes are in `metrics.json` while raw `clock.dat` files remain local. `verification.json` records the final focused deck, completion, threshold, behavior and manifest checks.

There was no additional refinement, full test suite, PVT or mismatch run. This is convergence evidence for one extracted compact circuit at one PV cold-start condition and the listed observables. Raw transients and local PDFs are excluded from exported evidence. No submission, publication, push or fabrication was initiated.
