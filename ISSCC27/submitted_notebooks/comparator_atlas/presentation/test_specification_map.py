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
    assert base64.b64decode("".join(outputs[-2]["data"]["image/png"])) == (
        spec.FOLDER / "selection_map.png"
    ).read_bytes()
    assert "".join(outputs[-1]["data"]["text/html"]) == spec.example_table(result)._repr_html_()
