"""Idealized two-state closed-loop driver model of the reduced-model study.

The model implements the equations of REDUCED_MODEL_ANALYSIS.md exactly:

    tau_d dVd/dt = Vcmd + A_e (Vcmd - Vout) - Vd
    C_T dVout/dt = (Vd - Vout)/Rout - Idist

No transistor topology, SKY130 device, switch charge injection, or parasitic
mechanism is included in this phase.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm


@dataclass(frozen=True)
class SourceParams:
    A_e: float
    tau_d: float
    Rout: float
    Co: float
    Cs: float
    Vtarget: float

    @property
    def C_total(self) -> float:
        return self.Co + self.Cs

    @property
    def rc_time(self) -> float:
        return self.Rout * self.C_total


def equilibrium(vcmd: float) -> np.ndarray:
    """DC equilibrium [Vd, Vout] for a constant command and zero disturbance."""
    return np.array([vcmd, vcmd], dtype=float)


def state_matrix(p: SourceParams, C_total: float | None = None) -> np.ndarray:
    C = p.C_total if C_total is None else C_total
    return np.array(
        [
            [-1.0 / p.tau_d, -p.A_e / p.tau_d],
            [1.0 / (p.Rout * C), -1.0 / (p.Rout * C)],
        ],
        dtype=float,
    )


def command_input_vector(p: SourceParams) -> np.ndarray:
    return np.array([(1.0 + p.A_e) / p.tau_d, 0.0], dtype=float)


def disturbance_input_vector(C_total: float) -> np.ndarray:
    """Input vector for Idist with the sign convention of the analysis."""
    return np.array([0.0, -1.0 / C_total], dtype=float)


def characteristic_coefficients(p: SourceParams, C_total: float | None = None) -> np.ndarray:
    """Coefficients of D(s) in descending powers of s.

    D(s) = (tau_d s + 1)(Rout C_T s + 1) + A_e
         = tau_d Rout C_T s^2 + (tau_d + Rout C_T)s + (1 + A_e)
    """
    C = p.C_total if C_total is None else C_total
    rc = p.Rout * C
    return np.array([p.tau_d * rc, p.tau_d + rc, 1.0 + p.A_e], dtype=float)


def poles_from_denominator(p: SourceParams, C_total: float | None = None) -> np.ndarray:
    return np.roots(characteristic_coefficients(p, C_total))


def poles_from_state_matrix(p: SourceParams, C_total: float | None = None) -> np.ndarray:
    return np.linalg.eigvals(state_matrix(p, C_total))


def gcmd_polynomials(p: SourceParams, C_total: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return numerator/denominator of Gcmd(s) in the dimensionless D(s) form of the analysis."""
    return np.array([1.0 + p.A_e]), characteristic_coefficients(p, C_total)


def zout_polynomials(p: SourceParams, C_total: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return numerator/denominator of Zout_cl(s) = -Vout/Idist.

    Zout_cl(s) = Rout (tau_d s + 1) / D(s)
    """
    return np.array([p.Rout * p.tau_d, p.Rout]), characteristic_coefficients(p, C_total)


def exact_constant_command(
    t: Iterable[float],
    x0: np.ndarray,
    vcmd: float,
    p: SourceParams,
    C_total: float | None = None,
) -> np.ndarray:
    """Exact linear state-space solution for constant command and zero Idist."""
    A = state_matrix(p, C_total)
    xeq = equilibrium(vcmd)
    t = np.asarray(list(t), dtype=float)
    out = np.empty((t.size, 2), dtype=float)
    delta0 = np.asarray(x0, dtype=float) - xeq
    for i, ti in enumerate(t):
        out[i] = xeq + expm(A * ti) @ delta0
    return out


def integrate_constant_command(
    t: Iterable[float],
    x0: np.ndarray,
    vcmd: float,
    p: SourceParams,
    C_total: float | None = None,
) -> np.ndarray:
    """Numerical integration cross-check using solve_ivp."""
    C = p.C_total if C_total is None else C_total
    t = np.asarray(list(t), dtype=float)

    def rhs(_t: float, x: np.ndarray) -> np.ndarray:
        vd, vout = x
        dvd = (vcmd + p.A_e * (vcmd - vout) - vd) / p.tau_d
        dvout = (vd - vout) / (p.Rout * C)
        return np.array([dvd, dvout], dtype=float)

    sol = solve_ivp(
        rhs,
        (float(t[0]), float(t[-1])),
        np.asarray(x0, dtype=float),
        t_eval=t,
        rtol=1e-10,
        atol=1e-12,
        method="DOP853",
    )
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol.y.T


def charge_shared_voltage(Vtarget: float, Vprev: float, Co: float, Cs: float) -> float:
    return (Co * Vtarget + Cs * Vprev) / (Co + Cs)


def connected_initial_state(p: SourceParams, delta_vprev: float) -> np.ndarray:
    """A2 state just after ideal charge sharing.

    delta_vprev = Vtarget - Vprev. Positive values mean Vprev is below target.
    """
    vprev = p.Vtarget - delta_vprev
    vout0 = charge_shared_voltage(p.Vtarget, vprev, p.Co, p.Cs)
    return np.array([p.Vtarget, vout0], dtype=float)


def command_initial_state(vstart: float) -> np.ndarray:
    """A0 state just after command changes, assuming prior settled equilibrium."""
    return equilibrium(vstart)


def matched_a3_command_start(p: SourceParams, delta_vprev: float) -> float:
    """Prior command level giving the same initial Vout error as A2 after sharing."""
    e0 = (p.Cs / (p.Co + p.Cs)) * abs(delta_vprev)
    sign = 1.0 if delta_vprev >= 0 else -1.0
    return p.Vtarget - sign * e0


def with_updates(p: SourceParams, **kwargs: float) -> SourceParams:
    return replace(p, **kwargs)
