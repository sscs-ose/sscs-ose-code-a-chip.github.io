# A Sub-8 µA Capacitor-less LDO with Class-AB Current-Buffer Transient Enhancement and a ZTC-Biased Hysteretic Power-On-Reset for RF/NFC-Harvested IoT Sensor Tags (SKY130)

**IEEE SSCS Code-a-Chip, ISSCC 2027 submission**

| Name | Affiliation | IEEE Member | SSCS Member | Email |
|---|---|---|---|---|
| Poggy Macello Gultom | Institut Teknologi Bandung (ITB), Indonesia | No | No | gultompoggy@gmail.com |

## Summary

Battery-less sensor tags powered by NFC/RF energy harvesting run from a small storage capacitor whose voltage is
unregulated (1.8–3.3 V) and changes with the harvested power. This project designs, at transistor level in the open-source
**SkyWater SKY130** PDK, the two analog blocks such a tag needs:

* a **capacitor-less LDO** (VIN 1.8–3.3 V → VOUT 1.2 V, 0–1 mA, ≈ 7.4 µA quiescent current for the LDO alone, stable
  with 10–100 pF on-chip load capacitance, all thick-oxide `g5v0d10v5` devices). The "sub-8 µA" in the title is this
  LDO-alone figure from the schematic-level design. With the transistor-level bandgap and the POR (v3, after layout), the
  whole block draws 7.2 µA at tt / 27 °C and up to 12.9 µA at the cold corners. The pass gate is driven through a **class-AB common-gate
  current-buffer coupling path** (Ahuja-type compensation). This path gives the gate a coupling gain > 1 during fast load steps,
  which a passive Miller capacitor cannot provide. The same path carries a supply feed-forward that improves mid-band PSRR.
* a **hysteretic power-on-reset** whose threshold detector is biased at the MOSFET **zero-temperature-coefficient** point,
  so the release threshold (≈ 2.0 V) stays almost flat over −40…125 °C without a voltage reference. The LDO regulates
  from VIN = 1.8 V, but the core is held in reset until VIN passes the POR threshold (1.89–2.19 V over PVT after layout).

The notebook covers the full flow. It generates gm/Id lookup tables from the PDK, sizes the circuit by hand from them, generates
netlists from Python, and verifies the design with ngspice: DC, loop gain plus small-step damping, PSRR, load/line transients,
POR thresholds, harvester burst-mode start-up, PVT corners (5 corners × 3 temperatures × 3 supplies), 200-sample Monte Carlo,
and an automatic device voltage-stress check. It also documents the design iteration. The first version (plain Miller compensation,
`P_V1`) failed the 100 ns load-step spec, and the notebook explains why re-sizing could not fix it and compares v1 and v2 for every
affected spec.

## Key results (from the saved notebook run: schematic level, ideal VREF; post-layout results with the real bandgap are in the v3 section below)

| Parameter | Target | v1 (before) | v2 (this design) | Status |
|---|---|---|---|---|
| Load step 0↔1 mA, 100 ns edges, PVT worst | ≤ 300 mV | 398 mV | **266 mV** | PASS |
| Load step 0↔1 mA, 100 ns edges, tt | ≤ 300 mV | −313 / +264 mV | −188 / +122 mV | PASS |
| Load step 0↔1 mA, 1 µs edges, PVT worst | ≤ 300 mV | 295 mV | 133 mV | PASS |
| PSRR, worst in 100 kHz–1 MHz (tt) | improve | −0.4 dB | 8.7 dB (847 kHz: 11.4 dB) | improved |
| PSRR @ 1 kHz (PVT, 0 and 1 mA) | ≥ 30 dB | 22.5 dB | 34.6 dB | PASS |
| Quiescent current (LDO, PVT max) | ≤ 10 µA | 8.72 µA | 7.54 µA | PASS |
| Stability (PVT, 0–1 mA, 10–100 pF) | PM ≥ 45° | 63° (loop gain) | ≥ 96° loop-gain PM; small-step overshoot ≤ 17 % (≈ 51° equivalent) | PASS |
| VOUT accuracy (PVT + 3σ MC, ideal VREF) | ± 3 % | ± 1.33 % | ± 1.77 % | PASS |
| Dropout @ 1 mA (tt) | ≤ 400 mV | 339 mV | 378 mV | PASS |
| Line / load regulation | ≤ 5 mV/V, ≤ 5 mV/mA | 0.19 / 0.36 | 1.60 / 2.43 | PASS |
| Line step 2↔3 V in 10 µs | ≤ 100 mV | ±54 mV | ±12 mV | PASS |
| Transient FoM (Hazucha) | lower is better | 266 ps | 139 ps | — |
| LDO MIM area | — | 4,900 µm² | 8,460 µm² | — |
| POR V_on (PVT) / hysteresis | 2.0 V ± 10 % / ≥ 150 mV | 1.89–2.19 V / ≥ 250 mV | unchanged | PASS |
| Device voltage stress | ≤ 5.5 V (g5v0d10v5) | 3.6 V max | 3.6 V max | PASS |
| Output noise, 100 Hz–100 kHz (tt, ideal VREF) | info | n/a | 36–59 µVrms | INFO |

Costs of v2 (all still inside spec): less damping margin, ≈ 5 dB lower DC loop gain (hence worse line/load regulation and lower
low-frequency PSRR), slightly higher dropout, and ≈ 1.7× MIM area. Limitations of the v2 results (detailed in the notebook): ideal VREF/Iref,
schematic-level only (the xschem file is label-connected), mid-band PSRR ≈ 9 dB, and poly-resistor mismatch not modelled. v3 (below)
adds the real reference, the layout and post-layout results; with the reference filter the mid-band PSRR is ≈ 19–21 dB.

For context, the notebook (end of Section 13) places the design next to four published capacitor-less LDOs using the FOM table of
Ming, Zhou and Zhang (VLSI-SoC 2011): 0.14 ns (tt) / 0.20 ns (PVT worst) here, versus 0.032, 0.067, 1.29 and 19.5 ns for Hazucha 2005,
Man 2007, Or & Leung 2010 and Milliken 2007. Those are silicon measurements at 50–100 mA, so the comparison is indicative only.

## v3: real reference, layout and post-layout verification

v3 adds a transistor-level nano-power bandgap and replaces the ideal VREF/Iref with it.
- **Design:** no op-amp; 0.63 µA at 27 °C.
- **Trimmed Monte Carlo:** −0.61 … +0.96 % over −40…125 °C and 1.8–3.3 V.
- **Supply filter:** an RC filter outside the bandgap loop.

LDO + POR + bandgap have a fully scripted SKY130 layout, 391 × 522 µm:
- bandgap PNPs in a common-centroid row, the PMOS mirror in one row with dummies
- KLayout official DRC: **0 violations**
- Magic DRC on the final GDS: **0**
- Netgen LVS: **match**, 79 devices / 46 nets

The whole block was then re-simulated from the C-extracted netlist (1,991 parasitic capacitors), as power-up transients over 45 PVT points, plus loop gain and Monte Carlo:

| | Spec | Post-layout |
|---|---|---|
| Load step 0↔1 mA, 100 ns, PVT worst | ≤ 300 mV | −277 / +179 mV |
| Load step, tt (pre → post layout) | | −201 → −230 mV |
| Phase margin, 72 PVT × load × C_L points (global loop) | ≥ 45° | ≥ 95°, gain margin ≥ 16.7 dB at 68 points; 4 cold 1 mA points have a low-frequency doublet (step overshoot there ≤ 6.5 %) |
| Iq LDO + bandgap + POR | (LDO alone: ≤ 10 µA) | 7.2 µA tt; worst 12.9 µA (sf / −40 °C) |
| POR V_on / hysteresis (15 PVT points) | 2.0 V ± 10 % / ≥ 150 mV | 1.894–2.192 V / ≥ 244 mV |
| PSRR tt at 1 kHz / 100 kHz / 847 kHz | ≥ 30 dB at 1 kHz | **24.7 (FAIL)** / 22.1 / 19.1 dB |
| Monte Carlo with mismatch: tt / 27 °C (100), tt and ss / 125 °C / 1.8 V, fs / −40 °C (60 each) | | all start; VOUT σ 1.0–1.2 % untrimmed; undershoot ≤ 283 mV |
| VOUT 4 ms after power-up | ± 3 % | 43 / 45 points; **FAIL at fs / −40 °C / ≥ 2.5 V (+3.8 %, settles by 8 ms)** |

Notebook Section 16 has two code cells for these results:
- one re-plots them and checks them against the specs
- one re-simulates the extracted netlist with the notebook's own ngspice setup

Open points are listed with numbers in `layout/README.md`:
- start-up settling of up to 8 ms at fs / −40 °C (five alternative start-up circuits tried and documented)
- a 10 dB post-layout loss of 1 kHz PSRR, located in the bandgap's node capacitance but not fixed
- capacitance-only extraction (no RC)

Details: `layout/README.md` and notebook Section 16.

## Files

| File | Content |
|---|---|
| `capless_ldo_por_rf_harvest_sky130.ipynb` | The notebook (executed, outputs saved) |
| `LICENSE` | Apache License 2.0 |
| `README.md` | This file |
| `layout/` | v3: GDS, layout render, generator, verification and post-layout scripts, DRC/LVS/PEX reports, post-layout and bandgap data |
| `.gitignore` | Ignores simulation/PDK/tool folders created when the notebook runs |
| `xschem/capless_ldo_por.sch` | xschem schematic generated from the notebook parameters (devices connected by net labels, no drawn wires) |
| `xschem/capless_ldo_por.svg`, `.spice` | SVG export and xschem netlist; the netlist matches the notebook netlist device by device (35/35) |

## How to run

* **Colab:** open the notebook in Google Colab → *Runtime → Run all*. The first code cell installs
  ngspice (conda-forge via micromamba) and the SKY130 PDK (via ciel, ≈ 2 GB). Expect a few minutes for installation and
  roughly 20–35 min for the ≈ 1,400 simulations (≈ 5 min measured on 16 desktop cores).
  Section 16 part 2 re-simulates the extracted layout netlist and adds a few minutes (two power-up transients).
* **Linux/WSL:** same. If `ngspice` is on `PATH` and `$PDK_ROOT/sky130A` exists, installation is skipped.

Tested with ngspice-41 (conda-forge), open_pdks SKY130A `792ef67037d74c8c51811eab3ce23cf793491296` (ciel 3.2.0),
Python 3.12, numpy, pandas, matplotlib, schemdraw 0.23 on Ubuntu 24.04 (WSL2).

## Tools & assistance

I made this notebook with the help of an AI assistant (Claude, by Anthropic, used through Claude Code). The assistant helped write the notebook code, the scripts that generate the notebook, and most of the text. I chose the application and the specifications, ran the simulations, checked their results, and reviewed the final notebook. All circuit results in the notebook and in this README come from the ngspice simulations that the notebook runs. The open-source tools are the SKY130 PDK (open_pdks), ngspice-41, xschem and schemdraw. Prior work that the design relies on is listed in the References section at the end of the notebook (§15).

## License

Copyright 2026 Poggy Macello Gultom. Licensed under the Apache License, Version 2.0 (see `LICENSE`).
SPDX-License-Identifier: Apache-2.0
