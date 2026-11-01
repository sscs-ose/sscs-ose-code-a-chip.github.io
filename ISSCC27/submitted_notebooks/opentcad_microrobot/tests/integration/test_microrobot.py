"""System-level invariants independent of the particular DD/PV fit."""
from dataclasses import replace

import numpy as np
import pytest

from examples.microrobot.pv import PVTable
from examples.microrobot.system import Parameters, simulate


def synthetic_table():
    # Independent ideal single-diode table for system regression, not a
    # substitute for the application's DEVSIM characterization.
    voltage = np.linspace(0, 0.7, 281)
    dark = -1e-18 * np.expm1(voltage / 0.02585)
    return PVTable(voltage, dark, np.full(len(voltage), 1.35e-10), 1000)


def test_dark_system_cannot_create_charge_motion_or_clock():
    result = simulate(synthetic_table(), duration_s=1.5, light_scale=0)
    for name in ("logic_V", "positive_V", "negative_magnitude_V", "phase_cycles",
                 "curvature_A_m_inv", "curvature_B_m_inv", "storage_J"):
        assert np.max(np.abs(result[name])) < 1e-20
    assert result["metrics"]["startup_enable_s"] is None


def test_two_phase_startup_brownout_and_electrical_budget():
    result = simulate(synthetic_table(), dt_s=0.002, duration_s=4)
    assert result["metrics"]["enable_transitions"] == 2
    assert result["metrics"]["measured_phase_B_lag_cycles"] == pytest.approx(0.25, abs=0.01)
    dark = (result["time_s"] > 3.1) & (result["time_s"] < 3.3)
    assert np.all(result["enabled"][dark] == 0)
    assert np.max(np.abs(result["drive_A_V"][dark])) == 0
    # A finite return produces a nonzero floating electrolyte voltage.
    assert np.ptp(result["electrolyte_bulk_V"]) > 1e-3
    assert abs(result["metrics"]["electrical_energy_balance_relative_residual"]) < 0.04


def test_mechanical_relaxation_does_not_change_electrical_state():
    table = synthetic_table()
    normal = simulate(table, dt_s=0.002, duration_s=2)
    slow = simulate(table, dt_s=0.002, duration_s=2,
                    p=replace(Parameters(), mechanical_tau_s=0.2))
    assert np.array_equal(normal["eta_A_V"], slow["eta_A_V"])
    assert np.ptp(slow["curvature_A_m_inv"]) < np.ptp(normal["curvature_A_m_inv"])


def test_pv_table_rejects_uncharacterized_voltages():
    with pytest.raises(ValueError, match="outside"):
        synthetic_table().current(0.8, 1000, 100)


def test_characterized_clock_and_load_hooks_and_current_step_brownout():
    p = Parameters()
    run = simulate(synthetic_table(), dt_s=0.002, duration_s=4,
                   clock_response=lambda voltage: 8192.0,
                   analog_current_response=lambda voltage: 2e-9*voltage,
                   extra_logic_current_response=lambda voltage: 1e-10*voltage)
    assert run["metrics"]["mean_gait_Hz"] == pytest.approx(8192 / p.divider)
    enabled = run["enabled"] > 0
    assert np.all(run["logic_V"][enabled] >= p.brownout_off_V)
    assert run["bias_W"] == pytest.approx(2e-9 * run["logic_V"]**2)
