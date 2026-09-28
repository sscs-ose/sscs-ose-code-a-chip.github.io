import json

import pytest

from presentation import pvt45_results as pvt
from scripts import audit_pvt_failures as audit
from scripts import build_entry_notebook


@pytest.fixture
def frame():
    return pvt.load_results()["frame"]


def test_actual_factor_marginals_conserve_all_24_unresolved_points(frame):
    result = audit.audit(frame)
    expected = {
        "corner": [0, 12, 0, 0, 12],
        "vdd_v": [24, 0, 0],
        "temperature_c": [8, 8, 8],
        "differential_mv": [6, 6, 6, 6],
    }
    for factor, counts in expected.items():
        rows = [r for r in result["marginals"] if r["factor"] == factor]
        assert [r["unresolved_1ns"] for r in rows] == counts
        assert sum(r["points"] for r in rows) == 180
        assert sum(r["correct_1ns"] for r in rows) == 156
        assert sum(r["unresolved_1ns"] for r in rows) == 24
        assert all(r["correct_2ns"] == r["points"] for r in rows)
        assert all(r["wrong_1ns"] == r["wrong_2ns"] == r["unresolved_2ns"] == 0 for r in rows)
    failed = result["unresolved_1ns_records"]
    assert len(failed) == len({r["finest_attempt_id"] for r in failed}) == 24
    assert all(r["vdd_v"] == 1.62 and r["corner"] in ("ss", "fs") for r in failed)
    assert result["causal_or_statistical_significance_claim"] is False
    assert result["rc_model_physical_fidelity_qualified"] is False


@pytest.mark.parametrize("fault", [
    "missing", "duplicate_key", "duplicate_attempt", "missing_id", "empty_id",
    "unexpected_label", "unknown_numeric", "changed_counts",
])
def test_invalid_grid_or_relabeling_cannot_be_counted_as_the_published_result(frame, fault):
    changed = frame.copy(deep=True)
    if fault == "missing":
        changed = changed.iloc[:-1]
    elif fault == "duplicate_key":
        changed.loc[1, list(pvt.ROW_KEY)] = changed.loc[0, list(pvt.ROW_KEY)].to_numpy()
    elif fault == "duplicate_attempt":
        changed.loc[1, "finest_attempt_id"] = changed.loc[0, "finest_attempt_id"]
    elif fault == "missing_id":
        changed.loc[0, "point_id"] = None
    elif fault == "empty_id":
        changed.loc[0, "point_id"] = ""
    elif fault == "unexpected_label":
        changed.loc[0, "outcome_1ns"] = "pass"
    elif fault == "unknown_numeric":
        changed.loc[0, "numerically_qualified"] = False
    else:
        # A self-consistent alternative observation must still fail the fixed-count guard.
        i = changed.index[changed["mode"].eq("rc") & changed.outcome_1ns.eq("correct")][0]
        changed.loc[i, ["qp_at_deadline_v_1ns", "qn_at_deadline_v_1ns"]] = changed.loc[i, "vdd_v"]
        changed.loc[i, "decision_1ns"] = 0
        changed.loc[i, "outcome_1ns"] = "unresolved"
        changed.loc[i, "decision_time_ns_1ns"] = float("nan")
    with pytest.raises(ValueError):
        audit.audit(changed)


def test_notebook_table_matches_csv_audit_and_canonical_markdown(frame, monkeypatch):
    notebook = json.loads((pvt.ROOT / "Comparator_Atlas.ipynb").read_bytes())
    table = audit.markdown_table(audit.audit(frame))
    cells = [
        "".join(c["source"]) for c in notebook["cells"]
        if c["cell_type"] == "markdown" and "### Full-grid archived-deck outcomes" in "".join(c["source"])
    ]
    assert len(cells) == 1 and table in cells[0]
    assert "Each factor is a separate marginal partition of the same 180 RC points" in cells[0]
    assert "not a raw-waveform replay or evidence of physical causality" in cells[0]
    generated = []
    monkeypatch.setattr(build_entry_notebook.nbf, "write",
                        lambda document, destination: generated.append(document))
    build_entry_notebook.main()
    assert any(c.source == cells[0] for c in generated[0].cells)


def test_read_only_cli_outputs_the_same_table(frame, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["audit_pvt_failures", "--format", "markdown"])
    assert audit.main() == 0
    assert capsys.readouterr().out.rstrip() == audit.markdown_table(audit.audit(frame))


def test_cli_integrity_failure_is_nonzero(monkeypatch, capsys):
    def failed():
        raise RuntimeError("changed source checksum")
    monkeypatch.setattr(pvt, "load_results", failed)
    monkeypatch.setattr("sys.argv", ["audit_pvt_failures"])
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert not output.out and "FAILED" in output.err


def test_json_cli_binds_verified_source_and_lists_all_failed_identities(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["audit_pvt_failures"])
    assert audit.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["source_csv_sha256"] == pvt.REFERENCE_FILES["measurements.csv"]
    assert len(result["coverage"]) == 4
    assert len(result["marginals"]) == 15
    assert len(result["unresolved_1ns_records"]) == 24
    assert all(row["outcome_2ns"] == "correct" for row in result["unresolved_1ns_records"])
