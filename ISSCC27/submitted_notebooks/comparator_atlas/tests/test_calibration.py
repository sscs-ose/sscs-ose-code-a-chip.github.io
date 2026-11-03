import pytest

from comparator_atlas.experiments import (
    CalibrationError, cases, select_trim, switching_boundary,
)


def analytic_probe(offset=0.009, step=0.003, deadband=0):
    def probe(differential, code):
        effective = differential - (offset - code * step)
        if abs(effective) <= deadband:
            return 0
        return 1 if effective > 0 else -1
    return probe


def test_boundary_brackets_known_offset():
    result = switching_boundary(analytic_probe(), 0)
    assert result.negative_v < 0.009 < result.positive_v
    assert result.positive_v - result.negative_v <= 0.0002


def test_unresolved_deadband_is_not_zero_offset():
    result = switching_boundary(analytic_probe(offset=0, deadband=0.002), 0)
    assert result.negative_v <= -0.002
    assert result.positive_v >= 0.002
    assert result.halfwidth_mv >= 2


@pytest.mark.parametrize("sign", [-1, 1])
def test_calibration_accepts_either_trim_direction(sign):
    result = select_trim(analytic_probe(step=sign * 0.003))
    assert result["code"] == sign * 3
    assert result["selected"]["worst_absolute_mv"] <= 0.2


def test_zero_stress_prefers_zero_code():
    result = select_trim(analytic_probe(offset=0))
    assert result["code"] == 0


def test_saturation_is_explicit_not_success_shaped():
    result = select_trim(analytic_probe(offset=0.05))
    assert result["status"] == "no_zero_crossing_exhaustive_search"
    assert result["selected"]["worst_absolute_mv"] > 20


def test_unbracketable_circuit_is_an_error():
    with pytest.raises(CalibrationError):
        switching_boundary(lambda differential, code: 1, 0)


def test_quick_and_full_scope_are_explicit():
    quick = cases("quick")
    full = cases("full")
    assert len(quick) == 11
    assert len(full) == 49
    assert len(set(quick)) == len(quick)
    assert len(set(full)) == len(full)
    assert {point.corner for point in quick} == {"tt", "ss", "ff", "sf", "fs"}
