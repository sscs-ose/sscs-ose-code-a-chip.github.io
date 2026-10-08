from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from comparator_atlas.spice import (
    EVALUATION_START_S, Point, SimulationError, Trace, measure, rail_decision,
)


def synthetic_trace(*, differential=0.01, delay_ns=0.5, wrong=False, glitch=False):
    t = np.linspace(0, 30e-9, 3001)
    vdd = 1.8
    qp = np.full_like(t, vdd)
    qn = np.full_like(t, vdd)
    discharged = qp if wrong else qn
    discharged[t >= EVALUATION_START_S + delay_ns * 1e-9] = 0
    if glitch:
        discharged[(t >= EVALUATION_START_S + 0.1e-9) & (t < EVALUATION_START_S + 0.2e-9)] = 0
    values = np.column_stack((t, np.zeros_like(t), qp, qn, np.full_like(t, vdd),
                              np.full_like(t, vdd), np.full_like(t, -1e-6)))
    return Trace(Point(differential_v=differential), values, "synthetic", Path("."))


def test_requires_complementary_rails():
    assert rail_decision(1.5, 0.2, 1.8) == 1
    assert rail_decision(0.2, 1.5, 1.8) == -1
    assert rail_decision(1.8, 1.0, 1.8) == 0
    assert rail_decision(0.9, 0.1, 1.8) == 0


def test_energy_integrates_full_cycle_with_correct_sign():
    result = measure(synthetic_trace(), 1.0)
    assert result.outcome == "correct"
    assert result.core_energy_fj == pytest.approx(18)
    assert result.decision_time_ns == pytest.approx(0.505, abs=0.006)


def test_late_decision_does_not_pass_an_earlier_deadline():
    trace = synthetic_trace(delay_ns=0.8)
    assert measure(trace, 0.5).outcome == "unresolved"
    assert measure(trace, 1.0).outcome == "correct"


def test_wrong_and_zero_input_are_not_correct():
    assert measure(synthetic_trace(wrong=True), 1.0).outcome == "wrong"
    assert measure(synthetic_trace(differential=0), 1.0).outcome == "reference"


def test_glitch_is_not_reported_as_fast_decision():
    assert measure(synthetic_trace(glitch=True), 1.0).decision_time_ns > 0.49


def test_corrupt_or_truncated_waveforms_are_not_circuit_timeouts():
    trace = synthetic_trace()
    with pytest.raises(SimulationError):
        measure(replace(trace, values=trace.values[:-20]), 1)
    damaged = trace.values.copy()
    damaged[100, 2] = np.nan
    with pytest.raises(SimulationError):
        measure(replace(trace, values=damaged), 1)


def test_reset_failure_is_explicit():
    trace = synthetic_trace()
    damaged = trace.values.copy()
    damaged[:, 4] = 0
    with pytest.raises(SimulationError, match="reset"):
        measure(replace(trace, values=damaged), 1)


@pytest.mark.parametrize("fields", [
    {"corner": "unknown"}, {"vdd_v": 2.5}, {"vdd_v": float("nan")},
    {"trim_code": 8}, {"trim_code": 1.5}, {"trim_code": True},
    {"pair_skew": 0.3}, {"max_step_ps": 0}, {"load_ff": -1},
])
def test_point_validation(fields):
    with pytest.raises(ValueError):
        Point(**fields)
