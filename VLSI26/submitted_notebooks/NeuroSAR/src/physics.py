"""
NeuroSAR physics kernel — analytical / semi-analytical models of a
charge-redistribution SAR ADC front-end.

All equations are written in PyTorch so they are auto-differentiable
and can be used both for (a) synthetic data generation and
(b) physics-informed residual computation inside the PINN loss.

Key physical models
-------------------
1. **Capacitive DAC charge redistribution** — binary-weighted cap array,
   KCL at the DAC output node with parasitic load.
2. **Comparator large-signal regeneration** — cross-coupled latch modelled
   as a first-order ODE  dVdiff/dt = (gm/CL) * Vdiff  during the
   regeneration phase, with a pre-amp gain stage.
3. **Metastability dwell** — time for |Vdiff| to reach a decision
   threshold given initial residue.
4. **Energy model** — switching energy of binary cap array plus
   comparator dynamic power.

Reference coordinate: differential DAC output voltage around Vcm = Vref/2.
"""

from typing import Tuple

import torch
import numpy as np


# ── constants ────────────────────────────────────────────────────────────
K_BOLTZMANN = 1.380649e-23   # J/K
Q_ELECTRON  = 1.602176634e-19  # C
VDD_NOM     = 1.8              # Sky130 nominal supply


# =========================================================================
# 1.  Capacitive DAC model
# =========================================================================

def dac_total_cap(cu: torch.Tensor, n_bits: int) -> torch.Tensor:
    """Total capacitance of binary-weighted array: C_total = 2^n * Cu."""
    return cu * (2 ** n_bits)


def dac_trial_voltage(
    vin: torch.Tensor,
    vref: torch.Tensor,
    cu: torch.Tensor,
    cload: torch.Tensor,
    bit_decisions: torch.Tensor,
    n_bits: int,
) -> torch.Tensor:
    """
    Compute DAC output voltage after charge redistribution.

    During sampling: Vdac = Vin.
    At bit trial `k` (MSB-first), the DAC toggles cap C_k = 2^(n-1-k) * Cu
    from GND to Vref (if bit=1) or Vref to GND (if bit=0).

    Charge conservation at each step:
        (C_total + C_load) * ΔV = C_k * (2*bit_k - 1) * Vref

    Parameters
    ----------
    vin          : (B,)  sampled input voltage
    vref         : (B,)  reference voltage
    cu           : (B,)  unit capacitor value
    cload        : (B,)  parasitic load capacitance
    bit_decisions: (B, n_bits)  binary decisions {0, 1}
    n_bits       : int

    Returns
    -------
    vdac : (B, n_bits+1) — DAC node voltage after each trial,
           index 0 is the sampled value (= vin).
    """
    B = vin.shape[0]
    c_total = dac_total_cap(cu, n_bits)            # (B,)
    c_denom = c_total + cload                      # (B,)

    vdac = torch.zeros(B, n_bits + 1, device=vin.device, dtype=vin.dtype)
    vdac[:, 0] = vin

    for k in range(n_bits):
        c_k = cu * (2 ** (n_bits - 1 - k))        # cap weight for bit k
        # Charge packet sign: bit=1 → +Vref, bit=0 → –Vref
        delta_v = c_k / c_denom * vref * (2.0 * bit_decisions[:, k] - 1.0)
        vdac[:, k + 1] = vdac[:, k] + delta_v

    return vdac  # (B, n_bits+1)


def dac_settling(
    vdac_step: torch.Tensor,
    vdac_final: torch.Tensor,
    t_local: torch.Tensor,
    tau_settle: torch.Tensor,
) -> torch.Tensor:
    """
    Exponential settling model for each DAC step.
    v(t) = v_final + (v_step - v_final) * exp(-t / tau_settle)

    Returns continuous waveform value at local time t_local.
    """
    return vdac_final + (vdac_step - vdac_final) * torch.exp(-t_local / (tau_settle + 1e-15))


# =========================================================================
# 2.  Comparator regeneration model
# =========================================================================

def comparator_regeneration(
    v_residue: torch.Tensor,
    gm: torch.Tensor,
    cl: torch.Tensor,
    vos: torch.Tensor,
    t_local: torch.Tensor,
    v_preamp_gain: float = 4.0,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Large-signal comparator model (cross-coupled latch).

    Phase 1 — Pre-amplification (linear):
        V_in_comp = v_preamp_gain * (v_residue + vos)

    Phase 2 — Regeneration (exponential ODE):
        dVdiff/dt = (gm / CL) * Vdiff
        → Vdiff(t) = V_in_comp * exp(gm * t / CL)

    This is clipped to ±VDD to model rail-limiting.

    Parameters
    ----------
    v_residue : (B,) or (B, n_bits) — DAC residue seen by comparator
    gm        : (B,) — comparator transconductance
    cl        : (B,) — load capacitance at latch output
    vos       : (B,) — input-referred offset
    t_local   : (B, T) or (T,) — local time axis within regen window
    v_preamp_gain : float — pre-amp voltage gain (default 4)

    Returns
    -------
    vcomp : (B, T) — regenerated differential voltage vs time
    tau   : (B,)   — regeneration time constant gm/CL
    """
    tau_regen = cl / (gm + 1e-12)                    # (B,)
    v0 = v_preamp_gain * (v_residue + vos)          # (B,) or (B, n_bits)

    # Broadcast: v0 → (B,1), t_local → (B,T) or (1,T)
    if v0.dim() == 1:
        v0 = v0.unsqueeze(-1)
    if tau_regen.dim() == 1:
        tau_regen_2d = tau_regen.unsqueeze(-1)
    else:
        tau_regen_2d = tau_regen

    if t_local.dim() == 1:
        t_local = t_local.unsqueeze(0)              # (1, T)

    vcomp = v0 * torch.exp(t_local / (tau_regen_2d + 1e-15))
    vcomp = torch.clamp(vcomp, -VDD_NOM, VDD_NOM)   # rail clipping

    return vcomp, tau_regen


# =========================================================================
# 3.  Metastability
# =========================================================================

def metastability_dwell(
    v_residue: torch.Tensor,
    gm: torch.Tensor,
    cl: torch.Tensor,
    v_threshold: float = 0.5 * VDD_NOM,
    v_preamp_gain: float = 4.0,
) -> torch.Tensor:
    """
    Time for the comparator to resolve from v_residue to ±v_threshold.

    t_meta = (CL / gm) * ln(v_threshold / |gain * v_residue|)

    A large t_meta signals near-metastable behaviour.
    """
    v0 = v_preamp_gain * torch.abs(v_residue).clamp(min=1e-9)
    tau = cl / (gm + 1e-12)
    t_meta = tau * torch.log(v_threshold / v0)
    return t_meta.clamp(min=0.0)


# =========================================================================
# 4.  Energy model
# =========================================================================

def switching_energy(
    cu: torch.Tensor,
    vref: torch.Tensor,
    bit_decisions: torch.Tensor,
    n_bits: int,
) -> torch.Tensor:
    """
    Estimate DAC switching energy using monotonic switching scheme.

    E_switch ≈ Σ_k  C_k * Vref^2 * |Δbit_k|

    For an upper bound, every trial switches:
    E_max = C_total * Vref^2.
    """
    B = bit_decisions.shape[0]
    e_total = torch.zeros(B, device=cu.device, dtype=cu.dtype)
    for k in range(n_bits):
        c_k = cu * (2 ** (n_bits - 1 - k))
        e_total = e_total + c_k * vref ** 2  # worst-case per trial
    return e_total


def comparator_energy(
    gm: torch.Tensor,
    vdd: float,
    t_regen: torch.Tensor,
) -> torch.Tensor:
    """Dynamic comparator energy ≈ gm * VDD * t_regen (simplified)."""
    return gm * vdd * t_regen


def total_energy(
    cu: torch.Tensor,
    vref: torch.Tensor,
    gm: torch.Tensor,
    cl: torch.Tensor,
    bit_decisions: torch.Tensor,
    n_bits: int,
    vdd: float = VDD_NOM,
) -> torch.Tensor:
    """Total per-conversion energy = DAC switching + comparator."""
    e_dac = switching_energy(cu, vref, bit_decisions, n_bits)
    tau = cl / (gm + 1e-12)
    e_comp = comparator_energy(gm, vdd, tau * n_bits)
    return e_dac + e_comp


# =========================================================================
# 5.  ENOB / FoM helpers
# =========================================================================

def enob_proxy(
    settling_error: torch.Tensor,
    n_bits: int,
) -> torch.Tensor:
    """
    ENOB ≈ n_bits − log2(1 + settling_error / LSB).
    This is a simplified proxy — real ENOB requires an FFT on a full
    code sweep — but it captures how residual error degrades resolution.
    """
    lsb = 1.0 / (2 ** n_bits)
    return n_bits - torch.log2(1.0 + settling_error / (lsb + 1e-12))


def walden_fom(
    energy: torch.Tensor,
    fs: torch.Tensor,
    enob: torch.Tensor,
) -> torch.Tensor:
    """Walden FoM = Energy / (fs * 2^ENOB).  Units: J/conv-step."""
    return energy / (fs * 2.0 ** enob + 1e-30)
