import json
from itertools import product

import matplotlib.pyplot as plt
import numpy as np
import pytest

import entry_tools
import layout_evidence as physical
import single_row_a1_evidence as area


@pytest.fixture(scope="module")
def evidence():
    return area.load()


def test_actual_gds_bbox_and_frozen_geometry(evidence):
    for layout, width in (("control", 129.6), ("candidate", 121.8)):
        polygons = physical.gds_polygons((area.FOLDER / "native" / layout / "atlas.gds").read_bytes())
        points = np.array([xy for shapes in polygons.values() for shape in shapes for xy in shape])
        bounds = [*points.min(axis=0), *points.max(axis=0)]
        assert bounds == pytest.approx([-width / 2, -4.84, width / 2, 12.19])
        assert np.prod(points.max(axis=0) - points.min(axis=0)) == pytest.approx(width * 17.03)
    assert entry_tools.digest(area.FOLDER / "native/candidate/atlas.gds") == area.GDS_SHA256
    assert evidence["gates"]["native_drc_attempts"] == 1
    assert len(evidence["gates"]["checks"]) == 14
    assert evidence["gates"]["control_proof_reused_not_rerun"]
    static = area.read_json("native-a1/static-envelope-diagnosis.json")
    assert static["chosen_pitch_um"] == 4.5
    assert static["minimum_well_edge_gap_um"] == pytest.approx(1.54)
    assert entry_tools.digest(area.FOLDER / "native-a1/area_single_row.py") == (
        "ffa62dc441895c2fbcf5344e65313a36a8ca078676b519e6973e5a8152bbfa5f")


def test_cartesian_closure_outcomes_transitions_and_nulls(evidence):
    frame = evidence["frame"]
    expected = set(product(("tt", "ss", "ff", "sf", "fs"),
                           (1.62, 1.8, 1.95), (-40, 27, 125), (-10, -3, 3, 10)))
    keys = ["corner", "vdd_v", "temperature_c", "signed_input_mv"]
    for layout, mode in product(("control", "candidate"), ("c", "rc")):
        rows = frame[(frame.layout == layout) & (frame["mode"] == mode)]
        for deadline in (1, 2):
            part = rows[rows.deadline_ns == deadline]
            assert set(part[keys].itertuples(index=False, name=None)) == expected
            assert len(part) == 180
            assert part.numerically_qualified.all() and part.reset_ok.all()
        assert rows[rows.deadline_ns == 2].outcome.eq("correct").all()
    changed = evidence["paired"].query("control_outcome != candidate_outcome")
    assert set(changed[["mode", *keys, "deadline_ns"]].itertuples(index=False, name=None)) == {
        ("c", "ss", 1.62, -40, -10, 1), ("c", "ss", 1.62, -40, 10, 1)}
    assert changed.control_latency_ns.isna().all()
    assert changed.candidate_latency_ns.notna().all()
    assert frame[frame.outcome == "unresolved"].decision_time_ns.isna().all()
    audits = area.read_json("numerical-audits.json")
    assert len(audits) == 720 and all(row["qualified"] for row in audits)
    assert all(row["finest_max_step_ps"] == 5 for row in audits)
    assert len(area.read_json("pre-data-deck-plan.json")) == 1440


def test_claims_original_control_and_public_raw_closure(evidence):
    entry_tools.verify_files(area.ROOT, area.read_json("original-public-control-sha256.json"))
    provenance = evidence["provenance"]
    assert provenance["lossless_simulation_bytes"] and provenance["duplicated_models"] == 0
    assert len(provenance["raw_parts"]) == 12
    assert sum(row["transients"] for row in provenance["raw_parts"]) == 1440
    assert sum(row["members"] for row in provenance["raw_parts"]) == 11520
    assert all(row["bytes"] < 50 * 1024 * 1024 for row in provenance["raw_parts"])
    table = area.table(evidence).set_index(["version", "mode"])
    assert table.loc[("single-row-a1", "RC"), "mean core fJ"] == pytest.approx(421.0447302201909)
    assert table.loc[("single-row-a1", "RC"), "worst recorded ns"] == pytest.approx(1.8106318075694012)
    assert table.loc[("single-row-a1", "C"), "1ns correct/wrong/unresolved"] == "170/0/10"
    for factory in (area.layout_figure, area.comparison_figure, area.worst_figure):
        figure = factory(evidence)
        plt.close(figure)
    notebook = json.loads((area.ROOT / "Comparator_Atlas.ipynb").read_bytes())
    sources = "\n".join("".join(c["source"]) for c in notebook["cells"])
    assert "area.load()" in sources and "Historical original-control" in sources
    assert "not uncertainty bounds" in sources


@pytest.mark.parametrize("field,value", [
    ("decision_time_ns", float("inf")), ("decision_time_ns", float("nan")),
    ("core_energy_fj", float("nan")), ("outcome", "unavailable"), ("decision", 1),
])
def test_invalid_required_records_fail_explicitly(evidence, field, value):
    frame = evidence["frame"].iloc[:1].copy()
    assert frame.iloc[0].decision == -1
    frame.loc[frame.index[0], field] = value
    with pytest.raises(ValueError):
        area.validate_observations(frame)


def test_unresolved_latency_is_never_zero_filled(evidence):
    frame = evidence["frame"].query("outcome == 'unresolved'").iloc[:1].copy()
    assert frame.decision_time_ns.isna().all()
    frame.loc[frame.index[0], "decision_time_ns"] = 0
    with pytest.raises(ValueError, match="fabricated unresolved"):
        area.validate_observations(frame)
