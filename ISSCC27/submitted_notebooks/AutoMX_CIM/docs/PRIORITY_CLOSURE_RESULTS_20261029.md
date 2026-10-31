# AutoMX-CIM measured priority outcomes

Copyright 2026 EDABK Laboratory.

This report is generated from the audited fresh execution. It distinguishes completed experiments from electrical acceptance. The selected implementation is the isolated calibration-data ICG readout, the original compute/acquisition core, conditioner, upstream SAR ADC and real MHA IP. No enlarged-capacitance development macro is adopted.

Execution root: `/media/nam/EDABK/AutoMX_CIM_qualified_validation_20261029`. Fresh run: `/media/nam/EDABK/AutoMX_CIM_qualified_validation_20261029/runs/fresh_20261029_123523_717579`. Checked UTC: 2026-10-29T15:10:30.904778+00:00.

| Priority | Measured outcome | Acceptance |
|---|---|---|
| P0-A, electrical interface | 64 actual routed pulse cases; 5 failed contract checks | Pulse delivery measured; direct routed-PWM native closure remains unqualified |
| P0-B, calibration | 88 held-out + 8 anchor checks; 0 wrong | Pass for the declared ideal-stimulus partition |
| P0-C, storage switching | 60.943426% lower matched child energy; ICG enable +10.078860/+3.758537 ns | Adopted; actual mapped/gate/protocol checks pass |
| P0-D, service | Unforced boot, real programming, resident idle/wake, four settling policies and sensor/burst accounting | Measurements complete; settling uses ideal pulses; energy subtotals retain their ownership |
| P0-E, application | 2,947 windows; accuracy 81.405%; macro-F1 80.706%; six native frames / 384 transactions | Exact hardware/reference outputs; classifier errors retained |
| P0-F, reproducibility | 509 cells / 205 code; 509 preceding IDs retained; 154.68 minutes | All code outputs present, no notebook errors; three independent auditors pass |

## Matched active operation

| Variant | Frames | Latency, µs/frame | Child-digital nJ/frame | Mismatches |
|---|---:|---:|---:|---:|
| linear | 6 | 186.140000 | 1936.548737 | 0 |
| binary | 6 | 102.593333 | 1055.528380 | 0 |
| binary_gated | 6 | 102.593333 | 412.253226 | 0 |
| digital | 6 | 8.860000 | 19.432702 | 0 |
| current_readout | 6 | 102.593333 | 412.253226 | 0 |

Same frames, declared response policy, 25 MHz, SKY130 TT 1.8 V / 25 °C and OpenSTA 3.1 VCD/Liberty estimate with child SPEF. Parent CTS/IO, analog and SAR digital are separate. The serial digital sign/add baseline remains in the table.

## Analog and operation

- Nominal minimum sampled margin: 5 raw codes. Calibration uses 312 measured anchors, followed by the held-out checks.
- Seven-condition PVT: 100/196 frozen-TT errors; 0/196 after five-anchor interpolation; unresolved 0. Stimulus: ideal 50ps unit; analog/timing diagnostic only. This is sampled transistor-condition coverage with the declared nominal driver policy.
- Native campaign: 1016 unique acquisitions; 384 logical application conversions; six class-selected frames; 0 partial mismatches. Stimulus: ideal 50ps unit; analog/timing diagnostic only.
- Retained analog idle: 1.500532 mW for the measured masks/control state. Readout idle and boot come from real mapped activity. `sensor_duty_budget.json` retains the disjoint accounted terms.
- Conversion/projection values are integrated START–EOC windows, not complete-frame analog energy. Acquisition, controller, host and idle owners remain separate.

## Source, views and reproduction

- The source/executed notebooks are identical and preserve all earlier cells. Source-visible cells recreate native workers; no saved native responses are verification inputs.
- The five-block top is newly routed from source-matched hard IP. Its geometry, signal macro-boundary LVS, rails and hierarchical timing are independently checked. Fixed-palette KLayout overview exports match pixel for pixel.
- The source-IP archive is extracted into an isolated Python environment; actual MHA, ternary and decoder tests execute there. The short check has its own smaller documented coverage.
- Full-foundry-deck completion, routed short-pulse repair and full-chip supply energy are not implied by the prototype release. The real delivered-pulse failure remains visible in the notebook.

Reports and figures are in the fresh run under `electrical_closure/`; final GDS, overview/detail PNGs and source-IP archive are in `exports/`.

## Measured code budget and programming

The minimum remaining conditional guard is 4 raw codes after the conservative sampled settling debit. Noise/offset allocation is zero; this arithmetic budget applies to the declared finite experiment.

The readout programming window measures 285.609434 nJ over 36.800000 microseconds for 304 thresholds and four resident O-stage masks. MHA configuration, analog calibration acquisition and transport are separate owners.

## Fresh candidate electrical evaluation

The candidate contains 1288 physical MIM devices, with Magic DRC 0 and transistor LVS PASS. Its freshly routed parent has setup +5.510000 ns and hold +0.100000 ns.

All 64 actual delivered-pulse cases and 28 fixed signed native conversions were acquired in this full run. Native unresolved count: 0. Candidate decision: EVALUATED_REJECTED. Zero-input aliases within one code: 0.

The adoption gate retains the qualified controller and separate ideal-stimulus native proof. Candidate GDS and deterministic overview/detail are exported under `AutoMX_CIM_evaluated_candidate`; these are measured development results, not a passed routed-input application release.

## Physical repair and calibration-transfer decision

The adjacent gate/driver placement has 0 failed pulse checks over 64 newly acquired cases. Its 312 fresh calibration conversions produce 8/8 strictly ordered banks; the separate 96 same-sum checks have 35 wrong decoded sums. Ordered anchors and correct pulse polarity do not by themselves establish transferable scalar calibration.

The notebook displays the actual 16-row previous/adjacent-placement wire-capacitance table, each delivered waveform, calibration-bank steps and held-out errors. The current release retains the qualified ideal-stimulus partition. These candidate errors are preserved as measured outcomes, not bypassed by substituting expected ADC answers.
