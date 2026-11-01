"""Explicitly hypothetical system experiment, driven by OpenTCAD PV tables.

No controller transistor model or measured actuator fit is substituted here.
Electrical interface charging and mechanical relaxation are separate states.
All electrode potentials are relative to their local electrolyte equilibrium,
whose absolute offset to Ag/AgCl is unknown. Actuator/solution voltages use
the Pt return metal as zero; physical CMOS VSS is the bottom actuator rail.
``logic_V`` is the supply span VDDL-VSS, not the VDDL potential versus Pt.
"""
from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.special import expit

from .pv import PVTable


@dataclass(frozen=True)
class Parameters:
    # Every value here is a design/exploration choice, not a Reynolds fit.
    logic_series_cells: int = 4
    logic_cell_area_um2: float = 150
    actuator_cell_area_um2: float = 500  # two cells, with midpoint Pt return
    logic_storage_F: float = 50e-12
    actuator_storage_each_F: float = 200e-12
    bias_current_A: float = 5e-9
    logic_leakage_A: float = 0.2e-9
    effective_switched_F: float = 0.05e-12
    clock_Hz_at_1v6: float = 32768
    divider: int = 16384
    brownout_on_V: float = 1.60
    brownout_off_V: float = 1.45
    driver_ohm: float = 100e6
    solution_each_ohm: float = 10e6
    solution_return_ohm: float = 1e6
    actuator_area_um2: float = 200
    return_area_um2: float = 2000
    double_layer_F_m2: float = 0.2
    adsorption_C_m2: float = 1.3  # supporting 2020 scale; not a 2022 fit
    adsorption_midpoint_V: float = 0.0  # unknown Pt/electrolyte offset
    adsorption_width_V: float = 0.08
    adsorption_tau_s: float = 0.02
    faradaic_each_ohm: float = 10e9
    mechanical_tau_s: float = 0.05
    curvature_span_m_inv: float = 1e5
    hinge_length_um: float = 10
    actuator_series_cells_per_half: int = 1


def illumination(t):
    """Own test waveform: startup, darkness, recovery; no command reception."""
    return 0.0 if t < 0.05 or 3 <= t < 3.4 else 1000.0


def simulate(table: PVTable, *, dt_s=0.001, duration_s=6.0, p=Parameters(),
             light_scale=1.0, faradaic_scale=1.0, clock_response=None,
             analog_current_response=None, extra_logic_current_response=None):
    """First-order split integration; timestep convergence is checked by run.py.

    The clock is a supply-dependent behavioral phase accumulator with a
    hysteretic brownout/reset. Ideal switches plus finite Rdriver drive the
    electrodes. The default logic supply uses four series conceptual PVs;
    the published-fit experiment overrides this to three. Both differ from
    the two IC PVs in the paper. Storage capacitor area and
    driver level shifting are unresolved schematic/layout costs.

    Each interface obeys I = Cdl*deta/dt + Qmax*dtheta/dt + eta/Rfaradaic.
    theta relaxes toward a logistic adsorption curve; curvature independently
    relaxes toward kmax*(theta-0.5). A third interface models the finite Pt
    return, and solution resistances determine the floating bulk potential.
    """
    if dt_s <= 0 or duration_s <= 0 or light_scale < 0 or faradaic_scale <= 0:
        raise ValueError("Positive time/leakage parameters and non-negative light required")
    if not isinstance(p.actuator_series_cells_per_half, int) or p.actuator_series_cells_per_half < 1:
        raise ValueError("Actuator series-cell count must be a positive integer")
    t = np.arange(round(duration_s / dt_s) + 1) * dt_s
    names = ("logic_V", "positive_V", "negative_magnitude_V", "phase_cycles",
             "drive_A_V", "drive_B_V", "eta_A_V", "eta_B_V", "eta_return_V",
             "electrolyte_bulk_V", "theta_A", "theta_B", "curvature_A_m_inv",
             "curvature_B_m_inv", "current_A_A", "current_B_A", "enabled",
             "bias_W", "logic_W", "driver_W", "electrolyte_W", "faradaic_W",
             "interface_W", "adsorption_W", "actuator_PV_W", "logic_PV_W", "storage_J",
             "phase_Hz", "theta_return", "current_return_A", "electrolyte_KCL_A")
    out = {name: np.zeros(len(t)) for name in names}
    vlogic = vp = vn = phase = 0.0
    enabled = False
    eta = np.zeros(3)
    theta = np.full(3, 0.5)
    for name in ("theta_A", "theta_B", "theta_return"):
        out[name][0] = 0.5
    kappa = np.zeros(2)
    areas = np.array([p.actuator_area_um2] * 2 + [p.return_area_um2]) * 1e-12
    cap = areas * p.double_layer_F_m2
    qmax = areas * p.adsorption_C_m2
    rf = np.array([p.faradaic_each_ohm] * 2 + [
        p.faradaic_each_ohm * p.actuator_area_um2 / p.return_area_um2]) * faradaic_scale
    resistances = np.array([p.driver_ohm + p.solution_each_ohm] * 2
                           + [p.solution_return_ohm])
    conductance = 1 / resistances
    # Backward Euler for interface capacitance, Faradaic leakage and KCL.
    matrix = np.zeros((4, 4))
    matrix[:3, :3] = np.diag(cap / dt_s + 1 / rf + conductance)
    matrix[:3, 3] = conductance
    matrix[3, :3] = conductance
    matrix[3, 3] = conductance.sum()
    inverse = np.linalg.inv(matrix)
    adsorption_decay = np.exp(-dt_s / p.adsorption_tau_s)
    mechanical_decay = np.exp(-dt_s / p.mechanical_tau_s)

    def advance_supply(old, capacitance, area, cells, load, light):
        def residual(new):
            return capacitance * (new - old) / dt_s - table.current(
                new / cells, light, area) + load(new)
        limit = cells * table.voltage_V[-1]
        if residual(0) > 1e-18:
            raise RuntimeError("Supply step exhausted charge; reduce timestep")
        return brentq(residual, 0, limit, xtol=1e-12)

    for j in range(1, len(t)):
        light = illumination(t[j - 1]) * light_scale
        clock_for_load = ((clock_response(vlogic) if clock_response is not None
                           else p.clock_Hz_at_1v6 * vlogic / 1.6) if enabled else 0.0)

        def logic_load(v):
            bias = (analog_current_response(v) if analog_current_response is not None
                    else p.bias_current_A * min(v / 0.3, 1))
            leakage = p.logic_leakage_A * v / 1.6
            extra_logic = extra_logic_current_response(v) if extra_logic_current_response else 0
            return bias + leakage + extra_logic + p.effective_switched_F * v * clock_for_load
        # The independently powered logic supply is advanced before the
        # brownout/phase decision. Otherwise a collapsed supply could keep
        # the controller active for a complete extra integration step.
        vlogic = advance_supply(vlogic, p.logic_storage_F, p.logic_cell_area_um2,
                                p.logic_series_cells, logic_load, light)
        if enabled and vlogic < p.brownout_off_V:
            enabled = False
            phase = 0.0
        elif not enabled and vlogic >= p.brownout_on_V:
            enabled = True
        clock = ((clock_response(vlogic) if clock_response is not None
                  else p.clock_Hz_at_1v6 * vlogic / 1.6) if enabled else 0.0)
        phase += clock / p.divider * dt_s
        high = (np.mod(phase - np.array([0, 0.25]), 1) < 0.5)
        drive = np.where(high, vp, -vn) if enabled else np.zeros(2)
        metal = np.r_[drive, 0.0]
        equilibrium = expit((eta - p.adsorption_midpoint_V) / p.adsorption_width_V)
        new_theta = equilibrium + (theta - equilibrium) * adsorption_decay
        adsorption_A = qmax * (new_theta - theta) / dt_s
        rhs = np.r_[cap * eta / dt_s + metal * conductance - adsorption_A,
                    np.sum(metal * conductance)]
        solution = inverse @ rhs
        eta = solution[:3]
        bulk = solution[3]
        current = (metal - eta - bulk) / resistances
        if abs(current.sum()) > 1e-18:
            raise RuntimeError("Electrolyte KCL failed")
        ip = float(current[:2][high].sum()) if enabled else 0.0
        im = float(-current[:2][~high].sum()) if enabled else 0.0
        vp = advance_supply(vp, p.actuator_storage_each_F, p.actuator_cell_area_um2,
                            p.actuator_series_cells_per_half, lambda v: ip, light)
        vn = advance_supply(vn, p.actuator_storage_each_F, p.actuator_cell_area_um2,
                            p.actuator_series_cells_per_half, lambda v: im, light)

        theta = new_theta
        kappa = (p.curvature_span_m_inv * (theta[:2] - 0.5) * (1 - mechanical_decay)
                 + kappa * mechanical_decay)
        storage = (0.5 * p.logic_storage_F * vlogic**2
                   + 0.5 * p.actuator_storage_each_F * (vp**2 + vn**2)
                   + 0.5 * np.dot(cap, eta**2))
        values = (vlogic, vp, vn, phase, *drive, *eta, bulk, *theta[:2], *kappa,
                  *current[:2], int(enabled),
                  (analog_current_response(vlogic) if analog_current_response is not None
                   else p.bias_current_A * min(vlogic / 0.3, 1)) * vlogic,
                  (p.logic_leakage_A * vlogic / 1.6
                   + (extra_logic_current_response(vlogic) if extra_logic_current_response else 0)
                   + p.effective_switched_F * vlogic * clock_for_load) * vlogic,
                  np.dot(current[:2], current[:2]) * p.driver_ohm,
                  np.dot(current[:2], current[:2]) * p.solution_each_ohm
                  + current[2]**2 * p.solution_return_ohm,
                  np.sum(eta**2 / rf), np.dot(eta, current), np.dot(eta, adsorption_A),
                  table.current(vp / p.actuator_series_cells_per_half, light, p.actuator_cell_area_um2) * vp
                  + table.current(vn / p.actuator_series_cells_per_half, light, p.actuator_cell_area_um2) * vn,
                  table.current(vlogic / p.logic_series_cells, light,
                                p.logic_cell_area_um2) * vlogic,
                  storage, clock / p.divider, theta[2], current[2], current.sum())
        for name, value in zip(names, values, strict=True):
            out[name][j] = value
    out["time_s"] = t
    out["irradiance_W_m2"] = np.array([illumination(x) * light_scale for x in t])
    out["parameters"] = asdict(p)
    steady = (t > 1) & (t < 2.5)
    frequency = float(np.mean(out["phase_Hz"][steady]))
    metrics = {"dt_s": dt_s, "mean_gait_Hz": frequency,
               "startup_enable_s": float(t[np.flatnonzero(out["enabled"])[0]])
               if np.any(out["enabled"]) else None,
               "steady_logic_V": float(np.mean(out["logic_V"][steady])),
               "steady_actuator_span_V": float(np.mean((
                   out["positive_V"] + out["negative_magnitude_V"])[steady])),
               "bending_peak_to_peak_rad": float(np.ptp(out["curvature_A_m_inv"][steady])
                                                 * p.hinge_length_um * 1e-6)}
    def rising_times(name):
        value = out[name]
        indices = np.flatnonzero((value[:-1] <= 0) & (value[1:] > 0)
                                 & steady[1:]) + 1
        return t[indices]
    rising_a, rising_b = rising_times("drive_A_V"), rising_times("drive_B_V")
    delays = [b - rising_a[rising_a < b][-1] for b in rising_b if np.any(rising_a < b)]
    metrics["measured_phase_B_lag_cycles"] = float(np.mean(delays) * frequency) if delays else None
    metrics["enable_transitions"] = int(np.count_nonzero(np.diff(out["enabled"]) > 0))
    for part in ("bias", "logic", "driver", "electrolyte", "faradaic", "interface",
                 "adsorption",
                 "actuator_PV", "logic_PV"):
        power = float(np.mean(out[f"{part}_W"][steady]))
        metrics[f"{part}_mean_W"] = power
        metrics[f"{part}_J_per_cycle"] = power / frequency if frequency else None
    # I*eta includes capacitive and adsorption storage, so it is not all heat.
    metrics["capacitor_final_J"] = float(out["storage_J"][-1])
    input_J = np.sum(out["logic_PV_W"] + out["actuator_PV_W"]) * dt_s
    accounted_J = out["storage_J"][-1] + dt_s * sum(np.sum(out[f"{part}_W"])
        for part in ("bias", "logic", "driver", "electrolyte", "faradaic", "adsorption"))
    metrics["electrical_energy_balance_relative_residual"] = float(
        (input_J - accounted_J) / input_J) if input_J else 0.0
    out["metrics"] = metrics
    return out
