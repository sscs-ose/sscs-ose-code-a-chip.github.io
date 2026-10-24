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
MANIFEST_SHA256 = "3c146a9f4f7f9b59a7582c6edff65aa267da089cb669cc31e770f24b19a3d96e"
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
