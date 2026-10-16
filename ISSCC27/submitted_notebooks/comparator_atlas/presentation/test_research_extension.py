import json
import shutil
from pathlib import Path

import matplotlib
import pytest

from presentation import research_extension as ext

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def data():
    return ext.load()


def test_manifest_covers_every_research_script(data):
    scripts = {p.name for p in (ROOT / "research").glob("*.py")}
    assert set(data["manifest"]["script_sha256"]) == scripts
    assert data["manifest"]["schema"] == "comparator-atlas-research-archive-v1"


def test_changed_archive_file_is_refused(tmp_path, monkeypatch, data):
    copy = tmp_path / "research"
    shutil.copytree(ext.DATA, copy)
    target = copy / "r1" / "r1_report.json"
    target.write_bytes(target.read_bytes() + b"\n")
    monkeypatch.setattr(ext, "DATA", copy)
    with pytest.raises(RuntimeError, match="r1/r1_report.json"):
        ext.load()
    manifest = copy / "manifest.json"
    manifest.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest changed"):
        ext.load()


def test_static_residual_explains_every_wrong_decision(data):
    law = ext.law_table(data)
    assert law["wrong decisions"].sum() == 303
    assert law["wrong, predicted by 0 < v/m < 1"].sum() == 303
    assert law["wrong, not predicted"].sum() == 0
    assert law.loc["lvt_balanced_4b", "max |m| (mV)"] == 2.58


def test_atlas_extension_keeps_the_original_answers(data):
    atlas = ext.atlas_table(data)
    assert atlas.loc["baseline", "1 ns"] == "none <= 30 mV"
    assert atlas.loc["lvt_balanced_4b", "1 ns"].startswith(">= 3 mV")
    assert atlas.loc["lvt_balanced_4b", "0.75 ns"].startswith(">= 10 mV")
    assert set(atlas.index) == {*ext.ATLAS_DESIGNS, *ext.PROSPECTIVE_DESIGNS, ext.FIX}


def test_prospective_agreement(data):
    table = ext.prospective_table(data)
    r2 = table[table.study.eq("r2") & ~table.index.str.startswith("all")]
    agree, total = (sum(int(v.split("/")[i]) for v in r2["held-out decisions predicted"]) for i in (0, 1))
    assert (agree, total) == (10359, 10584)


def test_paired_monte_carlo_fix(data):
    mc = ext.mc_table(data)
    fix = mc.loc["Fix: unit 5b trim, input W 6"]
    assert list(fix["+/-1 mV @ 1 ns"]) == ["80/80", "80/80"]
    assert list(fix["+/-1 mV @ 0.75 ns"]) == ["80/80", "80/80"]
    assert fix["max |m| (mV)"].max() == 0.59
    shipped = mc.loc[("Shipped: binary 4b trim, input W 3", "SS 1.62 V -40 C")]
    assert shipped["max |m| (mV)"] == 4.8


def test_fix_hits_trim_range_in_atlas(data):
    table = ext.fix_residual_table(data)
    saturated = table[~table.index.str.startswith("other")]
    assert len(saturated) == 11
    assert {abs(int(c)) for c in saturated.code} == {ext.FIX_CODE_LIMIT}
    assert max(abs(float(m)) for m in saturated["residual m (mV)"]) == 10.86
    assert min(abs(float(m)) for m in saturated["residual m (mV)"]) == 1.17
    assert table.loc["other 38 conditions", "residual m (mV)"] == "|m| <= 0.39"
    atlas = ext.atlas_table(data)
    assert atlas.loc[ext.FIX, "1 ns"].startswith(">= 30 mV")


def test_cost_tables(data):
    energy = ext.energy_table(data)
    assert energy.loc["Shipped: binary 4b, input W 3", "TT 1.8 V 27 C (fJ)"] == "244 / 252"
    assert energy.loc["Fix: unit 5b, input W 6", "TT 1.8 V 27 C (fJ)"] == "420 / 444"
    rc = ext.postlayout_table(data)
    assert rc.loc["Fix, schematic", "correct @ 1.0 ns"] == "180/180"
    assert rc.loc["Fix, estimated RC", "correct @ 1.0 ns"] == "178/180"


def test_no_unfilled_placeholders():
    texts = [(ROOT / n).read_text(encoding="utf-8") for n in
             ("Comparator_Atlas.ipynb", "README.md", "REVIEWER_GUIDE.md", "REPRODUCIBILITY.md")]
    for text in texts:
        assert "R13_" not in text
    assert len(ext.MANIFEST_SHA256) == 64


def test_trim_major_carry_and_figure(data):
    steps = ext.trim_steps(data)
    binary = steps[steps.trim.str.contains("binary")]
    assert binary.step_mv.max() > 11
    fig = ext.figure(data)
    assert len(fig.axes) == 3 and ext.SCOPE_LABEL in fig.texts[0].get_text()
    matplotlib.pyplot.close(fig)
