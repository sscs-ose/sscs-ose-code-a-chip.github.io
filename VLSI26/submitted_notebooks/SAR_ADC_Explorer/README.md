# SAR ADC Explorer: An Interactive Educational Notebook

**Submission for IEEE SSCS Open-Source Ecosystem "Code-a-Chip" Travel Grant Awards at VLSI'26**

SPDX-License-Identifier: Apache-2.0

## Team

| Name | Affiliation | Email |
|:----:|:-----------:|:-----:|
| Daniel Tyukov | Independent Researcher | danieltyukov@gmail.com |

## Overview

This Jupyter notebook provides a comprehensive, interactive educational exploration of the **Successive Approximation Register (SAR) ADC** — one of the most widely used and energy-efficient ADC architectures in modern integrated circuits.

The notebook combines:
- **Animated visualizations** of the SAR binary search algorithm and charge redistribution
- **Transistor-level design** using the gm/ID methodology with the SkyWater SKY130 PDK
- **SPICE simulation** of a StrongARM latch comparator with ngspice
- **Performance analysis** including DNL/INL, FFT-based ENOB extraction
- **Figure-of-Merit comparison** against published state-of-the-art SAR ADCs
- **Layout visualization** of the binary-weighted CDAC using gdstk
- **Design space exploration** showing fundamental resolution-speed-power trade-offs

## Tools & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Primary language |
| NumPy | Latest | Numerical computation |
| SciPy | Latest | Signal processing |
| Matplotlib | Latest | Visualization & animation |
| schemdraw | 0.22+ | Circuit schematic drawing |
| ngspice | 42+ | SPICE simulation |
| PySpice | 1.5 | Python-ngspice interface |
| SKY130 PDK | Latest | Process Design Kit |
| gdstk | 0.9+ | GDS layout manipulation |

## How to Run

### Google Colab (Recommended)
Click the "Open in Colab" badge at the top of the notebook. All dependencies are installed automatically.

### Local Environment
```bash
pip install numpy scipy matplotlib schemdraw PySpice gdstk ipywidgets jupyter
sudo apt-get install ngspice  # On Ubuntu/Debian
jupyter notebook SAR_ADC_Explorer.ipynb
```

## Notebook Structure

1. **Environment Setup** — Install tools and import libraries
2. **SAR ADC Concept** — Architecture, binary search algorithm with animation
3. **Comparator Design** — StrongARM latch topology and operation
4. **SPICE Simulation** — gm/ID characterization, transistor sizing, SPICE verification
5. **Performance Analysis** — DNL/INL static linearity, FFT-based dynamic analysis
6. **FoM Analysis** — Walden & Schreier FoM comparison with state-of-the-art
7. **Layout Visualization** — CDAC layout with gdstk
8. **Design Space Exploration** — Resolution vs. speed vs. power trade-offs
9. **Advanced Topics** — Monotonic vs. conventional switching energy analysis

## License

This work is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
