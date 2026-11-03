# Adjacent-placement repair: completed electrical and native diagnostic

Copyright 2026 EDABK Laboratory.

This completed development experiment is separate from the current full-notebook acquisition. Its rejection is retained; the verified ideal-stimulus release remains selected.

| Check | Observed result |
|---|---|
| Extracted loaded pulse | 64/64 cases; all seven contract checks pass |
| Calibration anchors | 312 conversions; all eight 39-level banks strictly ordered; minimum adjacent step 5 codes |
| Same-sum transfer | 35/96 wrong; minimum margin -8 codes |
| Native application | 162/384 partial sums differ; 42/48 final values differ from the ideal integer model |
| Real MHA/readout RTL | Zero differences from the measured-error arithmetic outputs, with request identities checked |
| Actual control schedule | Maximum 80 ns difference from the native acquisition profile; timing acceptance fails |

## Six preselected frames

| Test index | True class | Integer-model class | Routed-native class | Output relative L2 |
|---:|---:|---:|---:|---:|
| 79 | 0 | 1 | 1 | 0.224814 |
| 133 | 1 | 1 | 1 | 0.321634 |
| 109 | 2 | 0 | 0 | 0.424918 |
| 31 | 3 | 3 | 4 | 0.357967 |
| 0 | 4 | 4 | 4 | 0.071550 |
| 55 | 5 | 5 | 5 | 0.075378 |

The integer reference class is retained on five of six examples, but the small selection is not a dataset accuracy estimate. These six examples contain two reference classifier errors and one additional class change.

## Engineering consequence

The placement repair restores short-pulse delivery. Ordered calibration anchors do not remove decomposition-dependent charge/code spread. The data-dependent decoder path also changes later control timestamps when measured words take different search branches. Complete routed-input acceptance requires both pulse/charge linearization and a timing-consistent calibration/replay loop. Positive STA and a passed pulse gate are insufficient.

## Reproduction and evidence

- Physical recipe and all pulses: `experiments/closure_20261028/harden_pulse_adjacent.py`, `adjacent_qualification/pwm/verification.json`.
- Native campaign: `/media/nam/EDABK/AutoMX_CIM_electrical_lab_20261029/nominal/electrical/`, including per-case source/summary and the complete trace.
- Real RTL: `experiments/closure_20261028/replay_rejected_native.py`, `adjacent_measured_error_rtl_replay/`; the control-timing assertion is intentionally retained as failed.
- Final clean Run All reacquires candidate pulse/calibration-transfer evidence instead of taking this diagnostic as an ADC-response input.

## Measured scalar-calibration separability

Exact interval/order test on 312 measured calibration anchors plus the 96 nominal pattern checks. A conflicting level pair proves no monotone scalar threshold table can classify every member of this finite measured set. It is not a noise/yield bound.

| Bank | Wrong / 12 | Minimum guard, raw codes | Conflicting neighboring intervals |
|---:|---:|---:|---:|
| 0 | 5 | -7 | 0 |
| 1 | 5 | -7 | 0 |
| 2 | 5 | -8 | 0 |
| 3 | 5 | -8 | 0 |
| 4 | 3 | -5 | 0 |
| 5 | 4 | -5 | 0 |
| 6 | 4 | -6 | 0 |
| 7 | 4 | -6 | 0 |

![Measured scalar-calibration intervals](figures/adjacent_scalar_separability.png)

No neighboring measured level intervals conflict in this limited nominal pattern set. The current midpoint LUT fails, but these observations do not prove that every scalar LUT must fail. Selecting thresholds against this held-out set would consume it as training data. A richer, predeclared calibration-pattern policy must therefore be checked on new independent patterns, both weight polarities and the actual application/control schedule.

## Retrospective threshold-policy diagnostic

Using the old 96 same-sum checks as additional **training** permits interval-aware thresholds for that finite nominal set. Re-decoding the 384 recorded application requests reduces partial errors from 162 to 129 (Q/K/V/O: 25/35/37/32). This does not replay the altered attention context or its new O requests and does not reconcile control timing. It is not a new validation pass; the former 96 checks have been consumed as training. The remaining errors motivate testing weight/sign context together with pulse/charge linearity, rather than claiming a threshold-only repair.

## Next bounded repair

1. Characterize row/sign width and charge, including the nonzero-code intercept; choose the tap/driver construction to support additive products before freezing scalar thresholds.
2. Retest single/multiple active rows and both weight polarities. Keep anchor and held-out decompositions disjoint.
3. Reconcile control timestamps with actual replayed ADC decisions, or select a documented constant-latency decoder policy, before remeasuring held-out margins.
4. Adopt only after the six fixed frames and tagged RTL replay pass under that same schedule.

Full internal-wire transistor PEX, production mismatch/yield and whole-chip energy remain separate scopes.
