# Switch-width study

Date: 2026-10-30 JST. The definition is followed by the result.

## Why

The width of the transmission gate is the notebook's example of one design variable acting on several requirements. Two sides were measured by the supporting measurements of `DESIGN_BRIEF.md`: the DC on-resistance falls as the width grows, and the hold step at turn-off grows with it. The third side was not: whether a lower on-resistance actually shortens the connected acquisition settling, and how the turn-on disturbance changes with width. A hand estimate suggested that the driver dominates (`Ron,max · Cs` ≈ 0.7 ns for the chosen gate against connected settling of 20–30 ns), but the width also scales the gate capacitances through which the clock edges couple at turn-on.

> This study exists so that the reader can see whether, in this sample-and-hold circuit, widening the sampling switch shortens the acquisition settling that its lower on-resistance is meant to improve, and what it does to the turn-on disturbance, beside the increase of the turn-off hold step.

## Definition

Test (c), unchanged except for the gate size:

| Gate | NMOS (`nfet_01v8`, L = 0.15 µm) | PMOS (`pfet_01v8`, L = 0.15 µm) |
|---|---|---|
| half | 3 × 2.5 µm (7.5 µm) | 6 × 2.5 µm (15 µm) |
| chosen | 3 × 5 µm (15 µm) | 6 × 5 µm (30 µm) |
| double | 6 × 5 µm (30 µm) | 12 × 5 µm (60 µm) |

Points (target/previous): 1.2/0.6 and 0.6/1.2 (full scale) and 0.9/0.9 (zero step, turn-on disturbance only). `tt`, 27 °C; the same clock edges and simulation settings as test (c).

Metrics: last time `|Vsamp − Vref| ≥ ε`; error at 40 ns; extreme of `Vout − Vref` in the first nanosecond (turn-on excursion at the driver output).

Readings:

- **Settling side.** Let `T_fs` be the later of the two full-scale last crossings. If `T_fs` of the half and double gates differs from the chosen gate's by less than 1 ns, the worst-case acquisition settling over this range of widths is set mainly by the driver. Otherwise the direction and size of the change are reported.
- **Turn-on side.** If the zero-step last crossing and the turn-on excursion both grow with width, widening the gate increases the turn-on part of the acquisition error while it lowers the on-resistance.
- PASS or FAIL at 40 ns is reported for every case.

## Result

Data: `results/data/sky130_summary.json` (`switch_width`); figure: `results/figures/figure_sky130_switch_width.png`.

| Gate | max. on-resistance | full-scale down / up, last crossing | zero step at 0.9 V, last crossing | turn-on excursion at 0.9 V |
|---|---:|---:|---:|---:|
| half | 1.44 kΩ | 30.0 / 21.3 ns | 0.8 ns | +7.1 mV |
| chosen | 744 Ω | 29.7 / 19.3 ns | 7.5 ns | +14.2 mV |
| double | 372 Ω | 29.9 / 19.1 ns | 8.8 ns | +26.1 mV |

**Settling side:** `T_fs` changes by +0.28 ns (half) and +0.18 ns (double): over this range the worst-case acquisition settling is set by this driver. **Turn-on side:** both the zero-step settling and the excursion grow with width. Every case passes at 40 ns.

The held-sample study (`HOLD_ERROR_DESIGN_RESPONSE.md`) extends this ladder downward to one quarter and one eighth of the chosen width and measures the turn-off error at seven levels.
