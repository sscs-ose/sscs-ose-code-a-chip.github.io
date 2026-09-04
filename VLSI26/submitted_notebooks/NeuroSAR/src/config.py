"""
NeuroSAR configuration — design-space bounds, training hyper-parameters,
and file paths.  Every numeric constant traces back to a Sky130 or
general-purpose SAR ADC motivation.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW     = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROC    = os.path.join(PROJECT_ROOT, "data", "processed")
DATA_SPICE   = os.path.join(PROJECT_ROOT, "data", "spice")
CHECKPOINTS  = os.path.join(PROJECT_ROOT, "data", "checkpoints")
EXPORTS      = os.path.join(PROJECT_ROOT, "data", "exports")
FIGURES      = os.path.join(PROJECT_ROOT, "assets", "figures")


# ---------------------------------------------------------------------------
# Design-space specification
# ---------------------------------------------------------------------------
@dataclass
class DesignSpace:
    """Ranges for each design variable in the SAR ADC front-end model."""

    n_bits: int = 10                          # resolution target

    # Input / reference
    vin_range:  Tuple[float, float] = (0.0, 1.8)     # V
    vref:       float                = 1.8            # V  (Sky130 nominal)

    # Capacitive DAC
    cu_range:   Tuple[float, float] = (1e-15, 50e-15) # unit cap, F
    cload_range: Tuple[float, float] = (10e-15, 500e-15)  # load cap, F

    # Comparator
    gm_range:   Tuple[float, float] = (50e-6, 2e-3)  # trans-conductance, S
    tau_range:   Tuple[float, float] = (10e-12, 500e-12)  # regen τ, s
    vos_range:   Tuple[float, float] = (-10e-3, 10e-3)    # offset, V

    # Environment
    temp_range:  Tuple[float, float] = (250.0, 400.0) # K
    fs_range:    Tuple[float, float] = (1e6, 200e6)   # sample rate, Hz

    # Time resolution per bit cycle
    n_time_steps: int = 64                    # points per local bit window


# ---------------------------------------------------------------------------
# Training hyper-parameters
# ---------------------------------------------------------------------------
@dataclass
class TrainConfig:
    """All tuneable training knobs live here."""

    # Dataset
    n_samples:    int   = 8000
    val_fraction: float = 0.15
    batch_size:   int   = 256

    # Architecture
    hidden_dims:  Tuple[int, ...] = (256, 256, 256, 128)
    activation:   str   = "tanh"      # tanh preserves smooth derivatives

    # Optimiser
    lr:           float = 3e-4
    weight_decay: float = 1e-5
    epochs:       int   = 500
    scheduler:    str   = "cosine"    # 'cosine' | 'step'

    # Loss weights  (the key PINN knobs)
    w_data:       float = 1.0
    w_kcl:        float = 0.5
    w_charge:     float = 0.5
    w_comp_ode:   float = 1.0
    w_smooth:     float = 0.05

    # Checkpoint
    checkpoint_every: int = 50
    best_model_name:  str = "best_model.pt"

    # Reproducibility
    seed: int = 42


# ---------------------------------------------------------------------------
# Feature normalisation stats (populated during dataset creation)
# ---------------------------------------------------------------------------
@dataclass
class NormStats:
    """Min-max stats for input / output normalisation."""
    input_min:  Dict[str, float] = field(default_factory=dict)
    input_max:  Dict[str, float] = field(default_factory=dict)
    output_min: Dict[str, float] = field(default_factory=dict)
    output_max: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Convenience singletons
# ---------------------------------------------------------------------------
DESIGN = DesignSpace()
TRAIN  = TrainConfig()
