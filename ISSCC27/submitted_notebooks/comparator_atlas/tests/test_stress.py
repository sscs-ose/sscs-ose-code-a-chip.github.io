from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from comparator_atlas.spice import Point, SimulationError, Trace
from comparator_atlas.stress import STRESS_NAMES, apply_refinements, input_disturbance, stressed_point


def test_stresses_do_not_silently_retune_the_circuit():
    base = Point(trim_code=-2, design_name="lvt_fine_4b")
    for name in STRESS_NAMES:
        stressed = stressed_point(base, name, -0.001)
        assert stressed.trim_code == -2
        assert stressed.design_name == base.design_name
        assert stressed.differential_v == -0.001


def test_history_is_opposite_to_the_requested_decision():
    assert stressed_point(Point(), "opposite_input_history", 0.001).previous_differential_v < 0
    assert stressed_point(Point(), "settling_10k_200f", -0.001).previous_differential_v > 0


def test_input_error_is_actual_pin_error_not_random_noise():
    t = np.linspace(20e-9, 30e-9, 1001)
    values = np.zeros((len(t), 9))
    values[:, 0] = t
    values[:, 7] = 0.905
    values[:, 8] = 0.895
    result = input_disturbance(Trace(Point(differential_v=0.001), values, "synthetic", Path(".")))
    assert result["max_differential_input_error_mv"] == pytest.approx(9)
    assert result["max_common_mode_input_error_mv"] == pytest.approx(0)


def test_no_invented_kickback_when_input_voltages_are_absent():
    values = np.zeros((20, 7))
    with pytest.raises(SimulationError, match="input-pin"):
        input_disturbance(Trace(Point(), values, "legacy", Path(".")))


def test_unknown_stress_is_rejected():
    with pytest.raises(ValueError):
        stressed_point(Point(), "not-a-profile", 0.001)


def refinement_fixture():
    row = {
        **asdict(Point(differential_v=-0.001)), "case_id": "case", "deadline_ns": 1.0,
        "run_id": "original", "outcome": "correct", "decision": -1,
        "decision_time_ns": 0.6, "core_energy_fj": 200.0,
        "reset_ok": True, "qp_at_deadline_v": 0.0, "qn_at_deadline_v": 1.8,
    }
    frame = pd.DataFrame([{**row, "policy": policy} for policy in ("local_boundary", "deadline_aware")])
    correction = {
        **row, "original_run_id": "original", "run_id": "fine", "max_step_ps": 0.625,
        "outcome": "wrong", "decision": 1, "qp_at_deadline_v": 1.8, "qn_at_deadline_v": 0.0,
    }
    return frame, pd.DataFrame([correction])


def test_refinement_propagates_worse_results_to_every_matching_policy():
    frame, updates = refinement_fixture()
    result = apply_refinements(frame, updates)
    assert len(result) == len(frame)
    assert (result.outcome == "wrong").all()
    assert (result.initial_run_id == "original").all()
    assert (result.run_id == "fine").all()
    assert result.numerically_refined.all()
    assert (frame.outcome == "correct").all()


def test_numerical_correction_cannot_retune_or_change_the_physical_stimulus():
    frame, updates = refinement_fixture()
    updates.loc[0, "trim_code"] = -2
    with pytest.raises(SimulationError, match="physical experiment"):
        apply_refinements(frame, updates)


def test_refinement_cannot_overwrite_a_point_twice_or_use_a_coarser_step():
    frame, updates = refinement_fixture()
    with pytest.raises(SimulationError, match="Duplicate"):
        apply_refinements(frame, pd.concat([updates, updates], ignore_index=True))
    updates.loc[0, "max_step_ps"] = 20
    with pytest.raises(SimulationError, match="finer"):
        apply_refinements(frame, updates)


def test_no_refinement_leaves_the_original_results_marked_as_unmodified():
    frame, _ = refinement_fixture()
    result = apply_refinements(frame, pd.DataFrame())
    assert (result.outcome == frame.outcome).all()
    assert not result.numerically_refined.any()
