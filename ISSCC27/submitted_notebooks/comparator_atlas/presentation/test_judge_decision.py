"""Narrow saved-input/UI contracts; no simulator, waveform audit or native job."""
from collections import Counter
import ast
import json
import math

import pandas as pd
import pytest

import entry_tools as entry
from presentation import judge_decision as preview
from presentation import specification_map as spec


@pytest.fixture(scope="module")
def data():
    return preview.load_payload()


@pytest.fixture(scope="module")
def evidence():
    return entry.load_evidence()


def test_exact_36_choices_108_original_design_rows(data, evidence):
    original = spec.analyze(evidence)
    assert data["selections"] == original["per_specification"]
    assert len(data["candidates"]) == 108
    for actual, expected in zip(data["candidates"], original["per_design"]):
        assert {k: actual[k] for k in expected} == expected
        assert actual["correct"] + actual["wrong"] + actual["unresolved"] == actual["points"]
    assert Counter(row["winner"] for row in data["selections"]) == {
        None: 28, "lvt_balanced_4b": 5, "lvt_base_3b": 3}


def test_every_witness_exact_saved_key_location_run_null_and_csv_record(data, evidence):
    frame = evidence["frame"]
    local = frame[frame.policy.eq("local_boundary") & frame.input_mv.ne(0)]
    assert len(data["observations"]) == len(local) == 10584
    tables = {
        "verified_measurements.csv": pd.read_csv(entry.STUDY / "verified_measurements.csv"),
        "professional/measurements.csv": pd.read_csv(entry.STUDY / "professional/measurements.csv"),
    }
    seen = set()
    for record in data["observations"]:
        key = tuple(record[k] for k in [*spec.SAMPLE_KEY, "deadline_ns"])
        assert key not in seen
        seen.add(key)
        actual = tables[record["source_csv"]].iloc[record["source_record"] - 1]
        for field in spec.OBSERVATION:
            expected = actual[field]
            if pd.isna(expected):
                assert record[field] is None
            elif isinstance(expected, (float, int)):
                assert math.isclose(record[field], expected, abs_tol=0, rel_tol=0)
            else:
                assert record[field] == expected
    for minimum in spec.MINIMUMS_MV:
        for deadline in spec.DEADLINES_NS:
            choice, candidates = preview.inspect(minimum, deadline, data)
            for row in candidates:
                failures = [r for r in data["observations"] if r["design_name"] == row["design"]
                            and r["deadline_ns"] == deadline and abs(r["input_mv"]) >= minimum
                            and r["outcome"] != "correct"]
                expected = local[local.design_name.eq(row["design"]) & local.deadline_ns.eq(deadline)
                                 & local.input_mv.abs().ge(minimum) & ~local.outcome.eq("correct")]
                assert {tuple(r[k] for k in spec.OBSERVATION[:3]) for r in failures} \
                    == set(map(tuple, expected[spec.OBSERVATION[:3]].values))
                assert len(failures) == row["wrong"] + row["unresolved"]
                assert Counter(r["outcome"] for r in failures) == Counter(expected.outcome)
            if choice["winner"] is None:
                assert choice["mean_core_energy_fj"] is choice["sampled_limits"] is None
                assert choice["minimum_energy_ties"] == []
    assert all(r["decision_time_ns"] is None for r in data["observations"] if r["outcome"] == "unresolved")


def test_waveforms_only_if_identity_and_saved_observation_match(data):
    lab = json.loads((entry.ROOT / "evidence_traces/waveform_lab/waveform_lab.json").read_bytes())
    matched = [r for r in data["observations"] if r["waveform_sample_id"] is not None]
    assert len(matched) == 6
    for record in matched:
        sample = next(s for s in lab["samples"] if s["id"] == record["waveform_sample_id"])
        assert sample["source_kind"] == "schematic" and sample["id"] == "schematic_calibrated"
        assert sample["run_id"] == record["run_id"]
        assert sample["point"]["design_name"] == record["design_name"]
        for field in ("corner", "vdd_v", "temperature_c", "pair_skew", "trim_code"):
            assert sample["point"][field] == record[field]
        assert sample["point"]["differential_v"] * 1000 == record["input_mv"]
        reading = next(o for o in sample["observations"] if o["deadline_ns"] == record["deadline_ns"])
        assert reading["outcome"] == record["outcome"]
        assert reading["decision_time_ns"] == record["decision_time_ns"] \
            or math.isclose(reading["decision_time_ns"], record["decision_time_ns"], abs_tol=1e-12)
    assert sum(r["waveform_sample_id"] is None for r in data["observations"]) == 10578


def test_wrong_is_not_unresolved_same20_actual_keys(data):
    selected = data["selected_wrong"]
    assert selected["count_1ns"] == selected["count_2ns"] == 20 and selected["same_sample_set"]
    wrong = [{tuple(r[k] for k in spec.SAMPLE_KEY) for r in data["observations"]
              if r["design_name"] == "lvt_balanced_4b" and abs(r["input_mv"]) >= 1
              and r["deadline_ns"] == deadline and r["outcome"] == "wrong"} for deadline in (1, 2)]
    assert wrong[0] == wrong[1] == {tuple(r[k] for k in spec.SAMPLE_KEY) for r in selected["samples"]}


def test_notebook_static_presets_have_working_source_and_honest_scope(data):
    notebook = json.loads((entry.ROOT / "Comparator_Atlas.ipynb").read_bytes())
    assert len(notebook["cells"]) == 28 and sum(c["cell_type"] == "code" for c in notebook["cells"]) == 13
    source = "".join(notebook["cells"][1]["source"])
    assert "https://github.com/WLHsu0827/" in source
    assert '"git", "clone"' in source and "requirements-review.txt" in source
    assert "PRIVATE" not in source and "sys.version_info[:3]" not in source
    assert "RUN_LIVE_SPICE = False" in source and "RUN_FULL_CAMPAIGN = False" in source
    controls = "".join(notebook["cells"][8]["source"])
    assert "notebook_view" in controls and "interactive_output" in controls and "set_preset" in controls
    for minimum in (1, 3, 30):
        output = preview.notebook_view(minimum, 1)
        assert "wrong" in output and "unresolved" in output and "local_boundary" in output
        assert ("NONE" if minimum == 1 else preview.inspect(minimum, 1, data)[0]["winner"]) in output
    assert preview.SUBTITLE in "".join(notebook["cells"][0]["source"])


def test_generators_have_only_public_source_dependencies():
    source = (entry.ROOT / "presentation/judge_decision.py").read_text(encoding="utf-8")
    assert "RECEIPTS" not in source and "ROOT.parent" not in source and "source-Notebook" not in source
    assert "integrate_report" in (entry.ROOT / "comparator_atlas/study_report.py").read_text(encoding="utf-8")
    assert "integrate_notebook" in (entry.ROOT / "scripts/build_entry_notebook.py").read_text(encoding="utf-8")


def test_layout_selector_displays_actual_saved_schema_and_preserves_nulls():
    import single_row_evidence as area

    notebook = json.loads((entry.ROOT / "Comparator_Atlas.ipynb").read_bytes())
    source = next("".join(c["source"]) for c in notebook["cells"]
                  if c["cell_type"] == "code" and "def inspect_area_version(" in "".join(c["source"]))
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "inspect_area_version")
    adopted = area.load()
    shown = []
    context = {"adopted": adopted, "display": shown.append}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<layout-selector>", "exec"), context)
    for layout in ("candidate", "control"):
        for mode in ("rc", "c"):
            context["inspect_area_version"](layout, mode)
            expected = adopted["frame"].loc[
                adopted["frame"].layout.eq(layout) & adopted["frame"]["mode"].eq(mode)]
            pd.testing.assert_frame_equal(shown[-1], expected)


def test_saved_widget_state_has_no_embedded_errors():
    notebook = json.loads((entry.ROOT / "Comparator_Atlas.ipynb").read_bytes())
    preview.validate_notebook_outputs(notebook)


def test_nested_widget_error_is_rejected_despite_clean_top_level_cells():
    fixture = {
        "cells": [{"cell_type": "code", "outputs": [], "execution_count": 1}],
        "metadata": {"widgets": {"application/vnd.jupyter.widget-state+json": {
            "state": {"example": {"state": {"outputs": [
                {"output_type": "error", "ename": "KeyError", "evalue": "missing column"}
            ]}}}}}},
    }
    with pytest.raises(ValueError, match="metadata.widgets.*missing column"):
        preview.validate_notebook_outputs(fixture)


def test_complete_local_three_design_map_exact_saved_values(data, evidence):
    cube = json.loads((entry.STUDY / "decision_map_data.json").read_bytes())
    assert cube["designs"] == list(spec.DESIGNS) and cube["policies"] == ["local_boundary"]
    assert len(cube["rows"]) == 11466
    keys = {tuple(r[:5]) for r in cube["rows"]}
    assert len(keys) == 11466
    by_key = {tuple(r[:5]): r for r in cube["rows"]}
    outcomes = {"wrong": 0, "unresolved": 1, "correct": 2}
    for record in data["observations"]:
        key = (cube["designs"].index(record["design_name"]), cube["cases"].index(record["case_id"]),
               0, cube["deadlines"].index(record["deadline_ns"]), cube["inputs"].index(record["input_mv"]))
        row = by_key[key]
        assert row[5:] == [outcomes[record["outcome"]], record["decision_time_ns"],
                           record["core_energy_fj"], record["trim_code"]]
