"""
opentcad.process.doping.implant — Analytic ion-implant kernel.

Takes a MeshField with populated geometry (material_id per cell) and
*adds* the depth profile of a Pearson-IV-type ion implant to its
donor or acceptor field — producing the Nd / Na the downstream device
solver will read.

Physics (MVP):

  * Vertical profile is a Gaussian in depth below the top surface,
    centred on the projected range Rp with standard deviation dRp
    (both looked up from `pearson_iv.moments_for`). Shipping the full
    Pearson-IV shape with skewness γ and kurtosis β is on the backlog;
    gamma and beta sit in the YAML tables already, waiting for the
    evaluator.

  * Lateral straggle is folded into the mask edge by replacing the hard
    rectangular window with an erf-based blur of characteristic width
    σ_lat ≈ 0.7 · dRp (literature-standard first approximation; the
    exact ratio depends weakly on species and energy and belongs with
    the Pearson-IV upgrade).

  * Dose is per unit area (cm⁻²) and conserves itself: the integral of
    the vertical profile over depth equals the local effective dose
    seen at each column after the mask-edge blur. In the window centre
    the local dose equals the input dose; far outside it decays to zero.

  * Donor species (phosphorus, arsenic) add to Nd; acceptor species
    (boron) add to Na. The MeshField's `net_doping = Nd - Na` reflects
    the sum of every implant plus whatever doping the Structure DSL
    seeded. Nothing is deleted or clipped: two implants of the same
    species accumulate.

  * Tilt is a documented but unimplemented parameter; a nonzero tilt
    logs a warning and is otherwise ignored (shifts Rp by cos(tilt)
    and offsets the lateral mask, both one-liners when we add them).

Surface detection: for Phase 2.1 we treat the top of the wafer as flat
and take `y_surface = max y across the mesh`. This holds for the hand-
built Structure devices Phase 0 targets, and for the post-LOCOS stacks
we tested in Phase 1 (field oxide mesa is 0.5 µm tall but S/D implants
land in the active area where the surface is flat). Per-column surface
lookup is a Unit-B refinement.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from opentcad.geometry.formats import Material, MeshField

from .pearson_iv import PearsonMoments, canonicalize_species, moments_for


#: µm → cm conversion for the DEVSIM side of the house.
_UM_TO_CM = 1e-4


@dataclass(frozen=True)
class ImplantResult:
    """Diagnostic summary returned alongside the in-place mutation.

    Lets tests and the GUI inspect what the implant actually did
    without re-deriving the Pearson lookup."""
    species: str
    energy_keV: float
    dose_cm2: float
    moments: PearsonMoments
    sigma_lat_um: float
    window_x_um: Optional[Tuple[float, float]]
    added_to: str                       # "Nd" or "Na"
    integrated_added_per_unit_width: float   # cm⁻¹ (dose · window width in cm)


def apply_implant(mf: MeshField,
                  species: str,
                  energy_keV: float,
                  dose_cm2: float,
                  window_x_um: Optional[Tuple[float, float]] = None,
                  *,
                  target: Material = Material.SI,
                  sigma_lat_frac: float = 0.7,
                  tilt_deg: float = 0.0,
                  ) -> ImplantResult:
    """Apply an ion implant to *mf* in place; return a diagnostic record.

    Args:
        mf: MeshField to dope. Mutated in place — Nd or Na point_data
            arrays get the implant contribution added.
        species: "boron" / "B" / "phosphorus" / "P" / "arsenic" / "As"
            (case-insensitive; see pearson_iv.canonicalize_species).
        energy_keV: implant energy in keV. Must lie in the tabulated
            range for the species (Pearson lookup refuses to extrapolate).
        dose_cm2: dose per unit area in cm⁻². Typical S/D implants are
            1e14-1e16 cm⁻².
        window_x_um: optional (x0, x1) mask opening in µm. The mask
            edge is softened by an erf blur of width σ_lat (lateral
            straggle) so the physical pattern of concentration past the
            mask edge is reproduced to first order.
        target: substrate material the Pearson table applies to. Only
            Si is tabulated today; the kwarg is here so the API doesn't
            change when we ship GaN/4H-SiC tables.
        sigma_lat_frac: σ_lat as a fraction of dRp. Default 0.7 is a
            literature-standard compromise across species and energies.
        tilt_deg: documented but not yet implemented; nonzero → warning.

    Returns:
        ImplantResult diagnostic record.
    """
    if dose_cm2 <= 0:
        raise ValueError(f"dose must be positive (got {dose_cm2} cm⁻²)")
    if tilt_deg != 0.0:
        warnings.warn(
            f"apply_implant: tilt_deg={tilt_deg} ignored (not yet "
            "implemented; vertical implant assumed).",
            stacklevel=2)

    moments = moments_for(species, energy_keV, target=target)
    canonical = canonicalize_species(species)
    sigma_lat_um = float(sigma_lat_frac) * moments.dRp_um

    # Points in physical (x, y) µm.
    pts_um = np.asarray(mf.grid.points, dtype=float)[:, :2]
    xs_um = pts_um[:, 0]
    ys_um = pts_um[:, 1]

    # Flat-top-surface assumption: implant from above, surface at
    # max y. Per-column surface tracking is deferred to Unit B.
    y_surface_um = float(ys_um.max())
    depth_um = y_surface_um - ys_um
    # Beam enters at y_surface; nodes above surface get zero contribution.
    valid = depth_um >= -1e-9
    depth_um = np.clip(depth_um, 0.0, None)

    # Vertical Gaussian in cm (DEVSIM-compatible units).
    Rp_cm = moments.Rp_um * _UM_TO_CM
    dRp_cm = moments.dRp_um * _UM_TO_CM
    depth_cm = depth_um * _UM_TO_CM
    peak_norm_cm_inv = 1.0 / (math.sqrt(2.0 * math.pi) * dRp_cm)
    vertical = peak_norm_cm_inv * np.exp(
        -0.5 * ((depth_cm - Rp_cm) / dRp_cm) ** 2)

    # Lateral mask: effective local dose at each x after erf blur of
    # the window edges. In the limit sigma_lat → 0 this reproduces a
    # hard mask; in the limit window → whole domain it reproduces an
    # unmasked blanket implant.
    if window_x_um is None:
        local_dose_cm2 = np.full_like(xs_um, float(dose_cm2))
    else:
        x0, x1 = window_x_um
        if not (x1 > x0):
            raise ValueError(
                f"window_x_um must be (x0, x1) with x1 > x0; got "
                f"{window_x_um!r}")
        s = sigma_lat_um
        # 0.5 * [erf((x1 - x) / (√2 · σ)) - erf((x0 - x) / (√2 · σ))]
        from scipy.special import erf
        attenuation = 0.5 * (
            erf((x1 - xs_um) / (math.sqrt(2.0) * s))
            - erf((x0 - xs_um) / (math.sqrt(2.0) * s))
        )
        local_dose_cm2 = float(dose_cm2) * attenuation

    contribution = vertical * local_dose_cm2  # cm⁻³
    contribution = np.where(valid, contribution, 0.0)

    # Add to Nd / Na. MeshField's property setters validate shape +
    # non-negativity; we read current values via the properties (which
    # return zeros if absent), add, and write back.
    is_donor = moments.dopant_kind == "donor"
    if is_donor:
        new_vals = mf.Nd + contribution
        mf.Nd = new_vals
        added_to = "Nd"
    else:
        new_vals = mf.Na + contribution
        mf.Na = new_vals
        added_to = "Na"

    window_width_cm = (
        (window_x_um[1] - window_x_um[0]) * _UM_TO_CM
        if window_x_um is not None
        else (float(xs_um.max()) - float(xs_um.min())) * _UM_TO_CM
    )
    integrated = float(dose_cm2) * window_width_cm

    return ImplantResult(
        species=canonical,
        energy_keV=float(energy_keV),
        dose_cm2=float(dose_cm2),
        moments=moments,
        sigma_lat_um=sigma_lat_um,
        window_x_um=window_x_um,
        added_to=added_to,
        integrated_added_per_unit_width=integrated,
    )
