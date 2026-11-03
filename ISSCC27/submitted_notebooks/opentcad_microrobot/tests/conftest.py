"""Shared pytest fixtures for OpenTCAD tests."""
import numpy as np
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "requires_devsim: requires devsim installed")
    config.addinivalue_line("markers", "requires_viennaps: requires ViennaPS installed")
    config.addinivalue_line("markers", "integration: full pipeline integration tests")


@pytest.fixture(autouse=True)
def _cleanup_devsim_devices():
    """DEVSIM keeps a global device/mesh table; ds.solve() acts on every
    live device. Drop them between tests so stale Poisson-only devices
    from earlier tests don't get pulled into a later DD solve."""
    yield
    try:
        import devsim as ds
        for d in list(ds.get_device_list()):
            ds.delete_device(device=d)
    except ImportError:
        pass

@pytest.fixture
def simple_si_meshfield():
    """Minimal 2D Si pn-junction MeshField with anode/cathode contacts.

    Triangle mesh built via the Structure DSL — compatible with the 2D
    DEVSIM drift-diffusion solver. 1 um square, junction at y=0.5 um.
    """
    from opentcad.geometry.structure import Structure
    from opentcad.geometry.formats import Material
    s = (Structure(width_um=1.0, name="pn_junction")
         .add_substrate("p_body", 0.5, Material.SI, doping_Na=1e17)
         .add_layer("n_well", 0.5, Material.SI, doping_Nd=1e17)
         .add_contact("anode", 0.0, 1.0, "p_body", surface="bottom")
         .add_contact("cathode", 0.0, 1.0, "n_well", surface="top"))
    return s.to_meshfield(mesh_size_um=0.1)
