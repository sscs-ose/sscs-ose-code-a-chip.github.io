"""Prescribed optical generation for drift-diffusion (SI optical inputs).

This is a single-pass, monochromatic Beer-Lambert model, not an optical
field solver. Absorption and reflection must be supplied by the caller.
No interference, scattering, spectral database or surface recombination
is implied. Geometry uses um; generation uses electron-hole pairs/cm^3/s.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from opentcad.geometry.formats import Material, MeshField

GENERATION_FIELD = "optical_generation_cm3_s"
H_J_S = 6.62607015e-34
C_M_S = 299792458.0


@dataclass(frozen=True)
class BeerLambert:
    """Uniform incident irradiance on a flat, homogeneous absorbing slab.

    ``G(d) = yield * (1-R) * irradiance / photon_energy * alpha * exp(-alpha*d)``.
    Irradiance is W/m^2, wavelength nm, alpha cm^-1, depth um. ``quantum_yield``
    is pairs per absorbed photon (0..1). It is not collection efficiency;
    carrier collection is computed by drift-diffusion. The caller must use
    a wavelength/absorption coefficient appropriate to the material/bandgap.
    """

    wavelength_nm: float
    irradiance_W_m2: float
    absorption_cm_inv: float
    reflectance: float = 0.0
    quantum_yield: float = 1.0

    def __post_init__(self):
        values = np.array(list(asdict(self).values()), dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("Optical parameters must be finite")
        if self.wavelength_nm <= 0:
            raise ValueError("wavelength_nm must be positive")
        if self.irradiance_W_m2 < 0 or self.absorption_cm_inv < 0:
            raise ValueError("irradiance and absorption must be non-negative")
        if not 0 <= self.reflectance <= 1 or not 0 <= self.quantum_yield <= 1:
            raise ValueError("reflectance and quantum_yield must be in [0, 1]")

    @property
    def photon_flux_cm2_s(self) -> float:
        """Incident photons/cm^2/s (before reflection)."""
        energy_J = H_J_S * C_M_S / (self.wavelength_nm * 1e-9)
        return self.irradiance_W_m2 / energy_J * 1e-4

    def generation_cm3_s(self, depth_um):
        """Evaluate at non-negative depths inside the absorbing material."""
        depth = np.asarray(depth_um, dtype=float)
        if np.any(~np.isfinite(depth)) or np.any(depth < 0):
            raise ValueError("depth_um must be finite and non-negative")
        return (self.quantum_yield * (1 - self.reflectance) * self.photon_flux_cm2_s
                * self.absorption_cm_inv * np.exp(-self.absorption_cm_inv * depth * 1e-4))

    def absorbed_pairs_cm2_s(self, thickness_um: float) -> float:
        """Analytical depth integral of G, for photon-budget validation."""
        if not np.isfinite(thickness_um) or thickness_um < 0:
            raise ValueError("thickness_um must be finite and non-negative")
        return float(self.quantum_yield * (1 - self.reflectance) * self.photon_flux_cm2_s
                     * -np.expm1(-self.absorption_cm_inv * thickness_um * 1e-4))

    def apply(self, meshfield: MeshField, *, surface_y_um: float,
              material: Material = Material.SI) -> None:
        """Replace the mesh's prescribed generation field; illumination travels -y.

        ``surface_y_um`` is the flat entrance plane in the absorber, not the
        top of an overlying optical stack. Other materials get zero generation.
        Shared interface nodes belong to both materials; DeviceSolver ignores
        generation in insulators. Multiple absorbing layers/oblique incidence
        need their own field calculation, not repeated calls to this method.
        No automatic shadowing or transmission through overlayers is computed.
        """
        if not np.isfinite(surface_y_um):
            raise ValueError("surface_y_um must be finite")
        ids = meshfield.get_cells_for_material(material)
        if len(ids) == 0:
            raise ValueError(f"No cells for material {material.name}")
        if not np.all(np.asarray(meshfield.grid.celltypes) == 5):
            raise NotImplementedError("Optical mesh assignment supports 2D triangles only")
        nodes = np.unique(meshfield.grid.cells.reshape(-1, 4)[ids, 1:])
        depths = surface_y_um - meshfield.points[nodes, 1]
        if np.min(depths) < -1e-9:
            raise ValueError("Absorbing material extends above surface_y_um")
        generation = np.zeros(meshfield.n_points)
        generation[nodes] = self.generation_cm3_s(np.maximum(depths, 0))
        meshfield.grid.point_data[GENERATION_FIELD] = generation
        meshfield.metadata["optical_generation"] = {
            "model": "single_pass_beer_lambert", **asdict(self),
            "surface_y_um": surface_y_um, "material": material.name,
            "direction": "-y", "generation_units": "pairs/cm^3/s",
        }


def current_from_2d(current_A_per_cm, *, depth_um: float):
    """Scale a translationally invariant 2D terminal current to physical A.

    The in-plane width has already been integrated by DEVSIM. Multiply only
    by the OUT-OF-PLANE depth in cm. This assumes no edge effects in that
    direction; it does not convert arbitrary 2D geometry into a 3D device.
    """
    if not np.isfinite(depth_um) or depth_um <= 0:
        raise ValueError("depth_um must be finite and positive")
    current = np.asarray(current_A_per_cm, dtype=float)
    if np.any(~np.isfinite(current)):
        raise ValueError("current_A_per_cm must be finite")
    return current * depth_um * 1e-4
