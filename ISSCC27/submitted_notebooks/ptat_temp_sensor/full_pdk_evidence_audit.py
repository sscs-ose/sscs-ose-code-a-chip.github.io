#!/usr/bin/env python3
"""Fail-closed consistency audit for retained full-PDK evidence."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "full_pdk_20260926"


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise AuditError(f"missing retained evidence: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot parse retained evidence: {path}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{path}: expected JSON object")
    return value


def close(label: str, actual: float, expected: float) -> None:
    if not math.isclose(
        float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12
    ):
        raise AuditError(
            f"{label}: retained={actual!r}, release={expected!r}"
        )


def source_fingerprint(source: dict) -> tuple:
    required = (
        "artifact_id",
        "artifact_zip_sha256",
        "github_workflow_run_id",
        "source_commit",
    )
    missing = [key for key in required if not source.get(key)]
    if missing:
        raise AuditError(f"incomplete source provenance: {missing}")
    return tuple(source[key] for key in required)


def audit() -> dict:
    release = load_json(ROOT / "release_requirements.json")
    dense = load_json(RESULTS / "dense_pdk_analysis.json")
    mismatch = load_json(RESULTS / "mismatch_summary.json")
    holdout = load_json(RESULTS / "mismatch_calibration_holdout.json")

    dense_source = dense.get("source", {})
    mismatch_source = mismatch.get("source", {})
    holdout_source = holdout.get("source", {})
    fingerprint = source_fingerprint(dense_source)
    if source_fingerprint(mismatch_source) != fingerprint:
        raise AuditError("dense and mismatch evidence provenance disagree")
    if source_fingerprint(holdout_source) != fingerprint:
        raise AuditError("holdout and transistor evidence provenance disagree")

    policy = release["evidence_policy"]
    if not policy.get("new_results_must_name_tool_and_pdk_provenance"):
        raise AuditError("release evidence policy unexpectedly weakened")
    if dense_source.get("pdk_revision") != mismatch_source.get("pdk_revision"):
        raise AuditError("dense and mismatch PDK revisions disagree")
    if dense_source.get("ngspice") != mismatch_source.get("ngspice"):
        raise AuditError("dense and mismatch ngspice versions disagree")

    known = release["known_evidence"]
    dense_known = known["dense_grid_20260926"]
    dense_analysis = dense["analysis"]
    if dense_analysis.get("status") != "PASS":
        raise AuditError("retained dense characterization is not PASS")
    if dense_known.get("status") != dense_analysis.get("status"):
        raise AuditError("release dense status disagrees with retained evidence")
    close(
        "dense worst PWL error",
        dense_analysis["worst_five_point_pwl_max_abs_error_c"],
        dense_known["worst_five_point_pwl_max_abs_error_c"],
    )
    close(
        "dense temperature step",
        dense_analysis["max_temperature_step_c"],
        dense_known["temperature_step_c"],
    )
    if (
        int(dense_source["github_workflow_run_id"])
        != int(dense_known["source_workflow_run_id"])
    ):
        raise AuditError("release dense workflow provenance disagrees")

    mismatch_known = known["local_mismatch_20260926"]
    if mismatch.get("status") != "FAIL":
        raise AuditError("retained mismatch result must remain an explicit FAIL")
    if int(mismatch["samples"]) != int(mismatch_known["samples"]):
        raise AuditError("release mismatch sample count disagrees")
    close(
        "mismatch error yield",
        mismatch["yield_percent_error_le_target"],
        mismatch_known["error_yield_percent"],
    )
    close(
        "mismatch branch yield",
        mismatch["yield_percent_branch_mismatch_le_1pct"],
        mismatch_known["branch_mismatch_yield_percent_at_1pct"],
    )
    close(
        "mismatch p95 error",
        mismatch["max_abs_error_c"]["p95"],
        mismatch_known["p95_max_abs_error_c"],
    )
    close(
        "mismatch worst error",
        mismatch["max_abs_error_c"]["worst"],
        mismatch_known["worst_max_abs_error_c"],
    )
    if (
        int(mismatch_source["github_workflow_run_id"])
        != int(mismatch_known["source_workflow_run_id"])
    ):
        raise AuditError("release mismatch workflow provenance disagrees")

    candidate = known["six_point_candidate_20260926"]
    candidate_status = str(candidate.get("status", ""))
    if not candidate_status.endswith("NOT_RELEASE_VALIDATED"):
        raise AuditError("six-point candidate was promoted without new validation")
    anchors = [float(x) for x in candidate["calibration_anchors_c"]]
    if anchors == [
        float(x)
        for x in release["release_architecture"]["calibration_anchors_c"]
    ]:
        raise AuditError("candidate anchors unexpectedly equal release anchors")
    discovery = mismatch["six_point_candidate_study"]
    if [float(x) for x in discovery["anchors_c"]] != anchors:
        raise AuditError("discovery and release-record candidate anchors disagree")
    if [float(x) for x in holdout["fold_a_selected_anchors_c"]] != anchors:
        raise AuditError("fold A selected a different candidate schedule")
    if [float(x) for x in holdout["fold_b_selected_anchors_c"]] != anchors:
        raise AuditError("fold B selected a different candidate schedule")
    if holdout.get("same_schedule_selected_by_both_folds") is not True:
        raise AuditError("holdout folds did not select the same schedule")

    fold_a = holdout["fold_a_training"]
    fold_b = holdout["fold_b_holdout"]
    reverse = holdout["fold_a_reverse_holdout"]
    combined = holdout["combined_point_estimate_for_shared_schedule"]
    if int(fold_a["samples"]) != 50 or int(fold_b["samples"]) != 50:
        raise AuditError("holdout fold sizes must remain 50 samples each")
    if int(reverse["samples"]) != 50 or int(combined["samples"]) != 100:
        raise AuditError("holdout sample accounting is inconsistent")
    if holdout.get("status") != "PASS":
        raise AuditError("retained split-sample robustness study is not PASS")
    close(
        "fold A-to-B holdout yield",
        fold_b["yield_percent"],
        candidate["fold_a_to_b_holdout_yield_percent"],
    )
    close(
        "fold B-to-A holdout yield",
        reverse["yield_percent"],
        candidate["fold_b_to_a_holdout_yield_percent"],
    )
    close(
        "combined candidate yield",
        combined["yield_percent"],
        candidate["combined_point_yield_percent"],
    )
    retained_ci = [float(x) for x in combined["yield_wilson_95_percent_ci"]]
    release_ci = [float(x) for x in candidate["combined_wilson_95_percent_ci"]]
    if len(retained_ci) != 2 or len(release_ci) != 2:
        raise AuditError("invalid Wilson interval")
    for index, (actual, expected) in enumerate(zip(retained_ci, release_ci)):
        close(f"combined Wilson interval[{index}]", actual, expected)

    a_start, a_end = [int(x) for x in holdout["fold_a_train_seeds"]]
    b_start, b_end = [int(x) for x in holdout["fold_b_holdout_seeds"]]
    if not (a_start <= a_end < b_start <= b_end):
        raise AuditError("holdout seed folds are not disjoint and ordered")
    if (a_end - a_start + 1) != 50 or (b_end - b_start + 1) != 50:
        raise AuditError("holdout seed ranges do not each contain 50 seeds")

    return {
        "status": "PASS",
        "source_fingerprint": {
            "artifact_id": fingerprint[0],
            "artifact_zip_sha256": fingerprint[1],
            "github_workflow_run_id": fingerprint[2],
            "source_commit": fingerprint[3],
        },
        "dense_status": dense_analysis["status"],
        "mismatch_status": mismatch["status"],
        "candidate_status": candidate_status,
        "candidate_combined_yield_percent": combined["yield_percent"],
    }


def main() -> int:
    try:
        result = audit()
    except (AuditError, KeyError, TypeError, ValueError) as exc:
        print(f"FULL-PDK EVIDENCE AUDIT: FAIL\n{exc}")
        return 1
    print("FULL-PDK EVIDENCE AUDIT: PASS")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
