# A Pulse-Programmable STT-MRAM Stochastic Primitive for Uncertainty-Aware Neural Inference
### IEEE SSCS Code-a-Chip — ISSCC 2027 Submission

*Open-source 1T1MTJ stochastic primitive using a SKY130 CMOS access circuit with an abstract MTJ interface, DRC/LVS-verified layout, device-variation analysis, and Monte-Carlo dropout demonstration.*

**Author:** Tanay Das
**Affiliation:** AMD India
**License:** Apache 2.0 (see `LICENSE`)
**Notebook:** [`STT_MRAM_Uncertainty_Aware_ISSCC27_V4.ipynb`](STT_MRAM_Uncertainty_Aware_ISSCC27_V4.ipynb)

## Overview
Physical stochastic devices offer intrinsic randomness, but turning it into a *programmable, calibrated* hardware probability source is difficult: switching probability depends on pulse conditions and device variation. This notebook builds that source end to end:

**MTJ physics → pulse-width-controlled switching probability → calibrated Bernoulli source → SKY130 CMOS access circuit → layout (DRC/LVS/PEX) → post-layout simulation → device-variation analysis → Monte-Carlo dropout inference (MNIST, Fashion-MNIST OOD).**

## Key results
| Item | Result |
|---|---|
| Calibration | p* = 0.30 programmed at PW* ≈ 0.53 ns (Néel-Brown model) |
| Access device | Official SKY130 `sky130_fd_pr__nfet_01v8` (tt) in ngspice |
| Layout | 1T1MTJ cell 3.24 µm², 4×4 array; flat DRC 0 errors; Netgen LVS match (cell and array) |
| Post-layout | Capacitance-only PEX; I_BL and E_pulse change < 0.05 % |
| **Key finding** | Nominal calibration ≠ uniform calibration: ECE 0.012–0.172 across 20 static virtual devices (ideal 0.062 ± 0.003), tracking each device's switching probability → motivates per-device pulse-width trimming |
| MC dropout | MNIST accuracy ≈ 94 %; device variation degrades calibration (ECE), accuracy and OOD AUROC essentially unchanged |
| Energy (negative result) | E_pulse 721 fJ (755 fJ with extracted 4×4 capacitance) = 4.7–4.9× a parametric LFSR estimate; parity would need ≈ 66 fJ pulses **and** restore < 200 fJ/event |

## Scope — what is and is not claimed
- The MTJ is an **abstract interface**: a fixed behavioral resistor in SPICE and an abstract M2/M3 device in layout. SKY130 has no MTJ process.
- Switching is decided by an analytical Néel-Brown model in Python; ngspice evaluates only the resulting electrical state.
- Device-variation magnitudes are assumed stress-test values, not extracted manufacturing statistics.
- **Not claimed:** energy efficiency, a fabricated MRAM cell, or an embedded-MRAM SKY130 implementation.

## How to run
1. Open the notebook in **Google Colab** (verified) or a local Linux Jupyter environment.
2. **Runtime → Run all.** The notebook automatically installs ngspice, downloads a pinned SKY130 PDK build, builds Magic from source (Colab), installs Netgen, and downloads MNIST / Fashion-MNIST.
3. Expected runtime: roughly 15–25 minutes on Colab (the Magic build takes a few minutes).

If Magic/Netgen cannot be installed, Sections 8–9 load **reference layout results embedded in the notebook** (produced by the same flow) and state this explicitly; all other sections run normally.

### Tested tool versions
| Tool | Version |
|---|---|
| Environment | Google Colab; local Linux (Python 3.12 / 3.13) |
| ngspice | 42 |
| Magic | 8.3.684 (≥ 8.3.411 required by the SKY130 tech file) |
| Netgen | 1.5.133 |
| SKY130 PDK | open_pdks build `0fe599b2afb6708d281543108caf8310912f54af` |
| KLayout (Python) | 0.30 |

## References
See the *Key Citations* section at the top of the notebook (SpinDrop, Gal & Ghahramani MC dropout, Néel-Brown / STT switching, Kim et al. MTJ SPICE model, SkyWater SKY130 PDK).
