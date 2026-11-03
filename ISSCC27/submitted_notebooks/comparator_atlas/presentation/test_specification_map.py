import base64
from collections import Counter
from copy import deepcopy
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import entry_tools as entry
from presentation import specification_map as spec


@pytest.fixture(scope="module")
def evidence():
    return entry.load_evidence()


@pytest.fixture(scope="module")
def result(evidence):
    return spec.analyze(evidence)


@pytest.mark.parametrize("minimum,deadline,counts,winner,energy", [
    (1, 1, (310, 372, 351), None, None),
    (3, 1, (253, 294, 285), "lvt_balanced_4b", 249.655),
    (30, 1, (89, 98, 98), "lvt_base_3b", 150.531),
    (10, 2, (187, 196, 196), "lvt_base_3b", 152.662),
    (10, 0.75, None, "lvt_balanced_4b", 247.618),
    (30, 0.5, None, None, None),
])
def test_known_specifications(result, minimum, deadline, counts, winner, energy):
    rows = [row for row in result["per_design"]
            if row["minimum_abs_input_mv"] == minimum and row["deadline_ns"] == deadline]
    if counts is not None:
        assert tuple(row["correct"] for row in rows) == counts
    if (minimum, deadline) == (30, 0.5):
        assert rows[1]["correct"] == 96 and rows[1]["points"] == 98
    selected = next(row for row in result["per_specification"]
                    if row["minimum_abs_input_mv"] == minimum and row["deadline_ns"] == deadline)
    assert selected["winner"] == winner
    if energy is None:
        assert selected["status"] == spec.NO_FEASIBLE
        assert selected["mean_core_energy_fj"] is None
    else:
        assert selected["mean_core_energy_fj"] == pytest.approx(energy, abs=0.0005)


def test_full_shapes_and_strict_winners(result):
    assert len(result["per_design"]) == 108
    assert len(result["per_specification"]) == 36
    assert Counter(row["winner"] for row in result["per_specification"]) == {
        None: 28, "lvt_balanced_4b": 5, "lvt_base_3b": 3,
    }
    assert result["conditions"] == 49 and result["new_physical_simulations"] == 0
    assert result["policy"] == "local_boundary"
    for selected in result["per_specification"]:
        if selected["minimum_abs_input_mv"] <= 1:
            assert selected["winner"] is None
        rows = [row for row in result["per_design"]
                if row["minimum_abs_input_mv"] == selected["minimum_abs_input_mv"]
                and row["deadline_ns"] == selected["deadline_ns"]]
        qualifying = [row for row in rows if row["correct"] == row["points"]
                      and row["fully_passing_conditions"] == 49]
        assert {row["design"] for row in qualifying} == set(selected["qualifying_designs"])
        if selected["winner"] is not None:
            assert selected["mean_core_energy_fj"] == min(row["mean_core_energy_fj"] for row in qualifying)


@pytest.mark.parametrize("damage", [
    "missing", "duplicate", "unavailable", "nonfinite_input", "nonfinite_energy",
    "reset", "run_id", "outcome",
])
def test_invalid_observations_never_become_passes(evidence, damage):
    frame = evidence["frame"].copy(deep=True)
    index = frame.index[frame.policy.eq("local_boundary") & frame.input_mv.ne(0)][0]
    if damage == "missing":
        frame = frame.drop(index)
    elif damage == "duplicate":
        frame = pd.concat([frame, frame.loc[[index]]])
    else:
        field, value = {
            "unavailable": ("policy_available", False),
            "nonfinite_input": ("input_mv", np.inf),
            "nonfinite_energy": ("core_energy_fj", np.nan),
            "reset": ("reset_ok", False),
            "run_id": ("run_id", ""),
            "outcome": ("outcome", "not_run"),
        }[damage]
        frame.loc[index, field] = value
    with pytest.raises(ValueError):
        spec.analyze({**evidence, "frame": frame})


def test_exact_energy_ties_are_disclosed_and_deterministic(result):
    rows = deepcopy([row for row in result["per_design"]
                     if row["minimum_abs_input_mv"] == 30 and row["deadline_ns"] == 1])
    for row in rows:
        if row["all_correct"]:
            row["mean_core_energy_fj"] = 150.0
    selected = spec.choose(list(reversed(rows)))
    assert selected["minimum_energy_ties"] == ["lvt_balanced_4b", "lvt_base_3b"]
    assert selected["winner"] == "lvt_balanced_4b"
    assert selected["mean_core_energy_fj"] == 150.0


def test_no_feasible_design_has_no_best_average_fallback(result):
    rows = [row for row in result["per_design"]
            if row["minimum_abs_input_mv"] == 1 and row["deadline_ns"] == 1]
    assert spec.choose(rows) == {
        "status": spec.NO_FEASIBLE, "winner": None, "mean_core_energy_fj": None,
        "qualifying_designs": [], "minimum_energy_ties": [],
    }


def test_saved_artifact_recomputes_from_unchanged_evidence(evidence, result):
    saved = spec.load_checked(evidence)
    assert saved == result
    entry.verify_files(entry.ROOT, saved["source_sha256"])
    assert len(saved["source_sha256"]) == len(spec.SOURCES)


def test_figure_is_not_color_only(result):
    figure = spec.figure(result)
    labels = [text.get_text() for text in figure.axes[0].texts]
    plt.close(figure)
    assert len(labels) == 36
    assert labels.count("NONE") == 28
    assert sum(label.startswith("SEL\n") for label in labels) == 5
    assert sum(label.startswith("CTL\n") for label in labels) == 3


def test_notebook_sources_and_saved_map_match_generator(monkeypatch, result):
    from scripts import build_entry_notebook

    notebook = json.loads((entry.ROOT / "Comparator_Atlas.ipynb").read_bytes())
    generated = []
    monkeypatch.setattr(build_entry_notebook.nbf, "write",
                        lambda document, destination: generated.append(document))
    build_entry_notebook.main()
    for index in (6, 7):
        assert generated[0].cells[index].source == "".join(notebook["cells"][index]["source"])
    outputs = notebook["cells"][7]["outputs"]
    assert base64.b64decode("".join(outputs[-5]["data"]["image/png"])) == (
        spec.FOLDER / "selection_map.png"
    ).read_bytes()
    assert "".join(outputs[-4]["data"]["text/html"]) == spec.example_table(result)._repr_html_()
    assert base64.b64decode("".join(outputs[-3]["data"]["image/png"])) == (
        spec.FOLDER / "failure_transitions.png"
    ).read_bytes()
    assert "".join(outputs[-2]["data"]["text/html"]) == spec.failure_table(result)._repr_html_()
    assert "".join(outputs[-1]["data"]["text/html"]) == spec.selected_wrong_table(result)._repr_html_()


def test_failure_counts_shapes_and_exact_transitions(result):
    analysis = result["failure_analysis"]
    assert {name: len(rows) for name, rows in analysis["grouped_counts"].items()} == {
        "design_deadline": 18, "signed_input": 216, "corner": 90,
        "vdd_v": 54, "temperature_c": 54, "pair_skew": 90, "case_id": 882,
    }
    for rows in analysis["grouped_counts"].values():
        assert sum(row["points"] for row in rows) == 10584
        assert all(row["points"] == sum(row[outcome] for outcome in spec.OUTCOMES) for row in rows)
    assert len(analysis["matched_samples"]) == 1176
    assert len(analysis["transition_matrix"]) == 27
    matrices = [[row["points"] for row in analysis["transition_matrix"] if row["design"] == design]
                for design in spec.DESIGNS]
    assert matrices == [
        [310, 0, 0, 0, 22, 0, 29, 9, 22],
        [372, 0, 0, 0, 20, 0, 0, 0, 0],
        [351, 0, 0, 0, 32, 0, 6, 3, 0],
    ]
    assert spec.failure_table(result)[list(spec.OUTCOMES)].values.tolist() == [
        [310, 22, 60], [339, 31, 22], [372, 20, 0],
        [372, 20, 0], [351, 32, 9], [357, 35, 0],
    ]
    assert len({tuple(row[key] for key in spec.SAMPLE_KEY)
                for row in analysis["matched_samples"]}) == 1176
    expected = set(spec.SAMPLE_KEY + spec.LOCATION) | {
        f"{name}_{endpoint}ns" for name in (
            "deadline_ns", "run_id", "outcome", "decision_time_ns", "core_energy_fj",
        ) for endpoint in (1, 2)
    }
    assert all(set(row) == expected for row in analysis["matched_samples"])
    assert all(set(row) == {"design", "outcome_1ns", "outcome_2ns", "points"}
               for row in analysis["transition_matrix"])


def test_actual_selected_wrong_identities_and_metadata(result):
    wrong = result["failure_analysis"]["selected_wrong"]
    assert (wrong["count_1ns"], wrong["count_2ns"], wrong["same_sample_set"]) == (20, 20, True)
    expected = {
        ("ff", 1.8, -40, .04, -1, -4), ("ff", 1.8, 125, .04, 1, -9),
        ("ff", 1.8, 27, .04, -1, -6), ("fs", 1.62, -40, .04, -1, -1),
        ("fs", 1.62, 27, .04, 1, -2), ("fs", 1.8, 125, .04, -1, -3),
        ("fs", 1.95, 27, .04, -1, -3), ("sf", 1.62, -40, .04, 1, -3),
        ("sf", 1.62, 125, .04, -1, -6), ("sf", 1.8, -40, .04, -1, -4),
        ("sf", 1.8, 27, .04, 1, -7), ("sf", 1.95, 27, .04, -1, -8),
        ("ss", 1.62, -40, .04, 1, -2), ("ss", 1.8, -40, .04, -1, -2),
        ("ss", 1.8, 125, .04, -1, -3), ("ss", 1.95, -40, .04, -1, -3),
        ("ss", 1.95, 27, .04, 1, -4), ("tt", 1.62, 27, .04, -1, -2),
        ("tt", 1.8, 27, .08, 1, -8), ("tt", 1.8, 27, -.08, -1, 8),
    }
    assert {tuple(row[key] for key in (
        "corner", "vdd_v", "temperature_c", "pair_skew", "input_mv", "trim_code",
    )) for row in wrong["samples"]} == expected
    assert all(row["outcome_1ns"] == row["outcome_2ns"] == "wrong" for row in wrong["samples"])


def test_shuffled_rows_do_not_change_pairing_or_analysis(evidence, result):
    shuffled = {**evidence, "frame": evidence["frame"].sample(frac=1, random_state=3)}
    assert spec.failure_analysis(shuffled) == result["failure_analysis"]


def test_equal_failure_totals_do_not_imply_persistent_samples(evidence):
    frame = evidence["frame"].copy(deep=True)
    selected = frame.policy.eq("local_boundary") & frame.design_name.eq("lvt_balanced_4b") \
        & frame.input_mv.abs().ge(1) & frame.deadline_ns.eq(2)
    wrong = frame.index[selected & frame.outcome.eq("wrong")][0]
    correct = frame.index[selected & frame.outcome.eq("correct")][0]
    frame.loc[wrong, "outcome"] = "correct"
    frame.loc[correct, "outcome"] = "wrong"
    result = spec.failure_analysis({**evidence, "frame": frame})
    assert result["selected_wrong"]["count_1ns"] == result["selected_wrong"]["count_2ns"] == 20
    assert result["selected_wrong"]["same_sample_set"] is False
    assert len(result["selected_wrong"]["samples"]) == 21
    matrix = {(row["outcome_1ns"], row["outcome_2ns"]): row["points"]
              for row in result["transition_matrix"] if row["design"] == "lvt_balanced_4b"}
    assert matrix[("correct", "wrong")] == matrix[("wrong", "correct")] == 1


@pytest.mark.parametrize("damage", ["missing", "duplicate", "unmatched", "metadata"])
def test_transition_join_rejects_bad_endpoints(evidence, damage):
    frame = evidence["frame"]
    frame = frame[frame.policy.eq("local_boundary") & frame.input_mv.abs().ge(1)].copy()
    index = frame.index[frame.deadline_ns.eq(2)][0]
    if damage == "missing":
        frame = frame.drop(index)
    elif damage == "duplicate":
        frame = pd.concat([frame, frame.loc[[index]]])
    elif damage == "unmatched":
        frame.loc[index, "input_mv"] = 99
    else:
        frame.loc[index, "trim_code"] += 1
    with pytest.raises(ValueError):
        spec.matched_transitions(frame)


@pytest.mark.parametrize("field,value", [
    ("decision_time_ns", np.inf), ("decision_time_ns", np.nan),
    ("decision_time_ns", -1), ("decision_time_ns", 99),
    ("trim_code", np.nan), ("trim_code", 0.5),
    ("vdd_v", np.inf), ("corner", "unknown"),
])
def test_invalid_required_observations_rejected(evidence, field, value):
    frame = evidence["frame"].copy(deep=True)
    index = frame.index[frame.policy.eq("local_boundary") & frame.input_mv.ne(0)
                        & frame.outcome.eq("correct")][0]
    frame.loc[index, field] = value
    with pytest.raises(ValueError):
        spec.analyze({**evidence, "frame": frame})


def test_unresolved_times_cannot_be_invented(evidence):
    frame = evidence["frame"].copy(deep=True)
    index = frame.index[frame.policy.eq("local_boundary") & frame.input_mv.ne(0)
                        & frame.outcome.eq("unresolved")][0]
    frame.loc[index, "decision_time_ns"] = .1
    with pytest.raises(ValueError, match="Unresolved"):
        spec.analyze({**evidence, "frame": frame})


@pytest.mark.parametrize("minimum,deadline,margin,maximum,time_input,energy_input", [
    (3, 1, 154.51661322480092, 363.2168092468344, -3, -3),
    (30, 1, 118.7313648023307, 212.40560518391467, -30, 30),
    (10, 2, 915.7959489390499, 220.32543578798465, -10, 10),
])
def test_sampled_limit_anchors_and_exact_limiting_samples(
        result, minimum, deadline, margin, maximum, time_input, energy_input):
    row = next(row for row in result["per_specification"]
               if row["minimum_abs_input_mv"] == minimum and row["deadline_ns"] == deadline)
    limits = row["sampled_limits"]
    assert limits["minimum_decision_margin_ps"] == pytest.approx(margin, abs=1e-10)
    assert limits["maximum_core_energy_fj"] == pytest.approx(maximum, abs=1e-10)
    assert len(limits["timing_limiting_samples"]) == len(limits["energy_limiting_samples"]) == 1
    timing, energy = limits["timing_limiting_samples"][0], limits["energy_limiting_samples"][0]
    assert timing["case_id"] == "FS | 1.62 V | -40 C | skew +4%"
    assert timing["input_mv"] == time_input
    assert energy["case_id"] == "FF | 1.95 V | 125 C | skew +4%"
    assert energy["input_mv"] == energy_input


def test_every_qualified_design_limits_and_none_nulls(evidence, result):
    frame = evidence["frame"]
    for row in result["per_design"]:
        if not row["all_correct"]:
            assert row["sampled_limits"] is None
            continue
        part = frame[frame.policy.eq("local_boundary") & frame.design_name.eq(row["design"])
                     & frame.deadline_ns.eq(row["deadline_ns"])
                     & frame.input_mv.abs().ge(row["minimum_abs_input_mv"])]
        assert row["sampled_limits"] == spec.sampled_limits(part)
    for row in result["per_specification"]:
        if row["winner"] is None:
            assert row["mean_core_energy_fj"] is row["sampled_limits"] is None
        else:
            design = next(record for record in result["per_design"]
                          if record["design"] == row["winner"]
                          and record["minimum_abs_input_mv"] == row["minimum_abs_input_mv"]
                          and record["deadline_ns"] == row["deadline_ns"])
            assert row["sampled_limits"] == design["sampled_limits"]


def test_sampled_limit_ties_empty_and_unqualified(evidence):
    frame = evidence["frame"]
    part = frame[frame.policy.eq("local_boundary") & frame.outcome.eq("correct")].head(2).copy()
    part["decision_time_ns"] = .125
    part["deadline_ns"] = 1
    part["core_energy_fj"] = 100
    part["input_mv"] = [-30, 30]
    limits = spec.sampled_limits(part.iloc[::-1])
    assert limits["minimum_decision_margin_ps"] == 875
    assert limits["maximum_core_energy_fj"] == 100
    for field in ("timing_limiting_samples", "energy_limiting_samples"):
        assert [row["input_mv"] for row in limits[field]] == [-30, 30]
    with pytest.raises(ValueError, match="empty"):
        spec.sampled_limits(part.iloc[:0])
    part.loc[part.index[0], "outcome"] = "wrong"
    assert spec.sampled_limits(part) is None


def test_empty_wrong_table_and_textual_transition_figure(result):
    empty = deepcopy(result)
    empty["failure_analysis"]["selected_wrong"]["samples"] = []
    table = spec.selected_wrong_table(empty)
    assert table.empty and list(table.columns) == [
        "case_id", "input_mv", "trim_code", "outcome_1ns", "outcome_2ns",
    ]
    figure = spec.failure_figure(result)
    assert [[int(text.get_text()) for text in ax.texts] for ax in figure.axes] == [
        [310, 0, 0, 0, 22, 0, 29, 9, 22],
        [372, 0, 0, 0, 20, 0, 0, 0, 0],
        [351, 0, 0, 0, 32, 0, 6, 3, 0],
    ]
    plt.close(figure)


@pytest.mark.parametrize("damage", ["source", "figure", "records"])
def test_derived_artifact_integrity_is_fail_closed(evidence, monkeypatch, damage):
    if damage == "records":
        original = spec.analyze

        def altered(evidence):
            result = original(evidence)
            result["failure_analysis"]["matched_samples"][0]["outcome_1ns"] = "wrong"
            return result

        monkeypatch.setattr(spec, "analyze", altered)
    else:
        original = entry.digest
        target = "specification_map.py" if damage == "source" else "failure_transitions.png"
        monkeypatch.setattr(entry, "digest", lambda path: "changed"
                            if path.name == target else original(path))
    with pytest.raises(RuntimeError, match="differs"):
        spec.load_checked(evidence)
