# Hardened Fixed-Point Perceptron Core for Secure Biomedical Edge-AI Anomaly Detection

IEEE SSCS Open-Source Ecosystem **Code-a-Chip** submission for **ISSCC 2027**.

**Author:** Juan Carlos Aquino Hernández — Universidad Tecnológica de Nayarit (UTNay), División de Electromecánica Industrial
**License:** Apache License 2.0 (see [`LICENSE`](LICENSE))

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Juan-AquinoH/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/hardened_perceptron_anomaly_core/anomaly_core_codeachip.ipynb)

## What this is

A 4-input, 8-bit perceptron anomaly-detection core for wearable / biomedical edge nodes, hardened against
arithmetic overflow and data injection, taken end to end with open-source tools:

* **RTL** (Verilog) with a wide accumulator, an optional symmetric saturator (`SAT_GUARD`) and an enable-gated
  isolation bit that freezes the alert line and diagnostic registers.
* **Verification** (cocotb + Icarus Verilog): 6 structural tests, a saturation test with a negative control, and a
  bit-exact comparison of the RTL against a Python reference over 1 000 validation vectors plus constrained-random stimulus.
* **RTL-to-GDSII** (LibreLane 3.0.14 + SkyWater Sky130) with DRC/LVS signoff and setup/hold reported per PVT corner.
* **Design-space sweep** of accumulator / bias widths, with and without the live saturator.

## How to run

Open the notebook in Colab (badge above), CPU runtime, and choose **Runtime → Run all**. Expect about 2 hours
(toolchain ≈ 5 min, baseline flow ≈ 30 min, 5-variant sweep ≈ 70 min). If the runtime restarts, `/nix` and `/content`
are wiped: re-run §1 and every later cell. No external accounts are needed.

## Results (as stored in the notebook)

| Check | Result |
|---|---|
| cocotb structural regression (Table 1) | 6/6 PASS |
| RTL vs Python reference, 1 000 validation vectors | 0 score mismatches, 0 decision mismatches |
| Constrained-random RTL vs 32-bit saturating model | 0 mismatches |
| HW accuracy / precision / recall / F1 (synthetic data) | 0.813 / 0.468 / 0.874 / 0.610 |
| Baseline (ACC_W = 32, BIAS_W = 16) at 40 ns | DRC 0 (Magic, KLayout), LVS 0, setup WNS +2.447 ns, hold WNS +0.121 ns |
| Baseline synthesised area / cells / power (typ.) | 25 538 µm² / 2 300 cells / 3.22 mW |

Accumulator-width sweep (all at 40 ns, synthesised area from Yosys):

| Variant | ACC_W / BIAS_W / SAT_GUARD | Area vs baseline | Setup WNS (ns) | Timing met |
|---|---|---|---|---|
| baseline | 32 / 16 / 0 | 0 % | +2.447 | yes |
| acc24_bias16 | 24 / 16 / 0 | −1.6 % | +3.690 | yes |
| acc20_bias13 | 20 / 13 / 0 | −5.2 % | +1.954 | yes |
| acc20_bias13_guard3 | 20 / 13 / 3 | −4.3 % | +4.800 | yes |
| acc17_bias16 | 17 / 16 / 0 (can overflow) | −9.4 % | −0.845 | **no** |
| acc17_bias16_guard3 | 17 / 16 / 3 (live clamp) | −3.3 % | −1.356 | **no** |

The live clamp costs +6.7 % synthesised area (+27 cells) at 17 bits. Both 17-bit variants fail setup at 40 ns.

## Limitations

* The dataset is synthetic: accuracy figures validate the hardware against the software model, not clinical performance.
* 40 ns is the smallest period of the candidates tried, not a proven minimum.
* Bit-exact functional checks apply to the baseline configuration; sweep variants are compared on area, timing and power.
* In the slow corner (`ss_100C_1v60`) the extended checks still report max-slew violations and one clock-root fanout
  violation (see §5 of the notebook); setup, hold, DRC and LVS are clean in all corners.
* Sky130 is a 130 nm teaching PDK; area and power are not representative of a production medical-device node.

## Files

| File | Purpose |
|---|---|
| `anomaly_core_codeachip.ipynb` | The submission notebook (self-contained: it writes the RTL, testbenches and scripts itself) |
| `LICENSE` | Apache License 2.0 |
| `results/` | Small result artifacts produced by the notebook (sweep table, signoff report, layout image, tool versions) |

## Tools (versions are recorded by the notebook in `tool_versions.json`)

LibreLane 3.0.14, Yosys 0.62, OpenROAD, Magic 8.3.623, Netgen 1.5.316, KLayout 0.30.7, cocotb 2.1.0,
Icarus Verilog 12.0, SkyWater Sky130 PDK (ciel hash `8afc8346a57fe1ab7934ba5a6056ea8b43078e71`).

## Reference

J. C. Aquino Hernández, "RTL Hardening Methodology for Secure Fixed-Point Edge AI Inference Engines: A Perceptron-Based
Biomedical Case Study," 2026 (companion paper).
