"""Unit tests for the SPICE validation helper — runs entirely in fallback mode
so it works in CI with no PDK installed."""
import numpy as np
import pytest

from src.spice_validation import (
    SpiceConfig, analytical_sar, extract_code,
    extract_dwell_time_ps, extract_energy_fJ,
    run_validation, ngspice_available,
)
from src.biomedical_specs import (
    BIOMEDICAL_TARGETS, walden_fom_fJ_per_step, meets_spec, target_by_name,
)


def test_analytical_oracle_shape():
    cfg = SpiceConfig(n_bits=8, fs_MHz=1.0)
    out = analytical_sar(cfg, 0.9)
    assert out["t"].ndim == 1
    T = cfg.n_bits * cfg.n_points_per_bit
    assert out["vdac"].shape == (T,)
    assert out["vcmp_p"].shape == (T,)
    assert out["vcmp_n"].shape == (T,)
    assert 0 <= out["code"] < 2 ** cfg.n_bits


def test_code_extraction_monotonic():
    cfg = SpiceConfig(n_bits=8, fs_MHz=1.0)
    lo = analytical_sar(cfg, 0.1)["code"]
    hi = analytical_sar(cfg, 1.7)["code"]
    assert hi > lo


def test_dwell_and_energy_positive():
    cfg = SpiceConfig(n_bits=8)
    o = analytical_sar(cfg, 0.9)
    assert extract_dwell_time_ps(o["vcmp_p"], o["vcmp_n"], cfg) >= 0.0
    T = cfg.n_bits * cfg.n_points_per_bit
    vdac = np.interp(np.linspace(o["t"][0], o["t"][-1], T), o["t"], o["vdac"])
    assert extract_energy_fJ(vdac, cfg) >= 0.0


def test_run_validation_fallback_runs():
    cfg = SpiceConfig(n_bits=8, n_conversions=16, seed=0)
    def oracle_predict(vin, cfg):
        o = analytical_sar(cfg, float(vin))
        T = cfg.n_bits * cfg.n_points_per_bit
        t_t = np.linspace(o["t"][0], o["t"][-1], T)
        return {
            "vdac": np.interp(t_t, o["t"], o["vdac"]),
            "vcmp_p": np.interp(t_t, o["t"], o["vcmp_p"]),
            "vcmp_n": np.interp(t_t, o["t"], o["vcmp_n"]),
            "code": o["code"],
            "dwell_ps": extract_dwell_time_ps(o["vcmp_p"], o["vcmp_n"], cfg),
            "energy_fJ": extract_energy_fJ(
                np.interp(t_t, o["t"], o["vdac"]), cfg),
        }
    result = run_validation(cfg, oracle_predict)
    # Oracle vs oracle should be perfect
    assert result.metrics["R2_vdac"] > 0.99
    assert result.metrics["code_match_rate"] > 0.99


def test_biomedical_targets_present():
    names = [t.name for t in BIOMEDICAL_TARGETS]
    assert "Pacemaker telemetry AFE" in names
    assert "Neural-recorder front-end" in names
    assert target_by_name("Wearable ECG / PPG").n_bits == 12


def test_walden_fom_sane():
    # 1 pJ, 10 ENOB → FoM = 1000/1024 ≈ 0.977 fJ/step
    assert abs(walden_fom_fJ_per_step(1.0, 10.0) - 0.9765625) < 1e-6


def test_meets_spec_checker():
    t = target_by_name("Neural-recorder front-end")
    ok = meets_spec(t, energy_pJ=8.0, enob=9.1, p_meta=5e-10)
    assert all(ok.values())
    bad = meets_spec(t, energy_pJ=20.0, enob=8.0, p_meta=1e-6)
    assert not any(bad.values())
