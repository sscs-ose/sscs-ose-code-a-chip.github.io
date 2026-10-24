import ast
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

import pytest

from scripts import check_public_waveforms as checker


def synthetic_rows():
    times = [19e-9, 20.5e-9, 21e-9, 21.5e-9, 22e-9, checker.EVALUATION]
    times += [checker.EVALUATION + n * 1e-9 for n in (0.1, 0.2, 0.3, 0.6, 0.7, 1, 2)]
    times += [28e-9, 31e-9]
    return [
        (t, 0, 1, 0 if t >= checker.EVALUATION + 0.6e-9 else 1, 1, 1, -2e-6, 0.5, 0.5)
        for t in times
    ]


def npz(rows, *, descriptor="<f8", order=False, version=b"\x01\x00"):
    header = repr({"descr": descriptor, "fortran_order": order, "shape": (len(rows), 9)}).encode()
    raw = b"\x93NUMPY" + version + struct.pack("<H", len(header)) + header
    raw += b"".join(struct.pack("<9d", *row) for row in rows)
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("values.npy", raw)
    return data.getvalue()


def test_scalar_contract_with_analytic_energy_and_sampled_latency():
    rows = checker.read_waveform(npz(synthetic_rows()))
    for deadline in (1, 2):
        observed = checker.recompute(rows, 1, 0.003, deadline)
        assert observed["outcome"] == "correct"
        assert observed["decision"] == 1
        assert observed["decision_time_ns"] == pytest.approx(0.6, abs=1e-14)
        assert observed["core_energy_fj"] == pytest.approx(20, abs=1e-13)
        assert observed["qp_at_deadline_v"] == 1
        assert observed["qn_at_deadline_v"] == 0


def test_full_cycle_trapezoids_insert_endpoints_and_ignore_deadline():
    rows = [
        row[:6] + (-1e-6 * (1 + (row[0] - 20e-9) / 10e-9),) + row[7:]
        for row in synthetic_rows()
    ]
    assert all(row[0] not in (20e-9, 30e-9) for row in rows)
    for deadline in (1, 2):
        assert checker.recompute(rows, 1, 0.003, deadline)["core_energy_fj"] == pytest.approx(15)


def test_deadline_voltages_are_linearly_interpolated():
    stop = checker.EVALUATION + 1e-9
    rows = []
    for row in synthetic_rows():
        if row[0] == stop:
            continue
        if row[0] >= checker.EVALUATION:
            qn = max(0, 0.4 * (1.2 - (row[0] - checker.EVALUATION) / 1e-9))
            row = row[:3] + (qn,) + row[4:]
        rows.append(row)
    # Add a point above the deadline so the surrounding segment is a known ramp.
    right = checker.EVALUATION + 1.2e-9
    rows.append((right, 0, 1, 0, 1, 1, -2e-6, 0.5, 0.5))
    rows.sort()
    observed = checker.recompute(rows, 1, 0.003, 1)
    assert observed["qp_at_deadline_v"] == 1
    assert observed["qn_at_deadline_v"] == pytest.approx(0.08, abs=1e-14)
    assert observed["outcome"] == "correct"


def test_early_glitch_is_not_a_stable_decision():
    rows = synthetic_rows()
    early = next(i for i, row in enumerate(rows) if row[0] == checker.EVALUATION + 0.1e-9)
    rows[early] = rows[early][:3] + (0,) + rows[early][4:]
    assert checker.recompute(rows, 1, 0.003, 1)["decision_time_ns"] == pytest.approx(0.6)


@pytest.mark.parametrize("qp,qn,outcome,decision", [
    (0.8, 0.2, "correct", 1),
    (0.2, 0.8, "wrong", -1),
    (0.8, 0.21, "unresolved", 0),
    (0.79, 0.2, "unresolved", 0),
])
def test_both_complementary_rails_are_required(qp, qn, outcome, decision):
    rows = [
        row[:2] + (qp, qn) + row[4:] if row[0] >= checker.EVALUATION else row
        for row in synthetic_rows()
    ]
    observed = checker.recompute(rows, 1, 0.003, 1)
    assert (observed["outcome"], observed["decision"]) == (outcome, decision)
    assert (observed["decision_time_ns"] is None) == (decision == 0)


def test_negative_input_polarity_and_zero_reference():
    rows = [row[:2] + (row[3], row[2]) + row[4:] for row in synthetic_rows()]
    assert checker.recompute(rows, 1, -0.003, 1)["outcome"] == "correct"
    assert checker.recompute(rows, 1, 0, 1)["outcome"] == "reference"


@pytest.mark.parametrize("fault,message", [
    ("reset", "Reset"), ("nan", "Non-finite"), ("duplicate", "strictly increasing"),
    ("truncated", "full 20-30"), ("energy", "negative net"),
])
def test_invalid_waveforms_fail_closed(fault, message):
    rows = synthetic_rows()
    if fault == "reset":
        rows = [row[:4] + (0,) + row[5:] for row in rows]
    elif fault == "nan":
        rows[0] = rows[0][:6] + (float("nan"),) + rows[0][7:]
    elif fault == "duplicate":
        rows[1] = rows[0]
    elif fault == "truncated":
        rows = rows[:-1]
    else:
        rows = [row[:6] + (2e-6,) + row[7:] for row in rows]
    with pytest.raises(checker.CheckError, match=message):
        checker.recompute(rows, 1, 0.003, 1)


@pytest.mark.parametrize("options,message", [
    ({"descriptor": "|O"}, "float64"), ({"order": True}, "C-order"),
    ({"version": b"\x02\x00"}, "NPY 1.0"),
])
def test_unsupported_npy_formats_are_rejected(options, message):
    with pytest.raises(checker.CheckError, match=message):
        checker.read_waveform(npz(synthetic_rows(), **options))


def test_shape_and_archive_members_are_not_silently_ignored():
    raw = npz(synthetic_rows())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        member = archive.read("values.npy")
    for payload, name in ((member[:-8], "values.npy"), (member, "../values.npy")):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(name, payload)
        with pytest.raises(checker.CheckError):
            checker.read_waveform(output.getvalue())


@pytest.fixture
def copied_evidence(tmp_path):
    source = checker.ROOT / checker.DATA
    target = tmp_path / checker.DATA
    index = json.loads((source / "representative-traces" / "review-index.json").read_bytes())
    names = ["measurements.csv", "representative-traces/review-index.json"]
    names += ["representative-traces/" + name for name in index["artifact_sha256"]]
    for name in names:
        destination = target / Path(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / Path(name), destination)
    return tmp_path


@pytest.mark.parametrize("fault,message", [
    ("missing", "Missing artifact"), ("trace", "SHA-256 mismatch"),
    ("index", "SHA-256 mismatch"), ("table", "SHA-256 mismatch"),
])
def test_public_artifact_tampering_and_missing_trace_fail_closed(copied_evidence, fault, message):
    directory = copied_evidence / checker.DATA
    index_path = directory / "representative-traces" / "review-index.json"
    index = json.loads(index_path.read_bytes())
    trace = directory / "representative-traces" / index["examples"][0]["attempt_id"] / "waveform.npz"
    target = {"missing": trace, "trace": trace, "index": index_path,
              "table": directory / "measurements.csv"}[fault]
    if fault == "missing":
        target.unlink()
    else:
        target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(checker.CheckError, match=message):
        checker.check(copied_evidence)


@pytest.mark.parametrize("fault", ["run", "mode", "polarity", "status"])
def test_semantic_identity_checks_reject_relabeling_even_before_measurement(fault):
    directory = checker.ROOT / checker.DATA
    index = json.loads((directory / "representative-traces" / "review-index.json").read_bytes())
    example = copy.deepcopy(index["examples"][0])
    run = directory / "representative-traces" / example["attempt_id"]
    review = json.loads((run / "collector-review.json").read_bytes())
    original = json.loads((run / "metadata.json").read_bytes())
    if fault == "run":
        example["point_run_identity"] = "0" * 64
    elif fault == "mode":
        example["mode"] = "rc"
    elif fault == "polarity":
        example["differential_mv"] *= -1
    else:
        example["original_metadata_status"] = "success"
    with pytest.raises(checker.CheckError, match="identity|status"):
        checker.check_identity(example, review, original, {})


def test_changed_measurement_labels_and_numbers_are_not_accepted():
    observed = checker.recompute(synthetic_rows(), 1, 0.003, 1)
    for field, wrong in (("outcome", "unresolved"), ("decision_time_ns", None),
                         ("core_energy_fj", 21), ("qp_at_deadline_v", 0.79)):
        expected = {**observed, field: wrong}
        with pytest.raises(checker.CheckError, match="Measurement mismatch"):
            checker.compare(observed, expected, "synthetic")


def test_table_identity_cannot_be_swapped_between_public_examples():
    directory = checker.ROOT / checker.DATA
    index = json.loads((directory / "representative-traces" / "review-index.json").read_bytes())
    example = index["examples"][0]
    run = directory / "representative-traces" / example["attempt_id"]
    review = json.loads((run / "collector-review.json").read_bytes())
    original = json.loads((run / "metadata.json").read_bytes())
    with (directory / "measurements.csv").open(newline="", encoding="utf-8") as source:
        row = next(r for r in csv.DictReader(source) if r["finest_attempt_id"] == example["attempt_id"])
    checker.check_identity(example, review, original, row)
    row["finest_attempt_id"] = index["examples"][1]["attempt_id"]
    with pytest.raises(checker.CheckError, match="Table identity"):
        checker.check_identity(example, review, original, row)


def test_artifact_path_cannot_escape_root(tmp_path):
    with pytest.raises(checker.CheckError, match="Unsafe artifact"):
        checker.checked_bytes(tmp_path, "../outside", "0" * 64)


def test_public_cli_without_site_packages_and_without_producer_imports():
    script = Path(checker.__file__)
    imports = []
    for node in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imports += [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module.split(".")[0])
    assert set(imports) <= sys.stdlib_module_names
    assert not set(imports) & {"subprocess", "socket", "urllib", "comparator_atlas", "numpy"}
    process = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(script)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    report = json.loads(process.stdout)
    assert report["status"] == "pass"
    assert (report["trace_count"], report["observation_count"]) == (10, 20)
    assert report["fresh_simulations"] == 0
    assert report["full_720_replay"] is False
    assert report["rc_model_physical_fidelity_qualified"] is False
    assert report["checker_sha256"] == hashlib.sha256(script.read_bytes()).hexdigest()
    observations = report["observations"]
    first = [o["measured"] for o in observations if o["measured"]["deadline_ns"] == 1]
    second = [o["measured"] for o in observations if o["measured"]["deadline_ns"] == 2]
    assert sum(m["outcome"] == "unresolved" for m in first) == 2
    assert sum(m["outcome"] == "correct" for m in first) == 8
    assert all(m["outcome"] == "correct" for m in second)
    assert max(m["decision_time_ns"] for m in second) == pytest.approx(1.8350324672430902)
    assert len({o["attempt_id"] for o in observations}) == 10


def test_cli_failure_is_nonzero_and_not_a_success_report(tmp_path):
    process = subprocess.run(
        [sys.executable, "-I", "-S", "-B", checker.__file__, "--entry", str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 1
    assert not process.stdout
    assert "FAILED: Missing artifact" in process.stderr
