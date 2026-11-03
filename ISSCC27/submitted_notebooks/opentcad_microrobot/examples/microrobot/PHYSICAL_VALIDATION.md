# Driver and first physical-layout milestone

This is a functional SKY130 reimplementation, not the Reynolds XT018 SOI
circuit or layout. The earlier device/fit/behavioral system remains in
`microrobot.ipynb`. `electrical_layout.ipynb` checks and displays the experiments
below. The notebooks distinguish measured-paper data, fitted PV parameters,
my component choices and numerical verification.

## Short coupled startup follow-up

[M4_STARTUP_STATUS.md](M4_STARTUP_STATUS.md) records the newer short coupled
finite-PV clock/reset/driver experiments, including failed candidates and a
current-limited nominal reset reference. The original 2 pF logic storage is
retained. A separate LVT driver-enable qualifier improves the early nominal
clamp error and passes scoped nominal TT 2 ms / 50 ns and 25 ns checks. A single
85 °C attempt aborts before powered operation; hot startup remains unresolved.
The full controller is still unaccepted. These experiments add no
controller layout, post-layout corner or fabrication qualification. The older
standalone results below retain their original scope.

## Executed scope

- Two transistor drivers, level conversion, reset-to-midpoint switches and a
  finite actuator PV pair drive two reduced electrochemical interfaces and a
  Pt return through electrolyte resistances. Phase, ready and logic supply
  are external ideal stimuli in this bench; this is not an integrated controller.
- The clock's five-transistor bias macro and its two MIM capacitors have a
  routed layout, native and GDS-round-trip DRC/LVS, RC extraction and electrical
  comparisons with the remaining clock and first divider stage at schematic level.
- The brownout circuit is a **rejected development candidate**. Its FS threshold
  exceeds the available PV-powered logic rail; it cannot provide the final ready
  signal. Complete POR/reset, oscillator/driver/digital layout, assembly and
  full-controller post-layout validation remain outstanding.

## Reproduction

Use `requirements-notebook.txt` and the native prerequisites in `SETUP.md`.
The old Python 3.14.2 lock records the historical environment only. Native tools used: ngspice 44.2,
Magic 8.3.546 (Tcl 9.0.3), SKY130A/open_pdks 1.0.535, Netgen 1.5.325
(commit `e5a185dcfa16ee6317883f02bfdc8cf10feabd0e`, Tcl 8.6.16).
Model/generator/setup hashes are in the reports and the milestone manifest.
These are the tested versions, not a claim that newer releases are equivalent.

```sh
export PDK_ROOT=/usr/local/share/pdk
export NETGEN=/tmp/opentcad-netgen/bin/netgen  # replace with your installation
export MPLCONFIGDIR=/tmp/opentcad-mpl
python -m examples.microrobot.electrical --output examples/microrobot/local_runs/electrical_reproduction
python -m examples.microrobot.layout --output examples/microrobot/local_runs/layout_reproduction
python -m pytest tests/integration/test_electrode_spice.py tests/integration/test_layout_edge_audit.py
```

The layout flow requires a fresh destination to preserve existing work. It
runs 2/3/5 pF storage cases, a longer 5 pF run, tight-tolerance checks and
matched schematic comparisons, retaining all failures.
`--no-postlayout` runs physical checks/extraction without ngspice. Full raw
transients are generated locally and ignored; archived `.csv.gz` previews are losslessly compressed and decimated
for plotting only. Metrics and edge counts use the full adaptive transients.
The report notebook defaults to archived results and checks their hashes;
its explicit regeneration cell runs the external tools in fresh directories.

Netgen was built locally from its official source. On this Mac, configuration
used `--with-tcl=/opt/homebrew/opt/tcl-tk@8/lib`, the corresponding `--with-tk`,
`--with-x --x-includes=/opt/X11/include --x-libraries=/opt/X11/lib`,
`CC=/usr/bin/clang`, and
`CFLAGS='-std=gnu17 -Wno-error=implicit-function-declaration'` with a local
`--prefix`. Run `make -j4` and `make install` after configuring; no global
installation is required. The Python lock does not install these native tools.

The installed Magic generator's relative Tcl variable qualification fails under
Tcl 9. `layout.py` substitutes `$::sky130::ruleset` for `$sky130::ruleset` in an
in-memory copy. It does not modify installed PDK files, DRC decks or device rules.
Magic versions before 8.3.597 use the legacy `ext2sim`/`extresist` sequence used
here; other versions require requalification against the official documentation.

## Driver circuit and electrical results

`circuits/actuator_driver.spice` has explicit well/body connections and a
cross-coupled level converter from the logic to actuator domain. A transmission
gate clamps each output to the Pt midpoint while ready is low. Standard-Vt
clamps failed the 50 mV discharge criterion in SS and FS. Long-channel LVT
clamps pass. A chosen 7 × 7 µm MIM (~103 fF) per output suppresses switching
feedthrough. This is a design component, not extracted electrode capacitance.
The old revision and its failures remain in `results/electrical`; the current
source corresponds to `results/electrical_v2`.

Five corners (TT/SS/FF/SF/FS at 26.85 °C), TT at 85 °C, half illumination,
1 µs input edges, and a halved timestep all pass my preliminary limits:
excursions outside actuator rails <100 mV, settled output error <20 mV,
and reset clamp error <50 mV after 20 ms. Settled measurements exclude 2 ms
around either channel's switching edge because they share a return; the peak
check includes those transients. Worst excursion in these nine tests is about
46.7 mV; the largest five-corner reset error is 3.61 mV. These limits are my
engineering choices, not a published electrochemical safe operating window.

Nominal actuator PV delivery is 2.395 nW at 3 Hz, approximately 0.798 nJ per
cycle for both outputs and their interfaces. Halving the maximum timestep
changes that power by 0.026%. Logic and stimulus-port powers are measured
separately, with signed currents (ports can return charge). Their few-pW
residuals are **not converged precision power estimates**: cancellation around
fast switching edges changes them materially with timestep. Full controller
power must include the source of phase/ready and the unfinished brownout logic.
The hot bench also dips to ~0.718 V actuator span during reset transitions;
passing the three output criteria is not a guarantee of arbitrary load margin.

The interface model has Cdl, adsorption charge with finite relaxation, Faradaic
leakage, and a finite electrolyte return. For each leg, chosen Cdl=40 pF,
Qmax=260 pC, relaxation=20 ms and RF=10 GΩ; the return is ten times the charge/
capacitance and one tenth the resistance. These values remain uncalibrated.
The internal 1 nF state capacitor is a numerical encoding of coverage, not a
physical energy store. Analytical tests independently check the no-adsorption
RC limit, adsorption relaxation and terminal charge conservation. Mechanical
relaxation remains separate in the earlier reduced system; these transistor
bench results do not establish walking speed or a calibrated bending prediction.
PV temperature is held at the fit temperature in hot-driver experiments.

## Brownout result: not accepted

`circuits/brownout_candidate.spice` uses the clock bias, a current-mirror
comparator and positive feedback. Slow transient ramps, not DC branch-switching
artifacts, establish its turn-on/off thresholds. At VACT=1.245 V:

| Corner | Turn on (V) | Turn off (V) |
|---|---:|---:|
| TT | 1.705 | 1.648 |
| SS | 1.707 | 1.651 |
| FF | 1.708 | 1.653 |
| SF | 1.553 | 1.498 |
| FS | 1.872 | 1.816 |

The prior finite-PV FS clock rail is ~1.798 V, below FS turn-on. TT at 85 °C
requires ~1.776 V and draws ~61.6 nW from the actuator supply at Vlogic=1.77 V.
VACT sensitivity is substantial. Redesign and integration are necessary before
claiming autonomous startup/brownout recovery or laying out this candidate.

## Layout and extraction evidence

`results/layout/bias_reference_final` contains the current rectangular-port `.mag`, GDS, exact scripts,
DRC/LVS logs, negative-control LVS, extracted netlists and electrical benches.
The macro is 92.4 × 40.265 µm (about 3720 µm²), deliberately spacious and not
optimized for the paper's footprint. Four equal NMOS devices share orientation;
the sensing device and mirror are adjacent. PDK-generated substrate/well
contacts and guard structures surround the devices. This is not a common-centroid
array or a statistical matching guarantee. Bias routing uses M2/M3; MIM top plates
escape in M4 before vias descend outside the plates. No switching clock route
crosses this standalone macro.

- Native Magic DRC: **0 errors** over the complete macro.
- Native Netgen LVS: **unique match**, 7 devices and 5 nets, with PDK property checks.
- An intentionally wrong gate connection: **rejected** by LVS.
- GDS exported and imported into a new session: **0 DRC errors and LVS match**.
  Zero-area ports initially disappeared on GDS import; rectangular pin markers
  corrected the export. Both generator reproduction and round-trip checks passed.
- Legacy Magic RC extraction: **152 resistors, 45 parasitic capacitors**, in
  addition to the two explicit MIM devices. Capacitance-only extraction is
  retained for comparison. This is not a calibrated 3D field-solver result.

At an ideal 1.8 V supply, extracted bias changes frequency by about −0.054%
and power by +0.61%. Initial finite-PV runs at ngspice `reltol=1e-4` produced
inconsistent divider failures across 2/3/5 pF storage, timestep and a fresh
extraction. Increasing storage alone was **not an established fix**. The
original point-port results remain in `results/layout/bias_reference`; they
are superseded by the explicit numerical-tolerance audit below.

Tightening `reltol` to **1e-6** makes both 2 pF and 5 pF pass at **50 ns and
25 ns** maximum timesteps, including every observed steady-state divider period.
At 2 pF, halving the timestep changes frequency by **0.00445%** and power by
**0.000870%**. At 5 pF, the corresponding changes are about 0.00459% and
0.00171%. These results are consistent with a numerical artifact at loose
settings, not proof that physical storage must increase. Keep the original
2 pF as the nominal choice; no additional capacitor area is justified by this
experiment. The qualification requires all edge checks and <1% changes in both
frequency and power. All loose-setting failures are retained for diagnosis.

The matched **2 pF / 25 ns / reltol=1e-6 / TT** comparison gives:

| Quantity | Schematic | Extracted bias macro |
|---|---:|---:|
| Clock frequency | 13.0542 kHz | 12.9347 kHz |
| Clock plus first-DFF power | 43.5846 nW | 43.6718 nW |
| First-DFF divide-by-two | pass | pass |

Frequency changes by −0.915%, power by +0.200%, and the first clock crossing
is 12.23% later. These are **4 ms nominal TT** checks with Gear2 and
`abstol=1e-15 A`, not full post-layout PVT, mismatch or long-duration signoff.
A separate 5 pF / 25 ns run lasted 20 ms at the looser tolerance and passed;
it is supporting sensitivity evidence, not a longer tight-tolerance 2 pF test.
Remaining corners and integrated supplies/reset still require qualification.

Capacitance-only extraction agrees across rebuilds after component ordering
is normalized; native LVS netlists are identical. RC terminal names/order
change, and rectangular port markers shift small series resistances. The
current GDS and current extraction come from the same fresh build. Numerical
checks use that extraction rather than assuming the earlier transient repeats.
Supply storage is still an ideal lumped component and has not been laid out
or extracted. Oscillator, remaining divider and driver routing are also not
extracted. A passing nominal receiver simulation does not validate the complete
physical controller.

DRC/LVS do not establish electrical compliance or fabrication readiness. No
full-controller DRC/LVS, density/fill/antenna, ESD, latch-up, extracted-passive
corner, mismatch or foundry signoff has been performed. The behavioral system's
2 pF/estimated-driver assumptions are retained as the earlier experiment;
the tolerance-qualified macro experiment has not replaced its clock lookup or bending results.

## Contributions and next stage

The new contributions are a documented transistor actuator interface, independent
SPICE electrode-limit tests, a scripted PDK bias layout, a verified GDS interface,
and a physical/electrical regression that exposed a supply-storage failure.
Published topology and PV data remain attributed in `references.md`; SKY130,
Magic, Netgen and ngspice retain their upstream licenses and attribution.
Next: qualify clock reception across corners and redesign the brownout/reference,
integrate clock/divider/driver supplies,
then lay out the oscillator and drivers and assemble the digital macro. Recheck
power, startup and loading after each extraction. No publication or submission
has been performed.

Official sources checked 2026-10-27:
[Magic extraction](https://www.opencircuitdesign.com/magic/howto.html),
[Magic technology/port representation](https://www.opencircuitdesign.com/magic/techref/maint2.html),
[Netgen](https://github.com/RTimothyEdwards/netgen),
[SKY130 device documentation](https://github.com/google/skywater-pdk/tree/main/docs/rules/device-details).
