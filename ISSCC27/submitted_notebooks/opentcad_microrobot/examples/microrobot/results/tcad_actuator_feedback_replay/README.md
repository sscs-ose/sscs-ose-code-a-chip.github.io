# Reduced actuator-feedback logic-rail replay

**Reviewed and accepted as failed reduced actuator-feedback diagnostic evidence; global abort prevents model-specific completion claims and end-to-end validation remains blocked.**

The sole **250 µs /25 ns** request aborts globally at **44.1052575471 µs**, saving **11251 ×55 finite values**. Ngspice returns zero but reports `TRAN: Timestep too small; time =4.41053e-05, timestep =3.125e-20: trouble with node "vp_stable_r#branch"`, then aborts. The reported stable-return equation is not a physical/numerical cause, and does not establish that the RC copy would complete independently. No rescue or second transient ran.

Both copies end with replayed `logic` **0.552416305 V**, actuator span about **1.751815133 V** and physical midpoint about **0.875894341 V**. Drivers remain held low and PV voltages remain within the characterized domain. The powered-clamp check remains **null/untested**, since logic never reaches its 1 V qualification threshold. All eta/coverage/current comparisons pass only over the saved prefix; completion fails, so they do not qualify startup or either model independently.

Prefix peak terminal-current KCL residuals are **0.1945 pA RC /0.2162 pA stable**, with local terminal-versus-solution discrepancies **0.1629 /0.1854 pA** and integrated electrode charge residuals at most **2.65×10⁻²⁰ C**. These remain numerical precision observations, not exact conservation. Prefix PV delivery is about **9.0687×10⁻¹³ J** per copy; external replayed-logic delivery is **6.1956×10⁻¹⁶ J**. The actuator storage change is about **7.6721×10⁻¹³ J**, and the measured actuator supply residual is about **3.14×10⁻¹⁸ J**. External logic energy prevents full-TCAD power validation.

Effective settings are confirmed from the native post-analysis option block: **GEAR2, RELTOL10⁻⁶, ABSTOL10⁻¹⁵ A, CHGTOL10⁻¹⁴ C, TRTOL7, VNTOL1 µV**, Sparse1.3. The pre-analysis option display shows old defaults, not queued options. The effective block is extracted from ngspice.log because native option output bypassed the requested file redirection. No tolerance was changed. Only the completed passive benchmark's logic rail is replayed from all adaptive samples. Actual electrode metals, actuator rails and Pt midpoint remain solved feedback nodes. External logic-rail power is explicitly measured, so this is not a full TCAD-powered controller test.

Exact inclusion list is configuration.json: two DD actuator half-stacks and 1 pF storage each, native transistor drivers, passive phase/ready clamps, three electrode interfaces and 10/10/1 MΩ solution paths. Shared driver macros and retained lines are copied from the frozen deck with node/instance namespaces only. Clock, DFF, proxy/counter and supervisor dynamics and logicPV/storage are removed. RC/stable copies differ only in electrode adsorption branch. Default operating point, no seeds/UIC, unchanged Gear2/reltol/abstol and 25 ns maximum step.

Before execution, numerical_conventions.md records installed charge/truncation defaults and branch-current conventions. Effective post-initialization options are in options_effective.txt. The pre-analysis list is not proof queued options are applied. ABSTOL alone cannot explain or bound prior pA discrepancies.

Coverage/eta/current comparisons retain prior replay floors/limits without posthoc changes. Native current precision, signed electrode work, finite-PV/storage/driver-port balance and externally supplied logic work remain separate. Incomplete traces support prefix checks only. A global two-copy abort cannot identify one copy as its cause without additional evidence; no released actuation, bending or unique simulator-defect claim follows.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_actuator_feedback_replay
```

Waveform-bearing logic include and raw output remain local; compact deck template, log, options, exact provenance and source are retained. No rescue, fine, source/DD/layout rerun, publication, submission, push or fabrication occurred.

One focused retained-line/namespacing assembly test passes in 1.36 s; Ruff passes. The exact inclusion list, source hashes, local logic-history hash and compact deck prove retained DD/driver/electrode/storage/ramp settings; no electrode metal or midpoint is replayed. The configuration-only query made no analysis call; one version query and one no-analysis options query are separately counted from the sole two-copy transient. Waveform data remain local.

Review recommends unchanged independent RC-only and stable-only versions to separate shared global-step effects before any tolerance tuning. They were not executed here.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_actuator_feedback_replay.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_actuator_feedback_replay.py tests/integration/test_tcad_actuator_feedback_replay.py
```
