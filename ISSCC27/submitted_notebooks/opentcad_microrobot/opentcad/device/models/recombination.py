"""
opentcad/device/models/recombination.py — Net recombination contributors.

Each model registers a single node_model expression returning the rate
multiplied by -q (so DEVSIM's continuity equation, which expects an
A/cm^3 source, can sum it directly). The solver builds the total
recombination as the sum of every registered model's term_name.

Models implemented:
  SRH       — Shockley-Read-Hall, mid-gap traps (Phase 0 default)
  Auger     — three-particle band-to-band, dominant at >1e18 cm^-3
  Radiative — band-to-band photon emission (negligible in Si, central
              for direct-gap III-V)
"""
from __future__ import annotations
from ..physics import RecombinationModel


def _node_with_carrier_derivs(ds, device, region, name, eq):
    """Helper: register a node model and its derivatives w.r.t. Electrons
    and Holes via DEVSIM symbolic diff(). Used by every recombination
    contributor."""
    ds.node_model(device=device, region=region, name=name, equation=eq)
    for var in ("Electrons", "Holes"):
        ds.node_model(device=device, region=region,
                      name=f"{name}:{var}",
                      equation=f"simplify(diff({eq}, {var}))")


class SRH(RecombinationModel):
    """Shockley-Read-Hall recombination with a single mid-gap trap.

    U_SRH = (n*p - n_i^2) / (tau_p*(n + n1) + tau_n*(p + p1))

    Parameters tau_n_s, tau_p_s come from MaterialParams.recombination.
    n1 = p1 = n_i for a mid-gap trap (Et = 0 in the YAML default).
    `n_i_expr` is substituted for the bare n_i wherever BGN is active."""

    term_name = "USRH"

    def attach(self, ds, device, region, params, T_K, n_i_expr="n_i"):
        ds.set_parameter(device=device, region=region, name="taun",
                         value=float(params.recombination.tau_n_s))
        ds.set_parameter(device=device, region=region, name="taup",
                         value=float(params.recombination.tau_p_s))
        ds.set_parameter(device=device, region=region, name="n1",
                         value=float(params.band_structure.ni_cm3_300K))
        ds.set_parameter(device=device, region=region, name="p1",
                         value=float(params.band_structure.ni_cm3_300K))
        eq = (f"-ElectronCharge*(Electrons*Holes - ({n_i_expr})^2)/"
              f"(taup*(Electrons + n1) + taun*(Holes + p1))")
        _node_with_carrier_derivs(ds, device, region, self.term_name, eq)


class Auger(RecombinationModel):
    """Auger recombination — three-particle process where the energy
    released by an electron-hole recombination is given to a third
    carrier instead of a photon.

    U_Auger = (C_n*n + C_p*p) * (n*p - n_i^2)

    Coefficients C_n, C_p for Si: Dziewior & Schmid, APL 31, 346 (1977).
    Auger dominates over SRH for carrier densities > ~1e18 cm^-3, i.e.
    in the n+ emitter / source-drain regions of bipolar and MOS devices.
    """

    term_name = "UAuger"

    def attach(self, ds, device, region, params, T_K, n_i_expr="n_i"):
        ds.set_parameter(device=device, region=region, name="Cn_Auger",
                         value=float(params.recombination.Cn_cm6_per_s))
        ds.set_parameter(device=device, region=region, name="Cp_Auger",
                         value=float(params.recombination.Cp_cm6_per_s))
        eq = (f"-ElectronCharge*(Cn_Auger*Electrons + Cp_Auger*Holes)*"
              f"(Electrons*Holes - ({n_i_expr})^2)")
        _node_with_carrier_derivs(ds, device, region, self.term_name, eq)


class Radiative(RecombinationModel):
    """Band-to-band radiative recombination.

    U_rad = B * (n*p - n_i^2)

    Coefficient B from MaterialParams.recombination.B_rad_cm3_per_s.
    Negligible in indirect-gap Si (B ~ 1e-14 cm^3/s); dominant in direct-
    gap GaAs/GaN (B ~ 1e-10)."""

    term_name = "URad"

    def attach(self, ds, device, region, params, T_K, n_i_expr="n_i"):
        ds.set_parameter(device=device, region=region, name="B_rad",
                         value=float(params.recombination.B_rad_cm3_per_s))
        eq = (f"-ElectronCharge*B_rad*"
              f"(Electrons*Holes - ({n_i_expr})^2)")
        _node_with_carrier_derivs(ds, device, region, self.term_name, eq)
