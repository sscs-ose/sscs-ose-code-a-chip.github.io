"""Reduced photovoltaic terminal model and optional SPICE text export.

This model fits terminal IV data; it does not infer a unique doping profile,
optical stack, lifetime or process. SI electrical units, temperature in K.
Only matched series cells, an ideal diode and prescribed photocurrent are
supported. Rs, shunt leakage, breakdown, junction charge and mismatch are absent.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re

import numpy as np
from scipy.optimize import brentq, least_squares

Q_C = 1.602176634e-19
KB_J_K = 1.380649e-23


@dataclass(frozen=True)
class SingleDiodePV:
    """Delivering current is positive; dark forward terminal current is negative.

    ``I = Iph_ref * E/Eref - I0 * expm1(V/(Ns*n*kT/q))``.
    ``ideality`` is per cell and ``saturation_A`` is the current through the
    series string. Parameters are defined at ``temperature_K`` only. Changing
    temperature requires a separately justified parameter set.
    """

    saturation_A: float
    ideality: float
    photocurrent_A: float
    reference_irradiance_W_m2: float = 1000.0
    series_cells: int = 1
    temperature_K: float = 300.0

    def __post_init__(self):
        positive = (self.saturation_A, self.ideality, self.reference_irradiance_W_m2,
                    self.temperature_K)
        if not all(np.isfinite(x) and x > 0 for x in positive):
            raise ValueError("I0, ideality, reference irradiance and temperature must be positive")
        if not np.isfinite(self.photocurrent_A) or self.photocurrent_A < 0:
            raise ValueError("photocurrent_A must be finite and non-negative")
        if self.series_cells < 1 or int(self.series_cells) != self.series_cells:
            raise ValueError("series_cells must be a positive integer")

    @property
    def diode_voltage_V(self):
        return self.series_cells * self.ideality * KB_J_K * self.temperature_K / Q_C

    def current_A(self, voltage_V, irradiance_W_m2=1000.0):
        voltage = np.asarray(voltage_V, dtype=float)
        light = np.asarray(irradiance_W_m2, dtype=float)
        if np.any(~np.isfinite(voltage)) or np.any(~np.isfinite(light)) or np.any(light < 0):
            raise ValueError("Finite voltages and non-negative finite irradiance required")
        return (self.photocurrent_A * light / self.reference_irradiance_W_m2
                - self.saturation_A * np.expm1(voltage / self.diode_voltage_V))

    def open_circuit_V(self, irradiance_W_m2=1000.0):
        if not np.isfinite(irradiance_W_m2) or irradiance_W_m2 < 0:
            raise ValueError("Non-negative finite irradiance required")
        return float(self.diode_voltage_V * np.log1p(self.photocurrent_A
                     * irradiance_W_m2 / self.reference_irradiance_W_m2 / self.saturation_A))

    def maximum_power_point(self, irradiance_W_m2=1000.0):
        """Return (V, delivering A, W) at the unique first-quadrant maximum."""
        voc = self.open_circuit_V(irradiance_W_m2)
        if voc == 0:
            return 0.0, 0.0, 0.0
        a = self.diode_voltage_V

        def derivative(v):
            return (self.current_A(v, irradiance_W_m2)
                    - v * self.saturation_A * np.exp(v / a) / a)
        v = brentq(derivative, 0, voc, xtol=1e-13)
        i = float(self.current_A(v, irradiance_W_m2))
        return v, i, v * i

    def scaled_current(self, factor: float):
        """Scale I0 and Iph together, e.g. assumed identical current density.

        This preserves Voc, but is not valid when edge recombination, shading
        or contact geometry change with physical device area.
        """
        if not np.isfinite(factor) or factor <= 0:
            raise ValueError("factor must be finite and positive")
        return replace(self, saturation_A=self.saturation_A * factor,
                       photocurrent_A=self.photocurrent_A * factor)

    def spice_subcircuit(self, name="photovoltaic"):
        """Export an ideal diode + photocurrent subcircuit with pins p, n.

        Run SPICE at the fitted temperature (in Celsius). No capacitance is
        inferred from DC IV. ``illumination`` is W/m²; ``area_scale`` multiplies
        both currents. The external simulator is not a Python dependency.
        """
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError("Use a simple SPICE subcircuit identifier")
        return (f"* Terminal fit at {self.temperature_K:g} K; no charge/Rs/shunt model\n"
                f".subckt {name} p n params: illumination={self.reference_irradiance_W_m2:g} "
                "area_scale=1\n"
                f"Iphoto n p DC {{{self.photocurrent_A:.12g}*illumination/"
                f"{self.reference_irradiance_W_m2:g}*area_scale}}\n"
                f"Dpv p n {name}_diode area={{area_scale}}\n"
                f".model {name}_diode D(IS={self.saturation_A:.12g} "
                f"N={self.ideality*self.series_cells:.12g} "
                f"TNOM={self.temperature_K-273.15:.12g} EG=0 XTI=0)\n"
                f".ends {name}\n")


def fit_single_diode(voltage_V, delivered_A, irradiance_W_m2, *, series_cells=1,
                     temperature_K=300.0, reference_irradiance_W_m2=1000.0,
                     uncertainty_A=None):
    """Fit I0, per-cell ideality and Iph to dark/illuminated terminal data.

    Ideality is constrained to 0.5..4 (an explicit model bound); Rs and shunt
    leakage are fixed absent. At least two light levels and a forward-current
    region are required. Supplied uncertainties weight current residuals.
    Returned diagnostics are numerical fit metrics, not confidence intervals.
    Horizontal uncertainty and parameter non-uniqueness need separate analysis.
    """
    v, i, light = np.broadcast_arrays(np.asarray(voltage_V, dtype=float),
                                      np.asarray(delivered_A, dtype=float),
                                      np.asarray(irradiance_W_m2, dtype=float))
    if (v.ndim != 1 or len(v) < 6 or not all(np.all(np.isfinite(a)) for a in (v, i, light))
            or np.any(light < 0) or len(np.unique(light)) < 2 or not np.any(i < 0)):
        raise ValueError("Supply finite 1D dark/light data including forward current")
    # Validate metadata even before creating optimization parameters.
    trial = SingleDiodePV(1e-18, 1, 1e-9, reference_irradiance_W_m2,
                          series_cells, temperature_K)
    scale = max(float(np.max(np.abs(i))), 1e-30)
    sigma = np.broadcast_to(np.asarray(uncertainty_A if uncertainty_A is not None
                                      else scale * 1e-3, dtype=float), v.shape)
    if np.any(~np.isfinite(sigma)) or np.any(sigma <= 0):
        raise ValueError("uncertainty_A must be finite and positive")
    iph_guess = max(float(np.max(i)), scale * 0.1)
    n_guess = 1.2
    v_forward = float(np.max(v))
    i0_guess = max(scale * np.exp(-v_forward / (trial.diode_voltage_V * n_guess)),
                   scale * 1e-20)

    def model(x):
        i0, ideality, iph = np.exp(x)
        return SingleDiodePV(i0, ideality, iph, reference_irradiance_W_m2,
                             series_cells, temperature_K)

    def residual(x):
        return (model(x).current_A(v, light) - i) / sigma
    fit = least_squares(residual, np.log([i0_guess, n_guess, iph_guess]),
                        bounds=(np.log([scale*1e-30, 0.5, scale*1e-8]),
                                np.log([scale, 4, scale*1e3])),
                        x_scale="jac", max_nfev=2000, ftol=1e-12, xtol=1e-12, gtol=1e-10)
    if not fit.success:
        raise RuntimeError(f"Single-diode fit failed: {fit.message}")
    fitted = model(fit.x)
    error = fitted.current_A(v, light) - i
    return fitted, {"rms_current_error_A": float(np.sqrt(np.mean(error**2))),
                    "maximum_current_error_A": float(np.max(np.abs(error))),
                    "weighted_rms_residual": float(np.sqrt(np.mean(residual(fit.x)**2))),
                    "evaluations": int(fit.nfev), "points": len(v),
                    "ideality_at_bound": bool(np.any(fit.active_mask[1]))}
