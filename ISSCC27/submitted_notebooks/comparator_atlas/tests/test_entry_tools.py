from pathlib import Path

import pandas as pd
import pytest

from entry_tools import artifact_path, full_reproduction, summary, verify_files


def test_archived_windows_keys_resolve_portably(tmp_path):
    assert artifact_path(tmp_path, "results\\study\\data.csv") == tmp_path / "results" / "study" / "data.csv"
    assert artifact_path(tmp_path, "results/study/data.csv") == tmp_path / "results" / "study" / "data.csv"


@pytest.mark.parametrize("name", ["../secret", "..\\secret", "/absolute", "C:\\private"])
def test_artifact_paths_cannot_escape_the_entry(tmp_path, name):
    with pytest.raises(ValueError):
        artifact_path(tmp_path, name)


def test_missing_evidence_is_not_silently_skipped(tmp_path):
    with pytest.raises(RuntimeError, match="Missing"):
        verify_files(tmp_path, {"missing.csv": "0" * 64})


def test_explicit_full_reproduction_refreshes_teaching_data_after_scientific_stages(monkeypatch):
    calls = []

    def capture(command, **options):
        assert options["check"] is True
        calls.append(command)

    monkeypatch.setattr("entry_tools.subprocess.run", capture)
    full_reproduction()
    assert [command[3] for command in calls[:3]] == ["optimize", "study", "stress"]
    assert calls[3][2] == "comparator_atlas.professional_audit"
    assert calls[4][2] == "presentation.waveform_lab"


def test_worst_case_and_coverage_do_not_hide_unavailable_policies():
    rows = []
    for case in ("A", "B"):
        for value in (-1, 0, 1):
            rows.append({
                "case_id": case, "design_name": "baseline", "policy": "local_boundary",
                "deadline_ns": 1, "input_mv": value,
                "outcome": "correct" if case == "A" else "calibration_unavailable",
                "core_energy_fj": 100 if case == "A" else None,
            })
    result = summary({"frame": pd.DataFrame(rows)}).loc["baseline"]
    assert result.points == 4
    assert result.correct == 2
    assert result.fully_passing_conditions == 1
    assert result.worst_condition_coverage == 0
    assert result.simulated_points == 2
