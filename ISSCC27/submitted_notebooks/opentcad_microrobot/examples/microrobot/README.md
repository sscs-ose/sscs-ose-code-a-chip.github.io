# Microrobot controller: device foundation and electrical validation

An openly licensed, paper-inspired experiment extending OpenTCAD while
keeping robot-specific physics and workflows here. This is a functional
reimplementation project; it does not reproduce X-FAB XT018 fabrication,
layout or performance. See [evidence and missing material](references.md)
before interpreting any plot. No submission, publication, push or fabrication
is performed by the scripts.

## Submission status and portability

The primary deliverable is the [executed notebook](../../submission.ipynb);
[submission.ipynb](submission.ipynb) is its unexecuted export source. It is an executable
end-to-end **mixed-abstraction model with separately validated transistor
blocks**. Actual drift-diffusion PV tables supply a characterized schematic
clock/first-DFF lookup, behavioral divider/reset and finite-resistance drivers,
nonlinear electrochemistry with a finite Pt return, and predicted bending.
The notebook identifies archived inputs and freshly executed computations, embeds
the actual compact clock layout and detailed plots/tables, and includes expandable
complete numerical records with links to bundled machine-readable artifacts.

**The fully transistor-coupled controller startup experiment failed and remains
unresolved.** This package does not claim an accepted autonomous transistor
controller, a calibrated physical robot, walking, or a complete controller
layout. TCAD PV/process parameters are conceptual; actuator and mechanics
parameters are assumptions. See [submission scope and limitations](SUBMISSION_STATUS.md).

Compact-clock DRC/LVS/PEX, pre/post-layout comparison, nominal timestep
consistency and one hot-electronics sensitivity are separate evidence. They
qualify the stated clock experiment only. They do not resolve coupled startup.

Team: **Abhineet Agarwal, IIT Bombay**; IEEE member: **No**; SSCS member: **No**.
SPDX-License-Identifier: Apache-2.0. See [attribution/IP](ATTRIBUTION.md).

Use [SETUP.md](SETUP.md) and `tools/build_microrobot_submission.py` for a
self-contained `ISSCC27/submitted_notebooks/opentcad_microrobot/` folder.
Only curated evidence is exported; local reference PDFs, raw SPICE transients
and supplied measurement CSVs with unverified redistribution rights are excluded.
Python 3.12 dependencies are pinned. Colab is untested. New calculations write
to fresh `local_runs/`; exported reference evidence is checked for changes.
The scripts do not submit, publish, push or initiate fabrication.

## Run

From the repository root, in a Python environment matching
`requirements-notebook.txt` (Python 3.12 target; see SETUP.md for native prerequisites):

```sh
python -m pip install -r examples/microrobot/requirements-notebook.txt
python -m examples.microrobot.run
python -m examples.microrobot.run --spice  # optional installed ngspice + SKY130
python -m examples.microrobot.digitize     # re-fit committed, attributed S2E numerical traces
python -m examples.microrobot.published    # use archived clock characterization
python -m examples.microrobot.published --spice  # rerun the current clock/corner/startup benches
python -m pytest tests/device/test_optical.py tests/device/test_compact_pv.py \
  tests/integration/test_microrobot.py tests/integration/test_electrode_spice.py \
  tests/integration/test_layout_edge_audit.py tests/integration/test_phase_generator.py -ra
```

`microrobot.ipynb` explains and reruns the numerical experiment. It can execute
without ngspice and also runs the circuit experiment when models/tools are
installed. `run.py` requires no network access.
For an interactive Jupyter session, select this virtual environment's kernel
or register it with `python -m ipykernel install --user --name opentcad-microrobot`.
Results include JSON provenance/metrics, CSV, mesh and timestep checks, PV
and coupled transient plots, and optional ngspice decks, logs and PVT results.
Full SPICE `.dat` waveforms and new runs are ignored by git. Tracked plotting
previews are losslessly compressed `.csv.gz`; they are distinct from full
waveforms. CLI defaults and notebooks write to `local_runs/`, preserving the
reference archive.

## Executed results

Historical M3 full-suite execution passed **174 tests** with ngspice and Icarus
installed (one pre-existing Auger diagnostic warning). Without those tools four
tests skip in that checkout; M2 logs describe an earlier suite. Current test
counts and skip reasons come from `pytest -ra`, not this historical count.
The archived macOS finest conceptual PV mesh gives approximately
0.1355 A/W responsivity and 0.461 V open-circuit voltage at 1000 W/m².
The archived medium-to-fine Isc change is about 0.37%; platform reruns can
differ (an independent run reported about 0.40%). Current notebook values are
computed from run JSON and checked against declared tolerances; the largest terminal-current
imbalance among the DD sweeps is about 3.1e-12 relative. The system gives
2.24 Hz behavioral outputs with measured phase lag 0.251 cycles. Halving
its timestep changes bending range by 0.051%, driver energy by 0.95%
and adsorption electrical work by 1.57%; its electrical energy-balance
residual is 0.127%. These are numerical checks, not measured robot agreement.

The SKY130 RC ring runs at 23.54 kHz, consuming 1.443 uW at TT/1.6 V/27 C.
SS/FF and additional voltage/temperature experiments also oscillated.
The proposed four-cell logic array has a theoretical maximum power of only
about 29 nW in this conceptual DD model. **Reject this ring for that PV
allocation**; it exceeds even the array's maximum-power budget by about
50 times. The behavioral controller's assumed loads do not establish that
a transistor implementation will meet them. See generated
`results/spice_budget.json`, `results/validation.json` and the notebook.

### Published-data and low-power-clock milestone

The 2022 supplement is available locally and its S2E dark/illuminated curves
have been digitized. The committed CSV retains raster coordinates; calibration,
PDF checksum and pixel-sensitivity assumptions are in `data/`. Re-fitting
requires no paper download. See [extraction method](data/README.md).

The reduced ideal-diode fit gives approximately 145 nA photocurrent, 1.245 V
pair Voc and 147 nW pair maximum power. These are effective terminal-fit
parameters at an assumed 300 K, not unique TCAD/process calibration. The
48-trial pixel sensitivity ranges are not confidence intervals. Current and
voltage digitization scales are included; the dark trace's small raster
offset is retained explicitly in residuals.

`circuits/starved_clock.spice` is a new functional SKY130 candidate: a
supply-dependent diode-stack bias, five current-starved inverter stages,
PDK MIM capacitors and two output buffers. It is not the paper's compensated
PTAT/relaxation topology. At 1.8 V/26.85 C/TT, including a real SKY130 DFF
and feedback inverter, it runs near 14.6 kHz at 55 nW. The first DFF divides
by two. Startup uses a zero-supply operating point and a supply/optical ramp;
there is no UIC, seeded node voltage or ideal startup current pulse.

With three scaled cell proxies (150 um² each) and a chosen 2 pF supply
capacitor, direct SPICE settles near 1.77 V, 13.0 kHz and 43 nW. This
assumes the large measured PV's current density applies to the proposed
logic cells; the paper does not establish that scaling. Electrical clocks
also run in TT/SS/FF/SF/FS, temperature and supply experiments. Some ideal
1.8 V cases exceed the nominal one-sun array's 61 nW maximum. Finite-PV
SF/FS tests settle at different voltages/frequencies. An oscillation pass
and a power-budget pass are separate report fields.

The updated system uses bounded TT voltage/frequency/current lookups with
a withheld-voltage check. Its nominal two outputs run near 1.53 Hz and a
quarter-cycle phase lag. Bias-reference, oscillator/buffer, first-DFF,
remaining-logic estimate, driver and electrochemical energies are separate.
The quasistatic clock proxy differs from direct PV-powered SPICE by about
2% in frequency and 7% in power; it omits supply ripple. Direct SPICE is
the electrical-startup reference. Drivers and mechanics remain reduced models.

`rtl/phase_generator.v` implements a configurable-at-build-time divider
(default /8192) and two phases. Icarus checks period, duty, phase and
asynchronous reset/restart. Yosys produced a generic 13-flop, 50-cell
netlist. This is not PDK placement/routing or a timing/power signoff.
The tested loaded process corners imply substantial gait-frequency spread;
frequency trim and temperature compensation remain design work.

### Transistor drivers and first bias layout

The next milestone is executed: two transistor drivers pass nine preliminary
corner/sensitivity checks, and the bias macro passes native and GDS-round-trip
DRC/LVS. Extraction exposed missed divider edges with 2 pF supply storage;
a fresh extraction exposed numerical sensitivity. Tightening ngspice tolerance
qualifies the original 2 pF nominal receiver at two timesteps; a storage increase
is not established as necessary. Full post-layout corners remain pending. The brownout candidate
fails the required corner envelope and remains a development circuit.
See [physical/electrical results and reproduction](PHYSICAL_VALIDATION.md) and
`electrical_layout.ipynb` for the actual artifacts and limitations. This is a
bias macro layout, not a completed controller. The earlier notebook and reduced
system results below retain their original assumptions.

## Feasibility and repository audit

The initial audit predates the repository AGENTS.md workflow instructions now in force. README,
PHASES, Strategy, geometry/MeshField, solver/physics, material data,
process/doping, examples and numerical tests were inspected. Existing code
already implements analytic Gaussian implant profiles and an intrinsic
Fick-diffusion anneal through Cartesian resampling/Gaussian filtering; the
roadmap's blanket “planned” description is stale. This is not a validated
concentration-dependent process simulator or a foundry transistor model.
The baseline device/geometry/material/bridge suite passed 63 tests. The full
suite originally failed collection without ViennaLS; ViennaLS 5.9.0 was
installed into the repository virtual environment to execute it.

Reusable additions are `BeerLambert`, the prescribed generation-field
contract, explicit 2D current conversion and a terminal-current reader.
Illumination exposed an existing shared-sign recombination-source defect:
the hole source and hole time charge now have the correct opposite sign.
Analytical and DD regressions are in `tests/device/test_optical.py`; the
small general example is `examples/07_photovoltaic.py`. A reusable ideal-diode
terminal fit/MPP/SPICE-export module and independent SPICE round-trip tests
are documented in [compact PV models](../../docs/photovoltaic_compact.md),
with a small `examples/08_pv_compact.py` example. See also
[physics/units documentation](../../docs/optical_generation.md).
No new process simulator, plugin framework, or generic mechanics package
was needed. Surface recombination and calibrated optical spectra remain
the next reusable device-physics needs if measurement data support them.

## Electrical topology: published connections and my adaptation

The separate IC and actuator PV pairs and exposed Pt solution return must
be retained. The supplement, obtained locally on 2026-10-27, confirms
the common lower rail and actuator midpoint/switch arrangement in Fig. S1B.
The published-data experiment adapts the logic pair to three cells:

```text
VDDL ---- 3 series conceptual PV cells ---- VSS   (my SKY130 supply adaptation)

VACT ---- PV+ ---- VMID ---- PV- ---- VSS        (published actuator topology)
                    |
               exposed Pt return interface
                    |
              finite electrolyte network
                    |
        SEA A interface    SEA B interface
             |                  |
           LEGA               LEGB
             +-- switches to VACT or VSS --+
```

Published S2E values are 540 um² per large PV, approximately 1.24 V Voc
for the series pair and 150 nA Isc at 1000 W/m². The first experiment's
500 um² cells and conceptual DD curves remain separate design choices.
The first experiment used four logic cells because its uncalibrated cells
had lower Voc. Applying the published cell fit to four cells would exceed
the controller voltage range; that configuration is rejected. Three cells
also need an overvoltage solution for stronger illumination: the unloaded
stack exceeds 1.95 V at 5000 W/m². Current exploration is 500–2000 W/m².
The reported-data sources are the paper and supplement; the broken Zenodo
archive is optional and does not block the extracted-figure comparisons.

Actuator and electrolyte voltages use VMID metal as coordinate zero;
`logic_V` is the separate supply span VDDL-VSS. The physical VDDL potential
relative to VMID is therefore `logic_V - negative_magnitude_V`. A physical bulk-CMOS
implementation would use VSS as its lowest rail; VMID is not an ideal,
fixed electrolyte potential. The logic PV array has its own loading and
starts from zero. The series PVs require electrical isolation; no claim is
made that a bulk-PDK substrate diode can supply this stack. Controller
well/body ties follow the circuit's VSS/VDDL. Transistor driver level shifting and midpoint clamps now have standalone
validation; input overvoltage protection and final reset integration remain
pending. Driver switches in the earlier coupled model are behavioral.

The first two outputs are 90 degrees apart. Extra phases and optical command
reception are deferred. The first system used an assumed clock law; the
published-data system uses characterized TT clock frequency and current,
plus assumed power for the remaining divider. Its hysteretic brownout
advances the logic supply before deciding validity. A transistor brownout candidate has been tested and rejected across corners;
the complete POR remains pending. The old RC ring is retained as a
rejected comparison; it does not drive the updated model.
The behavioral brownout state connects the outputs through their resistances
to VMID. This neutral-clamp policy is my choice and would require an explicit
hardware path. The new standalone transistor-driver bench implements and
tests that path with externally supplied ready; autonomous reset is not validated.

Each SEA and the Pt return have double-layer capacitance, an adsorption
state with finite relaxation, and a Faradaic leakage resistance. Electrolyte
resistances solve the floating solution voltage by KCL. Terminal drive and
local electrode potential are separate outputs. Curvature follows adsorption
through a separate mechanical relaxation state; a hinge angle follows from
curvature times hinge length. There is no friction/locomotion solver or
validated walking-speed prediction.

## Numerical experiments and limitations

- PV: dark/light IV, 660 nm illumination, mesh spacing 0.16/0.08/0.04 um,
  shorter SRH lifetime, and direct DD at half illumination. Doping is
  analytically prescribed; optical alpha/R and geometry are choices.
- System: supply startup, a dark interval and recovery, brownout/reset,
  two phases, interface charging and bending. A halved timestep checks
  frequency, bending range and bias power. Light and leakage sweeps are
  exploratory sensitivity, not foundry process corners or mismatch.
- Energy: logic, analog bias, driver resistance, electrolyte resistance,
  Faradaic leakage, adsorption electrical work and capacitor storage are
  separate. Interface `I*eta` contains stored energy and must not be counted
  again as heat. The mechanical model has no calibrated work/efficiency.
- The initial 0.3 A/W bar is an approximate published anchor. Separate
  digitized dark/illuminated S2E traces now support the terminal comparison.
  The fit does not validate the conceptual DD structure or small logic PVs.
- Side boundaries assume passivation (zero normal flux); no surface
  recombination, optical shading or wavelength-dependent material database.
- The tabular supply uses dark/light superposition and bounded voltage
  interpolation. Half-intensity DD checks one point of its validity, not
  arbitrary illumination or temperature. DEVSIM states are steady-state;
  junction capacitance and carrier-storage transients are absent.
- Storage capacitances are explicit choices, not measured PV junction charge.
  The first model's 50/200 pF placeholders remain in its baseline; the updated
  model uses 2 pF logic and 1 pF per actuator rail. Area, routing parasitics,
  process compatibility and complete controller footprint remain unverified.
- The new clock has no temperature compensation or statistical-mismatch
  validation. Its tested MIM capacitors use typical passive parameters;
  the corner matrix is not a complete combined transistor/passive PVT signoff.
- The system uses split first-order integration. Reported timestep changes
  bound this experiment; fast electrochemical transients need finer steps.
- Absolute electrochemical offsets, fit uniqueness, mechanical stiffness,
  load geometry and Faradaic kinetics are unresolved. Linear leakage does
  not predict an electrochemical operating window or long-term degradation.

## Primary controller stack and physical layout stages

Use the locally installed SKY130A/open_pdks, ngspice 44.2, Magic 8.3.546
and KLayout 0.30.5. The model/PDK hashes and build metadata are captured by
the SPICE adapter. Netgen 1.5.325 was built locally and used for LVS.
Xschem, OpenLane and OpenROAD were not found on PATH. Icarus Verilog and Yosys are present.
Use small transistor/digital macros first; defer OpenLane until a divider's
size warrants its overhead. Do not install GLayout, ALIGN and several PDKs
before a circuit topology earns the layout effort.

SKY130 is bulk CMOS with available 1.8 V FETs, passives and supported Magic
integration. Its wells do not reproduce XT018 SOI isolation. The original
two-cell logic voltage is not automatically suitable for SKY130 library
timing. The conceptual PV and custom postprocessed Pt/Ti structures are
outside this controller-PDK manufacturability claim.

| Stage | Exit evidence |
|---|---|
| 1: implemented foundation | Optical budget, charge conservation, PV mesh checks; labelled system notebook and tool/model experiment |
| 2: electrical blocks, in progress | S2 digitization/terminal fit and low-power-clock startup/load checks executed; RTL verified; transistor actuator drivers checked separately; complete POR and optional compensated reference still pending |
| 3: circuit robustness | Process corners separately from mismatch; supported V/T, illumination, cold start, brownout, maximum electrode load, leakage and power/energy budget |
| 4: analog layout | Validated schematics first; reference/oscillator/timing/driver cells; matched orientation, symmetry and routing as required; well/substrate contacts and justified guard rings |
| 5: controller assembly | Pins VSS, VDDL, VACT, VMID, LEGA, LEGB and test clock/reset; tiny digital macro or OpenLane divider; sensitive nodes shielded from switching routes |
| 6: physical verification | Pinned PDK-supported Magic DRC; Netgen LVS against exact source netlist; extraction with PDK-supported device/parasitic treatment; archive decks, logs and tool versions |
| 7: post-layout validation | Startup, frequency/phase, supply loading, power and drive before/after extraction; iterate against explicit electrical specifications |

The bias macro now has GDS, DRC/LVS reports, RC extraction and post-layout
electrical comparisons; see [the executed physical milestone](PHYSICAL_VALIDATION.md).
Oscillator/driver/digital layout and full controller assembly remain pending.
These macro checks do not establish fabrication readiness.

Official tooling documentation checked 2026-10-26:
[SKY130 devices/rules](https://skywater-pdk.readthedocs.io/en/main/),
[open_pdks integrations](https://github.com/fossi-foundation/open-pdks),
[ngspice manuals](https://ngspice.sourceforge.io/docs.html),
[Magic](https://opencircuitdesign.com/magic/),
[OpenLane 2](https://openlane2.readthedocs.io/en/latest/).

