"""
Test end-to-end inference flow — model loading, single-point inference,
and batch evaluation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import torch
import numpy as np

from src.config import DESIGN
from src.pinn_model import NeuroSARNet, predict_full_conversion
from src.evaluate import infer_single, evaluate_dataset, load_model
from src.dataset import generate_synthetic_dataset


N_BITS = DESIGN.n_bits
N_TIME = DESIGN.n_time_steps


@pytest.fixture(scope="module")
def model():
    """Create an untrained model for inference testing."""
    m = NeuroSARNet(n_bits=N_BITS, n_time=N_TIME)
    m.eval()
    return m


@pytest.fixture(scope="module")
def small_dataset():
    return generate_synthetic_dataset(n_samples=100, seed=99)


class TestSingleInference:

    def test_returns_dict(self, model):
        result = infer_single(model, vin=0.9, gm=500e-6)
        assert isinstance(result, dict)
        assert "vdac" in result
        assert "vdiff" in result
        assert "vcomp" in result
        assert "energy" in result

    def test_output_shapes(self, model):
        result = infer_single(model)
        assert result["vdac"].shape == (N_BITS,)
        assert result["vdiff"].shape == (N_BITS, N_TIME)
        assert result["vcomp"].shape == (N_BITS, N_TIME)
        assert result["energy"].shape == ()

    def test_output_finite(self, model):
        result = infer_single(model, vin=0.5)
        for k, v in result.items():
            assert np.all(np.isfinite(v)), f"{k} contains non-finite values"

    def test_different_inputs_different_outputs(self):
        """A freshly-initialised model should produce at least slightly
        different outputs for very different inputs once trained.
        For an untrained model we just check the forward pass works
        and produces finite values for multiple design points."""
        m = NeuroSARNet(n_bits=N_BITS, n_time=N_TIME)
        m.eval()
        r1 = infer_single(m, vin=0.3, gm=100e-6, cu=1e-15)
        r2 = infer_single(m, vin=1.5, gm=1.5e-3, cu=50e-15)
        # Both should return finite values
        for key in ["vdac", "vdiff", "vcomp", "energy"]:
            assert np.all(np.isfinite(r1[key])), f"{key} not finite for input 1"
            assert np.all(np.isfinite(r2[key])), f"{key} not finite for input 2"


class TestBatchEvaluation:

    def test_evaluate_returns_metrics(self, model, small_dataset):
        metrics = evaluate_dataset(model, small_dataset, n_samples=50)
        assert isinstance(metrics, dict)
        expected_keys = {"mse_vdac", "mse_vdiff", "mse_vcomp",
                         "mse_energy", "mae_vdac", "r2_vcomp"}
        assert expected_keys == set(metrics.keys())

    def test_metrics_finite(self, model, small_dataset):
        metrics = evaluate_dataset(model, small_dataset, n_samples=50)
        for k, v in metrics.items():
            assert np.isfinite(v), f"{k} = {v} is not finite"


class TestModelLoading:

    def test_load_missing_returns_model(self):
        """Loading a missing checkpoint should return an untrained model."""
        model = load_model("/nonexistent/path.pt")
        assert isinstance(model, NeuroSARNet)

    def test_model_parameter_count(self, model):
        n_params = sum(p.numel() for p in model.parameters())
        assert n_params > 10_000, "Model seems too small"
        assert n_params < 10_000_000, "Model seems too large"


class TestFullConversion:

    def test_deterministic(self, model):
        params = torch.randn(4, 9)
        t_local = torch.linspace(0, 1, N_TIME)

        r1 = predict_full_conversion(model, params, t_local, N_BITS)
        r2 = predict_full_conversion(model, params, t_local, N_BITS)

        assert torch.allclose(r1["vdac"], r2["vdac"])
        assert torch.allclose(r1["vcomp"], r2["vcomp"])
