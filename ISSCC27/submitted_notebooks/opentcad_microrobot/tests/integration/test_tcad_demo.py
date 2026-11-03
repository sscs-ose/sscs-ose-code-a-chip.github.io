"""Input provenance, compatibility and serialization without native reruns."""

import json
import numpy as np
from examples.microrobot import tcad_demo as demo
from examples.microrobot.system import Parameters


def test_real_DD_table_and_schematic_clock_envelope():
    table, clock = demo.inputs()
    assert len(table.voltage_V) == 29
    assert table.reference_irradiance_W_m2 == 1000
    assert clock.voltage.tolist() == [1.6, 1.7, 1.8, 1.9]
    assert 8000 < clock.clock(1.7) < 8300


def test_new_design_and_original_defaults_are_explicit():
    original = Parameters()
    p = demo.parameters()
    assert original.actuator_series_cells_per_half == 1
    assert original.actuator_cell_area_um2 == 500
    assert original.logic_cell_area_um2 == 150
    assert p.actuator_series_cells_per_half == 2 and p.logic_series_cells == 4
    assert p.logic_cell_area_um2 == p.actuator_cell_area_um2 == 1080
    assert p.logic_storage_F == 50e-12 and p.actuator_storage_each_F == 200e-12


def test_numpy_scalar_json_and_completion_failure_detection():
    value = json.loads(
        json.dumps(
            {"ok": np.bool_(True), "rows": np.int64(3), "value": np.float64(0.5)},
            default=demo.json_value,
        )
    )
    assert value == {"ok": True, "rows": 3, "value": 0.5}
    assert demo.completion({"time_s": np.array([0.0, 1.0])}, 1.0)["complete"]
    assert not demo.completion({"time_s": np.array([0.0, 0.9])}, 1.0)["complete"]
