# TCAD-powered controller functional experiment

**Astra reviewed and accepted as failed integration evidence; no functional TCAD-powered controller acceptance.** The sole nominal request was 8 ms at a 25 ns maximum step. Ngspice returned zero but reported `TRAN: Timestep too small; time = 8.75049e-05, timestep = 3.125e-20`, with trouble equation `vreturn#branch`, and aborted. That equation is not an established physical or numerical root cause. The saved **5482 × 50 finite values stop at 87.504897 µs**, before the 101 µs optical ramp finishes. There was no fine run or rescue transient.

Final logic / actuator / midpoint are **1.590416 / 1.613524 / 0.806751 V**. A separate released-logic gate also fails: with actuator ≥0.5 V and driver-ready >actuator/2, a sampled early interval of **20.427937–21.302937 µs** has logic only **0.074000–0.084347 V**. There is no valid sustained released phase sequence, three complete cycles, both electrode polarities or phase-correlated actuator response. `prefix_observations.json` records all rail/reset bounds.

The passing energy, clamp and KCL checks apply only to this incomplete prefix. Prefix PV delivery is **11.283863 pJ**, storage increase **3.180288 pJ**, and signed measured load-port energy **8.103378 pJ**; residual is **0.000197 pJ (0.001747%)**. This bookkeeping does not establish complete startup, steady load power or autonomous operation. Coverage remains essentially 0.5, and the tiny plotted curvature follows the uncalibrated assumed relaxation only.

The run connects the fresh R=0.3, 29-point drift-diffusion table to the native extracted compact clock, first resettable DFF, existing current-limited reset converter, brownout candidate, qualified LVT receiver and two transistor drivers. Two XSPICE bits make a changed **/8 real-time functional test**. The final /8192 divider and extracted RTL power remain untested. The remaining digital power uses a measured switched PDK-capacitor proxy. Functional phase bridges transfer charge from the measured logic rail through 10 kΩ conductances; signal-only event controls provide no analog output energy.

This is a new **8640 µm²** conceptual PV design: four logic cells and two series cells per actuator half, each 1080 µm². Common lower rail is physical CMOS ground and the physical midpoint connects the Pt return. Storage is 2 pF logic and 1 pF per half. Dark/light superposition is conditional as recorded in configuration.json; no empirical PV fit is used. SPICE PWL endpoint behavior is never accepted outside the characterized per-cell domain: the full saved transient must pass the bounded-domain gate. Native DC verifies every knot and midpoint at zero, half and full reference illumination for both series counts before any transient.

Electrodes retain 40 pF double layer, 260 pC adsorption scale, 20 ms kinetics and 10 GΩ Faradaic resistance; Pt return uses 400 pF, 2600 pC and 1 GΩ. Solution resistances are 10/10/1 MΩ. Electrical metrics separately retain double-layer energy change, signed adsorption work and resistive losses. Current KCL and source/storage/load balance use all adaptive samples. Logic limits 1.4–1.94 V, 50 mV reset clamp and 100 mV rail excursion are engineering bench limits, not foundry or electrochemical safety specifications.

Coverage drives an assumed 50 ms relaxation and 10⁵ m⁻¹ curvature span, with no force, contact or walking model. Eight milliseconds is a short-window response, not mechanical steady state or a calibrated actuator reproduction. Raw waveforms remain local; plots are decimated only for display. Exit status alone is not acceptance.

Reproduce from repository root with fresh destinations:

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_controller
```

The runner allows exactly one nominal 8 ms / 25 ns transient and only permits one 12.5 ns repeat if completion and every nominal gate pass. Failed nominal execution stops this branch; no automatic rescue. See execution_counts.json, metrics.json, exact decks/logs, source_validation.json, configuration.json and sha256.json. No DD/layout rerun, publication, submission, push or fabrication was performed.

Native DC source validation ran twice: the initial 8-digit `wrdata` check failed an absolute tolerance at the largest forward-current endpoint due to printed precision; the retained 17-digit repeat passes all 57 voltages at both series counts and all three irradiances, worst absolute error **3.45 fA**. No transient was run before that pass. Seven simulator-free focused tests pass; Ruff passes. The original executed runner is preserved. Its UTC field was written after subprocess return and mislabeled `started_UTC`; evidence labels now read `completed_UTC` with provenance, and the final module fixes this label. No exact process start timestamp is inferred.

Saved-data audit, with no simulator invocation:

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python examples/microrobot/results/tcad_controller/audit_saved.py
```

Use `verification.json` for checks and `prefix_observations.json` for incomplete-waveform scope. Initial DC artifacts are retained with `initial_precision8_` names. The runner refuses nonfresh destinations; `--resume-preflight` was used only after the first DC failure and before any transient. This branch is stopped.
