"""Hash-checked tables and figure for the follow-on research extension (Notebook section 9).

Every number comes from results/research, written by research/archive_results.py. These are later
schematic (and archived-extraction) simulations; they are not part of the sealed decision record.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from entry_tools import artifact_path, digest, verify_files

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "research"
MANIFEST_SHA256 = "0d10c49736bcc447c4e7d9b3e35d32914c9f32e490e00a95a70986b6dc7a8d93"
ATLAS_DESIGNS = ("baseline", "lvt_base_3b", "lvt_balanced_4b")
PROSPECTIVE_DESIGNS = ("svt_fast_4b", "lvt_fine_3b", "lvt_fine_4b", "lvt_fast_4b", "lvt_fast_fine_4b", "lvt_wide_5b")
FIX = "fix_x2_unit5b"
FIX_CODE_LIMIT = 31
RANGE_DESIGNS = ("unit5_w3", "unit6_w6", "u6_w12_l05")
RANGE_VARIANTS = (
    # design, label, residual file, code limit
    ("lvt_balanced_4b", "Shipped: binary 4b, input W 3", "r1/r1_residuals.csv", 15),
    (FIX, "r13 fix: unit 5b, input W 6", "r13/fix_residuals.csv", 31),
    ("unit5_w3", "r15a: unit 5b, input W 3", "r15a/unit5_w3_residuals.csv", 31),
    ("unit6_w6", "r15b: unit 6b, input W 6", "r15b/unit6_w6_residuals.csv", 63),
    ("u6_w12_l05", "r19: unit 6b at L 0.5, input W 12", "r19/u6_w12_l05_residuals.csv", 63),
)
PROSPECTIVE_STUDIES = (("r2", "prospective"), ("r13", "prospective fix"),
                       ("r15a", "prospective range"), ("r15b", "prospective range"), ("r19", "prospective range"))
BANDS_MV = (0.5, 1.0, 3.0, 10.0, 30.0)
TABLE_DEADLINES_NS = (0.75, 1.0, 2.0)
SCOPE_LABEL = "Extension: later local schematic simulations, not part of the sealed decision record"
MC_VARIANTS = (
    # label, condition, archive pattern, seed filter
    ("Shipped: binary 4b trim, input W 3", "TT 1.8 V 27 C", "r3/mc_lvt_balanced_4b_*.jsonl", 40),
    ("Shipped: binary 4b trim, input W 3", "SS 1.62 V -40 C", "r3/mc_ss1.62V-40C_lvt_balanced_4b_*.jsonl", 40),
    ("Unit-array 4b trim, input W 3", "SS 1.62 V -40 C", "r8/mc_unit_ss1.62V-40C_*.jsonl", 40),
    ("Unit 4b trim x2, input W 6", "SS 1.62 V -40 C", "r9/mc_combo_t2_ss1.62V-40C_*.jsonl", 40),
    ("Fix: unit 5b trim, input W 6", "TT 1.8 V 27 C", "r10/mc_combo_5b_tt1.8V27C_*.jsonl", 40),
    ("Fix: unit 5b trim, input W 6", "SS 1.62 V -40 C", "r10/mc_combo_5b_ss1.62V-40C_*.jsonl", 40),
    ("Rejected: gate-switched 5b trim", "TT 1.8 V 27 C", "r12/mc_gate5b_tt1.8V27C_*.jsonl", 40),
    ("Rejected: gate-switched 5b trim", "SS 1.62 V -40 C", "r12/mc_gate5b_ss1.62V-40C_*.jsonl", 40),
    ("6-bit: unit 6b trim, input W 6", "TT 1.8 V 27 C", "r16/mc_unit6_tt1.8V27C_*.jsonl", 40),
    ("6-bit: unit 6b trim, input W 6", "SS 1.62 V -40 C", "r16/mc_unit6_ss1.62V-40C_*.jsonl", 40),
    ("r19: unit 6b trim at L 0.5, input W 12", "TT 1.8 V 27 C", "r19/mc_w12_tt1.8V27C_*.jsonl", 40),
    ("r19: unit 6b trim at L 0.5, input W 12", "SS 1.62 V -40 C", "r19/mc_w12_ss1.62V-40C_*.jsonl", 40),
    ("Shipped: binary 4b trim, input W 3", "SF 1.95 V 125 C", "r22/mc_sf1.95V125C_lvt_balanced_4b_*.jsonl", 40),
    ("Shipped: binary 4b trim, input W 3", "FF 1.95 V 125 C", "r22/mc_ff1.95V125C_lvt_balanced_4b_*.jsonl", 40),
    ("Sealed lvt_base_3b: binary 3b trim, input W 2", "SF 1.95 V 125 C",
     "r22/mc_sf1.95V125C_lvt_base_3b_*.jsonl", 40),
)
MC_CHECKS = ((3.0, 1.0), (1.0, 0.75), (1.0, 1.0), (0.5, 1.0))
ENERGY_VARIANTS = {
    "binary4_w3_shipped": "Shipped: binary 4b, input W 3",
    "unit4_w3": "Unit 4b, input W 3",
    "unit4_w6": "Unit 4b, input W 6",
    "unit5_w3": "Unit 5b, input W 3",
    "unit5_w6_fix": "Fix: unit 5b, input W 6",
    "gate5_w6_r12": "Rejected: gate-switched 5b",
    "unit6_w6": "6-bit: unit 6b, input W 6",
}
ENERGY_CONDITIONS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("ff", 1.95, 125.0))
POSTLAYOUT_R11 = {"schematic": "r11 fix, schematic (binary-sized netlist)", "rc_x2_unit5b": "r11 fix, estimated RC",
                  "rc_x2_unit5b_half_q": "r11 fix, estimated RC, half q-node wiring"}
POSTLAYOUT_R17 = {"schematic_unit5": "r17 fix, schematic (unit-array netlist)",
                  "schematic_unit6": "r17 unit6_w6, schematic", "rc_unit6": "r17 unit6_w6, estimated RC",
                  "rc_unit6_half_q": "r17 unit6_w6, estimated RC, half q-node wiring"}
WIDE_RC = (
    # archive file, variant key, label
    ("r17/r17_pvt45.jsonl", "schematic_unit6", "unit6_w6, schematic"),
    ("r17/r17_pvt45.jsonl", "rc_unit6", "unit6_w6, estimated RC"),
    ("r17/r17_pvt45.jsonl", "rc_unit6_half_q", "unit6_w6, estimated RC, half q-node wiring"),
    ("r19/r19_rc.jsonl", "schematic_w12_l05", "u6_w12_l05, schematic"),
    ("r19/r19_rc.jsonl", "rc_w12_l05", "u6_w12_l05, estimated RC"),
    ("r19/r19_rc.jsonl", "rc_w12_l05_half_q", "u6_w12_l05, estimated RC, half q-node wiring"),
    ("r19/r19_rc.jsonl", "rc_unit6_no_q", "bound: input W 12, trim L 1, no q-node wiring"),
)
BIN_DESIGNS = (*ATLAS_DESIGNS, "unit6_w6", "u6_w12_l05")
NOISE_REALIZATIONS = 40
NOISE_Z_1E6 = 4.753
NOISE_VARIANTS = (
    # label, condition, r23 run pattern (dt 2 ps), noisy devices, Monte Carlo pattern for the trim residual m
    ("Sealed baseline: no trim, input W 2", "TT 1.8 V 27 C", "r23/run_baseline_tt_1.8V_27C_dt2ps_s*.jsonl",
     "all", None),
    ("Sealed lvt_base_3b: binary 3b trim, input W 2", "TT 1.8 V 27 C",
     "r23/run_lvt_base_3b_tt_1.8V_27C_dt2ps_s*.jsonl", "all", "r3/mc_lvt_base_3b_*.jsonl"),
    ("Shipped: binary 4b trim, input W 3", "SS 1.62 V -40 C",
     "r23/run_lvt_balanced_4b_ss_1.62V_-40C_dt2ps_pruned_s*.jsonl", "off trim branches quiet",
     "r3/mc_ss1.62V-40C_lvt_balanced_4b_*.jsonl"),
    ("Shipped: binary 4b trim, input W 3", "TT 1.8 V 27 C",
     "r23/run_lvt_balanced_4b_tt_1.8V_27C_dt2ps_pruned_s*.jsonl", "off trim branches quiet",
     "r3/mc_lvt_balanced_4b_*.jsonl"),
    ("Shipped: binary 4b trim, input W 3", "SF 1.95 V 125 C",
     "r23/run_lvt_balanced_4b_sf_1.95V_125C_dt2ps_pruned_s*.jsonl", "off trim branches quiet",
     "r22/mc_sf1.95V125C_lvt_balanced_4b_*.jsonl"),
    ("6-bit: unit 6b trim, input W 6", "TT 1.8 V 27 C", "r23/run_unit6_w6_tt_1.8V_27C_dt2ps_pruned_s*.jsonl",
     "off trim branches quiet", "r16/mc_unit6_tt1.8V27C_*.jsonl"),
    ("r19: unit 6b trim at L 0.5, input W 12", "TT 1.8 V 27 C",
     "r23/run_u6_w12_l05_tt_1.8V_27C_dt2ps_pruned_s*.jsonl", "off trim branches quiet",
     "r19/mc_w12_tt1.8V27C_*.jsonl"),
)
ISF_LABELS = {"baseline": "Sealed baseline: no trim, input W 2",
              "lvt_base_3b": "Sealed lvt_base_3b: binary 3b trim, input W 2",
              "lvt_balanced_4b": "Shipped: binary 4b trim, input W 3", "unit6_w6": "6-bit: unit 6b trim, input W 6",
              "u6_w12_l05": "r19: unit 6b trim at L 0.5, input W 12"}
ISF_BENCHES = (
    # bench, design, condition, archived r23 MC (None: the pinned-prior MC lives only in the r24 report)
    ("original", "lvt_balanced_4b", ("tt", 1.8, 27.0), "r23/run_lvt_balanced_4b_tt_1.8V_27C_dt2ps_pruned_s*.jsonl"),
    ("original", "lvt_balanced_4b", ("ss", 1.62, -40.0), "r23/run_lvt_balanced_4b_ss_1.62V_-40C_dt2ps_pruned_s*.jsonl"),
    ("original", "lvt_balanced_4b", ("sf", 1.95, 125.0), "r23/run_lvt_balanced_4b_sf_1.95V_125C_dt2ps_pruned_s*.jsonl"),
    ("original", "baseline", ("tt", 1.8, 27.0), "r23/run_baseline_tt_1.8V_27C_dt2ps_s*.jsonl"),
    ("original", "lvt_base_3b", ("tt", 1.8, 27.0), "r23/run_lvt_base_3b_tt_1.8V_27C_dt2ps_s*.jsonl"),
    ("original", "unit6_w6", ("tt", 1.8, 27.0), "r23/run_unit6_w6_tt_1.8V_27C_dt2ps_pruned_s*.jsonl"),
    ("pinned", "lvt_balanced_4b", ("tt", 1.8, 27.0), None),
    ("pinned", "unit6_w6", ("tt", 1.8, 27.0), None),
    ("pinned, CM 0.6 V", "lvt_balanced_4b", ("tt", 1.8, 27.0), None),
)


def load() -> dict:
    """Verify the pinned manifest and every archived file before any number is used."""
    manifest_path = DATA / "manifest.json"
    if digest(manifest_path) != MANIFEST_SHA256:
        raise RuntimeError("The research archive manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_files(DATA, manifest["artifact_sha256"])
    verify_files(ROOT / "research", manifest["script_sha256"])
    return {"manifest": manifest, "files": sorted(manifest["artifact_sha256"])}


def _json(name: str):
    return json.loads(artifact_path(DATA, name).read_text(encoding="utf-8"))


def _jsonl(data: dict, pattern: str) -> list[dict]:
    names = [n for n in data["files"] if Path(n).match(pattern)]
    if not names:
        raise RuntimeError(f"No archived file matches {pattern}")
    return [json.loads(line) for n in names
            for line in artifact_path(DATA, n).read_text(encoding="utf-8").splitlines() if line.strip()]


def law_table(data: dict) -> pd.DataFrame:
    """r1: a static post-calibration residual m predicts every wrong-sign decision."""
    report = _json("r1/r1_report.json")
    rows = []
    for design in ATLAS_DESIGNS:
        cells = [v for k, v in report["confusion_by_design_deadline"].items() if k.split("@")[0] == design]
        residual = report["residual_summary"][design]
        rows.append({
            "design": design,
            "resolved decisions": sum(c["resolved"] for c in cells),
            "wrong decisions": sum(c["wrong"] for c in cells),
            "wrong, predicted by 0 < v/m < 1": sum(c["true_pos"] for c in cells),
            "wrong, not predicted": sum(c["false_neg"] for c in cells),
            "predicted wrong, observed correct": sum(c["false_pos"] for c in cells),
            "median |m| (mV)": round(residual["abs_residual_mv_median"], 2),
            "max |m| (mV)": round(residual["abs_residual_mv_max"], 2),
            "conditions with |m| > 1 mV": residual["conditions_with_abs_residual_over"]["1mV"],
        })
    return pd.DataFrame(rows).set_index("design")


def _atlas_cells() -> pd.DataFrame:
    summary = json.loads((ROOT / "results" / "study" / "specification_map" / "summary.json").read_text(encoding="utf-8"))
    rows = [{"design": r["design"], "band_mv": r["minimum_abs_input_mv"], "deadline_ns": r["deadline_ns"],
             "qualifies": bool(r["all_correct"]), "energy_fj": r["mean_core_energy_fj"], "source": "atlas"}
            for r in summary["per_design"]]
    for study, source in PROSPECTIVE_STUDIES:
        frame = pd.read_csv(artifact_path(DATA, f"{study}/r2_atlas_new_designs.csv"))
        rows += [{"design": r.design_name, "band_mv": r.band_mv, "deadline_ns": r.deadline_ns,
                  "qualifies": bool(r.observed_qualifies), "energy_fj": r.mean_core_energy_fj, "source": source}
                 for r in frame.itertuples()]
    return pd.DataFrame(rows)


def atlas_table(data: dict) -> pd.DataFrame:
    """Smallest input band in which every one of 49 conditions is correct, per deadline."""
    cells = _atlas_cells()
    rows = []
    for design in (*ATLAS_DESIGNS, *PROSPECTIVE_DESIGNS, FIX, *RANGE_DESIGNS):
        part = cells[cells.design.eq(design)]
        row = {"design": design, "source": part.source.iloc[0]}
        for deadline in TABLE_DEADLINES_NS:
            ok = part[part.deadline_ns.eq(deadline) & part.qualifies & part.band_mv.isin(BANDS_MV)]
            if ok.empty:
                row[f"{deadline:g} ns"] = "none <= 30 mV"
                continue
            best = ok.sort_values("band_mv").iloc[0]
            row[f"{deadline:g} ns"] = f">= {best.band_mv:g} mV ({best.energy_fj:.0f} fJ)"
        rows.append(row)
    return pd.DataFrame(rows).set_index("design")


def prospective_table(data: dict) -> pd.DataFrame:
    """r2, r13 and r15: predictions sealed by sha256 before the held-out inputs were simulated."""
    rows = []
    for study, _ in PROSPECTIVE_STUDIES:
        report = _json(f"{study}/r2_evaluation.json")
        for design, agreement in report["sample_agreement"].items():
            rows.append({"design": design, "study": study,
                         "registry sha256": ", ".join(r["sha256"][:12] for r in report["registrations"]),
                         "held-out decisions predicted": f"{agreement['agree']}/{agreement['n']}",
                         "agreement": f"{agreement['agree'] / agreement['n']:.1%}"})
        rows.append({"design": f"all {study}", "study": study, "registry sha256": "",
                     "held-out decisions predicted": "atlas cells " + report["atlas_agreement_predictive_cells"],
                     "agreement": ""})
    return pd.DataFrame(rows).set_index("design")


def fix_residual_table(data: dict) -> pd.DataFrame:
    """r13: the fix's calibration code and residual m; conditions where the code hits the range end."""
    frame = pd.read_csv(artifact_path(DATA, "r13/fix_residuals.csv"))
    saturated = frame.code.abs().eq(FIX_CODE_LIMIT)
    rows = [{"condition": r.case_id, "code": str(r.code), "residual m (mV)": f"{r.residual_mv:+.2f}"}
            for r in frame[saturated].itertuples()]
    rest = frame[~saturated]
    rows.append({"condition": f"other {len(rest)} conditions", "code": f"{rest.code.min()} to {rest.code.max()}",
                 "residual m (mV)": f"|m| <= {rest.residual_mv.abs().max():.2f}"})
    return pd.DataFrame(rows).set_index("condition")


def range_table(data: dict) -> pd.DataFrame:
    """Trim step against trim range: calibration codes and residual m over the 49 conditions."""
    atlas = atlas_table(data)
    rows = []
    for design, label, name, limit in RANGE_VARIANTS:
        frame = pd.read_csv(artifact_path(DATA, name))
        if "design_name" in frame:
            frame = frame[frame.design_name.eq(design)]
        if len(frame) != 49 or frame.code.isna().any():
            raise RuntimeError(f"{name}: expected 49 calibrated conditions")
        rows.append({"variant": label, "code range": f"+/-{limit}",
                     "codes used": f"{int(frame.code.min())} to {int(frame.code.max())}",
                     "conditions at range end": int(frame.code.abs().eq(limit).sum()),
                     "conditions with |m| > 1 mV": int(frame.residual_mv.abs().gt(1).sum()),
                     "max |m| (mV)": round(float(frame.residual_mv.abs().max()), 2),
                     "atlas @ 1 ns": atlas.loc[design, "1 ns"]})
    return pd.DataFrame(rows).set_index("variant")


def _mc_summary(records: list[dict], limit: int) -> dict:
    records = [r for r in records if r["seed"] < limit]
    seeds = sorted(r["seed"] for r in records)
    if seeds != list(range(limit)):
        raise RuntimeError("Monte Carlo seeds are incomplete or duplicated")
    covered = [r for r in records if r["covered"]]
    row = {"seeds": len(records), "trim range covers offset": f"{len(covered)}/{len(records)}",
           "max |m| (mV)": round(max(abs(r["m_mv"]) for r in covered), 2) if covered else math.nan}
    for band, deadline in MC_CHECKS:
        evals = [e for r in records for e in r["evals"]
                 if abs(e["v_mv"]) == band and e["deadline_ns"] == deadline]
        if len(evals) != 2 * len(records):
            raise RuntimeError(f"Missing evaluations at {band} mV, {deadline} ns")
        correct = sum(e["outcome"] == "correct" for e in evals)
        wrong = sum(e["outcome"] == "wrong" for e in evals)
        row[f"+/-{band:g} mV @ {deadline:g} ns"] = f"{correct}/{len(evals)}" + (f" ({wrong} wrong)" if wrong else "")
    return row


def mc_table(data: dict) -> pd.DataFrame:
    """Paired mismatch Monte Carlo: the same device-level z draws for every variant."""
    rows = [{"variant": label, "condition": condition, **_mc_summary(_jsonl(data, pattern), limit)}
            for label, condition, pattern, limit in MC_VARIANTS]
    return pd.DataFrame(rows).set_index(["variant", "condition"])


def trim_steps(data: dict) -> pd.DataFrame:
    rows = []
    for record in _jsonl(data, "r7/trim_dnl.jsonl"):
        boundaries = {int(k): v for k, v in record["boundaries"].items()}
        codes = sorted(boundaries)
        corner = "/".join(c.upper() if isinstance(c, str) else f"{c:g}" for c in record["cond"])
        for low, high in zip(codes, codes[1:]):
            rows.append({"trim": record["variant"], "corner": corner,
                         "code": high, "step_mv": abs(boundaries[high] - boundaries[low])})
    return pd.DataFrame(rows)


def postlayout_table(data: dict) -> pd.DataFrame:
    """r11 (5-bit fix) and r17 (6-bit unit6_w6): 45 PVT conditions, code 0, nominal devices."""
    r11 = _json("r11/r11_report.json")
    r17 = _json("r17/r17_report.json")
    rows = []
    for key, label in POSTLAYOUT_R11.items():
        r = r11[key]
        rows.append({"variant": label,
                     **{f"+/-3, 10 mV correct @ {d} ns": f"{r[f'correct@{d}ns']}/{r['n']}" for d in ("0.75", "1.0", "2.0")},
                     **{f"+/-1 mV correct @ {d} ns": "-" for d in ("0.75", "1.0", "2.0")},
                     "worst decision, +/-3, 10 mV (ns)": round(r["worst_t_ns"], 3), "mean energy (fJ)": round(r["energy_mean_fj"], 1)})
    for key, label in POSTLAYOUT_R17.items():
        r = r17[key]
        rows.append({"variant": label,
                     **{f"+/-3, 10 mV correct @ {d} ns": r[f"3_10mv_correct@{d}ns"] for d in ("0.75", "1.0", "2.0")},
                     **{f"+/-1 mV correct @ {d} ns": r.get(f"1mv_correct@{d}ns", "-") for d in ("0.75", "1.0", "2.0")},
                     "worst decision, +/-3, 10 mV (ns)": round(r["3_10mv_worst_t_ns"], 3), "mean energy (fJ)": round(r["energy_mean_fj"], 1)})
    return pd.DataFrame(rows).set_index("variant")


def wide_rc_table(data: dict) -> pd.DataFrame:
    """r17 against r19 on the same inputs (+/-1, +/-3 mV): 45 PVT conditions, code 0, nominal devices."""
    rows = []
    for name, key, label in WIDE_RC:
        records = [r for r in _jsonl(data, name) if r["variant"] == key and abs(r["v_mv"]) in (1.0, 3.0)]
        if len(records) != 180:
            raise RuntimeError(f"{name} {key}: expected 180 rows")
        ones = [r for r in records if abs(r["v_mv"]) == 1.0]
        threes = [r for r in records if abs(r["v_mv"]) == 3.0]
        row = {"variant": label}
        for d in ("0.75", "1.0", "2.0"):
            row[f"+/-1 mV correct @ {d} ns"] = f"{sum(r['at'][d] == 'correct' for r in ones)}/90"
        row["+/-3 mV correct @ 1.0 ns"] = f"{sum(r['at']['1.0'] == 'correct' for r in threes)}/90"
        row["wrong decisions"] = sum(v == "wrong" for r in records for v in r["at"].values())
        row["worst decision, +/-1 mV (ns)"] = round(max(r["t_ns"] or math.inf for r in ones), 2)
        row["mean energy (fJ)"] = round(sum(r["energy_fj"] for r in records) / len(records))
        rows.append(row)
    return pd.DataFrame(rows).set_index("variant")


def bin_stress_table(data: dict) -> pd.DataFrame:
    """r20 and r21: atlas width skew against a bin-neutral current skew (instance m = 1 +/- 0.04)."""
    summary = _json("r20/bin_stress_summary.json")
    dc = _json("r20/eff_skew.json")
    scores = _json("r21/r21_score_refined.json")
    rows = []
    for design in BIN_DESIGNS:
        s = summary[design]
        if s["validated"] != s["conditions"] or s["max_dev_from_archive_mv"] > 0.2:
            raise RuntimeError(f"r20 {design}: width mode does not reproduce the archive")
        skew = dc[f"{s['input_device']}|tt|{s['input_w_um']:g}"]
        row = {"design": design, "input pair": f"{s['input_device']}, W {s['input_w_um']:g} um",
               "DC current skew, TT (ideal 0.040)": f"{min(skew):.3f}-{max(skew):.3f}",
               "median |offset|, width skew (mV)": round(s["width_abs_median_mv"], 1),
               "median |offset|, m skew (mV)": round(s["mult_abs_median_mv"], 1),
               "width / m (LSQ)": round(s["lsq_slope"], 2)}
        for mode in ("width", "m"):
            r = scores.get(f"{'mult' if mode == 'm' else 'width'}|{design}")
            row[f"1 ns correct (fully passing), {mode} skew"] = \
                f"{r['correct']}/392 ({r['fully_passing_conditions']}/49)" if r else "-"
        rows.append(row)
    return pd.DataFrame(rows).set_index("design")


def trim_range_table(data: dict) -> pd.DataFrame:
    """r22: nominal trim range of the sealed designs over the 45 PVT conditions (no skew, no mismatch)."""
    records = _jsonl(data, "r22/range.jsonl")
    rows = []
    for design in ATLAS_DESIGNS:
        rs = sorted((r for r in records if r["design"] == design), key=lambda r: r["half_range_mv"])
        if len(rs) != 45 or max(abs(r["b0_mv"]) for r in rs) > 0.5:
            raise RuntimeError(f"r22 {design}: expected 45 nominal ranges centred on 0 mV")
        half = [r["half_range_mv"] for r in rs]
        corner, vdd, temp = rs[0]["cond"]
        rows.append({"design": design, "trim codes": f"+/-{rs[0]['max_code']}",
                     "half-range, median (mV)": round(float(pd.Series(half).median()), 1),
                     "half-range, narrowest (mV)": round(half[0], 1),
                     "narrowest condition": f"{corner.upper()} {vdd:g} V {temp:g} C",
                     "conditions below 25 mV": sum(h < 25 for h in half)})
    return pd.DataFrame(rows).set_index("design")


def noise_sigma(data: dict, pattern: str) -> tuple[float, float, float]:
    """r23: input-referred thermal-noise sigma (mV) with its 95% chi-square-normal interval."""
    records = _jsonl(data, pattern)
    if sorted(r["realization"] for r in records) != list(range(NOISE_REALIZATIONS)) or any(r["edge"] for r in records):
        raise RuntimeError(f"{pattern}: expected {NOISE_REALIZATIONS} interior noise realizations")
    sigma = float(np.std([r["noise_mv"] for r in records], ddof=1))
    half = 1.96 / math.sqrt(2 * (len(records) - 1))
    return sigma, sigma * (1 - half), sigma * (1 + half)


def noise_table(data: dict) -> pd.DataFrame:
    """r23: transient thermal noise turns a residual m into an error rate P = Phi(-(v - |m|) / sigma_n)."""
    rows = []
    for label, condition, pattern, noisy, mc_pattern in NOISE_VARIANTS:
        sigma, low, high = noise_sigma(data, pattern)
        row = {"variant": label, "condition": condition, "noisy devices": noisy,
               "sigma_n (mV, 95% CI)": f"{sigma:.2f} ({low:.2f}-{high:.2f})",
               "trim residual rms (mV, covered)": "-", "rms |m| / sigma_n": "-",
               "median P(wrong) at +/-1 mV": "-", "input for 1e-6 errors, median / p90 (mV)": "-"}
        if mc_pattern:
            records = _jsonl(data, mc_pattern)
            if sorted(r["seed"] for r in records) != list(range(len(records))):
                raise RuntimeError(f"{mc_pattern}: Monte Carlo seeds are incomplete or duplicated")
            m = np.array([abs(r["m_mv"]) for r in records if r["covered"]])
            rms = float(np.sqrt(np.mean(m ** 2)))
            p_wrong = [0.5 * math.erfc((1.0 - x) / sigma / math.sqrt(2)) for x in m]
            need = m + NOISE_Z_1E6 * sigma
            row.update({"trim residual rms (mV, covered)": f"{rms:.2f} ({len(m)}/{len(records)})",
                        "rms |m| / sigma_n": round(rms / sigma, 2),
                        "median P(wrong) at +/-1 mV": f"{float(np.median(p_wrong)):.3f}",
                        "input for 1e-6 errors, median / p90 (mV)":
                            f"{np.percentile(need, 50):.1f} / {np.percentile(need, 90):.1f}"})
        rows.append(row)
    return pd.DataFrame(rows).set_index(["variant", "condition"])


def _condition(c) -> str:
    return f"{c[0].upper()} {c[1]:g} V {c[2]:g} C"


def _r24() -> dict:
    report = _json("r24/r24_report.json")
    benches = [(v["bench"], v["design"], tuple(v["condition"])) for v in report["validation"]]
    if benches != [(b, d, tuple(c)) for b, d, c, _ in ISF_BENCHES]:
        raise RuntimeError("r24 validation benches changed")
    return report


def isf_table(data: dict) -> pd.DataFrame:
    """r24: noise from the measured impulse sensitivity (ISF) vs the r23 transient-noise Monte Carlo, realization
    by realization (same noise sequences). Original-bench MC shifts are re-checked against the r23 archive."""
    rows = []
    for v, (bench, design, condition, r23_pattern) in zip(_r24()["validation"], ISF_BENCHES):
        mc, isf = np.array(v["mc_mv"]), np.array(v["isf_mv"])
        if v["realization"] != list(range(NOISE_REALIZATIONS)) or v["edge"]:
            raise RuntimeError(f"r24 {bench} {design}: expected {NOISE_REALIZATIONS} interior realizations")
        if r23_pattern:
            archived = sorted(_jsonl(data, r23_pattern), key=lambda r: r["realization"])
            if not np.allclose([r["noise_mv"] for r in archived], mc, rtol=0, atol=1e-9):
                raise RuntimeError(f"r24 {design}: MC shifts differ from the r23 archive")
        sigma = float(np.std(mc, ddof=1))
        half = 1.96 / math.sqrt(2 * (len(mc) - 1))
        slope = np.polyfit(isf, mc, 1)[0]
        share = v["group_sigma_mv"]["input"] ** 2 / v["isf_sigma_mv"] ** 2
        rows.append({"bench": bench, "variant": ISF_LABELS[design], "condition": _condition(condition),
                     "ISF sigma_n (mV)": round(v["isf_sigma_mv"], 3),
                     "MC sigma_n (mV, 95% CI)": f"{sigma:.3f} ({sigma * (1 - half):.2f}-{sigma * (1 + half):.2f})",
                     "corr": round(float(np.corrcoef(isf, mc)[0, 1]), 4), "slope": round(float(slope), 3),
                     "rms(MC - ISF) (uV)": round(float(np.sqrt(np.mean((mc - isf) ** 2))) * 1e3, 1),
                     "input-pair share": f"{share:.0%}", "x_half (ps)": v["x_half_ps"]})
    return pd.DataFrame(rows).set_index(["bench", "variant", "condition"])


def isf_atlas_table(data: dict) -> pd.DataFrame:
    """r24: sigma_n (mV) of the shipped 4b design at the 45 PVT conditions from the ISF (pinned bench), with the
    input step that keeps decision errors below 1e-6 (4.753 sigma_n, noise only)."""
    rows = _jsonl(data, "r24/atlas_pinned_lvt_balanced_4b.jsonl")
    if len(rows) != 45 or len({tuple(r["condition"]) for r in rows}) != 45 or any(r["edge"] for r in rows):
        raise RuntimeError("r24 atlas: expected 45 distinct interior PVT conditions")
    frame = pd.DataFrame([{"corner": r["condition"][0].upper(),
                           "VDD / T": f"{r['condition'][1]:g} V {r['condition'][2]:g} C",
                           "sigma": r["sigma_mv"]} for r in rows])
    table = frame.pivot(index="corner", columns="VDD / T", values="sigma").round(2)
    order = sorted({tuple(r["condition"][1:]) for r in rows})
    table = table[[f"{v:g} V {t:g} C" for v, t in order]]
    worst = max(rows, key=lambda r: r["sigma_mv"])
    table.attrs["worst"] = (_condition(worst["condition"]), worst["sigma_mv"], NOISE_Z_1E6 * worst["sigma_mv"])
    return table


def noise_law_table(data: dict) -> pd.DataFrame:
    """r24b: integration-phase law sigma_in^2 = 4kT gamma (Id/gm) / Q_int, calibrated once on the PVT atlas and
    used to predict the input-common-mode sweep before the exact ISF (and, at 0.6 V, a fresh MC) was run."""
    report = _r24()
    ratio = np.array([r["sigma_in_mv"] / r["sigma_cf_in_mv"] for r in report["scaling"]])
    if len(ratio) != 45:
        raise RuntimeError("r24 closed-form fit: expected 45 conditions")
    k = float(ratio.mean())
    rows = []
    for r in report["cm_sweep"]:
        pred = k * r["sigma_cf_in_mv"]
        rows.append({"input CM (V)": r["cm_v"], "Id/gm (mV)": round(r["id_over_gm_mV"]),
                     "gamma": round(r["gamma"], 2), "Q_int (fC)": round(r["q_int_fC"], 1),
                     "t_int (ps)": round(r["t_int_ps"]),
                     "predicted sigma_in (mV)": round(pred, 3), "exact sigma_in (mV)": round(r["sigma_in_mv"], 3),
                     "error": f"{pred / r['sigma_in_mv'] - 1:+.0%}", "total sigma_n (mV)": round(r["sigma_mv"], 3),
                     "input-pair share": f"{r['input_share']:.0%}", "dq100 (ps)": round(r["dq100_ps"]),
                     "sigma_n^2 x dq100 (mV^2 ps)": round(r["sigma_mv"] ** 2 * r["dq100_ps"])})
    table = pd.DataFrame(rows).set_index("input CM (V)")
    table.attrs["calibration"] = (k, float(ratio.std()), float(ratio.min()), float(ratio.max()), len(ratio))
    return table


def memory_table(data: dict) -> pd.DataFrame:
    """r24: decision memory. Threshold of the last cycle after two earlier decisions on a held prior input,
    thr = a sign(prior) + c prior (TT 1.8 V 27 C): as built, with the off trim branches deleted, and with
    the series switch moved to the x side (the swapped trim also changes the trim steps, last columns)."""
    fits = {v: _json(f"r24/memory_tt_1.8V_27C{s}.json")["fit"] for v, s in
            (("as built", ""), ("off trim branches deleted", "_strip"), ("switch on the x side", "_swap"))}
    steps = _json("r24/trim_steps_swap.json")
    rows = []
    for design in ("baseline", "lvt_balanced_4b", "unit6_w6", "u6_w12_l05"):
        row = {"variant": ISF_LABELS[design]}
        for v, fit in fits.items():
            row[f"{v}: a (uV) / c"] = f"{fit[design]['decision_uv']:.1f} / {fit[design]['input_carry']:.2%}"
        if design in steps:
            for v in ("original", "swap"):
                s = steps[design][v]
                msb = next(k for k in s if k not in ("code0", "Vtp0"))
                row[f"trim LSB / MSB step, {v} (mV)"] = f"{s['Vtp0'] - s['code0']:+.2f} / {s[msb] - s['code0']:+.1f}"
        rows.append(row)
    return pd.DataFrame(rows).set_index("variant").fillna("-")


def gain_law_table(data: dict) -> pd.DataFrame:
    """r24c: total noise from the input-pair term and the integration-phase gain,
    sigma_n^2 = sigma_in^2 (1 + (A0 / A_int)^2), A_int = (gm/Id) VDD/2; A0 fitted once on the 45 PVT conditions
    and applied unchanged to the input-common-mode sweep."""
    law = _json("r24/gain_law.json")
    if len(law["rows"]) != 45 or len(law["leave_one_corner_out"]) != 5:
        raise RuntimeError("r24c gain law: expected 45 conditions and 5 held-out corners")
    rows = [{"input CM (V)": r["cm_v"], "A_int": round(r["a_int"], 1), "exact sigma_n (mV)": round(r["sigma_mv"], 3),
             "law, exact sigma_in (mV)": round(r["pred_mv"], 3), "error": f"{r['err']:+.1%}",
             "law, closed-form sigma_in (mV)": round(r["pred_closed_mv"], 3), "error, closed form": f"{r['err_closed']:+.0%}"}
            for r in law["cm_sweep"]]
    table = pd.DataFrame(rows).set_index("input CM (V)")
    loco = [v["a0"] for v in law["leave_one_corner_out"].values()]
    table.attrs.update(a0=law["a0"], k=law["k_input"], pvt=law["pvt_exact_in"], closed=law["pvt_closed_form"],
                       input_only=law["pvt_input_only"], loco=(min(loco), max(loco),
                       max(v["max"] for v in law["leave_one_corner_out"].values())),
                       a_int=law["a_int_range_pvt"], share=(law["reset_vs_pre_edge_share_max_abs"], law["share_benches"]))
    return table


PROBE_MODES = (("base", "as built"), ("self", "own value forced"),
               ("short", "pair shorted"), ("transplant", "opposite prior forced"))


def memory_probe_table(data: dict) -> pd.DataFrame:
    """r24c: causal probe. The floating trim nodes are left in place and only their state is set during the last
    reset (ideal switches, 20.0-21.9 ns): thr = a sign(prior) + c prior, a in uV (TT 1.8 V 27 C)."""
    probe = _json("r24/memory_probe.json")
    rows = []
    for design in ("baseline", "lvt_balanced_4b", "unit6_w6", "u6_w12_l05"):
        fit = probe["fit"][design]
        split = probe["node_split_mv"][design]
        rows.append({"variant": ISF_LABELS[design],
                     "node split, prior +5 vs -5 (mV)": f"{min(split.values()):+.2f} to {max(split.values()):+.2f}",
                     **{f"{label}: a (uV) / c": f"{fit[m]['decision_uv']:.1f} / {fit[m]['input_carry']:.2%}"
                        for m, label in PROBE_MODES}})
    return pd.DataFrame(rows).set_index("variant")


FIX_LABELS = {"original": "as built", "swap": "series switch on the x side",
              "precharge": "precharge nodes to VDD (8 PMOS)", "equalize": "equalize sp<k>/sn<k> (4 NMOS + inverter)"}


def memory_fix_table(data: dict) -> pd.DataFrame:
    """r24c: memory fixes on the shipped 4b trim. Memory at TT, the full 31-code transfer at the r7 conditions,
    the half range at the 45 PVT conditions (earlier cycles pinned at -5 mV), energy per comparison at TT
    (VDD plus clock-edge charge), and the light 6-bit check."""
    fix = _json("r24/memory_fix_lvt_balanced_4b.json")
    spot = _json("r24/memory_spot_unit6_w6.json")
    energy = _json("r24/memory_energy_lvt_balanced_4b.json")
    energy6 = _json("r24/memory_energy_unit6_w6.json")
    conds = ("tt 1.8 27", "ss 1.62 -40", "fs 1.62 -40")
    rows = []
    for v, label in FIX_LABELS.items():
        s, m = fix["summary"][v], fix["memory"][v]
        if len(s["half_range_mv"]) != 45:
            raise RuntimeError(f"r24c {v}: expected 45 half ranges")
        tr = [s["transfer"].get(c) for c in conds]
        row = {"fix": label, "memory a (uV) / c": f"{m['decision_uv']:.1f} / {m['input_carry']:.2%}",
               "LSB TT / SS / FS (mV)": " / ".join("-" if t is None else f"{t['lsb_mv']:+.2f}" for t in tr),
               "max |DNL| TT / SS / FS (LSB)": " / ".join("-" if t is None else f"{t['dnl_max_lsb']:.2f}" for t in tr),
               "monotonic": all(t is not None and t["monotonic"] for t in tr),
               "half range min / median (mV)": "{:.1f} / {:.1f}".format(*s["half_range_min_median_max"][:2]),
               "range out of span": s["edge_failures"]}
        if f"{v} 0" in energy:
            e = [energy[f"{v} {k}"]["vdd_fj"] + energy[f"{v} {k}"]["clk_fj"] for k in (0, 15)]
            row["energy code 0 / 15 (fJ)"] = f"{e[0]:.0f} / {e[1]:.0f}"
        if v in spot["memory"]:
            e6 = energy6[f"{v} 0"]["vdd_fj"] + energy6[f"{v} 0"]["clk_fj"]
            lsb6 = spot["summary"][v]["tt 1.8 27"]["lsb_mv"]
            row["unit6_w6: a (uV) / LSB TT (mV) / energy (fJ)"] = \
                f"{spot['memory'][v]['decision_uv']:.1f} / {lsb6:+.2f} / {e6:.0f}"
        rows.append(row)
    return pd.DataFrame(rows).set_index("fix").fillna("-")


def fix_mc_table(data: dict) -> pd.DataFrame:
    """r24c: the r22 mismatch Monte Carlo (same seeds and device draws) with the equalize fix added, and the
    nominal half range of each variant at that condition (r22 bench, no mismatch)."""
    fix_range = {tuple(r["cond"]): r["half_range_mv"] for r in _json("r24/fixrange_lvt_balanced_4b.json")}
    r22_range = {tuple(r["cond"]): r["half_range_mv"] for r in _jsonl(data, "r22/range.jsonl")
                 if r["design"] == "lvt_balanced_4b"}
    if len(fix_range) != 45 or set(fix_range) != set(r22_range):
        raise RuntimeError("r24c: expected the 45 r22 range conditions")
    rows = []
    for corner in ("sf", "ff"):
        cond = f"{corner.upper()} 1.95 V 125 C"
        for label, pattern, half in (
                ("as built (r22)", f"r22/mc_{corner}1.95V125C_lvt_balanced_4b_*.jsonl", r22_range),
                ("equalize fix", f"r24/fixmc_{corner}1.95V125C_lvt_balanced_4b.jsonl", fix_range)):
            recs = _jsonl(data, pattern)
            row = {"variant": label, "condition": cond, "nominal half range (mV)": round(half[(corner, 1.95, 125.0)], 1),
                   **_mc_summary(recs, 40)}
            row["|m| rms (mV)"] = round(math.sqrt(np.mean([r["m_mv"] ** 2 for r in recs if r["seed"] < 40 and r["covered"]])), 2)
            row["uncovered seeds (residual m, mV)"] = ", ".join(
                f"{r['seed']} ({r['m_mv']:+.1f})" for r in sorted(recs, key=lambda r: r["seed"])
                if r["seed"] < 40 and not r["covered"]) or "-"
            rows.append(row)
    table = pd.DataFrame(rows).set_index(["condition", "variant"])
    table.attrs.update(narrowest=(min(r22_range.values()), min(fix_range.values())),
                       below_25=(sum(v < 25 for v in r22_range.values()), sum(v < 25 for v in fix_range.values())))
    return table


TRIM5 = "eq5_l100"
TRIM5_LABEL = "5b + equalize (r25)"


def _gate_area_um2(trim_bits: int) -> float:
    """Gate-area proxy (comparator_atlas.designs; equalizer switches not counted) of the shipped core."""
    from dataclasses import replace

    from comparator_atlas.designs import DESIGNS
    return replace(DESIGNS["lvt_balanced_4b"], trim_bits=trim_bits).gate_area_um2


def trim_length_table(data: dict) -> pd.DataFrame:
    """r25: the shipped core with a 5-bit binary trim and the equalizer, against trim device length L.
    Nominal end-point half range and end-point LSB (code +-31), and the full 63-code transfer at the two hot
    corners where it was run."""
    screen = {}
    for r in _jsonl(data, "r25/screen.jsonl"):
        screen.setdefault(r["trim_l"], {})[r["cond"][0]] = r
    transfer = {}
    for n in data["files"]:
        if Path(n).match("r25/dnl_*.json"):
            for r in _json(n):
                transfer.setdefault(r["design"], {})[r["cond"][0]] = r
    rows = []
    for length, c in sorted(screen.items()):
        if set(c) != {"tt", "sf", "ff"}:
            raise RuntimeError(f"r25 screen at L {length}: expected TT, SF and FF")
        t = transfer.get(c["tt"]["design"])
        rows.append({"trim L (um)": length,
                     "half range TT / SF / FF (mV)": " / ".join(f"{c[k]['half_range_mv']:.1f}" for k in ("tt", "sf", "ff")),
                     "end-point LSB TT / SF / FF (mV)": " / ".join(f"{c[k]['lsb_mv']:+.2f}" for k in ("tt", "sf", "ff")),
                     "63 codes at SF / FF hot: monotonic, max |DNL| (LSB)": "-" if t is None else " / ".join(
                         f"{'yes' if t[k]['monotonic'] else 'no'}, {t[k]['dnl_max_lsb']:.1f}" for k in ("sf", "ff"))})
    return pd.DataFrame(rows).set_index("trim L (um)")


def trim5_mc_table(data: dict) -> pd.DataFrame:
    """r25: paired mismatch Monte Carlo (same seeds; the core and the 4b-named trim devices keep their r22/r3 draw)
    of the shipped 4b trim, the equalized 4b trim and the equalized 5b trim (L 1), with the nominal half range at
    each condition. attrs: energy per comparison at TT (VDD plus clock edge, code 0), gate-area proxy, memory."""
    r22_range = {tuple(r["cond"]): r["half_range_mv"] for r in _jsonl(data, "r22/range.jsonl")
                 if r["design"] == "lvt_balanced_4b"}
    fix_range = {tuple(r["cond"]): r["half_range_mv"] for r in _json("r24/fixrange_lvt_balanced_4b.json")}
    r25_range = {tuple(r["cond"]): r["half_range_mv"] for r in _json(f"r25/range_{TRIM5}.json")}
    if len(r25_range) != 45 or set(r25_range) != set(r22_range):
        raise RuntimeError("r25: expected the 45 r22 range conditions")
    benches = []
    for corner in ("sf", "ff"):
        tag = f"{corner}1.95V125C"
        benches += [(f"{corner.upper()} 1.95 V 125 C", (corner, 1.95, 125.0), label, pattern, half) for label, pattern, half in (
            ("4b as built (r22)", f"r22/mc_{tag}_lvt_balanced_4b_*.jsonl", r22_range),
            ("4b + equalize (r24c)", f"r24/fixmc_{tag}_lvt_balanced_4b.jsonl", fix_range),
            (TRIM5_LABEL, f"r25/mc_{tag}_{TRIM5}.jsonl", r25_range))]
    benches += [("TT 1.8 V 27 C", ("tt", 1.8, 27.0), "4b as built (r3)", "r3/mc_lvt_balanced_4b_*.jsonl", r22_range),
                ("TT 1.8 V 27 C", ("tt", 1.8, 27.0), TRIM5_LABEL, f"r25/mc_tt1.8V27C_{TRIM5}.jsonl", r25_range)]
    rows = []
    for cond, key, label, pattern, half in benches:
        recs = [r for r in _jsonl(data, pattern) if r["seed"] < 40]
        by_seed = {r["seed"]: r for r in recs}
        row = {"condition": cond, "variant": label, "nominal half range (mV)": round(half[key], 1),
               **_mc_summary(recs, 40)}
        row["|m| rms (mV)"] = round(math.sqrt(np.mean([r["m_mv"] ** 2 for r in recs if r["covered"]])), 2)
        row["seeds 3 / 13: m (mV)"] = " / ".join(
            f"{by_seed[s]['m_mv']:+.2f}" + ("" if by_seed[s]["covered"] else " (out of range)") for s in (3, 13))
        rows.append(row)
    table = pd.DataFrame(rows).set_index(["condition", "variant"])
    e4 = _json("r24/memory_energy_lvt_balanced_4b.json")
    e5 = _json(f"r25/memory_energy_{TRIM5}.json")
    mem = _json(f"r25/memory_{TRIM5}.json")
    fj = {k: e[f"equalize {c}"]["vdd_fj"] + e[f"equalize {c}"]["clk_fj"] for k, e, c in (("4b", e4, 0), ("5b", e5, 0))}
    table.attrs.update(energy_fj=(fj["4b"], fj["5b"]), area_um2=(_gate_area_um2(4), _gate_area_um2(5)),
                       memory_uv={v: m["decision_uv"] for v, m in mem.items()},
                       narrowest=min(r25_range.values()), median=float(np.median(list(r25_range.values()))))
    return table


# r26 / r26b: (study, design, trim layout, bits, input-pair and tail scale k); r25 is the k 1 width-binary reference
UNIT_DESIGNS = (("r25", TRIM5, "width-binary", 5, 1.0), ("r26", "s5_k125", "width-binary", 5, 1.25),
                ("r26", "s6_k150", "width-binary", 6, 1.5), ("r26b", "u5_k125", "unit cell", 5, 1.25),
                ("r26b", "u5_k150", "unit cell", 5, 1.5))
UNIT_SELECTED = "u5_k150"
BIT_WEIGHT_CONDS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("fs", 1.62, -40.0), ("sf", 1.95, 125.0),
                    ("ff", 1.95, 125.0))


def _scaled_area_um2(bits: int, k: float) -> float:
    """Gate-area proxy of the shipped core with the input pair and tail widened by k; the proxy counts the trim
    as 2 * max_code unit cells, so a width-binary and a unit-cell trim of the same bits have the same area."""
    from dataclasses import replace

    from comparator_atlas.designs import DESIGNS
    core = DESIGNS["lvt_balanced_4b"]
    return replace(core, trim_bits=bits, input_w=core.input_w * k, tail_w=core.tail_w * k).gate_area_um2


def bit_weight_table(data: dict) -> pd.DataFrame:
    """r26b: single-bit weights |b(2^k) - b(0)| (nominal, bits 0-4) of the 5b k 1.25 trim built width-binary (bit k:
    one trim device W 0.42 * 2^k and one switch W 2^k) or from unit cells (bit k: 2^k cells W 0.42 / W 1)."""
    rows = {}
    for r in _jsonl(data, "r26b/weights.jsonl"):
        rows[(r["design"], tuple(r["cond"]))] = r
    out = []
    for cond in BIT_WEIGHT_CONDS:
        row = {"condition": _condition(list(cond))}
        for design, label in (("s5_k125", "width-binary"), ("u5_k125", "unit cell")):
            r = rows[(design, cond)]
            b = r["b_mv"]
            w = [(abs(b[str(1 << i)] - b["0"]) + abs(b[str(-(1 << i))] - b["0"])) / 2 for i in range(5)]
            row[f"{label}: bit 0-4 weights (mV)"] = " ".join(f"{x:.1f}" for x in w)
            row[f"{label}: w4 / w0"] = round(w[4] / w[0], 1)
            row[f"{label}: full range (mV)"] = round((b["-31"] - b["31"]) / 2, 1)
        out.append(row)
    table = pd.DataFrame(out).set_index("condition")
    table.attrs["spread"] = {label: max(table[f"{label}: full range (mV)"]) / min(table[f"{label}: full range (mV)"])
                             for label in ("width-binary", "unit cell")}
    return table


def unit_trim_table(data: dict) -> pd.DataFrame:
    """r26/r26b: the equalized trim with the input pair and tail widened by k (width-binary, r26) and built from
    unit cells (r26b), against r25. Nominal 63/127-code transfer, 45-condition half range, paired MC over SF and FF
    1.95 V 125 C and TT (40 seeds each, 1 ns), TT energy per comparison (code 0, VDD plus clock edge), area."""
    rows = []
    for study, design, layout, bits, k in UNIT_DESIGNS:
        transfer = {r["cond"][0]: r for r in _json(f"{study}/dnl_{design}.json")}
        if set(transfer) != {"tt", "ss", "fs", "sf", "ff"}:
            raise RuntimeError(f"{design}: expected the transfer at TT, SS, FS, SF and FF")
        step = {c: abs(r.get("max_abs_step_mv", r.get("max_step_mv"))) for c, r in transfer.items()}
        half = [r["half_range_mv"] for r in _json(f"{study}/range_{design}.json")]
        if len(half) != 45:
            raise RuntimeError(f"{design}: expected 45 range conditions")
        recs = []
        for tag in ("sf1.95V125C", "ff1.95V125C", "tt1.8V27C"):
            part = [r for r in _jsonl(data, f"{study}/mc_{tag}_{design}.jsonl") if r["seed"] < 40]
            _mc_summary(part, 40)
            recs += part
        ok = {band: sum(e["outcome"] == "correct" for r in recs for e in r["evals"]
                        if abs(e["v_mv"]) == band and e["deadline_ns"] == 1.0) for band in (1, 3)}
        e = _json(f"{study}/memory_energy_{design}.json")["equalize 0"]
        rows.append({
            "design": design, "trim": layout, "bits": bits, "input pair / tail scale": k,
            "TT LSB / max step (mV)": f"{transfer['tt']['lsb_mv']:+.2f} / {step['tt']:.2f}",
            "cold max step (mV)": round(max(step["ss"], step["fs"]), 1),
            "hot max |DNL| (LSB)": round(max(transfer[c]["dnl_max_lsb"] for c in ("sf", "ff")), 1),
            "45-condition half range min / median / max (mV)":
                f"{min(half):.1f} / {np.median(half):.1f} / {max(half):.1f}",
            "covered (of 120)": sum(r["covered"] for r in recs),
            "+/-1 mV @ 1 ns (of 240)": ok[1], "+/-3 mV @ 1 ns (of 240)": ok[3],
            "max |m| (mV)": round(max(abs(r["m_mv"]) for r in recs if r["covered"]), 2),
            "TT energy, code 0 (fJ)": round(e["vdd_fj"] + e["clk_fj"]),
            "gate area (um^2)": round(_scaled_area_um2(bits, k), 1)})
    return pd.DataFrame(rows).set_index("design")


# r26c: u5_k150 (r26b, one minimum equalizer per bit) vs e5_k150 (2^k unit equalizers per bit, clkb inverter m 4)
EQ_DESIGNS = (("u5_k150", "r26b/dnl_u5_k150.json", "minimum equalizer per bit", 5, 1),
              ("e5_k150", "r26c/dnl_e5_k150.json", "unit-cell equalizer", 31, 4))
EQ_SEEDS = 200
EQ_DEVICE_UM2 = 0.42 * 0.15


def _clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    def cdf(j, p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(j + 1))

    def solve(f, target):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) > target else (lo, mid)
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(lambda p: cdf(k - 1, p), 1 - alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: cdf(k, p), alpha / 2)
    return lower, upper


def equalizer_mc_table(data: dict) -> pd.DataFrame:
    """r26c: 200 paired MC seeds at the five DNL conditions for the r26b unit-cell trim (u5_k150) and the same trim
    with its equalizer also built from unit cells (e5_k150). Static: |m| <= 1 mV (borderline seeds re-bisected to
    0.01 mV). At 1 ns: both +-1 mV inputs decided correctly. Exact 95% Clopper-Pearson intervals over seeds."""
    rows = []
    for design, dnl, label, eq_gates, inv_m in EQ_DESIGNS:
        seeds = _jsonl(data, f"r26c/seeds_{design}.jsonl")
        transfer = {r["cond"][0]: r for r in _json(dnl)}
        for cond in (*BIT_WEIGHT_CONDS, None):
            part = [r for r in seeds if cond is None or tuple(r["cond"]) == cond]
            if cond is not None and sorted(r["seed"] for r in part) != list(range(EQ_SEEDS)):
                raise RuntimeError(f"{design} {cond}: Monte Carlo seeds are incomplete or duplicated")
            m = np.array([r.get("fine_m_mv", r["m_mv"]) for r in part])
            static = int(np.sum(np.abs(m) <= 1.0))
            ok1 = sum(r["out_1mv_1ns"] == ["correct", "correct"] for r in part)
            ok3 = sum(r["out_3mv_1ns"] == ["correct", "correct"] for r in part)
            dec = [o for r in part for o in r["out_1mv_1ns"]]
            lo, hi = _clopper_pearson(ok1, len(part))
            row = {"condition": "pooled" if cond is None else _condition(list(cond)), "design": design,
                   "covered": f"{sum(r['covered'] for r in part)}/{len(part)}",
                   "static |m| <= 1 mV": f"{static}/{len(part)}",
                   "+/-1 mV @ 1 ns (seeds)": f"{ok1}/{len(part)}",
                   "95% CI": f"{lo:.3f} - {hi:.3f}",
                   "wrong / unresolved decisions": f"{dec.count('wrong')} / {dec.count('unresolved')}",
                   "+/-3 mV @ 1 ns (seeds)": f"{ok3}/{len(part)}",
                   "|m| rms / max (mV)": f"{np.sqrt(np.mean(m ** 2)):.2f} / {np.max(np.abs(m)):.2f}"}
            if cond is None:
                row["LSB / max step (mV), DNL (LSB)"] = "-"
            else:
                t = transfer[cond[0]]
                row["LSB / max step (mV), DNL (LSB)"] = (f"{abs(t['lsb_mv']):.2f} / {t['max_abs_step_mv']:.2f}, "
                                                         f"{t['dnl_max_lsb']:.2f}" + ("" if t["monotonic"] else " (non-mono)"))
            rows.append(row)
    table = pd.DataFrame(rows).set_index(["condition", "design"])
    energy, area, half = {}, {}, {}
    for design, _, _, eq_gates, inv_m in EQ_DESIGNS:
        study = "r26b" if design.startswith("u") else "r26c"
        e = _json(f"{study}/memory_energy_{design}.json")["equalize 0"]
        energy[design] = e["vdd_fj"] + e["clk_fj"]
        area[design] = (eq_gates + 2 * inv_m) * EQ_DEVICE_UM2
        half[design] = [r["half_range_mv"] for r in _json(f"{study}/range_{design}.json")]
    table.attrs.update(energy_fj=energy, equalizer_area_um2=area, core_area_um2=_scaled_area_um2(5, 1.5),
                       half_range_mv={d: (min(h), float(np.median(h)), max(h)) for d, h in half.items()})
    return table


def inverter_sweep_table(data: dict) -> pd.DataFrame:
    """r26c: the clkb inverter that drives the 31 unit equalizers sets the trim gain (e5_k150; nominal steps of codes
    0-11 at 0.01 mV, TT energy at code 0)."""
    rows = []
    for r in _json("r26c/inv_sweep.json"):
        row = {"clkb inverter m": r["inv_m"]}
        for c, name in (("ss", "SS 1.62 V -40 C"), ("tt", "TT 1.8 V 27 C"), ("sf", "SF 1.95 V 125 C")):
            row[f"{name} step min / mean / max (mV)"] = " / ".join(f"{x:.2f}" for x in r[f"{c}_step_min_mean_max_mv"])
        row["SF / SS mean step"] = round(r["sf_step_min_mean_max_mv"][1] / r["ss_step_min_mean_max_mv"][1], 1)
        row["TT energy, code 0 (fJ)"] = round(r["energy_fj_code0"])
        rows.append(row)
    if [r["clkb inverter m"] for r in rows] != [1, 2, 4, 8]:
        raise RuntimeError("r26c inverter sweep rows changed")
    return pd.DataFrame(rows).set_index("clkb inverter m")


# r26d: input-pair scale k of the unit-equalizer trim; the archive study that holds each design's files
K_DESIGNS = (("e5_k150", "r26c", 1.5), ("e5_k175", "r26d", 1.75))
SEGMENT_SCHEMES = (("binary", "binary (5 bits)"), ("seg_b3", "2 thermometer MSBs + 3 binary"),
                   ("seg_b2", "3 thermometer MSBs + 2 binary"), ("seg_b1", "4 thermometer MSBs + 1 binary"),
                   ("thermometer", "full thermometer"))


def input_scale_table(data: dict) -> pd.DataFrame:
    """r26d: the unit-equalizer trim at input-pair scale 1.5 (r26c) and 1.75, same 200 paired MC seeds at the five
    DNL conditions. 'MC 1-bit step' is the mean local step of the seeds that sit between codes one bit apart; at
    the hot corners it is 10-17% above the nominal LSB."""
    rows = []
    for design, study, k in K_DESIGNS:
        seeds = _jsonl(data, f"{study}/seeds_{design}.jsonl")
        transfer = {r["cond"][0]: r for r in _json(f"{study}/dnl_{design}.json")}
        carry = {c["cond"][0]: c for c in _json(f"r26d/carry_{design}.json")["conditions"]}
        for cond in (*BIT_WEIGHT_CONDS, None):
            part = [r for r in seeds if cond is None or tuple(r["cond"]) == cond]
            if cond is not None and sorted(r["seed"] for r in part) != list(range(EQ_SEEDS)):
                raise RuntimeError(f"{design} {cond}: Monte Carlo seeds are incomplete or duplicated")
            m = np.array([r.get("fine_m_mv", r["m_mv"]) for r in part])
            b0 = np.array([r["b0_mv"] for r in part])
            ok1 = sum(r["out_1mv_1ns"] == ["correct", "correct"] for r in part)
            dec = [o for r in part for o in r["out_1mv_1ns"]]
            lo, hi = _clopper_pearson(ok1, len(part))
            row = {"condition": "pooled" if cond is None else _condition(list(cond)), "input pair scale k": k,
                   "covered": f"{sum(r['covered'] for r in part)}/{len(part)}",
                   "static |m| <= 1 mV": f"{int(np.sum(np.abs(m) <= 1.0))}/{len(part)}",
                   "+/-1 mV @ 1 ns (seeds)": f"{ok1}/{len(part)}", "95% CI": f"{lo:.3f} - {hi:.3f}",
                   "wrong / unresolved decisions": f"{dec.count('wrong')} / {dec.count('unresolved')}",
                   "b0 sigma / max (mV)": f"{np.std(b0):.2f} / {np.max(np.abs(b0)):.1f}"}
            if cond is None:
                row["nominal LSB / MC 1-bit step (mV)"] = "-"
            else:
                c = cond[0]
                row["nominal LSB / MC 1-bit step (mV)"] = (f"{abs(transfer[c]['lsb_mv']):.2f} / "
                                                           f"{carry[c]['classes']['1']['mean_mv']:.2f}")
            rows.append(row)
    table = pd.DataFrame(rows).set_index(["condition", "input pair scale k"])
    energy, half, rho = {}, {}, {}
    for design, study, k in K_DESIGNS:
        e = _json(f"{study}/memory_energy_{design}.json")["equalize 0"]
        energy[k] = e["vdd_fj"] + e["clk_fj"]
        h = [r["half_range_mv"] for r in _json(f"{study}/range_{design}.json")]
        half[k] = (min(h), float(np.median(h)), max(h))
        t = {r["cond"][0]: abs(r["lsb_mv"]) for r in _json(f"{study}/dnl_{design}.json")}
        rho[k] = t["sf"] / t["ss"]
    table.attrs.update(energy_fj=energy, half_range_mv=half, rho_sf_ss=rho)
    return table


def carry_law_table() -> pd.DataFrame:
    """r26d: spread of the local trim step by the number j of magnitude bits that toggle (2^j - 1 unit cells switch),
    pooled over the five conditions and normalized to each condition's mean 1-bit step, against the fitted law
    sqrt(sigma0^2 + (2^j - 1) sigma_u^2)."""
    rows = []
    for design, _, k in K_DESIGNS:
        pooled = _json(f"r26d/carry_{design}.json")["pooled_normalized"]
        s0, su = pooled["fit_sigma0_lsb"], pooled["fit_sigma_unit_lsb"]
        for j in ("1", "2", "3", "4"):
            c = pooled["classes"][j]
            n = 2 ** int(j) - 1
            rows.append({"input pair scale k": k, "toggled bits j": int(j), "unit cells switched": n,
                         "seeds": c["count"], "step sd (LSB)": round(c["sd_lsb"], 3),
                         "fit (LSB)": round(math.sqrt(s0 ** 2 + n * su ** 2), 3)})
    table = pd.DataFrame(rows).set_index(["input pair scale k", "toggled bits j"])
    table.attrs["fit_lsb"] = {k: (_json(f"r26d/carry_{d}.json")["pooled_normalized"]["fit_sigma0_lsb"],
                                  _json(f"r26d/carry_{d}.json")["pooled_normalized"]["fit_sigma_unit_lsb"])
                              for d, _, k in K_DESIGNS}
    return table


def segmentation_table() -> pd.DataFrame:
    """r26d: static misses per 1000 seeds (200 per condition, five conditions) predicted from the fitted step law,
    for the simulated binary coding and for segmented codings that were not simulated, with the observed count."""
    rows = []
    for design, _, k in K_DESIGNS:
        seg = _json(f"r26d/segment_{design}.json")["rows"]
        if sorted(r["cond"][0] for r in seg) != ["ff", "fs", "sf", "ss", "tt"]:
            raise RuntimeError(f"{design}: expected the segmentation model at the five DNL conditions")
        row = {"input pair scale k": k, "observed (binary)": sum(r["observed_static_miss"] for r in seg)}
        for key, label in SEGMENT_SCHEMES:
            row[label] = round(sum(r["predicted_miss"][key] for r in seg), 2)
        rows.append(row)
    return pd.DataFrame(rows).set_index("input pair scale k")


# r26e: the k = 1.75 trim with binary coding (r26d) and with 3 thermometer MSBs + 2 binary LSBs; the most cells
# that one code step can switch
SEG_DESIGNS = (("e5_k175", "r26d", "binary (5 bits)", 31), ("g5_k175", "r26e", "3 thermometer MSBs + 2 binary", 7))


def segmented_mc_table(data: dict) -> pd.DataFrame:
    """r26e: the segmented trim simulated with the same 200 paired MC seeds at the five DNL conditions as the binary
    trim. 'local steps > 2 mV' counts the seeds whose bracketing code step exceeds 2 mV (so that a 1 mV input could
    fall more than 1 mV from a boundary); the law column is the r26d binary fit applied to each design's step mix."""
    compare = _json("r26e/compare_g5_k175.json")
    if compare["n_seeds"] != len(BIT_WEIGHT_CONDS) * EQ_SEEDS:
        raise RuntimeError("r26e comparison does not cover 200 seeds at each of the five conditions")
    rows = []
    for design, study, label, max_cells in SEG_DESIGNS:
        seeds = _jsonl(data, f"{study}/seeds_{design}.jsonl")
        for cond in BIT_WEIGHT_CONDS:
            if sorted(r["seed"] for r in seeds if tuple(r["cond"]) == cond) != list(range(EQ_SEEDS)):
                raise RuntimeError(f"{design} {cond}: Monte Carlo seeds are incomplete or duplicated")
        m = np.array([r.get("fine_m_mv", r["m_mv"]) for r in seeds])
        ok1 = sum(r["out_1mv_1ns"] == ["correct", "correct"] for r in seeds)
        dec = [o for r in seeds for o in r["out_1mv_1ns"]]
        lo, hi = _clopper_pearson(ok1, len(seeds))
        tail = compare["step_tails"][design]
        e = _json(f"{study}/memory_energy_{design}.json")["equalize 0"]
        rows.append({"coding": label, "most cells per step": max_cells,
                     "static |m| <= 1 mV": f"{int(np.sum(np.abs(m) <= 1.0))}/{len(seeds)}",
                     "+/-1 mV @ 1 ns (seeds)": f"{ok1}/{len(seeds)}", "95% CI": f"{lo:.4f} - {hi:.4f}",
                     "wrong / unresolved decisions": f"{dec.count('wrong')} / {dec.count('unresolved')}",
                     "max / rms |m| (mV)": f"{np.max(np.abs(m)):.2f} / {np.sqrt(np.mean(m ** 2)):.2f}",
                     "local steps > 2 mV (observed / law)": f"{tail['over_2mv']} / {tail['law_over_2mv']:.1f}",
                     "TT energy at code 0 (fJ)": round(e["vdd_fj"] + e["clk_fj"], 2)})
    table = pd.DataFrame(rows).set_index("coding")
    table.attrs.update(predicted_static_miss=compare["predicted_static_miss_total"],
                       tail_sign_test_p=compare["tail_sign_test_p_one_sided"])
    return table


def segmented_law_table() -> pd.DataFrame:
    """r26e: local-step spread by the number n of unit cells a step switches, pooled over the five conditions and
    normalized to each condition's 1-bit step, against the r26d binary fit sqrt(sigma0^2 + n sigma_u^2)."""
    fit = _json("r26e/carry_e5_k175.json")["pooled_normalized"]
    s0, su = fit["fit_sigma0_lsb"], fit["fit_sigma_unit_lsb"]
    rows = []
    for design, _, label, _ in SEG_DESIGNS:
        classes = _json(f"r26e/carry_{design}.json")["pooled_normalized"]["classes"]
        for n in sorted(classes, key=int):
            c = classes[n]
            rows.append({"coding": label, "unit cells switched": int(n), "seeds": c["count"],
                         "step sd (LSB)": round(c["sd_lsb"], 3), "max step (LSB)": round(c["max_lsb"], 2),
                         "binary fit (LSB)": round(math.sqrt(s0 ** 2 + int(n) * su ** 2), 3)})
    table = pd.DataFrame(rows).set_index(["coding", "unit cells switched"])
    table.attrs["fit_lsb"] = {d: (_json(f"r26e/carry_{d}.json")["pooled_normalized"]["fit_sigma0_lsb"],
                                  _json(f"r26e/carry_{d}.json")["pooled_normalized"]["fit_sigma_unit_lsb"])
                              for d, _, _, _ in SEG_DESIGNS}
    return table


TAIL_LABELS = {"e5_k175": "binary", "g5_k175": "segmented"}


def tail_model_table() -> pd.DataFrame:
    """r26f: exact-likelihood step model (Gaussian, length-biased, quantized) with and without a carry drift delta
    per switched cell, fitted on one design and predicting the count of local steps > 2 mV of each design."""
    tail = _json("r26f/tail_g5_k175.json")
    rows = []
    for key, t in tail["transfer"].items():
        src, tgt = key.split("->")
        rows.append({"fitted on": TAIL_LABELS[src], "predicts": TAIL_LABELS[tgt],
                     "steps > 2 mV observed": t["observed"],
                     "Gaussian: predicted (P >= observed)":
                         f"{t['delta0']['predicted']:.2f} ({t['delta0']['p_ge_observed']:.2f})",
                     "with drift: predicted (P >= observed)":
                         f"{t['delta']['predicted']:.2f} ({t['delta']['p_ge_observed']:.2f})",
                     "static misses per 1000, with drift": round(t["delta"]["static_miss_predicted"], 2)})
    table = pd.DataFrame(rows).set_index(["fitted on", "predicts"])
    table.attrs.update(joint=tail["joint"],
                       kurtosis={TAIL_LABELS[d]: v["kurtosis_normalized"] for d, v in tail["designs"].items()},
                       steps={TAIL_LABELS[d]: v["steps"] for d, v in tail["designs"].items()})
    return table


DECODER = "d5_k175"
DECODER_SEEDS = 200


def decoder_table() -> pd.DataFrame:
    """r26f: the r26e segmented trim with a transistor-level thermometer decoder (d5) against the ideal decoder (g5)
    at the five DNL conditions: LSB, segment-gate dip at the clock edge, transfer and paired Monte Carlo."""
    kick = _json(f"r26f/kick_{DECODER}.json")
    comp = _json(f"r26f/compare_{DECODER}.json")
    dnl = {d: {tuple(r["cond"]): r for r in _json(f"{s}/dnl_{d}.json")}
           for d, s in ((DECODER, "r26f"), ("g5_k175", "r26e"))}
    if comp["pooled"]["n"] != len(BIT_WEIGHT_CONDS) * DECODER_SEEDS:
        raise RuntimeError("r26f comparison does not cover 200 seeds at each of the five conditions")
    rows = []
    for cond in BIT_WEIGHT_CONDS:
        k = next(r for r in kick if tuple(r["cond"]) == cond and r["design"] == DECODER)
        c = next(r for r in comp["rows"] if tuple(r["cond"]) == cond)
        d, g = dnl[DECODER][cond], dnl["g5_k175"][cond]
        rows.append({"condition": _condition(cond),
                     "LSB ideal / decoder (mV)": f"{abs(g['lsb_mv']):.3f} / {abs(d['lsb_mv']):.3f}",
                     "LSB change (%)": round(100 * (abs(d["lsb_mv"]) / abs(g["lsb_mv"]) - 1), 1),
                     "segment-gate dip (mV)": round(k["dip_mv"]), "dip > 10 mV (ps)": round(k["below_10mv_ps"]),
                     "max |DNL| (LSB)": round(d["dnl_max_lsb"], 2), "monotonic": bool(d["monotonic"]),
                     "same code (seeds)": f"{c['same_code']}/{c['n']}",
                     "static |m| <= 1 mV, decoder / ideal": f"{c['static_1mv']} / {c['static_1mv_ref']}",
                     "+/-1 mV @ 1 ns, decoder / ideal": f"{c['pass_1mv_1ns']} / {c['pass_1mv_1ns_ref']}"})
    table = pd.DataFrame(rows).set_index("condition")
    leak = _json("r26f/leak_decoder_L0.5.json")
    e = {d: _json(f"{s}/memory_energy_{d}.json")["equalize 0"] for d, s in ((DECODER, "r26f"), ("g5_k175", "r26e"))}
    table.attrs.update(pooled=comp["pooled"], leak_worst_na=leak["worst"]["both_sides_worst_na"],
                       leak_cond=_condition(leak["worst"]["cond"]), devices=leak["devices"],
                       gate_area_um2=leak["gate_area_um2"],
                       energy_fj={d: v["vdd_fj"] + v["clk_fj"] for d, v in e.items()})
    return table


def hold_cap_table(data: dict) -> pd.DataFrame:
    """r26f: decoder channel length L and a square nfet hold capacitor (side H) on each of the 14 segment gates
    against the trim boundaries at codes -31 / -16 and the gate dip, with the ideal decoder's boundaries."""
    ref = {tuple(r["cond"]): r["b_mv"] for r in _json("r26e/dnl_g5_k175.json")}
    rows = []
    for name in sorted(n for n in data["files"] if Path(n).match("r26f/kick_L*_H*.json")):
        r = _json(name)
        g = ref[tuple(r["cond"])]
        rows.append({"condition": _condition(r["cond"]), "decoder L (um)": r["L"],
                     "hold cap side H (um)": r["hold_um"],
                     "added gate area (um2)": round(14 * r["hold_um"] ** 2, 1),
                     "segment-gate dip (mV)": round(r["dip_mv"]),
                     "boundary -31 / -16 (mV)": f"{r['b_mv']['-31']:.2f} / {r['b_mv']['-16']:.2f}",
                     "ideal decoder (mV)": f"{g['-31']:.2f} / {g['-16']:.2f}"})
    if not rows:
        raise RuntimeError("No archived r26f hold-capacitor probe")
    return pd.DataFrame(rows).set_index(["condition", "decoder L (um)", "hold cap side H (um)"]).sort_index()


DIP_LAW = "r26g/dip_law_k175.json"
DRIVER_FIXES = ("d5", "b5", "s5", "d5 H1", "d5 H2", "d5 H4")
DRIVER_LABELS = {"d5": "CMOS decoder, LSBs on ideal sources", "b5": "+ LSB buffers (equal drivers)",
                 "s5": "+ drivers scaled with the switch", "d5 H1": "decoder + 1 um hold caps",
                 "d5 H2": "decoder + 2 um hold caps", "d5 H4": "decoder + 4 um hold caps"}


def _dip_law() -> list[dict]:
    law = _json(DIP_LAW)
    if [tuple(r["cond"]) for r in law] != list(BIT_WEIGHT_CONDS):
        raise RuntimeError("r26g dip law does not cover the five DNL conditions in order")
    return law


def dip_law_table() -> pd.DataFrame:
    """r26g: per condition, the fit of dip = A m / (m + m0 + c_h a) to the buffered 4 / 2 / 1-cell switches and the
    three hold capacitors (m = switch size in unit cells, a = hold-capacitor area per gate), and its out-of-sample
    prediction for drivers scaled with their switch, A / (1 + m0)."""
    rows = []
    for r in _dip_law():
        s = r["s5_meas_mv"]
        rows.append({"condition": _condition(r["cond"]), "A (mV)": round(r["A_mv"]),
                     "m0 (unit switches)": round(r["m0"], 2), "c_h (units/um2)": round(r["c_h_per_um2"], 2),
                     "worst fit error (%)": round(100 * r["max_rel_err"], 1),
                     "scaled drivers, predicted dip (mV)": round(r["s5_pred_mv"], 1),
                     "measured segment / LSB1 / LSB0 (mV)": f"{s[0]:.1f} / {s[1]:.1f} / {s[2]:.1f}",
                     "prediction error (%)": round(100 * r["s5_pred_err"], 1)})
    return pd.DataFrame(rows).set_index("condition")


def driver_fix_table() -> pd.DataFrame:
    """r26g: added gate area, TT segment-gate dip and the loss of the segment span (codes +/-28) and of the full
    span (+/-31) against the ideal decoder, from boundaries bisected to 0.01 mV, for the driver and hold fixes."""
    law = _dip_law()
    rows = []
    for fix in DRIVER_FIXES:
        tt = law[0]["designs"][fix]
        row = {"design": DRIVER_LABELS[fix], "added gate area (um2)": tt["area_um2"],
               "TT segment dip (mV)": round(tt["seg_dip_mv"]),
               "TT loss per mV of dip (%/mV)": round(tt["seg_loss_pct_per_mv"], 4)}
        for r in law:
            d = r["designs"][fix]
            loss = f"{d['seg_loss_pct']:.2f} / {d['full_loss_pct']:.2f}"
            row[f"{_condition(r['cond'])} segment / full loss (%)"] = loss
        rows.append(row)
    return pd.DataFrame(rows).set_index("design")


THEVENIN = "r26h/thevenin_k175.json"
THEVENIN_MOS = {"d5": "MOS: CMOS decoder (r26g)", "s5": "MOS: scaled drivers (r26g)",
                "d5 H1": "MOS: decoder + 1 um hold caps (r26g)"}


def thevenin_table() -> pd.DataFrame:
    """r26h: segment-gate dip (mV), segment-span loss (%) and loss per mV of dip (%/mV) at the five conditions for
    ideal segment sources behind a linear series R (and shunt C to VSS), next to three r26g MOS designs; boundaries
    bisected to 0.01 mV, loss of the segment span (codes +/-28) against the ideal decoder."""
    data = _json(THEVENIN)
    conds = list(BIT_WEIGHT_CONDS)
    pts = data["points"]
    drivers = sorted({(p["c_ff"] > 0, p["r_ohm"], p["c_ff"]) for p in pts})
    if len(drivers) != 8 or len(pts) != 8 * len(conds) or {tuple(p["cond"]) for p in pts} != set(conds):
        raise RuntimeError("r26h Thevenin sweep does not cover eight drivers at the five DNL conditions")

    def cell(dip, loss):
        return f"{dip:.0f} / {loss:.2f} / {loss / dip:.3f}"

    rows = []
    for _, r_ohm, c_ff in drivers:
        name = f"linear: R {r_ohm / 1000:g} kohm" + (f" + C {c_ff:g} fF" if c_ff else "")
        row = {"driver": name}
        for c in conds:
            p = next(p for p in pts if (p["r_ohm"], p["c_ff"], tuple(p["cond"])) == (r_ohm, c_ff, c))
            row[f"{_condition(c)} dip / loss / per mV"] = cell(p["seg_dip_mv"], p["seg_loss_pct"])
        rows.append(row)
    for key, name in THEVENIN_MOS.items():
        row = {"driver": name}
        for c in conds:
            d = data["mos"]["|".join(map(str, c))][key]
            row[f"{_condition(c)} dip / loss / per mV"] = cell(d["seg_dip_mv"], d["seg_loss_pct"])
        rows.append(row)
    return pd.DataFrame(rows).set_index("driver")


THEVENIN_STATE = "r26h/thevenin_state_k175.json"


def thevenin_state_table() -> pd.DataFrame:
    """r26h extension: per condition, the linear drivers fitted to the MOS designs at code -31 (on-state R_on / C_on,
    off-state R_off / C_off) and the segment-span loss (%) of the symmetric (on-gate-matched) and state-aware linear
    drivers against the MOS design, the H1 controls with only R_off or only C_off changed, and d5 with an ideal
    linear hold capacitor (segment dip mV / loss %); written by r26h_states.py fit."""
    data = _json(THEVENIN_STATE)
    rows = data["rows"]
    if [tuple(r["cond"]) for r in rows] != list(BIT_WEIGHT_CONDS):
        raise RuntimeError("r26h state-aware fit does not cover the five DNL conditions")
    lin = f"d5 + {data['lincap_ff']:g} fF linear: dip (mV) / loss"
    out = []
    for r in rows:
        d, h, lc = r["d5"], r["H1"], r["lincap"]
        if d["r_off_ohm"] != h["r_off_ohm"]:
            raise RuntimeError("r26h state-aware fit: d5 and H1 pull-down R differ")
        out.append({"condition": _condition(r["cond"]),
                    "R_on / R_off (kohm)": f"{r['r_on_ohm'] / 1000:.1f} / {d['r_off_ohm'] / 1000:.1f}",
                    "d5 C_on / C_off (fF)": f"{d['c_on_ff']:g} / {d['c_off_ff']:g}",
                    "H1 C_on / C_off (fF)": f"{h['c_on_ff']:g} / {h['c_off_ff']:g}",
                    "d5 loss: sym / state / MOS": " / ".join(f"{d[k]:.2f}" for k in
                                                             ("loss_sym_pct", "loss_state_pct", "loss_mos_pct")),
                    "H1 loss: sym / state / MOS": " / ".join(f"{h[k]:.2f}" for k in
                                                             ("loss_sym_pct", "loss_state_pct", "loss_mos_pct")),
                    "H1 loss: R_off only / C_off only": f"{h['loss_r_off_only_pct']:.2f} / {h['loss_c_off_only_pct']:.2f}",
                    lin: f"{lc['seg_dip_mv']:.0f} / {lc['loss_pct']:.2f}"})
    return pd.DataFrame(out).set_index("condition")


FIXES = "r26i/fixes_k175.json"


def fixes_table() -> pd.DataFrame:
    """r26i: segment-gate dip (mV) / segment-span loss (%) at the five conditions and the worst loss for d5 variants
    (N<m> / P<m>: decoder output-stage pull-down / pull-up multiplied by m, H<h>: h x h um nfet hold capacitor,
    PH<p>: p x p um pfet hold capacitor), with their added gate area per segment gate; written by r26i_drv.py table."""
    data = _json(FIXES)
    if [tuple(c) for c in data["conds"]] != list(BIT_WEIGHT_CONDS):
        raise RuntimeError("r26i fixes do not cover the five DNL conditions")
    out = []
    for lab, d in data["designs"].items():
        row = {"design": lab, "added area (um2)": "ideal" if d["area_um2"] is None else f"{d['area_um2']:.2f}"}
        for r in d["rows"]:
            row[f"{_condition(r['cond'])} dip / loss"] = f"{r['seg_dip_mv']:.0f} / {r['seg_loss_pct']:.2f}"
        row["worst loss (%)"] = round(d["worst_loss_pct"], 2)
        out.append(row)
    return pd.DataFrame(out).set_index("design")


VERIFY = "r26j/verify_k175.json"


def verify_table() -> pd.DataFrame:
    """r26j: the r26i fixes under mismatch Monte Carlo (worst of the five conditions per seed, paired with g5), with
    the b1-extracted gate-net capacitance (x1, x4), TT energy per decision, decoder leakage and the calibration Monte
    Carlo; footprint is a SKY130 rule estimate per segment gate; written by r26j_verify.py table."""
    data = _json(VERIFY)
    if [tuple(c) for c in data["conds"]] != list(BIT_WEIGHT_CONDS):
        raise RuntimeError("r26j checks do not cover the five DNL conditions")
    out = []
    for lab, d in data["designs"].items():
        mc, w = d["mc"], d["mc"]["per_seed_worst_pct"]
        flow = d["flow"]
        row = {"design": lab, "gate / footprint (um2)": f"{d['gate_area_um2']:.2f} / {d['footprint_um2']:.2f}",
               "nominal worst (%)": round(d["nominal_worst_pct"], 2),
               f"MC worst, {mc['n_seeds']} seeds (%)": f"{sum(w) / len(w):.2f} [{min(w):.2f}, {max(w):.2f}]",
               "MC SF / FF max (%)": round(max(mc["per_seed_hot_pct"]), 2),
               "gate net x1 / x4 worst (%)": " / ".join(f"{d['para_worst_abs_pct'][k]:.2f}" for k in ("1", "4")),
               "TT energy change (fJ)": round(d["energy"]["tt_vdd_delta_fj"], 2),
               "leakage (nA)": round(d["energy"]["leak_worst_na"], 2),
               "calibration MC, +/-1 mV at 1 ns": (f"{sum(r['pass_1mv_1ns'] for r in flow)}/{sum(r['n'] for r in flow)}"
                                                   if flow else "-")}
        out.append(row)
    return pd.DataFrame(out).set_index("design")


def energy_screen_table(data: dict) -> pd.DataFrame:
    """r18: nominal TT screen of lower-energy 6-bit unit trims (all decisions at 3.5 ns)."""
    rows = [r for r in _jsonl(data, "r18/screen.jsonl") if "boundaries_mv" in r]
    out = []
    for r in rows:
        side = "drain" if r["variant"].startswith("d") else "source"
        out.append({"variant": r["variant"] + (" (= unit6_w6)" if r["variant"] == "u6_w6_l1_s1" else ""),
                    "input W (um)": r["input_w"], "trim L (um)": r["trim_l"], "switch W (um)": r["switch_w"],
                    "switch side": side,
                    "energy code 0 / 63 (fJ)": f"{r['energy_fj_code0']:.0f} / {r['energy_fj_code63']:.0f}",
                    "mean step, codes 0-16 (mV)": round(abs(r["boundaries_mv"]["16"] - r["boundaries_mv"]["0"]) / 16, 2),
                    "range, code 63 (mV)": round(abs(r["boundaries_mv"]["63"]), 1)})
    if len(out) != 8:
        raise RuntimeError("r18 screen rows missing")
    return pd.DataFrame(out).set_index("variant")


def energy_table(data: dict) -> pd.DataFrame:
    """r14 and r16: nominal core energy at code 0 / full scale, three corners."""
    rows = [row for name in ("r14/energy.json", "r16/energy.json") for row in _json(name)]
    frame = pd.DataFrame(rows)
    frame = frame[frame.variant.isin(ENERGY_VARIANTS)]
    out = []
    for variant, label in ENERGY_VARIANTS.items():
        part = frame[frame.variant.eq(variant)]
        row = {"variant": label, "trim gate area (um^2)": part.gate_area_proxy_um2.iloc[0]}
        for cond in ENERGY_CONDITIONS:
            at = part[part.cond.apply(lambda c: tuple(c) == cond)].sort_values("code")
            if len(at) != 2:
                raise RuntimeError(f"Energy rows missing for {variant} at {cond}")
            row[f"{cond[0].upper()} {cond[1]:g} V {cond[2]:g} C (fJ)"] = \
                f"{at.core_energy_fj.iloc[0]:.0f} / {at.core_energy_fj.iloc[1]:.0f}"
        out.append(row)
    return pd.DataFrame(out).set_index("variant")


def figure(data: dict):
    import matplotlib.pyplot as plt

    from presentation.figure_style import FigureProfile, publication_style

    steps = trim_steps(data)
    profile = FigureProfile(height_in=2.55)
    blue, orange, green, grey = "#0072B2", "#D55E00", "#009E73", "#555555"
    with publication_style(profile):
        fig, axes = plt.subplots(1, 3, figsize=(profile.width_in, profile.height_in))
        fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.20, wspace=0.42)
        ax = axes[0]
        for trim, color, marker in (("binary", orange, "s"), ("unit", blue, "o")):
            part = steps[steps.trim.eq(trim) & steps.corner.str.startswith("SS")].sort_values("code")
            ax.plot(part.code, part.step_mv, marker=marker, markersize=3, color=color,
                    markerfacecolor="none", label=f"{trim} array")
        ax.set(xlabel="Trim code", ylabel="Step from previous code (mV)",
               title="(a) 4b trim steps, SS 1.62 V -40 C")
        ax.legend(frameon=False, loc="upper center")
        ax = axes[1]
        for (label, condition, pattern, limit), color, style in zip(
                [v for v in MC_VARIANTS if v[0].startswith(("Shipped", "Fix"))],
                (orange, orange, blue, blue), ("--", "-", "--", "-")):
            records = [r for r in _jsonl(data, pattern) if r["seed"] < limit]
            m = np.sort([abs(r["m_mv"]) if r["covered"] else np.inf for r in records])
            ax.step(np.r_[0, np.minimum(m, 6)], np.r_[0, np.arange(1, len(m) + 1) / len(m)], where="post", color=color,
                    linestyle=style, label=f"{label.split(':')[0]} {condition.split()[0]}")
        ax.axvline(1, color=grey, linestyle=":", linewidth=0.8)
        ax.set(xlim=(0, 5), ylim=(0, 1.02), xlabel="Residual |m| after trim (mV)",
               ylabel="Fraction of 40 seeds", title="(b) Mismatch Monte Carlo")
        ax.legend(frameon=False, loc="lower right", fontsize=profile.font_pt - 1)
        ax = axes[2]
        energy = pd.DataFrame(_json("r14/energy.json"))
        tt = energy[energy.cond.apply(lambda c: tuple(c) == ENERGY_CONDITIONS[0]) & energy.code.eq(0)
                    & energy.variant.isin(ENERGY_VARIANTS)]
        named = {"binary4_w3_shipped": ("shipped", orange, (16.5, 165)), "unit5_w6_fix": ("fix", blue, (31, 345)),
                 "gate5_w6_r12": ("gate-switched\n(rejected)", green, (27, 118))}
        for row in tt.itertuples():
            label, color, text = named.get(row.variant, (None, grey, None))
            ax.scatter(row.gate_area_proxy_um2, row.core_energy_fj, s=22 if label else 12, color=color,
                       zorder=4 if label else 3, facecolors="none" if label is None else color)
            if label:
                ax.annotate(label, (row.gate_area_proxy_um2, row.core_energy_fj), xytext=text,
                            fontsize=profile.font_pt - 1, arrowprops={"arrowstyle": "-", "color": grey, "lw": 0.6})
        ax.text(0.04, 0.96, "open: other unit-array\nvariants (table)", transform=ax.transAxes, va="top",
                fontsize=profile.font_pt - 1.5, color=grey)
        ax.set(xlim=(15, 45), ylim=(100, 500), xlabel="Trim gate area (um$^2$)",
               ylabel="Core energy, TT code 0 (fJ)", title="(c) Energy cost")
        for ax in axes:
            ax.tick_params(direction="out")
        fig.text(0.5, 0.98, SCOPE_LABEL, ha="center", va="top", fontsize=profile.font_pt)
    return fig
