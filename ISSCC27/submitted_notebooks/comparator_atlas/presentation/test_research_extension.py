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


def test_impulse_sensitivity_predicts_every_noise_realization(data):
    t = ext.isf_table(data)
    assert list(t["ISF sigma_n (mV)"]) == [0.648, 0.378, 1.249, 0.476, 0.67, 0.603, 0.64, 0.444, 0.344]
    assert [s.split()[0] for s in t["MC sigma_n (mV, 95% CI)"]] == \
           ["0.708", "0.356", "1.325", "0.464", "0.717", "0.518", "0.702", "0.482", "0.364"]
    assert list(t["rms(MC - ISF) (uV)"]) == [38.5, 25.7, 165.3, 35.6, 48.0, 168.5, 6.1, 7.6, 7.0]
    assert list(t["slope"])[-4:] == [0.773, 1.002, 1.007, 0.994]
    assert min(t["corr"].iloc[-3:]) >= 0.9998
    original = ext._r24()["validation"][:6]
    assert all(v["noise"] == ("all" if v["design"] in ("baseline", "lvt_base_3b") else "prune") for v in original)
    atlas = ext.isf_atlas_table(data)
    assert atlas.shape == (5, 9) and list(atlas.columns)[:3] == ["1.62 V -40 C", "1.62 V 27 C", "1.62 V 125 C"]
    assert atlas.loc["TT", "1.8 V 27 C"] == 0.64 and atlas.loc["FS", "1.62 V -40 C"] == 0.35
    worst, sigma, need = atlas.attrs["worst"]
    assert (worst, round(sigma, 2), round(need, 1)) == ("SF 1.95 V 125 C", 1.21, 5.7)


def test_closed_form_law_predicts_the_common_mode_sweep(data):
    t = ext.noise_law_table(data)
    k, sd, low, high, n = t.attrs["calibration"]
    assert (round(k, 3), round(sd, 3), round(low, 3), round(high, 3), n) == (0.729, 0.037, 0.661, 0.813, 45)
    assert list(t.index) == [0.6, 0.7, 0.9, 1.1]
    assert list(t["error"]) == ["+2%", "+12%", "+1%", "-17%"]
    assert list(t["total sigma_n (mV)"]) == [0.344, 0.401, 0.64, 1.159]
    assert list(t["sigma_n^2 x dq100 (mV^2 ps)"]) == [380, 155, 205, 548]
    q = [r["q_int_fC"] for r in ext._r24()["scaling"]] + list(t["Q_int (fC)"])
    assert 5.8 < min(q) and max(q) < 8.6


def test_off_trim_branches_carry_decision_memory(data):
    t = ext.memory_table(data)
    a = {k: float(v.split()[0]) for k, v in t["as built: a (uV) / c"].items()}
    assert [a[ext.ISF_LABELS[d]] for d in ("baseline", "lvt_balanced_4b", "unit6_w6", "u6_w12_l05")] == \
           [1.0, 7.5, 43.0, 9.5]
    for column in ("off trim branches deleted: a (uV) / c", "switch on the x side: a (uV) / c"):
        assert all(abs(float(v.split()[0])) <= 1.5 for v in t[column])
    shipped = t.loc[ext.ISF_LABELS["lvt_balanced_4b"]]
    assert (shipped["trim LSB / MSB step, original (mV)"], shipped["trim LSB / MSB step, swap (mV)"]) == \
           ("-2.64 / -22.5", "+6.49 / +39.4")


def test_gain_law_closes_the_latch_noise(data):
    t = ext.gain_law_table(data)
    a = t.attrs
    assert (round(a["a0"], 2), round(a["k"], 3)) == (3.13, 0.728)
    assert (round(a["pvt"]["rms"], 4), round(a["pvt"]["max"], 4)) == (0.0057, 0.0185)
    assert round(a["closed"]["rms"], 3) == 0.053 and round(a["input_only"]["rms"], 3) == 0.164
    assert 3.11 < a["loco"][0] and a["loco"][1] < 3.15 and a["loco"][2] < 0.02
    assert a["share"][0] < 0.021 and a["share"][1] == 13
    assert list(t.index) == [0.6, 0.7, 0.9, 1.1]
    assert list(t["error"]) == ["-1.0%", "+0.3%", "+0.2%", "-11.5%"]
    assert list(t["A_int"]) == [16.2, 11.1, 5.5, 3.8]


def test_memory_is_the_floating_node_charge(data):
    t = ext.memory_probe_table(data)
    a = {c: [float(v.split()[0]) for v in t[f"{c}: a (uV) / c"]]
         for c in ("as built", "own value forced", "pair shorted", "opposite prior forced")}
    assert a["as built"] == [1.0, 7.5, 43.0, 9.5]
    assert all(abs(x - y) <= 2.0 for x, y in zip(a["as built"], a["own value forced"]))
    assert all(abs(x) <= 1.5 for x in a["pair shorted"])
    assert a["opposite prior forced"] == [-x for x in a["own value forced"]]


def test_equalize_fix_is_requalified(data):
    t = ext.memory_fix_table(data)
    eq, orig = t.loc[ext.FIX_LABELS["equalize"]], t.loc[ext.FIX_LABELS["original"]]
    assert eq["memory a (uV) / c"] == "1.0 / 0.00%" and orig["memory a (uV) / c"] == "7.5 / 0.95%"
    assert list(t["monotonic"]) == [True, False, True, True]
    assert list(t["range out of span"]) == [0, 2, 0, 0]
    assert (eq["half range min / median (mV)"], orig["half range min / median (mV)"]) == ("27.5 / 40.7", "18.7 / 37.8")
    assert (orig["energy code 0 / 15 (fJ)"], eq["energy code 0 / 15 (fJ)"]) == ("288 / 298", "296 / 307")
    assert t.loc[ext.FIX_LABELS["precharge"], "energy code 0 / 15 (fJ)"] == "389 / 460"
    assert eq["unit6_w6: a (uV) / LSB TT (mV) / energy (fJ)"] == "1.0 / -1.00 / 785"
    mc = ext.fix_mc_table(data)
    assert list(mc["trim range covers offset"]) == ["38/40"] * 4
    assert list(mc["+/-1 mV @ 1 ns"]) == ["71/80 (9 wrong)", "65/80 (15 wrong)", "69/80 (11 wrong)", "62/80 (18 wrong)"]
    assert list(mc["uncovered seeds (residual m, mV)"]) == \
           ["3 (+16.5), 13 (+14.4)", "3 (+4.8), 13 (+2.7)", "3 (+16.1), 13 (+13.2)", "3 (+6.7), 13 (+3.9)"]
    assert list(mc["nominal half range (mV)"]) == [18.5, 29.3, 19.0, 27.2]
    assert mc.attrs["below_25"] == (4, 0)


def test_five_bit_trim_covers_the_hot_corner_seeds(data):
    screen = ext.trim_length_table(data)
    lsb_sf = {L: float(v.split(" / ")[1]) for L, v in screen["end-point LSB TT / SF / FF (mV)"].items()}
    assert all(lsb_sf[L] < 0 for L in (0.5, 0.75, 1.0)) and all(lsb_sf[L] > 0 for L in (1.5, 1.75, 2.0))
    assert abs(lsb_sf[1.25]) < 0.1
    mc = ext.trim5_mc_table(data)
    five = mc.xs(ext.TRIM5_LABEL, level="variant")
    assert list(five["trim range covers offset"]) == ["40/40"] * 3
    assert list(five["+/-3 mV @ 1 ns"]) == ["80/80"] * 3
    assert list(five["+/-1 mV @ 1 ns"]) == ["68/80 (12 wrong)", "71/80 (9 wrong)", "70/80 (10 wrong)"]
    assert list(five["seeds 3 / 13: m (mV)"]) == ["-0.12 / +0.12", "+0.82 / -0.82", "-0.59 / -0.82"]
    assert list(mc.xs("4b as built (r22)", level="variant")["trim range covers offset"]) == ["38/40"] * 2
    assert round(mc.attrs["narrowest"], 1) == 43.9 and round(mc.attrs["median"], 1) == 67.1
    assert [round(e) for e in mc.attrs["energy_fj"]] == [296, 460]
    assert [round(a, 2) for a in mc.attrs["area_um2"]] == [20.55, 38.79]
    assert round(mc.attrs["memory_uv"]["equalize"], 1) == -1.0


def test_unit_cell_trim_is_binary_over_pvt_and_reaches_one_millivolt(data):
    w = ext.bit_weight_table(data)
    assert list(w["width-binary: w4 / w0"]) == [17.2, 29.5, 32.8, 6.8, 7.3]
    assert list(w["unit cell: w4 / w0"]) == [14.5, 17.2, 18.6, 11.5, 12.2]
    assert round(w.attrs["spread"]["width-binary"], 2) == 2.40 and round(w.attrs["spread"]["unit cell"], 2) == 1.08
    t = ext.unit_trim_table(data)
    assert list(t.index) == [ext.TRIM5, "s5_k125", "s6_k150", "u5_k125", ext.UNIT_SELECTED]
    assert list(t["covered (of 120)"]) == [120] * 5 and list(t["+/-3 mV @ 1 ns (of 240)"]) == [240] * 5
    assert list(t["+/-1 mV @ 1 ns (of 240)"]) == [209, 235, 238, 235, 240]
    assert list(t["max |m| (mV)"]) == [1.52, 1.05, 1.29, 1.05, 0.82]
    assert list(t["TT energy, code 0 (fJ)"]) == [460, 476, 818, 465, 482]
    assert list(t["gate area (um^2)"]) == [38.8, 39.3, 76.2, 39.3, 39.8]
    assert list(t["cold max step (mV)"]) == [14.4, 12.0, 10.3, 2.6, 2.1]
    assert list(t["hot max |DNL| (LSB)"]) == [2.2, 3.0, 4.4, 1.4, 1.5]
    assert t.loc[ext.UNIT_SELECTED, "45-condition half range min / median / max (mV)"] == "31.6 / 39.0 / 44.5"


def test_r26c_equalizer_monte_carlo_and_inverter_sweep(data):
    t = ext.equalizer_mc_table(data)
    pooled = t.xs("pooled", level="condition")
    assert list(pooled["static |m| <= 1 mV"]) == ["989/1000", "997/1000"]
    assert list(pooled["+/-1 mV @ 1 ns (seeds)"]) == ["978/1000", "996/1000"]
    assert list(pooled["95% CI"]) == ["0.967 - 0.986", "0.990 - 0.999"]
    assert list(pooled["wrong / unresolved decisions"]) == ["7 / 15", "4 / 0"]
    assert list(pooled["+/-3 mV @ 1 ns (seeds)"]) == ["1000/1000"] * 2
    assert list(t.xs("e5_k150", level="design")["+/-1 mV @ 1 ns (seeds)"]) == \
        ["200/200", "200/200", "199/200", "199/200", "198/200", "996/1000"]
    assert t.loc[("SS 1.62 V -40 C", "u5_k150"), "+/-1 mV @ 1 ns (seeds)"] == "185/200"
    assert t.loc[("SF 1.95 V 125 C", "u5_k150"), "LSB / max step (mV), DNL (LSB)"] == "1.18 / 1.76, 1.50 (non-mono)"
    assert t.loc[("SS 1.62 V -40 C", "e5_k150"), "LSB / max step (mV), DNL (LSB)"] == "0.97 / 1.17, 0.24"
    assert {d: round(e) for d, e in t.attrs["energy_fj"].items()} == {"u5_k150": 482, "e5_k150": 517}
    assert {d: round(a, 2) for d, a in t.attrs["equalizer_area_um2"].items()} == {"u5_k150": 0.44, "e5_k150": 2.46}
    assert [round(x, 1) for x in t.attrs["half_range_mv"]["e5_k150"]] == [30.0, 37.8, 49.8]
    s = ext.inverter_sweep_table(data)
    assert list(s["SF / SS mean step"]) == [3.5, 2.2, 1.7, 1.4]
    assert list(s["TT energy, code 0 (fJ)"]) == [498, 504, 517, 541]
    assert s.loc[4, "SS 1.62 V -40 C step min / mean / max (mV)"] == "0.86 / 0.95 / 1.00"


def test_r26d_input_scale_carry_law_and_segmentation(data):
    t = ext.input_scale_table(data)
    pooled = t.xs("pooled", level="condition")
    assert list(pooled["static |m| <= 1 mV"]) == ["997/1000", "999/1000"]
    assert list(pooled["+/-1 mV @ 1 ns (seeds)"]) == ["996/1000", "999/1000"]
    assert list(pooled["95% CI"]) == ["0.990 - 0.999", "0.994 - 1.000"]
    assert list(pooled["wrong / unresolved decisions"]) == ["4 / 0", "1 / 0"]
    assert list(t.xs(1.75, level="input pair scale k")["+/-1 mV @ 1 ns (seeds)"]) == \
        ["200/200", "200/200", "200/200", "199/200", "200/200", "999/1000"]
    assert t.loc[("SF 1.95 V 125 C", 1.5), "nominal LSB / MC 1-bit step (mV)"] == "1.46 / 1.71"
    assert t.loc[("SF 1.95 V 125 C", 1.75), "nominal LSB / MC 1-bit step (mV)"] == "1.22 / 1.36"
    assert t.loc[("SS 1.62 V -40 C", 1.75), "nominal LSB / MC 1-bit step (mV)"] == "0.81 / 0.81"
    assert {k: round(e) for k, e in t.attrs["energy_fj"].items()} == {1.5: 517, 1.75: 533}
    assert [round(x, 1) for x in t.attrs["half_range_mv"][1.75]] == [24.9, 32.5, 42.2]
    assert {k: round(r, 2) for k, r in t.attrs["rho_sf_ss"].items()} == {1.5: 1.51, 1.75: 1.51}
    c = ext.carry_law_table()
    assert list(c.loc[1.5, "step sd (LSB)"]) == [0.123, 0.188, 0.221, 0.367]
    assert list(c.loc[1.5, "fit (LSB)"]) == [0.122, 0.176, 0.252, 0.358]
    assert list(c.loc[1.5, "seeds"]) == [539, 250, 119, 87]
    assert {k: (round(s0, 3), round(su, 3)) for k, (s0, su) in c.attrs["fit_lsb"].items()} == \
        {1.5: (0.083, 0.09), 1.75: (0.118, 0.088)}
    s = ext.segmentation_table()
    assert list(s["observed (binary)"]) == [3, 1]
    assert list(s["binary (5 bits)"]) == [4.59, 0.73]
    assert list(s["3 thermometer MSBs + 2 binary"]) == [2.46, 0.07]
    assert list(s["full thermometer"]) == [0.53, 0.0]


def test_r26e_segmented_trim(data):
    t = ext.segmented_mc_table(data)
    assert list(t["most cells per step"]) == [31, 7]
    assert list(t["static |m| <= 1 mV"]) == ["999/1000", "1000/1000"]
    assert list(t["+/-1 mV @ 1 ns (seeds)"]) == ["999/1000", "1000/1000"]
    assert list(t["95% CI"]) == ["0.9944 - 1.0000", "0.9963 - 1.0000"]
    assert list(t["wrong / unresolved decisions"]) == ["1 / 0", "0 / 0"]
    assert list(t["max / rms |m| (mV)"]) == ["1.11 / 0.34", "0.82 / 0.34"]
    assert list(t["local steps > 2 mV (observed / law)"]) == ["10 / 5.8", "3 / 1.6"]
    assert list(t["TT energy at code 0 (fJ)"]) == [533.05, 533.08]
    assert t.attrs["predicted_static_miss"] == {"binary": 0.73, "segmented": 0.066}
    assert t.attrs["tail_sign_test_p"] == 0.0461
    c = ext.segmented_law_table()
    seg = c.loc["3 thermometer MSBs + 2 binary"]
    assert list(seg["seeds"]) == [499, 258, 243]
    assert list(seg["step sd (LSB)"]) == [0.153, 0.204, 0.268]
    assert list(seg["binary fit (LSB)"]) == [0.147, 0.193, 0.261]
    assert list(c.loc["binary (5 bits)", "seeds"]) == [508, 252, 133, 100, 5]
    assert {d: (round(s0, 3), round(su, 3)) for d, (s0, su) in c.attrs["fit_lsb"].items()} == \
        {"e5_k175": (0.118, 0.088), "g5_k175": (0.126, 0.09)}


def test_r26f_tail_model_and_hold_cap(data):
    t = ext.tail_model_table()
    assert list(t["steps > 2 mV observed"]) == [10, 3, 10, 3]
    assert list(t["with drift: predicted (P >= observed)"]) == \
        ["6.77 (0.15)", "1.52 (0.20)", "8.14 (0.30)", "1.94 (0.31)"]
    assert t.attrs["joint"]["delta_hat"] == 0.0053
    assert t.attrs["joint"]["delta_ci95"] == [0.0016, 0.0089]
    assert t.attrs["joint"]["per_condition_positive"] == 10
    h = ext.hold_cap_table(data)
    tt = h.loc[("TT 1.8 V 27 C", 0.5)]
    assert list(tt["segment-gate dip (mV)"]) == [178, 103, 47, 15]
    assert list(tt["boundary -31 / -16 (mV)"]) == \
        ["30.62 / 15.97", "31.20 / 16.55", "31.49 / 16.55", "31.49 / 16.85"]
    assert set(h["ideal decoder (mV)"].loc["TT 1.8 V 27 C"]) == {"31.79 / 16.85"}
    assert h.loc[("SS 1.62 V -40 C", 0.5, 4.0), "boundary -31 / -16 (mV)"] == "25.05 / 12.45"
    assert list(h.loc["TT 1.8 V 27 C"].xs(0.0, level=1)["segment-gate dip (mV)"]) == [134, 178, 186]


def test_r26f_transistor_decoder():
    t = ext.decoder_table()
    assert list(t["LSB change (%)"]) == [-3.7, -4.7, -4.3, -1.5, -1.6]
    assert list(t["segment-gate dip (mV)"]) == [178, 126, 113, 262, 232]
    assert t["monotonic"].all() and t["max |DNL| (LSB)"].max() == 0.39
    assert list(t["same code (seeds)"]) == ["165/200", "164/200", "182/200", "136/200", "150/200"]
    assert set(t["static |m| <= 1 mV, decoder / ideal"]) == {"200 / 200"}
    assert set(t["+/-1 mV @ 1 ns, decoder / ideal"]) == {"200 / 200"}
    p = t.attrs["pooled"]
    assert (p["n"], p["same_code"], p["static_1mv"], p["pass_1mv_1ns"], p["pass_1mv_1ns_ref"]) == \
        (1000, 797, 1000, 1000, 1000)
    assert t.attrs["devices"] == 96 and round(t.attrs["gate_area_um2"], 1) == 39.6
    assert round(t.attrs["leak_worst_na"], 2) == 2.93 and t.attrs["leak_cond"] == "SF 1.95 V 125 C"
    assert {d: round(v, 2) for d, v in t.attrs["energy_fj"].items()} == {"d5_k175": 533.02, "g5_k175": 533.08}


def test_r26g_dip_law_and_driver_fixes():
    law = ext.dip_law_table()
    assert list(law.index) == ["TT 1.8 V 27 C", "SS 1.62 V -40 C", "FS 1.62 V -40 C", "SF 1.95 V 125 C",
                               "FF 1.95 V 125 C"]
    assert list(law["A (mV)"]) == [330, 271, 223, 423, 388]
    assert law["worst fit error (%)"].max() < 8 and law["prediction error (%)"].max() < 8
    assert list(law["scaled drivers, predicted dip (mV)"]) == [72.5, 52.9, 45.9, 106.6, 91.4]
    t = ext.driver_fix_table()
    assert list(t["added gate area (um2)"].round(1)) == [0.0, 6.6, 42.9, 14.0, 56.0, 224.0]
    assert list(t["TT segment dip (mV)"]) == [178, 179, 76, 103, 47, 15]
    cols = [c for c in t.columns if c.endswith("loss (%)")]
    seg, full = ({d: [float(v.split(" / ")[i]) for v in t.loc[d, cols]] for d in t.index} for i in (0, 1))
    lab = ext.DRIVER_LABELS
    s5, h1, h2, h4, d5 = (seg[lab[k]] for k in ("s5", "d5 H1", "d5 H2", "d5 H4", "d5"))
    assert all(a < b for a, b in zip(full[lab["d5 H1"]], full[lab["s5"]]))
    assert sum(a < b for a, b in zip(h1, s5)) == 4
    assert all(a > b > c > d for a, b, c, d in zip(d5, h1, h2, h4))
    assert d5[0] == 4.55 and max(h2) <= 1.25


def test_r26h_thevenin_drivers():
    t = ext.thevenin_table()
    lin = ["linear: R 1 kohm", "linear: R 2 kohm", "linear: R 4 kohm", "linear: R 7 kohm",
           "linear: R 2 kohm + C 20 fF", "linear: R 7 kohm + C 10 fF", "linear: R 7 kohm + C 20 fF",
           "linear: R 7 kohm + C 40 fF"]
    assert list(t.index) == lin + list(ext.THEVENIN_MOS.values())
    assert [c.split(" dip")[0] for c in t.columns] == ["TT 1.8 V 27 C", "SS 1.62 V -40 C", "FS 1.62 V -40 C",
                                                       "SF 1.95 V 125 C", "FF 1.95 V 125 C"]
    v = {d: [tuple(float(x) for x in t.loc[d, c].split(" / ")) for c in t.columns] for d in t.index}
    assert v[lin[0]][0][:2] == (64, 4.32) and v[lin[6]][0][:2] == (68, 1.40)
    assert min(v[d][0][0] for d in lin) == 41 and max(v[d][0][0] for d in lin) == 213
    r_only, rc = lin[:4], lin[4:]
    for i in (0, 3, 4):  # TT, SF, FF: every series-R-only driver costs more per mV than every shunt-C driver
        assert min(v[d][i][2] for d in r_only) > max(v[d][i][2] for d in rc)
    assert max(v[d][i][2] for d in rc for i in (3, 4)) <= 0.009
    d5, s5, h1 = (v[ext.THEVENIN_MOS[k]] for k in ("d5", "s5", "d5 H1"))
    for i in (1, 2):  # SS, FS: linear band 0.038 - 0.050 %/mV, s5 inside, the slow MOS designs below
        band = [v[d][i][2] for d in lin]
        assert 0.038 <= min(band) and max(band) <= 0.050 and min(band) <= s5[i][2] <= max(band)
        assert d5[i][2] < min(band) and h1[i][2] < min(band)
        assert 0.07 <= 1 - max(d5[i][2], h1[i][2]) / min(band) and 1 - min(d5[i][2], h1[i][2]) / min(band) <= 0.23  # 8 - 21 % before rounding
    pair = v[lin[5]]
    assert pair[0][0] == h1[0][0] == 103 and abs(h1[0][1] / pair[0][1] - 1) < 0.08
    assert 2.0 < max(h1[i][1] / pair[i][1] for i in (3, 4)) < 2.45


def test_r26h_state_aware_fit():
    t = ext.thevenin_state_table()
    assert list(t.index) == [ext._condition(c) for c in ext.BIT_WEIGHT_CONDS]
    lin = "d5 + 8.3 fF linear: dip (mV) / loss"
    assert list(t.columns)[-1] == lin

    def num(col):
        return [[float(x) for x in s.split(" / ")] for s in t[col]]
    d5, h1 = num("d5 loss: sym / state / MOS"), num("H1 loss: sym / state / MOS")
    for sym, state, mos in d5 + h1:  # the state-aware driver reproduces all ten MOS losses
        assert abs(state - mos) <= 0.08
    assert max(abs(sym - mos) for sym, _, mos in d5 + h1) > 0.9  # the on-gate-matched symmetric driver does not
    r_off = [r for r, _ in num("R_on / R_off (kohm)")]
    assert min(r_off) >= 8.0 and max(r_off) <= 13.3
    assert all(3.0 <= r <= 3.4 for _, r in num("R_on / R_off (kohm)"))
    assert all(c_off < 0.5 * c_on for c_on, c_off in num("H1 C_on / C_off (fF)"))
    fix = num(lin)
    for (_, loss), (_, _, mos) in zip(fix[3:], h1[3:]):  # SF, FF: a linear hold capacitor halves the loss
        assert loss < 0.6 and loss < 0.5 * mos
    for (_, loss), (_, _, mos) in zip(fix[:3], h1[:3]):  # TT, SS, FS: within 8 %
        assert abs(loss / mos - 1) <= 0.08
    assert abs(max(x[1] for x in fix) - max(x[2] for x in h1)) < 0.05  # worst corner unchanged


def test_r26i_fixes():
    t = ext.fixes_table()
    assert list(t.index) == ["d5", "d5 H1", "d5 H2", "d5 + 8.3 fF linear (r26h)", "d5 H1.4", "d5 H1.72", "d5 H1 PH1",
                             "d5 P4 H1", "d5 N4", "d5 N4 H1", "d5 N4 H1 PH1"]
    worst = t["worst loss (%)"].to_dict()
    loss = {d: [float(t.loc[d, c].split(" / ")[1]) for c in t.columns if c.endswith("dip / loss")] for d in t.index}
    hot = {d: max(v[3:]) for d, v in loss.items()}
    assert worst["d5 H1"] == 2.50 and worst["d5 H2"] == 1.25
    assert worst["d5 N4 H1"] < 2.1 and worst["d5 H1 PH1"] < worst["d5 + 8.3 fF linear (r26h)"]
    assert hot["d5 N4 H1"] < 0.35 * hot["d5 H1"]
    assert worst["d5 H1.4"] < min(worst["d5 N4 H1"], worst["d5 H1 PH1"])  # ~2 um2: the larger nfet cap wins the worst
    assert worst["d5 H1.72"] < worst["d5 N4 H1 PH1"]  # ~3 um2
    assert hot["d5 N4 H1"] < 0.5 * hot["d5 H1.4"] and hot["d5 N4 H1 PH1"] < 0.5 * hot["d5 H1.72"]  # off-state buys hot
    assert hot["d5 P4 H1"] > hot["d5 H1"] and worst["d5 N4"] > worst["d5 H1"]
    area = {d: float(a) for d, a in t["added area (um2)"].items() if a != "ideal"}
    assert abs(area["d5 H1.4"] - area["d5 N4 H1"]) < 0.05 and abs(area["d5 H1.72"] - area["d5 N4 H1 PH1"]) < 0.05


def test_r26j_verify():
    t = ext.verify_table()
    data = ext._json(ext.VERIFY)
    d = data["designs"]
    assert list(t.index) == ["d5", "d5 H1", "d5 H1.4", "d5 H1.72", "d5 N4 H1", "d5 H1 PH1", "d5 N4 H1 PH1"]
    assert len(data["seeds"]) == 40
    assert all(max(v["mc"]["sd_pct"]) < 0.15 for v in d.values())  # mismatch barely moves the segment loss
    assert all(abs(sum(v["mc"]["per_seed_worst_pct"]) / 40 - v["nominal_worst_pct"]) < 0.09 for v in d.values())
    dev = {k: max(abs(a - b) for a, b in zip(v["mc"]["mean_pct"], v["nominal_loss_pct"])) for k, v in d.items()}
    assert max(dev.values()) < 0.15 and max(dev, key=dev.get) == "d5 N4 H1 PH1"  # text: within 0.15, N4/PH most
    assert all(p["seeds"] == p["n"] == 40 for p in data["worst_rank_pairs"].values())  # r26i's ranking, every seed
    assert all(v["energy"]["tt_vdd_delta_fj"] < 0.5 for v in d.values())
    ref = ext._json("r26f/memory_energy_d5_k175.json")  # r26f's d5 energy, reproduced by the r26j path
    assert all(abs(d["d5"]["energy"]["tt_vdd_fj"][c] - ref[f"equalize {c}"]["vdd_fj"]) < 1e-6 for c in ("0", "31", "-31"))
    leak = {k: v["energy"]["leak_worst_na"] for k, v in d.items()}
    assert leak["d5 N4 H1"] > 1.3 * leak["d5 H1"] and abs(leak["d5 H1.4"] - leak["d5"]) < 1e-6
    fp = {k: v["footprint_um2"] for k, v in d.items()}
    assert fp["d5 H1.4"] < 0.8 * fp["d5 N4 H1"] and abs(fp["d5 H1.72"] - fp["d5 N4 H1"]) < 0.3
    para = {k: v["para_worst_abs_pct"] for k, v in d.items()}
    assert abs(para["d5 H1.4"]["1"] - para["d5 N4 H1"]["1"]) < 0.05  # extracted net: area-matched tie
    assert para["d5 N4 H1"]["4"] < para["d5 H1.72"]["4"] < para["d5 H1.4"]["4"]  # x4: the pull-down wins
    assert para["d5 H1.72"]["1"] < para["d5 N4 H1"]["1"]  # footprint-matched at x1: the larger capacitor
    flow = {k: v["flow"] for k, v in d.items()}
    assert all(flow.values())  # every fix, and d5 from r26b on the same seeds
    for rows in flow.values():
        assert sum(r["n"] for r in rows) == 100 and sum(r["pass_1mv_1ns"] for r in rows) == 100


def test_no_unfilled_placeholders():
    texts = [(ROOT / n).read_text(encoding="utf-8") for n in
             ("Comparator_Atlas.ipynb", "README.md", "REVIEWER_GUIDE.md", "REPRODUCIBILITY.md")]
    for text in texts:
        assert "R13_" not in text and "R19_MC" not in text and "R19MCMAX" not in text and "MC_TEXT" not in text
    assert len(ext.MANIFEST_SHA256) == 64


def test_trim_major_carry_and_figure(data):
    steps = ext.trim_steps(data)
    binary = steps[steps.trim.str.contains("binary")]
    assert binary.step_mv.max() > 11
    fig = ext.figure(data)
    assert len(fig.axes) == 3 and ext.SCOPE_LABEL in fig.texts[0].get_text()
    matplotlib.pyplot.close(fig)
