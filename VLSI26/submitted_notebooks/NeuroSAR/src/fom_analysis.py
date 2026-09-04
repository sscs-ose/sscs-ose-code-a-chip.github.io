"""
NeuroSAR Figure-of-Merit analysis — parameter sweeps, heatmaps,
and design-space exploration using the trained PINN surrogate.

Key FoMs
--------
- Energy per conversion (E_conv)
- Metastability dwell time (T_meta)
- ENOB proxy
- Walden FoM = E_conv / (fs · 2^ENOB)
"""

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch

from src.config import DESIGN, EXPORTS
from src.utils import get_device, ensure_dir, to_tensor
from src.pinn_model import NeuroSARNet, predict_full_conversion
from src.physics import metastability_dwell, enob_proxy, walden_fom, total_energy
from src.dataset import DESIGN_PARAM_NAMES


# =========================================================================
# Parameter sweep engine
# =========================================================================

def parameter_sweep_2d(
    model: NeuroSARNet,
    param_x: str,
    param_y: str,
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    n_grid: int = 25,
    base_params: Optional[Dict[str, float]] = None,
) -> Dict[str, np.ndarray]:
    """
    Sweep two design parameters on a grid, evaluate the PINN, and
    return FoM surfaces.

    Parameters
    ----------
    model     : trained NeuroSARNet
    param_x   : name of x-axis parameter (must be in DESIGN_PARAM_NAMES)
    param_y   : name of y-axis parameter
    x_range   : (min, max) for x
    y_range   : (min, max) for y
    n_grid    : grid resolution per axis
    base_params: default values for non-swept parameters

    Returns
    -------
    dict with: x_vals, y_vals, energy (n,n), meta_max (n,n), enob (n,n), fom (n,n)
    """
    device = next(model.parameters()).device
    defaults = {
        "vin": 0.9, "vref": 1.8, "cu": 10e-15, "cload": 100e-15,
        "gm": 500e-6, "tau_regen": 100e-12, "vos": 0.0,
        "temp": 300.0, "fs": 50e6,
    }
    if base_params:
        defaults.update(base_params)

    ix = DESIGN_PARAM_NAMES.index(param_x)
    iy = DESIGN_PARAM_NAMES.index(param_y)

    x_vals = np.linspace(x_range[0], x_range[1], n_grid)
    y_vals = np.linspace(y_range[0], y_range[1], n_grid)

    energy_grid = np.zeros((n_grid, n_grid))
    meta_grid   = np.zeros((n_grid, n_grid))
    enob_grid   = np.zeros((n_grid, n_grid))
    fom_grid    = np.zeros((n_grid, n_grid))

    t_local = torch.linspace(0, 1, DESIGN.n_time_steps, device=device)

    model.eval()
    with torch.no_grad():
        for i, xv in enumerate(x_vals):
            for j, yv in enumerate(y_vals):
                p = [defaults[k] for k in DESIGN_PARAM_NAMES]
                p[ix] = xv
                p[iy] = yv
                params = to_tensor([p], device=device)

                result = predict_full_conversion(model, params, t_local, DESIGN.n_bits)

                e = result["energy"][0].item()
                energy_grid[j, i] = e

                # Metastability from physics (using predicted vdac as residue proxy)
                vdac = result["vdac"][0]
                residues = vdac - defaults["vref"] / 2.0
                gm_val = to_tensor([p[4]], device=device)
                cl_val = to_tensor([p[3]], device=device)
                t_meta = metastability_dwell(residues, gm_val, cl_val)
                meta_grid[j, i] = t_meta.max().item()

                # ENOB proxy
                settling_err = torch.abs(result["vdiff"][0, -1, -1])
                enob_val = enob_proxy(settling_err.unsqueeze(0), DESIGN.n_bits)
                enob_grid[j, i] = enob_val.item()

                # Walden FoM
                fs_val = to_tensor([p[8]], device=device)
                fom_val = walden_fom(
                    to_tensor([e], device=device),
                    fs_val,
                    enob_val.to(device),
                )
                fom_grid[j, i] = fom_val.item()

    return {
        "x_vals": x_vals,
        "y_vals": y_vals,
        "x_name": param_x,
        "y_name": param_y,
        "energy": energy_grid,
        "meta_max": meta_grid,
        "enob": enob_grid,
        "walden_fom": fom_grid,
    }


# =========================================================================
# 1-D sweep
# =========================================================================

def parameter_sweep_1d(
    model: NeuroSARNet,
    param_name: str,
    sweep_range: Tuple[float, float],
    n_points: int = 50,
    base_params: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Sweep a single parameter and return a DataFrame of FoMs."""
    device = next(model.parameters()).device
    defaults = {
        "vin": 0.9, "vref": 1.8, "cu": 10e-15, "cload": 100e-15,
        "gm": 500e-6, "tau_regen": 100e-12, "vos": 0.0,
        "temp": 300.0, "fs": 50e6,
    }
    if base_params:
        defaults.update(base_params)

    idx = DESIGN_PARAM_NAMES.index(param_name)
    sweep_vals = np.linspace(sweep_range[0], sweep_range[1], n_points)
    t_local = torch.linspace(0, 1, DESIGN.n_time_steps, device=device)

    rows = []
    model.eval()
    with torch.no_grad():
        for sv in sweep_vals:
            p = [defaults[k] for k in DESIGN_PARAM_NAMES]
            p[idx] = sv
            params = to_tensor([p], device=device)
            result = predict_full_conversion(model, params, t_local, DESIGN.n_bits)
            e = result["energy"][0].item()

            settling_err = torch.abs(result["vdiff"][0, -1, -1])
            enob_val = enob_proxy(settling_err.unsqueeze(0), DESIGN.n_bits).item()

            rows.append({
                param_name: sv,
                "energy_j": e,
                "enob": enob_val,
            })

    return pd.DataFrame(rows)


# =========================================================================
# Export sweep data
# =========================================================================

def export_sweep(
    sweep_data: Dict[str, np.ndarray],
    filename: str = "sweep_2d.csv",
) -> str:
    """Flatten a 2-D sweep dict to CSV for external use."""
    x = sweep_data["x_vals"]
    y = sweep_data["y_vals"]
    rows = []
    for i, xv in enumerate(x):
        for j, yv in enumerate(y):
            rows.append({
                sweep_data["x_name"]: xv,
                sweep_data["y_name"]: yv,
                "energy_j": sweep_data["energy"][j, i],
                "meta_max_s": sweep_data["meta_max"][j, i],
                "enob": sweep_data["enob"][j, i],
                "walden_fom": sweep_data["walden_fom"][j, i],
            })
    df = pd.DataFrame(rows)
    path = os.path.join(ensure_dir(EXPORTS), filename)
    df.to_csv(path, index=False)
    print(f"[NeuroSAR] Sweep exported → {path}")
    return path
