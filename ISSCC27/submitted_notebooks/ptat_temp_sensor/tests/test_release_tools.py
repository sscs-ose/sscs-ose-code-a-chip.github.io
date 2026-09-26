import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import full_pdk_evidence_audit
import pdk_calibration_analysis
import readout_budget
import run_sky130
import sizing_candidate_qualification
import mismatch_sizing_study


MATCHING_PROVENANCE = {
    "ngspice": "ngspice-46",
    "ngspice_compatibility_mode": "hsa",
    "pdk_revision": "test-pdk-revision",
    "model_sha256": "a" * 64,
    "design_requirements_sha256": "b" * 64,
}


def candidate_readout(status="PASS"):
    return {
        "status": status,
        "anchors_c": [-40, -20, 0, 50, 125],
        "bits": 12,
        "vref_v": 1.8,
        "analog_gain": 10.0,
        "worst_quantization_rms_c": 0.05,
        "worst_full_scale_utilization": 0.5,
        "worst_quantized_pwl_sampled_error_c": 0.45,
        "provenance": MATCHING_PROVENANCE.copy(),
    }


def test_retained_five_point_target_is_met():
    r = pdk_calibration_analysis.analyze()
    assert r["five_point_pwl_grid_calibration"]["worst_max_abs_error_c"] < 0.5


def test_retained_two_point_target_is_not_hidden():
    r = pdk_calibration_analysis.analyze()
    assert r["two_point_endpoint_calibration"]["worst_max_abs_error_c"] > 0.5


def test_release_architecture_matches_evidence():
    rel = json.loads((ROOT / "release_requirements.json").read_text())
    assert rel["release_architecture"]["calibration"] == "five_point_piecewise_linear"
    assert rel["known_evidence"]["two_point_release_target_met"] is False
    assert rel["known_evidence"]["five_point_pwl_release_target_met"] is True


def test_behavioral_readout_budget_passes():
    r = readout_budget.analyze()
    assert r["status"] == "PASS"
    assert r["worst_quantization_rms_c"] <= r["quantization_rms_target_c"]
    assert r["worst_full_scale_utilization"] <= r["full_scale_utilization_target_max"]
    assert (
        r["worst_quantized_pwl_sampled_error_c"]
        <= r["quantized_sampled_grid_target_c"]
    )


def test_notebook_submission_structure_is_explicit():
    import submission_preflight

    ok, errors = submission_preflight.check_notebook()
    assert ok, errors


def test_sky130_runner_uses_isolated_hsa_compatibility_mode(tmp_path):
    env, spiceinit = run_sky130.prepare_ngspice_environment(tmp_path)
    assert env["HOME"] == str((tmp_path / "ngspice_home").resolve())
    assert spiceinit == (tmp_path / "ngspice_home" / ".spiceinit").resolve()
    assert spiceinit.read_text(encoding="utf-8") == "set ngbehavior=hsa\n"


def test_sky130_render_matches_retained_micron_dimension_convention(tmp_path):
    model = tmp_path / "sky130.lib.spice"
    ideal = run_sky130.render("ideal", "tt", [-40.0, 125.0], "dense_pdk/test.csv", model)
    assert "LCH=0.5" in ideal
    assert "W1=1.0" in ideal
    assert "W2=8.0" in ideal
    assert "0.5u" not in ideal
    assert "1.0u" not in ideal
    assert "8.0u" not in ideal

    mirror = run_sky130.render("mirror", "tt", [-40.0, 125.0], "dense_pdk/test.csv", model)
    assert "LNS=0.5" in mirror
    assert "WNS1=1.0" in mirror
    assert "WNS2=8.0" in mirror
    assert "LPM=1.0" in mirror
    assert "WPM=4.0" in mirror
    assert "__WNS1__" not in mirror
    assert "__WNS2__" not in mirror
    assert "0.5u" not in mirror


def test_mismatch_sizing_preserves_operating_ratios_and_scales_area():
    base = run_sky130.load_design()
    scaled = mismatch_sizing_study.scaled_design(base, 4.0, 8.0)
    bseed = base["nominal_characterization_seed"]
    sseed = scaled["nominal_characterization_seed"]

    assert (
        sseed["sensor_nmos"]["w_large_um"]
        / sseed["sensor_nmos"]["w_small_um"]
        == bseed["sensor_nmos"]["w_large_um"]
        / bseed["sensor_nmos"]["w_small_um"]
    )
    assert (
        sseed["sensor_nmos"]["w_small_um"] / sseed["sensor_nmos"]["l_um"]
        == bseed["sensor_nmos"]["w_small_um"] / bseed["sensor_nmos"]["l_um"]
    )
    assert (
        sseed["mirror_pmos"]["w_um"] / sseed["mirror_pmos"]["l_um"]
        == bseed["mirror_pmos"]["w_um"] / bseed["mirror_pmos"]["l_um"]
    )
    assert (
        mismatch_sizing_study.active_device_area_um2(scaled)
        > mismatch_sizing_study.active_device_area_um2(base)
    )


def test_mismatch_sizing_candidate_score_prioritizes_yield_deficit():
    better_yield = {
        "yield_target_percent": 95.0,
        "yield_percent_error_le_target": 95.0,
        "yield_percent_branch_mismatch_le_target": 95.0,
        "max_abs_error_c": {"p95": 0.49},
    }
    smaller_but_bad = {
        "yield_target_percent": 95.0,
        "yield_percent_error_le_target": 100.0,
        "yield_percent_branch_mismatch_le_target": 50.0,
        "max_abs_error_c": {"p95": 0.20},
    }
    assert mismatch_sizing_study.candidate_score(better_yield, 1000.0) < (
        mismatch_sizing_study.candidate_score(smaller_but_bad, 10.0)
    )


def test_mismatch_sizing_default_seed_sets_are_disjoint():
    screen_start, screen_samples = 2001, 16
    validation_start, validation_samples = 5001, 100
    screen = set(range(screen_start, screen_start + screen_samples))
    validation = set(range(validation_start, validation_start + validation_samples))
    assert screen.isdisjoint(validation)


def test_retained_full_pdk_evidence_is_internally_consistent():
    result = full_pdk_evidence_audit.audit()
    assert result["status"] == "PASS"
    assert result["dense_status"] == "PASS"
    assert result["mismatch_status"] == "FAIL"
    assert result["candidate_status"].endswith("NOT_RELEASE_VALIDATED")

def test_sky130_runner_supports_independent_sensor_and_mirror_scaling():
    seed = run_sky130.characterization_seed(
        sensor_linear_scale=2.0,
        mirror_linear_scale=24.0,
    )
    sensor = seed["sensor_nmos"]
    mirror = seed["mirror_pmos"]

    assert sensor["l_um"] == 1.0
    assert sensor["w_small_um"] == 2.0
    assert sensor["w_large_um"] == 16.0
    assert mirror["l_um"] == 24.0
    assert mirror["w_um"] == 96.0



def test_sizing_candidate_qualification_requires_both_mismatch_and_dense_pass():
    selected = {
        "candidate": "i10_m8_s2",
        "iref_scale": 10.0,
        "mirror_linear_scale": 8.0,
        "sensor_linear_scale": 2.0,
        "headroom_pass": True,
    }
    validation = {
        "candidate": "i10_m8_s2",
        "status": "PASS",
        "samples": 100,
        "seed_start": 9001,
        "error_yield_percent": 97.0,
        "branch_yield_percent": 96.0,
        "headroom_pass": True,
        "min_sensor_headroom_v": 0.5,
    }
    sweep = {
        "recommended_for_independent_validation": selected,
        "independent_validation": validation,
        "provenance": MATCHING_PROVENANCE.copy(),
        "samples_per_candidate": 12,
        "seed_start": 3001,
    }
    metadata = {
        **MATCHING_PROVENANCE,
        "sensor_linear_scale": 2.0,
        "mirror_linear_scale": 8.0,
        "operating_point": {
            "reference_current_a": 1.0e-6,
            "branch_current_a": 1.0e-6,
            "vdd_v": 1.8,
        },
    }
    dense = {
        "status": "PASS",
        "anchors_c": [-40, -20, 0, 50, 125],
        "worst_pwl_max_abs_error_c": 0.45,
        "worst_five_point_pwl_max_abs_error_c": 0.45,
        "worst_mirror_branch_mismatch_percent": 0.8,
        "max_temperature_step_c": 5.0,
    }
    readout = candidate_readout()

    result = sizing_candidate_qualification.analyze(
        sweep, dense, metadata, readout, 1.0e-7
    )
    assert result["status"] == "QUALIFIED_FOR_RELEASE_REVIEW"
    assert result["qualified_for_release_review"] is True
    assert result["release_architecture_changed"] is False

    dense["status"] = "FAIL"
    result = sizing_candidate_qualification.analyze(
        sweep, dense, metadata, readout, 1.0e-7
    )
    assert result["status"] == "NOT_QUALIFIED_FOR_RELEASE_REVIEW"
    assert result["qualified_for_release_review"] is False

    dense["status"] = "PASS"
    validation["headroom_pass"] = False
    result = sizing_candidate_qualification.analyze(
        sweep, dense, metadata, readout, 1.0e-7
    )
    assert result["status"] == "NOT_QUALIFIED_FOR_RELEASE_REVIEW"
    assert (
        result["qualification_components"]["independent_headroom_pass"]
        is False
    )

    validation["headroom_pass"] = True
    readout["status"] = "FAIL"
    result = sizing_candidate_qualification.analyze(
        sweep, dense, metadata, readout, 1.0e-7
    )
    assert result["qualified_for_release_review"] is False
    assert result["qualification_components"]["readout_pass"] is False


def test_sizing_candidate_qualification_rejects_evidence_mismatch():
    sweep = {
        "provenance": MATCHING_PROVENANCE.copy(),
        "recommended_for_independent_validation": {
            "candidate": "i1_m4_s2",
            "iref_scale": 1.0,
            "mirror_linear_scale": 4.0,
            "sensor_linear_scale": 2.0,
            "headroom_pass": True,
        },
        "independent_validation": {
            "candidate": "i1_m4_s2",
            "status": "PASS",
            "samples": 100,
            "seed_start": 9001,
            "error_yield_percent": 100.0,
            "branch_yield_percent": 100.0,
            "headroom_pass": True,
        },
    }
    metadata = {
        **MATCHING_PROVENANCE,
        "sensor_linear_scale": 2.0,
        "mirror_linear_scale": 8.0,
        "operating_point": {
            "reference_current_a": 1.0e-7,
            "branch_current_a": 1.0e-7,
            "vdd_v": 1.8,
        },
    }
    dense = {
        "status": "PASS",
        "anchors_c": [-40, -20, 0, 50, 125],
        "worst_five_point_pwl_max_abs_error_c": 0.4,
        "worst_mirror_branch_mismatch_percent": 0.5,
    }
    with __import__("pytest").raises(
        sizing_candidate_qualification.QualificationError,
        match="mirror linear scale",
    ):
        sizing_candidate_qualification.analyze(
            sweep, dense, metadata, candidate_readout(), 1.0e-7
        )



def test_sizing_candidate_qualification_rejects_provenance_mismatch():
    sweep = {"provenance": MATCHING_PROVENANCE.copy()}
    dense_metadata = MATCHING_PROVENANCE.copy()
    dense_metadata["pdk_revision"] = "different-pdk-revision"

    with __import__("pytest").raises(
        sizing_candidate_qualification.QualificationError,
        match="pdk_revision provenance mismatch",
    ):
        sizing_candidate_qualification.require_matching_provenance(
            sweep, dense_metadata
        )



def test_candidate_readout_budget_accepts_dense_linear_data(tmp_path):
    temps = [float(value) for value in range(-40, 126, 5)]
    for mode in ("ideal", "mirror"):
        for corner in ("tt", "ff", "ss"):
            path = tmp_path / f"ptat_{mode}_{corner}.csv"
            lines = ["temp_c,dvgs_v"]
            for temp in temps:
                dvgs = 0.050 + (temp + 40.0) * 0.0002
                lines.append(f"{temp:.1f},{dvgs:.12g}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    metadata = {
        **MATCHING_PROVENANCE,
        "sensor_linear_scale": 2.0,
        "mirror_linear_scale": 8.0,
        "operating_point": {
            "reference_current_a": 1.0e-6,
            "branch_current_a": 1.0e-6,
            "vdd_v": 1.8,
        },
    }
    (tmp_path / "run_metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    result = readout_budget.analyze_directory(tmp_path)
    assert result["status"] == "PASS"
    assert result["anchors_c"] == [-40, -20, 0, 50, 125]
    assert result["worst_quantization_rms_c"] < 0.1
    assert result["worst_full_scale_utilization"] < 0.9
    assert result["worst_quantized_pwl_sampled_error_c"] < 0.5
    assert result["provenance"] == MATCHING_PROVENANCE
