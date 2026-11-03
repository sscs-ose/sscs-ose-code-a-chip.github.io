"""
Test tensor shapes throughout the NeuroSAR pipeline.
Ensures dimensional consistency across physics, model, and loss modules.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import torch
from src.config import DESIGN
from src.physics import (
    dac_total_cap,
    dac_trial_voltage,
    comparator_regeneration,
    metastability_dwell,
    switching_energy,
    total_energy,
    enob_proxy,
    walden_fom,
)
from src.pinn_model import NeuroSARNet, predict_full_conversion


B = 8        # batch size
N_BITS = 10
N_TIME = 64


class TestPhysicsShapes:
    """Verify physics functions produce correct output shapes."""

    def test_dac_total_cap(self):
        cu = torch.rand(B)
        c_total = dac_total_cap(cu, N_BITS)
        assert c_total.shape == (B,)

    def test_dac_trial_voltage(self):
        vin = torch.rand(B) * 1.8
        vref = torch.full((B,), 1.8)
        cu = torch.rand(B) * 50e-15
        cload = torch.rand(B) * 100e-15
        bits = torch.randint(0, 2, (B, N_BITS)).float()

        vdac = dac_trial_voltage(vin, vref, cu, cload, bits, N_BITS)
        assert vdac.shape == (B, N_BITS + 1)

    def test_comparator_regeneration(self):
        v_res = torch.randn(B) * 0.1
        gm = torch.rand(B) * 1e-3
        cl = torch.rand(B) * 100e-15
        vos = torch.randn(B) * 1e-3
        t = torch.linspace(0, 1, N_TIME)

        vcomp, tau = comparator_regeneration(v_res, gm, cl, vos, t)
        assert vcomp.shape == (B, N_TIME)
        assert tau.shape == (B,)

    def test_metastability_dwell(self):
        v_res = torch.randn(B) * 0.1
        gm = torch.rand(B) * 1e-3 + 1e-6
        cl = torch.rand(B) * 100e-15 + 1e-15
        t_meta = metastability_dwell(v_res, gm, cl)
        assert t_meta.shape == (B,)
        assert (t_meta >= 0).all()

    def test_switching_energy(self):
        cu = torch.rand(B) * 10e-15
        vref = torch.full((B,), 1.8)
        bits = torch.randint(0, 2, (B, N_BITS)).float()
        e = switching_energy(cu, vref, bits, N_BITS)
        assert e.shape == (B,)
        assert (e >= 0).all()

    def test_total_energy(self):
        cu = torch.rand(B) * 10e-15
        vref = torch.full((B,), 1.8)
        gm = torch.rand(B) * 1e-3
        cl = torch.rand(B) * 100e-15
        bits = torch.randint(0, 2, (B, N_BITS)).float()
        e = total_energy(cu, vref, gm, cl, bits, N_BITS)
        assert e.shape == (B,)

    def test_enob_proxy(self):
        err = torch.rand(B) * 0.01
        enob = enob_proxy(err, N_BITS)
        assert enob.shape == (B,)

    def test_walden_fom(self):
        e = torch.rand(B) * 1e-12
        fs = torch.full((B,), 50e6)
        enob = torch.full((B,), 9.0)
        fom = walden_fom(e, fs, enob)
        assert fom.shape == (B,)


class TestModelShapes:
    """Verify PINN model output shapes."""

    @pytest.fixture
    def model(self):
        return NeuroSARNet(n_bits=N_BITS, n_time=N_TIME)

    def test_forward_shapes(self, model):
        params = torch.randn(B, 9)
        t_local = torch.linspace(0, 1, N_TIME)
        bit_idx = torch.randint(0, N_BITS, (B,)).float()

        out = model(params, t_local, bit_idx)

        assert out["vdac"].shape == (B, 1)
        assert out["vdiff"].shape == (B, N_TIME)
        assert out["vcomp"].shape == (B, N_TIME)
        assert out["energy"].shape == (B, 1)

    def test_full_conversion_shapes(self, model):
        params = torch.randn(B, 9)
        t_local = torch.linspace(0, 1, N_TIME)

        out = predict_full_conversion(model, params, t_local, N_BITS)

        assert out["vdac"].shape == (B, N_BITS)
        assert out["vdiff"].shape == (B, N_BITS, N_TIME)
        assert out["vcomp"].shape == (B, N_BITS, N_TIME)
        assert out["energy"].shape == (B,)

    def test_model_differentiable(self, model):
        params = torch.randn(B, 9, requires_grad=True)
        t_local = torch.linspace(0, 1, N_TIME)
        bit_idx = torch.zeros(B)

        out = model(params, t_local, bit_idx)
        loss = out["vdac"].sum() + out["vcomp"].sum()
        loss.backward()

        assert params.grad is not None
        assert params.grad.shape == (B, 9)
