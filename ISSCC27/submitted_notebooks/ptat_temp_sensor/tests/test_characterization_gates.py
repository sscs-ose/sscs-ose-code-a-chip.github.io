import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import calibration_candidate_validation
import dense_characterization
import mismatch_mc
import mismatch_sizing_sweep
import run_sky130


DENSE_TEMPS = [float(t) for t in range(-40, 126, 5)]
ANCHOR_TEMPS = [-40.0, -20.0, 0.0, 50.0, 125.0]


def _write_rows(path: Path, temps: list[float], *, offset: float = 0.0,
                slope: float = 2.5e-4, branch_ratio: float = 1.0) -> None:
    fieldnames = [
        "temp_c",
        "vgs_small_v",
        "vgs_large_v",
        "dvgs_v",
        "supply_current_a",
        "power_w",
        "branch_small_a",
        "branch_large_a",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for temp in temps:
            dvgs = offset + 0.05 + slope * (temp + 40.0)
            writer.writerow(
                {
                    "temp_c": temp,
                    "vgs_small_v": 0.45 + dvgs,
                    "vgs_large_v": 0.45,
                    "dvgs_v": dvgs,
                    "supply_current_a": 3.0e-7,
                    "power_w": 5.4e-7,
                    "branch_small_a": 1.0e-7,
                    "branch_large_a": 1.0e-7 * branch_ratio,
                }
            )


def test_branch_mismatch_metric_is_polarity_invariant():
    expected = abs(1.0 - 1.01) / ((1.0 + 1.01) / 2.0) * 100.0
    assert dense_characterization.branch_mismatch_percent(-1.0, -1.01) == pytest.approx(expected)
    assert mismatch_mc.branch_mismatch_percent(-1.0, -1.01) == pytest.approx(expected)


def test_dense_characterization_fails_closed_on_mirror_mismatch(tmp_path):
    for mode in ("ideal", "mirror"):
        for corner in ("tt", "ff", "ss"):
            ratio = 1.02 if mode == "mirror" and corner == "tt" else 1.0
            _write_rows(
                tmp_path / f"ptat_{mode}_{corner}.csv",
                DENSE_TEMPS,
                branch_ratio=ratio,
            )

    result = dense_characterization.analyze(tmp_path)
    assert result["worst_five_point_pwl_max_abs_error_c"] < 1e-9
    assert (
        result["worst_mirror_branch_mismatch_percent"]
        > result["mirror_branch_mismatch_target_percent"]
    )
    assert result["status"] == "FAIL"


def test_mismatch_mc_requires_branch_mismatch_yield(monkeypatch, tmp_path):
    monkeypatch.setitem(
        mismatch_mc.RELEASE["release_targets"], "mismatch_min_samples", 2
    )
    first = tmp_path / "sample_01001.csv"
    second = tmp_path / "sample_01002.csv"
    _write_rows(first, ANCHOR_TEMPS, offset=0.0, branch_ratio=1.0)
    _write_rows(second, ANCHOR_TEMPS, offset=1.0e-3, slope=2.55e-4, branch_ratio=1.02)

    result = mismatch_mc.analyze([first, second], ANCHOR_TEMPS)
    assert result["yield_percent_error_le_target"] == pytest.approx(100.0)
    assert result["yield_percent_branch_mismatch_le_target"] == pytest.approx(50.0)
    assert result["error_yield_status"] == "PASS"
    assert result["branch_mismatch_yield_status"] == "FAIL"
    assert result["status"] == "FAIL"


def test_pdk_revision_prefers_explicit_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SKY130_PDK_REVISION", "pinned-revision")
    model = tmp_path / "sky130.lib.spice"
    assert run_sky130.pdk_revision(model) == "pinned-revision"


def test_pdk_revision_can_be_inferred_from_volare_path(monkeypatch, tmp_path):
    monkeypatch.delenv("SKY130_PDK_REVISION", raising=False)
    model = (
        tmp_path
        / "sky130"
        / "versions"
        / "abc123"
        / "sky130A"
        / "libs.tech"
        / "ngspice"
        / "sky130.lib.spice"
    )
    assert run_sky130.pdk_revision(model) == "abc123"


def test_dense_provenance_fails_closed_when_metadata_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        dense_characterization.load_provenance(tmp_path)


def test_dense_provenance_requires_exact_pdk_revision(tmp_path):
    metadata = {
        "ngspice": "ngspice-46",
        "ngspice_compatibility_mode": "hsa",
        "pdk_revision": "unknown",
        "model_library": "/pdk/sky130.lib.spice",
        "model_sha256": "a" * 64,
        "design_requirements_sha256": "b" * 64,
    }
    (tmp_path / "run_metadata.json").write_text(
        __import__("json").dumps(metadata), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="exact PDK revision is unknown"):
        dense_characterization.load_provenance(tmp_path)



def test_anchor_parser_accepts_candidate_schedule():
    anchors = mismatch_mc.parse_anchor_list("-40,-25,-5,25,65,125")
    assert anchors == [-40.0, -25.0, -5.0, 25.0, 65.0, 125.0]


def test_anchor_parser_rejects_unsorted_values():
    with pytest.raises(ValueError, match="strictly increasing"):
        mismatch_mc.parse_anchor_list("-40,25,0,125")


def test_mismatch_render_scales_w_and_l_together(tmp_path):
    model = tmp_path / "sky130.lib.spice"
    rendered = mismatch_mc.render(
        1234,
        [-40.0, 25.0, 125.0],
        "scaled.csv",
        model,
        sensor_linear_scale=2.0,
        mirror_linear_scale=3.0,
    )
    assert ".param VDDVAL=1.8 IREF=1e-07 LNS=1.0 WNS1=2.0 WNS2=16.0" in rendered
    assert "LPM=3.0 WPM=12.0" in rendered
    assert "__WNS1__" not in rendered
    assert "__WPM__" not in rendered


def test_candidate_validation_keeps_branch_mismatch_separate(tmp_path):
    first = tmp_path / "sample_02001.csv"
    second = tmp_path / "sample_02002.csv"
    _write_rows(first, DENSE_TEMPS, offset=0.0, branch_ratio=1.0)
    _write_rows(second, DENSE_TEMPS, offset=1.0e-3, branch_ratio=1.02)

    result = calibration_candidate_validation.analyze(
        files=[first, second],
        baseline_anchors_c=[-40.0, -20.0, 0.0, 50.0, 125.0],
        candidate_anchors_c=[-40.0, -25.0, -5.0, 25.0, 65.0, 125.0],
        error_target_c=0.5,
        branch_target_percent=1.0,
        yield_target_percent=95.0,
        minimum_samples=2,
    )
    assert result["status"] == "PASS"
    assert result["candidate"]["yield_percent_le_target"] == pytest.approx(100.0)
    assert result["branch_mismatch"]["status"] == "FAIL"
    assert result["branch_mismatch"]["yield_percent_le_target"] == pytest.approx(50.0)

def test_characterization_seed_supports_low_power_operating_point():
    seed = run_sky130.characterization_seed(
        1.0,
        vdd_v=1.2,
        branch_current_a=1.0e-8,
        reference_current_a=1.0e-8,
    )
    assert seed["vdd_v"] == pytest.approx(1.2)
    assert seed["branch_current_a"] == pytest.approx(1.0e-8)
    assert seed["reference_current_a"] == pytest.approx(1.0e-8)
    assert seed["sensor_nmos"]["w_small_um"] == pytest.approx(1.0)
    assert seed["sensor_nmos"]["w_large_um"] == pytest.approx(8.0)


def test_mismatch_render_applies_low_power_overrides(tmp_path):
    rendered = mismatch_mc.render(
        7001,
        ANCHOR_TEMPS,
        "test_candidate.csv",
        tmp_path / "sky130.lib.spice",
        vdd_v=1.2,
        reference_current_a=1.0e-8,
    )
    assert "VDDVAL=1.2" in rendered
    assert "IREF=1e-08" in rendered
    assert "__VDDVAL__" not in rendered
    assert "__IREF__" not in rendered


def test_dense_characterization_accepts_explicit_anchor_schedule(tmp_path):
    custom_anchors = [-40.0, -20.0, 25.0, 75.0, 125.0]
    for mode in ("ideal", "mirror"):
        for corner in ("tt", "ff", "ss"):
            _write_rows(
                tmp_path / f"ptat_{mode}_{corner}.csv",
                DENSE_TEMPS,
                branch_ratio=1.0,
            )
    result = dense_characterization.analyze(tmp_path, custom_anchors)
    assert result["anchors_c"] == custom_anchors
    assert result["calibration_anchor_count"] == len(custom_anchors)
    assert result["uses_release_anchors"] is False
    assert result["worst_pwl_max_abs_error_c"] < 1e-9
    assert result["worst_five_point_pwl_max_abs_error_c"] < 1e-9
    assert result["status"] == "PASS"



def test_dense_characterization_rejects_incomplete_anchor_coverage():
    temps = [-40.0, -20.0, 0.0, 20.0, 40.0]
    volts = [0.05, 0.055, 0.06, 0.065, 0.07]
    with pytest.raises(ValueError, match="cover the full dense temperature grid"):
        dense_characterization.fixed_pwl_errors(
            temps,
            volts,
            [-20.0, 0.0, 20.0],
        )


def test_calibration_candidate_status_guard_accepts_only_unpromoted_states():
    guard = calibration_candidate_validation.candidate_status_is_unpromoted
    assert guard("DISCOVERY_ONLY_NOT_RELEASE_VALIDATED")
    assert guard("RETROSPECTIVE_SPLIT_ROBUSTNESS_PASS_NOT_RELEASE_VALIDATED")
    assert not guard("RELEASE_VALIDATED")
    assert not guard(None)


def test_sizing_validation_seed_ranges_must_be_disjoint():
    assert mismatch_sizing_sweep.seed_ranges_overlap(3001, 12, 3010, 100)
    assert not mismatch_sizing_sweep.seed_ranges_overlap(3001, 12, 9001, 100)


def test_sizing_sweep_delegates_to_canonical_mismatch_runner(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr(
        run_sky130,
        "load_design",
        lambda: {
            "nominal_characterization_seed": {
                "reference_current_a": 1.0e-7,
            }
        },
    )

    def fake_run_sample(seed, temps, out, model_lib, ngspice, **kwargs):
        captured.update(
            seed=seed,
            temps=temps,
            out=out,
            model_lib=model_lib,
            ngspice=ngspice,
            kwargs=kwargs,
        )
        return tmp_path / "sample.csv"

    monkeypatch.setattr(mismatch_mc, "run_sample", fake_run_sample)
    model = tmp_path / "sky130.lib.spice"
    result = mismatch_sizing_sweep.run_sample(
        3001,
        [-40.0, 125.0],
        tmp_path,
        model,
        "ngspice",
        10.0,
        4.0,
        2.0,
    )

    assert result == tmp_path / "sample.csv"
    assert captured["seed"] == 3001
    assert captured["kwargs"]["reference_current_a"] == pytest.approx(1.0e-6)
    assert captured["kwargs"]["mirror_linear_scale"] == pytest.approx(4.0)
    assert captured["kwargs"]["sensor_linear_scale"] == pytest.approx(2.0)


def test_dense_characterization_rejects_zero_pwl_voltage_span():
    with pytest.raises(ValueError, match="zero PWL voltage span"):
        dense_characterization.fixed_pwl_errors(
            [-40.0, 0.0, 40.0],
            [0.05, 0.05, 0.06],
            [-40.0, 0.0, 40.0],
        )

def test_dense_and_runner_reject_nonfinite_csv(tmp_path):
    path = tmp_path / "nonfinite.csv"
    _write_rows(path, DENSE_TEMPS)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["power_w"] = "nan"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="non-finite"):
        dense_characterization.read_xy(path)
    with pytest.raises(RuntimeError, match="non-finite"):
        run_sky130.validate_csv(path, DENSE_TEMPS, "mirror")

def test_dense_and_runner_reject_inconsistent_dvgs(tmp_path):
    path = tmp_path / "bad_dvgs.csv"
    _write_rows(path, DENSE_TEMPS)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["dvgs_v"] = str(float(rows[0]["dvgs_v"]) + 0.01)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="inconsistent"):
        dense_characterization.read_xy(path)
    with pytest.raises(RuntimeError, match="inconsistent"):
        run_sky130.validate_csv(path, DENSE_TEMPS, "mirror")



def test_dense_characterization_includes_headroom_in_status(tmp_path):
    for mode in ("ideal", "mirror"):
        for corner in ("tt", "ff", "ss"):
            _write_rows(
                tmp_path / f"ptat_{mode}_{corner}.csv",
                DENSE_TEMPS,
                branch_ratio=1.0,
            )
    result = dense_characterization.analyze(
        tmp_path, ANCHOR_TEMPS, vdd_v=0.55
    )
    assert result["worst_five_point_pwl_max_abs_error_c"] < 1e-9
    assert (
        result["min_sensor_headroom_v"]
        < result["sensor_headroom_target_v"]
    )
    assert result["status"] == "FAIL"


def test_ngspice_version_ignores_banner_line(monkeypatch):
    class Proc:
        returncode = 0
        stdout = (
            "******\n"
            "** ngspice-46 : Circuit level simulation program\n"
            "******\n"
        )
        stderr = ""

    monkeypatch.setattr(
        run_sky130.subprocess,
        "run",
        lambda *args, **kwargs: Proc(),
    )
    assert run_sky130.ngspice_version("ngspice") == "ngspice 46"


def test_ngspice_version_fails_closed_when_unparseable(monkeypatch):
    class Proc:
        returncode = 0
        stdout = "******\nversion unavailable\n"
        stderr = ""

    monkeypatch.setattr(
        run_sky130.subprocess,
        "run",
        lambda *args, **kwargs: Proc(),
    )
    with pytest.raises(RuntimeError, match="unable to parse ngspice version"):
        run_sky130.ngspice_version("ngspice")
