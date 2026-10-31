# CIM–SAR–MHA operating contract

Copyright 2026 EDABK Laboratory.

This document explains the implemented interface and measured operating procedure. The packaged measured outcomes are recorded in `PRIORITY_CLOSURE_RESULTS_20261029.md`; the accepted electrical-closure release is recorded in `../results/execution/release_validation.json` and `../results/execution/FINAL_RELEASE.json`. Development measurements do not replace that release gate.

## Computation and ownership

The reusable MHA IP implements two tokens, four channels and two heads. It requests Q, K, V and O projections from a programmable ternary backend. The mixed backend reuses one four-row/four-column compute macro, acquisition/conditioning and one SAR conversion path. The readout evaluates two row phases, reads four columns sequentially, decodes each measured partial sum and adds the two phases. One four-output token projection therefore needs eight conversions; a complete two-token Q/K/V/O frame needs 64.

The controller registers hold `WPOS/WNEG` masks. Each eight-NMOS leaf contains four series branches that discharge the positive or negative bitline according to activation sign and programmed weight. There is no SRAM storage latch inside that leaf. Activation magnitudes are represented by wordline pulse duration; the charge depends on delivered voltage and duration, not just the RTL code. MXFP4 is the block-scaled numerical representation; X2 is the integer representation of its E2M1 element values used by this prototype.

The MHA score, probability approximation and context arithmetic execute in RTL. Feature extraction, token embedding and the final six-class classifier execute in software. A full sensor classification therefore includes host work as well as IP service time.

## Initialization and resident state

1. Apply reset and allow the actual 8,192-clock analog-bias boot interval. At 25 MHz this is 327.68 µs.
2. Program 304 ordered thresholds: 38 boundaries in each of eight phase/column banks. The accepted-write interface performs neighbor checks before returning ready. The measured sequence takes 36.48 µs, excluding boot. Threshold payload is 3,648 bits; including nine-bit addresses, the accepted transactions carry 6,384 bits.
3. Program 16 weight rows: four matrices, four rows each. Stored masks total 128 bits. The measured sequence takes 0.64 µs; its interface transactions carry 192 bits including projection/row addresses.
4. Submit only when ready and hold each valid payload until acceptance. Keep ownership with the MHA transaction until all backend requests have completed. Backpressure must retain valid outputs and their values.
5. Retained idle keeps masks and calibration resident. The measured wake regression checks six distinct idle intervals before new frames. It does not presume an analog power switch or a software serial transport.

Threshold data clock gating changes accepted-write activity only. Validity, reset, control and fault state preserve the original protocol. The measured isolated ICG comparison checks actual threshold FF clock edges as well as output equivalence; a power tool that ignores gated clock activity cannot determine this design choice.

## Electrical interpretation

Calibration and payload must use the same pulse source/loading, differential orientation, acquisition/hold schedule and ADC-word interpretation. The conditioner `AINN` connects to ADC `inp`; `AINP` connects to `inn`. This orientation makes supported signed sums increase with the raw word. The 12-bit word is a code format; it is not an ENOB measurement.

The physical pulse experiment reconstructs actual mapped SKY130 transistor cells, distributed readout/parent SPEF and core-PEX input loading. FF clock arrival/slew comes from propagated child timing. It checks all 64 row/sign/code combinations, quiet unselected lines, single pulses, swing, ordered widths and bitline polarity. The notebook retains a measured rejection on the previous placement before retesting an adjacent gate/driver candidate on identical RTL. The evaluated candidate places its pulse-forming gates and strong output drivers in four adjacent clusters, and the output-net wire terms are tabulated from both actual SPEFs. A new parent route is measured again; an earlier parent waveform does not qualify it automatically. Only a passed current-run pulse and native application gate supports a routed-input release; the audited release receipt states the actual accepted stimulus.

The separately completed ideal-50-ps experiment follows measured RTL control timing and contains 1,016 native stimuli, six activity frames and zero electrical output mismatches. It provides a diagnostic reference, not proof that an earlier routed short-pulse path works. Two of those six examples are classified incorrectly by the frozen application even when the hardware output is exact.

At sampled transistor PVT conditions, frozen TT thresholds produced 100/196 held-out errors in that diagnostic. Five measured anchors per bank/condition with piecewise interpolation reduced them to 0/196. This is a sampled recalibration policy, with 140 anchors and 196 held-out checks; it is not a statistical mismatch/yield result. The routed pulse-delay study remains nominal TT unless an explicit corner-specific driver experiment is supplied.

The timed replay observes six clocks / 240 ns from the START pin to EOC. An ADC fixture parameter of five accounts for its extra detection clock. A timer parameter alone must not be reported as the measured conversion duration. The last column sees a much older held sample than the first; per-request timestamps carry this distinction into native measurement and replay.

## Cost and useful service

Compare linear decoding, binary decoding, calibration-gated binary decoding and serial ternary digital projection under matched frames, response timing, output readiness, supply, Liberty and power-tool version. Report mapped cell area, actual routed standard-cell area and hard-macro footprint separately. The isolated gating result is a controlled intervention; the current-readout row repeats the adopted gated view under the same six-frame fixture.

Conversion energy is the actual sampled V×I integral over SAR START–EOC. A token projection table may sum its eight conversion windows, but this omits acquisition/hold and controller/MHA work. Warm readout/MHA VCD energy, analog/reference energy, SAR digital control, parent clock tree, I/O, programming, retained idle and host work have different ownership windows. They must not be added or compared as complete-chip totals without a consistent continuous operation.

The HAR sensor window is 128 samples at 50 Hz, with a 1.28-second decision stride. The always-biased analog partition consumes approximately 1.320 mW in the initial idle-control profile; programming the deployed O-weight masks gives 1.501 mW in the completed resident-idle API experiment. The fresh notebook measures its actual retained controls again. Idle bias dominates the sensor-stride energy. The sensor and burst tables report disjoint accounted terms and identify missing owners rather than claiming complete-system or digital-baseline energy superiority.

The application policy remains frozen across 2,947 official test windows from nine unseen subjects. All observed RTL outputs are compared with the independent quantized reference. Validation-only missing-channel, gain and offset challenges do not retune on test subjects. A second supported configuration sets Q=0 to implement the existing retrained uniform-attention control without changing the IP.

## Reproduction

`scripts/quick_review.py` recomputes frozen model predictions, runs six representative frames per RTL path and inspects GDS hierarchy. Its short runtime does not include circuit acquisition, training or routing. The extracted-IP check installs NumPy into an isolated environment and runs actual numerical/protocol/decoder checks outside the workspace. Full Run All uses a new empty run tree, acquires new native responses/activity and routes a fresh parent from declared source/IP/PDK inputs.

Source-visible notebook cells contain the implementations executed by the run cells. Principal tables/plots appear adjacent to the corresponding experiment; full native transcripts and per-case outcomes remain in the current run directory. All baseline cell IDs and useful numerical lessons are retained in the candidate. Main and executed candidate notebooks are published together only after full execution and independent artifact checks pass.
