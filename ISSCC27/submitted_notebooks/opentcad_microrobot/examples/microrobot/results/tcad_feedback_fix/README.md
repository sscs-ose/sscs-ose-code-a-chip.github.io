# Independent feedback diagnostics and charge-control attempt

**No startup fix is established.** Exactly two authorized initial runs and one approved CHGTOL control executed. The matching RC charge-control run was skipped because stable failed completion. Simulations stopped; no other input, physics, probe, solver or formulation variant ran.

| Independent run | Last saved time | Completion | Saved finite data | Reported trouble equation | Peak local terminal/solution current discrepancy |
|---|---:|---|---|---|---:|
| RC, CHGTOL 10⁻¹⁴ C |250 µs | complete |80147×28 | none |97.582 pA |
| Stable nonlinear, CHGTOL 10⁻¹⁴ C |60.4060961974 µs | aborted |15883×28 |vp_stable_r#branch |1.31370 pA |
| Stable nonlinear, CHGTOL 10⁻²⁰ C |51.8743846430 µs | aborted |13589×28 |vp_stable_r#branch |0.249444 pA |

Zero simulator exit codes do not override the abort/completion checks. Each first run deletes only the other active copy and its saved vectors from the frozen two-copy bench, retaining names, definitions, physical parameters, all legal series-ammeter probes, replay knots, initialization and options. The charge control changes only CHGTOL 10⁻¹⁴→10⁻²⁰ C; its exact diff is retained. All other effective options remain GEAR2, RELTOL10⁻⁶, ABSTOL10⁻¹⁵ A, TRTOL7 and VNTOL1 µV. Extracted native option blocks confirm this.

RC completes but its saved-current precision is not accepted: terminal-current KCL peaks at 107.630 pA and local terminal/solution discrepancy at 97.582 pA. Stable's initial prefix has KCL 1.271 pA and local discrepancy 1.314 pA. Its charge-controlled prefix has lower reported peaks, 0.3080/0.2494 pA, but ends earlier; this is not a matched-window improvement test. Completion still fails, and the charge-controlled powered-clamp gate is null/untested because logic never reaches 1 V. DD domains pass; prefix current, charge and energy comparisons cannot qualify complete startup. The initial RC/stable powered-clamp peaks are 1.211/1.119 µV. No end-to-end or released-actuation claim follows.

The approved accuracy gates were recorded before the charge-control run: prior benchmark comparisons unchanged; per-interface terminal/solution allowance 5 pA+2% frozen benchmark branch peak, sum-terminal KCL allowance equal to their sum; fixed charge and existing energy/domain/clamp gates. No threshold was relaxed. Stable failed completion, so the matching RC control did not run. Charge-state and signed terminal-work bookkeeping remains numerical-model evidence, not chemical-energy validation.

## Saved-only failure alignment

The source is the completed passive benchmark's actual `time` and `v(logic)` columns, preserved at 17 digits in the local-only logic_history.spice. failure_knot_audit.json records exact rows, names, hashes, neighboring points and offsets. Times below are **last accepted saved times**, not an invented high-precision rejected-step time.

| Run | Nearest original PWL knot | Last accepted time minus knot | Adjacent knot intervals | Adjacent slope change |
|---|---:|---:|---|---:|
| Stable original |60.4060969787 µs |−0.78125 ps |48.828/97.656/195.313/390.625 ps |0.05336 V/s around 32402.7 V/s |
| Stable CHGTOL control |51.8743807367 µs |+3.90625 ps |390.625/781.25/1562.5/3125 ps |0.46742 V/s around 29414.5 V/s |

The original PWL has 14298 knots/14297 intervals: 848 intervals below 1 ns,24 below 10 ps, none below 1 ps; minimum 1.179315 ps and maximum 25 ns. There are 45 strict slope-sign reversals globally. The completed RC run traverses both neighborhoods, with 24/22 saved points there, and includes the exact original stable last-accepted timestamp. These broader controls prevent attributing either failure uniquely to knot density, small slope changes, a particular input event or one equation. No simplifier or changed waveform was implemented.

## Offline scale and circuit inspection

charge_scale_audit.json records maximum adsorption charges: RC working 1.168×10⁻¹⁶ C and return 2.335×10⁻¹⁶ C; corresponding excursions 1.181/2.362×10⁻¹⁶ C. Stable-prefix excursions are 2.453/4.906×10⁻¹⁷ C. Cdl charge excursions are about 8.722×10⁻¹⁶/1.744×10⁻¹⁵ C. The candidate 10⁻²⁰ C control was justified by these scales and 1 pA×25 ns=2.5×10⁻²⁰ C; this is not a direct current-error bound. Accepted-step minima were12.91 fs for completed RC and 0.9766 ps for original stable.

State capacitors are solution-referenced; return Cads 8.125 nF is 8125 times a 1 pF actuator storage capacitor. State nodes have finite Rads or nonzero state-current Jacobian paths; the electrolyte has RF/solution DC paths. No disconnected state node or contradictory ideal-source loop was identified. The return probe is a legal series ammeter and was preserved. These observations motivate further review, not a claimed cause. Astra review was unavailable for new architecture after this approved failed control; no new solver/formulation decision or simulation followed.

One focused deletion-only assembly test passes; Ruff passes. Exact decks, logs, executed initial/control runners, diffs, effective options and source hashes are retained. Waveform-bearing replay and raw data remain local. Prior evidence/defaults are unchanged. No full controller, DD/layout, fine/rescue, publication, submission, push or fabrication action ran.
