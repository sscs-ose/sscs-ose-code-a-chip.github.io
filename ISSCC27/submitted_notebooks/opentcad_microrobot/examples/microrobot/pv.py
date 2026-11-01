"""Conceptual PV experiment and bounded tabular coupling to the system model."""
from dataclasses import dataclass

import numpy as np

from opentcad.device.optical import BeerLambert, current_from_2d
from opentcad.device.solver import DeviceSolver, Q_C
from opentcad.geometry.formats import Material
from opentcad.geometry.structure import Structure
from opentcad.materials.database import load_material


class _AuditedPVSolver(DeviceSolver):
    """Observe both terminal currents during the unchanged core IV sweep."""

    def iv_sweep(self, *args, **kwargs):
        self.terminal_samples_A_per_cm = []
        self._record_pv_terminals = True
        try:
            return super().iv_sweep(*args, **kwargs)
        finally:
            self._record_pv_terminals = False

    def _get_contact_current(self, contact):
        current = super()._get_contact_current(contact)
        if getattr(self, "_record_pv_terminals", False):
            other = "n" if contact == "p" else "p"
            opposite = super()._get_contact_current(other)
            self.terminal_samples_A_per_cm.append((current, opposite))
        return current


def characterize(mesh_um=0.08, lifetime_s=1e-5, irradiance_W_m2=1000.0, *, reflectance=0.3):
    """Return physical IV for a 1 um × 1 um illuminated footprint at 300 K.

    Analytic abrupt doping, 3 um Si, 0.3 um emitter, ideal transparent ohmic
    top/back contacts, insulating side boundaries. This is NOT XT018 or SKY130.
    No sidewall/interface recombination, parasitic Rs, optical metal shading,
    interference or temperature calibration. Photon loss at ohmic contacts is
    retained. The mesh spacing and voltage step are recorded in the result.
    """
    import devsim
    mf = (Structure(width_um=1, name="concept_pv")
          .add_substrate("p", 2.7, Material.SI, doping_Na=1e16)
          .add_layer("n", 0.3, Material.SI, doping_Nd=1e18)
          .add_contact("p", 0, 1, "p", surface="bottom")
          .add_contact("n", 0, 1, "n", surface="top")
          .to_meshfield(mesh_size_um=mesh_um))
    light = BeerLambert(660, irradiance_W_m2, 3000, reflectance=reflectance)
    light.apply(mf, surface_y_um=3)
    si = load_material("Si")
    si.recombination.tau_n_s = si.recombination.tau_p_s = lifetime_s
    solver = _AuditedPVSolver(mf, {"Silicon": si})
    try:
        v, current = solver.iv_sweep("p", "n", 0, 0.70, 0.025)
        i = -current_from_2d(current, depth_um=1)
        a = solver.contact_current_A_per_cm("p")
        c = solver.contact_current_A_per_cm("n")
        imbalance = abs(a + c) / max(abs(a), abs(c), 1e-30)
    finally:
        devsim.delete_device(device=solver._device_name)
    v = np.asarray(v)
    terminals = current_from_2d(solver.terminal_samples_A_per_cm, depth_um=1)
    if terminals.shape != (len(v), 2):
        raise RuntimeError("PV terminal audit must contain exactly one sample per voltage")
    absolute_balance = np.abs(np.sum(terminals, axis=1))
    relative_balance = absolute_balance / np.maximum(np.max(np.abs(terminals), axis=1), 1e-30)
    voc = float(np.interp(0, -i, v)) if i[0] > 0 else 0.0
    power = v * i
    photon_limit = Q_C * light.absorbed_pairs_cm2_s(3) * 1e-8
    return dict(mesh_um=mesh_um, nodes=mf.n_points, lifetime_s=lifetime_s,
                reflectance=reflectance,
                irradiance_W_m2=irradiance_W_m2, voltage_V=v.tolist(),
                delivered_A_per_um2=i.tolist(), isc_A_per_um2=float(i[0]), voc_V=voc,
                pmax_W_per_um2=float(max(0, np.max(power))),
                responsivity_A_W=float(i[0] / (irradiance_W_m2 * 1e-12))
                if irradiance_W_m2 else None,
                absorbed_photon_limit_A_per_um2=photon_limit,
                terminal_entering_A_per_um2=terminals.tolist(),
                contact_imbalance_absolute_A_per_um2=absolute_balance.tolist(),
                contact_imbalance_relative_by_voltage=relative_balance.tolist(),
                contact_imbalance_relative=imbalance)


@dataclass
class PVTable:
    """TCAD table at one illumination; dark/light superposition is an approximation.

    Scale the dark and photocurrent tables by physical area in um². Irradiance
    dependence is linear photocurrent superposition, not a new DD solution.
    The run compares at least one additional illumination against DD. No
    voltage extrapolation is allowed: an out-of-range state fails loudly.
    """
    voltage_V: np.ndarray
    dark_delivered_A_um2: np.ndarray
    photocurrent_A_um2: np.ndarray
    reference_irradiance_W_m2: float

    @classmethod
    def from_results(cls, dark, light):
        v = np.asarray(dark["voltage_V"])
        if not np.array_equal(v, light["voltage_V"]):
            raise ValueError("Dark/light voltage grids must match")
        d = np.asarray(dark["delivered_A_per_um2"])
        return cls(v, d, np.asarray(light["delivered_A_per_um2"]) - d,
                   light["irradiance_W_m2"])

    def current(self, voltage, irradiance, area_um2):
        if voltage < -1e-9 or voltage > self.voltage_V[-1] + 1e-9:
            raise ValueError(f"PV voltage {voltage:g} V outside characterized interval")
        if irradiance < 0 or area_um2 <= 0:
            raise ValueError("Non-negative irradiance and positive area required")
        values = self.dark_delivered_A_um2 + self.photocurrent_A_um2 * (
            irradiance / self.reference_irradiance_W_m2)
        return float(np.interp(voltage, self.voltage_V, values) * area_um2)
