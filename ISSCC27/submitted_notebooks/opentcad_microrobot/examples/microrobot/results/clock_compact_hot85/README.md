# One 85 °C electronics sensitivity with fitted PV fixed at 26.85 °C

**Reviewed and accepted as hot-electronics sensitivity evidence with fitted PV fixed at 26.85 °C; no electrical design acceptance.** One new compact-clock 4 ms / 12.5 ns run completed at global electronics temperature **85 °C**, with all three fitted PV diodes explicitly held at **26.85 °C**. The unchanged clock-swing/divider bench criteria pass, with seven steady Q rises and exactly two clock rises between every successive sustained Q rise. No new frequency or power threshold was imposed.

| Observable, exact 2.4–4 ms window | Nominal electronics 26.85 °C | Electronics 85 °C, PV 26.85 °C | Hot / nominal |
|---|---:|---:|---:|
| Clock frequency, Hz | 5954.900207 | 8467.250089 | 1.421896 |
| Analog clock power, nW | 43.672419 | 55.599421 | 1.273101 |
| First FF + feedback power, nW | 2.583378 | 3.491877 | 1.351671 |
| Whole clock + first FF power, nW | 46.255797 | 59.091298 | 1.277490 |
| Time-averaged rail, V | 1.743216874 | 1.633155845 | 0.936863 |
| Rail minimum, V | 1.51673804 | 1.44502527 | 0.952719 |
| Rail maximum, V | 1.82072471 | 1.73647009 | 0.953725 |

Power and rail means use the accepted full-data audit: trapezoidal integration over exactly 2.4–4 ms, linear interpolation at boundaries, and power from vdd × measured current. Frequency uses crossings relative to instantaneous vdd/2. Separate internal bias-reference power is unavailable. The finite PV rail changes with circuit current; the frequency and power changes are sensitivity observations, without additive causal attribution.

| Existing behavior checks | Nominal | Hot electronics |
|---|---:|---:|
| Steady clock rises / Q rises / Q falls | 9 / 5 / 4 | 13 / 7 / 6 |
| Sustained >=0.4 ms Q/clock frequency ratio | 0.499999999015 | 0.499995989037 |
| Clock rises between every successive sustained Q rise | 2 | 2 |
| Existing full-swing / divider bench criterion | true | true |

The unchanged bench requires at least five steady clock rises and three steady Q rises, clock swing below 0.1 × rail and above 0.9 × rail, and divide-by-two frequency within its existing tolerance. Hot clock minimum/maximum are −0.000184513 / 1.7364702 V. All crossing arrays and the original sample-index bench calculation remain in `metrics.json`. Passing these bench criteria is not electrical design acceptance or a 13 kHz requirement.

The new full transient has **332247 rows and eight finite columns**, starts at zero, has nondecreasing time and reaches exactly **0.004 s**. No abort, `doAnalyses:` or timestep-too-small marker occurs. The single simulator invocation returned **zero in 161.877564 s**, within the unchanged **180 s** timeout. The log confirms global `TEMP = 85`; it contains no unknown or ignored temperature-parameter warning. The known PDK multiplier hierarchy warning remains. Completion is verified from full data and logs, independently of return status.

The accepted nominal 12.5 ns deck and its full transient were reused. Exactly **four deck lines** changed: `.temp 26.85` became `.temp 85`, and `TEMP=26.85` was appended to each of Dp1/Dp2/Dp3. `deck.diff` contains the complete diff, with both decks saved. Explicit diode instance temperature is required to hold the fitted PV thermal voltage fixed: model `EG=0 XTI=0` alone does not freeze its full temperature response. The fitted model, including `TNOM=26.85`, remains unchanged.

All TT models, compact extracted RC, illumination, storage, load, solver and startup settings are identical: three fitted cells at assumed 150 µm²/cell; 1 µs dark then 100 µs optical ramp; 2 pF storage; 2 fF output load; real SKY130 DFF and feedback; Gear2, reltol 1e-6, abstol 1e-15; zero-supply operating point without UIC or seeded voltages. The `nominal_reference_assumptions` field in metrics reproduces the nominal base setup; `temperature_policy` specifies the hot intervention. No physical evidence was regenerated.

Before simulation, the runner verified all accepted nominal input/output hashes, the top-level PDK library hash, unchanged receiver/init files, and exact reversal of the four-line substitution. `input_checks.json` preserves the UTC pre-execution checkpoint and frozen runner/helper hashes. `execution.json`, logs, exact deck diff, full-data hashes and compact metrics retain the evidence; `sha256.json` covers exported files except itself and Python caches. Raw `clock.dat` remains local under `local_runs/clock_layout/compact_x_v1/hot85_fixed_pv26p85_12p5ns/`.

Executed from the repository root:

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -u examples/microrobot/results/clock_compact_hot85/run_hot85.py
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python examples/microrobot/results/clock_compact_hot85/audit_saved.py
```

The first command created a fresh directory and invoked ngspice exactly once. Its simulator completed, then its offline audit stopped on a JSON bookkeeping assertion: the four changed-line tuples had become arrays when serialized. The minimal `audit_saved.py` wrapper normalizes that comparison through JSON and reuses the unchanged full-data audit; it also labels the inherited nominal assumptions explicitly. It invokes no simulator and preserves the frozen executed runner and input checkpoint. Use this wrapper for saved-run audits; the original runner's direct audit-only path retains the same tuple/array assertion. There was no simulator rescue, retry or refinement.

This is **one hot-electronics sensitivity with fitted PV fixed at 26.85 °C**. It is not whole-device thermal calibration, hot timestep convergence, PVT/mismatch qualification or resolution of prior coupled-controller hot failures. No coupled controller was simulated, and no full test suite or additional run was performed. No raw transient or local PDF is exported; no submission, publication, push or fabrication was initiated.
