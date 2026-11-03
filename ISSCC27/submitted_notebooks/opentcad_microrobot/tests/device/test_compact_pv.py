"""Independent limits and parameter recovery for the reduced terminal model."""
import numpy as np
import pytest
import shutil
import subprocess

from opentcad.device.compact import SingleDiodePV, fit_single_diode


def test_limits_scaling_and_power_stationarity():
    cell = SingleDiodePV(1e-16, 1.2, 150e-9)
    assert cell.current_A(0, 1000) == pytest.approx(150e-9)
    assert cell.current_A(0, 0) == 0
    assert cell.current_A(cell.open_circuit_V()) == pytest.approx(0, abs=1e-21)
    pair = SingleDiodePV(1e-16, 1.2, 150e-9, series_cells=2)
    assert pair.open_circuit_V() == pytest.approx(2 * cell.open_circuit_V())
    assert cell.scaled_current(3).open_circuit_V() == pytest.approx(cell.open_circuit_V())
    v, i, p = cell.maximum_power_point()
    assert 0 < v < cell.open_circuit_V() and 0 < i < 150e-9
    assert p > (v + 1e-4) * cell.current_A(v + 1e-4)
    assert p > (v - 1e-4) * cell.current_A(v - 1e-4)
    assert cell.maximum_power_point(0) == (0, 0, 0)


def test_recovers_known_parameters_and_predicts_withheld_light_level():
    expected = SingleDiodePV(2e-16, 1.35, 130e-9, series_cells=2)
    voltages = np.tile(np.linspace(-0.2, 1.4, 81), 2)
    light = np.repeat([0, 1000], 81)
    current = expected.current_A(voltages, light)
    actual, info = fit_single_diode(voltages, current, light, series_cells=2,
                                     uncertainty_A=1e-9)
    assert actual.saturation_A == pytest.approx(expected.saturation_A, rel=1e-5)
    assert actual.ideality == pytest.approx(expected.ideality, rel=1e-6)
    assert actual.photocurrent_A == pytest.approx(expected.photocurrent_A, rel=1e-6)
    assert info["rms_current_error_A"] < 1e-15
    v = np.linspace(0, 1.3, 31)
    assert actual.current_A(v, 500) == pytest.approx(expected.current_A(v, 500), abs=1e-15)


def test_rejects_unsupported_input_and_unsafe_spice_name():
    with pytest.raises(ValueError):
        SingleDiodePV(0, 1, 1e-9)
    with pytest.raises(ValueError):
        SingleDiodePV(1e-18, 1, 1e-9, series_cells=1.5)
    with pytest.raises(ValueError):
        SingleDiodePV(1e-18, 1, 1e-9).spice_subcircuit("bad\n.end")
    with pytest.raises(ValueError):
        fit_single_diode(np.arange(10), np.ones(10), np.zeros(10))


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="optional ngspice executable")
def test_spice_export_matches_numerical_current(tmp_path):
    pv = SingleDiodePV(1e-16, 1.2, 150e-9, series_cells=2)
    deck = ("* Independent SPICE round trip at the fitted temperature\n"
            + pv.spice_subcircuit("roundtrip")
            + "Vtest p 0 0\nXpv p 0 roundtrip illumination=500 area_scale=2\n"
            + ".temp 26.85\n.options gmin=1e-18\n.control\n"
            + "set wr_vecnames\nset wr_singlescale\ndc Vtest 0 1.3 0.05\n"
            + "wrdata result.dat v(p) i(Vtest)\nquit\n.endc\n.end\n")
    (tmp_path / "test.spice").write_text(deck)
    process = subprocess.run([shutil.which("ngspice"), "-n", "-b", "test.spice"],
                             cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stdout + process.stderr
    values = np.loadtxt(tmp_path / "result.dat", skiprows=1)
    # Allow 100 ppm for SPICE's physical constants and printed precision;
    # the absolute discrepancy here is only a few pA.
    assert values[:, 2] == pytest.approx(2 * pv.current_A(values[:, 1], 500),
                                        rel=1e-4, abs=1e-12)
