# Closure brief — parent requirement, budget, verification, and selection (restart)

Date: 2026-10-31 JST. Status: **pre-registered before any redesign sweep.** This file is the authoritative experiment and
design brief of the restart. It supersedes the acceptance logic of `experiments/experiment_a/sky130/DESIGN_BRIEF.md`
for closure; that brief and its results remain evidence for the Candidate F2 circuit. Results of this brief live in
`results/closure/` and `results/generated/closure/`, never in the F2 files.

Labels: **frozen** (human decision, the frozen project requirements), **declared** (an engineering choice fixed here before
results), **derived**, **diagnostic** (reported, not pass/fail).

Any change to a declared item after results are seen is recorded in the project decision record as a requirement
or verification change, with all affected results re-evaluated.

## 1. Parent function and frozen conditions

Single-ended sample-and-hold front end: `closed-loop driver → sampling network → Cs → high-impedance downstream use`.
1.8 V SKY130 supply family (frozen; 1.8 V core devices, plus a thick-oxide native input pair operated within the same
supply); input range 0.6–1.2 V (frozen); acquisition interval `Tacq` = 40 ns (frozen);
SKY130 + ngspice (frozen).

`VLSB` = 0.6 V / 1024 (derived; computed in code, `VLSB = 0.5859375 mV`).

The parent value ±1 `VLSB` is the same number Candidate F2 used. What the restart changes is the domain over which
it must hold (real repeated samples, the PVT set below, both read windows) and the requirement that one design is
selected and closed. The acquisition error is no longer a separately allocated pass/fail item: it is part of the
held sample measured in the sequential bench.

## 2. Parent metric (PM)

**Clocking (declared).** Sampling period `Ts` = 100 ns: the switch closes at `t_c[k] = k·Ts` and starts to open at
`t_o[k] = t_c[k] + 40 ns`; hold lasts 60 ns. Clock high level = VDD of the PVT condition; complementary gate clocks
with linear edges of 0.2 ns (nominal). F2 used 40 ns as "for example 40 % of a 100 ns period"; the 100 ns period is now
declared.

**Input timing (declared).** The command `u[k+1]` steps (0.5 ns ramp) at `t_o[k] + 1 ns`, i.e. at the start of the hold
of sample k, so the driver re-settles while the switch is off. This exercises hold-mode feedthrough of the next input
into the held sample and the real charge kickback when the switch next closes. *Stress variant* (declared): `u[k+1]`
steps at `t_c[k+1]`, so command settling and kickback share the 40 ns acquisition.

**Held value (declared).** Two read windows, both required:
- early `y_E[k]` = mean of `V(Cs)` over `[t_o + 10 ns, t_o + 20 ns]` (continuity with F2);
- late `y_L[k]` = mean of `V(Cs)` over `[t_c[k+1] − 6 ns, t_c[k+1] − 1 ns]` (latest use before the next acquisition;
  includes droop and feedthrough).
Peak-to-peak of `V(Cs)` in each window is reported (ringing check, diagnostic).

**Error.** `e[k] = y[k] − u[k]`, referred to the command (never to the driver output).

**Two-point correction (declared).** Terminal-based, analogous to the terminal-based gain/offset of IEEE Std 1241; it is
an adaptation to a held-voltage metric, not the standard's INL. Per PVT condition and per window: run same-level repeated
samples at 0.6 V and at 1.2 V; `ē(0.6)`, `ē(1.2)` are the means of the last two of four repeated cycles at each level.
Offset `o = ē(0.6)`, gain error `g = (ē(1.2) − ē(0.6))/0.6 V`. The same line is applied to every sequence, previous
state, and level at that PVT condition. No refit per sequence, history, or direction; no best-fit line.

**Residual.** `r[k] = e[k] − o − g·(u[k] − 0.6 V)` (output-referred; the input-referred value differs by 1/(1+g), below
3 %).

**Start-up.** The transient starts from the DC operating point with the switch closed and the command at the first
level. Cycle 0 is start-up and is excluded; from cycle 1 on, every previous state is a real held sample.

**PASS (parent).** `max |r[k]| ≤ VLSB` over every counted cycle, both windows, every sequence, every condition of the
declared final verification set (Section 5). Max-abs only; no averaging or exclusions other than cycle 0.

**Diagnostic side reports.** Raw `o`, `g` per PVT condition and their spread; the residual if calibration were done once
at `tt`/27 °C/1.8 V (informational, not pass/fail: the declared system calibrates per operating condition).

## 3. Provisional error budget (declared; allocations are diagnostic, the parent is pass/fail)

All entries are deterministic level- or history-dependent residuals after the correction of Section 2.

| Entry | Mechanism(s) | Provisional allocation | Rationale |
|---|---|---:|---|
| `R_S` static tracking | driver finite/level-dependent loop gain, CMRR, tail headroom at low input | 0.15 mV (¼ `VLSB`) | F2 measured 0.33 mV: the driver must improve by > 2×; a precision follower can reach this with more loop gain |
| `R_P` turn-off | channel-charge injection and clock feedthrough at opening, level-dependent part | 0.15 mV (¼ `VLSB`) | F2 width ladder: scales with switch width/`Cs`; reachable by sizing or a switch/clock change |
| `R_A` history / acquisition | incomplete settling after the kickback, driver memory (`Cc`, internal nodes) | 0.10 mV | F2 acquisition residual at 40 ns ≤ 0.04 mV at `tt`; slow corners need margin |
| `R_H` hold | droop/leakage and next-input feedthrough through the off switch over the 60 ns hold | 0.10 mV | not measured in F2; estimate 0.5 fF·0.6 V/1 pF ≈ 0.3 mV unless reduced |
| reserve | PVT spread, model and numerical uncertainty | 0.086 mV | remainder |
| **sum** | | **0.586 mV** | |
| random (separate) | kT/C + driver noise, sampled | ≤ 0.25 `VLSB` rms (0.146 mV) | kT/C alone is 64 µV at 1 pF, 300 K, 74 µV at 125 °C |

The allocations are a working split: they tell the designer where to look, not whether the design passes. They are
not four independently measured final components. The final sequential measurement uses corrected residuals `r_S`
immediately before opening, `r_P = r_E − r_S` from pre-opening to early hold, and `r_H = r_L − r_E` from early to
late hold. Thus `r_E = r_S + r_P` and `r_L = r_S + r_P + r_H`. Acquisition/history remaining before opening is
included in `r_S`; its spread across previous states diagnoses history dependence. There is no independently measured
final `r_A`. Final `r_P` includes next-command coupling before early hold. Signed effects may cancel; Section 7 governs
how far a PASS may rely on that.

Margin has a cost: a larger `Cs` reduces `R_P` and kT/C but needs more driver current for the same settling; a wider
switch lowers `Ron` but raises `R_P` and `R_H`; more loop gain costs current, headroom, or compensation. Section 6 makes
those costs part of selection.

## 4. Benches

All sequential benches use `experiments/closure/shbench.py` (no ideal precharge switch).

Level sets: `L7` = {0.6, 0.7, …, 1.2} V; `L13` = 50 mV steps; `L25` = 25 mV steps.

| ID | Sequence (after the start-up cycle) | Counted cycles | Purpose |
|---|---|---:|---|
| Q-cal+alt | 4× 0.6, 4× 1.2, then 0.6 ↔ 1.2 alternating ×12 | 20 | calibration; full-scale accumulation |
| Q-pair | order-2 de Bruijn sequence over `L7` | 49 | every (previous, target) pair at 0.1 V; next-input feedthrough of every pair |
| Q-stair | staircase over `L13`, up then down | 25 | level shape at 50 mV, small steps from both directions |
| Q-mem | order-3 de Bruijn sequence over {0.6, 0.9, 1.2} | 28 | dependence on the sample before the previous one |

Supporting benches: DC tracking sweep, operating-point saturation margins, AC loop gain with the acquisition load
(switch on + `Cs`) and the hold load (switch off), closed-loop peaking, `.noise` (kT/C + driver), and the F2
zero-step hold bench as a mechanism-isolation tool only.

## 5. Verification sets

**Screening set (candidates).** Q-cal+alt, Q-pair at 7 PVT points: `tt`/1.80/27; `ss`/1.62/−40; `ff`/1.98/125;
`sf`/1.62/−40; `fs`/1.62/−40; `sf`/1.98/125; `fs`/1.98/125; plus any condition flagged worst by the cheap all-condition
sweeps (DC tracking, AC, zero-step hold over all 45 conditions). A candidate advances to final verification only with
`max|r| ≤ 0.85 VLSB` on the screening set (selection guard band; the parent limit stays 1 `VLSB`).

**Final verification set (declared).** Process {`tt`, `ss`, `ff`, `sf`, `fs`} (all MOS corners in the installed
the SKY130 model library) × VDD {1.62, 1.80, 1.98} V × T {−40, 27, 125} °C = 45 conditions, each with all four sequences of
Section 4, primary input timing. No pruning. In addition:
- stress input timing (input change at closure) with Q-pair at `tt`/1.8/27 and at the three worst conditions;
- Q-stair over `L25` at `tt`/1.8/27 and at the three worst conditions (if the max residual differs from `L13` by more
  than 0.03 mV, refine at every condition);
- sensitivities at `tt`/1.8/27 and at the two worst conditions, PASS required: clock edges 0.1 ns and 0.5 ns;
  `phi`/`phib` skew ±50 ps; `Iref` ±20 %; `Cs` ±10 %.

**Not covered (stated limitation unless Section 7 makes it mandatory):** device mismatch (Monte Carlo), layout
extraction, aging, package, silicon, transistor-level clock drivers (the edge/skew sweep stands in for them), PDK R/C
corners (the passives `Rz`, `Cc`, `Cs` are ideal; `Cs` ±10 % covers the dominant one).

## 6. Driver stability and operation (declared criteria, all 45 conditions, levels 0.6/0.9/1.2 V)

- Loop phase margin ≥ 45° and gain margin ≥ 10 dB with both the acquisition load and the hold load.
- No device of the driver in triode at the three levels (`vds − vdsat ≥ 50 mV` for saturated devices); any exception is
  explained by mechanism or fails.
- Transient: no ringing larger than 0.1 `VLSB` peak-to-peak in either read window.

## 7. Cancellation rule (operational)

Technical correction to the interpretation of the existing calculation: at each PVT condition report the final
measured component maxima `max|r_S|`, `max|r_P|`, `max|r_H|` and the parent `max|r|`. Define
`M = max|r_S| + max|r_P| + max|r_H|` and the paired quantity
`Q = max_k(|r_S[k]| + |r_P[k]| + |r_H[k]|)`. Since `Q <= M`, `M <= VLSB` conservatively certifies that a PASS
does not rely on cancellation. `M > VLSB` is inconclusive: paired/pointwise analysis is required before reliance can
be concluded. If that analysis establishes cancellation reliance, the sign relationship must hold over all 45
conditions, edge/skew sensitivity is mandatory, mismatch Monte Carlo is run, and the notebook says so. The saved
`cancellation_reliant` field retains its historical name for compatibility; true only flags a passing case requiring
paired analysis, not demonstrated reliance. No measured quantity or bound calculation is changed.

## 8. Numerical acceptance

On the worst cycle at the worst condition and on the full-scale step at the slowest condition: `tmax` and `reltol`
tightened as in `NUMERICS.md`, `method=gear` vs trapezoidal. Accept if `r` moves by at most 0.02 mV. If the parent
margin at any condition is smaller than the largest observed numerical change, that condition is **unresolved**, not
PASS.

## 9. Selection objective (lexicographic, per ENGINEERING_CLOSURE_REQUIREMENTS §6)

1. Parent closure over the final verification set.
2. Robustness: margin to `VLSB` at the worst condition; no cancellation-reliant PASS without the checks of Section 7.
3. 40 ns acquisition with a stable driver (Section 6); random noise within its budget.
4. Cost: supply current, total device width/area proxy, `Cs`, number of clock phases, device count.
5. Explainability and reproducibility in an open notebook.

Among candidates that pass 1–3 with margin, the cheaper one is preferred even if another has a larger margin.

## 10. Final closure result

Machine-readable `results/closure/final/q1_boot2/final_closure.json` with, per condition: `max|r|` (both windows), `o`, `g`, component
maxima, acquisition residual, read-window ripple, loop phase/gain margin, supply current, and PASS/FAIL; and a reader
matrix (process × VDD × T heat map of `max|r|/VLSB`). A final PASS requires every condition of Section 5 to pass.
*Note (2026-11-01, not an amendment): the design named here, `q1_boot2`, was superseded after the completed A3
check (forward body-source voltage) failed. The selected design is `q1_nvt1`, verified against the same criteria;
its result is `results/closure/final/q1_nvt1/final_closure.json` (same structure), and the reader matrix is drawn as
separate per-condition panels for the residual, noise, and phase margin.*

## Amendments before final verification (2026-10-31, after the independent R3 midpoint audit)

Source: the design-study record. Recorded before any final-verification run; each
is a verification-method or verification-domain correction with a stated public/technical reason, not a response to a
pass/fail result.

**A1 — Supply range.** The declared supply set becomes {1.60, 1.80, 1.95} V (was {1.62, 1.80, 1.98} V). Reason: SkyWater
publishes SKY130 1.8 V MOS model validity for VDS/VGS up to 1.95 V, and the PDK's own 1.8 V standard cells are
characterised at 1.60 V and 1.95 V. ENGINEERING_CLOSURE_REQUIREMENTS §4 allows the ±10 % default to be replaced by a
documented public/technical range. The low end (1.60 V) is harsher than before; the high end stays inside model validity.
Temperatures stay {−40, 27, 125} °C. Screening and stress-extra points are re-mapped to the new supplies.

**A2 — Random-noise requirement and method.** Status: the sampled-noise budget of 0.25 `VLSB` rms (146 µV) is a
pre-registered selection requirement (Section 9 item 3; human direction of 2026-10-31), separate from the deterministic
parent; it is not diagnostic as the Section 3 table wording suggested. Method (`noise.py`): track-mode output-noise PSD on
Cs with the switch on, integrated from 1 mHz (declared lower bound standing in for a calibration interval) to 50 GHz;
the switch is counted as exactly kT/C (the SKY130 MOS noise model gives ≈ 0.81–0.83 kT/C at Vds = 0; its model
contribution, measured with an ideal noiseless driver, is replaced by kT/C). Conditions: all 45 final conditions at
0.6 V and 1.2 V input. PASS: ≤ 146 µV at every point; a result within 3 µV (2 %) of the limit is *unresolved* and does not
count as PASS. Iref and clock noise are not included (stated).

**A3 — Device voltage limits (final design).** Steady state: every device |VGS|, |VGD|, |VDS| ≤ 1.95 V at every final
condition. Transient exceedances above 1.95 V are reported with measured peak and duration. VBS must stay within the model
range (+0.3 to −1.95 V) or the device's body is tied to its source in an isolated p-well (stated as such; the deep-n-well
junction is not modelled). Gate-to-bulk above VDD is accepted only under an inverted channel and is stated as a limitation
(no TDDB/HCI qualification). Checked over all 1.95 V and all 125 °C conditions, both timings, and 0.1 ns edges.
*Implementation note (2026-10-31, bootstrap model-domain investigation): the original assembler evaluated only the
reverse end of the VBS range; the forward end (NMOS +0.3 V, PMOS +0.1 V) is now evaluated at every instant. The
criterion is unchanged. The investigation record (BOOTSTRAP_MODEL_DOMAIN_HANDOFF.md) is kept in the development
repository.*

**A4 — Current.** The 300/450/800 µA figures used during the driver iterations were exploration bounds, not requirements.
Supply current is a selection cost (Section 9 item 4), reported at tt and as the maximum over the final set.

**A5 — Records.** Screening results are labelled with set, sequences, and timing and are never called closure; the
0.85 `VLSB` advancement guard is evaluated explicitly.

## Amendments by human review decision (2026-10-31, after the H1-type stop)

Source: human review decision A (recorded in the project decision record). Recorded before the final bounded
refinement and before any final-verification run. Unchanged: deterministic ±1 `VLSB` parent, repeated-sample sequences,
PVT set (A1), 40 ns acquisition, 0.6–1.2 V range, Cs = 1 pF, driver family limited to the existing z7/A family.

**A6 — STRESS timing becomes a reported diagnostic.** The primary timing (next command applied 1 ns after the switch
opens, i.e. the input changes during the hold) is the final functional timing requirement. The STRESS case (full-scale
command step exactly at switch closure) is run and reported in the final result but is not PASS/FAIL. Reason: the frozen
parent function does not specify a full-scale command transition coincident with switch closure; STRESS was an
additional declared worst-case test, not the parent input model.

**A7 — Random-noise allocation, pre-declared conditional revision.** One final bounded refinement of the z7/A driver
family aims at the declared 0.25 `VLSB` rms (146 µV) under the primary timing. If that refinement still misses 146 µV
(PASS needs ≤ 143 µV under the A2 unresolved band), the separate random-noise allocation is revised once to the 10-bit
quantization-noise-equivalent value `VLSB/√12 ≈ 0.289 VLSB rms ≈ 169.1 µV` (PASS then needs ≤ 166.1 µV). Rationale: a
sampled-noise allocation equal to the quantization noise of the 10-bit-equivalent step is a standard reference point for a
10-bit-equivalent front end; the value is fixed here, not fitted to a candidate, and is not relaxed further.

**A8 — Device terminal voltages.** Bootstrap transient terminal-voltage excursions above 1.95 V are reported as
limitations/diagnostics with peak and duration (A3 measurement unchanged); no transistor reliability sign-off is claimed.

**A9 — Final PASS set and supporting checks (submission-priority decision, 2026-10-31).** Recorded before the final
result was assembled. The final PASS/FAIL set is: all 45 conditions × the four sequences in the primary timing (both
read windows), driver stability, saturation (as a design target with the bounded-corner rule), sampled noise, and the
switch device-voltage checks. The STRESS timing (A6), the 25 mV staircase, the edge/skew/Iref/Cs sensitivities, and the
finer-numerics reruns become supporting checks: run in the background and reported if available, not prerequisites for
the final result. Statements in the notebook about them are generated from whichever of them exist.
