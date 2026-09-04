# NeuroSAR: Project Overview

## Summary

NeuroSAR is a physics-informed neural network (PINN) surrogate for charge-redistribution successive-approximation register (SAR) analog-to-digital converter (ADC) waveforms, implemented in Python/PyTorch and targeting the SkyWater Sky130 open-source process design kit (PDK). It produces differentiable, physically consistent predictions of the complete time-domain DAC settling waveform and comparator regeneration trajectory across a 9-dimensional circuit design space, enabling real-time interactive exploration, automated figure-of-merit (FoM) mapping, and gradient-based inverse design — capabilities that are intractable with conventional SPICE-based workflows.

---

## Target Audience

| Audience | Why NeuroSAR Is Relevant |
|---|---|
| **Mixed-signal circuit designers** | Rapid design-space exploration and sensitivity analysis without running thousands of SPICE simulations. PINN gradients expose which parameters most strongly affect ENOB, metastability margin, and power |
| **ML researchers** | A concrete, well-motivated application of physics-informed machine learning to analog circuit surrogate modeling. Demonstrates loss composition, Fourier feature encoding, and multi-output regression on a scientifically grounded problem |
| **EDA educators** | An interactive teaching tool for SAR ADC operating principles. Students can move sliders and immediately see how capacitor sizing affects DAC accuracy, or how transconductance governs comparator speed — with no SPICE installation required |
| **Open-source EDA contributors** | A worked example of how to couple the Sky130 PDK with Python-based ML workflows via ngspice, serving as a template for similar PDK-aware surrogate models |

---

## What Makes This Different from a Black-Box Regression Model

A purely data-driven regression model trained on SAR ADC waveforms would minimize a data loss only:

$$\mathcal{L}_\text{black-box} = \frac{1}{N} \sum_{i=1}^N \left\| \hat{y}_i - y_i \right\|^2$$

Such a model faces three critical limitations:

1. **Generalization failure outside training distribution**: Without physical constraints, a neural network can predict thermodynamically impossible waveforms — V_dac trajectories that violate charge conservation, or V_comp curves that regenerate faster than the latch transconductance permits.

2. **Data inefficiency**: Physical laws are free constraints. A PINN that embeds KCL and the regeneration ODE requires substantially less labeled data to achieve the same prediction accuracy, because the physics residuals act as informative regularizers.

3. **No interpretable structure**: A black-box model gives no handle on *why* a prediction is what it is. The PINN's physics residuals are individually interpretable: a large KCL residual tells you the model is struggling to conserve charge in a particular region of design space, guiding debugging and further data collection.

NeuroSAR addresses all three by incorporating four physics residual terms (KCL, charge redistribution, comparator ODE, smoothness) directly into the training objective, evaluated at every training point via automatic differentiation through the network.

---

## How the PINN Loss Encodes Circuit Physics

The PINN training loss is:

$$\mathcal{L} = w_\text{data} \mathcal{L}_\text{data} + w_\text{kcl} \mathcal{L}_\text{kcl} + w_\text{charge} \mathcal{L}_\text{charge} + w_\text{ode} \mathcal{L}_\text{comp} + w_\text{smooth} \mathcal{L}_\text{smooth}$$

Each physics term is derived from a first-principles circuit equation and evaluated without additional simulation — the network's own output and its automatic derivatives provide all necessary quantities:

### KCL at the DAC Node

The charge-redistribution DAC settles between bit decisions with no net current injection. Kirchhoff's Current Law therefore requires:

$$\left( C_\text{total} + C_\text{load} \right) \frac{dV_\text{dac}}{dt} \approx 0 \quad \text{during settling intervals}$$

This is enforced by computing $\partial \hat{V}_\text{dac} / \partial t$ via `torch.autograd.grad` and penalizing non-zero values during settling windows.

### Charge Redistribution

At each bit decision event, the DAC switches capacitor $C_k$. The voltage step predicted by the network must match the theoretical value:

$$\Delta \hat{V}_\text{dac}^{(k)} = \frac{C_k}{C_\text{total}} \cdot V_\text{ref} \cdot (2 b_k - 1)$$

This is the fundamental operating equation of charge-redistribution DACs and directly encodes bit accuracy.

### Comparator Regeneration ODE

The cross-coupled latch in regeneration mode is described by a first-order linear ODE in the small-signal differential voltage:

$$\frac{dV_\text{comp}}{dt} = \frac{g_m}{C_L} V_\text{comp}$$

The PINN enforces this by penalizing departures of $\partial \hat{V}_\text{comp} / \partial t$ from $(g_m / C_L) \hat{V}_\text{comp}$.

### Smoothness Regularization

An additional term penalizes the second time derivative of both outputs, suppressing non-physical high-frequency oscillations that have no circuit counterpart:

$$\mathcal{L}_\text{smooth} = \left\| \frac{\partial^2 \hat{V}_\text{dac}}{\partial t^2} \right\|^2 + \left\| \frac{\partial^2 \hat{V}_\text{comp}}{\partial t^2} \right\|^2$$

---

## Differentiability and Its Consequences

Because the PINN is a standard PyTorch neural network, it is fully differentiable with respect to *both* its inputs and its parameters. This enables:

- **Sensitivity analysis**: $\partial \hat{V}_\text{dac} / \partial C_\text{unit}$ tells you how the DAC settling changes per unit capacitance — without running any simulation.
- **Inverse design**: Treating the design parameters as optimization variables and the PINN as the forward model, Adam or L-BFGS can find the parameter set that minimizes $|$ENOB$_\text{target}$ − ENOB$_\text{predicted}|$ + λ · Power in tens of gradient steps.
- **Uncertainty-aware design**: By training an ensemble of PINNs with different random seeds, prediction variance can be used as a proxy for model uncertainty across the design space.

---

## Relationship to Prior Work

NeuroSAR builds on the PINN framework introduced by Raissi et al. (2019) for solving PDEs with neural networks, adapting it to the lumped-circuit setting where the governing equations are ODEs derived from Kirchhoff's laws rather than partial differential equations. The key adaptation is the multi-output formulation (joint prediction of V_dac and V_comp), the Fourier feature time encoding to handle the multi-scale temporal dynamics of SAR conversion (fast comparator regeneration at ~1 ns superimposed on slow DAC settling at ~100 ns), and the practical focus on open-source PDK compatibility via Sky130.

See `docs/TECH_REP.md` for a full literature review and `docs/physics_model.md` for detailed derivations of each physics residual.
