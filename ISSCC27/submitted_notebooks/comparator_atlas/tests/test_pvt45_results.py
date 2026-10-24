from itertools import product

import pandas as pd
import numpy as np
import pytest

from presentation.pvt45_results import (
    CORNERS, INPUTS_MV, MODES, TEMPERATURES, VOLTAGES, case_table,
    comparison_table, coverage_table, load_results, paired_points, review_examples, summary, timing_figure,
    tradeoff_figure, validate_grid,
)


def fixture():
    rows = []
    for number, (corner, voltage, temperature, input_mv, mode) in enumerate(
        product(CORNERS, VOLTAGES, TEMPERATURES, INPUTS_MV, MODES)
    ):
        positive = input_mv > 0
        row = {
            "corner": corner, "vdd_v": voltage, "temperature_c": temperature,
            "differential_mv": input_mv, "mode": mode, "pair_skew": 0, "trim_code": 0,
            "common_mode_ratio": 0.5, "output_load_ff_each": 5, "finest_step_ps": 5.0,
            "run_identity": f"synthetic-contract-only-{number}", "execution_status": "success",
            "numerically_qualified": True, "reset_ok": True,
            "core_energy_fj": 200.0 if mode == "schematic" else 300.0,
        }
        for deadline in (1, 2):
            row.update({
                f"outcome_{deadline}ns": "correct", f"decision_{deadline}ns": 1 if positive else -1,
                f"decision_time_ns_{deadline}ns": 0.3 if mode == "schematic" else 0.6,
                f"qp_at_deadline_v_{deadline}ns": voltage if positive else 0.0,
                f"qn_at_deadline_v_{deadline}ns": 0.0 if positive else voltage,
            })
        rows.append(row)
    return pd.DataFrame(rows)


def test_complete_synthetic_grid_keeps_exact_denominators():
    result = summary(fixture())
    assert result["rc_primary_correct"] == 180
    assert result["data_grid_executed"]
    assert result["all_point_histories_numerically_confirmed"]
    assert result["matched_statistics"]["points"] == 180
    assert result["matched_statistics"]["mean_per_point_energy_overhead_percent"] == 50
    assert not result["execution_window_conformance_assessed_by_this_table"]
    conditions = case_table(fixture())
    assert len(conditions) == 45
    assert conditions.sampled_inputs.eq(4).all()
    assert conditions.rc_correct_2ns.eq(4).all()
    assert len(paired_points(fixture())) == 180


def test_actual_complete_reference_matches_the_repaired_circuit_and_audit():
    data = load_results()
    assert data["summary"]["rc_primary_correct"] == 180
    result = comparison_table(data["frame"]).set_index("implementation")
    assert result.loc["Schematic", "correct_at_1ns"] == 180
    assert result.loc["Extracted RC", "correct_at_1ns"] == 156
    assert result.loc["Extracted RC", "correct_at_2ns"] == 180
    assert result.loc["Extracted RC", "worst_delay_ns_at_2ns"] == pytest.approx(1.835032467243)
    assert data["audit"]["original_two_window_time_conformance"] is False


def test_ten_representative_raw_traces_remeasure_to_the_same_full_grid_values():
    data = load_results()
    observed = review_examples(data)
    assert len(observed) == 20
    assert observed.attempt_id.nunique() == 10
    assert observed[observed.deadline_ns == 2].outcome.eq("correct").all()
    fs_rc = observed[(observed["mode"] == "rc") & observed.condition.str.startswith("FS")]
    assert fs_rc[fs_rc.deadline_ns == 1].outcome.eq("unresolved").all()
    assert fs_rc[fs_rc.deadline_ns == 2].decision_time_ns.max() == pytest.approx(1.835032467243)


def test_tradeoff_figure_contains_every_matched_point_in_both_panels():
    import matplotlib.pyplot as plt

    data = load_results()
    pairs = paired_points(data["frame"])
    fig = tradeoff_figure(data["frame"])
    try:
        for axis, fields in zip(fig.axes, (
            ("decision_time_ns_2ns_schematic", "decision_time_ns_2ns_rc"),
            ("core_energy_fj_schematic", "core_energy_fj_rc"),
        )):
            assert len(axis.collections) == 5
            assert sum(len(collection.get_offsets()) for collection in axis.collections) == 180
            for corner, collection in zip(CORNERS, axis.collections):
                expected = pairs.loc[pairs.corner == corner, list(fields)].to_numpy()
                np.testing.assert_allclose(collection.get_offsets(), expected, rtol=0, atol=1e-12)
                assert expected[:, 0].min() >= axis.get_xlim()[0]
                assert expected[:, 0].max() <= axis.get_xlim()[1]
                assert expected[:, 1].min() >= axis.get_ylim()[0]
                assert expected[:, 1].max() <= axis.get_ylim()[1]
    finally:
        plt.close(fig)


def test_final_size_figures_remain_readable_with_the_bundled_free_font(monkeypatch):
    import matplotlib.pyplot as plt
    import presentation.figure_style as style

    monkeypatch.setattr(style, "available_font", lambda: "DejaVu Sans")
    data = load_results()
    for factory, height in ((timing_figure, 1.95), (tradeoff_figure, 2.90)):
        figure = factory(data["frame"])
        try:
            style.review_artists(figure, style.FigureProfile(height_in=height))
        finally:
            plt.close(figure)


def test_a_complete_heatmap_cannot_silently_ignore_a_numerically_unknown_point():
    data = fixture()
    data.loc[0, "numerically_qualified"] = False
    data.loc[0, "finest_step_ps"] = 10
    with pytest.raises(ValueError, match="every declared observation"):
        case_table(data)


def test_missing_or_duplicate_physical_points_cannot_make_an_all_pass_grid():
    data = fixture()
    with pytest.raises(ValueError, match="exactly 180"):
        validate_grid(data.iloc[1:])
    data.iloc[1] = data.iloc[0]
    with pytest.raises(ValueError, match="exactly 180"):
        validate_grid(data)


def test_single_coarse_observation_is_unknown_even_if_raw_polarity_is_correct():
    data = fixture()
    index = data.index[data["mode"] == "rc"][0]
    data.loc[index, "numerically_qualified"] = False
    data.loc[index, "finest_step_ps"] = 10
    result = summary(data)
    assert result["rc_primary_correct"] == 179
    assert result["rc_primary_numerical_unknown"] == 1
    assert not result["all_180_rc_points_correct_at_2ns"]


def test_unexecuted_point_must_not_have_fabricated_energy_or_qualification():
    data = fixture()
    index = data.index[data["mode"] == "rc"][0]
    data.loc[index, "execution_status"] = "not_run"
    data.loc[index, "numerically_qualified"] = False
    with pytest.raises(ValueError, match="invented"):
        validate_grid(data)


def test_two_ns_pass_does_not_turn_a_one_ns_unresolved_point_into_correct():
    data = fixture()
    index = data.index[data["mode"] == "rc"][0]
    data.loc[index, "outcome_1ns"] = "unresolved"
    data.loc[index, "decision_1ns"] = 0
    data.loc[index, "decision_time_ns_1ns"] = float("nan")
    data.loc[index, "qp_at_deadline_v_1ns"] = data.loc[index, "vdd_v"] * 0.6
    data.loc[index, "qn_at_deadline_v_1ns"] = data.loc[index, "vdd_v"] * 0.6
    data.loc[index, "decision_time_ns_2ns"] = 1.4
    table = coverage_table(data).set_index(["mode", "deadline_ns"])
    assert table.loc[("rc", 1), "confirmed_unresolved"] == 1
    assert table.loc[("rc", 1), "confirmed_correct"] == 179
    assert table.loc[("rc", 2), "confirmed_correct"] == 180


def test_wrong_direction_and_late_decision_are_separate():
    data = fixture()
    index = data.index[data["mode"] == "rc"][0]
    for deadline in (1, 2):
        data.loc[index, f"qp_at_deadline_v_{deadline}ns"] = data.loc[index, "vdd_v"]
        data.loc[index, f"qn_at_deadline_v_{deadline}ns"] = 0
        data.loc[index, f"decision_{deadline}ns"] = 1
        data.loc[index, f"outcome_{deadline}ns"] = "wrong"
    table = coverage_table(data).set_index(["mode", "deadline_ns"])
    assert table.loc[("rc", 2), "confirmed_wrong"] == 1
    assert table.loc[("rc", 2), "confirmed_unresolved"] == 0


@pytest.mark.parametrize("field,value", [
    ("trim_code", 1), ("output_load_ff_each", 4), ("common_mode_ratio", 0.45),
    ("core_energy_fj", float("nan")), ("reset_ok", False),
    ("finest_step_ps", 10), ("decision_2ns", 0), ("outcome_2ns", "wrong"),
])
def test_changed_experiment_or_inconsistent_measurements_are_rejected(field, value):
    data = fixture()
    data.loc[0, field] = value
    with pytest.raises(ValueError):
        validate_grid(data)
