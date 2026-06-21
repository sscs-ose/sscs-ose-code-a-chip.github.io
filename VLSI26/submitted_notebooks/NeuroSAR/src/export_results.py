"""
NeuroSAR export utilities — package results, figures, and model
artefacts for submission or sharing.
"""

import os
import json
import shutil
from typing import Dict, Optional

import torch
import numpy as np
import pandas as pd

from src.config import CHECKPOINTS, EXPORTS, FIGURES, PROJECT_ROOT
from src.utils import ensure_dir


# =========================================================================
# Export training summary
# =========================================================================

def export_training_summary(
    history_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """Export training history to a JSON file."""
    history_path = history_path or os.path.join(CHECKPOINTS, "training_history.pt")
    output_path = output_path or os.path.join(ensure_dir(EXPORTS), "training_summary.json")

    if not os.path.exists(history_path):
        print(f"[NeuroSAR] No training history at {history_path}")
        return ""

    history = torch.load(history_path, weights_only=False)
    summary = {
        "n_epochs": len(history.get("train", [])),
        "final_train_loss": history["train"][-1] if history.get("train") else None,
        "final_val_loss": history["val"][-1] if history.get("val") else None,
    }

    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"[NeuroSAR] Training summary → {output_path}")
    return output_path


# =========================================================================
# Export model card
# =========================================================================

def export_model_card(
    model_params: int,
    val_loss: float,
    n_train_samples: int,
    output_path: Optional[str] = None,
) -> str:
    """Generate a model card markdown file."""
    output_path = output_path or os.path.join(ensure_dir(EXPORTS), "MODEL_CARD.md")

    card = f"""# NeuroSAR Model Card

## Model Description
Physics-informed neural network (PINN) surrogate for SAR ADC transient dynamics.

## Architecture
- Type: Multi-head MLP with Fourier feature encoding
- Parameters: {model_params:,}
- Activation: tanh (smooth second derivatives for physics residuals)
- Output heads: vdac, vdiff(t), vcomp(t), energy

## Training Data
- Source: Synthetic transient generator (analytical physics models)
- Samples: {n_train_samples:,}
- Design space: 9 parameters (Vin, Vref, Cu, Cload, gm, τ, Vos, T, fs)

## Performance
- Best validation loss: {val_loss:.4e}
- Physics residuals embedded: KCL, charge conservation, comparator ODE

## Intended Use
- Educational exploration of SAR ADC design trade-offs
- Interactive design-space navigation via Jupyter notebooks
- Demonstration of physics-informed ML for circuit design

## Limitations
- Trained on analytical models, not transistor-level SPICE
- ENOB proxy is simplified (no full FFT-based SNDR)
- Comparator model is first-order (no noise, no kickback)

## License
Apache 2.0
"""

    with open(output_path, "w") as f:
        f.write(card)

    print(f"[NeuroSAR] Model card → {output_path}")
    return output_path


# =========================================================================
# Package submission
# =========================================================================

def package_submission(
    output_dir: Optional[str] = None,
) -> str:
    """
    Collect all submission artefacts into a clean directory.
    """
    output_dir = output_dir or os.path.join(PROJECT_ROOT, "submission_package")
    ensure_dir(output_dir)

    # Copy key files
    items_to_copy = [
        ("README.md", "README.md"),
        ("LICENSE", "LICENSE"),
        ("requirements.txt", "requirements.txt"),
    ]

    for src_rel, dst_rel in items_to_copy:
        src = os.path.join(PROJECT_ROOT, src_rel)
        dst = os.path.join(output_dir, dst_rel)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    # Copy notebooks
    nb_src = os.path.join(PROJECT_ROOT, "notebooks")
    nb_dst = os.path.join(output_dir, "notebooks")
    if os.path.exists(nb_src):
        shutil.copytree(nb_src, nb_dst, dirs_exist_ok=True)

    # Copy figures
    fig_src = FIGURES
    fig_dst = os.path.join(output_dir, "figures")
    if os.path.exists(fig_src):
        shutil.copytree(fig_src, fig_dst, dirs_exist_ok=True)

    # Copy checkpoint
    ckpt_src = os.path.join(CHECKPOINTS, "best_model.pt")
    if os.path.exists(ckpt_src):
        ensure_dir(os.path.join(output_dir, "checkpoints"))
        shutil.copy2(ckpt_src, os.path.join(output_dir, "checkpoints", "best_model.pt"))

    print(f"[NeuroSAR] Submission package → {output_dir}")
    return output_dir
