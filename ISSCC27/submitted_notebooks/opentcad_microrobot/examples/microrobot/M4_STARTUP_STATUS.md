# M4: short coupled startup investigation

**Exploratory electrical evidence, not an accepted autonomous controller.**
The clock, native first DFF, reset conversion, two transistor drivers and finite
PV supplies now run together in short diagnostic benches. The remaining divider
is an XSPICE event model, its power is a switched-capacitance proxy, and the
interfaces are reduced electrochemical models. No full gait, dark recovery,
complete POR corner envelope or controller layout has been qualified.

Existing numerical reference artifacts remain unchanged. The M3 integrity
manifest refreshes only the current `electrical.py` workflow hash for the M4
simulator-abort guard; its previous hash is retained separately, without
rewriting historical execution claims. Compact M4
reports, exact generated decks, source hashes and plot previews are in
[results/m4_startup](results/m4_startup/manifest.json). Full adaptive `.dat`
waveforms remain in ignored local run directories. Reports use those full
waveforms; preview decimation is for plotting only.

## What the short experiments establish

The original cross-coupled reset converter consumes about **1.40 pJ** during the
0.50–0.55 ms release window. Its logic rail falls from about 1.60 V to 1.06 V;
reset undershoots by about 0.378 V in the completed 100 ns run. A 50 ns repeat
agrees around the defect but later aborts. These observations support excessive
converter transient loading; they do not establish an exact physical undershoot.
The subsequent reset-converter experiments retain 2 pF logic storage.

The nonregenerative `ready_levelshift_current_limited.spice` removes the latch.
With the original 2 pF logic storage, matched TT **2 ms / 50 ns and 25 ns**
diagnostics both reach their requested stop. Each of 13 steady clock rising
edges has one native-Q transition, consistent with divide-by-two. Reset's minimum
is approximately −15.6 mV, and release occurs with logic above approximately
1.57 V. Full source-energy differences are below 0.046%; very small signed phase
power residuals have much larger relative differences and are not precision
power estimates. This is a numerical gate for the short logic-reset reference,
not autonomous or PVT acceptance.

Driver clamp policy is a separate problem. Connecting an actuator-powered pair
of inverters to native reset releases driver gates while logic is still at
subthreshold voltage. The pair and the standard-Vt AND qualifier each produce
about **235 mV** early electrode-metal error relative to the PV midpoint.
Forcing the actual driver-ready pins to zero reduces that error to **3.179 mV**;
this is an ideal isolation control, not an implemented solution.

Changing only the final AND output pulldown to a supported LVT NFET reduces the
nominal 0–0.4 ms peak metal error to **3.422 mV**, with local electrode eta bounded
by about **21.5 µV during that cold window**. A residual early driver-enable voltage pulse
remains at very low rails. A logic-ratio threshold crossing at such rails does
not establish useful CMOS operation. The 50 ns full 2 ms run reaches its stop with all 18 post-release clock
rising edges mapped to native-Q transitions. Its largest electrode excursion
outside the actuator rails is about 9.90 mV; definite-reset-low midpoint error
is about 25.3 µV where logic ≥1 V, actuator ≥0.5 V and reset ≤10% of
instantaneous logic. The chosen checks are <50 mV for that clamp error and
<100 mV outside the actuator rails; they are diagnostic engineering limits.
The matched 25 ns run also reaches 2 ms. Both runs map all 18 post-release
clock rising edges to native-Q transitions; frequency changes by 0.002441%
and all full source energies change by less than 0.0564%. Cold clamp error is
3.422/3.424 mV at 50/25 ns. No full-controller acceptance
follows from these short nominal checks.


The single TT **85 °C** sensitivity attempt requested 0.8 ms but aborted at
**101.757 µs**, with 2230 finite saved rows and a timestep-too-small report
(`vdriverbuffer#branch`). It stopped before powered operation: logic was about
33 µV and actuator supply about 0.448 mV. This is an unresolved numerical
startup test, not evidence of a physical hot failure or a hot leakage bound.
No rescue run was included in that frozen 17-case snapshot. The nominal TT
result does not qualify hot startup.

A [later numerical follow-up](results/m4_hot_followup/REPORT.md), outside the
frozen 670-hash review bundle, also aborts before powered operation after
removing one probe and after changing Gear order. It provides no hot-startup
or hot-leakage qualification; the follow-up branch is stopped.

A [later nominal dark/recovery experiment](results/m4_dark_recovery/REPORT.md)
requests 4.5 ms but aborts at 3.00089994 ms before relight. Reset/driver enable
remain released through the observed falling-light/dark interval. Separate
2.2 ms 50/25 ns prefixes reproduce that retention; they do not qualify recovery
or change the original failed completion. This evidence also remains outside
the frozen review bundle.

The reported metal-to-midpoint error and local electrochemical eta are different
quantities. Later in the 2 ms transient, local eta spans approximately ±0.534 V;
that range has no calibrated electrochemical safe-window interpretation.
The native reset also exceeds the tiny logic rail by up to **157.6 mV during
cold startup**. No input-stress, protection-diode or overvoltage qualification
is established by the output-electrode limits.

The chosen interface parameters and clamp limits are engineering
assumptions, not calibrated electrochemical safety limits or measured robot data.

Reviewer plots: [cold clamp and local eta](results/m4_startup/cold_clamp_and_local_eta.png),
[release window](results/m4_startup/release_window.png), and
[historical reset comparison](results/m4_startup/reset_comparison_reproduced.png).

## Circuit status matrix

“Default” identifies preserved source/API behavior; it does not mean accepted.
All custom variants retain explicit limitations and have no new layout signoff.

| Circuit | Role and executed status |
|---|---|
| `starved_clock.spice` | Preserved nominal clock; previously qualified clock/first-DFF benches. Full controller not qualified. |
| `actuator_driver.spice` | Preserved driver with standalone preliminary corner checks; actual gates retained in coupled experiments. |
| `electrochemical.spice` | Reduced interface model; not calibrated device data. |
| `bias_reference.spice` | Existing physically verified bias macro only; no new M4 layout. |
| `brownout_candidate.spice` | Original corner-rejected monitor; not complete POR. |
| `brownout_v2.spice` | Legacy coupled default monitor; startup investigated, no complete POR corner gate. |
| `brownout_v3.spice` | Exploratory keeper revision; no complete POR acceptance. |
| `ready_levelshift.spice` | Legacy cross-coupled converter; nominal startup loading failure. |
| `ready_levelshift_weak.spice` | PMOS L16 model-eligible, but release at 1.289 V and −0.411 V undershoot fail provisional gate. |
| `ready_levelshift_buffered.spice` | Actuator prebuffer plus original latch; rejected low-rail release/negative reset excursion. |
| `ready_levelshift_current_limited.spice` | Six-port bp-connected nonregenerative converter; short nominal 50/25 ns numerical reference passes. Original monitor-ready still controls drivers in that reference. |
| `ready_levelshift_qualified.spice` | **Unexecuted, superseded design sketch.** Starved first stage does not bound ordinary second-stage crowbar. |
| `ready_levelshift_schmitt.spice` | Isolated receiver has 0.451 V hysteresis and fast edges, but 99 pJ rising-ramp energy; rejected for this supply budget. No coupled run. |
| `ready_driver_buffer.spice` | Direct actuator inverter pair; low energy but early cold-start clamp release. Rejected policy. |
| `ready_driver_qualified.spice` | AND(native reset, monitor-ready), standard-Vt output; cold-start metal error remains about 235 mV. |
| `ready_driver_qualified_lvt.spice` | Same AND with final LVT output pulldown; TT 2 ms / 50 ns and 25 ns scoped numerical/clamp gates pass; 85 °C startup remains unresolved after an early numerical abort. Full controller remains unaccepted. |
| `starved_clock_slow.spice` | Real changed clock design, not time acceleration. Enlarged timing plates total 2100 µm²; finite-PV native-divider gate fails. |

The isolated actuator-powered pair draws about 0.352 pJ over its imposed
bidirectional 100 µs ramps, but its output is already 90% high at raw input
0.472 V, below the diagnostic 90%-of-logic comparison of 1.53 V. This
comparison is not a PDK input-high or reset-removal specification. The coupled
pair is rejected on its measured cold-start metal error, rather than that
comparison alone. Low energy does not establish correct clamp policy. The custom Schmitt's 99 pJ rising
ramp exceeds the entire 2 pF / 1.7 V reservoir energy by about 34 times.

## Reproduction and API scope

Use the environment/native prerequisites in [SETUP.md](SETUP.md). The explicit
`controller.run_diagnostic()` API defaults to a fresh **2 ms**, **50 ns maximum
step**, adaptive waveform with the current-limited converter's sixth port
connected to the native clock `bp`. It omits auxiliary numerical energy states
and integrates signed port powers offline, including the actuator converter port.
The original `controller.run()` / `controller_deck()` APIs retain their legacy
exploratory defaults and numerical energy integrators; they are not the qualified
reference. The module CLI defaults to the short logic-only diagnostic;
`--legacy` explicitly selects the old circuit/integrator path. The LVT driver
qualifier is an explicit optional policy, reproduced in a fresh directory with:

```sh
python -m examples.microrobot.controller --driver-ready qualified-lvt \
  --stop .002 --max-step 25e-9 \
  --output examples/microrobot/local_runs/m4_reproduction_NEW
```

The public generated deck matches the executed control deck apart from comments.
Both nominal TT runs complete. This verifies only the reported short nominal
gates; availability of the flag is not complete-controller acceptance.

Recreate the static cold-start/release figures without ngspice or the PDK:

```sh
MPLCONFIGDIR=/tmp/opentcad-mpl python examples/microrobot/results/m4_startup/reproduce_plots.py
```

This regenerates the plots from archived small extrema-preserving previews,
not the numerical metrics. Exact decks and hashes identify the executed cases;
regenerating a result requires the corresponding installed models/native tools.
The earlier reset comparison PNG is retained as historical 100 ns evidence.

Remaining work includes a justified complete reset/clamp policy, cold/dark
restarts and recovery, supported process/temperature/illumination corners,
full output cycles, numerical stability and energy balance, and physical
verification of the assembled controller. No fabrication has been performed.
