"""
NeuroSAR dataset — build, save, and load training tensors.

Two modes are supported:

  Mode A  (default) — Lightweight synthetic generator.
    Produces physically-plausible SAR waveforms using the analytical
    models in `physics.py`.  No external tools needed.

  Mode B  — Real-SPICE integration.
    Parse transient CSV / HDF5 files exported from ngspice or Xyce
    running an open-source Sky130 SAR ADC testbench.
    See `simulate_spice.py` for deck templates.
"""

import os
from typing import Dict, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, random_split

from src.config import DESIGN, TRAIN, DATA_PROC, NormStats
from src.physics import (
    dac_trial_voltage,
    dac_settling,
    comparator_regeneration,
    metastability_dwell,
    total_energy,
    enob_proxy,
)
from src.utils import seed_everything, to_tensor, ensure_dir


# =========================================================================
# Feature / label column names
# =========================================================================
DESIGN_PARAM_NAMES = [
    "vin", "vref", "cu", "cload", "gm", "tau_regen", "vos", "temp", "fs",
]
OUTPUT_NAMES = [
    "vdac", "vdiff", "vcomp",
]


# =========================================================================
# Mode A: Synthetic dataset generator
# =========================================================================

def _sample_design_params(n: int, rng: np.random.Generator) -> Dict[str, np.ndarray]:
    """Draw `n` random design-parameter vectors within the design space."""
    D = DESIGN
    U = rng.uniform
    return {
        "vin":       U(*D.vin_range, n).astype(np.float32),
        "vref":      np.full(n, D.vref, dtype=np.float32),
        "cu":        U(*D.cu_range, n).astype(np.float32),
        "cload":     U(*D.cload_range, n).astype(np.float32),
        "gm":        U(*D.gm_range, n).astype(np.float32),
        "tau_regen": U(*D.tau_range, n).astype(np.float32),
        "vos":       U(*D.vos_range, n).astype(np.float32),
        "temp":      U(*D.temp_range, n).astype(np.float32),
        "fs":        U(*D.fs_range, n).astype(np.float32),
    }


def generate_synthetic_dataset(
    n_samples: int = TRAIN.n_samples,
    n_bits: int = DESIGN.n_bits,
    n_time: int = DESIGN.n_time_steps,
    seed: int = TRAIN.seed,
) -> Dict[str, torch.Tensor]:
    """
    Generate a complete synthetic dataset of SAR ADC waveforms.

    Returns
    -------
    dict with keys:
      params    — (N, 9)          design parameter matrix
      t_local   — (T,)            normalised local time axis [0, 1)
      vdac      — (N, n_bits+1)   DAC node voltage after each trial
      vdiff     — (N, n_bits, T)  differential voltage per bit cycle
      vcomp     — (N, n_bits, T)  comparator output per bit cycle
      energy    — (N,)            total conversion energy
      meta_dwell— (N, n_bits)     metastability dwell per bit
      bits      — (N, n_bits)     binary decisions
    """
    seed_everything(seed)
    rng = np.random.default_rng(seed)
    N = n_samples

    # --- sample design points -------------------------------------------
    dp = _sample_design_params(N, rng)
    params = np.stack([dp[k] for k in DESIGN_PARAM_NAMES], axis=1)  # (N, 9)

    vin   = to_tensor(dp["vin"])
    vref  = to_tensor(dp["vref"])
    cu    = to_tensor(dp["cu"])
    cload = to_tensor(dp["cload"])
    gm    = to_tensor(dp["gm"])
    tau   = to_tensor(dp["tau_regen"])
    vos   = to_tensor(dp["vos"])

    # --- ideal bit decisions (SAR logic) --------------------------------
    bits = torch.zeros(N, n_bits, dtype=torch.float32)
    residue = vin.clone()
    for k in range(n_bits):
        bit_weight = vref / (2.0 ** (k + 1))
        bits[:, k] = (residue >= (vref / 2.0)).float()
        residue = residue - bits[:, k] * bit_weight + (1 - bits[:, k]) * 0.0

    # --- DAC trial voltages ---------------------------------------------
    vdac = dac_trial_voltage(vin, vref, cu, cload, bits, n_bits)  # (N, n_bits+1)

    # --- local time axis ------------------------------------------------
    t_local = torch.linspace(0, 1, n_time, dtype=torch.float32)  # normalised

    # --- comparator waveforms per bit -----------------------------------
    vdiff_all = torch.zeros(N, n_bits, n_time)
    vcomp_all = torch.zeros(N, n_bits, n_time)
    meta_dwell = torch.zeros(N, n_bits)

    for k in range(n_bits):
        # Residue seen by comparator at trial k
        v_res = vdac[:, k + 1] - vref / 2.0  # (N,)

        # Physical time scale: t_phys = t_local * tau
        t_phys = t_local.unsqueeze(0) * tau.unsqueeze(1)  # (N, T)

        vcomp_k, _ = comparator_regeneration(v_res, gm, cload, vos, t_phys)
        vcomp_all[:, k, :] = vcomp_k

        # Differential input (exponential settling towards final DAC value)
        tau_settle = tau * 0.3  # DAC settling is faster than regen
        vdiff_all[:, k, :] = dac_settling(
            vdac[:, k].unsqueeze(-1),
            vdac[:, k + 1].unsqueeze(-1),
            t_phys,
            tau_settle.unsqueeze(-1),
        )

        meta_dwell[:, k] = metastability_dwell(v_res, gm, cload)

    # --- energy ---------------------------------------------------------
    energy = total_energy(cu, vref, gm, cload, bits, n_bits)

    return {
        "params":     to_tensor(params),
        "t_local":    t_local,
        "vdac":       vdac,
        "vdiff":      vdiff_all,
        "vcomp":      vcomp_all,
        "energy":     energy,
        "meta_dwell": meta_dwell,
        "bits":       bits,
    }


# =========================================================================
# Mode B: SPICE data loader (stub + parser skeleton)
# =========================================================================

def load_spice_csv(
    csv_path: str,
    n_bits: int = DESIGN.n_bits,
) -> Dict[str, torch.Tensor]:
    """
    Parse a transient waveform CSV exported from ngspice or Xyce.

    Expected columns:
        time_s, bit_index, vin_v, vdac_v, vdiff_v, vcomp_v,
        cu_f, cload_f, gm_s, tau_s, vos_v, temp_k, fs_hz

    To generate this CSV from a Sky130 SAR ADC testbench:
      1. Run the ngspice deck produced by `simulate_spice.py`.
      2. Use `.wrdata` or export via Python post-processing.
      3. Point this function at the resulting file.

    Returns same dict schema as `generate_synthetic_dataset`.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)

    required_cols = {"time_s", "vin_v", "vdac_v", "vdiff_v", "vcomp_v"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV missing columns: {missing}.  "
            f"See docs/physics_model.md for expected format."
        )

    # Group by conversion cycle (assumes a 'cycle_id' column or sequential)
    if "cycle_id" not in df.columns:
        # Infer cycles from time resets
        dt = df["time_s"].diff()
        df["cycle_id"] = (dt < 0).cumsum()

    cycles = df.groupby("cycle_id")
    N = cycles.ngroups

    # Collect into tensors — real implementation would align grids
    # For now, return a best-effort parse
    vdac_list, vdiff_list, vcomp_list = [], [], []
    for _, grp in cycles:
        vdac_list.append(grp["vdac_v"].values)
        vdiff_list.append(grp["vdiff_v"].values)
        vcomp_list.append(grp["vcomp_v"].values)

    print(f"[NeuroSAR] Loaded {N} conversion cycles from {csv_path}")

    return {
        "vdac":  to_tensor(np.array(vdac_list)),
        "vdiff": to_tensor(np.array(vdiff_list)),
        "vcomp": to_tensor(np.array(vcomp_list)),
    }


def load_spice_hdf5(hdf5_path: str) -> Dict[str, torch.Tensor]:
    """
    Load waveform data from an HDF5 archive.

    Expected groups: /params, /vdac, /vdiff, /vcomp, /energy
    """
    import h5py

    data = {}
    with h5py.File(hdf5_path, "r") as f:
        for key in f.keys():
            data[key] = to_tensor(f[key][:])
    print(f"[NeuroSAR] Loaded HDF5 with keys: {list(data.keys())}")
    return data


# =========================================================================
# PyTorch Dataset wrapper
# =========================================================================

class SARDataset(Dataset):
    """Wraps the generated / loaded tensors for DataLoader consumption."""

    def __init__(self, data: Dict[str, torch.Tensor]):
        self.params     = data["params"]      # (N, D)
        self.t_local    = data["t_local"]     # (T,)
        self.vdac       = data["vdac"]        # (N, n_bits+1)
        self.vdiff      = data["vdiff"]       # (N, n_bits, T)
        self.vcomp      = data["vcomp"]       # (N, n_bits, T)
        self.energy     = data["energy"]      # (N,)
        self.meta_dwell = data["meta_dwell"]  # (N, n_bits)
        self.bits       = data["bits"]        # (N, n_bits)
        self.n = self.params.shape[0]

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "params":     self.params[idx],
            "t_local":    self.t_local,
            "vdac":       self.vdac[idx],
            "vdiff":      self.vdiff[idx],
            "vcomp":      self.vcomp[idx],
            "energy":     self.energy[idx],
            "meta_dwell": self.meta_dwell[idx],
            "bits":       self.bits[idx],
        }


# =========================================================================
# Build normalised datasets + data-loaders
# =========================================================================

def compute_norm_stats(data: Dict[str, torch.Tensor]) -> NormStats:
    """Compute min/max normalisation statistics from the dataset."""
    stats = NormStats()
    params = data["params"]
    for i, name in enumerate(DESIGN_PARAM_NAMES):
        col = params[:, i]
        stats.input_min[name] = col.min().item()
        stats.input_max[name] = col.max().item()

    for key in ("vdac", "vdiff", "vcomp", "energy"):
        t = data[key]
        stats.output_min[key] = t.min().item()
        stats.output_max[key] = t.max().item()
    return stats


def build_dataloaders(
    data: Dict[str, torch.Tensor],
    val_fraction: float = TRAIN.val_fraction,
    batch_size: int = TRAIN.batch_size,
    seed: int = TRAIN.seed,
) -> Tuple[DataLoader, DataLoader, NormStats]:
    """Split into train / val and return DataLoaders + norm stats."""
    ds = SARDataset(data)
    n_val = int(len(ds) * val_fraction)
    n_train = len(ds) - n_val
    gen = torch.Generator().manual_seed(seed)
    train_ds, val_ds = random_split(ds, [n_train, n_val], generator=gen)

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                          drop_last=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)

    stats = compute_norm_stats(data)
    return train_dl, val_dl, stats


# =========================================================================
# Persistence
# =========================================================================

def save_dataset(data: Dict[str, torch.Tensor], path: Optional[str] = None):
    """Save generated dataset to disk."""
    path = path or os.path.join(ensure_dir(DATA_PROC), "sar_dataset.pt")
    torch.save(data, path)
    print(f"[NeuroSAR] Dataset saved → {path}  ({data['params'].shape[0]} samples)")
    return path


def load_dataset(path: Optional[str] = None) -> Dict[str, torch.Tensor]:
    """Load dataset from disk."""
    path = path or os.path.join(DATA_PROC, "sar_dataset.pt")
    data = torch.load(path, weights_only=False)
    print(f"[NeuroSAR] Dataset loaded ← {path}  ({data['params'].shape[0]} samples)")
    return data
