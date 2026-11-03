"""Photon budgets, dimensional scaling, and real DD conservation regressions."""
import numpy as np
import pytest

from opentcad.device.optical import BeerLambert, GENERATION_FIELD, current_from_2d
from opentcad.device.solver import DeviceSolver, Q_C
from opentcad.geometry.formats import Material
from opentcad.geometry.structure import Structure
from opentcad.materials.database import load_material


def diode(mesh=0.08, doping=1e17):
    return (Structure(width_um=1.0, name="illuminated_diode")
            .add_substrate("p", 0.5, Material.SI, doping_Na=doping)
            .add_layer("n", 0.5, Material.SI, doping_Nd=doping)
            .add_contact("anode", 0, 1, "p", surface="bottom")
            .add_contact("cathode", 0, 1, "n", surface="top")
            .to_meshfield(mesh_size_um=mesh))


def test_absorbed_photon_budget():
    light = BeerLambert(660, 1000, 3000, reflectance=0.3)
    depth = np.linspace(0, 10, 10001)
    integrated = np.trapezoid(light.generation_cm3_s(depth), depth * 1e-4)
    assert integrated == pytest.approx(light.absorbed_pairs_cm2_s(10), rel=1e-7)
    assert light.photon_flux_cm2_s == pytest.approx(3.322516934e17, rel=1e-9)
    assert light.absorbed_pairs_cm2_s(1e5) == pytest.approx(
        0.7 * light.photon_flux_cm2_s)
    assert light.absorbed_pairs_cm2_s(0) == 0
    assert BeerLambert(660, 0, 3000).generation_cm3_s(1) == 0
    assert BeerLambert(660, 1000, 0).absorbed_pairs_cm2_s(10) == 0
    assert BeerLambert(660, 1000, 3000, reflectance=1).generation_cm3_s(0) == 0


@pytest.mark.parametrize("kwargs", [dict(wavelength_nm=0), dict(irradiance_W_m2=-1),
                                   dict(absorption_cm_inv=np.nan), dict(reflectance=1.1),
                                   dict(quantum_yield=-0.1)])
def test_invalid_optics(kwargs):
    params = dict(wavelength_nm=660, irradiance_W_m2=1000, absorption_cm_inv=3000)
    with pytest.raises(ValueError):
        BeerLambert(**(params | kwargs))


def test_physical_current_scaling():
    assert current_from_2d([-1e-4, 2e-4], depth_um=20) == pytest.approx([-2e-7, 4e-7])
    with pytest.raises(ValueError):
        current_from_2d(1, depth_um=-1)


@pytest.mark.requires_devsim
def test_illuminated_dd_collects_pairs_and_conserves_terminal_current():
    # Generation localized well inside a depleted, high-lifetime diode:
    # collection approaches unity away from the absorbing ohmic contacts.
    # The Gaussian volume integral provides an independent analytical limit.
    mf = diode(mesh=0.04, doping=1e14)
    sigma_um, peak = 0.08, 1e18
    mf.grid.point_data[GENERATION_FIELD] = peak * np.exp(
        -((mf.points[:, 1] - 0.5) / sigma_um)**2)
    si = load_material("Si")
    si.recombination.tau_n_s = si.recombination.tau_p_s = 1e-3
    solver = DeviceSolver(mf, {"Silicon": si})
    _, current = solver.iv_sweep("anode", "cathode", 0, 0, 0.05)
    expected = -Q_C * peak * sigma_um * np.sqrt(np.pi) * 1e-8
    assert current[0] == pytest.approx(expected, rel=0.03)
    a = solver.contact_current_A_per_cm("anode")
    c = solver.contact_current_A_per_cm("cathode")
    assert abs(a + c) / abs(a) < 1e-5
    assert a < 0 < c


@pytest.mark.requires_devsim
def test_dark_recombination_conserves_current_with_short_lifetime():
    # The old shared-sign URec residual fails this test; near-equilibrium
    # and Shockley-slope-only checks did not expose the defect.
    si = load_material("Si")
    si.recombination.tau_n_s = si.recombination.tau_p_s = 1e-9
    solver = DeviceSolver(diode(), {"Silicon": si})
    solver.iv_sweep("anode", "cathode", 0, 0.5, 0.05)
    a = solver.contact_current_A_per_cm("anode")
    c = solver.contact_current_A_per_cm("cathode")
    assert a > 0
    assert abs(a + c) / abs(a) < 1e-4


def test_mesh_assignment_and_invalid_field():
    mf = diode()
    light = BeerLambert(660, 1000, 3000)
    light.apply(mf, surface_y_um=1.0)
    assert mf.grid.point_data[GENERATION_FIELD] == pytest.approx(
        light.generation_cm3_s(1 - mf.points[:, 1]))
    with pytest.raises(ValueError, match="above"):
        light.apply(mf, surface_y_um=0.9)
    mf.grid.point_data[GENERATION_FIELD][0] = -1
    with pytest.raises(ValueError, match="non-negative"):
        DeviceSolver(mf, {"Silicon": load_material("Si")}).initialize()
