"""
NeuroSAR inverse design — use gradients through the trained PINN
surrogate to optimise design parameters towards a target specification.

Example objective:
    Minimise metastability dwell time while keeping energy below a budget.

Because the PINN is a differentiable function of design parameters,
we can back-propagate through it and update the parameters directly.
This is fundamentally impossible with a non-differentiable SPICE
simulator, which is the core value proposition.
"""

from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from src.config import DESIGN
from src.utils import get_device, to_tensor
from src.pinn_model import NeuroSARNet, predict_full_conversion
from src.physics import metastability_dwell, enob_proxy
from src.dataset import DESIGN_PARAM_NAMES


# =========================================================================
# Differentiable design-parameter wrapper
# =========================================================================

class DesignParameterSet(nn.Module):
    """
    Wraps a design parameter vector as a learnable nn.Parameter
    so that torch.optim can update it.

    Clamping is applied after each step to keep values physical.
    """

    def __init__(
        self,
        init_values: Dict[str, float],
        optimisable: List[str],
    ):
        super().__init__()
        self.param_names = DESIGN_PARAM_NAMES
        self.optimisable = set(optimisable)

        vals = [init_values.get(k, 0.0) for k in self.param_names]
        self._raw = nn.Parameter(torch.tensor(vals, dtype=torch.float32))

        # Store which indices are optimisable
        self._opt_mask = torch.tensor(
            [1.0 if k in self.optimisable else 0.0 for k in self.param_names]
        )

        # Clamping bounds
        D = DESIGN
        self._lo = torch.tensor([
            D.vin_range[0], D.vref, D.cu_range[0], D.cload_range[0],
            D.gm_range[0], D.tau_range[0], D.vos_range[0],
            D.temp_range[0], D.fs_range[0],
        ])
        self._hi = torch.tensor([
            D.vin_range[1], D.vref, D.cu_range[1], D.cload_range[1],
            D.gm_range[1], D.tau_range[1], D.vos_range[1],
            D.temp_range[1], D.fs_range[1],
        ])

    def forward(self) -> torch.Tensor:
        """Return (1, 9) parameter tensor."""
        return self._raw.unsqueeze(0)

    @torch.no_grad()
    def clamp(self):
        """Project parameters back into the feasible design space."""
        self._raw.data.clamp_(self._lo.to(self._raw.device),
                               self._hi.to(self._raw.device))

    @torch.no_grad()
    def zero_frozen_grads(self):
        """Zero out gradients for non-optimisable parameters."""
        if self._raw.grad is not None:
            mask = self._opt_mask.to(self._raw.device)
            self._raw.grad.mul_(mask)

    def to_dict(self) -> Dict[str, float]:
        with torch.no_grad():
            return {k: self._raw[i].item() for i, k in enumerate(self.param_names)}


# =========================================================================
# Objective functions
# =========================================================================

def metastability_energy_objective(
    model: NeuroSARNet,
    params: torch.Tensor,
    t_local: torch.Tensor,
    energy_budget: float = 1e-12,
    meta_weight: float = 1.0,
    energy_penalty: float = 10.0,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """
    Objective: minimise metastability risk subject to an energy budget.

    L = meta_weight * max_meta_dwell
        + energy_penalty * max(0, energy - budget)

    Returns (loss, info_dict).
    """
    result = predict_full_conversion(model, params, t_local, DESIGN.n_bits)

    # Metastability: proxy from vdac residues
    vdac = result["vdac"][0]
    residues = vdac - params[0, 1] / 2.0  # vref / 2
    gm = params[0, 4]
    cl = params[0, 3]
    t_meta = metastability_dwell(residues, gm.unsqueeze(0), cl.unsqueeze(0))
    max_meta = t_meta.max()

    energy = result["energy"][0]

    # Penalty for exceeding energy budget
    energy_excess = torch.relu(energy - energy_budget)

    loss = meta_weight * max_meta + energy_penalty * energy_excess

    info = {
        "loss": loss.item(),
        "max_meta_s": max_meta.item(),
        "energy_j": energy.item(),
        "energy_excess": energy_excess.item(),
    }
    return loss, info


# =========================================================================
# Inverse design optimisation loop
# =========================================================================

def run_inverse_design(
    model: NeuroSARNet,
    initial_params: Dict[str, float],
    optimisable: List[str] = ["cu", "gm"],
    n_steps: int = 200,
    lr: float = 1e-4,
    energy_budget: float = 1e-12,
    meta_weight: float = 1.0,
    energy_penalty: float = 10.0,
    verbose: bool = True,
) -> Dict[str, object]:
    """
    Run gradient-based inverse design.

    Parameters
    ----------
    model           : trained PINN (frozen)
    initial_params  : starting design point
    optimisable     : which parameters to update
    n_steps         : optimisation iterations
    lr              : learning rate for design params
    energy_budget   : energy ceiling (J)

    Returns
    -------
    dict with: trajectory (list of dicts), final_params, final_info
    """
    device = next(model.parameters()).device
    model.eval()

    # Freeze model weights
    for p in model.parameters():
        p.requires_grad_(False)

    design = DesignParameterSet(initial_params, optimisable).to(device)
    opt = torch.optim.Adam(design.parameters(), lr=lr)

    t_local = torch.linspace(0, 1, DESIGN.n_time_steps, device=device)

    trajectory = []

    for step in range(1, n_steps + 1):
        opt.zero_grad()
        params = design()

        loss, info = metastability_energy_objective(
            model, params, t_local,
            energy_budget=energy_budget,
            meta_weight=meta_weight,
            energy_penalty=energy_penalty,
        )

        loss.backward()
        design.zero_frozen_grads()
        opt.step()
        design.clamp()

        step_info = {"step": step, **info, **design.to_dict()}
        trajectory.append(step_info)

        if verbose and (step % 20 == 0 or step == 1):
            print(
                f"  Step {step:4d} | loss {info['loss']:.4e} | "
                f"meta {info['max_meta_s']:.3e} s | "
                f"energy {info['energy_j']:.3e} J | "
                + " | ".join(f"{k}={design.to_dict()[k]:.3e}" for k in optimisable)
            )

    final_params = design.to_dict()
    print(f"\n[NeuroSAR] Inverse design complete.")
    print(f"  Final: " + " | ".join(f"{k}={v:.4e}" for k, v in final_params.items()
                                       if k in optimisable))

    return {
        "trajectory": trajectory,
        "final_params": final_params,
        "final_info": trajectory[-1],
    }
