import json

import pytest

from comparator_atlas.experiments import load_results, source_hashes
from comparator_atlas.spice import SimulationError, sha256, write_json


@pytest.fixture
def evidence(tmp_path):
    (tmp_path / "measurements.csv").write_text("input_mv,outcome\n1,correct\n", encoding="utf-8")
    write_json(tmp_path / "calibration.json", [{"code": 0}])
    manifest = {
        "status": "complete", "row_count": 1, "case_count": 1,
        "source_hashes": source_hashes(),
        "artifact_sha256": {
            name: sha256(tmp_path / name) for name in ("measurements.csv", "calibration.json")
        },
    }
    write_json(tmp_path / "manifest.json", manifest)
    return tmp_path


def test_completed_evidence_loads(evidence):
    frame, calibration, _ = load_results(evidence)
    assert len(frame) == len(calibration) == 1


def test_modified_measurements_are_rejected(evidence):
    with (evidence / "measurements.csv").open("a") as file:
        file.write("2,correct\n")
    with pytest.raises(SimulationError, match="modified"):
        load_results(evidence)


def test_incomplete_run_is_not_presented(evidence):
    path = evidence / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["status"] = "running"
    write_json(path, manifest)
    with pytest.raises(SimulationError, match="did not complete"):
        load_results(evidence)


def test_stale_source_results_are_rejected(evidence):
    path = evidence / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["source_hashes"] = {}
    write_json(path, manifest)
    with pytest.raises(SimulationError, match="code changed"):
        load_results(evidence)
