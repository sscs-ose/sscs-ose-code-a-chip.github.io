"""R4: two-factor (static residual + regeneration tau) outcome model from cached waveforms.

Per calibrated condition, fit t_d = t0 + tau * ln(1 mV / |v - m|) on |v| >= 3 mV only,
where m is the post-trim residual boundary from R1. Then predict decision time and
correct / wrong / unresolved at every deadline for the held-out |v| <= 1 mV inputs.
No new SPICE: decision times are re-measured from the archived raw waveforms.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r1_trim_floor as r1  # noqa: E402

DESKTOP = Path(__file__).resolve().parents[1]  # entry root (comparator_atlas, .deps, .tools, .cache)
CACHE = DESKTOP / ".cache" / "spice"
sys.path.insert(0, str(r1.ENTRY))
from comparator_atlas.spice import Point, Trace, measure  # noqa: E402

FIT_MIN_MV = 3.0
DEADLINES = (0.25, 0.35, 0.5, 0.75, 1.0, 2.0)


def load_trace(row) -> Trace:
    folder = CACHE / row.run_id
    meta = json.loads((folder / "metadata.json").read_text())
    archive = folder / "waveform.npz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != meta["waveform_sha256"]:
        raise RuntimeError(f"waveform hash mismatch {row.run_id}")
    point = Point(**meta["identity"]["point"])
    if abs(point.differential_v * 1000 - row.input_mv) > 1e-9:
        raise RuntimeError(f"identity mismatch {row.run_id}")
    with np.load(archive, allow_pickle=False) as z:
        return Trace(point, z["values"], row.run_id, folder)


def samples() -> pd.DataFrame:
    cols = ["design_name", "case_id", "policy", "input_mv", "deadline_ns", "outcome", "run_id"]
    frame = pd.concat([
        pd.read_csv(r1.STUDY / "verified_measurements.csv", usecols=cols),
        pd.read_csv(r1.STUDY / "professional" / "measurements.csv", usecols=cols),
    ])
    frame = frame[frame.policy.eq("local_boundary")]
    observed = frame.pivot_table(index=["design_name", "case_id", "input_mv"], columns="deadline_ns",
                                 values="outcome", aggfunc="first")
    observed.columns = [f"obs_{c:g}" for c in observed.columns]
    runs = frame.drop_duplicates(["design_name", "case_id", "input_mv"])[
        ["design_name", "case_id", "input_mv", "run_id"]]
    out = runs.merge(observed.reset_index(), on=["design_name", "case_id", "input_mv"])
    times = []
    for row in out.itertuples():
        m = measure(load_trace(row), 3.5)
        times.append((m.decision_time_ns, m.decision))
    out["t35_ns"] = [t for t, _ in times]
    out["decision35"] = [d for _, d in times]
    return out.merge(r1.residuals(), on=["design_name", "case_id"], validate="many_to_one")


def fit_and_predict(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (design, case), g in df.groupby(["design_name", "case_id"]):
        g = g.copy()
        g["veff"] = (g.input_mv - g.residual_mv).abs()
        g["x"] = np.log(1.0 / g.veff)
        fit = g[g.input_mv.abs().ge(FIT_MIN_MV) & g.t35_ns.notna()]
        tau, t0 = np.polyfit(fit.x, fit.t35_ns, 1)
        fit_rms = float(np.sqrt(np.mean((fit.t35_ns - (t0 + tau * fit.x)) ** 2)))
        g["tau_ps"], g["t0_ns"], g["fit_rms_ps"] = tau * 1000, t0, fit_rms * 1000
        g["t_pred_ns"] = t0 + tau * g.x
        g["held_out"] = g.input_mv.abs().lt(FIT_MIN_MV)
        rows.append(g)
    return pd.concat(rows)


def outcome_pred(row, deadline: float) -> str:
    if row.t_pred_ns > deadline:
        return "unresolved"
    return "correct" if np.sign(row.input_mv - row.residual_mv) == np.sign(row.input_mv) else "wrong"


def main() -> int:
    df = fit_and_predict(samples())
    df.to_csv(r1.OUT / "r4_samples.csv", index=False)
    held = df[df.held_out & df.input_mv.ne(0)]
    report = {"model": "t_d = t0 + tau*ln(1mV/|v-m|); fit |v|>=3 mV, predict |v|<=1 mV"}
    per = {}
    for design, g in df.groupby("design_name"):
        cond = g.drop_duplicates("case_id")
        h = held[held.design_name.eq(design)]
        timed = h[h.t35_ns.notna()]
        err = (timed.t_pred_ns - timed.t35_ns) * 1000
        acc = {}
        for d in DEADLINES:
            pred = h.apply(outcome_pred, axis=1, deadline=d)
            obs = h[f"obs_{d:g}"]
            acc[f"{d:g}ns"] = {"agree": int((pred == obs).sum()), "n": int(len(h)),
                               "confusion": pd.crosstab(obs, pred).to_dict()}
        per[design] = {
            "tau_ps_median": float(cond.tau_ps.median()),
            "tau_ps_range": [float(cond.tau_ps.min()), float(cond.tau_ps.max())],
            "t0_ns_median": float(cond.t0_ns.median()),
            "fit_rms_ps_median": float(cond.fit_rms_ps.median()),
            "fit_rms_ps_max": float(cond.fit_rms_ps.max()),
            "heldout_time_err_ps_median_abs": float(err.abs().median()),
            "heldout_time_err_ps_p90_abs": float(err.abs().quantile(0.9)),
            "heldout_outcome_agreement": acc,
        }
    report["per_design"] = per
    (r1.OUT / "r4_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
