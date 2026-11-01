# Held-input actuator-network startup add-back

**Reviewed and accepted as failed actuator-network add-back evidence; complete startup and actuator operation remain unvalidated.**

The sole 250 µs / 25 ns request aborts at **81.534263 µs**. The saved prefix has **4588 × 48 finite values**. Ngspice returns zero but reports `TRAN: Timestep too small; time = 8.15343e-05, timestep = 3.125e-20: trouble with node "vsupervisor_driver#branch"`, then aborts. This equation does not establish the cause. No fine or rescue run followed.

Final logic / actuator span / midpoint are **1.577750 / 1.821612 / 0.910804 V**; reset is **−1.342202 mV**, and driver-ready is **+0.466810 µV**. All numerical reset/driver-ready/phase controls stay zero. Physical reset spans **−1.390550 to +0.376632 mV**, driver-ready **−125.205 to +54.043 µV**, and each phase pin **−155.486 to +5.993 µV**. The maximum per-cell voltage is **0.455404 V**, inside the DD domain. Global electrode-to-midpoint error is **5.733096 mV**; the powered reset-clamp check peaks at **1.199918 µV**. These observations cover the prefix only.

Prefix PV energy is **5.163848 pJ**, with **3.318861 pJ** supply-storage increase and supply accounting residual **0.000496 pJ**. Double-layer change, signed adsorption work, Faradaic/solution losses and terminal-current/KCL residuals are separated in metrics.json. These checks do not validate complete startup or released power. No phase, gait, bending or autonomous behavior is tested. The reduced logic-only bench passed, while this altered add-back fails; multiple coupling/loading changes remain, so the comparison does not uniquely isolate a cause. Reset, driver-ready and both phase commands are held low through the existing measured rail-powered 10 kΩ bridges. Signal-only zero controls supply no analog gate charge. Event counter and supervisor-state circuitry are absent. No fine, rescue, DC, DD or layout run is added.

The passing logic-isolation core is retained: identical four-series TCAD logic source, compact extracted clock, native resettable DFF/feedback, switched-capacitor proxy, ramp, 2 pF storage and solver. This add-back restores both two-series TCAD actuator half-stacks, 1 pF storage per half, physical midpoint, transistor drivers and full working/Pt-return electrode and solution network. All eight conceptual cells retain 1080 µm² each. The conditional dark/light superposition and characterized domain are unchanged; exact source expressions match the previously verified deck.

Metrics cover finite completion, DD/rail limits, held-input/reset clamps and signed electrical energy/KCL bookkeeping. Incomplete traces support prefix checks only. The engineering limits are not foundry or electrochemical safety specifications. This diagnostic provides no released-controller, phase/gait, bending or autonomous-operation validation. Any reported trouble equation is not an established root cause; passing this altered bench also would not uniquely isolate the previous cause.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_actuator_startup
```

Fresh destinations are required. Exact deck/log/diff, executed runner and metrics are retained; raw data remain local. Prior accepted evidence is unchanged. No publication, submission, push or fabrication occurred.

Two focused simulator-free assembly tests pass in 1.26 s; Ruff passes. They verify all three DD source expressions, restored physical network, fixed signal controls, measured rail-powered bridges and absent event/supervisor circuitry. No full suite or extra simulation was run. Exact clock/source comparisons and source-dependency hashes are retained in verification.json and configuration.json.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_actuator_startup.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_actuator_startup.py tests/integration/test_tcad_actuator_startup.py
```

An offline equivalence audit of the executed deck confirms that all fixed-zero controls make the reset, driver-ready and both phase high-side behavioral current branches identically zero. Each corresponding low-side expression becomes exactly `I = V(output)/10000`, mathematically a 10 kΩ resistor from the output to ground. Thus a possible next numerical diagnostic could omit those open high-side branches and their now-unloaded rail-current probes and replace the low branches with explicit 10 kΩ resistors, without changing the intended held-input terminal relation. This is an algebraic observation only: changing auxiliary source/probe equations can change numerical conditioning, and matching physical terminal equations does not guarantee matching simulator trajectories. It does not identify the abort cause. Gate-coupling current and resistor dissipation would still exist. No deck was edited and no simulation was run for this audit.
