# 🔬 MX Precision Lab: Error-Budgeted Accumulator Width for MX Dot-Product Cores
### IEEE SSCS Code-a-Chip Travel Grant · ISSCC 2027

**Author:** Kuan-Yu Liu  
**Affiliation:** University of Toronto  
**License:** Apache 2.0

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/12yuuuu/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/mx_precision_lab/submission.ipynb)

***

## 📌 Overview

Microscaling (MX) formats share one 8-bit scale per block of 32 elements. An MX dot product therefore adds block sums that sit at different exponents. The accumulator aligns them and keeps a fixed number of fractional bits. That width **W** sets both the numerical error and the silicon cost.

**MX Precision Lab** turns that width into a measured decision. You give a layer and two error budgets: the accumulation error and the total error against FP32. The tool compares every format and width with a bit-exact model. It then joins each candidate to the RTL, mapped and routed GF180MCU evidence of exactly that design. The same two budgets apply at every stage, from the panels to the physical selection.

> On an MNIST layer with a 0.1 % accumulation budget and a 12 % total budget, **W18 (F2)** is enough. Its routed core is **7.15 % smaller** than the next qualified width (W20), with positive slack at 50 ns and clean DRC and LVS.

***

## 🚀 Key Contributions

- 🎯 **Error-budgeted width selection:** input quantization and accumulation error are kept apart. A candidate must meet both budgets, and the smallest qualified routed core wins.
- 🧱 **Physical evidence per candidate:** LibreLane place and route on GF180MCU, nine STA corners, Magic DRC and Netgen LVS. The raw reports of the selected F2 core and its F4 alternative are included and checked again.
- 🔁 **Two backends:** the routed MXFP4 core, and a generic core for six OCP MX encodings (MXFP4 example: W18 maps to 1.82 % less area than W20).
- 📈 **Workload study:** 14 layers × 6 budgets. A fixed F4 misses the budget in 27 of 84 cases, while F0 or F2 suffice in 32.
- ✅ **Verified RTL:** 17,527 regression transactions with 0 mismatches.
- ❌ **Measured negative result:** selective exact recompute is 40.7 % larger than four fixed F6 cores, so it is rejected.
- ⏱️ **Cycle-exact C++ model:** 64 cases and 424,232 events with zero cycle error against the RTL.
- 🛑 **Fails loudly:** if any evidence check fails, the run stops and no submission bundle is written.

***

## 🧠 Concept

For the MXFP4 backend, let $B = K/32$ be the number of blocks, with exact block sums $S_g$ and block exponents $E_g$. Define $E_{\max} = \max_g E_g$.

Each block sum is aligned and rounded using round-to-nearest, ties-to-even (RNE):

$$
T_g = \mathrm{RNE}\left(S_g \cdot 2^{E_g - E_{\max} + F}\right).
$$

With 14-bit exact block sums, the accumulator width is:

$$
W = 14 + \left\lceil \log_2 B \right\rceil + F.
$$

At $K = 128$, we have $B = 4$ and $W = 16 + F$.

If

$$
F \geq \max_g \left(E_{\max} - E_g\right),
$$

the accumulation is exact **relative to the quantized MX inputs**, provided the accumulator does not overflow.

The tool finds the smallest $F$ that meets **both error budgets** and has a **qualified routed core**.

***

## 📊 Results Summary

[//]: # (results table start)
| Metric | Value |
|:-|:-|
| Selected core (MNIST fc2, 0.1 % and 12 % budgets) | W18 (F2), 58,071.8 µm² routed standard-cell area |
| Saving against W20 (F4) | 7.15 % |
| Timing and signoff at 50 ns | setup +11.99 ns, 9 STA corners, DRC 0, LVS 0 |
| Generic MX core, MXFP4 example, W18 vs W20 | 1.82 % less mapped area |
| Fixed F4 across 84 workload × budget cases | misses the budget in 27, F0 or F2 is enough in 32 |
| Inexact flag (routed area) | +0.42 % at F2, +0.10 % at F4 |
| Selective exact recompute, N4 top | +40.7 % area vs fixed F6 |
| C++ model vs RTL | 64 cases, 424,232 events, max cycle error 0 |

| F | W | area (µm²) | setup WS (ns) | hold WS (ns) | slew / cap | DRC / LVS | qualified |
|:-|:-|-:|-:|-:|:-|:-|:-|
| 0 | 16 | 56,223.5 | +9.936 | +0.211 | 0 / 0 | 0 / 0 | no: calibration accumulation error exceeds budget |
| 2 | 18 | 58,071.8 | +11.993 | +0.206 | 0 / 0 | 0 / 0 | **selected** |
| 4 | 20 | 62,543.4 | +11.991 | +0.163 | 0 / 0 | 0 / 0 | yes |
| 6 | 22 | 62,773.9 | +12.488 | +0.178 | 0 / 0 | 0 / 0 | yes |
| 8 | 24 | 64,027.4 | +11.911 | +0.173 | 0 / 0 | 0 / 0 | yes |
| 12 | 28 | 61,757.6 | +12.073 | +0.130 | 0 / 0 | 0 / 0 | yes |
| 24 | 40 | 67,695.6 | +12.521 | +0.142 | 0 / 1 | 0 / 0 | no: slew/cap/parasitic-coverage checks not qualified |
[//]: # (results table end)

***

## ⚙️ Setup

| File | Content |
|:-|:-|
| `README.md` | introduction, Colab button, license |
| `submission.ipynb` | walkthrough, interactive panels, key figures and results |
| `mx_precision_lab_support.zip` | code, RTL, data and verification records |

Click the badge, then **Runtime → Run all**. The first cell downloads the support ZIP from this folder, checks its SHA-256 and unpacks it. On your own machine it uses the ZIP next to the notebook instead.

GitHub shows a static HTML preview of the notebook. Open it in Colab to use the interactive panels.

***

## 📂 What the Support ZIP Holds

The support ZIP holds the code, RTL, C++ model, flow configuration, records, evidence views and layer data the notebook runs on. Section 1 checks its SHA-256, unpacks it and checks every file.

- The complete raw signoff reports of F2 and F4 are included, and Section 8 reads them again.
- The raw reports of the other routed runs and the final layout views (226 MB) are not included. Only their summary numbers and SHA-256 values are kept. This is the historical record.
- The 10,000-image test splits of two MNIST models (GELU+LayerNorm and K512) are not included. Their recorded test results are used.
- The synthetic layers are rebuilt from their generator and seed, and must match their recorded data exactly.

***

## 🛠️ Tools & Technologies

- GF180MCU PDK · LibreLane 3.0.16 (OpenROAD, Magic, Netgen, KLayout)
- Icarus Verilog · Yosys and ABC · Graphviz
- Python (NumPy, Matplotlib, ipywidgets) · C++17 and CMake

***

## 🔁 Reproducibility

Click **Runtime → Run all** (after the first-run setup). All tools are open-source. The GF180MCU PDK is publicly available. Apache 2.0 licensed.

To run the notebook locally, keep `mx_precision_lab_support.zip` next to `submission.ipynb`:

```bash
python -m pip install numpy matplotlib ipywidgets jupyterlab
jupyter lab submission.ipynb
```

Section 1 unpacks the ZIP into `mx_precision_lab_support/`. All paths below are inside that folder.

```
src/mxlab/        interactive panels, generic MX core, figures, submission bundle
src/mxacc/        MXFP4 core model, studies and plots, support-package checks
rtl/              MXFP4 core, optional inexact flag variant, recompute system
cpp/              C++17 cycle-exact performance model
data/             MNIST, BERT-Tiny FFN and synthetic layers
evidence/         circuit and layout views of every recorded design
results/          RTL, mapped and routed records with their hashes
flow/, scripts/   pinned LibreLane configuration and the scripts that reproduce the records
SUPPORT.json      what is in the package, what is rebuilt and what is only recorded
SHA256SUMS        the hash of every file in the package
```

- **Routed records:** `scripts/run_flow.py` reproduces them in the pinned LibreLane environment of `flow/environment.json`. The raw signoff reports of F2 and F4 are in `results/physical/f2/evidence/` and `results/physical/f4/evidence/`.
- **Your own layer:** export `calibration.npz` and `test.npz` with keys `x` (rows × K) and `w` (outputs × K, the same in both files). Then choose *Your own layer export* in Section 3. `src/mxlab/torch_bridge.py` exports every `torch.nn.Linear` of a PyTorch model with forward hooks.
- **Submission bundle:** Section 15 writes `results/submission_bundle.zip`.

***

## ⚠️ Scope

- The generic MX core has mapped-synthesis evidence only. It has no layout yet.
- Power is the flow's vectorless estimate, not an activity-based measurement.
- Each routed candidate is one place-and-route run, so placement noise is not characterised.

***

## 📎 Citation

Kuan-Yu Liu, "MX Precision Lab: Error-Budgeted Accumulator Width for MX Dot-Product Cores," IEEE SSCS Code-a-Chip, ISSCC 2027.

## 📬 Contact

Kuan-Yu Liu: ana.liu@mail.utoronto.ca
