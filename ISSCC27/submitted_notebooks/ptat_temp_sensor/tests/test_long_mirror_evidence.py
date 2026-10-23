"""Reject mixed or corrupted retained candidate evidence."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import long_mirror_evidence_audit as audit


def test_retained_long_mirror_evidence_recomputes():
    result = audit.audit()
    assert result["status"] == "PASS"
    assert result["raw_simulations_checked"] == 118


@pytest.mark.parametrize("corruption", ["archive", "geometry", "validation_seed"])
def test_corrupted_or_mixed_candidate_evidence_is_rejected(tmp_path, corruption):
    for name in ("raw_evidence.tar.gz", "manifest.json", "sizing_summary.json",
                 "dense_analysis.json", "readout_analysis.json", "qualification.json"):
        shutil.copyfile(audit.RESULTS / name, tmp_path / name)
    if corruption == "archive":
        with (tmp_path / "raw_evidence.tar.gz").open("ab") as stream:
            stream.write(b"corrupt")
        message = "archive hash"
    else:
        path = tmp_path / "sizing_summary.json"
        data = json.loads(path.read_text())
        if corruption == "geometry":
            data["recommended_for_independent_validation"]["mirror_length_multiplier"] = 1
            message = "geometry"
        else:
            data["independent_validation"]["seed_start"] = 9001
            message = "seed mismatch"
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=message):
        audit.audit(tmp_path)
