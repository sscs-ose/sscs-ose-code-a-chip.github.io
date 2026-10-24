from itertools import product
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest

import entry_tools
import layout_evidence
from layout_nominal27 import contract
import single_row_evidence as area


@pytest.fixture(scope="module")
def evidence():
    return area.load()


def test_frozen_geometry_and_versioned_native_proof(evidence):
    for layout, width in (("control", 121.8), ("candidate", 110)):
        layers = layout_evidence.gds_polygons((area.FOLDER / "native" / layout / "atlas.gds").read_bytes())
        points = np.array([xy for polygons in layers.values() for polygon in polygons for xy in polygon])
        assert [*points.min(axis=0), *points.max(axis=0)] == pytest.approx(
            [-width / 2, -4.84, width / 2, 12.19])
        assert np.prod(points.max(axis=0) - points.min(axis=0)) == pytest.approx(width * 17.03)
    assert area.VERSION == "single-row-local-pitch-b1"
    assert entry_tools.digest(area.FOLDER / "native/candidate/atlas.gds") == area.GDS_SHA256
    assert evidence["gates"]["native_drc_attempts"] == 1
    assert evidence["gates"]["control_proof_reused_not_rerun"]
    routing = area.read_json("native-b1/protocol.json")["layout"]["routing"]
    assert routing["balanced_outputs"]["bus_half_span_um"] == 20.4
    assert routing["ground_shields"]["metal4_spine_x_um"] == [-21, 21]
    proof = area.read_json("native-b1/relative-invariants.json")
    assert proof
    assert area.read_json("native-b1/inherited-global-tracks.json")["inherited_rule_margin_um"] == .16
    for factory in (area.layout_figure, area.comparison_figure, area.worst_figure):
        plt.close(factory(evidence))


def test_four180_key_populations_and_exact_transition_keys(evidence):
    frame, paired = evidence["frame"], evidence["paired"]
    for layout, mode, deadline in product(("control", "candidate"), ("c", "rc"), (1, 2)):
        rows = frame[(frame.layout == layout) & (frame["mode"] == mode) & (frame.deadline_ns == deadline)]
        assert len(rows) == 180 and rows.numerically_qualified.all() and rows.reset_ok.all()
        if deadline == 2:
            assert rows.outcome.eq("correct").all()
    changed = paired[paired.control_outcome != paired.candidate_outcome]
    assert set(changed[["mode", "corner", "vdd_v", "temperature_c", "signed_input_mv", "deadline_ns"]]
               .itertuples(index=False, name=None)) == {
                   ("rc", "ss", 1.62, 125, -10, 1), ("rc", "ss", 1.62, 125, 10, 1)}
    assert changed.control_latency_ns.isna().all() and changed.candidate_latency_ns.notna().all()
    assert frame[frame.outcome == "unresolved"].decision_time_ns.isna().all()
    table = area.table(evidence).set_index(["version", "mode"])
    assert table.loc[(area.VERSION, "RC"), "1ns correct/wrong/unresolved"] == "158/0/22"
    assert table.loc[(area.VERSION, "RC"), "mean core fJ"] == pytest.approx(412.8794689093196)
    assert table.loc[(area.VERSION, "RC"), "worst recorded ns"] == pytest.approx(1.7602764829954507)
    assert table.loc[("Matched adopted a1", "RC"), "mean core fJ"] == pytest.approx(421.0447302201909)


def test_recompute_all720_numeric_receipts_without_native_or_spice(evidence):
    records = area.read_json("execution-index.json")
    histories = {}
    for r in records:
        key = (r["layout"], r["mode"], tuple(r["condition"]), r["signed_input_mv"])
        histories.setdefault(key, []).append(r)
    audits = area.read_json("numerical-audits.json")
    assert len(audits) == len(histories) == 720
    for row in audits:
        key = (row["layout"], row["mode"], tuple(row["condition"]), row["signed_input_mv"])
        expected = {k: v for k, v in row.items() if k not in (
            "layout", "mode", "condition", "signed_input_mv")}
        assert contract.refinement_state(histories[key]) == expected
        assert expected["qualified"] and expected["finest_max_step_ps"] == 5
    reference = area.read_json("fresh-control-archived-a1-agreement.json")
    assert len(reference) == 360 and all(row["passed"] for row in reference)
    assert all(c["fresh"] == c["archived"] for row in reference for c in row["checks"])


def test_pointwise_changes_and_distinct_energy_estimators(evidence):
    comparisons = area.read_json("keyed-layout-comparisons.json")
    lookup = {(r["layout"], r["mode"], *r["condition"], r["signed_input_mv"]): r
              for r in area.read_json("numerical-audits.json")}
    for r in comparisons:
        for label in ("control", "candidate"):
            observations = lookup[(label, r["mode"], *r["condition"], r["signed_input_mv"])]["finest_measurements"]
            assert r[label] == next(m for m in observations if m["deadline_ns"] == r["deadline_ns"])
        a, b = r["control"], r["candidate"]
        assert r["energy_change_percent"] == 100 * (b["core_energy_fj"] / a["core_energy_fj"] - 1)
        assert not r["regression_gate"]
        if a["decision_time_ns"] is None or b["decision_time_ns"] is None:
            assert r["latency_delta_ns"] is None
        else:
            assert r["latency_delta_ns"] == b["decision_time_ns"] - a["decision_time_ns"]
    rc = next(row for row in evidence["analysis"]["mode_deltas"] if row["mode"] == "rc")
    assert rc["ratio_of_total_and_mean_energy_change_percent"] == pytest.approx(-1.9392859534428042)
    assert rc["mean_per_point_energy_change_percent"] == pytest.approx(-1.9456588943449311)
    assert rc["ratio_of_total_and_mean_energy_change_percent"] != rc["mean_per_point_energy_change_percent"]


def test_portable_mapping_retains_all_actual_raw_members(evidence):
    provenance = evidence["provenance"]
    assert provenance["lossless_actual_simulation_bytes"] and provenance["duplicated_models"] == 0
    assert len(provenance["raw_parts"]) == 12
    assert all(p["bytes"] < 30 * 1024**2 for p in provenance["raw_parts"])
    members = provenance["raw_members"]
    assert sum(n.startswith("full45/raw/simulations/") for n in members) == 1440 * 8
    assert sum(n.startswith("bounded64/diagnostic-raw/simulations/") for n in members) == 64 * 8
    entry_tools.verify_files(area.ROOT, area.read_json("historical-source-sha256.json"))


def test_current_selector_mismatch_fails_explicitly(monkeypatch):
    original = Path.read_bytes
    selector = area.ROOT / "layout_single_row" / "current.json"

    def changed_version(path):
        data = original(path)
        if path == selector:
            value = json.loads(data)
            value["adopted_version"] = "single-row-a1"
            return json.dumps(value).encode()
        return data

    monkeypatch.setattr(Path, "read_bytes", changed_version)
    with pytest.raises(ValueError, match="selector and entry metadata disagree"):
        area.load()
