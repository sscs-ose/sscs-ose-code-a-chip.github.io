# TCAD-powered mixed-abstraction system demo

**All declared system-model checks pass.** This executable six-second demo couples archived actual drift-diffusion PV tables to the validated native **schematic** clock/current lookup, a behavioral /8192 controller and finite-resistance driver, nonlinear electrode interfaces, finite Pt return/electrolyte, and assumed bending relaxation. It is not a successful full transistor transient, measured-PV calibration, large-signal electrochemical qualification or walking simulation. Extracted-clock and native MOS-driver evidence remain separate.

| Check | Executed result |
|---|---:|
| Nominal / half-step / dark duration |0–6 s, all finite and strictly increasing |
| Saved rows |6001 /12001 /6001 |
| Startup / darkness shutdown / recovery |0.051 /3.001 /3.401 s |
| Enabled logic supply |1.713649–1.816675 V |
| Commanded phase frequency |1.964178 Hz |
| B lag behind A |0.250760 cycles |
| Predicted hinge angle peak-to-peak |0.977430 rad |
| Recovered predicted angle peak-to-peak |0.977653 rad |
| Electrical energy residual |0.143794% |
| Electrolyte KCL residual |1.97×10⁻²³ A |
| Largest principal half-step change |1.5785% (driver energy/cycle) |
| All-dark control |no supply, enable, phase or bending |

Four logic cells and two series cells per actuator half each use 1080 µm², total 8640 µm². The 50 pF logic/200 pF per-half capacitors and 100 MΩ driver are explicit design choices; capacitor layout/area and native driver operating costs are not qualified. The native schematic lookup uses only passing TT 26.85°C points 1.6–1.9 V; below that range its startup current is an approximation. The ideal supervisory thresholds 1.65/1.60 V and phase accumulator do not qualify native POR/divider integration. Remaining digital 20 fF switched capacitance/0.2 nA leakage is assumed.

The original nonlinear adsorption, separate Cdl/Faradaic branches, finite Pt return and solution paths remain in system.py. Coverage stays bounded. Predicted bending uses an assumed 50 ms relaxation, 10⁵ m⁻¹ curvature span and 10 µm hinge; the near 1 rad excursion follows those uncalibrated assumptions, not a measured robot. No contact, force or locomotion model is present. The unknown electrochemical reference offset/safe window and native coupled transient failures remain unresolved.

Inputs are results/pv.json actual dark/light DD (linear irradiance superposition), results/clock_final/summary.json and the matching canonical schematic clock source. No fitted published terminal_table, digitization/CSV fit, SPICE, DD or layout computation is invoked by the demo.

```python
from examples.microrobot.tcad_demo import run
report = run("fresh/output/directory", dt_s=0.001, duration_s=6.0)
assert report["all_gates_pass"]
```

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_demo --output fresh/output/directory
```

Optional --pv-file / pv_path supplies an equivalent dark/light DD archive. The output directory must be fresh. Outputs are summary.json, system.png and waveforms.csv.gz. Summary records actual completion and every numerical gate; the waveform is the nominal run. The accepted three-case batch took 3.07 s locally. Eight focused/existing system regression tests and Ruff pass; the plot was visually inspected. No full test suite ran.

The first three calculations completed before a NumPy-boolean serialization error at report writing; their nominal waveform/plot were preserved locally. After scalar serialization was corrected, the three cases were rerun unchanged for the accepted report. execution_history.json records six system calculations total, zero SPICE/DD/layout runs. No numerical parameter rescue or timestep sweep occurred. Existing Parameters defaults remain unchanged; the added actuator series count defaults to 1. Initial coverage output is now correctly 0.5 and return/KCL diagnostics are additive.
