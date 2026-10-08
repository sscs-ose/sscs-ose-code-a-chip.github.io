# Subthreshold current-steering VGA core + SPICE-validated gm/ID LUT flow (SKY130)

IEEE SSCS Code-a-Chip, ISSCC 2027. Notebook: `notebook.ipynb`. License: Apache-2.0.

## Summary
A **SPICE-validated $g_m/I_D$ lookup-table flow** for a nine-transistor subthreshold current-steering VGA core
in open SKY130. A LUT evaluator — KCL operating-point solve on interpolated device data with body effect,
plus a full small-signal nodal solve, no SPICE in the loop — predicts gain within **0.31 dB**
and output resistance within **1.2 %** at its calibration point, where the textbook estimate
misses by **22.9 dB** and gets the direction of gain control wrong: the output device is a cascode
on a node the gain control itself modulates. Across 15 SPICE-checked designs spanning
2.5–80 µm widths its error grows to 2.7 dB (SKY130 width binning),
so the flow re-verifies every design it keeps in SPICE. It swept **4,320** candidates under headroom,
current and bandwidth constraints and returns a Pareto front plus two SPICE-verified picks; neither pick dominates the hand-sized baseline:

- **Flow-S** (speed and noise): control range 12.5 dB, max-gain bandwidth 8.7 kHz, integrated input noise 14.8 µV, 5.43 µW; better than the hand-sized baseline on 4 compared metrics (bandwidth at min gain, bandwidth at max gain, integrated noise at max gain, NEF at max gain), worse on 4 (control range, monotonic control range, supply power, output swing at max gain).
- **Flow-R** (range): control range 17.3 dB, max-gain bandwidth 1.9 kHz, integrated input noise 21.5 µV, 2.44 µW; better than the hand-sized baseline on 6 compared metrics (control range, monotonic control range, integrated noise at min gain, integrated noise at max gain, NEF at max gain, supply power), worse on 3 (bandwidth at min gain, bandwidth at max gain, output swing at max gain).
- **Hand-sized baseline:** control range 13.9 dB, max-gain bandwidth 4.8 kHz, integrated input noise 29.1 µV, 3.67 µW.

Flow-S meets 3 of 11 graded targets and Flow-R 2. Every miss is traced to a mechanism
in §9: a structural gain floor, $R_{out}$-shared gain–bandwidth, and flicker noise.

| Evaluator accuracy | Value |
|:--|:--|
| Error vs SPICE at the calibration point (gain / $R_{out}$) | 0.31 dB / 1.2 % |
| Error across the SPICE-checked designs (gain / $R_{out}$) | 2.7 dB / 26 % |
| Textbook-estimate error (gain) | 22.9 dB |
| Candidates swept / feasible / Pareto | 4,320 / 344 / 144 |

| Headline | Baseline (hand) | Flow-S | Flow-R |
|:--|:--:|:--:|:--:|
| Control range, 0–0.3 V / monotonic (dB) | 13.9 / 16.8 | 12.5 / 14.2 | 17.3 / 20.2 |
| $f_{-3dB}$ min / max gain, $C_L$ = 1 pF (kHz) | 11.0 / 4.8 | 17.3 / 8.7 | 6.4 / 1.9 |
| Integrated input noise min / max gain (µV$_{rms}$) | 46.9 / 29.1 | 46.4 / 14.8 | 35.9 / 21.5 |
| Supply current (µA) / power (µW) | 2.04 / 3.67 | 3.01 / 5.43 | 1.35 / 2.44 |


## Specification compliance (tt, 27 °C, 1.8 V, schematic level)

| Parameter | Target | Baseline (hand) | Flow-S | Flow-R | Met S | Met R |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|
| Supply current | ≤ 5 µA | 2.04 µA | 3.01 µA | 1.35 µA | ✅ | ✅ |
| Power | — | 3.67 µW | 5.43 µW | 2.44 µW | — | — |
| Control range, 0 → 0.3 V | ≥ 30 dB | 13.87 dB | 12.50 dB | 17.31 dB | ❌ | ❌ |
| Monotonic control range | ≥ 30 dB | 16.85 dB | 14.16 dB | 20.16 dB | ❌ | ❌ |
| f-3dB, min gain (C_L 1 pF) | ≥ 10 kHz | 11.00 kHz | 17.26 kHz | 6.38 kHz | ✅ | ❌ |
| f-3dB, max gain (C_L 1 pF) | ≥ 10 kHz | 4.82 kHz | 8.71 kHz | 1.88 kHz | ❌ | ❌ |
| Noise @1 kHz, min gain | ≤ 50 nV/√Hz | 563 nV/√Hz | 560 nV/√Hz | 419 nV/√Hz | ❌ | ❌ |
| Noise @1 kHz, max gain | ≤ 50 nV/√Hz | 348 nV/√Hz | 171 nV/√Hz | 247 nV/√Hz | ❌ | ❌ |
| Integrated noise, min gain | ≤ 7 µV | 46.9 µV | 46.4 µV | 35.9 µV | ❌ | ❌ |
| Integrated noise, max gain | ≤ 7 µV | 29.1 µV | 14.8 µV | 21.5 µV | ❌ | ❌ |
| NEF, max gain | ≤ 5 | 11.3 | 7.0 | 6.8 | ❌ | ❌ |
| Output swing at THD ≤ 1 %, min gain | report | 34 mV pk | 20 mV pk | 24 mV pk | — | — |
| Output swing at THD ≤ 1 %, max gain | report | 54 mV pk | 38 mV pk | 37 mV pk | — | — |
| Input dynamic range, max gain | report | 4.1 dB | 8.6 dB | -1.0 dB | — | — |
| Min device V_DS, both endpoints | ≥ 130 mV | 165 mV | 157 mV | 156 mV | ✅ | ✅ |

## Device sizes (W / L in µm) and bias

| Device group | Baseline (hand) | Flow-S | Flow-R |
|:--|:--:|:--:|:--:|
| M2, M3 (input pair) | 20 / 1 | 80 / 2 | 20 / 2 |
| M6–M9 (steering) | 5 / 1 | 2.5 / 1 | 10 / 1 |
| M1, M4 (PMOS mirror) | 5 / 1 | 10 / 1 | 10 / 2 |
| M5 (tail) | 5 / 1 | 5 / 1 | 5 / 1 |
| V_bias (V) | 0.61 | 0.63 | 0.59 |
| steering common mode (V) | 1.15 | 1.20 | 1.10 |

## Reproduce
* Tier 1 (Python only, < 1 min): `pip install numpy scipy pandas matplotlib jupyter`, open `notebook.ipynb`, Run All.
* Tier 2/3 (IIC-OSIC-TOOLS container): set `RERUN_SPICE`, `REBUILD_LUT`, `RERUN_SWEEP` to `True` in §2 and Run All,
  or run `python tools/run_nb.py --mode full`.

## Layout
`scripts/` holds all simulation logic; `cache/` the characterisation table, sweep and every simulation result;
`images/` every figure.
