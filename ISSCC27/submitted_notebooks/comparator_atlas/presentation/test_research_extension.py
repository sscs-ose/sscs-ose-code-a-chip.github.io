import json
import shutil
from pathlib import Path

import matplotlib
import numpy as np
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
    assert set(atlas.index) == {*ext.ATLAS_DESIGNS, *ext.PROSPECTIVE_DESIGNS, ext.FIX, *ext.RANGE_DESIGNS}


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


def test_six_bit_trim_reaches_one_millivolt(data):
    atlas = ext.atlas_table(data)
    assert atlas.loc["unit6_w6", "1 ns"].startswith(">= 1 mV")
    assert atlas.loc["unit6_w6", "2 ns"].startswith(">= 1 mV")
    assert atlas.loc["unit6_w6", "0.75 ns"].startswith(">= 3 mV")
    assert atlas.loc["unit5_w3", "1 ns"].startswith(">= 3 mV")
    table = ext.prospective_table(data)
    assert table.loc["unit5_w3", "held-out decisions predicted"] == "1695/1764"
    assert table.loc["unit6_w6", "held-out decisions predicted"] == "1677/1764"
    rng = ext.range_table(data)
    six = rng.loc["r15b: unit 6b, input W 6"]
    assert (six["max |m| (mV)"], six["conditions at range end"], six["conditions with |m| > 1 mV"]) == (0.55, 0, 0)
    assert rng.loc["r13 fix: unit 5b, input W 6", "conditions at range end"] == 11
    assert rng.loc["r15a: unit 5b, input W 3", "max |m| (mV)"] == 1.33


def test_six_bit_mismatch_and_energy(data):
    mc = ext.mc_table(data)
    six = mc.loc["6-bit: unit 6b trim, input W 6"]
    assert list(six["trim range covers offset"]) == ["40/40", "40/40"]
    assert list(six["+/-1 mV @ 0.75 ns"]) == ["80/80", "80/80"]
    assert list(six["+/-1 mV @ 1 ns"]) == ["80/80", "80/80"]
    assert six["max |m| (mV)"].max() == 0.59
    energy = ext.energy_table(data)
    assert energy.loc["6-bit: unit 6b, input W 6", "TT 1.8 V 27 C (fJ)"] == "731 / 780"


def test_cost_tables(data):
    energy = ext.energy_table(data)
    assert energy.loc["Shipped: binary 4b, input W 3", "TT 1.8 V 27 C (fJ)"] == "244 / 252"
    assert energy.loc["Fix: unit 5b, input W 6", "TT 1.8 V 27 C (fJ)"] == "420 / 444"
    rc = ext.postlayout_table(data)
    col = "+/-3, 10 mV correct @ 1.0 ns"
    assert rc.loc["r11 fix, schematic (binary-sized netlist)", col] == "180/180"
    assert rc.loc["r11 fix, estimated RC", col] == "178/180"


def test_six_bit_post_layout_estimate(data):
    rc = ext.postlayout_table(data)
    assert rc.loc["r17 fix, schematic (unit-array netlist)", "+/-3, 10 mV correct @ 1.0 ns"] == "180/180"
    six = rc.loc["r17 unit6_w6, schematic"]
    assert [six[f"+/-1 mV correct @ {d} ns"] for d in ("0.75", "1.0", "2.0")] == ["90/90"] * 3
    est = rc.loc["r17 unit6_w6, estimated RC"]
    assert (est["+/-1 mV correct @ 1.0 ns"], est["+/-1 mV correct @ 2.0 ns"]) == ("69/90", "90/90")
    assert rc.loc["r17 unit6_w6, estimated RC, half q-node wiring", "+/-1 mV correct @ 1.0 ns"] == "78/90"
    report = ext._json("r17/r17_report.json")
    assert all(v[f"all_wrong@{d}ns"] == 0 for v in report.values() for d in ("0.75", "1.0", "2.0"))


def test_energy_screen(data):
    screen = ext.energy_screen_table(data)
    base = screen.loc["u6_w6_l1_s1 (= unit6_w6)"]
    assert (base["energy code 0 / 63 (fJ)"], base["range, code 63 (mV)"]) == ("731 / 780", 44.4)
    assert screen.loc["u6_w12_l05_s1", "energy code 0 / 63 (fJ)"] == "611 / 664"
    assert screen.loc["u6_w12_l05_s1", "range, code 63 (mV)"] == 37.1
    drain = screen[screen["switch side"].eq("drain")]
    assert len(drain) == 2 and (drain["range, code 63 (mV)"] < 25).all()


def test_wide_input_six_bit(data):
    atlas = ext.atlas_table(data)
    w12 = atlas.loc["u6_w12_l05"]
    assert w12["0.75 ns"].startswith(">= 1 mV") and w12["1 ns"].startswith(">= 1 mV")
    assert w12["2 ns"].startswith(">= 0.5 mV")
    assert atlas.loc["unit6_w6", "0.75 ns"].startswith(">= 3 mV")
    table = ext.prospective_table(data)
    assert table.loc["u6_w12_l05", "held-out decisions predicted"] == "1674/1764"
    assert table.loc["all r19", "held-out decisions predicted"] == "atlas cells 16/18"
    rng = ext.range_table(data).loc["r19: unit 6b at L 0.5, input W 12"]
    assert (rng["codes used"], rng["conditions at range end"], rng["max |m| (mV)"]) == ("-16 to 15", 0, 0.39)
    rc = ext.wide_rc_table(data)
    assert rc.loc["unit6_w6, estimated RC", "+/-1 mV correct @ 1.0 ns"] == "69/90"
    est = rc.loc["u6_w12_l05, estimated RC"]
    assert (est["+/-1 mV correct @ 1.0 ns"], est["+/-3 mV correct @ 1.0 ns"], est["mean energy (fJ)"]) == ("78/90", "90/90", 827)
    assert rc.loc["u6_w12_l05, estimated RC, half q-node wiring", "+/-1 mV correct @ 1.0 ns"] == "90/90"
    assert rc["wrong decisions"].sum() == 0
    mc = ext.mc_table(data).loc["r19: unit 6b trim at L 0.5, input W 12"]
    assert list(mc["trim range covers offset"]) == ["40/40", "40/40"]
    assert list(mc["+/-1 mV @ 0.75 ns"]) == ["80/80", "80/80"]
    assert list(mc["+/-1 mV @ 1 ns"]) == ["80/80", "80/80"]
    assert list(mc["+/-0.5 mV @ 1 ns"]) == ["79/80 (1 wrong)", "78/80 (2 wrong)"]
    assert list(mc["max |m| (mV)"]) == [0.59, 0.82]


def test_width_skew_is_not_design_neutral(data):
    t = ext.bin_stress_table(data)
    assert list(t.index) == list(ext.BIN_DESIGNS)
    assert t.loc["lvt_balanced_4b", "DC current skew, TT (ideal 0.040)"] == "0.031-0.038"
    assert t.loc["unit6_w6", "DC current skew, TT (ideal 0.040)"] == "0.048-0.072"
    assert list(t["width / m (LSQ)"]) == [1.21, 1.14, 0.81, 1.58, 1.0]
    assert (t.loc["unit6_w6", "median |offset|, width skew (mV)"], t.loc["unit6_w6", "median |offset|, m skew (mV)"]) == (16.1, 10.2)
    assert t.loc["lvt_base_3b", "median |offset|, m skew (mV)"] == t.loc["lvt_balanced_4b", "median |offset|, m skew (mV)"] == 11.6
    width = list(t["1 ns correct (fully passing), width skew"])
    assert width == ["310/392 (16/49)", "350/392 (17/49)", "373/392 (30/49)", "-", "-"]
    assert list(t["1 ns correct (fully passing), m skew"])[:3] == ["310/392 (20/49)", "348/392 (16/49)", "377/392 (34/49)"]
    scores = ext._json("r21/r21_score_refined.json")
    assert {k.split("|", 1)[1]: v for k, v in scores["selection"].items() if k.startswith("width")} == \
           {k.split("|", 1)[1]: v for k, v in scores["selection"].items() if k.startswith("mult")} == \
           {"1": None, "3": "lvt_balanced_4b", "10": "lvt_balanced_4b", "30": "lvt_base_3b"}
    raw = ext._json("r21/r21_score.json")
    assert [raw[f"width|{d}"]["correct"] for d in ext.ATLAS_DESIGNS] == [310, 351, 374]


def test_selected_trim_range_is_narrowest_when_hot(data):
    t = ext.trim_range_table(data)
    assert list(t["half-range, narrowest (mV)"]) == [24.3, 28.4, 18.5]
    assert t.loc["lvt_balanced_4b", "narrowest condition"] == "SF 1.95 V 125 C"
    mc = ext.mc_table(data)
    for condition in ("SF 1.95 V 125 C", "FF 1.95 V 125 C"):
        hot = mc.loc[("Shipped: binary 4b trim, input W 3", condition)]
        assert hot["trim range covers offset"] == "38/40"
        assert hot["+/-3 mV @ 1 ns"].startswith("78/80")
    other = mc.loc[("Sealed lvt_base_3b: binary 3b trim, input W 2", "SF 1.95 V 125 C")]
    assert other["trim range covers offset"] == "38/40"
    assert other["+/-3 mV @ 1 ns"].startswith("76/80")
    uncovered = {d: sorted(r["seed"] for r in ext._jsonl(data, f"r22/mc_sf1.95V125C_{d}_*.jsonl")
                           if not r["covered"]) for d in ("lvt_balanced_4b", "lvt_base_3b")}
    assert uncovered == {"lvt_balanced_4b": [3, 13], "lvt_base_3b": [3, 13]}


def test_thermal_noise_sets_the_error_rate_of_the_residual(data):
    t = ext.noise_table(data)
    assert [float(s.split()[0]) for s in t["sigma_n (mV, 95% CI)"]] == [0.46, 0.72, 0.36, 0.71, 1.32, 0.52, 0.39]
    assert list(t["median P(wrong) at +/-1 mV"])[1:] == ["0.767", "0.307", "0.279", "0.377", "0.044", "0.011"]
    shipped = t.loc["Shipped: binary 4b trim, input W 3"]
    assert list(shipped["input for 1e-6 errors, median / p90 (mV)"]) == ["2.5 / 3.7", "4.0 / 4.4", "6.9 / 7.4"]
    assert list(t["rms |m| / sigma_n"])[-2:] == [0.5, 0.7]
    report = ext._json("r23/r23_report.json")
    for _, _, pattern, _, _ in ext.NOISE_VARIANTS:
        key = pattern[len("r23/run_"):pattern.rindex("_s*")]
        assert ext.noise_sigma(data, pattern)[0] == pytest.approx(report["sigma"][key]["sigma_mv"], abs=1e-12)
    full = ext.noise_sigma(data, "r23/run_lvt_balanced_4b_tt_1.8V_27C_dt2ps_s*.jsonl")[0]
    assert round(full, 2) == 0.70
    assert {k.split("_tt")[0]: (v["n"], round(v["rms_diff_mv"], 2)) for k, v in report["pruning"].items()} == \
           {"lvt_balanced_4b": (40, 0.05), "unit6_w6": (5, 0.03), "u6_w12_l05": (3, 0.01)}
    for name, ratios in (("validate_dt0.5ps", (0.972, 1.032)), ("validate_dt2ps", (0.85, 0.964))):
        checks = report["validation"][name]
        assert tuple(round(checks[d]["ratio_to_dotnoise"], 3) for d in ("nfet_01v8", "pfet_01v8")) == ratios
        assert all(abs(c["S_table"] / c["S_direct_at_vds0"] - 1) < 1e-3 for c in checks.values())
    groups = report["groups"]["lvt_balanced_4b_tt_1.8V_27C_dt2ps"]
    share = {k: round(groups[k]["sigma_mv"] ** 2 / groups["sum_of_variances_mv2"], 2)
             for k in ("input", "latchn", "reset", "latchp", "tail")}
    assert share == {"input": 0.82, "latchn": 0.11, "reset": 0.07, "latchp": 0.0, "tail": 0.0}
    assert groups["superposition"]["n"] == 24 and groups["superposition"]["rms_total_minus_sum_mv"] < 0.02
    two = {r["realization"]: r["noise_mv"] for r in ext._jsonl(data, "r23/run_lvt_balanced_4b_tt_1.8V_27C_dt2ps_s*")}
    one = {r["realization"]: r["noise_mv"] for r in ext._jsonl(data, "r23/run_lvt_balanced_4b_tt_1.8V_27C_dt1ps_s*")}
    a, b = [one[i] for i in sorted(one)], [two[i] for i in sorted(one)]
    assert len(a) == 16 and sum(x * x for x in a) / sum(x * x for x in b) == pytest.approx(1.013, abs=5e-4)
    half = {r["realization"]: r["noise_mv"] for r in ext._jsonl(data, "r23/run_lvt_balanced_4b_tt_1.8V_27C_dt0.5ps_s*")}
    assert sorted(half) == [0, 4, 8, 12]
    assert sum(v * v for v in half.values()) / sum(two[i] ** 2 for i in half) == pytest.approx(0.955, abs=5e-4)

    def paired_t(first, second):
        x, y = (np.array([r["noise_mv"] for r in sorted(ext._jsonl(data, f"r23/run_{k}_s*"),
                                                         key=lambda r: r["realization"])]) for k in (first, second))
        rho = np.corrcoef(x + y, x - y)[0, 1]
        return round(float(abs(rho) * np.sqrt((len(x) - 2) / (1 - rho ** 2))), 1)

    tt = "tt_1.8V_27C_dt2ps"
    assert paired_t(f"baseline_{tt}", f"lvt_balanced_4b_{tt}_pruned") == 3.6
    assert paired_t(f"lvt_base_3b_{tt}", f"lvt_balanced_4b_{tt}") == 0.4
    assert paired_t(f"unit6_w6_{tt}_pruned", f"u6_w12_l05_{tt}_pruned") == 9.6


def test_no_unfilled_placeholders():
    texts = [(ROOT / n).read_text(encoding="utf-8") for n in
             ("Comparator_Atlas.ipynb", "README.md", "REVIEWER_GUIDE.md", "REPRODUCIBILITY.md")]
    for text in texts:
        assert "R13_" not in text and "R19_MC" not in text and "R19MCMAX" not in text
    assert len(ext.MANIFEST_SHA256) == 64


def test_trim_major_carry_and_figure(data):
    steps = ext.trim_steps(data)
    binary = steps[steps.trim.str.contains("binary")]
    assert binary.step_mv.max() > 11
    fig = ext.figure(data)
    assert len(fig.axes) == 3 and ext.SCOPE_LABEL in fig.texts[0].get_text()
    matplotlib.pyplot.close(fig)
