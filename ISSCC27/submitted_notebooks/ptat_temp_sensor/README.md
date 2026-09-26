# Open-Source CMOS PTAT Temperature Sensor with Digital Calibration

**ISSCC 2027 Code-a-Chip** — reproducible SKY130 temperature-sensor project.

## Submission architecture

The release scope is deliberately explicit:

- analog core: two diode-connected SKY130 NMOS devices operated at an effective
  1:8 current-density ratio;
- bias distribution: PMOS current mirror characterized with an external `IREF`;
- observable: `ΔVGS`;
- digital correction: fixed five-point piecewise-linear calibration at
  **−40, −20, 0, 50, 125 °C**;
- readout: behavioral/external 12-bit, 1.8-V ADC model with release gain 10;
- power claim: PTAT core/mirror testbench only, **not** a complete ADC/system claim.

This scope avoids turning unimplemented blocks into implied silicon claims.

## Evidence classes

1. **Analytical** — first-principles Python model.
2. **Synthetic** — assumed variation only; never presented as PDK mismatch.
3. **Real PDK** — ngspice against SKY130/open_pdks, with retained raw CSVs and
   machine-readable provenance.
4. **Physical** — DRC/LVS/PEX only when retained sign-off artifacts exist.

## Current verified retained evidence

Run 221 used:

- ngspice 46
- open_pdks/SKY130 revision `12df12e2e74145e31c5a13de02f9a1e176b56e67`
- TT / FF / SS
- temperatures −40, −20, 0, 25, 50, 75, 100, 125 °C
- ideal-current and PMOS-mirror configurations

Retained deterministic mirror results include a worst branch mismatch of
**0.372%** and maximum characterized core/testbench power below **0.549 µW**.

## Calibration decision

Endpoint two-point calibration does **not** meet the 0.5 °C internal target:
the retained worst sampled error is **4.600 °C**.

The evidence-backed release method is five-point PWL calibration:

- anchors: **−40, −20, 0, 50, 125 °C**
- worst retained sampled-point absolute error: **0.472 °C**
- worst retained sampled-point RMS error: **0.212 °C**

These values apply only to the retained simulation samples. They are not
silicon, mismatch, post-layout, or between-sample guarantees.

## Readout decision

The original design seed used gain 8. The release readout uses **gain 10**
because it preserves headroom while reducing quantization degradation:

- 12-bit, 1.8-V behavioral ADC
- worst full-scale utilization: **0.787**
- worst quantization RMS: **0.0476 °C**
- worst quantized five-point sampled error: **0.455 °C**

This is a behavioral readout result, not a transistor-level ADC or ADC-power claim.

## Reproduce retained checks

    python evidence_audit.py
    python pdk_calibration_analysis.py --check
    python readout_budget.py --check
    python submission_preflight.py

or:

    make submission-preflight

## Dense real-PDK verification

A new pinned-PDK run completed on a **5 °C grid from −40 to 125 °C** across
TT/FF/SS and both ideal-current and PMOS-mirror configurations. The fixed
five-point PWL release calibration achieved a worst sampled-grid error of
**0.472 °C**, so the deterministic dense-grid target passed.

The compact retained record is in
`results/full_pdk_20260926/dense_pdk_analysis.json`; it names the workflow,
source commit, artifact, ngspice version, and PDK revision.

Reproduce it with:

    python run_sky130.py --mode both --corners tt ff ss --temps=-40:125:5
    python dense_characterization.py

## Real local-mismatch Monte Carlo

A 100-seed SKY130 `tt_mm` Monte Carlo run is now retained. With the release
five-point calibration it produced:

- **66%** error yield at ≤0.5 °C versus the internal 95% target;
- **0.962 °C** p95 maximum absolute error;
- **1.124 °C** worst maximum absolute error;
- **4%** branch-mismatch yield at ≤1%.

Therefore the statistical mismatch target is **not met** by the current
transistor sizing. This is reported as a negative engineering result, not
converted into a passing claim. The per-seed metrics and provenance are retained
under `results/full_pdk_20260926/`.

A retrospective two-fold split-sample robustness study now reduces the tuning
leakage in that six-point result. Seeds 1001–1050 and 1051–1100 were treated as
disjoint folds. Each fold independently selected the same schedule,
**−40, −25, −5, 25, 65, 125 °C**, using only its own 50 samples, and each
opposite-fold evaluation passed **49/50 samples (98%)** at ≤0.5 °C. Across all
100 samples the shared schedule passes 98/100; the Wilson 95% interval for that
point estimate is approximately **93.0%–99.45%**.

This is stronger than fitting all 100 seeds at once, but it remains a
**retrospective study from one retained Monte-Carlo run**, not a new independent
confirmation run. It is therefore not promoted into the release architecture,
and it does not change the separate **4%** branch-mismatch yield failure.

The retained compact study is
`results/full_pdk_20260926/mismatch_calibration_holdout.json`. The raw artifact
can be reprocessed with `mismatch_holdout_analysis.py`.

## Independent candidate validation

CI run 36259524511 added genuinely disjoint validation evidence for the
low-power and mismatch-sizing candidates using the same pinned SKY130/open_pdks
revision.

The **1.2 V / 10 nA** operating-point candidate was evaluated on 100 independent
seeds (7001–7100). Its calibrated temperature error passed on **100%** of
samples, with p95 maximum error **0.378 °C** and worst maximum error
**0.462 °C**, but the ≤1% branch-mismatch yield was only **5%**. It therefore
fails the statistical release contract despite its strong temperature-error
result.

The sizing screen selected **`i1_m16_s1`** for independent validation:
nominal sensor geometry, 16× linear PMOS-mirror scaling (256× mirror device
area), and the nominal 100 nA reference current. On the disjoint 100-seed set
9001–9100 it achieved:

- temperature-error yield at ≤0.5 °C: **66%**;
- branch-mismatch yield at ≤1%: **64%**;
- p95 maximum temperature error: **0.770 °C**;
- p95 maximum branch mismatch: **1.929%**;
- minimum sensor headroom: **1.169 V**.

The same candidate still passes deterministic dense TT/FF/SS verification
(**0.472 °C** worst PWL error, **0.950%** worst deterministic mirror mismatch)
and the behavioral 12-bit / gain-10 readout budget (**0.478 °C** worst
quantized sampled error). The final machine-evaluated result is therefore
**`NOT_QUALIFIED_FOR_RELEASE_REVIEW`** because the independent mismatch
criterion fails. The release architecture remains unchanged.

The compact retained record is
`results/full_pdk_20260926/candidate_validation_summary.json`, tied to workflow
run 36259524511 and artifact digest
`sha256:489e26dc01ed0dde54091e204d3162c47d472d969b48dd4b153a9bb59c2d3c84`.

## Physical implementation

A layout is encouraged by the Code-a-Chip program but not required. The
`layout/` directory defines the physical boundary, matching strategy, LVS source
netlist, and retained-artifact contract. No DRC/LVS/PEX PASS is claimed yet.

## Jupyter notebook

`PTAT_Temperature_Sensor_Code_a_Chip.ipynb` is the primary competition artifact.
It explains the circuit, reads the retained real-PDK evidence, reproduces the
calibration result, checks the behavioral readout budget, and states all
evidence boundaries.

## License

Apache-2.0. See `LICENSE`.
