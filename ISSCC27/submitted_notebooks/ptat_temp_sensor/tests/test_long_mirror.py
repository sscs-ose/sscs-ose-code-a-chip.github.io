"""Geometry and export regressions; fixtures are not simulation evidence."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mismatch_mc
import run_sky130


def test_dense_and_mismatch_use_identical_long_mirror_dimensions():
    kwargs = dict(sensor_linear_scale=8, mirror_linear_scale=16,
                  mirror_length_multiplier=4, reference_current_a=5e-7)
    seed = run_sky130.characterization_seed(**kwargs)
    assert seed["mirror_pmos"]["l_um"] == 64
    assert seed["mirror_pmos"]["w_um"] == 64
    assert seed["sensor_nmos"]["l_um"] == 4
    assert seed["sensor_nmos"]["w_small_um"] == 8
    assert seed["sensor_nmos"]["w_large_um"] == 64
    texts = [
        run_sky130.render("mirror", "tt", [-40, 125], "test.csv",
                          Path("/model.spice"), **kwargs),
        mismatch_mc.render(123, [-40, 125], "test.csv",
                           Path("/model.spice"), **kwargs),
    ]
    for text in texts:
        assert "LPM=64.0 WPM=64.0" in text
        assert "LNS=4.0 WNS1=8.0 WNS2=64.0" in text


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_mirror_length_is_rejected_by_both_renderers(value):
    with pytest.raises(ValueError):
        run_sky130.characterization_seed(mirror_length_multiplier=value)
    with pytest.raises(ValueError):
        mismatch_mc.render(123, [-40, 125], "test.csv", Path("/model.spice"),
                           mirror_length_multiplier=value)


@pytest.mark.parametrize("missing_row", [False, True])
def test_captured_rows_preserve_grid_and_reject_incomplete_output(
    monkeypatch, tmp_path, missing_row
):
    monkeypatch.setattr(mismatch_mc, "ROOT", tmp_path)
    monkeypatch.setattr(mismatch_mc, "render", lambda *a, **k:
                        'echo "temp_c,vgs_small_v,vgs_large_v,dvgs_v,'
                        'supply_current_a,power_w,branch_small_a,branch_large_a"'
                        ' > results/sample.csv\n'
                        "  echo $t',' 0 >> results/sample.csv\n")
    rows = ["PTAT_CSV -40,0.3,0.2,0.1,1e-6,1.8e-6,1e-7,1e-7"]
    if not missing_row:
        rows.append("PTAT_CSV 125,0.4,0.2,0.2,1e-6,1.8e-6,1e-7,1e-7")
    monkeypatch.setattr(mismatch_mc.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=0, stderr="",
                                        stdout="ngspice log\n" + "\n".join(rows)))
    call = lambda: mismatch_mc.run_sample(
        123, [-40, 125], tmp_path / "results" / "sample", Path("/model"), "ngspice"
    )
    if missing_row:
        with pytest.raises(RuntimeError, match="temperature grid"):
            call()
    else:
        assert len(mismatch_mc.read_rows(call())) == 2
