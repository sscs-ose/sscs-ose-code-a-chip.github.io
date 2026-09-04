"""
NeuroSAR utilities — seeding, normalisation helpers, device selection,
and small convenience functions shared across the code-base.
"""

import os
import random
from typing import Dict, Optional, Tuple

import numpy as np
import torch


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
def seed_everything(seed: int = 42) -> None:
    """Set random seeds for Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Min-max normalisation
# ---------------------------------------------------------------------------
def minmax_normalize(
    x: torch.Tensor,
    x_min: torch.Tensor,
    x_max: torch.Tensor,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Scale x to [0, 1] given pre-computed min / max."""
    return (x - x_min) / (x_max - x_min + eps)


def minmax_denormalize(
    x_norm: torch.Tensor,
    x_min: torch.Tensor,
    x_max: torch.Tensor,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Invert min-max normalisation."""
    return x_norm * (x_max - x_min + eps) + x_min


# ---------------------------------------------------------------------------
# Tensor helpers
# ---------------------------------------------------------------------------
def to_tensor(x, device: Optional[torch.device] = None,
              dtype: torch.dtype = torch.float32) -> torch.Tensor:
    """Convert numpy / list / scalar to a torch tensor."""
    if isinstance(x, torch.Tensor):
        t = x.to(dtype)
    else:
        t = torch.tensor(x, dtype=dtype)
    if device is not None:
        t = t.to(device)
    return t


def ensure_dir(path: str) -> str:
    """Create directory (and parents) if it does not exist. Returns path."""
    os.makedirs(path, exist_ok=True)
    return path
