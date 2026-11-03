"""Independent, read-only arithmetic check of the ten published PVT waveforms.

Only Python's standard library is used. No producer measurement code is imported.
The fixed measurement contract is restated in REPRODUCIBILITY.md.
"""

from __future__ import annotations

import argparse
import ast
from bisect import bisect_right
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DATA = Path("results/study/postlayout_pvt45")
INDEX_SHA256 = "0860bdc0258e002abc0d633a12f1a1050122a7177bffb49091036f872b6390aa"
TABLE_SHA256 = "0710979ebc65c955a8d7071e5704e51a34ef9c03993ebe9138c7461d6856d9ca"
EVALUATION = 22.025e-9
CYCLE_START, CYCLE_END = 20e-9, 30e-9
MAX_BYTES = 16 * 1024 * 1024
TOLERANCE = 1e-11


class CheckError(ValueError):
    """Missing, malformed, relabeled or numerically inconsistent public evidence."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def checked_bytes(root: Path, relative: str, digest: str) -> bytes:
    parts = PurePosixPath(relative)
    require(
        not parts.is_absolute() and "\\" not in relative
        and ":" not in relative and ".." not in parts.parts,
        f"Unsafe artifact path: {relative}",
    )
    path = (root / Path(*parts.parts)).resolve()
    require(path.is_relative_to(root.resolve()), f"Artifact escapes root: {relative}")
    require(path.is_file(), f"Missing artifact: {relative}")
    require(path.stat().st_size <= MAX_BYTES, f"Oversized artifact: {relative}")
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == digest, f"SHA-256 mismatch: {relative}")
    return data


def read_waveform(data: bytes) -> list[tuple[float, ...]]:
    """Read only the bounded NPY 1.0 C-order float64 format in the public NPZs."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        require(len(members) == 1 and members[0].filename == "values.npy",
                "NPZ must contain exactly values.npy")
        require(members[0].file_size <= MAX_BYTES, "Oversized NPY member")
        raw = archive.read(members[0])
    require(raw[:8] == b"\x93NUMPY\x01\x00", "Expected NPY 1.0")
    require(len(raw) >= 10, "Truncated NPY header")
    header_size = struct.unpack_from("<H", raw, 8)[0]
    require(header_size <= 4096 and 10 + header_size <= len(raw), "Invalid NPY header size")
    header = ast.literal_eval(raw[10:10 + header_size].decode("ascii").strip())
    require(isinstance(header, dict) and set(header) == {"descr", "fortran_order", "shape"},
            "Unexpected NPY header fields")
    require(header["descr"] == "<f8" and header["fortran_order"] is False,
            "Expected little-endian C-order float64; object arrays are not supported")
    shape = header["shape"]
    require(isinstance(shape, tuple) and len(shape) == 2
            and all(type(n) is int for n in shape)
            and 10 <= shape[0] <= 100000 and shape[1] == 9,
            "Expected 10..100000 rows and nine columns")
    payload = raw[10 + header_size:]
    require(len(payload) == shape[0] * 9 * 8, "NPY payload size does not match shape")
    rows = list(struct.iter_unpack("<9d", payload))
    validate_rows(rows)
    return rows


def validate_rows(rows: list[tuple[float, ...]]) -> None:
    require(len(rows) >= 10 and all(len(row) == 9 for row in rows), "Invalid waveform shape")
    require(all(math.isfinite(x) for row in rows for x in row), "Non-finite waveform")
    require(all(a[0] < b[0] for a, b in zip(rows, rows[1:])), "Time is not strictly increasing")
    require(rows[0][0] <= CYCLE_START and rows[-1][0] >= CYCLE_END - 1e-15,
            "Waveform does not cover the full 20-30 ns cycle")


def recompute(rows: list[tuple[float, ...]], vdd: float, differential: float,
              deadline: int) -> dict:
    """Scalar interpolation, stable-suffix latency and interval-by-interval energy."""
    validate_rows(rows)
    require(math.isfinite(vdd) and vdd > 0 and math.isfinite(differential),
            "Invalid supply or differential input")
    require(type(deadline) is int and deadline in (1, 2), "Only the 1/2 ns checks are defined")
    times = [row[0] for row in rows]

    def at(time: float, column: int) -> float:
        right = bisect_right(times, time)
        if right == 0:
            return rows[0][column]
        if right == len(times):
            return rows[-1][column]
        left = right - 1
        slope = (rows[right][column] - rows[left][column]) / (times[right] - times[left])
        return rows[left][column] + slope * (time - times[left])

    reset = EVALUATION - 100e-12
    require(all(at(reset, column) >= 0.9 * vdd for column in (2, 3, 4, 5)),
            "Reset qualification failed")
    stop = EVALUATION + deadline * 1e-9
    qp, qn = at(stop, 2), at(stop, 3)
    decision = 0
    if qp >= 0.8 * vdd and qn <= 0.2 * vdd:
        decision = 1
    elif qn >= 0.8 * vdd and qp <= 0.2 * vdd:
        decision = -1
    outcome = "unresolved" if not decision else (
        "reference" if differential == 0 else
        "correct" if decision == (1 if differential > 0 else -1) else "wrong"
    )
    latency = None
    if decision:
        high, low = (2, 3) if decision == 1 else (3, 2)
        candidates = [EVALUATION] + [t for t in times if EVALUATION <= t < stop] + [stop]
        earliest = stop
        # Walk the final valid suffix backwards; an early glitch cannot count.
        for time in reversed(candidates):
            if at(time, high) < 0.8 * vdd or at(time, low) > 0.2 * vdd:
                break
            earliest = time
        latency = (earliest - EVALUATION) * 1e9
    boundaries = [CYCLE_START] + [t for t in times if CYCLE_START < t < CYCLE_END] + [CYCLE_END]
    charge = math.fsum(
        (end - start) * (at(start, 6) + at(end, 6)) / 2
        for start, end in zip(boundaries, boundaries[1:])
    )
    energy = -vdd * charge * 1e15
    require(energy >= -1e-3, "Unexpected negative net rail energy")
    return {
        "deadline_ns": deadline, "decision": decision, "outcome": outcome,
        "decision_time_ns": latency, "core_energy_fj": energy, "reset_ok": True,
        "qp_at_deadline_v": qp, "qn_at_deadline_v": qn,
    }


def check_identity(example: dict, review: dict, original: dict, table: dict) -> None:
    attempt = example["attempt_id"]
    require(re.fullmatch(r"a[0-9]{4}-[0-9a-f]{24}", attempt) is not None, "Invalid attempt identity")
    run = example["point_run_identity"]
    require(re.fullmatch(r"[0-9a-f]{64}", run) is not None
            and attempt.split("-")[1] == run[:24], "Attempt/run identity mismatch")
    for key, expected in (
        ("attempt_id", attempt), ("run_identity", run),
        ("point_id", example["point_id"]), ("mode", example["mode"]),
    ):
        require(review[key] == original[key] == expected, f"Metadata identity mismatch: {key}")
    require(review["status"] == example["linked_review_status"] == "success"
            and original["status"] == example["original_metadata_status"],
            "Original collector status was relabeled")
    require(review["measurements"] == original["measurements"], "Collector changed measurements")
    point = review["point"]
    require(point == original["point"], "Collector changed physical point")
    require(review["physical_identity"] == original["physical_identity"], "Physical identity changed")
    physical = review["physical_identity"]
    require(physical["mode"] == example["mode"] and physical["point_id"] == example["point_id"]
            and physical["point"] == {k: v for k, v in point.items() if k != "max_step_ps"},
            "Physical identity/point mismatch")
    require(review["geometry_device_count"] == 27 and review["reset_ok"] is True,
            "Missing 27-device/reset evidence")
    for key, expected in (
        ("trim_code", 0), ("pair_skew", 0), ("max_step_ps", 5),
        ("common_mode_ratio", 0.5), ("load_ff", 5),
    ):
        require(point[key] == expected, f"Point violates fixed contract: {key}")
    require(example["step_ps"] == review["max_step_ps"] == 5, "Wrong timestep identity")
    for key in ("corner", "vdd_v", "temperature_c"):
        require(point[key] == example[key], f"Index/point mismatch: {key}")
    require(math.isclose(point["differential_v"] * 1000, example["differential_mv"],
                         rel_tol=0, abs_tol=1e-12), "Index/input identity mismatch")
    for key, expected in (
        ("finest_attempt_id", attempt), ("run_identity", run),
        ("point_id", example["point_id"]), ("mode", example["mode"]), ("corner", point["corner"]),
    ):
        require(table[key] == expected, f"Table identity mismatch: {key}")
    for key, expected in (
        ("vdd_v", point["vdd_v"]), ("temperature_c", point["temperature_c"]),
        ("differential_mv", example["differential_mv"]), ("finest_step_ps", 5),
        ("trim_code", 0), ("pair_skew", 0), ("common_mode_ratio", 0.5),
        ("output_load_ff_each", 5),
    ):
        require(float(table[key]) == expected, f"Table point mismatch: {key}")


def compare(actual: dict, expected: dict, context: str) -> dict:
    require(actual.keys() == expected.keys(), f"Measurement fields differ: {context}")
    differences = {}
    for key, value in actual.items():
        reference = expected[key]
        if type(value) is float:
            require(type(reference) in (float, int) and math.isfinite(reference)
                    and math.isclose(value, reference, rel_tol=TOLERANCE, abs_tol=TOLERANCE),
                    f"Measurement mismatch: {context}/{key}")
            differences[key] = abs(value - reference)
        else:
            require(value == reference and (type(value) is not bool or type(reference) is bool),
                    f"Measurement mismatch: {context}/{key}")
    return differences


def check(entry: Path = ROOT) -> dict:
    directory = entry / DATA
    traces = directory / "representative-traces"
    index = json.loads(checked_bytes(traces, "review-index.json", INDEX_SHA256))
    table_bytes = checked_bytes(directory, "measurements.csv", TABLE_SHA256)
    table = list(csv.DictReader(io.StringIO(table_bytes.decode("utf-8"))))
    examples = index["examples"]
    require(len(examples) == 10 and len({e["attempt_id"] for e in examples}) == 10,
            "Expected ten distinct representative traces")
    require(len(index["artifact_sha256"]) == 60, "Incomplete representative artifact inventory")
    artifacts = {
        name: checked_bytes(traces, name, digest)
        for name, digest in index["artifact_sha256"].items()
    }
    observations = []
    for example in examples:
        attempt = example["attempt_id"]
        original_bytes = artifacts[f"{attempt}/metadata.json"]
        original = json.loads(original_bytes)
        review = json.loads(artifacts[f"{attempt}/collector-review.json"])
        require(hashlib.sha256(original_bytes).hexdigest() == review["original_metadata_sha256"],
                "Collector is not bound to original metadata")
        matches = [row for row in table if row["finest_attempt_id"] == attempt]
        require(len(matches) == 1, "Missing or duplicate representative table identity")
        row = matches[0]
        check_identity(example, review, original, row)
        waveform = read_waveform(artifacts[f"{attempt}/waveform.npz"])
        for deadline in (1, 2):
            measured = recompute(waveform, review["point"]["vdd_v"],
                                 review["point"]["differential_v"], deadline)
            archived = [m for m in review["measurements"] if m["deadline_ns"] == deadline]
            require(len(archived) == 1, "Missing or duplicate archived deadline")
            collector_delta = compare(measured, archived[0], f"{attempt}/{deadline}ns/collector")
            expected = {
                "deadline_ns": deadline, "decision": int(row[f"decision_{deadline}ns"]),
                "outcome": row[f"outcome_{deadline}ns"], "reset_ok": row["reset_ok"] == "True",
                "decision_time_ns": (
                    float(row[f"decision_time_ns_{deadline}ns"])
                    if row[f"decision_time_ns_{deadline}ns"] else None
                ),
                "core_energy_fj": float(row["core_energy_fj"]),
                "qp_at_deadline_v": float(row[f"qp_at_deadline_v_{deadline}ns"]),
                "qn_at_deadline_v": float(row[f"qn_at_deadline_v_{deadline}ns"]),
            }
            table_delta = compare(measured, expected, f"{attempt}/{deadline}ns/table")
            observations.append({
                "attempt_id": attempt, "point_id": example["point_id"], "mode": example["mode"],
                "run_identity": example["point_run_identity"],
                "waveform_sha256": index["artifact_sha256"][f"{attempt}/waveform.npz"],
                "measured": measured, "collector_absolute_differences": collector_delta,
                "table_absolute_differences": table_delta,
            })
    return {
        "status": "pass", "scope": "ten_public_traces_twenty_deadline_observations_only",
        "independence": "separate_arithmetic_implementation_not_independent_physical_evidence",
        "selection": "existing_representative_examples_not_random_or_held_out",
        "fresh_simulations": 0, "full_720_replay": False, "rc_model_physical_fidelity_qualified": False,
        "trace_count": len(examples), "observation_count": len(observations),
        "index_sha256": INDEX_SHA256, "table_sha256": TABLE_SHA256,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "relative_tolerance": TOLERANCE, "absolute_tolerance_in_each_reported_unit": TOLERANCE,
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", type=Path, default=ROOT, help="Complete public entry directory")
    args = parser.parse_args()
    try:
        result = check(args.entry)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError,
            zipfile.BadZipFile, struct.error) as error:
        print(f"Public-waveform check FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
