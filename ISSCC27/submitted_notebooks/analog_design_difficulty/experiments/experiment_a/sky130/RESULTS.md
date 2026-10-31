# SKY130 sample-and-hold front end — results

Definition: `DESIGN_BRIEF.md`. Follow-up studies: `SWITCH_WIDTH_STUDY.md`, `SMALL_STEP_PORT_COMPARISON.md`, `HOLD_ERROR_DESIGN_RESPONSE.md`, each with its own result section. Data: `results/data/sky130_summary.json`, `sky130_grid_error_tt.csv`, `sky130_switch_ron.csv`, `sky130_waveforms_tt.csv`, `sky130_small_signal.csv` (`run_sky130.py`) and `sky130_followup_summary.json` (`run_followup.py`). Toolchain: ngspice-42, open_pdks `c6d73a35f524070e85faff4a6a9eef49553ebc2b`; `tt`, 27 °C unless stated.

Statements are marked *Observed* (simulated here) or *Interpretation*.

## 1. Summary against the parent requirement

| Budget entry (`DESIGN_BRIEF.md` Section 2) | Allocation | Chosen transmission gate | Status |
|---|---|---|---|
| acquisition settling | ε = 0.29 mV at 40 ns (≈ ½ `VLSB`) | worst error at 40 ns 0.011 mV; latest crossing of ε 29.7 ns | **PASS** at all nine points |
| held-sample error after two-point correction (zero step, seven levels) | ½ `VLSB` = 0.293 mV; parent limit ±1 `VLSB` = 0.586 mV | 0.64 mV | **FAIL** (also above ±1 `VLSB` on its own) |
| — turn-off component | ¼ `VLSB` = 0.15 mV | 0.83 mV (uncorrected hold step −7.8 to +5.0 mV) | FAIL |
| — driver static tracking | ¼ `VLSB` = 0.15 mV | 0.33 mV | above its share |
| sampled kT/C noise | separate random entry, outside the deterministic ±1 `VLSB` | 64 µV rms (derived) | — |

*Observed:* the driver and switch meet the acquisition-settling allocation, while the held-sample function fails its deterministic 10-bit-equivalent accuracy target under the tested `tt` zero-step conditions; the turn-off error dominates. The residual components add with sign (`R_E = R_S + R_P`) and partly cancel, so the total 0.64 mV is smaller than the 0.83 mV turn-off component. This failure was expected from the hand estimate in `DESIGN_BRIEF.md` Section 2; the simulation quantifies it.

## 2. Driver bring-up

*Observed:* loop unity-gain frequency 54.4 MHz, phase margin 64.9° with 1 pF; 85.0° with a 1 fF load (≥ 45° required for the output-port tests to start from a settled driver). Closed-loop `|Zout|` 33 Ω at low frequency, peak 1.17 kΩ near 89 MHz; input-to-output peaking 0.02 dB. DC tracking within 1 mV for inputs 0.52–1.50 V; +0.36, +0.43, −0.02 mV at 0.6, 0.9, 1.2 V.

## 3. Transmission-gate on-resistance (DC, both terminals at the level)

| Gate, NMOS / PMOS | 0.6 V | 0.9 V | 1.0 V | 1.2 V | maximum in 0.6–1.2 V |
|---|---:|---:|---:|---:|---:|
| half, 7.5 / 15 µm | 202 Ω | 1.01 kΩ | 1.40 kΩ | 575 Ω | 1.44 kΩ at 0.98 V |
| **chosen, 15 / 30 µm** | **96 Ω** | **479 Ω** | **728 Ω** | **284 Ω** | **744 Ω at 0.98 V** |
| double, 30 / 60 µm | 48 Ω | 240 Ω | 364 Ω | 142 Ω | 372 Ω at 0.98 V |

`R_if` = 744 Ω. The chosen gate meets the 1 kΩ switch allocation; its on-resistance still varies 7.8 : 1 over the range.

## 4. Tests (a), (b), (c) at the nine operating points

Last time `|error| ≥ ε` (ns) / error at 40 ns (mV); points are target/previous.

| Point | (a) input step | (b) output-port test, `R_if` | (c) connected | (b) − (c) | (b) is |
|---|---:|---:|---:|---:|---|
| 0.6/0.6 | — | 0.5 / +0.0000 | 10.3 / +0.0000 | −9.8 | optimistic |
| 0.6/0.9 | 24.3 / −0.0010 | 26.3 / −0.0050 | 24.4 / −0.0000 | +1.9 | conservative |
| 0.6/1.2 | 33.5 / +0.0611 | 31.1 / −0.0308 | 29.7 / −0.0108 | +1.4 | conservative |
| 0.9/0.6 | 20.0 / −0.0001 | 20.9 / −0.0007 | 19.5 / −0.0003 | +1.5 | conservative |
| 0.9/0.9 | — | 0.8 / −0.0000 | 7.5 / +0.0000 | −6.7 | optimistic |
| 0.9/1.2 | 21.1 / +0.0001 | 23.2 / +0.0014 | 22.5 / +0.0015 | +0.8 | agrees |
| 1.2/0.6 | 26.7 / +0.0034 | 21.6 / −0.0009 | 19.3 / +0.0000 | +2.3 | conservative |
| 1.2/0.9 | 19.5 / −0.0001 | 20.5 / −0.0006 | 18.7 / +0.0001 | +1.8 | conservative |
| 1.2/1.2 | — | 0.0 / −0.0000 | 9.1 / +0.0000 | −9.1 | optimistic |

*Observed:*

- Every test passes at 40 ns at every point. The slowest case is the full-scale step down: 29.7 ns connected, 33.5 ns for the input step.
- With `R_if` at the maximum on-resistance, (b) is conservative by 1.4–2.3 ns at five transitions and agrees within 1 ns at the sixth.
- At the zero-step points (b) crosses ε only briefly: its initial error is the driver's DC tracking error relative to the ideal precharge level (+0.36 and +0.43 mV at 0.6 and 0.9 V, −0.02 mV at 1.2 V), removed within 0.8 ns. The connected test stays above ε for 7.5–10.3 ns because of the gate's turn-on disturbance: charge coupled by the complementary gate edges into the driver output (+26 mV at 0.6 V, +14 mV at 0.9 V, −30 mV at 1.2 V), which the driver then removes. The resistor-only representation has no term for it.
- Step-down transitions are slower than step-up ones (29.7 against 19.3 ns at full scale in (c)). At the 0.9 V target, `t(Vprev = 1.2) − t(Vprev = 0.6)` is 2.3 ns in (b) and 3.0 ns in (c): about three quarters (0.76, additive split assumed) of the direction dependence remains with a linear switch representation.
- (a) settles later than (c) at four of the six transitions; at 10 ns its error is larger at every transition. Whether (a) bounds (c) depends on the metric and the point.

## 5. Acquisition-time sensitivity: block-PASS / connected-FAIL

From the last crossings above, the times after which the error remains within ε (reading defined in `DESIGN_BRIEF.md` Section 6). Figure: `figure_sky130_acquisition_window.png`.

| Rows | (b) supports | (c) needs | Interval |
|---|---:|---:|---|
| zero step 0.6/0.6 | 0.5 ns | 10.3 ns | block PASS, connected FAIL for 0.5 < T ≤ 10.3 ns |
| zero step 0.9/0.9 | 0.8 ns | 7.5 ns | block PASS, connected FAIL for 0.8 < T ≤ 7.5 ns |
| zero step 1.2/1.2 | 0.0 ns | 9.1 ns | block PASS, connected FAIL for 0 < T ≤ 9.1 ns |
| six transitions | 20.5–31.1 ns | 18.7–29.7 ns | conservative or agreeing (block FAIL, connected PASS for up to 2.3 ns) |
| input class: any previous sample | 31.1 ns | 29.7 ns | conservative: block FAIL, connected PASS for 29.7 < T ≤ 31.1 ns |
| zero-step fixture only (`Cs` starts at the target) | 0.8 ns | 10.3 ns | **block PASS, connected FAIL for 0.8 < T ≤ 10.3 ns** |
| small steps ±10, ±20 mV at 0.9 V (small-step study) | 10.7–11.9 ns | 9.7–11.4 ns | agrees within 1 ns or conservative |

*Interpretation:* for the declared input class (any previous sample) and any allocation, the conservative representation never accepts an allocation that the connected circuit rejects. In the zero-step fixture, in which `Cs` starts exactly at the target, every allocation between 0.8 and 10.3 ns would pass the block test and fail in the connected circuit. A real repeated sample would start with the previous hold error (−7.8 to +5.0 mV for the chosen gate), so the exact interval belongs to the fixture. Steps of 10–20 mV at 0.9 V already move enough charge that the representation agrees within 1 ns or is conservative. The resistor representation is adequate or conservative for the tested transition cases, but it omits a turn-on mechanism that becomes decision-relevant as the initial charge-transfer demand approaches zero and the allowed acquisition interval becomes short. No allocation other than 40 ns was simulated; the interval is read from the waveforms.

## 6. Matched control (m) against (c), full-scale transitions

| Transition | largest normalized difference, 0–40 ns | (m) last crossing | (c) last crossing |
|---|---:|---:|---:|
| 0.6 → 1.2 (driver supplies) | **0.86** at 3.5 ns | 31.3 ns | 19.3 ns |
| 1.2 → 0.6 (driver sinks) | **0.79** at 8.8 ns | 33.5 ns | 29.7 ns |

*Observed:* both exceed the 0.10 criterion. In (c) node `x` is pulled through `Cc` within the first nanosecond: down to 1.08 V when the driver must supply charge (M6 current up to 595 µA), up to 1.66 V when it must sink (M6 nearly off; M7 up to 131 µA). In (m) node `x` stays within about 0.06 V of its settled value while the output slews at 32–36 V/µs, close to `Itail/Cc` = 40 V/µs. *Interpretation:* at full scale an input step is limited by first-stage slewing and a connection event by the output stage and its class-A sink current.

## 7. Small-step port comparison (`SMALL_STEP_PORT_COMPARISON.md`)

*Observed:* with ±10 and ±20 mV steps at 0.9 V and the switch represented by `R_if`, the normalized difference between input step and output-port disturbance is 0.53 at all four steps, while no case slews (largest first-stage imbalance 0.22) and the normalized waveforms are amplitude-independent within 0.012. The port difference therefore exists in the approximately linear regime; the full-scale values contain a large-signal contribution on top of it. The reduced model's 0.46 is not a quantitative reference for 0.53: the reduced model is a qualitative mechanism model, not fitted to this driver.

## 8. Checks

- **Numerical convergence:** with a 10 ps maximum step and with `reltol` = 1e-5, last crossings move by at most 0.01 ns and errors at 40 ns by at most 0.00004 mV (limits 0.2 ns and 0.03 mV): PASS.
- **Corners (27 °C, full-scale transitions):** all PASS at 40 ns. Last crossing, up / down: (a) 26.8 / 34.5 ns (`ss`), 26.7 / 33.0 ns (`ff`); (b) 21.6 / 33.1 ns (`ss`), 21.9 / 29.5 ns (`ff`); (c) 20.9 / 32.3 ns (`ss`), 18.7 / 27.4 ns (`ff`). (b), with the `tt` value of `R_if`, stays conservative at both corners.
- **Conditional second-stage variation:** the step down is slower, but the M7 current rose to 131 µA, above the 1.2 × bias (122 µA) condition, so the variation was not run.

## 9. Switch width and held-sample error

- Switch width (`SWITCH_WIDTH_STUDY.md`): from half to double width the worst-case acquisition moves by less than 0.3 ns (driver-dominated), while the zero-step settling (0.8, 7.5, 8.8 ns) and the turn-on excursion (7, 14, 26 mV) grow.
- Held sample (`HOLD_ERROR_DESIGN_RESPONSE.md`), level-dependent turn-off component after two-point correction, with the worst connected acquisition over the nine evaluated points:

| Gate | max. on-resistance | turn-off component | held-sample residual | check | worst acquisition |
|---|---:|---:|---:|---|---:|
| chosen | 744 Ω | 0.83 mV | 0.64 mV | FAIL | 29.7 ns |
| chosen + half-size dummies | 744 Ω | 0.46 mV | 0.78 mV | FAIL | 29.9 ns |
| one eighth | 5.2 kΩ | 0.09 mV | 0.27 mV | PASS of the zero-step check (0.02 mV margin against ½ `VLSB`) | 32.2 ns |
| one quarter | 2.9 kΩ | 0.20 mV | 0.23 mV | PASS of the zero-step check | 30.8 ns |

*Observed:* the dummy-switch response reduces the uncorrected hold step about fivefold but its level-dependent part only 1.8-fold (outcome C by the criterion of the study). The turn-off component scales with width, while acquisition with this driver changes little down to one eighth of the chosen width. Only the one-eighth gate meets the turn-off share; the total zero-step residual ranks half (0.19 mV, three acquisition points), quarter (0.23 mV), and one eighth (0.27 mV) the other way.

## 10. Reading

*Interpretation:*

- The acquisition-settling allocation was met with 10.3 ns of margin in the connected test at `tt` (6.5 ns over the slowest input-step test).
- The held-sample requirement was not met by the chosen gate under the tested `tt` conditions. For this fixed driver at `tt`, acquisition settling is weakly sensitive to switch width over the studied ladder, while the turn-off residual scales strongly with width; the 1 kΩ local switch allocation, from a linear time-constant budget (7.6 τ in 40 ns), was therefore more restrictive than this driver's measured acquisition required. A faster driver could make the switch resistance important again. Half-size dummies mainly removed offset and gain.
- The local turn-off share and the parent signed residual rank the widths differently: optimizing a local error allocation and optimizing the parent signed error are not necessarily the same problem. The driver's static tracking residual (0.33 mV) is above its share, and the narrow gates pass the zero-step check only through partial cancellation. For them the parent requirement for every previous sample is an estimate (acquisition residual at most 0.04 mV at 40 ns, turn-off component assumed to depend on the held level), not a demonstrated pass; transition-then-open cases, continuous coverage, and corners were not simulated. No final width is selected. The demonstrated need is a driver revision that reduces the measured level-dependent tracking error, or another budget split.
- The conservative one-resistance representation was adequate for the declared input class at every allocation, and inadequate in the zero-step fixture below about 10 ns. Whether a representation is adequate depends on the requirement it is used for.
