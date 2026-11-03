"""
NeuroSAR PINN architecture — a multi-output physics-informed neural
network that maps (design_params, t_local, bit_index) → (vdac, vdiff, vcomp).

Key design choices
------------------
- **Tanh activations** preserve smooth second derivatives needed for
  physics residuals (KCL, ODE).
- **Separate output heads** for vdac (scalar per trial), vdiff(t),
  and vcomp(t) allow different physics constraints per output.
- **Fourier feature encoding** of the time axis improves learning of
  oscillatory / exponential transient behaviour.
"""

from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import numpy as np

from src.config import TRAIN, DESIGN


# =========================================================================
# Fourier feature embedding (Tancik et al., 2020)
# =========================================================================

class FourierFeatures(nn.Module):
    """
    Map scalar input t to [sin(2π σ_i t), cos(2π σ_i t)] for a bank
    of learned or fixed frequencies.  Dramatically improves fitting of
    high-frequency transient content.
    """

    def __init__(self, n_freqs: int = 32, sigma: float = 10.0):
        super().__init__()
        B = torch.randn(1, n_freqs) * sigma
        self.register_buffer("B", B)

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """t: (..., 1) → (..., 2*n_freqs)"""
        proj = 2.0 * np.pi * t @ self.B  # (..., n_freqs)
        return torch.cat([torch.sin(proj), torch.cos(proj)], dim=-1)


# =========================================================================
# Core PINN network
# =========================================================================

class NeuroSARNet(nn.Module):
    """
    Multi-head physics-informed surrogate for SAR ADC transients.

    Inputs
    ------
    design_params : (B, D)   D = 9 design parameters
    t_local       : (B, T)   normalised local time within bit window
    bit_index     : (B, 1)   which bit trial (0 = MSB)

    Outputs (dict)
    -------
    vdac  : (B, 1)       — DAC node voltage at end of this trial
    vdiff : (B, T)       — differential voltage waveform over time
    vcomp : (B, T)       — comparator regeneration waveform over time
    energy: (B, 1)       — estimated per-cycle energy contribution
    """

    def __init__(
        self,
        n_design: int = 9,
        n_bits: int = DESIGN.n_bits,
        n_time: int = DESIGN.n_time_steps,
        hidden_dims: Tuple[int, ...] = TRAIN.hidden_dims,
        n_fourier: int = 32,
        activation: str = TRAIN.activation,
    ):
        super().__init__()
        self.n_design = n_design
        self.n_bits = n_bits
        self.n_time = n_time

        # Activation
        act_fn = {"tanh": nn.Tanh, "gelu": nn.GELU, "silu": nn.SiLU}[activation]

        # Fourier encoding for time
        self.time_enc = FourierFeatures(n_freqs=n_fourier)
        time_feat_dim = 2 * n_fourier

        # Input dimension: design params + bit index + time features
        in_dim = n_design + 1 + time_feat_dim

        # Shared trunk
        trunk_layers = []
        prev = in_dim
        for h in hidden_dims:
            trunk_layers.append(nn.Linear(prev, h))
            trunk_layers.append(act_fn())
            prev = h
        self.trunk = nn.Sequential(*trunk_layers)

        # Output heads
        self.head_vdac  = nn.Sequential(
            nn.Linear(prev, 64), act_fn(), nn.Linear(64, 1)
        )
        self.head_vdiff = nn.Sequential(
            nn.Linear(prev, 128), act_fn(), nn.Linear(128, n_time)
        )
        self.head_vcomp = nn.Sequential(
            nn.Linear(prev, 128), act_fn(), nn.Linear(128, n_time)
        )
        self.head_energy = nn.Sequential(
            nn.Linear(prev, 64), act_fn(), nn.Linear(64, 1), nn.Softplus()
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight, gain=0.5)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(
        self,
        design_params: torch.Tensor,
        t_local: torch.Tensor,
        bit_index: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass.

        Parameters
        ----------
        design_params : (B, 9)
        t_local       : (B, T) or (T,)
        bit_index     : (B, 1) or (B,)
        """
        B = design_params.shape[0]

        # Normalise bit index to [0, 1]
        if bit_index.dim() == 1:
            bit_index = bit_index.unsqueeze(-1)
        bit_norm = bit_index.float() / max(self.n_bits - 1, 1)

        # Time features — use middle time point for the trunk
        if t_local.dim() == 1:
            t_local = t_local.unsqueeze(0).expand(B, -1)
        t_mid = t_local[:, t_local.shape[1] // 2].unsqueeze(-1)  # (B, 1)
        t_feat = self.time_enc(t_mid)  # (B, 2*n_fourier)

        # Concatenate input
        x = torch.cat([design_params, bit_norm, t_feat], dim=-1)  # (B, in_dim)

        # Shared trunk
        h = self.trunk(x)

        return {
            "vdac":   self.head_vdac(h),         # (B, 1)
            "vdiff":  self.head_vdiff(h),         # (B, T)
            "vcomp":  self.head_vcomp(h),         # (B, T)
            "energy": self.head_energy(h),        # (B, 1)
        }


# =========================================================================
# Helper: full-conversion forward pass
# =========================================================================

def predict_full_conversion(
    model: NeuroSARNet,
    design_params: torch.Tensor,
    t_local: torch.Tensor,
    n_bits: int = DESIGN.n_bits,
) -> Dict[str, torch.Tensor]:
    """
    Run the model over all bit trials for a batch of design points.

    Returns
    -------
    vdac_all  : (B, n_bits)
    vdiff_all : (B, n_bits, T)
    vcomp_all : (B, n_bits, T)
    energy    : (B,) — summed across bit trials
    """
    B = design_params.shape[0]
    T = t_local.shape[-1] if t_local.dim() > 0 else DESIGN.n_time_steps
    device = design_params.device

    vdac_list  = []
    vdiff_list = []
    vcomp_list = []
    energy_sum = torch.zeros(B, device=device)

    model.eval()
    with torch.no_grad():
        for k in range(n_bits):
            bit_idx = torch.full((B,), k, dtype=torch.float32, device=device)
            out = model(design_params, t_local, bit_idx)
            vdac_list.append(out["vdac"].squeeze(-1))
            vdiff_list.append(out["vdiff"])
            vcomp_list.append(out["vcomp"])
            energy_sum += out["energy"].squeeze(-1)

    return {
        "vdac":   torch.stack(vdac_list, dim=1),   # (B, n_bits)
        "vdiff":  torch.stack(vdiff_list, dim=1),   # (B, n_bits, T)
        "vcomp":  torch.stack(vcomp_list, dim=1),   # (B, n_bits, T)
        "energy": energy_sum,                        # (B,)
    }
