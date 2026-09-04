"""
NeuroSAR evaluation — load a trained checkpoint, run inference on
held-out or custom design points, and produce quantitative metrics.

Usage
-----
    python src/evaluate.py
    python src/evaluate.py --checkpoint data/checkpoints/best_model.pt
"""

import argparse
import os
from typing import Dict, Optional

import numpy as np
import torch
import torch.nn.functional as F

from src.config import DESIGN, TRAIN, CHECKPOINTS, EXPORTS
from src.utils import get_device, ensure_dir, to_tensor
from src.pinn_model import NeuroSARNet, predict_full_conversion
from src.dataset import (
    generate_synthetic_dataset,
    load_dataset,
    DESIGN_PARAM_NAMES,
)
from src.physics import metastability_dwell, enob_proxy, walden_fom


# =========================================================================
# Load checkpoint
# =========================================================================

def load_model(
    checkpoint_path: Optional[str] = None,
    device: Optional[torch.device] = None,
) -> NeuroSARNet:
    """Load a trained NeuroSARNet from a checkpoint file."""
    device = device or get_device()
    ckpt_path = checkpoint_path or os.path.join(CHECKPOINTS, TRAIN.best_model_name)

    if not os.path.exists(ckpt_path):
        print(f"[NeuroSAR] No checkpoint found at {ckpt_path}. Returning untrained model.")
        model = NeuroSARNet(n_bits=DESIGN.n_bits, n_time=DESIGN.n_time_steps)
        return model.to(device).eval()

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    cfg = ckpt.get("config", {})
    model = NeuroSARNet(
        n_bits=cfg.get("n_bits", DESIGN.n_bits),
        n_time=cfg.get("n_time", DESIGN.n_time_steps),
    )
    model.load_state_dict(ckpt["model_state"])
    model = model.to(device).eval()

    print(f"[NeuroSAR] Loaded checkpoint (epoch {ckpt.get('epoch', '?')}, "
          f"val_loss {ckpt.get('val_loss', '?'):.4e})")
    return model


# =========================================================================
# Single-point inference
# =========================================================================

def infer_single(
    model: NeuroSARNet,
    vin: float = 0.9,
    vref: float = 1.8,
    cu: float = 10e-15,
    cload: float = 100e-15,
    gm: float = 500e-6,
    tau: float = 100e-12,
    vos: float = 0.0,
    temp: float = 300.0,
    fs: float = 50e6,
    device: Optional[torch.device] = None,
) -> Dict[str, np.ndarray]:
    """
    Run the PINN for a single design point across all bit trials.
    Returns numpy arrays for plotting.
    """
    device = device or next(model.parameters()).device
    params = to_tensor(
        [[vin, vref, cu, cload, gm, tau, vos, temp, fs]],
        device=device,
    )
    t_local = torch.linspace(0, 1, DESIGN.n_time_steps, device=device)

    result = predict_full_conversion(model, params, t_local, n_bits=DESIGN.n_bits)

    return {k: v.squeeze(0).cpu().numpy() for k, v in result.items()}


# =========================================================================
# Batch evaluation metrics
# =========================================================================

@torch.no_grad()
def evaluate_dataset(
    model: NeuroSARNet,
    data: Dict[str, torch.Tensor],
    device: Optional[torch.device] = None,
    n_samples: int = 500,
) -> Dict[str, float]:
    """
    Compute aggregate error metrics on a dataset.

    Returns
    -------
    dict with keys: mse_vdac, mse_vdiff, mse_vcomp, mse_energy,
                    mae_vdac, r2_vcomp
    """
    device = device or get_device()
    model = model.to(device).eval()

    N = min(n_samples, data["params"].shape[0])
    params = data["params"][:N].to(device)
    t_local = data["t_local"].to(device)

    pred = predict_full_conversion(model, params, t_local, DESIGN.n_bits)

    # Ground truth
    vdac_gt  = data["vdac"][:N, 1:].to(device)   # skip initial sample
    vdiff_gt = data["vdiff"][:N].to(device)
    vcomp_gt = data["vcomp"][:N].to(device)
    energy_gt = data["energy"][:N].to(device)

    mse_vdac  = F.mse_loss(pred["vdac"], vdac_gt).item()
    mse_vdiff = F.mse_loss(pred["vdiff"], vdiff_gt).item()
    mse_vcomp = F.mse_loss(pred["vcomp"], vcomp_gt).item()
    mse_energy = F.mse_loss(pred["energy"], energy_gt).item()

    mae_vdac = (pred["vdac"] - vdac_gt).abs().mean().item()

    # R² for vcomp (flattened)
    y = vcomp_gt.flatten()
    y_hat = pred["vcomp"].flatten()
    ss_res = ((y - y_hat) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2_vcomp = 1.0 - (ss_res / (ss_tot + 1e-10)).item()

    metrics = {
        "mse_vdac":   mse_vdac,
        "mse_vdiff":  mse_vdiff,
        "mse_vcomp":  mse_vcomp,
        "mse_energy": mse_energy,
        "mae_vdac":   mae_vdac,
        "r2_vcomp":   r2_vcomp,
    }

    print("[NeuroSAR] Evaluation metrics:")
    for k, v in metrics.items():
        print(f"  {k:15s}: {v:.6e}")

    return metrics


# =========================================================================
# Export predictions
# =========================================================================

def export_predictions(
    model: NeuroSARNet,
    data: Dict[str, torch.Tensor],
    output_path: Optional[str] = None,
    n_samples: int = 200,
) -> str:
    """Export predicted waveforms to CSV for external analysis."""
    import pandas as pd

    device = next(model.parameters()).device
    N = min(n_samples, data["params"].shape[0])
    params = data["params"][:N].to(device)
    t_local = data["t_local"].to(device)

    pred = predict_full_conversion(model, params, t_local, DESIGN.n_bits)

    # Flatten to a long-format DataFrame
    rows = []
    for i in range(N):
        for k in range(DESIGN.n_bits):
            for t_idx in range(DESIGN.n_time_steps):
                rows.append({
                    "sample_id": i,
                    "bit": k,
                    "t_idx": t_idx,
                    "t_local": data["t_local"][t_idx].item(),
                    **{name: params[i, j].item() for j, name in enumerate(DESIGN_PARAM_NAMES)},
                    "vdac":  pred["vdac"][i, k].item(),
                    "vdiff": pred["vdiff"][i, k, t_idx].item(),
                    "vcomp": pred["vcomp"][i, k, t_idx].item(),
                })

    df = pd.DataFrame(rows)
    output_path = output_path or os.path.join(ensure_dir(EXPORTS), "predictions.csv")
    df.to_csv(output_path, index=False)
    print(f"[NeuroSAR] Predictions exported → {output_path} ({len(df)} rows)")
    return output_path


# =========================================================================
# CLI entry
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate NeuroSAR PINN")
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--dataset", type=str, default=None)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()

    device = get_device()
    model = load_model(args.checkpoint, device)

    if args.dataset and os.path.exists(args.dataset):
        data = load_dataset(args.dataset)
    else:
        data = generate_synthetic_dataset(n_samples=1000)

    evaluate_dataset(model, data, device)

    if args.export:
        export_predictions(model, data)


if __name__ == "__main__":
    main()
