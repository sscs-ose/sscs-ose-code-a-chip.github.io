"""Synthetic input-contract tests; these fixtures are not PDK evidence."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sizing_candidate_qualification as qualification


@pytest.fixture
def evidence():
    provenance = {
        "ngspice": "test-ngspice",
        "ngspice_compatibility_mode": "hsa",
        "pdk_revision": "synthetic-fixture-only",
        "model_sha256": "a" * 64,
        "design_requirements_sha256": "b" * 64,
    }
    sweep = {
        "provenance": provenance.copy(),
        "seed_start": 3001,
        "samples_per_candidate": 12,
        "recommended_for_independent_validation": {
            "candidate": "i10_m8_s2",
            "iref_scale": 10.0,
            "mirror_linear_scale": 8.0,
            "sensor_linear_scale": 2.0,
            "headroom_pass": True,
        },
        "independent_validation": {
            "candidate": "i10_m8_s2",
            "status": "PASS",
            "samples": 100,
            "seed_start": 11001,
            "error_yield_percent": 97.0,
            "branch_yield_percent": 96.0,
            "headroom_pass": True,
            "min_sensor_headroom_v": 0.5,
        },
    }
    dense = {
        "status": "PASS",
        "anchors_c": [-40, -20, 0, 50, 125],
        "worst_pwl_max_abs_error_c": 0.45,
        "worst_mirror_branch_mismatch_percent": 0.8,
        "max_temperature_step_c": 5.0,
    }
    metadata = {
        **provenance,
        "sensor_linear_scale": 2.0,
        "mirror_linear_scale": 8.0,
        "operating_point": {
            "reference_current_a": 1.0e-6,
            "branch_current_a": 1.0e-6,
            "vdd_v": 1.8,
        },
    }
    readout = {
        "status": "PASS",
        "anchors_c": [-40, -20, 0, 50, 125],
        "bits": 12,
        "vref_v": 1.8,
        "analog_gain": 10.0,
        "worst_quantization_rms_c": 0.05,
        "worst_full_scale_utilization": 0.8,
        "worst_quantized_pwl_sampled_error_c": 0.45,
        "provenance": provenance.copy(),
    }
    return sweep, dense, metadata, readout, 1.0e-7


@pytest.mark.parametrize(
    "field,value",
    [
        ("samples", 99),
        ("error_yield_percent", 94.0),
        ("branch_yield_percent", 94.0),
        ("min_sensor_headroom_v", 0.0),
        ("headroom_pass", "true"),
    ],
)
def test_pass_label_cannot_override_failed_validation(evidence, field, value):
    evidence[0]["independent_validation"][field] = value
    result = qualification.analyze(*evidence)
    assert result["qualified_for_release_review"] is False
    assert result["release_architecture_changed"] is False


@pytest.mark.parametrize(
    "start,expected", [(2901, True), (2902, False), (3001, False),
                       (3012, False), (3013, True), (11001, True)]
)
def test_seed_independence_checks_both_inclusive_endpoints(
    evidence, start, expected
):
    evidence[0]["independent_validation"]["seed_start"] = start
    result = qualification.analyze(*evidence)
    assert result["qualification_components"]["disjoint_validation_seeds"] is expected
    assert result["qualified_for_release_review"] is expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("worst_pwl_max_abs_error_c", 0.51),
        ("worst_mirror_branch_mismatch_percent", 1.01),
        ("max_temperature_step_c", 10),
        ("max_temperature_step_c", 0),
        ("anchors_c", [-40, -25, -5, 25, 65, 125]),
    ],
)
def test_dense_pass_label_cannot_override_release_contract(evidence, field, value):
    evidence[1][field] = value
    result = qualification.analyze(*evidence)
    assert result["qualification_components"]["dense_tt_ff_ss_pass"] is False
    assert result["qualified_for_release_review"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("samples", 100.5),
        ("samples", True),
        ("seed_start", 9001.5),
        ("seed_start", 0),
        ("error_yield_percent", float("nan")),
        ("branch_yield_percent", float("inf")),
        ("branch_yield_percent", 101.0),
        ("error_yield_percent", -1.0),
    ],
)
def test_invalid_validation_numbers_fail_closed(evidence, field, value):
    evidence[0]["independent_validation"][field] = value
    with pytest.raises(qualification.QualificationError):
        qualification.analyze(*evidence)


def test_current_dense_metric_does_not_require_legacy_alias(evidence):
    result = qualification.analyze(*evidence)
    assert result["qualified_for_release_review"] is True
    assert result["dense_tt_ff_ss"]["worst_pwl_max_abs_error_c"] == 0.45


def test_legacy_dense_metric_remains_accepted(evidence):
    dense = evidence[1]
    dense["worst_five_point_pwl_max_abs_error_c"] = dense.pop(
        "worst_pwl_max_abs_error_c"
    )
    assert qualification.analyze(*evidence)["qualified_for_release_review"] is True


def test_missing_seed_metadata_cannot_claim_independence(evidence):
    del evidence[0]["samples_per_candidate"]
    with pytest.raises((qualification.QualificationError, KeyError)):
        qualification.analyze(*evidence)


@pytest.mark.parametrize("recorded_ranges", [None, []])
def test_seen_holdout_cannot_qualify_despite_disjoint_current_screen(
    evidence, recorded_ranges
):
    sweep = evidence[0]
    sweep["independent_validation"]["seed_start"] = 9001
    if recorded_ranges is not None:
        sweep["validation_excluded_seed_ranges"] = recorded_ranges
    result = qualification.analyze(*evidence)
    assert result["qualification_components"]["disjoint_validation_seeds"] is True
    assert result["qualification_components"]["unseen_validation_seeds"] is False
    assert result["qualified_for_release_review"] is False
    assert result["validation_seed_conflicts"][0]["start"] == 9001


def test_additional_examined_ranges_are_rechecked(evidence):
    evidence[0]["validation_excluded_seed_ranges"] = [
        {"start": 11050, "stop": 11149, "source_run_id": 123}
    ]
    result = qualification.analyze(*evidence)
    assert result["qualification_components"]["unseen_validation_seeds"] is False
    assert result["qualified_for_release_review"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "FAIL"),
        ("bits", 11),
        ("vref_v", 1.7),
        ("analog_gain", 9.0),
        ("worst_quantization_rms_c", 0.11),
        ("worst_full_scale_utilization", 0.91),
        ("worst_quantized_pwl_sampled_error_c", 0.51),
        ("anchors_c", [-40, -25, -5, 25, 65, 125]),
    ],
)
def test_readout_pass_label_cannot_override_release_contract(
    evidence, field, value
):
    evidence[3][field] = value
    result = qualification.analyze(*evidence)
    assert result["qualification_components"]["readout_pass"] is False
    assert result["qualified_for_release_review"] is False


def test_readout_provenance_mismatch_fails_closed(evidence):
    evidence[3]["provenance"]["pdk_revision"] = "different-pdk"
    with pytest.raises(
        qualification.QualificationError,
        match="readout pdk_revision provenance mismatch",
    ):
        qualification.analyze(*evidence)
