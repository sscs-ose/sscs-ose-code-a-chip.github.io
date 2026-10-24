from dataclasses import replace

import pytest

from comparator_atlas.designs import DESIGNS, circuit_text, controls, get_design
from comparator_atlas.experiments import CalibrationError, select_trim, switching_boundaries
from comparator_atlas.spice import Point


def test_original_transistor_count_and_area_proxy():
    baseline = get_design("baseline")
    assert baseline.transistor_count == 23
    assert baseline.gate_area_um2 == pytest.approx(10.83)
    assert baseline.max_code == 7


@pytest.mark.parametrize("name", list(DESIGNS))
def test_generated_family_contains_the_declared_physical_devices(name):
    design = get_design(name)
    netlist = circuit_text(design)
    instances = [line for line in netlist.splitlines() if line.startswith("X")]
    assert len(instances) == design.transistor_count
    assert len(controls(design)) == 2 * design.trim_bits
    assert "sky130_fd_pr__" + design.input_device in netlist


def test_trim_domain_depends_on_the_actual_circuit():
    Point(design_name="lvt_wide_5b", trim_code=-31)
    with pytest.raises(ValueError):
        Point(trim_code=-31)
    with pytest.raises(ValueError):
        Point(design_name="not-a-design")


def test_history_and_source_loading_are_bounded():
    Point(source_resistance_ohm=1000, sample_cap_ff=20, previous_differential_v=0.03)
    for fields in (
        {"source_resistance_ohm": -1}, {"sample_cap_ff": float("nan")},
        {"previous_differential_v": 10}, {"previous_differential_v": float("inf")},
    ):
        with pytest.raises(ValueError):
            Point(**fields)


def test_batched_boundaries_preserve_unresolved_intervals():
    def batch(requests):
        replies = []
        for value, code in requests:
            center = code * 0.003
            replies.append(-1 if value < center - 0.001 else 1 if value > center + 0.001 else 0)
        return replies
    results = switching_boundaries(batch, [-2, 0, 2])
    for code, result in results.items():
        assert result.negative_v <= code * 0.003 - 0.001
        assert result.positive_v >= code * 0.003 + 0.001


def test_batch_protocol_does_not_accept_missing_responses():
    with pytest.raises(CalibrationError, match="missing"):
        switching_boundaries(lambda requests: [], [0])


def test_five_bit_calibration_can_choose_outside_the_old_range():
    def probe(value, code):
        effective = value - (0.018 - code * 0.001)
        return -1 if effective < -1e-10 else 1 if effective > 1e-10 else 0
    result = select_trim(probe, max_code=31)
    assert result["code"] == 18
