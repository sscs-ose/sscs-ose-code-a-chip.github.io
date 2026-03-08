# Physics-Informed Bayesian Optimization for Analog SerDes Equalizer Design

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/VLSI26/submitted_notebooks/ML_SerDes_Equalizer/ML_SerDes_Equalizer.ipynb)

## Overview

Standard Bayesian optimization treats analog circuits as black boxes, ignoring known device physics. At 112 Gbps PAM4, CTLE designers must optimize 5+ transistor-level parameters via expensive SPICE simulation — a process that wastes hundreds of evaluations re-learning physics the designer already knows.

This notebook proposes **Physics-Informed Gaussian Process (PI-GP)** optimization that encodes CTLE pole-zero structure directly into the GP input space, achieving dramatically better sample efficiency.

## Novel Contributions

1. **Physics-Informed GP (PI-GP) Surrogate** — A domain-aware feature transform maps raw circuit parameters (Rs, Cs, Rd, W, Ib) to physics-motivated features (peaking frequency, gm·Rd, degeneration ratio). Validated via 5-fold cross-validation and learning curve analysis showing faster convergence than standard GP.

2. **Cross-Channel Transfer Learning** — PI-GP physics features are channel-invariant, enabling a surrogate trained on one channel configuration to warm-start optimization on a different channel with quantified sample efficiency improvement.

3. **Multi-Fidelity PI-GP Pipeline** — Fast PI-GP surrogate with UCB acquisition (Stage 1) generates candidates refined by accurate BSIM4 SPICE simulation (Stage 2), outperforming SPICE-only optimization.

4. **On-Chip Adaptive Equalization** — Trained PI-GP exported as a lightweight firmware lookup table (<4 KB SRAM) for real-time CTLE coefficient adaptation, bridging design-time optimization and silicon deployment.

## Supporting Analysis

- 4-algorithm benchmark (TPE, CMA-ES, Random, DE) with statistical robustness analysis
- SKY130-class BSIM4 (level=14) CTLE with 30+ MOSFET parameters and 5 process corners
- Real SKY130 PDK validation against `sky130_fd_pr__nfet_01v8` device models
- BER estimation and bathtub curves for quantitative link margin validation
- PVT corner robustness across 7 corners
- Multi-scenario validation (HBM chiplet, NVLink-style, PCIe Gen6)

## Key Results

- PI-GP achieves higher R² and lower RMSE than standard GP on held-out SPICE data
- Transfer learning reduces SPICE evaluations needed to reach target quality
- Multi-fidelity pipeline outperforms SPICE-only with same compute budget
- Eye diagrams go from **completely closed** to **wide open** after ML optimization
- Coefficients generalize across PVT corners
- PI-GP inference takes <100 μs per prediction — firmware-deployable for real-time adaptation

## Tools Used (All Open-Source)

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Framework |
| NumPy / SciPy | Signal processing, Differential Evolution |
| Optuna 3.5+ | TPE, CMA-ES, Random Search |
| scikit-learn | Gaussian Process surrogate, cross-validation |
| Matplotlib | Visualization |
| ngspice 40+ | Transistor-level CTLE simulation (BSIM4) |

## References

1. Srinivas et al., "GP-UCB," ICML 2010
2. Bull, "Convergence Rates of Efficient Global Optimization," JMLR 2011
3. Lyu et al., "Batch Bayesian Optimization for Analog Design," ICML 2018
4. SkyWater SKY130 PDK, Apache 2.0
5. Bergstra et al., "Algorithms for Hyper-Parameter Optimization," NeurIPS 2011

## Running the Notebook

```bash
pip install optuna numpy scipy matplotlib scikit-learn cmaes
```

Or click the "Open in Colab" badge above (recommended).

## License

Apache 2.0
