# Hardened Fixed-Point Perceptron Core for Secure Biomedical Edge-AI Anomaly Detection

IEEE SSCS Open-Source Ecosystem **Code-a-Chip** submission for **ISSCC 2027**.

**Author:** Juan Carlos Aquino Hernández — Universidad Tecnológica de Nayarit (UTNay), División de Electromecánica Industrial  
**License:** Apache License 2.0 (see [`LICENSE`](LICENSE))

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Juan-AquinoH/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/hardened_perceptron_anomaly_core/anomaly_core_codeachip.ipynb)

## What this is

A 4-input, 8-bit perceptron anomaly-detection core for wearable and biomedical edge nodes, hardened against arithmetic overflow and data injection, taken end to end with open-source tools:

- **RTL** (Verilog) with a wide accumulator, an optional symmetric saturator (`SAT_GUARD`), and an enable-gated isolation bit that freezes the alert line and diagnostic registers.
- **Verification** (cocotb + Icarus Verilog): 6 structural tests, a saturation test with a negative control, and bit-exact RTL-to-Python comparison over 1,000 validation vectors plus constrained-random stimulus.
- **RTL-to-GDSII** (LibreLane 3.0.14 + SkyWater Sky130) with DRC/LVS signoff and setup/hold timing reported per PVT corner.
- **Design-space sweep** of accumulator and bias widths, with and without the live saturator.

## How to run

Open the notebook in Colab using the badge above, select a CPU runtime, and choose **Runtime → Run all**.

Expected execution time is approximately 2 hours:

- Toolchain setup: approximately 5 minutes
- Baseline physical-design flow: approximately 30 minutes
- Five-variant sweep: approximately 70 minutes

If the runtime restarts, `/nix` and `/content` are wiped. Re-run Section 1 and every subsequent cell. No external accounts are required.

## Results

| Check | Result |
|---|---|
| cocotb structural regression (Table 1) | 6/6 PASS |
| RTL vs. Python reference, 1,000 validation vectors | 0 score mismatches; 0 decision mismatches |
| Constrained-random RTL vs. 32-bit saturating model | 0 mismatches |
| Hardware accuracy / precision / recall / F1 on synthetic data | 0.813 / 0.468 / 0.874 / 0.610 |
| Baseline (`ACC_W = 32`, `BIAS_W = 16`) at 40 ns | DRC 0 (Magic, KLayout); LVS 0; setup WNS +2.447 ns; hold WNS +0.121 ns |
| Baseline synthesised area / cells / power (typical) | 25,538 µm² / 2,300 cells / 3.22 mW |

Accumulator-width sweep, all evaluated at a 40 ns target period. Synthesised area is reported by Yosys.

| Variant | `ACC_W` / `BIAS_W` / `SAT_GUARD` | Area vs. baseline | Setup WNS (ns) | Timing met |
|---|---|---:|---:|---|
| baseline | 32 / 16 / 0 | 0% | +2.447 | yes |
| acc24_bias16 | 24 / 16 / 0 | −1.6% | +3.690 | yes |
| acc20_bias13 | 20 / 13 / 0 | −5.2% | +1.954 | yes |
| acc20_bias13_guard3 | 20 / 13 / 3 | −4.3% | +4.800 | yes |
| acc17_bias16 | 17 / 16 / 0 (can overflow) | −9.4% | −0.845 | no |
| acc17_bias16_guard3 | 17 / 16 / 3 (live clamp) | −3.3% | −1.356 | no |

At 17 bits, enabling the live clamp adds 6.7% synthesised area relative to the unguarded 17-bit variant, corresponding to 27 additional cells. Both 17-bit variants fail setup at the 40 ns target period.

## Limitations

- The dataset is synthetic. Accuracy figures validate the hardware implementation against the software model and do not establish clinical performance.
- Timing results reported here use a 40 ns target period. This is a characterization point, not a proven minimum achievable clock period.
- Bit-exact functional checks apply to the baseline configuration. Sweep variants are compared for area, timing, and power.
- In the slow corner (`ss_100C_1v60`), extended checks still report maximum-slew violations and one clock-root fanout violation; setup, hold, DRC, and LVS are clean in all reported corners. See Section 5 of the notebook.
- Sky130 is a 130 nm teaching PDK. Reported area and power are not representative of a production medical-device process node.

## Files

| File | Purpose |
|---|---|
| `anomaly_core_codeachip.ipynb` | Self-contained submission notebook. It generates the RTL, testbenches, and scripts used in the flow. |
| `LICENSE` | Apache License 2.0 |

## Tools

Tool versions are recorded by the notebook in `tool_versions.json`.

- LibreLane 3.0.14
- Yosys 0.62
- OpenROAD
- Magic 8.3.623
- Netgen 1.5.316
- KLayout 0.30.7
- cocotb 2.1.0
- Icarus Verilog 12.0
- SkyWater Sky130 PDK, ciel hash `8afc8346a57fe1ab7934ba5a6056ea8b43078e71`

## Reference

J. C. Aquino Hernández, *“RTL Hardening Methodology for Secure Fixed-Point Edge AI Inference Engines: A Perceptron-Based Biomedical Case Study,”* 2026 (companion paper).