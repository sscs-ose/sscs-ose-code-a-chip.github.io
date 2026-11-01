"""
opentcad/device/models/bgn.py — Bandgap-narrowing models.

BGN reduces the effective bandgap in heavily-doped regions, raising the
effective intrinsic density:

    n_i_eff = n_i * exp(dEg(N) / (2*V_t))

Every place the solver used `n_i` (Poisson, contact BCs, recombination)
substitutes `n_i_expr()` from the active BGN model. NoBGN is the default
and is a no-op — the expression is just the parameter `n_i`.

Models:
  NoBGN     — no bandgap narrowing (Phase 0 baseline)
  Slotboom  — Slotboom (1976) empirical fit for Si, standard workhorse
"""
from __future__ import annotations
from ..physics import BandgapNarrowingModel


class NoBGN(BandgapNarrowingModel):
    """No bandgap narrowing. n_i stays constant. Used as the default so
    existing callers get identical behavior to Phase 0."""

    def attach(self, ds, device, region, params, T_K):
        # Nothing to register — the solver falls back to the plain n_i
        # parameter that _set_region_parameters already writes.
        pass

    def n_i_expr(self): return "n_i"


class Slotboom(BandgapNarrowingModel):
    """Slotboom empirical bandgap narrowing (1976, updated fit).

        dEg(N) = E_ref * ( ln(N / N_ref)
                          + sqrt(ln(N / N_ref)^2 + 0.5) )   [eV]

    where N is |NetDoping|, N_ref = 1e17 cm^-3, E_ref = 6.92 meV in the
    updated del Alamo / Slotboom fit (Klaassen unified BGN gives similar
    results). Below N_ref, dEg is essentially 0.

    n_i_eff = n_i * exp(dEg / (2*V_t))

    Reference: Slotboom & de Graaff, Solid-State Electron. 19, 857 (1976).
    """

    #: Reference bandgap-narrowing prefactor [eV]. Common Si fits use
    #: 6.92 meV (del Alamo/Klaassen unified) or 9 meV (original Slotboom);
    #: 6.92 gives closer agreement with modern SIMS-calibrated data.
    E_ref_eV: float = 6.92e-3
    #: Reference doping at which dEg starts to activate [cm^-3].
    N_ref_cm3: float = 1.0e17

    def attach(self, ds, device, region, params, T_K):
        ds.set_parameter(device=device, region=region, name="BGN_Eref",
                         value=float(self.E_ref_eV))
        ds.set_parameter(device=device, region=region, name="BGN_Nref",
                         value=float(self.N_ref_cm3))
        # Total ionised dopant. Use max(., 1) to keep log() finite when
        # a region has literally zero doping.
        ds.node_model(device=device, region=region, name="BGN_N",
                      equation="max((Donors + Acceptors), 1)")
        # ln(N/N_ref). Slotboom formula.
        ds.node_model(device=device, region=region, name="BGN_ln",
                      equation="log(BGN_N / BGN_Nref)")
        # dEg [eV]. Slotboom sqrt() form is always >= 0 for any real ln.
        ds.node_model(
            device=device, region=region, name="BGN_dEg",
            equation="BGN_Eref * (BGN_ln + (BGN_ln*BGN_ln + 0.5)^(0.5))")
        # n_i_eff = n_i * exp(dEg / (2*V_t)). n_i and V_t are parameters
        # already set on the region by DeviceSolver.
        ds.node_model(device=device, region=region, name="n_i_eff",
                      equation="n_i * exp(BGN_dEg / (2*V_t))")

    def n_i_expr(self): return "n_i_eff"
