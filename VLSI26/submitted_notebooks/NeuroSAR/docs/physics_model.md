# Physics Model: Derivation and Implementation of PINN Residuals

This document provides rigorous derivations of the four physics residual terms embedded in the NeuroSAR PINN training loss. Each residual encodes a specific first-principles constraint that any physically valid SAR ADC waveform must satisfy.

---

## 1. KCL Residual: Current Conservation at the DAC Node

### Circuit Background

In a charge-redistribution SAR ADC, the DAC is implemented as a binary-weighted capacitor array. The top plate of the array (the "DAC node") connects to the comparator input. During the settling phase between bit decisions, the switches have reached their final positions and no further charge is being injected. The only element connected to the DAC node is the comparator input capacitance $C_\text{load}$ in parallel with the total DAC capacitance $C_\text{total}$.

### Governing Equation

By Kirchhoff's Current Law, the net current into any node at any instant must sum to zero. During the settling interval after bit $k$ is resolved:

$$I_\text{net} = \left( C_\text{total} + C_\text{load} \right) \frac{dV_\text{dac}}{dt} = 0$$

This is equivalent to saying that charge on the DAC node is conserved — no new charge enters or leaves once the switch positions are fixed.

### PINN Residual Formulation

The network predicts $\hat{V}_\text{dac}(t; \boldsymbol{\theta})$ where $\boldsymbol{\theta}$ is the set of design parameters. The KCL residual at collocation point $(t_j, \boldsymbol{\theta}_i)$ within a settling window $\mathcal{T}_\text{settle}$ is:

$$r_\text{kcl}(t_j, \boldsymbol{\theta}_i) = \frac{\partial \hat{V}_\text{dac}}{\partial t}\bigg|_{(t_j, \boldsymbol{\theta}_i)}$$

The time derivative is computed via PyTorch automatic differentiation:

```python
dVdac_dt = torch.autograd.grad(
    outputs=V_dac_pred,
    inputs=t_colloc,
    grad_outputs=torch.ones_like(V_dac_pred),
    create_graph=True
)[0]
```

The KCL loss averages the squared residual over settling-window collocation points:

$$\mathcal{L}_\text{kcl} = \frac{1}{|\mathcal{T}_\text{settle}|} \sum_{j \in \mathcal{T}_\text{settle}} \left( \frac{\partial \hat{V}_\text{dac}}{\partial t}\bigg|_{t_j} \right)^2$$

### Physical Significance

This constraint prevents the network from predicting waveforms with spurious settling oscillations or non-physical drift during intervals when the circuit should be holding a stable charge. It is the PINN analog of enforcing that the DAC node is not a current source.

**Implementation note:** The settling windows $\mathcal{T}_\text{settle}^{(k)}$ are defined relative to the bit-decision times $t_k$, which are themselves functions of design parameters (conversion speed depends on $g_m$ and $C_L$). In NeuroSAR, these windows are precomputed during data generation and stored as part of the dataset metadata.

---

## 2. Charge Conservation Residual: DAC Voltage Step at Bit Switching

### Circuit Background

The charge-redistribution DAC operates on a fundamental principle: when capacitor $C_k$ is switched from bottom plate connected to $V_\text{bot}^\text{before}$ to $V_\text{bot}^\text{after}$, charge conservation on the DAC node top plate dictates the resulting voltage change.

For a binary-weighted array with unit capacitance $C_u$, capacitor $k$ has value $C_k = 2^{N-1-k} C_u$ for bit $k \in \{0, 1, \ldots, N-1\}$. The total array capacitance is:

$$C_\text{total} = \sum_{k=0}^{N-1} C_k + C_\text{dummy} = 2^N C_u$$

### Governing Equation

When bit $k$ is resolved and capacitor $C_k$ switches from $0$ to $V_\text{ref}$ (or vice versa), charge conservation on the top plate gives:

$$\Delta V_\text{dac}^{(k)} = \frac{C_k}{C_\text{total} + C_\text{load}} \cdot V_\text{ref} \cdot (2 b_k - 1)$$

where $b_k \in \{0, 1\}$ is the bit decision (1 = switch toward $V_\text{ref}$, 0 = switch toward GND), and $(2b_k - 1) \in \{-1, +1\}$ gives the correct sign.

For ideal matched capacitors (no mismatch), this simplifies to:

$$\Delta V_\text{dac}^{(k)} = \frac{2^{N-1-k}}{2^N} \cdot V_\text{ref} \cdot (2 b_k - 1) = \frac{V_\text{ref}}{2^{k+1}} \cdot (2 b_k - 1)$$

### PINN Residual Formulation

Let $t_k^-$ and $t_k^+$ denote time instants just before and after bit $k$ switching. The charge conservation residual is:

$$r_\text{charge}^{(k)} = \hat{V}_\text{dac}(t_k^+) - \hat{V}_\text{dac}(t_k^-) - \frac{C_k(1 + \epsilon_k)}{C_\text{total} + C_\text{load}} \cdot V_\text{ref} \cdot (2 b_k - 1)$$

where $\epsilon_k \sim \mathcal{N}(0, \sigma_\text{mismatch}^2)$ is a capacitor mismatch sample included in the design parameter vector $\boldsymbol{\theta}$.

The charge conservation loss sums over all $N$ bit decisions:

$$\mathcal{L}_\text{charge} = \frac{1}{N} \sum_{k=0}^{N-1} \left( r_\text{charge}^{(k)} \right)^2$$

### Physical Significance

This is the most directly circuit-relevant constraint. It ensures the PINN reproduces the quantization step structure of the SAR conversion — the staircase waveform on V_dac. Without this constraint, the network could predict an arbitrary smooth curve that has the right average level but completely wrong step pattern, which would yield correct MSE in a statistical sense but be physically wrong.

The inclusion of $\epsilon_k$ (capacitor mismatch) enables the PINN to learn how DNL/INL degrade gracefully as mismatch increases, which is the primary mechanism behind ENOB reduction in real SAR ADCs.

---

## 3. Comparator Regeneration ODE Residual

### Circuit Background

The dynamic comparator (typically a StrongARM latch or similar topology) regenerates during the evaluation phase. In the small-signal regime, the differential output voltage $V_\text{comp} = V_\text{op} - V_\text{on}$ obeys the cross-coupled latch equation. Modeling the cross-coupled NMOS pair in saturation with transconductance $g_m$ and total load capacitance $C_L$:

$$C_L \frac{dV_\text{comp}}{dt} = g_m V_\text{comp}$$

This is a first-order linear autonomous ODE with solution:

$$V_\text{comp}(t) = V_\text{comp}(0) \cdot \exp\!\left( \frac{g_m}{C_L} t \right), \quad t > 0$$

where $V_\text{comp}(0) = V_\text{in} - V_\text{dac}(t_k)$ is the overdrive voltage (the residue from the DAC at bit $k$).

The regeneration time constant is:

$$\tau_\text{regen} = \frac{C_L}{g_m}$$

A small $\tau_\text{regen}$ (high $g_m$ or small $C_L$) means fast regeneration and low metastability risk. Near-zero overdrive $|V_\text{comp}(0)| \to 0$ represents the metastability condition.

### PINN Residual Formulation

The ODE residual at collocation point $t_j$ within the regeneration window is:

$$r_\text{ode}(t_j) = \frac{\partial \hat{V}_\text{comp}}{\partial t}\bigg|_{t_j} - \frac{g_m}{C_L} \hat{V}_\text{comp}(t_j)$$

The ODE loss is:

$$\mathcal{L}_\text{comp} = \frac{1}{|\mathcal{T}_\text{regen}|} \sum_{j \in \mathcal{T}_\text{regen}} \left( \frac{\partial \hat{V}_\text{comp}}{\partial t}\bigg|_{t_j} - \frac{g_m}{C_L} \hat{V}_\text{comp}(t_j) \right)^2$$

Implementation:

```python
dVcomp_dt = torch.autograd.grad(
    outputs=V_comp_pred,
    inputs=t_colloc,
    grad_outputs=torch.ones_like(V_comp_pred),
    create_graph=True
)[0]

regen_rate = gm / C_load  # scalar, broadcast over batch
r_ode = dVcomp_dt - regen_rate * V_comp_pred
L_ode = torch.mean(r_ode ** 2)
```

### Metastability Implications

The ODE residual directly couples the PINN to the physical phenomenon of metastability. A network that minimizes $\mathcal{L}_\text{comp}$ is constrained to predict exponential regeneration with the *correct time constant* $\tau = C_L / g_m$. This means:

1. The comparator decision time $t_\text{dec}$ (when $|V_\text{comp}|$ exceeds the latch decision threshold $V_\text{th}$) is correctly predicted as a function of overdrive and device parameters.
2. Cases where $|V_\text{comp}(0)|$ is small (near metastability) correctly show slow regeneration, which the PINN can flag as a potential timing violation.
3. Sensitivity $\partial t_\text{dec} / \partial g_m$ can be computed analytically from the PINN, giving a gradient-based metastability margin.

**Note on nonlinear extensions:** The linear ODE is accurate for small differential signals. For large-signal regeneration (deep into saturation), a higher-order ODE with $g_m(V)$ nonlinearity is needed. This is identified as future work in `docs/TECH_REP.md`.

---

## 4. Smoothness Regularization

### Motivation

Even with the three physics constraints above, the network may still predict small-amplitude high-frequency oscillations that are numerically stable (low loss) but physically impossible — a real SAR ADC circuit has no mechanism to generate GHz-rate oscillations on the DAC node. These spurious oscillations arise because the neural network has high-frequency capacity in its activation functions and no bandwidth limitation is built into the architecture.

### Formulation

The smoothness regularizer penalizes the curvature (second time derivative) of both output waveforms:

$$\mathcal{L}_\text{smooth} = \frac{1}{N_t} \sum_j \left[ \left( \frac{\partial^2 \hat{V}_\text{dac}}{\partial t^2}\bigg|_{t_j} \right)^2 + \lambda_\text{comp} \left( \frac{\partial^2 \hat{V}_\text{comp}}{\partial t^2}\bigg|_{t_j} \right)^2 \right]$$

The second derivatives are computed by differentiating through the first-derivative computation graph:

```python
d2Vdac_dt2 = torch.autograd.grad(
    outputs=dVdac_dt,
    inputs=t_colloc,
    grad_outputs=torch.ones_like(dVdac_dt),
    create_graph=True
)[0]
```

The coefficient $\lambda_\text{comp}$ downweights the comparator output's smoothness penalty during the regeneration phase (exponential growth is physically smooth but has high curvature), typically set to $\lambda_\text{comp} = 0.1$.

### Physical Significance

This term acts as a physical bandwidth constraint. Real SAR ADC waveforms are bandlimited by the RC time constants of the circuit. By penalizing high-curvature predictions, the PINN is steered toward waveforms consistent with a finite-bandwidth circuit, even in regions of design space not well-covered by training data.

---

## Differentiability: From Surrogate to Inverse Design Tool

The full PINN forward pass is:

$$(\hat{V}_\text{dac}(t), \hat{V}_\text{comp}(t)) = f_\text{PINN}(t, \boldsymbol{\theta}; \mathbf{W})$$

where $\boldsymbol{\theta} = [C_u, g_m, C_L, V_\text{ref}, I_D, N, \sigma_\text{mm}, \sigma_n, R_\text{dac}]$ and $\mathbf{W}$ are the trained weights (fixed at inference).

Because $f_\text{PINN}$ is a composition of smooth operations (matrix multiplications, GELU activations, Fourier features), it is $C^\infty$ differentiable with respect to $\boldsymbol{\theta}$:

$$\frac{\partial \hat{V}_\text{dac}}{\partial C_u}, \quad \frac{\partial \hat{V}_\text{comp}}{\partial g_m}, \quad \frac{\partial^2 \hat{V}_\text{dac}}{\partial C_u \partial V_\text{ref}}, \quad \ldots$$

are all computable by a single backward pass. This enables:

| Application | Required Derivative |
|---|---|
| Sensitivity analysis | $\nabla_{\boldsymbol{\theta}} \hat{V}_\text{dac}(t)$ |
| ENOB gradient for inverse design | $\partial \text{ENOB} / \partial C_u$ via chain rule through PINN |
| FoM Pareto front generation | $\nabla_{\boldsymbol{\theta}} [\text{FoM}, \text{ENOB}]$ for multi-objective |
| Metastability margin gradient | $\partial t_\text{dec} / \partial g_m$ |
| Noise sensitivity | $\partial \hat{V}_\text{comp} / \partial \sigma_n$ |

This differentiability is the core technical advantage of the PINN approach over lookup-table interpolation or black-box regression models evaluated without physical constraints.

---

## Summary Table

| Residual | Circuit Origin | Enforced Quantity | Loss Term |
|---|---|---|---|
| KCL | Kirchhoff's Current Law | $dV_\text{dac}/dt = 0$ during settling | $\mathcal{L}_\text{kcl}$ |
| Charge conservation | Charge redistribution DAC | $\Delta V_\text{dac}^{(k)} = \frac{C_k}{C_\text{total}} V_\text{ref} (2b_k-1)$ | $\mathcal{L}_\text{charge}$ |
| Comparator ODE | Cross-coupled latch | $\dot{V}_\text{comp} = (g_m/C_L) V_\text{comp}$ | $\mathcal{L}_\text{comp}$ |
| Smoothness | Finite circuit bandwidth | $|\partial^2 V / \partial t^2|$ bounded | $\mathcal{L}_\text{smooth}$ |
