"""
Test dataset generation — verify the synthetic generator produces
consistent, physically-plausible data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import torch
import numpy as np

from src.config import DESIGN
from src.dataset import (
    generate_synthetic_dataset,
    SARDataset,
    build_dataloaders,
    compute_norm_stats,
    save_dataset,
    load_dataset,
    DESIGN_PARAM_NAMES,
)


N_SAMPLES = 200
N_BITS = DESIGN.n_bits
N_TIME = DESIGN.n_time_steps


@pytest.fixture(scope="module")
def dataset():
    """Generate a small dataset once for all tests."""
    return generate_synthetic_dataset(n_samples=N_SAMPLES, seed=123)


class TestSyntheticGeneration:

    def test_all_keys_present(self, dataset):
        required = {"params", "t_local", "vdac", "vdiff", "vcomp",
                     "energy", "meta_dwell", "bits"}
        assert required == set(dataset.keys())

    def test_params_shape(self, dataset):
        assert dataset["params"].shape == (N_SAMPLES, len(DESIGN_PARAM_NAMES))

    def test_vdac_shape(self, dataset):
        assert dataset["vdac"].shape == (N_SAMPLES, N_BITS + 1)

    def test_vdiff_shape(self, dataset):
        assert dataset["vdiff"].shape == (N_SAMPLES, N_BITS, N_TIME)

    def test_vcomp_shape(self, dataset):
        assert dataset["vcomp"].shape == (N_SAMPLES, N_BITS, N_TIME)

    def test_energy_positive(self, dataset):
        assert (dataset["energy"] >= 0).all()

    def test_bits_binary(self, dataset):
        bits = dataset["bits"]
        assert ((bits == 0) | (bits == 1)).all()

    def test_vdac_initial_equals_vin(self, dataset):
        """First DAC value should be the sampled input voltage."""
        vin = dataset["params"][:, 0]
        vdac_0 = dataset["vdac"][:, 0]
        assert torch.allclose(vin, vdac_0, atol=1e-6)

    def test_vdac_within_bounds(self, dataset):
        """DAC voltage should stay within a reasonable range.
        Note: charge redistribution can produce negative voltages
        when many LSB caps switch from Vref to GND."""
        vdac = dataset["vdac"]
        assert vdac.min() >= -2.0, "DAC voltage unreasonably negative"
        assert vdac.max() <= 4.0, "DAC voltage unreasonably high"

    def test_reproducibility(self):
        d1 = generate_synthetic_dataset(n_samples=50, seed=42)
        d2 = generate_synthetic_dataset(n_samples=50, seed=42)
        assert torch.allclose(d1["params"], d2["params"])
        assert torch.allclose(d1["vdac"], d2["vdac"])


class TestSARDataset:

    def test_len(self, dataset):
        ds = SARDataset(dataset)
        assert len(ds) == N_SAMPLES

    def test_getitem_keys(self, dataset):
        ds = SARDataset(dataset)
        item = ds[0]
        assert "params" in item
        assert "vdac" in item
        assert "vdiff" in item
        assert "vcomp" in item


class TestDataLoaders:

    def test_build_dataloaders(self, dataset):
        train_dl, val_dl, stats = build_dataloaders(dataset, batch_size=32)
        assert len(train_dl) > 0
        assert len(val_dl) > 0

        batch = next(iter(train_dl))
        assert batch["params"].shape[1] == len(DESIGN_PARAM_NAMES)

    def test_norm_stats(self, dataset):
        stats = compute_norm_stats(dataset)
        assert len(stats.input_min) == len(DESIGN_PARAM_NAMES)
        for k in DESIGN_PARAM_NAMES:
            assert stats.input_min[k] <= stats.input_max[k]


class TestPersistence:

    def test_save_and_load(self, dataset, tmp_path):
        path = str(tmp_path / "test_dataset.pt")
        save_dataset(dataset, path)
        loaded = load_dataset(path)

        assert set(loaded.keys()) == set(dataset.keys())
        assert torch.allclose(loaded["params"], dataset["params"])
        assert torch.allclose(loaded["energy"], dataset["energy"])
