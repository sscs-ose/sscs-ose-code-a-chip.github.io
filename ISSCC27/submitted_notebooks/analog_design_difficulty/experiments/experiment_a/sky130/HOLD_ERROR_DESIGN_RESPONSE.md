# Held-sample error: one architectural design response — definition

Date: 2026-10-30 JST
The technique, its sizing, the cases, metrics, and acceptance criteria are defined below; nothing is tuned to the results. Conditions not named here are those of `DESIGN_BRIEF.md`.

## Why this study is needed

Under the 10-bit-equivalent held-sample requirement of `DESIGN_BRIEF.md`, the transmission-gate sample-and-hold meets the acquisition-settling allocation ε at every tested operating point, but its hold-step measurement (−7.8, −2.1, +5.0 mV at 0.6, 0.9, 1.2 V) is far outside the held-sample budget, as the hand estimate of `DESIGN_BRIEF.md` Section 2 suggested. The question is what kind of revision the failure calls for.

> **This study exists so that the reader can see whether an established change of the sampling-switch architecture, aimed at the measured switch-opening error, reduces the held-sample error without destroying acquisition settling, and whether simply resizing the switch could have done the same.**

## Selecting the technique

The measured error is the change of the held voltage when the gate opens: the channel charge of the NMOS and PMOS devices and their gate-overlap coupling of the clock edges, with an NMOS/PMOS imbalance that changes with the held level (Wegmann et al. 1987; Razavi 2017; Carusone et al. 2012). Established remedies, judged against this parent function (single-ended, held voltage observed at high impedance, `Cs` to ground, same driver and clocks):

| Technique | Mechanism it acts on | Fit to this parent function | Cost |
|---|---|---|---|
| smaller switch or larger `Cs` | scales the injected charge, or the voltage it produces | moves along the existing trade-off with on-resistance, settling, and kT/C | none in devices; checked by the extended width ladder below |
| **dummy-switch compensation** | half-size dummy devices on the `Cs` side, clocked in antiphase, absorb the channel charge that the main devices release toward `Cs` and cancel the overlap coupling; the dummy channel forms at the held level, so the compensation follows the level (Eichenberger and Guggenbühl 1990; Razavi 2017) | direct: acts on the held node of a voltage-mode hold with the existing complementary clocks | two small devices, no new clock phase |
| bottom-plate sampling | the bottom-plate switch opens first, so the charge on the isolated plate no longer depends on the signal-side switch (Carusone et al. 2012) | indirect: it changes the hold architecture and clock sequencing; its usual benefit relies on preserving charge on an isolated plate and is commonly used with charge-transfer or differential readout structures, outside the simple voltage-mode parent function studied here | an extra switch and an advanced clock phase, usually with a charge-transfer or differential readout |
| bootstrapped switch | holds the gate-source voltage nearly constant, so the channel charge becomes nearly level-independent | partial: turns the level-dependent part into an offset, but a single NMOS device with full gate drive injects a large constant charge | a boosting circuit (capacitor, several devices, gate-stress checks) |
| differential sampling | cancels the part that is common to both halves | not applicable to a single-ended parent function | a second signal path |

**Selected: dummy-switch compensation.** It is the technique whose mechanism matches the measured error most directly in this parent function, and the smallest change: two devices driven by clocks that already exist. Its known limitation: the textbook half-size dummy assumes that half of each main device's channel charge flows toward `Cs`. The actual split depends on the impedances at both terminals and on the clock edge rate (Wegmann et al. 1987; Eichenberger and Guggenbühl 1990). Here one terminal is the closed-loop driver output, whose impedance rises with frequency, and the edges are 0.2 ns, so the split need not be equal; the level-dependent timing of the main and dummy devices during the simultaneous edges can also leave a residual. The study does not adjust the dummy size or the clock timing to reduce that residual.

## Circuit of the design response

The chosen gate (NMOS 3 × 5 µm, PMOS 6 × 5 µm, L = 0.15 µm) plus, on the `Cs` side:

- dummy NMOS `nfet_01v8`, 3 × 2.5 µm (7.5 µm), L = 0.15 µm, drain and source at the sampling node, gate on the PMOS clock `phib`, bulk at 0 V;
- dummy PMOS `pfet_01v8`, 6 × 2.5 µm (15 µm), L = 0.15 µm, drain and source at the sampling node, gate on the NMOS clock `phi`, bulk at 1.8 V.

Each dummy turns on when its main device turns off, with the same simultaneous complementary 0.2 ns edges. Benches: `tb_t5_connected_dummy.spice` (as test (c)) and `tb_t6_hold_dummy.spice` (as the hold-step bench).

## Cases

1. **Held-sample check** (`DESIGN_BRIEF.md` Section 6) at seven levels, `V` ∈ {0.6, 0.7, …, 1.2} V, zero step, for the chosen gate and for the gate with dummies. The gate closes at 25 ns and opens at 65 ns.
2. **Acquisition settling with dummies**: test (c) over the nine representative operating points.
3. **Extended width ladder**: the held-sample check at the same seven levels for gates of one eighth (3 × 0.625 µm / 6 × 0.625 µm), one quarter (3 × 1.25 / 6 × 1.25 µm), one half, and double the chosen width; test (c) for the eighth and quarter gates at three operating points, the two full-scale transitions and the 0.9 V zero step (half and double were run in the switch-width study). These are the existing width ladder extended downward until the hand trend of the turn-off error (proportional to width) would fall below its share.

`tt`, 27 °C; same simulation settings as the existing tests.

## Metrics

For each gate variant and level: `Vbefore` = mean `Vsamp` over 63.0–64.8 ns; `Vafter` = mean over 75–85 ns.

- hold step `P(V) = Vafter − Vbefore`; pre-opening error `S(V) = Vbefore − V`; held-sample error `E(V) = Vafter − V = S + P`;
- for each of `P`, `S`, `E`: the residual after the two-point correction through 0.6 V and 1.2 V, and its largest magnitude over the seven levels;
- offset and gain parts of `P` (its value at 0.6 V and the slope of the correction line), reported only;
- acquisition: last crossing of ε and error at 40 ns per operating point; turn-on excursion at the driver output at the zero-step points.

## Readings (acceptance criteria of this study)

- **Held-sample check (zero step).** PASS if `max |R_E| ≤ ½ VLSB` (0.293 mV). Reported for the chosen gate and for the gate with dummies. `R_E = R_S + R_P`: the components add with sign. A variant whose `max |R_E|` alone exceeds ±1 `VLSB` fails the parent requirement under the tested conditions.
- **Turn-off component.** `max |R_P|` against its ¼ `VLSB` share (0.15 mV).
- **Pre-opening component.** `max |R_S|` against its ¼ `VLSB` share. The DC bring-up already shows a level-dependent tracking error of the driver of about 0.33 mV at 0.7 V relative to the line through its values at 0.6 V and 1.2 V. That is above its share and above the whole ½ `VLSB` remainder, so the held-sample check can pass only if the turn-off component happens to cancel part of it. The design response is therefore judged on the turn-off component; the check on the total is reported beside it.
- **Outcome of the design response** (gate with dummies, against the chosen gate):
  - **A:** turn-off component ≤ 0.15 mV and every operating point still meets ε at 40 ns: the switch's share of the budget is closed.
  - **B:** turn-off component reduced by at least a factor of two, but above 0.15 mV, with acquisition still passing.
  - **C:** reduced by less than a factor of two, or acquisition no longer passes.
- **Extended width ladder.** Plot, for each width, the worst connected last crossing at the three points against the turn-off component. Report whether any width in the ladder meets both ε at 40 ns at those points and the 0.15 mV turn-off share.

Whatever the outcome, it is reported. No second remedy is tried in this study.

## References

- Eichenberger, C.; Guggenbühl, W. (1990). On charge injection in analog MOS switches and dummy switch compensation techniques. *IEEE Transactions on Circuits and Systems*, 37(2), 256–264. https://doi.org/10.1109/31.45719
- Carusone, T. C.; Johns, D. A.; Martin, K. W. (2012). *Analog Integrated Circuit Design*, 2nd ed. Wiley.
- Razavi, B. (2017). *Design of Analog CMOS Integrated Circuits*, 2nd ed. McGraw-Hill.
- Wegmann, G.; Vittoz, E. A.; Rahali, F. (1987). Charge injection in analog MOS switches. *IEEE Journal of Solid-State Circuits*, 22(6), 1091–1097. https://doi.org/10.1109/JSSC.1987.1052859

---

## Result (2026-10-30 JST)

Script: `run_followup.py`; data: `results/data/sky130_followup_summary.json` (`held_sample`); figure: `results/figures/figure_sky130_held_sample.png`. `VLSB` = 0.586 mV, share ¼ `VLSB` = 0.146 mV, remainder ½ `VLSB` = 0.293 mV.

| Gate | max. on-resistance | hold step at 0.6 / 0.9 / 1.2 V (mV) | turn-off component, largest `R_P` | pre-opening, largest `R_S` | held-sample, largest `R_E` | zero-step check | worst connected last crossing over the evaluated points |
|---|---:|---|---:|---:|---:|---|---:|
| chosen, 15 / 30 µm | 744 Ω | −7.79 / −2.14 / +5.01 | 0.83 mV | 0.33 mV | 0.64 mV | **FAIL** | 29.7 ns |
| chosen + half-size dummies | 744 Ω | −1.56 / −0.33 / +0.54 | 0.46 mV | 0.33 mV | 0.78 mV | **FAIL** | 29.9 ns |
| one eighth, 1.9 / 3.8 µm | 5.2 kΩ | −0.76 / −0.09 / +0.75 | 0.09 mV | 0.33 mV | 0.27 mV | PASS | 32.2 ns |
| one quarter, 3.8 / 7.5 µm | 2.9 kΩ | −1.61 / −0.32 / +1.37 | 0.20 mV | 0.33 mV | 0.23 mV | PASS | 30.8 ns |
| half, 7.5 / 15 µm | 1.4 kΩ | −3.55 / −0.90 / +2.53 | 0.38 mV | 0.33 mV | 0.19 mV | PASS | 30.0 ns (three points) |
| double, 30 / 60 µm | 372 Ω | −16.07 / −4.22 / +10.76 | 1.91 mV | 0.33 mV | 1.73 mV | FAIL | 29.9 ns (three points) |

Every variant meets ε at 40 ns at every evaluated point. For the half and double gates the acquisition values are those of the switch-width study (three points). For the eighth and quarter gates, six additional operating points were run after the initial three-point result, as a check of the narrow candidates, and all pass. The on-resistance of the eighth and quarter gates (`tb_switch_ron_narrow.spice`) was also measured after that result.

**Held-sample check, chosen gate: FAIL.** Acquisition settling passes, but the hold step `P` runs from −7.8 to +5.0 mV (up to 13 `VLSB`), and the total held-sample error `E = S + P` from −7.4 to +5.0 mV. After the two-point correction removes the offset of `E` (−7.4 mV at 0.6 V) and its gain error (20.7 mV/V), the level-dependent residual `R_E` is still 0.64 mV, more than the whole ±1 `VLSB` on its own: the chosen gate fails the parent requirement under the tested `tt` zero-step conditions. The turn-off component, max |`R_P`| = 0.83 mV at 1.0 V, is 5.7 times its share; the pre-opening component, max |`R_S`| = 0.33 mV, peaks at 0.7 V. From 0.7 to 1.1 V the two have opposite signs and partly cancel (at 1.0 V, +0.18 − 0.83 = −0.64 mV), which is why `R_E` is smaller than `R_P`.

**Design response, dummy-switch compensation: outcome C** by the criterion of this study. The uncorrected hold step `P` falls about fivefold (largest magnitude 7.8 → 1.6 mV; offset of `P` −7.8 → −1.6 mV; gain error of `P` 21 → 3.5 mV/V). The level-dependent turn-off component falls only by a factor of 1.8 (0.83 → 0.46 mV); the remaining corrected turn-off error is concentrated in the lower part of the range, with the largest residual, +0.46 mV, at 0.8 V. Acquisition settling is unchanged at the transitions (worst 29.9 ns), and the zero-step turn-on settling is shorter (5.3–8.9 ns instead of 7.5–10.3 ns). The held-sample residual gets worse (0.64 → 0.78 mV): in the chosen gate the negative turn-off residual partly cancelled the driver's positive static residual; with dummies the turn-off residual is positive from 0.7 to 0.9 V and adds to it. *Interpretation:* consistent with imperfect compensation caused by effects such as unequal charge partition and level-dependent timing of the main and dummy devices; these contributions were not separated.

**Extended width ladder.** The turn-off component scales almost exactly with width (0.09, 0.20, 0.38, 0.83, 1.91 mV), while the worst connected acquisition over the evaluated points moves only between 29.7 and 32.2 ns from one eighth to double width. The one-eighth gate meets ε at 40 ns at all nine points and is the only width meeting the turn-off share. Its maximum on-resistance, 5.2 kΩ, is five times the 1 kΩ switch allocation of the brief. The total zero-step residual `R_E` ranks the widths differently: half 0.19 mV, quarter 0.23 mV, one eighth 0.27 mV. *Interpretation:* for this fixed driver at `tt`, acquisition settling is weakly sensitive to switch width over the studied ladder, while the turn-off residual scales strongly with width; the 1 kΩ local allocation, from a linear time-constant budget, was therefore more restrictive than this driver's measured acquisition required. A faster driver could make the switch resistance important again. The two rankings differ because the parent metric is a signed sum: optimizing a local error allocation and optimizing the parent signed error are not necessarily the same problem.

**What remains.** The pre-opening component, 0.33 mV for every gate, is the driver's static tracking error and is above its ¼ `VLSB` share. The narrow gates pass the zero-step check only because their turn-off residual has the opposite sign to the driver's residual and partly cancels it; the one-eighth gate passes with 0.27 mV against the 0.293 mV sub-allocation. For the narrow gates the parent requirement is not demonstrated for every previous sample: at 40 ns their measured acquisition residual is at most 0.04 mV at the evaluated points, small enough that treating the turn-off component as primarily a function of the held level gives a parent-error estimate within the stated limit (at most about 0.31 mV against ±0.586 mV), but transition-then-open cases, continuous coverage of the range, and corners were not simulated. No final width is selected: the narrow widths are `tt`, 27 °C only; the driver's tracking error exceeds its share; mismatch, temperature, and extraction are not covered; and cancellation affects the parent metric. The demonstrated need is a driver revision that reduces the measured level-dependent tracking error, or a different budget split; the specific circuit remedy was not studied.
