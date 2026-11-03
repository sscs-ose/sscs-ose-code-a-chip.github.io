"""R1: trim-resolution floor analysis from saved Comparator Atlas data (no new SPICE).

Hypothesis: a calibrated comparator decides a static input v wrongly exactly when v lies
between 0 and the residual switching boundary m left by the integer trim code
(0 < v/m < 1). The achievable floor is therefore set by trim-step (LSB) quantization.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ENTRY = Path(__file__).resolve().parents[1]
STUDY = ENTRY / "results" / "study"
OUT = Path(__file__).resolve().parent / "out"
INPUTS = (1.0, 3.0, 10.0, 30.0)


def lsb_of(cb: dict) -> float:
    ks = sorted(cb, key=int)
    if len(ks) < 2 or int(ks[-1]) == int(ks[0]):
        return np.nan
    return abs(cb[ks[-1]]["midpoint_mv"] - cb[ks[0]]["midpoint_mv"]) / abs(int(ks[-1]) - int(ks[0]))


def residuals() -> pd.DataFrame:
    rows = []
    for r in json.loads((STUDY / "validation_calibration.json").read_text()):
        rows.append((r["design_name"], r["case_id"], r["local"]["selection"]))
    for r in json.loads((STUDY / "professional" / "calibration.json").read_text()):
        rows.append((r["point"]["design_name"], r["case_id"], r["calibration"]["selection"]))
    out = []
    for design, case, sel in rows:
        cb = sel["candidate_boundaries"]
        chosen = cb[str(sel["code"])]
        out.append({
            "design_name": design, "case_id": case, "code": sel["code"],
            "residual_mv": chosen["midpoint_mv"], "halfwidth_mv": chosen["halfwidth_mv"],
            "lsb_mv": lsb_of(cb),
        })
    return pd.DataFrame(out)


def measurements() -> pd.DataFrame:
    cols = ["design_name", "case_id", "policy", "input_mv", "deadline_ns", "outcome", "decision_time_ns"]
    frame = pd.concat([
        pd.read_csv(STUDY / "verified_measurements.csv", usecols=cols),
        pd.read_csv(STUDY / "professional" / "measurements.csv", usecols=cols),
    ])
    return frame[frame.policy.eq("local_boundary") & frame.input_mv.abs().ge(1)]


def predict(frame: pd.DataFrame, res: pd.DataFrame) -> pd.DataFrame:
    m = frame.merge(res, on=["design_name", "case_id"], how="left", validate="many_to_one")
    ratio = m.input_mv / m.residual_mv
    m["between"] = (ratio > 0) & (ratio < 1)
    m["ambiguous"] = (m.input_mv - m.residual_mv).abs() <= m.halfwidth_mv
    return m


def training_lsb() -> pd.DataFrame:
    sel = json.loads((STUDY / "selection.json").read_text())
    rows = []
    for cand in sel["candidates"]:
        d = cand["design"]
        for cal in cand["calibrations"]:
            if not cal["available"]:
                continue
            cb = cal["selection"]["candidate_boundaries"]
            rows.append({
                "design_name": d["name"], "trim_l": d["trim_l"], "trim_bits": d["trim_bits"],
                "corner": cal["point"]["corner"], "lsb_mv": lsb_of(cb),
                "residual_mv": cb[str(cal["selection"]["code"])]["midpoint_mv"],
            })
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    res = residuals()
    m = predict(measurements(), res)
    report = {"hypothesis": "wrong <=> 0 < input/residual < 1 (static boundary from 3.5 ns calibration)"}
    confusion = {}
    for (design, deadline), g in m.groupby(["design_name", "deadline_ns"]):
        resolved = g[g.outcome.ne("unresolved")]
        wrong = resolved.outcome.eq("wrong")
        unresolved = g[g.outcome.eq("unresolved")]
        confusion[f"{design}@{deadline:g}ns"] = {
            "resolved": int(len(resolved)), "wrong": int(wrong.sum()),
            "true_pos": int((wrong & resolved.between).sum()),
            "false_pos": int((~wrong & resolved.between).sum()),
            "false_neg": int((wrong & ~resolved.between).sum()),
            "ambiguous_within_bisection_tol": int(resolved.ambiguous.sum()),
            "unresolved": int(len(unresolved)),
            "unresolved_on_wrong_side": int(unresolved.between.sum()),
        }
    report["confusion_by_design_deadline"] = confusion
    summary = {}
    for design, g in res.groupby("design_name"):
        a = g.residual_mv.abs()
        summary[design] = {
            "conditions": int(len(g)),
            "lsb_mv_median": float(g.lsb_mv.median()), "lsb_mv_max": float(g.lsb_mv.max()),
            "abs_residual_mv_median": float(a.median()), "abs_residual_mv_max": float(a.max()),
            "max_abs_residual_over_lsb": float((a / g.lsb_mv).max()),
            "conditions_with_abs_residual_over": {f"{v:g}mV": int((a > v).sum()) for v in INPUTS},
        }
    report["residual_summary"] = summary
    tl = training_lsb()
    report["training_lsb_by_design"] = {
        name: {"trim_l": float(g.trim_l.iloc[0]), "trim_bits": int(g.trim_bits.iloc[0]),
               "lsb_mv_by_training_case": [round(x, 3) for x in g.lsb_mv],
               "abs_residual_mv_max": round(float(g.residual_mv.abs().max()), 3)}
        for name, g in tl.groupby("design_name", sort=False)
    }
    res.to_csv(OUT / "r1_residuals.csv", index=False)
    (OUT / "r1_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
