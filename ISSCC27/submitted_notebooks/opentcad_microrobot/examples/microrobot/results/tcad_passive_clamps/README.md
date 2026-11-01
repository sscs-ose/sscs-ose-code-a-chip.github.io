# Passive-equivalent held-input startup

**Reviewed and accepted as failed passive-equivalent startup diagnostic evidence; full startup and end-to-end operation remain unvalidated.**

The sole 250 µs / 25 ns request aborts at **151.540937 µs**. The trace contains **8406 × 45 finite values**. Ngspice returns zero but reports `TRAN: Timestep too small; time = 0.000151541, timestep = 3.125e-20: trouble with node "vreturn#branch"`, then aborts. This equation is not an established cause. The longer saved prefix does not establish complete startup or explain the changed failure time.

Final logic / actuator span / midpoint are **1.636781 / 1.842303 / 0.921151 V**; reset is **+1.063873 mV**, driver-ready **−0.725635 µV**. Commands remain fixed zero. Reset ranges **−2.439938 to +1.063873 mV**, driver-ready **−125.363 to +54.041 µV**, and each physical phase pin **−257.658 to +5.998 µV**. Maximum per-cell DD voltage is **0.460576 V**. Global metal-to-midpoint error is **5.733096 mV**, with the powered reset-clamp check **1.195538 µV**. Every passing clamp/domain/energy/KCL check applies only to the saved prefix.

Prefix PV energy is **9.634903 pJ**, supply-storage increase **3.527573 pJ**, supply-balance residual **0.002192 pJ**. Explicit resistor dissipation is **1.527536×10⁻¹⁹ J** reset, **3.410912×10⁻¹⁸ J** ready and **4.303698×10⁻²⁰ J** per phase. These are component losses, not missing ideal-source deliveries or additional total-load terms. No full startup, released controller, phase or bending validation follows. No fine, rescue, DC, DD or layout run was added.

The frozen actuator add-back deck changes only four fixed-zero input bridges: their high-side current branches, which are identically open, and three unused high-side rail probes are removed; each low branch becomes an explicit 10 kΩ resistor to ground. Configuration.json records the equivalence per branch and deck.diff records every edit. Existing numerical zero controls remain signal-only instrumentation. All TCAD source expressions, extracted clock, native DFF/feedback, proxy, transistor drivers, working/Pt-return electrodes, storage, ramp and solver remain unchanged.

Removed probe deliveries are expected algebraic zeros, not measured native power removals. The saved-data audit supplies these zeros only as compatibility inputs, removes them from measured-load results, and labels them separately. Each clamp resistor's V²/R dissipation is retained as component bookkeeping; it is already supplied through measured native circuit ports and is not counted again in total load energy. All power, clamp and KCL checks on an incomplete trace are prefix-only.

Equivalent held-input terminal equations may have different numerical conditioning; a changed outcome does not identify a unique cause. Completion would establish only this held-input startup diagnostic, with no released phase, bending or autonomous operation. Raw waveforms stay local. Previous frozen evidence and defaults are unchanged.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_passive_clamps
```

The runner refuses existing destinations. No submission, publication, push or fabrication occurred.

The focused static transformation test passes in 1.29 s; it reverses the four resistor substitutions and proves the rest of the deck differs only by the intended open branches/probes and their output-vector removals. Ruff passes. Source expressions and compact clock are unchanged. No full-suite test, DC/DD/layout, fine or rescue simulation was run.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_passive_clamps.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_passive_clamps.py tests/integration/test_tcad_passive_clamps.py
```
