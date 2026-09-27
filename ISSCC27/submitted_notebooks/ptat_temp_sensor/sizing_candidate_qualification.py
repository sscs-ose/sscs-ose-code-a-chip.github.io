#!/usr/bin/env python3
"""Combine sizing-screen, independent mismatch, and dense-corner evidence.

The tool produces a machine-readable promotion recommendation. It never edits
release_requirements.json and therefore cannot silently promote an exploratory
candidate into the release architecture.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import seed_policy

ROOT = Path(__file__).resolve().parent

PROVENANCE_KEYS = (
    "ngspice",
    "ngspice_compatibility_mode",
    "pdk_revision",
    "model_sha256",
    "design_requirements_sha256",
)


class QualificationError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise QualificationError(f"missing evidence file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationError(f"cannot parse evidence file: {path}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{path}: expected JSON object")
    return value


def close(label: str, actual: float, expected: float) -> None:
    if not math.isclose(
        float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-15
    ):
        raise QualificationError(
            f"{label}: dense={actual!r}, selected={expected!r}"
        )


def require_matching_provenance(sweep: dict, metadata: dict) -> dict:
    sweep_provenance = sweep.get("provenance")
    if not isinstance(sweep_provenance, dict):
        raise QualificationError("sizing sweep is missing provenance")

    missing_sweep = [
        key for key in PROVENANCE_KEYS if not sweep_provenance.get(key)
    ]
    missing_dense = [
        key for key in PROVENANCE_KEYS if not metadata.get(key)
    ]
    if missing_sweep:
        raise QualificationError(
            f"sizing sweep provenance is incomplete: {missing_sweep}"
        )
    if missing_dense:
        raise QualificationError(
            f"dense-run provenance is incomplete: {missing_dense}"
        )

    for key in PROVENANCE_KEYS:
        if sweep_provenance[key] != metadata[key]:
            raise QualificationError(
                f"{key} provenance mismatch: "
                f"sweep={sweep_provenance[key]!r}, dense={metadata[key]!r}"
            )

    return {key: sweep_provenance[key] for key in PROVENANCE_KEYS}


def require_readout_provenance(
    readout: dict, metadata: dict
) -> dict:
    provenance = readout.get("provenance")
    if not isinstance(provenance, dict):
        raise QualificationError("candidate readout is missing provenance")
    missing = [key for key in PROVENANCE_KEYS if not provenance.get(key)]
    if missing:
        raise QualificationError(
            f"candidate readout provenance is incomplete: {missing}"
        )
    for key in PROVENANCE_KEYS:
        if provenance[key] != metadata.get(key):
            raise QualificationError(
                f"readout {key} provenance mismatch: "
                f"readout={provenance[key]!r}, dense={metadata.get(key)!r}"
            )
    return {key: provenance[key] for key in PROVENANCE_KEYS}


def number(label: str, value: object, *, minimum: float = 0.0,
           maximum: float = math.inf) -> float:
    """Reject malformed metrics before comparing them with release targets."""
    if isinstance(value, bool):
        raise QualificationError(f"{label}: expected a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise QualificationError(f"{label}: expected a finite number") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise QualificationError(f"{label}: invalid numeric value {value!r}")
    return result


def positive_integer(label: str, value: object) -> int:
    result = number(label, value, minimum=1.0)
    if not result.is_integer():
        raise QualificationError(f"{label}: expected a positive integer")
    return int(result)


def analyze(
    sweep: dict,
    dense: dict | None,
    metadata: dict | None,
    readout: dict | None,
    nominal_reference_current_a: float,
) -> dict:
    selected = sweep.get("recommended_for_independent_validation")
    validation = sweep.get("independent_validation")

    if selected is None:
        if validation is not None:
            raise QualificationError(
                "independent validation exists without a selected candidate"
            )
        return {
            "status": "NO_HEADROOM_QUALIFIED_CANDIDATE",
            "qualified_for_release_review": False,
            "release_architecture_changed": False,
            "reason": "sizing screen found no headroom-qualified candidate",
        }

    if selected.get("headroom_pass") is not True:
        raise QualificationError("selected candidate did not pass headroom gate")
    if validation is None:
        raise QualificationError("selected candidate lacks independent validation")
    if validation.get("candidate") != selected.get("candidate"):
        raise QualificationError("validation candidate differs from selected candidate")
    if dense is None or metadata is None:
        raise QualificationError("selected candidate lacks dense-corner evidence")
    if readout is None:
        raise QualificationError("selected candidate lacks readout evidence")

    expected_iref = (
        float(nominal_reference_current_a) * float(selected["iref_scale"])
    )
    operating = metadata.get("operating_point", {})
    close(
        "reference current",
        operating["reference_current_a"],
        expected_iref,
    )
    close(
        "ideal branch current",
        operating["branch_current_a"],
        expected_iref,
    )
    close(
        "sensor linear scale",
        metadata["sensor_linear_scale"],
        selected["sensor_linear_scale"],
    )
    close(
        "mirror linear scale",
        metadata["mirror_linear_scale"],
        selected["mirror_linear_scale"],
    )
    provenance = require_matching_provenance(sweep, metadata)
    readout_provenance = require_readout_provenance(readout, metadata)

    # PASS labels are insufficient: reapply the current release contract to
    # the retained numbers and the actual discovery/validation seed ranges.
    release = load_json(ROOT / "release_requirements.json")
    design = load_json(ROOT / "design_requirements.json")
    targets = release["release_targets"]
    samples = positive_integer("validation samples", validation["samples"])
    validation_start = positive_integer(
        "validation seed start", validation["seed_start"]
    )
    screen_samples = positive_integer(
        "screening samples", sweep["samples_per_candidate"]
    )
    screen_start = positive_integer("screening seed start", sweep["seed_start"])
    independent_seeds = (
        screen_start + screen_samples <= validation_start
        or validation_start + samples <= screen_start
    )
    excluded_ranges = list(seed_policy.PREVIOUSLY_EXAMINED_SEED_RANGES)
    recorded_ranges = sweep.get("validation_excluded_seed_ranges", [])
    if not isinstance(recorded_ranges, list):
        raise QualificationError("invalid examined seed-range evidence")
    for recorded in recorded_ranges:
        if recorded not in excluded_ranges:
            excluded_ranges.append(recorded)
    try:
        historical_conflicts = seed_policy.validation_conflicts(
            validation_start, samples, excluded_ranges
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise QualificationError("invalid examined seed-range evidence") from exc
    unseen_validation_seeds = not historical_conflicts
    error_yield = number(
        "error yield", validation["error_yield_percent"], maximum=100.0
    )
    branch_yield = number(
        "branch yield", validation["branch_yield_percent"], maximum=100.0
    )
    headroom = number(
        "validation headroom", validation["min_sensor_headroom_v"],
        minimum=-math.inf,
    )
    worst_error = number(
        "dense PWL error",
        dense["worst_pwl_max_abs_error_c"]
        if "worst_pwl_max_abs_error_c" in dense
        else dense["worst_five_point_pwl_max_abs_error_c"],
    )
    worst_branch = number(
        "dense branch mismatch", dense["worst_mirror_branch_mismatch_percent"]
    )
    grid_step = number("dense grid step", dense["max_temperature_step_c"])
    mismatch_pass = (
        validation.get("status") == "PASS"
        and samples >= targets["mismatch_min_samples"]
        and independent_seeds
        and unseen_validation_seeds
        and error_yield >= targets["mismatch_target_yield_percent"]
        and branch_yield >= targets["mismatch_target_yield_percent"]
    )
    validation_headroom_pass = (
        validation.get("headroom_pass") is True
        and headroom >= design["headroom_guardband_v_min"]
    )
    dense_pass = (
        dense.get("status") == "PASS"
        and worst_error <= targets["dense_grid_pwl_max_abs_error_c_max"]
        and worst_branch <= design["mirror_branch_mismatch_percent_max"]
        and 0.0 < grid_step <= targets["dense_grid_step_c_max"]
        and dense.get("anchors_c")
        == release["release_architecture"]["calibration_anchors_c"]
    )
    readout_bits = positive_integer("readout bits", readout["bits"])
    readout_vref = number("readout VREF", readout["vref_v"])
    readout_gain = number("readout analog gain", readout["analog_gain"])
    readout_qrms = number(
        "readout quantization RMS",
        readout["worst_quantization_rms_c"],
    )
    readout_utilization = number(
        "readout full-scale utilization",
        readout["worst_full_scale_utilization"],
    )
    readout_error = number(
        "readout quantized PWL error",
        readout["worst_quantized_pwl_sampled_error_c"],
    )
    readout_pass = (
        readout.get("status") == "PASS"
        and readout.get("anchors_c")
        == release["release_architecture"]["calibration_anchors_c"]
        and readout_bits == int(design["adc"]["bits"])
        and math.isclose(
            readout_vref,
            float(design["adc"]["vref_v"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and math.isclose(
            readout_gain,
            float(release["release_architecture"]["analog_gain"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and readout_qrms
        <= float(targets["adc_quantization_rms_c_max"])
        and readout_utilization
        <= float(targets["adc_full_scale_utilization_max"])
        and readout_error
        <= float(
            targets["quantized_sampled_grid_pwl_max_abs_error_c_max"]
        )
    )
    qualified = bool(
        mismatch_pass
        and validation_headroom_pass
        and dense_pass
        and readout_pass
    )

    return {
        "status": (
            "QUALIFIED_FOR_RELEASE_REVIEW"
            if qualified
            else "NOT_QUALIFIED_FOR_RELEASE_REVIEW"
        ),
        "qualified_for_release_review": qualified,
        "release_architecture_changed": False,
        "candidate": selected["candidate"],
        "geometry": {
            "sensor_linear_scale": float(selected["sensor_linear_scale"]),
            "mirror_linear_scale": float(selected["mirror_linear_scale"]),
        },
        "operating_point": {
            "reference_current_a": expected_iref,
            "branch_current_a": expected_iref,
            "vdd_v": float(operating["vdd_v"]),
        },
        "independent_mismatch": {
            "status": validation.get("status"),
            "samples": samples,
            "seed_start": validation_start,
            "error_yield_percent": error_yield,
            "branch_yield_percent": branch_yield,
            "headroom_pass": validation_headroom_pass,
            "min_sensor_headroom_v": headroom,
        },
        "qualification_components": {
            "independent_mismatch_pass": mismatch_pass,
            "disjoint_validation_seeds": independent_seeds,
            "unseen_validation_seeds": unseen_validation_seeds,
            "independent_headroom_pass": validation_headroom_pass,
            "dense_tt_ff_ss_pass": dense_pass,
            "readout_pass": readout_pass,
            "provenance_match": True,
            "readout_provenance_match": readout_provenance == provenance,
        },
        "provenance": provenance,
        "validation_excluded_seed_ranges": excluded_ranges,
        "validation_seed_conflicts": historical_conflicts,
        "readout": {
            "status": readout.get("status"),
            "bits": readout_bits,
            "vref_v": readout_vref,
            "analog_gain": readout_gain,
            "worst_quantization_rms_c": readout_qrms,
            "worst_full_scale_utilization": readout_utilization,
            "worst_quantized_pwl_sampled_error_c": readout_error,
        },
        "dense_tt_ff_ss": {
            "status": dense.get("status"),
            "anchors_c": dense.get("anchors_c"),
            "worst_pwl_max_abs_error_c": worst_error,
            "worst_mirror_branch_mismatch_percent": worst_branch,
            "max_temperature_step_c": grid_step,
        },
        "evidence_boundary": (
            "Qualification is simulation-only. PASS makes the candidate eligible "
            "for explicit release review; this tool never changes the release "
            "architecture or creates silicon/layout claims."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sweep-summary",
        type=Path,
        default=ROOT / "results" / "mismatch_sizing_sweep" / "summary.json",
    )
    parser.add_argument(
        "--dense-analysis",
        type=Path,
        default=ROOT / "results" / "dense_sizing_candidate_analysis.json",
    )
    parser.add_argument(
        "--dense-metadata",
        type=Path,
        default=ROOT / "results" / "dense_sizing_candidate" / "run_metadata.json",
    )
    parser.add_argument(
        "--readout-analysis",
        type=Path,
        default=ROOT / "results" / "dense_sizing_candidate_readout.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "sizing_candidate_qualification.json",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="return nonzero when the candidate is validly evaluated but not qualified",
    )
    args = parser.parse_args()

    try:
        sweep = load_json(args.sweep_summary)
        design = load_json(ROOT / "design_requirements.json")
        selected = sweep.get("recommended_for_independent_validation")
        dense = load_json(args.dense_analysis) if selected is not None else None
        metadata = load_json(args.dense_metadata) if selected is not None else None
        readout = (
            load_json(args.readout_analysis)
            if selected is not None
            else None
        )
        nominal_iref = float(
            design["nominal_characterization_seed"]["reference_current_a"]
        )
        result = analyze(
            sweep, dense, metadata, readout, nominal_iref
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (QualificationError, KeyError, TypeError, ValueError) as exc:
        print(f"SIZING CANDIDATE QUALIFICATION: FAIL: {exc}", file=sys.stderr)
        return 1

    print("SIZING CANDIDATE QUALIFICATION:", result["status"])
    if args.require_pass and not result["qualified_for_release_review"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
