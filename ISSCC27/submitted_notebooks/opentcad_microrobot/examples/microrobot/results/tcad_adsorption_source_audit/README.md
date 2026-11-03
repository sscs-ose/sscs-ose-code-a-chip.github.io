# Isolated native adsorption-source DC/AC audit

**Reviewed and accepted as isolated native DC/AC source-law and derivative evidence at audited biases; coupled transient and end-to-end actuation remain unvalidated.**

All isolated native current, Jacobian, input-matrix and sign checks pass. Maximum DC-current error is **6.97×10⁻²³ A**, AC-partial error **5.29×10⁻²³ S**; input-matrix and probe/source-current KCL errors are zero in saved output. All imaginary current coefficients are zero. Absolute-plus-relative limits were declared before execution: current **10⁻²² A +10⁻¹⁰|Iref|**, partial **10⁻²⁰ S +10⁻⁸|gref|**, independent input-voltage error **10⁻¹² V**. Near-zero coefficients use the absolute floor, not relative-to-zero error.

The one ngspice 44.2 process completed in **0.1233 s**. The primitive resistor independently verifies positive metal and negative state derivatives, zero solution derivative, and the probe orientation. The stable model's tiny solution derivative is directly measured by native AC, rather than inferred from offline differentiation. One installed-ngspice process packs six biases × three exact saved models × three independent terminal excitations, with one explicit operating-point analysis and one 1 Hz AC analysis (which also computes its DC operating point). **No controller transient, tolerance change, physics edit, DD or layout run occurs.**

The cases are zero, saved working-electrode peak eta, saved working-electrode and Pt-return pre-abort endpoints, a bounded common-mode shift, and one clearly nonlinear eta 0.16 V bias. Actual row/time/node values and source/raw hashes are retained in configuration.json. The source-only bench omits capacitors and surrounding circuits deliberately: independent ideal sources hold metal/state/solution voltages and isolate the static law and its native AC derivatives. No transient behavior is inferred.

Each clone has exactly one independent 1 V AC input, the other terminals AC0. The measured input matrix must be the identity. The zero-volt current probe points from the drive into metal, so positive I(Vprobe) is metal→state current. The primitive resistor oracle must give derivatives (+g,−g,0); saved source currents independently check probe sign and branch KCL.

The [official ngspice 44 manual](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf) §5.1.1 states that a B-source's AC coefficients are derivatives at its DC operating point; §1.2.2 explains unity input scaling. Native DC/AC outputs are compared with Decimal 80-digit current and voltage-partial references for the exact model expression, including the stable polynomial correction. Declared absolute-plus-relative thresholds protect near-zero current/partials from meaningless relative errors. Tiny nonlinear corrections and common-mode error floors remain explicit.

Agreement supports a reduced coupled reproducer next; it does not establish complete startup or a simulator defect. This audit does not qualify coupled startup, released actuation, electrochemistry or native transient integration.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_adsorption_source_audit
```

The runner requires fresh destinations. Exact deck/log, source snapshot, detailed metrics and hashes are retained; native raw files remain local. Prior evidence is unchanged. No publication, submission, push or fabrication occurred.

| Bias | Native stable current (A) | Native solution partial (S) | Stable minus linear current (A) | Correction above declared error budget? |
|---|---:|---:|---:|:---:|
| zero | 0.0000000e+00 | 0.0000000e+00 | 0.000e+00 | no |
| working_peak_eta | 7.5247359e-13 | 5.4474429e-16 | -3.367e-21 | yes |
| working_last | 4.9049795e-13 | 2.3493453e-16 | -9.506e-22 | yes |
| return_last | -9.8100215e-13 | 9.3974970e-17 | 7.084e-23 | no |
| working_last_common_mode_shift | 4.9049795e-13 | 2.3493453e-16 | -9.539e-22 | yes |
| nonlinear_eta_0p16 | 4.9503620e-09 | 2.3563542e-08 | -1.550e-09 | yes |

The return-case nonlinear DC correction is below the combined current error budget; that is a resolution limit, not a disagreement. The −0.5 V common-mode case preserves the working-last reference/current/partials within the same declared floors. The nonlinear eta 0.16 V point exercises the outer correction branch; actual saved points exercise the small-polynomial branch.

Saved state voltages need not be natural DC adsorption equilibria: the isolated ideal state source prescribes each snapshot so that the branch's instantaneous constitutive current and local Jacobian can be measured. Capacitor dynamics and the coupled controller matrix are intentionally absent. The completed isolated audit recommends a reduced coupled reproducer, not a simulator-defect or root-cause declaration.

Two focused tests pass in 0.77 s; Ruff passes. They check resistor sign/scaling, independent clone assembly and complex-output parsing. One postprocessing attempt failed on NumPy-boolean JSON serialization after the native analysis had completed. Only scalar conversion/refactoring was corrected; `--audit-only` then read the existing native outputs, without launching ngspice again. The executed original runner is preserved, and the final runner offers that saved-data-only path.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_adsorption_source_audit --audit-only
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_adsorption_source_audit.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_adsorption_source_audit.py tests/integration/test_tcad_adsorption_source_audit.py
```
