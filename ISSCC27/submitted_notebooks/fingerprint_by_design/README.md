# Fingerprint by Design

**Predicting, tracing and stabilising the RF fingerprint of an open-source SKY130 transmitter, before any silicon exists**

Submission to the IEEE SSCS "Code-a-Chip" Travel Grant Awards at ISSCC 2027 · License: Apache-2.0

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/byungkim113/Fingerprint-By-Design/blob/main/notebook/fingerprint_by_design.ipynb)

## Summary

Small manufacturing differences give radio chips of the same design slightly different responses to the same data:
an **RF fingerprint**. This project uses the open SkyWater SKY130 PDK to trace those differences through a transmitter,
test how design choices change them, and measure their sensitivity to supply and temperature.

The project includes two SKY130 blocks:

* an analog core (I/Q current-steering DACs, Gilbert mixers, LO path, PA, output buffer, bias reference) and an on-chip
  LDO regulator with a bandgap reference: DRC-clean in Magic and KLayout, strict LVS-clean (device sizes included),
  parasitic-extracted, with regulator start-up checked on the extracted layout;
* a digital front end (SPI port, 128-sample frame memory, thermometer decoders) taken through LibreLane to a routed,
  DRC/LVS-clean layout and tested at RTL and gate level.

We then simulated hundreds of Monte Carlo "virtual chips" at transistor level. Key findings:

* Chips of one design are identified at 100% at 30 dB SNR per sample (16 and 64 chips) when each decision averages an
  18-frame, 92 us burst of a known 128-sample frame; from a single frame, 89% (16 chips) and 73% (64 chips).
  Same-design impostors: 0% equal error rate at 30 dB, 7.4% at 20 dB.
* Chip-specific feature energy is 7.24x greater after the PA than at the mixer output. A more
  linear PA reduces RF fingerprint size to 0.62x of the baseline.
* The capacitance-extracted population has 0.99x the schematic population's fingerprint size.
* Supply drift causes a larger identification loss than temperature alone in this setup (external LO, known repeated frame, simulated devices;
  -10% supply: 100% -> 34%). Design-time drift models recover most of the loss; an **on-chip LDO maintains 100% identification
  at all seven tested supply values spanning +-10% at 30 dB SNR**, using the known 18-frame burst.
* Open problem: identifying chips from arbitrary data under temperature drift.

The main tests were pre-registered (prediction and pass rule written down before running) and failures are reported;
analyses chosen after seeing data are labelled post hoc or exploratory in the notebook.

## Contents

| Path | What it is |
|---|---|
| `fingerprint_by_design.ipynb` | The notebook (story, figures, results, limitations, reproduction guide) |
| `data/` | Result files (JSON) the figures are made from, including our run of the live demo |
| `gds/` | Layout files (gzipped GDS) of the analog core with LDO, and of the digital front end |
| `images/` | Layout renders and explanatory diagrams |
| `setup_tools.sh` | Installs the pinned SKY130 PDK and builds ngspice 47 for the live demo (Linux / Colab) |
| `sim/` | The six project scripts the live demo needs (netlist generator and helpers), copied unchanged |
| `sim/frame128_seed1.hex` | The exact main-study stimulus, avoiding a platform-dependent rounding difference |
| `LICENSE` | Apache License 2.0 |

## Running

* **Default (seconds):** every figure is regenerated from `data/` and `gds/` with `numpy`, `matplotlib` and `gdstk`,
  locally or on Colab.
* **Live transistor-level demo (Section 2b, optional):** set `RUN_LIVE = True` on Colab or Linux. It installs the PDK,
  builds ngspice 47, simulates two virtual chips and the mismatch-free design (about 5 minutes on a laptop, longer on a
  free Colab runtime) and checks the result against ours.
* **Full study (days):** not re-run in the notebook; Section 11 maps each result to its script.

## Reproducing everything

Full source (layout generators, simulation and analysis scripts, digital RTL, testbench and LibreLane configuration,
project log with every pre-registration): <https://github.com/byungkim113/Fingerprint-By-Design>. Section 11 of the notebook
lists the tool versions and the script behind each result.
