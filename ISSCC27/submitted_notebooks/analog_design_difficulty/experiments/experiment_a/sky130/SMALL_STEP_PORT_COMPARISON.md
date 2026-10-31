# Small-step excitation-port comparison — definition

Date: 2026-10-30 JST
Amplitudes, matching, metrics, and readings are defined below and are not adjusted to the results. Conditions not named here are those of `DESIGN_BRIEF.md`.

## Why this study is needed

The full-scale matched comparison, test (c) against test (m), shows that an input step and the connection of a charged `Cs` produce different transients (normalized difference 0.86 and 0.79). In that comparison both excitations are large-signal: a 0.6 V input step slews the first stage (about `Itail/Cc`), and the connection of a capacitor charged 0.6 V away drives the class-A output stage to its supply or sink limit. The reduced-model argument (same closed-loop poles, different numerators of `Gin` and `Zout`) is a linear argument. The full-scale result therefore does not show whether the port difference exists in this circuit when nothing slews.

> **This study exists so that the reader can see whether, in the SKY130 driver, an input step and an output-port disturbance of the same small size still produce different closed-loop transients when neither excitation drives the circuit out of its approximately linear range.**

## Cases

Target `Vtarget` = 0.9 V (the bring-up operating point). Signed step `Δ` ∈ {+10, −10, +20, −20} mV, where `+` means the sampling capacitor starts below the target (the driver supplies charge) and `−` that it starts above (the driver sinks charge). The amplitudes are chosen as small compared with the input pair's overdrive and with the output stage's 100 µA bias, while still about 35 and 70 times ε, so that a scaled settling metric stays well above the simulator's accuracy.

**Primary pair, switch represented by `R_if`** (isolates the excitation port from the switch's nonlinear and switching behaviour):

| Excitation | Bench | Initial state | Event at 25 ns |
|---|---|---|---|
| input step | `tb_s1_input_step_rif.spice` | `Cs` connected to the driver output through `R_if` (743.5 Ω) throughout, settled with the input at `Vtarget − Δ` | input steps to `Vtarget` (0.1 ns ramp) |
| output-port disturbance | `tb_s2_output_port_rif.spice` | input at `Vtarget`, driver settled; `Cs` precharged to `Vtarget − Δ + Voff` | `Cs` is connected through an ideal switch and `R_if` |

`Voff` is the driver's DC tracking error at 0.9 V, taken from the DC bring-up of the same run before the transients (+0.43 mV in the earlier runs). It makes the initial `Cs` error of the output-port case equal to `−Δ` relative to the settled output, as in the input-step case.

**Secondary pair, real transmission gate** (the same steps, for the composition reading below):

| Excitation | Bench | Initial state | Event at 25 ns |
|---|---|---|---|
| input step | `tb_s3_input_step_tg.spice` | chosen gate closed throughout, `Cs` settled with the input at `Vtarget − Δ` | input steps to `Vtarget` |
| connection | `tb_s4_connected_tg.spice` | input at `Vtarget`; `Cs` precharged to `Vtarget − Δ + Voff` | the gate closes (complementary 0.2 ns edges) |

Matching in each pair: same driver and bias, same total capacitance at the sampling node (`Cs` = 1 pF behind the same series element), same initial `Cs` error magnitude, same time axis (0 at the event). `tt`, 27 °C, maximum time step 20 ps, `reltol` = 1e-4, simulated to 225 ns; `Vref` is the mean output over the last 20 ns. Saved: `Vout`, `Vsamp`, node `x`, and the drain currents of M1, M2, M6, M7.

## Metrics

For each waveform, `e_n(t) = (Vsamp(t) − Vref) / (Vsamp(0⁻) − Vref)`, normalized by its own measured initial error; the initial errors of both cases are reported.

1. **Port difference** `D(Δ)` = maximum over 0–40 ns of `|e_n,input(t) − e_n,output(t)|`, and the time of that maximum.
2. **Slewing.** First-stage imbalance `s(t) = |i_M1 − i_M2| / (i_M1 + i_M2)`; its maximum over 0–40 ns. A case *slews* in the first stage if `max s ≥ 0.9`. The output-stage current `i_M6` is reported as its minimum and maximum relative to its value before the event.
3. **Node `x` trajectory.** Maximum of `|x(t) − x(∞)|` over 0–40 ns, and its time.
4. **Scaled settling.** Last time `|e_n| ≥ 0.02` (2 % of the initial error) within 200 ns. The last time `|Vsamp − Vref| ≥ ε` is reported beside it.

## Readings (acceptance criteria of this study)

**Linear-regime conditions.** The steps are treated as approximately linear if (L1) `max s ≤ 0.5` for both excitations, (L2) `i_M6` stays within 0.5 to 2 times its pre-event value, and (L3) for each excitation the normalized waveforms of the four steps agree with each other within 0.05 over 0–40 ns. The amplitudes are not changed if a condition fails; the failure is reported.

**Port claim.**

- If `D ≥ 0.10` at all four steps (the criterion used for the full-scale comparison) and L1–L3 hold, the notebook states that the two ports exercise different closed-loop dynamics in this driver in the approximately linear regime, and compares `D` with the full-scale values. The reduced model's 0.46 is not a quantitative reference: the reduced model is not fitted to this driver and uses a different observable.
- If `D < 0.10` at all four steps, the notebook narrows the transistor-level claim: the large full-scale difference is mainly a large-signal mechanism, and the linear port distinction rests on the reduced-model analysis.
- Otherwise the result is reported step by step as mixed, with the condition that fails.

**Composition reading (secondary).** With the same steps, the last crossings of ε in the output-port case through `R_if` (`t_b`) and in the connected case through the gate (`t_c`) are compared as in `DESIGN_BRIEF.md` Section 6: for an acquisition allocation `T` with `t_b < T ≤ t_c`, the interface representation passes and the connected circuit fails. The port difference of the gate pair is reported descriptively; it includes the gate's turn-on disturbance and is not used for the port claim.

Whatever the outcome, it is reported.

---

## Result (added after the runs, 2026-10-30 JST)

Script: `run_followup.py`; data: `results/data/sky130_followup_summary.json` (`small_step_ports`); figure: `results/figures/figure_sky130_small_step_ports.png`. `Voff` = +0.43 mV; initial `Cs` errors matched within 0.03 mV (−9.987 mV against −10.000 mV, and so on).

| Step | `D`, switch as `R_if` (time) | first-stage imbalance, input step / output port | `i_M6` range / bias | node `x` largest deviation, input step / output port | scaled settling (2 %), input step / output port | `D`, gate pair |
|---|---:|---|---|---|---|---:|
| +10 mV | 0.53 (2.5 ns) | 0.11 / 0.06 | 0.99–1.05 | 2.9 mV at 2.3 ns / 4.2 mV at 0.7 ns | 14.1 / 11.4 ns | 0.56 |
| −10 mV | 0.53 (2.6 ns) | 0.11 / 0.07 | 0.95–1.01 | 2.9 mV at 2.3 ns / 4.3 mV at 0.8 ns | 14.1 / 11.4 ns | 0.58 |
| +20 mV | 0.53 (2.5 ns) | 0.21 / 0.13 | 0.99–1.10 | 5.7 mV at 2.4 ns / 8.4 mV at 0.7 ns | 14.0 / 11.3 ns | 0.56 |
| −20 mV | 0.53 (2.6 ns) | 0.22 / 0.13 | 0.90–1.01 | 5.9 mV at 2.4 ns / 8.8 mV at 0.8 ns | 14.2 / 11.4 ns | 0.56 |

**Linear-regime conditions.** L1 holds (largest imbalance 0.22, far from the 0.9 slewing level); L2 holds (`i_M6` within 0.87–1.10 of its bias in every case); L3 holds (the four normalized waveforms of each excitation agree within 0.010 and 0.012).

**Port claim (reading defined for this study).** `D` ≥ 0.10 at all four steps with L1–L3 holding: the two ports exercise different closed-loop dynamics in this driver in the approximately linear regime. The difference, 0.53, is smaller than the full-scale 0.86 and 0.79, so the full-scale value contains a large-signal contribution on top of a linear port difference that does not depend on amplitude. The reduced model shows analytically that one internal dynamic state is sufficient to make the two ports non-equivalent; this SKY130 driver independently shows the same qualitative phenomenon. Its 0.46 and the 0.53 here are not compared numerically: the reduced model was not fitted to this amplifier and uses different parameters and a different observable. In the linear regime the output-port disturbance reaches node `x` through `Cc` within about 0.7 ns and its normalized error decays faster; the input step moves `x` later (about 2.3 ns) and settles to 2 % about 2.7 ns later.

**Composition reading (secondary).** With 10–20 mV steps the last crossings of ε are 10.7–11.9 ns through `R_if` and 9.7–11.4 ns through the gate: the representation agrees within 1 ns or is slightly conservative, so these steps give no block-PASS / connected-FAIL interval. The interval appears only where almost no charge has to move, in the zero-step fixture of the main grid, in which `Cs` starts exactly at the target.
