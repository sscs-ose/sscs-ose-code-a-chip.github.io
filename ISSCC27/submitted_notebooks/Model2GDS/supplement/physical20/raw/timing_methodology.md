# Frozen post-route timing methodology

The authoritative primary quantity is an explicit OpenSTA register-to-register
max/setup query after routing, in corner `max_ss_100C_1v60`. It uses the final
routed netlist, extracted maximum SPEF, the saved OpenLane final STA environment,
the same slow-corner libraries and final post-route SDC. All inputs are bound by
run-relative paths, byte sizes and hashes to the same selected configuration.
The TCL and this document are frozen before accelerator physical measurements.

`scripts/phase2_r2r_sta.tcl` sources the saved corner environment, loads the
final routed artifacts, sets nanosecond timing units, and queries from
`all_registers -clock_pins` to `all_registers -data_pins`, path_delay max,
sorted by slack. It preserves the full expanded-clock path report and reports
the minimum finite setup slack among the returned worst paths. No input/output
or pre-route path substitutes for the required internal register path.

The final route's propagated-clock SDC is used. Scripted artifact identity and
corner/clock/period checks fail on different runs, missing inputs, no internal
path, missing/nonfinite slack or the wrong corner. The parser checks the full
path report against the emitted scalar. Native nonfinite R2R summary fields
remain unavailable; they do not become numeric timing values.

Let P_constraint = 20.0 ns and S_r2r be the worst finite post-route R2R setup
slack in this corner. The parser alone derives:

```
P_sta_est_ns = P_constraint_ns - S_r2r_ns
require P_sta_est_ns > 0
F_sta_MHz = 1000 / P_sta_est_ns
```

The exact terminology is **post-route fixed-layout STA-derived frequency
estimate**. It is a zero-slack estimate from one fixed routed implementation
and one frozen query/constraint method. It is not measured silicon frequency
and does not independently re-optimize designs across clock targets. The same
limitation and measurement boundary apply identically to each configuration.

Negative setup slack is permitted as evidence under the fixed 20 ns target;
it is not permission to retune the recipe. Native post-route hold counts/slacks
for every analyzed corner, routing and enabled DRC/LVS/antenna checks must be
acceptable. The R2R setup scalar does not replace these integrity checks.

This freeze defines measurement only. Architecture winners, implementation
latencies, pairwise agreement, margins, reversals and research conclusions are
deferred to separately authorized Phase 3.
