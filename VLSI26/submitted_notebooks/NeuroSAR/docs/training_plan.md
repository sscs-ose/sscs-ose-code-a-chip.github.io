# Training Plan: Feature Engineering, Loss Strategy, and Evaluation

This document describes the complete training pipeline for NeuroSAR, including feature definitions, encoding strategies, data splitting, loss weight selection, checkpointing, and evaluation metrics.

---

## 1. Design Parameter Space (9 + 2 Dimensions)

The PINN input is an 11-dimensional vector: 9 circuit design parameters, 1 time variable, and 1 bit index.

### Circuit Design Parameters

| # | Symbol | Description | Range | Units | Scale |
|---|---|---|---|---|---|
| 1 | $C_u$ | Unit capacitor size | 0.5 – 5.0 | fF | log |
| 2 | $g_m$ | Comparator transconductance | 0.5 – 5.0 | mS | log |
| 3 | $C_L$ | Comparator load capacitance | 10 – 100 | fF | log |
| 4 | $V_\text{ref}$ | Reference voltage | 0.8 – 1.8 | V | linear |
| 5 | $I_D$ | Bias current | 10 – 200 | µA | log |
| 6 | $N$ | ADC resolution | 8 – 12 | bits | integer |
| 7 | $\sigma_\text{mm}$ | Capacitor mismatch std dev | 0.0 – 2.0 | % | linear |
| 8 | $\sigma_n$ | Input-referred voltage noise | 0.0 – 2.0 | mV$_\text{rms}$ | linear |
| 9 | $R_\text{dac}$ | DAC switch on-resistance | 10 – 500 | Ω | log |

**Sampling strategy:** Latin hypercube sampling (LHS) is used over the normalized parameter space to ensure uniform coverage of the 9-D design space. Log-scaled parameters are sampled uniformly in log space.

### Time Variable

| Symbol | Description | Range | Resolution |
|---|---|---|---|
| $t$ | Normalized time within conversion cycle | [0, 1] | 512 points per trace |

The raw time axis is normalized to $[0, 1]$ by dividing by $T_\text{conv} = N / f_s$, where $f_s = 1$ MS/s.

### Bit Index

| Symbol | Description | Range |
|---|---|---|
| $k$ | Current bit being resolved | 0 (MSB) to $N-1$ (LSB) |

The bit index encodes which phase of the SAR algorithm the waveform point belongs to. It is concatenated directly as an integer-normalized scalar in $[0, 1]$.

---

## 2. Fourier Feature Encoding for the Time Axis

Vanilla neural networks with standard activations struggle to learn sharp transitions and multi-scale temporal structure from a single scalar time input. The DAC staircase has:
- **Sharp edges** at bit-decision boundaries (~1–5 ns transitions)
- **Smooth settling** within each bit interval (~20–100 ns)
- **Exponential regeneration** on V_comp (~1–10 ns time constants)

To address the "spectral bias" (tendency of deep networks to learn low-frequency components first), NeuroSAR uses **random Fourier feature (RFF) encoding** on the time input:

$$\gamma(t) = \left[ \sin(2\pi \mathbf{b}_1 t), \cos(2\pi \mathbf{b}_1 t), \ldots, \sin(2\pi \mathbf{b}_m t), \cos(2\pi \mathbf{b}_m t) \right]$$

where $\mathbf{b} \in \mathbb{R}^m$ is sampled from $\mathcal{N}(0, \sigma_\text{ff}^2)$ at initialization and **frozen** during training.

### Configuration

| Parameter | Value | Rationale |
|---|---|---|
| $m$ (number of Fourier features) | 64 | Sufficient to resolve transitions at 1 ns in a 10 µs window |
| $\sigma_\text{ff}$ | 10.0 | Covers frequencies up to ~30× the fundamental conversion frequency |
| Frozen weights | Yes | RFF theory requires fixed random projection |

After Fourier encoding, the time feature dimension expands from 1 to $2m = 128$. The encoded time vector is concatenated with the 10 design parameters (9 circuit params + bit index) for a total input dimension of $128 + 10 = 138$.

---

## 3. Network Architecture

```
Input: [γ(t) ∈ ℝ^128, θ ∈ ℝ^10]  → ℝ^138
Dense(138 → 256)  + LayerNorm + GELU
Dense(256 → 256)  + LayerNorm + GELU
Dense(256 → 128)  + LayerNorm + GELU
Dense(128 → 128)  + LayerNorm + GELU
Dense(128 → 64)   + LayerNorm + GELU
Dense(64 → 2)     [V_dac, V_comp]
```

- **Activation:** GELU (smooth, differentiable; avoids kink-induced noise in second derivatives)
- **Normalization:** LayerNorm (preferred over BatchNorm for physics applications to avoid batch-size dependence of normalized statistics)
- **Output:** Two scalar outputs per (t, θ) query — no sigmoid/tanh output activation, as DAC and comparator voltages span variable ranges

**Parameter count:** ~270k trainable parameters.

---

## 4. Dataset Construction

### Waveform Generation

Each training sample is a tuple:
- **Input:** $(t_j, \boldsymbol{\theta}_i)$ — one time point and one design parameter vector
- **Output:** $(V_\text{dac}(t_j; \boldsymbol{\theta}_i),\, V_\text{comp}(t_j; \boldsymbol{\theta}_i))$

For $N_\text{traces} = 50{,}000$ parameter samples and $N_t = 512$ time points per trace, the full dataset has $50{,}000 \times 512 = 25.6\text{M}$ point-wise samples. Training on the full dataset at once is memory-intensive; mini-batching over traces is used.

### Train / Validation Split

| Split | Fraction | Traces | Points |
|---|---|---|---|
| Training | 85% | 42,500 | ~21.8M |
| Validation | 15% | 7,500 | ~3.8M |

Split is performed at the trace level (not the point level), ensuring no time points from the same trace appear in both splits. A fixed random seed (42) is used for reproducibility.

```python
from sklearn.model_selection import train_test_split

idx = np.arange(N_traces)
idx_train, idx_val = train_test_split(idx, test_size=0.15, random_state=42)
```

---

## 5. Loss Balancing Strategy

The multi-objective loss requires careful weight assignment to ensure no single term dominates, while still giving physics residuals enough influence to constrain the solution.

### Loss Terms and Default Weights

| Term | Symbol | Default Weight | Role |
|---|---|---|---|
| Data MSE | $w_\text{data}$ | 1.0 | Supervised accuracy on labeled waveform samples |
| KCL residual | $w_\text{kcl}$ | 0.1 | Enforce charge flow conservation |
| Charge conservation | $w_\text{charge}$ | 0.5 | Enforce DAC step accuracy |
| Comparator ODE | $w_\text{ode}$ | 0.2 | Enforce regeneration dynamics |
| Smoothness | $w_\text{smooth}$ | 0.05 | Suppress spurious oscillations |

These weights are set in `training/config.yaml` and can be overridden via command-line arguments.

### Loss Magnitude Normalization

Before applying weights, each loss term is normalized by its initial value at epoch 0:

$$\tilde{\mathcal{L}}_k = \frac{\mathcal{L}_k}{\mathcal{L}_k^{(0)}}$$

This ensures that all terms start at approximately 1.0 and the weights directly express their relative importance, independent of the absolute magnitude of each residual.

### Tips for Tuning Loss Weights

1. **Start with data loss only** (`w_kcl = w_charge = w_ode = w_smooth = 0`). Confirm the network can fit the data before adding physics constraints. A well-fitted data-only model achieves $R^2 > 0.95$ on V_dac within 50 epochs.

2. **Add charge conservation first** (`w_charge = 0.5`). This is the most directly interpretable constraint. If increasing $w_\text{charge}$ causes training instability, check that the bit-decision time indices in the dataset metadata are correct.

3. **Increase KCL and ODE weights gradually.** Physics residuals require $\partial / \partial t$ through the network, which can cause gradient norm spikes early in training. Use gradient clipping (`clip_grad_norm = 1.0`) when using physics loss terms.

4. **If the KCL residual loss does not decrease** after 100 epochs, the collocation points may be placed in the switching transients (where $dV/dt \neq 0$ is physically correct). Check that settling window masks are correctly excluding switching events.

5. **If the ODE residual loss does not decrease**, verify that $g_m / C_L$ is computed correctly from the normalized parameter values (not from raw unnormalized inputs).

6. **Smoothness weight** should be kept small ($w_\text{smooth} \leq 0.1$). Large smoothness penalties will cause the network to predict overly damped transitions, reducing DAC step sharpness.

---

## 6. Optimizer and Schedule

| Hyperparameter | Value |
|---|---|
| Optimizer | AdamW |
| Initial learning rate | 3×10⁻⁴ |
| Weight decay | 1×10⁻⁵ |
| Scheduler | Cosine annealing with warm restarts |
| $T_0$ (restart period) | 100 epochs |
| $\eta_\text{min}$ | 1×10⁻⁶ |
| Batch size | 256 traces (131k points/batch) |
| Gradient clipping | max norm = 1.0 |
| Total epochs | 500 |

---

## 7. Checkpointing

Checkpoints are saved to `models/checkpoints/` using the following naming convention:

```
checkpoint_epoch{epoch:04d}_val{val_loss:.4e}.pt
best_model.pt
```

The `best_model.pt` file is overwritten whenever a new minimum validation loss is achieved. Periodic saves occur every 25 epochs regardless of improvement.

### Checkpoint Contents

Each `.pt` file contains:

```python
{
    'epoch': int,
    'model_state_dict': OrderedDict,
    'optimizer_state_dict': OrderedDict,
    'scheduler_state_dict': OrderedDict,
    'val_loss': float,
    'train_loss': float,
    'loss_weights': dict,
    'config': dict,
    'rng_state': torch.ByteTensor,   # for exact reproducibility
    'numpy_rng_state': object
}
```

### Loading a Checkpoint

```python
from models.pinn import NeuroSARPINN
import torch

model = NeuroSARPINN(config)
ckpt = torch.load('models/checkpoints/best_model.pt', map_location='cpu')
model.load_state_dict(ckpt['model_state_dict'])
model.eval()
```

---

## 8. Evaluation Metrics

The following metrics are computed on the held-out validation set after training completes.

### Per-Output Metrics

| Metric | Formula | Applied To | Target |
|---|---|---|---|
| MSE | $\frac{1}{N}\sum(\hat{y}-y)^2$ | V_dac, V_comp | < 1×10⁻⁴ V² |
| RMSE | $\sqrt{\text{MSE}}$ | V_dac, V_comp | < 1 mV |
| MAE | $\frac{1}{N}\sum|\hat{y}-y|$ | V_dac | < 0.5 mV |
| R² | $1 - \text{SS}_\text{res}/\text{SS}_\text{tot}$ | V_comp | > 0.99 |
| Max absolute error | $\max|\hat{y}-y|$ | V_dac | < 5 mV |

### Physics Residual Metrics (Validation Set)

| Metric | Description | Target |
|---|---|---|
| KCL violation rate | Fraction of settling points with $|dV_\text{dac}/dt| > 10^6$ V/s | < 1% |
| Charge error (LSB) | $r_\text{charge}$ in units of LSB = $V_\text{ref} / 2^N$ | < 0.1 LSB RMS |
| ODE fit $R^2$ | $R^2$ of linear fit $\dot{V}_\text{comp}$ vs $(g_m/C_L) V_\text{comp}$ | > 0.98 |

### ADC-Level Metrics (Derived from PINN Predictions)

| Metric | Computation | Description |
|---|---|---|
| ENOB | Derived from INL/DNL of predicted DAC steps | Effective number of bits |
| Walden FoM | $P / (2^\text{ENOB} \cdot f_s)$ | Figure of merit [fJ/conv-step] |
| Regeneration time | Time for $|V_\text{comp}|$ to exceed $0.9 V_\text{DD}$ | Comparator speed |
| Metastability prob. | $P(t_\text{regen} > T_\text{clk})$ | Bit-error rate due to metastability |

---

## 9. Logging and Monitoring

Training progress is logged to both stdout and a `training/logs/run_{timestamp}.csv` file with columns:

```
epoch, t_elapsed, lr, L_total, L_data, L_kcl, L_charge, L_ode, L_smooth,
val_L_total, val_L_data, val_L_kcl, val_L_charge, val_L_ode, val_L_smooth,
val_mse_vdac, val_mse_vcomp, val_r2_vcomp, val_mae_vdac
```

Loss curves can be plotted with:

```bash
python training/plot_logs.py --log training/logs/run_YYYYMMDD_HHMMSS.csv
```
