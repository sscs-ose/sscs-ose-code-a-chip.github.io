import pytest

from comparator_atlas.study import (
    DEADLINES_NS, POLICIES, Evidence, TRAINING_INPUTS_MV, VALIDATION_INPUTS_MV,
    _payload_hash, chosen_code, protocol, read_case_checkpoint, training_cases,
)
from comparator_atlas.spice import Point, SimulationError, write_json


def test_selection_and_validation_inputs_are_disjoint():
    assert not set(TRAINING_INPUTS_MV) & set(VALIDATION_INPUTS_MV)


def test_declared_scope_and_budgets():
    plan = protocol()
    assert len(plan["candidate_family"]) == 9
    assert len(plan["validation_cases"]) == 49
    assert len(plan["policies"]) == 4
    assert len(training_cases("baseline")) == 3
    assert plan["budgets"]["maximum_gate_area_proxy_relative_to_baseline"] == 4


def test_unavailable_calibration_has_no_invented_code():
    assert chosen_code({"available": False, "selection": None}) is None


def test_unavailable_policy_has_no_invented_waveform_or_energy():
    class NoSimulation:
        def run_many(self, points):
            assert points == []
            return []
    evidence = Evidence(NoSimulation())
    rows = evidence.observations(
        Point(), {"unavailable": None}, (-1, 1), (0.5, 1.0),
    )
    assert len(rows) == 4
    assert all(row["outcome"] == "calibration_unavailable" for row in rows)
    assert all(row["core_energy_fj"] is None and row["run_id"] is None for row in rows)
    assert all(not row["policy_available"] for row in rows)


def test_checkpoint_requires_matching_identity_and_complete_grid(tmp_path):
    path = tmp_path / "case.json"
    identity = {"point": "test"}
    payload = {"rows": [{}] * (len(POLICIES) * len(VALIDATION_INPUTS_MV) * len(DEADLINES_NS))}
    assert read_case_checkpoint(path, identity) is None
    write_json(path, {"identity": identity, "payload": payload, "payload_sha256": _payload_hash(payload)})
    assert read_case_checkpoint(path, identity) == payload
    with pytest.raises(SimulationError, match="different experiment"):
        read_case_checkpoint(path, {"point": "changed"})
    payload["rows"].pop()
    write_json(path, {"identity": identity, "payload": payload, "payload_sha256": _payload_hash(payload)})
    with pytest.raises(SimulationError, match="incomplete"):
        read_case_checkpoint(path, identity)


def test_modified_checkpoint_is_not_silently_reused(tmp_path):
    path = tmp_path / "case.json"
    write_json(path, {"identity": {}, "payload": {"rows": []}, "payload_sha256": "incorrect"})
    with pytest.raises(SimulationError, match="modified"):
        read_case_checkpoint(path, {})
