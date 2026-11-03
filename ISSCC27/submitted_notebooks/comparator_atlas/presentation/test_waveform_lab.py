from copy import deepcopy

import pytest

from presentation.waveform_lab import DEADLINES, inspect_sample, load_lab, verify_observation


def test_declared_eight_examples_recompute_from_unchanged_full_waveforms():
    data = load_lab()
    assert data["sample_count"] == 8
    assert data["new_physical_simulations"] == 0
    assert tuple(data["deadlines_ns"]) == DEADLINES
    assert len({sample["id"] for sample in data["samples"]}) == 8
    assert sum(sample["source_kind"] == "schematic" for sample in data["samples"]) == 2
    assert sum(sample["source_kind"] == "layout_rc" for sample in data["samples"]) == 6


def test_calibration_example_is_the_same_electrical_point_except_for_trim():
    data = load_lab()
    before, wrong = inspect_sample(data, "schematic_untrimmed", 1)
    after, correct = inspect_sample(data, "schematic_calibrated", 1)
    fields = set(before["point"]) - {"trim_code"}
    assert all(before["point"][key] == after["point"][key] for key in fields)
    assert before["point"]["trim_code"] == 0 and after["point"]["trim_code"] == -2
    assert wrong["outcome"] == "wrong" and correct["outcome"] == "correct"
    assert inspect_sample(data, "schematic_untrimmed", 2)[1]["outcome"] == "wrong"
    assert correct["core_energy_fj"] > wrong["core_energy_fj"]


@pytest.mark.parametrize("sign", ("negative", "positive"))
@pytest.mark.parametrize("temperature", ("ss_cold", "ss_hot"))
def test_slow_corner_exploration_does_not_relabel_the_original_one_ns_gate(sign, temperature):
    data = load_lab()
    name = f"layout_{temperature}_{sign}"
    early = inspect_sample(data, name, 1)[1]
    later = inspect_sample(data, name, 2)[1]
    assert early["outcome"] == "unresolved" and early["decision_time_ns"] is None
    assert later["outcome"] == "correct" and 1 < later["decision_time_ns"] < 2
    assert early["core_energy_fj"] == later["core_energy_fj"]


def test_unsupported_example_or_window_has_no_silent_nearest_substitution():
    data = load_lab()
    with pytest.raises(ValueError, match="Unknown"):
        inspect_sample(data, "not_embedded", 1)
    with pytest.raises(ValueError, match="already reported"):
        inspect_sample(data, "layout_ss_cold_negative", 3.5)


def test_corrupted_metrics_or_outcomes_are_not_success_shaped():
    data = load_lab()
    reading = inspect_sample(data, "schematic_untrimmed", 1)[1]
    altered = deepcopy(reading)
    altered["outcome"] = "correct"
    with pytest.raises(RuntimeError, match="outcome"):
        verify_observation(reading, altered)
    altered = deepcopy(reading)
    altered["core_energy_fj"] *= 0.5
    with pytest.raises(RuntimeError, match="core_energy"):
        verify_observation(reading, altered)
