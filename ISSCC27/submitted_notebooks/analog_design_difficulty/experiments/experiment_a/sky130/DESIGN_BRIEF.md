# Design brief and experiment definition — SKY130 sample-and-hold front end

Date: 2026-10-30 JST

This is the authoritative definition of the SKY130 experiment: the function the circuit serves, its accuracy requirement and error budget, the circuit, the operating points, the tests, the metrics, and how each result is read. The run conditions of the acquisition tests (range, ε, `Tacq`, `Cs`, switch, clock, operating points, tests, metrics) are the ones used by every acquisition result; this document also states the function they serve. Two follow-up studies are defined in their own records: `SMALL_STEP_PORT_COMPARISON.md` and `HOLD_ERROR_DESIGN_RESPONSE.md`. The switch-width study is defined in `SWITCH_WIDTH_STUDY.md`. Results: `RESULTS.md`.

Each item is labelled **teaching assumption** (a stated choice), **derived** (follows by calculation), **engineering choice**, or **measured** (simulated here).

## 1. Parent function

A **single-ended sample-and-hold front end** that must preserve an input between 0.6 V and 1.2 V with **10-bit-equivalent accuracy** for a downstream consumer. The studied circuit is

```
closed-loop driver → sampling switch → hold capacitor Cs → high-impedance downstream observation of the held voltage
```

During acquisition the switch is closed and the driver charges `Cs` toward the input. When the switch opens, the voltage left on `Cs` is the held sample, and the downstream consumer reads it without loading it. The consumer is not modelled; it could be a comparator, a converter stage, or a buffer with a high-impedance input. *10-bit-equivalent* is this experiment's engineering definition: after a two-point offset and gain correction, the deterministic held-sample error stays within ±1 `VLSB`, one part in 1024 of the input span (Section 2). Random noise has a separate entry. This notebook does not implement an analog-to-digital converter.

**Relationship to SAR converters.** Many charge-redistribution SAR ADCs sample the analog input onto a capacitor array (the CDAC) during acquisition (McCreary and Gray 1975). From the external driver's side, such an input is a switched-capacitor load: a sampling switch with its resistance and a sampling capacitance, which draws a charge kickback when it connects and must be charged within the acquisition interval (Pachchigar 2017). A SAR input is therefore one practical example of a switched-capacitor load of the kind studied here. The single `Cs` of this experiment is a deliberately simple sample-and-hold capacitance, not a transistor-level implementation of a SAR CDAC, and no converter timing is used to derive any number below.

## 2. Accuracy requirement and error budget

| Quantity | Value | Kind |
|---|---|---|
| input span | `Vrange` = 1.2 V − 0.6 V = 0.6 V | teaching assumption |
| 10-bit-equivalent step | `VLSB` = 0.6 V / 1024 ≈ 0.586 mV | derived |
| held-sample accuracy | the deterministic held-sample error that a two-point offset and gain correction at the range ends cannot remove stays within ±1 `VLSB` (±0.59 mV), for every input and previous sample in the range; random noise (kT/C) is a separate entry | teaching assumption (engineering definition of this experiment) |

The separation of terminal-based offset and gain is borrowed by analogy from ADC terminology: IEEE Std 1241 defines terminal-based gain and offset as the values that make the deviations zero at the end points, and integral nonlinearity as the deviation that remains after correcting for gain and offset (IEEE 2011). The ±1 `VLSB` held-sample criterion is this experiment's own engineering definition, and its dependence on the previous sample is a dynamic, memory effect; neither is called IEEE integral nonlinearity here. A constant or proportional error can be removed by a downstream calibration; an error that depends on the level in another way, or on the previous sample, cannot.

**Error budget.** The held-sample error has several entries. They act at different moments of the sampling cycle and have different remedies.

| Entry | Allocation | Status in this experiment |
|---|---|---|
| acquisition settling: error at the end of `Tacq`, relative to the driver's settled output, for every target and previous sample | **ε = 0.29 mV**, an engineering allocation of approximately one half of the 0.586 mV step | evaluated by tests (a), (b), (c) |
| level-dependent error present with no transition (switch turn-off, driver static tracking, other deterministic effects) | the remaining **½ `VLSB` = 0.293 mV** | evaluated by the held-sample check (Section 6) |
| — of which the switch turn-off error (diagnostic share) | ¼ `VLSB` ≈ 0.15 mV | hold-step measurement |
| — of which the driver's static tracking and everything else (diagnostic share) | ¼ `VLSB` ≈ 0.15 mV | DC tracking measurement |
| sampled thermal noise | kT/C ≈ 64 µV rms at 1 pF, 300 K (0.11 `VLSB` rms) | derived; random, separate noise entry |
| offset and gain error | specified separately; removed by the two-point correction | measured and reported, not pass/fail |

ε is an engineering allocation inside the held-sample budget, not the whole accuracy requirement. Meeting ε closes one entry. The parent requirement is met only if the held sample, after acquisition **and** after the switch opens, is accurate enough.

**Hand estimate of the turn-off error.** The turn-off error was expected to be large. The channel charge of the 15 µm NMOS device is roughly `W L Cox (VDD − V − Vt)` ≈ 2.25 µm² × 8 fF/µm² × 0.7 V ≈ 13 fC near 0.6 V. If about half of it reaches 1 pF, the held voltage moves by several mV, an order of magnitude above both ε and `VLSB`. The PMOS device contributes charge of the opposite sign, which rises with level, so the error also depends on the level. A transmission gate of this size was therefore not expected to meet a 10-bit-equivalent held-sample requirement without a turn-off remedy. The experiment quantifies the error, and the engineer decides which kind of revision it needs.

## 3. Timing

| Item | Value | Kind |
|---|---|---|
| acquisition allocation | `Tacq` = 40 ns | teaching assumption: for example 40 % of a 100 ns sampling period, the rest being the hold and readout phase of the front end |
| settling depth | 0.6 V / ε ≈ 2070, ln 2070 ≈ 7.6 time constants of linear settling | derived; fewer if part of the transition is slew-limited |
| time-constant budget | 40 ns / 7.6 ≈ 5.3 ns total effective time constant | derived |
| switch allocation | `Ron · Cs` ≲ 1 ns, so `Ron,max` ≲ 1 kΩ over the range at 1 pF | approximate allocation: roughly one fifth of the time-constant budget |

The 40 ns allocation is local to this front end and does not come from any converter's bit-cycle timing.

## 4. Circuit

| Item | Value | Kind |
|---|---|---|
| driver | two-stage Miller amplifier in unity-gain feedback, 130 µA from 1.8 V (`netlists/source_two_stage.spice`; topology and sizing in `DRIVER_DESIGN.md`) | existing design, not resized for this brief |
| switch type | CMOS transmission gate of standard-threshold core devices | engineering choice: an NMOS switch with its gate at 1.8 V has only 0.6 V of gate-source voltage at a 1.2 V level, close to its body-affected threshold |
| switch size | `nfet_01v8` 3 × 5 µm (15 µm), `pfet_01v8` 6 × 5 µm (30 µm), L = 0.15 µm; bulks at 0 V and 1.8 V | engineering choice: the smallest width in 5 µm steps with `Ron,max` ≤ 1 kΩ over 0.6–1.2 V, PMOS twice as wide |
| `Cs` | 1 pF, ideal | teaching assumption |
| clock | complementary gate edges, 0 → 1.8 V on the NMOS gate and 1.8 → 0 V on the PMOS gate, simultaneous 0.2 ns linear ramps | teaching assumption: the edge of a modestly sized clock buffer |
| PVT | `tt`, 27 °C; `ss` and `ff` at 27 °C for the full-scale transitions | teaching scope, not sign-off |

The interface representation of the sampling network used by the driver's block test (b) is: `Cs`; the range of target and previous sample; `Tacq`; and one linear resistance **`R_if` = the chosen gate's maximum DC on-resistance over 0.6–1.2 V at `tt`** (a conservative single value for a settling budget).

## 5. Operating points and tests

Representative operating points: target `Vtarget` ∈ {0.6, 0.9, 1.2} V × previous sample `Vprev` ∈ {0.6, 0.9, 1.2} V. Two full-scale transitions (0.6 → 1.2 and 1.2 → 0.6), four half-scale transitions, three zero-step switching events in which only the switch's turn-on transient acts. They are the edges and midpoint of the range in each dimension, not a continuous sweep. A point is written target/previous.

All transients: event at 25 ns, simulated to 425 ns, maximum time step 20 ps, `reltol` = 1e-4. `Vref` is the settled driver output for the target (mean of the last 20 ns). The settling error is `Vsamp − Vref` (for test (a), `Vout − Vref`).

| Test | Bench | Points | Role |
|---|---|---|---|
| (a) input step, `Cs` hard-wired at the driver output | `tb_t0_command.spice` | the six transitions | block characterization at the external input |
| (b) output-port test: input held at `Vtarget`; `Cs` precharged to `Vprev` and connected through an ideal switch and `R_if` | `tb_t3_interface_model.spice` | all nine | interface-aware block characterization (recovery from the charge kickback of the sampling capacitor) |
| (c) connected test: as (b), but through the transmission gate | `tb_t1_connected.spice` | all nine | composition with the real sampling network |
| (m) matched control for (c): gate closed throughout, `Cs` settled with the driver at `Vprev`, input steps to `Vtarget` | `tb_t2_matched.spice` | the two full-scale transitions | isolates the excitation port |

Supporting measurements:

- **On-resistance.** DC sweep 0.5–1.3 V with both terminals at the level and the gates fully on, for the chosen gate and for half and double width (`tb_switch_ron.spice`). `R_if` is the chosen gate's maximum over 0.6–1.2 V.
- **Driver bring-up.** DC tracking, loop margins with 1 pF and with a light 1 fF load, closed-loop input-to-output response and output impedance (`tb_dc.spice`, `tb_ac.spice`).
- **Numerical-convergence check.** Full-scale (b) and (c) with a 10 ps maximum step, and full-scale (c) with `reltol` = 1e-5. If any last crossing moves by more than 0.2 ns or any error at 40 ns by more than 0.03 mV, the comparison is reconsidered before it is read.
- **Corners.** (a), (b), (c) for the two full-scale transitions at `ss` and `ff`, 27 °C; (b) keeps the `tt` value of `R_if`, as an interface specification would.
- **Hold step.** As (c) with `Vprev = Vtarget`; the gate opens at the end of `Tacq` (65 ns) with the same edges (`tb_t4_hold.spice`). Hold step = mean of `Vsamp` over 75–85 ns minus its mean over 63.0–64.8 ns. Channel charge and clock coupling are not separated.
- **Conditional second-stage variation.** If the full-scale step down in (c) is slower than the step up while the M7 current stays below 1.2 times its bias, (a) and (c) are rerun with the second-stage current doubled (`netlists/source_two_stage_2x.spice`).

## 6. Metrics and readings

**Acquisition settling.** (1) Error at `Tacq` = 40 ns: PASS if `|error| < ε`. (2) The last time `|error| ≥ ε` within 200 ns: the shortest acquisition interval the test supports. (3) Error at 5, 10, 15, 20, 25, 30, 40, 60, 80 ns.

**Representation against connection.** At each point, the last crossings of (b) and (c) agree if they differ by at most 1 ns; otherwise (b) is *optimistic* (earlier) or *conservative* (later).

**Acquisition-time sensitivity: block-PASS / connected-FAIL.** The 40 ns allocation is a teaching value, and another allocation would change which tests pass. At each operating point, `t_b` and `t_c` are the last crossings of ε in (b) and (c): the times after which the error remains within ε. For an acquisition allocation `T`:

- if `t_b < T ≤ t_c`, the interface representation passes and the connected circuit fails: the block test would support a design decision that the connected circuit does not;
- if `t_c < T ≤ t_b`, the representation is conservative: it fails where the connected circuit passes;
- otherwise both agree.

The interval of each kind is reported for every operating point, and for two declared input classes: (i) any previous sample in the range, whose worst case is the maximum over all nine points, and (ii) the zero-step fixture only, in which `Cs` starts exactly at the target; this isolates the switch's turn-on disturbance (a real repeated sample would start with the previous hold error). No single shorter allocation is selected; the interval itself is the result.

**Excitation port.** (m) against (c): the maximum difference of the errors, each normalized to the initial `Cs` error, over 0–40 ns. A difference ≥ 0.10 means that the two ports are not equivalent excitations.

**Held-sample check (zero-step check of the parent requirement).** At the zero-step condition, so that no transition is in progress, the held-sample error is `E(V) = Vheld(V) − V`, where `Vheld` is the mean of `Vsamp` 10–20 ns after the switch opens. The two-point correction removes the straight line through `E(0.6 V)` and `E(1.2 V)`, leaving the residual `R(V)`. The candidate meets this zero-step held-sample check if `max |R(V)|` over the evaluated levels is at most ½ `VLSB` (0.293 mV), so that together with acquisition settling (≤ ε = 0.29 mV, approximately ½ `VLSB`) the deterministic held error stays within ±1 `VLSB`, provided that the turn-off step depends primarily on the held level. The check opens the gate with no transition in progress; opening after a transition is not simulated. A candidate whose residual alone exceeds ±1 `VLSB` fails the parent requirement under the tested conditions, because a zero step belongs to the declared input class. Two diagnostic components are reported beside it: the turn-off component (the residual of the hold step) and the pre-opening component (the residual of `Vsamp − V` just before the switch opens, mainly the driver's static tracking), each against its ¼ `VLSB` share. The levels evaluated are fixed in `HOLD_ERROR_DESIGN_RESPONSE.md`.

Whatever the outcome, it is reported. The driver is not resized.

## References

- IEEE (2011). *IEEE Standard for Terminology and Test Methods for Analog-to-Digital Converters*, IEEE Std 1241-2010 (superseded by IEEE Std 1241-2023). https://doi.org/10.1109/IEEESTD.2011.5692956
- McCreary, J. L.; Gray, P. R. (1975). All-MOS charge redistribution analog-to-digital conversion techniques — Part I. *IEEE Journal of Solid-State Circuits*, 10(6), 371–379. https://doi.org/10.1109/JSSC.1975.1050629
- Pachchigar, M. (2017). Pin-compatible, high input impedance ADC family enables ease of drive and broadens ADC driver selection. *Analog Dialogue*, Analog Devices.
