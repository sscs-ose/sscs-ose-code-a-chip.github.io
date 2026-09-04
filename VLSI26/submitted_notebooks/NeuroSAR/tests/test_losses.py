"""
Test loss functions — verify each physics residual computes without
error and produces non-negative scalar losses.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import torch

from src.config import DESIGN
from src.losses import (
    data_loss,
    kcl_residual,
    charge_conservation_residual,
    comparator_ode_residual,
    smoothness_loss,
    total_pinn_loss,
)

B = 16
N_BITS = 10
N_TIME = 64


@pytest.fixture
def mock_pred():
    return {
        "vdac":   torch.randn(B, 1),
        "vdiff":  torch.randn(B, N_TIME),
        "vcomp":  torch.randn(B, N_TIME),
        "energy": torch.rand(B, 1),
    }


@pytest.fixture
def mock_target():
    return {
        "vdac":   torch.randn(B, 1),
        "vdiff":  torch.randn(B, N_TIME),
        "vcomp":  torch.randn(B, N_TIME),
        "energy": torch.rand(B, 1),
    }


class TestDataLoss:
    def test_returns_scalar(self, mock_pred, mock_target):
        loss = data_loss(mock_pred, mock_target)
        assert loss.dim() == 0
        assert loss.item() >= 0

    def test_zero_when_identical(self):
        pred = {"vdac": torch.ones(B, 1), "vdiff": torch.ones(B, N_TIME),
                "vcomp": torch.ones(B, N_TIME), "energy": torch.ones(B, 1)}
        loss = data_loss(pred, pred)
        assert loss.item() < 1e-10


class TestKCLResidual:
    def test_returns_scalar(self):
        vdac = torch.randn(B, 1)
        vdiff = torch.randn(B, N_TIME)
        t_local = torch.linspace(0, 1, N_TIME)
        cu = torch.rand(B) * 10e-15 + 1e-16
        cload = torch.rand(B) * 100e-15 + 1e-16

        loss = kcl_residual(vdac, vdiff, t_local, cu, cload, N_BITS)
        assert loss.dim() == 0
        assert loss.item() >= 0

    def test_settled_signal_low_residual(self):
        """A constant signal has zero derivative → zero KCL residual."""
        vdac = torch.ones(B, 1)
        vdiff = torch.ones(B, N_TIME) * 0.5  # constant
        t_local = torch.linspace(0, 1, N_TIME)
        cu = torch.full((B,), 10e-15)
        cload = torch.full((B,), 100e-15)

        loss = kcl_residual(vdac, vdiff, t_local, cu, cload, N_BITS)
        assert loss.item() < 1e-10


class TestChargeConservation:
    def test_returns_scalar(self):
        vdac_pred = torch.randn(B, N_BITS)
        params = torch.rand(B, 9)
        params[:, 1] = 1.8  # vref
        params[:, 2] = 10e-15  # cu
        params[:, 3] = 100e-15  # cload
        bits = torch.randint(0, 2, (B, N_BITS)).float()

        loss = charge_conservation_residual(vdac_pred, params, bits, N_BITS)
        assert loss.dim() == 0
        assert loss.item() >= 0


class TestComparatorODE:
    def test_returns_scalar(self):
        vcomp = torch.randn(B, N_TIME)
        t_local = torch.linspace(0, 1, N_TIME)
        gm = torch.rand(B) * 1e-3
        cl = torch.rand(B) * 100e-15

        loss = comparator_ode_residual(vcomp, t_local, gm, cl)
        assert loss.dim() == 0
        assert loss.item() >= 0

    def test_exact_exponential_low_residual(self):
        """If vcomp is exactly exp(gm/CL * t), residual should be small.
        Use a normalised [0,1] time axis with moderate gm/CL so the
        finite-difference approximation is accurate."""
        # Choose gm/CL = 2.0 (unitless with normalised time).
        # This gives vcomp = v0 * exp(2t), max at t=1 is v0*e^2 ~ 0.07.
        gm = torch.full((B,), 2.0)
        cl = torch.full((B,), 1.0)

        t_local = torch.linspace(0, 1, N_TIME)
        v0 = 0.01
        vcomp = v0 * torch.exp((gm / cl).unsqueeze(-1) * t_local.unsqueeze(0))

        loss = comparator_ode_residual(vcomp, t_local, gm, cl)
        # Finite differences introduce O(dt^2) error; with 64 points this is small
        assert loss.item() < 1e-3, f"ODE residual too large: {loss.item():.4e}"


class TestSmoothnessLoss:
    def test_returns_scalar(self):
        vdiff = torch.randn(B, N_TIME)
        vcomp = torch.randn(B, N_TIME)
        loss = smoothness_loss(vdiff, vcomp)
        assert loss.dim() == 0
        assert loss.item() >= 0

    def test_smooth_signal_low_loss(self):
        t = torch.linspace(0, 1, N_TIME)
        vdiff = t.unsqueeze(0).expand(B, -1) * 0.5  # linear → zero curvature
        vcomp = t.unsqueeze(0).expand(B, -1) * 0.3
        loss = smoothness_loss(vdiff, vcomp)
        assert loss.item() < 1e-10


class TestTotalPINNLoss:
    def test_all_terms_present(self):
        """Use single-trial predictions (B,1) as in actual training."""
        pred = {
            "vdac":   torch.randn(B, 1),
            "vdiff":  torch.randn(B, N_TIME),
            "vcomp":  torch.randn(B, N_TIME),
            "energy": torch.rand(B, 1),
        }
        target = {
            "vdac":   torch.randn(B, 1),
            "vdiff":  torch.randn(B, N_TIME),
            "vcomp":  torch.randn(B, N_TIME),
            "energy": torch.rand(B, 1),
        }
        params = torch.rand(B, 9)
        params[:, 2] = 10e-15
        params[:, 3] = 100e-15
        params[:, 4] = 500e-6
        t_local = torch.linspace(0, 1, N_TIME)
        bits = torch.randint(0, 2, (B, N_BITS)).float()

        losses = total_pinn_loss(pred, target, params, t_local, bits)

        assert "total" in losses
        assert "data" in losses
        assert "kcl" in losses
        assert "charge" in losses
        assert "comp_ode" in losses
        assert "smooth" in losses

        for k, v in losses.items():
            assert v.dim() == 0, f"{k} should be scalar"
            assert torch.isfinite(v), f"{k} is not finite"

    def test_gradients_flow(self):
        """Total loss must be differentiable w.r.t. predictions."""
        pred = {
            "vdac":   torch.randn(B, 1, requires_grad=True),
            "vdiff":  torch.randn(B, N_TIME, requires_grad=True),
            "vcomp":  torch.randn(B, N_TIME, requires_grad=True),
            "energy": torch.rand(B, 1, requires_grad=True),
        }
        target = {
            "vdac":   torch.randn(B, 1),
            "vdiff":  torch.randn(B, N_TIME),
            "vcomp":  torch.randn(B, N_TIME),
            "energy": torch.rand(B, 1),
        }
        params = torch.rand(B, 9)
        params[:, 2] = 10e-15
        params[:, 3] = 100e-15
        params[:, 4] = 500e-6
        t_local = torch.linspace(0, 1, N_TIME)
        bits = torch.randint(0, 2, (B, N_BITS)).float()

        losses = total_pinn_loss(pred, target, params, t_local, bits)
        losses["total"].backward()

        assert pred["vdac"].grad is not None
        assert pred["vcomp"].grad is not None
