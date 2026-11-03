"""
NeuroSAR loss functions — data fidelity + physics-informed residuals.

Each residual enforces a specific physical law of the SAR ADC front-end.
The total loss is a weighted sum:

    L = w_data * L_data  +  w_kcl * L_kcl  +  w_charge * L_charge
        + w_comp_ode * L_comp_ode  +  w_smooth * L_smooth

All residuals operate on auto-diff-capable tensors so gradients flow
through both the network output and the physics equations.
"""

from typing import Dict

import torch
import torch.nn.functional as F

from src.config import TRAIN, DESIGN


# =========================================================================
# 1.  Data fidelity loss
# =========================================================================

def data_loss(
    pred: Dict[str, torch.Tensor],
    target: Dict[str, torch.Tensor],
) -> torch.Tensor:
    """
    MSE between predicted and reference waveforms.

    Covers vdac (per-trial scalar), vdiff(t), vcomp(t), and energy.
    """
    loss = torch.tensor(0.0, device=pred["vdac"].device)

    # vdac — scalar per bit trial
    loss = loss + F.mse_loss(pred["vdac"], target["vdac"])

    # vdiff — waveform
    loss = loss + F.mse_loss(pred["vdiff"], target["vdiff"])

    # vcomp — waveform
    loss = loss + F.mse_loss(pred["vcomp"], target["vcomp"])

    # energy — scalar
    if "energy" in pred and "energy" in target:
        loss = loss + F.mse_loss(pred["energy"], target["energy"])

    return loss


# =========================================================================
# 2.  KCL residual — current conservation at the DAC node
# =========================================================================

def kcl_residual(
    vdac: torch.Tensor,
    vdiff: torch.Tensor,
    t_local: torch.Tensor,
    cu: torch.Tensor,
    cload: torch.Tensor,
    n_bits: int = DESIGN.n_bits,
) -> torch.Tensor:
    """
    At the DAC output node, KCL requires:

        C_total * dVdac/dt = I_cap_array − I_load

    For the simplified settling model:
        C_total * dVdac/dt + C_load * dVdac/dt ≈ 0  (after switching)

    The residual is:  (C_total + C_load) * dVdac/dt ≈ 0  during settling.

    We penalise |dVdiff/dt| at later time steps (where the DAC should have
    settled), enforcing that the physics model's settling is respected.

    Parameters
    ----------
    vdac   : (B, T) or (B,) — predicted DAC voltage
    vdiff  : (B, T) — predicted differential waveform
    t_local: (T,) — time axis
    cu     : (B,) — unit capacitor
    cload  : (B,) — load capacitor
    """
    if vdiff.dim() < 2 or vdiff.shape[-1] < 2:
        return torch.tensor(0.0, device=vdiff.device)

    dt = t_local[1] - t_local[0] + 1e-15
    dvdiff_dt = torch.diff(vdiff, dim=-1) / dt  # (B, T-1)

    c_total = cu * (2 ** n_bits)
    c_sum = (c_total + cload).unsqueeze(-1)  # (B, 1)

    # KCL residual: capacitive current should vanish at steady state
    # Weight later time points more heavily (settling region)
    T = dvdiff_dt.shape[-1]
    time_weight = torch.linspace(0.2, 1.0, T, device=vdiff.device)

    residual = c_sum * dvdiff_dt * time_weight
    return (residual ** 2).mean()


# =========================================================================
# 3.  Charge conservation residual
# =========================================================================

def charge_conservation_residual(
    vdac_pred: torch.Tensor,
    params: torch.Tensor,
    bits: torch.Tensor,
    n_bits: int = DESIGN.n_bits,
) -> torch.Tensor:
    """
    Charge conservation across each switching event.

    After trial k, the charge on the DAC node is:
        Q_k = C_total * V_dac[k]

    The charge change must equal:
        ΔQ_k = C_k * Vref * (2*bit_k - 1)

    Residual = |ΔV_pred - ΔV_physics|^2 summed over bit trials.

    Parameters
    ----------
    vdac_pred : (B, n_bits) — predicted DAC voltage at each trial end
    params    : (B, 9) — design parameters [vin, vref, cu, cload, ...]
    bits      : (B, n_bits) — bit decisions
    """
    vref  = params[:, 1]   # (B,)
    cu    = params[:, 2]   # (B,)
    cload = params[:, 3]   # (B,)
    c_total = cu * (2 ** n_bits)
    c_denom = c_total + cload

    residual = torch.tensor(0.0, device=vdac_pred.device)

    for k in range(n_bits - 1):
        c_k = cu * (2 ** (n_bits - 1 - k))
        delta_v_physics = c_k / c_denom * vref * (2.0 * bits[:, k] - 1.0)
        delta_v_pred = vdac_pred[:, k + 1] - vdac_pred[:, k]
        residual = residual + ((delta_v_pred - delta_v_physics) ** 2).mean()

    return residual / max(n_bits - 1, 1)


# =========================================================================
# 4.  Comparator ODE residual
# =========================================================================

def comparator_ode_residual(
    vcomp: torch.Tensor,
    t_local: torch.Tensor,
    gm: torch.Tensor,
    cl: torch.Tensor,
) -> torch.Tensor:
    """
    The cross-coupled latch obeys:

        dVcomp/dt = (gm / CL) * Vcomp     (regeneration ODE)

    Residual = |dVcomp/dt − (gm/CL) * Vcomp|^2

    This is the defining equation of regenerative amplification.
    Enforcing it in the loss ensures the PINN cannot learn an
    unphysical comparator response.

    Parameters
    ----------
    vcomp  : (B, T)
    t_local: (T,)
    gm     : (B,) — transconductance
    cl     : (B,) — latch load capacitance
    """
    if vcomp.shape[-1] < 2:
        return torch.tensor(0.0, device=vcomp.device)

    dt = t_local[1] - t_local[0] + 1e-15

    # Numerical derivative
    dvcomp_dt = torch.diff(vcomp, dim=-1) / dt  # (B, T-1)

    # Expected rate from ODE
    tau_inv = (gm / (cl + 1e-15)).unsqueeze(-1)  # (B, 1)
    vcomp_mid = 0.5 * (vcomp[:, 1:] + vcomp[:, :-1])  # mid-point
    expected_rate = tau_inv * vcomp_mid

    # Mask out rail-limited region (|vcomp| > 0.95 * VDD)
    mask = (torch.abs(vcomp_mid) < 0.95 * 1.8).float()

    residual = mask * (dvcomp_dt - expected_rate) ** 2
    return residual.mean()


# =========================================================================
# 5.  Smoothness regularisation
# =========================================================================

def smoothness_loss(
    vdiff: torch.Tensor,
    vcomp: torch.Tensor,
) -> torch.Tensor:
    """
    Penalise second-order finite differences (curvature) to discourage
    high-frequency artefacts that have no physical origin.
    """
    loss = torch.tensor(0.0, device=vdiff.device)
    for v in (vdiff, vcomp):
        if v.dim() >= 2 and v.shape[-1] > 2:
            d2 = v[..., 2:] - 2 * v[..., 1:-1] + v[..., :-2]
            loss = loss + (d2 ** 2).mean()
    return loss


# =========================================================================
# Total weighted loss
# =========================================================================

def total_pinn_loss(
    pred: Dict[str, torch.Tensor],
    target: Dict[str, torch.Tensor],
    params: torch.Tensor,
    t_local: torch.Tensor,
    bits: torch.Tensor,
    n_bits: int = DESIGN.n_bits,
    weights: Dict[str, float] = None,
) -> Dict[str, torch.Tensor]:
    """
    Compute the full PINN loss with all residual terms.

    Returns a dict with individual terms and 'total'.
    """
    w = weights or {}
    w_data   = w.get("data",     TRAIN.w_data)
    w_kcl    = w.get("kcl",      TRAIN.w_kcl)
    w_charge = w.get("charge",   TRAIN.w_charge)
    w_comp   = w.get("comp_ode", TRAIN.w_comp_ode)
    w_sm     = w.get("smooth",   TRAIN.w_smooth)

    # Extract design params
    cu    = params[:, 2]
    cload = params[:, 3]
    gm    = params[:, 4]
    cl    = cload  # comparator load ≈ DAC load for this abstraction

    # Individual terms
    l_data   = data_loss(pred, target)
    l_kcl    = kcl_residual(pred["vdac"].squeeze(-1), pred["vdiff"], t_local, cu, cload, n_bits)

    # For charge conservation, we need vdac per bit trial (B, n_bits).
    # During training, the model predicts one trial at a time (B, 1).
    # Skip charge residual when we only have a single-trial prediction.
    vdac_flat = pred["vdac"].squeeze(-1)
    if vdac_flat.dim() >= 2 and vdac_flat.shape[-1] >= 2:
        l_charge = charge_conservation_residual(vdac_flat, params, bits, n_bits)
    else:
        l_charge = torch.tensor(0.0, device=vdac_flat.device)
    l_comp   = comparator_ode_residual(pred["vcomp"], t_local, gm, cl)
    l_smooth = smoothness_loss(pred["vdiff"], pred["vcomp"])

    total = (
        w_data * l_data
        + w_kcl * l_kcl
        + w_charge * l_charge
        + w_comp * l_comp
        + w_sm * l_smooth
    )

    return {
        "total":     total,
        "data":      l_data,
        "kcl":       l_kcl,
        "charge":    l_charge,
        "comp_ode":  l_comp,
        "smooth":    l_smooth,
    }
