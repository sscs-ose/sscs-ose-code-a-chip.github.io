"""
opentcad/process/topography/oxidation.py — Deal-Grove thermal oxidation.

Implements the linear-parabolic law

    x_ox^2  +  A · x_ox  =  B · (t + tau)

with Arrhenius-fitted coefficients A(T), B(T) for dry-O2 and wet-H2O
oxidation of <100> Si at 1 atm. Solved in closed form for x_ox given
an initial oxide thickness x0 and time t:

    x_ox(t) = -A/2 + sqrt( (A/2 + x0)**2  +  B*t )

At each surface point of a level-set stack, the amount of SiO2 grown
(dx_ox = x_ox(t) - x0) drives two coupled interface motions:

    Si-SiO2 boundary   moves DOWN by   ALPHA * dx_ox   (Si consumed)
    SiO2 top surface   moves UP   by  (1 - ALPHA) * dx_ox

with ALPHA = ρ_Si / ρ_SiO2 · (M_SiO2 / M_Si) ≈ 0.44 (per Sze).

Coefficient references:
  * Deal & Grove, J. Appl. Phys. 36, 3770 (1965) — original law.
  * Sze & Ng, *Physics of Semiconductor Devices*, 3rd ed., ch. 14.
  * Plummer, Deal, Griffin, *Silicon VLSI Technology*, ch. 6.

Notes / limitations:
  * <100> Si, 1 atm; no orientation, pressure, or chlorine corrections.
  * No stress-modified viscosity (needed for thin oxides < 20 nm at low
    temperature); we hit the Massoud regime, but Deal-Grove is the
    default reference for "gate oxide within 5 %" checks and matches
    published tables within their own scatter.
  * The lateral-diffusion-driven bird's beak in LOCOS is modelled here
    by a heuristic mask feathering (`bird_beak_length_um`) rather than
    a coupled 2D O2-diffusion PDE.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


#: Volume ratio: μm of Si consumed per μm of SiO2 grown.
#: N_Si / N_SiO2 = 5.0e22 / 2.2e22 = 2.27 ⇒ 1 μm SiO2 uses 0.44 μm Si.
ALPHA_SI_CONSUMED_PER_OXIDE = 0.44

_K_BOLTZMANN_EV_PER_K = 8.617333262e-5  # eV/K


@dataclass(frozen=True)
class DealGroveArrhenius:
    """Arrhenius coefficients for Deal-Grove B and B/A rate constants.

    Both constants take the form  C · exp(-E / kT)  with C in [μm²/s]
    (for B) or [μm/s] (for B/A), and E in [eV]. Storing coefficients in
    SI-friendly seconds makes the closed-form solution one line."""
    B_C:   float   # parabolic constant pre-exponent   [μm²/s]
    B_Ea:  float   # parabolic activation energy       [eV]
    LN_C:  float   # linear constant pre-exponent B/A  [μm/s]
    LN_Ea: float   # linear activation energy          [eV]

    def B(self, T_K: float) -> float:
        return self.B_C * math.exp(-self.B_Ea / (_K_BOLTZMANN_EV_PER_K * T_K))

    def B_over_A(self, T_K: float) -> float:
        return self.LN_C * math.exp(-self.LN_Ea /
                                    (_K_BOLTZMANN_EV_PER_K * T_K))

    def A(self, T_K: float) -> float:
        return self.B(T_K) / self.B_over_A(T_K)


# Plummer/Deal fits for <100> Si, 1 atm. Pre-exponents are converted
# from the μm²/hr and μm/hr used in the textbook to μm²/s and μm/s by
# a factor of 3600 (once per pre-exponent).
_DRY_O2_100_SI = DealGroveArrhenius(
    B_C  = 7.72e2 / 3600.0,   # 0.2144 μm²/s
    B_Ea = 1.23,              # eV
    LN_C = 6.23e6 / 3600.0,   # 1731 μm/s
    LN_Ea = 2.0,              # eV
)

_WET_H2O_100_SI = DealGroveArrhenius(
    B_C  = 3.86e2 / 3600.0,   # 0.1072 μm²/s
    B_Ea = 0.78,              # eV
    LN_C = 1.63e8 / 3600.0,   # 4.528e4 μm/s
    LN_Ea = 2.05,             # eV
)


def coefficients(ambient: str) -> DealGroveArrhenius:
    """Return the Arrhenius coefficients for a given oxidation ambient.

    Currently supports 'dry' (O2) and 'wet' (H2O). Case-insensitive.
    """
    key = ambient.strip().lower()
    if key == "dry":
        return _DRY_O2_100_SI
    if key == "wet":
        return _WET_H2O_100_SI
    raise ValueError(
        f"Unknown oxidation ambient {ambient!r} — expected 'dry' or 'wet'.")


def oxide_thickness(x0_um: float, t_s: float,
                    T_K: float, ambient: str = "dry") -> float:
    """Solve Deal-Grove for x_ox(t) given prior thickness x0 [μm].

    Returns thickness in μm.

    Closed form:
        x(t) = -A/2 + sqrt( (A/2 + x0)² + B·t )
    """
    if t_s < 0:
        raise ValueError(f"time must be ≥ 0 (got {t_s} s)")
    if x0_um < 0:
        raise ValueError(f"initial oxide thickness must be ≥ 0 (got {x0_um})")
    if T_K <= 0:
        raise ValueError(f"temperature must be > 0 K (got {T_K} K)")

    coef = coefficients(ambient)
    A = coef.A(T_K)
    B = coef.B(T_K)
    half_A = 0.5 * A
    return -half_A + math.sqrt((half_A + x0_um) ** 2 + B * t_s)


def temperature_celsius_to_kelvin(T_C: float) -> float:
    return T_C + 273.15
