# Subthreshold current-steering VGA core + SPICE-validated gm/ID LUT flow (SKY130)

IEEE SSCS Code-a-Chip, ISSCC 2027. Notebook: `notebook.ipynb`. License: Apache-2.0.

## Summary
A **SPICE-validated $g_m/I_D$ lookup-table flow** for a nine-transistor subthreshold current-steering VGA core
in open SKY130. A LUT evaluator — KCL operating-point solve on interpolated device data with body effect,
plus a full small-signal nodal solve, no SPICE in the loop — predicts gain within **0.31 dB**
and output resistance within **1.2 %** at its calibration point, where the textbook estimate
misses by **22.9 dB** and gets the direction of gain control wrong: the output device is a cascode
on a node the gain control itself modulates. Across 12 SPICE-checked Pareto designs spanning
2.5–80 µm widths its error grows to 2.8 dB (SKY130 width binning), so the flow re-verifies every
kept design in SPICE. It swept **4,320** candidates under headroom, current and bandwidth constraints.
With no loss of control range (Rule B) it raised maximum-gain bandwidth from **4.8 to 3.7 kHz**
and cut integrated input noise from **29.1 to 34.9 µV** at 5.36 µW.
It meets 3 of 11 targets; the misses (Control range, 0 → 0.3 V, Monotonic control range, f-3dB, max gain (C_L 1 pF), Noise @1 kHz, min gain, Noise @1 kHz, max gain, Integrated noise, min gain, Integrated noise, max gain, NEF, max gain) are each traced to a mechanism
in §9 — chiefly a structural gain floor, $R_{out}$-shared gain–bandwidth, and flicker noise.

| Headline | Value |
|:--|:--|
| Evaluator error vs SPICE at calibration point (gain / $R_{out}$) | 0.31 dB / 1.2 % |
| Evaluator error across SPICE-checked front (gain / $R_{out}$) | 2.8 dB / 26 % |
| Textbook-estimate error (gain) | 22.9 dB |
| Candidates swept / feasible / Pareto | 4,320 / 771 / 220 |
| Rule B: control range (0–0.3 V / monotonic) | 17.4 / 20.5 dB |
| Rule B: supply current / power | 2.98 µA / 5.36 µW |
| Rule B: $f_{-3dB}$ min / max gain ($C_L$ = 1 pF) | 12.9 / 3.7 kHz |
| Rule B: integrated input noise min / max gain | 44.8 / 34.9 µV$_{rms}$ |


## Specification compliance (tt, 27 °C, 1.8 V, schematic level)

| Parameter | Target | Baseline (hand) | Rule B (no regression) | Met B |
|:--|:--:|:--:|:--:|:--:|
| Supply current | ≤ 5 µA | 2.04 µA | 2.98 µA | ✅ |
| Power | — | 3.67 µW | 5.36 µW | — |
| Control range, 0 → 0.3 V | ≥ 30 dB | 13.87 dB | 17.44 dB | ❌ |
| Monotonic control range | ≥ 30 dB | 16.85 dB | 20.51 dB | ❌ |
| f-3dB, min gain (C_L 1 pF) | ≥ 10 kHz | 11.00 kHz | 12.93 kHz | ✅ |
| f-3dB, max gain (C_L 1 pF) | ≥ 10 kHz | 4.82 kHz | 3.75 kHz | ❌ |
| Noise @1 kHz, min gain | ≤ 50 nV/√Hz | 563 nV/√Hz | 538 nV/√Hz | ❌ |
| Noise @1 kHz, max gain | ≤ 50 nV/√Hz | 348 nV/√Hz | 421 nV/√Hz | ❌ |
| Integrated noise, min gain | ≤ 7 µV | 46.9 µV | 44.8 µV | ❌ |
| Integrated noise, max gain | ≤ 7 µV | 29.1 µV | 34.9 µV | ❌ |
| NEF, max gain | ≤ 5 | 11.3 | 16.4 | ❌ |
| Output swing at THD ≤ 1 %, min gain | report | 20 mV pk | 20 mV pk | — |
| Output swing at THD ≤ 1 %, max gain | report | 50 mV pk | 20 mV pk | — |
| Input dynamic range, max gain | report | 3.5 dB | -10.9 dB | — |
| Min device V_DS, both endpoints | ≥ 130 mV | 165 mV | 153 mV | ✅ |

## Reproduce
* Tier 1 (Python only, < 1 min): `pip install numpy scipy pandas matplotlib jupyter`, open `notebook.ipynb`, Run All.
* Tier 2/3 (IIC-OSIC-TOOLS container): set `RERUN_SPICE`, `REBUILD_LUT`, `RERUN_SWEEP` to `True` in §2 and Run All.

## Layout
`scripts/` holds all simulation logic; `cache/` the characterisation table, sweep and every simulation result;
`images/` every figure.
