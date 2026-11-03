"""R2: prospective, pre-registered test of the two-factor outcome model on the six declared
candidates that were never validated (same 49 conditions, same local_boundary calibration).

  python r2_prospective.py phase_a <design>   # calibrate + fit inputs (+/-3, 10, 30 mV)
  python r2_prospective.py register           # freeze predictions for held-out inputs (hashed)
  python r2_prospective.py phase_b <design>   # simulate held-out inputs (0, +/-0.25, 0.5, 1 mV)
  python r2_prospective.py evaluate           # score predictions, build nine-design atlas
"""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

DESKTOP = Path(__file__).resolve().parents[1]  # entry root (comparator_atlas, .deps, .tools, .cache)
sys.path.insert(0, str(DESKTOP))
from comparator_atlas.experiments import DEADLINES_NS, case_id, cases  # noqa: E402
from comparator_atlas.spice import Simulator  # noqa: E402
from comparator_atlas.study import Evidence, chosen_code  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "r2"
CACHE = HERE / "cache" / "spice"
NEW_DESIGNS = ("svt_fast_4b", "lvt_fine_3b", "lvt_fine_4b", "lvt_fast_4b", "lvt_fast_fine_4b", "lvt_wide_5b")
FIT_INPUTS = (-30, -10, -3, 3, 10, 30)
HELD_INPUTS = (-1, -0.5, -0.25, 0, 0.25, 0.5, 1)
DEADLINES = tuple(DEADLINES_NS) + (3.5,)
BANDS = (0.25, 0.5, 1.0, 3.0, 10.0, 30.0)
def registries() -> list:
    """Registered prediction batches whose hash file still matches (each sealed before its phase B)."""
    found = []
    for path in sorted(OUT.glob("registered_predictions*.json")):
        text = path.read_text()
        digest = path.with_suffix(".sha256").read_text().strip()
        if hashlib.sha256(text.encode()).hexdigest() != digest:
            raise SystemExit(f"Registered predictions were modified: {path.name}")
        found.append((path.name, digest, json.loads(text)))
    return found


def registered_designs() -> set:
    return {p["design_name"] for _, _, reg in registries() for p in reg["sample_predictions"]}


def run_phase(design: str, inputs: tuple, tag: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    points = [replace(p, design_name=design) for p in cases("full")]
    if tag == "phase_b" and design not in registered_designs():
        raise SystemExit("Refusing phase_b before this design's predictions are registered")

    def evaluate(point):
        ev = Evidence(Simulator(CACHE, workers=1))
        cal = ev.calibration(point)
        code = chosen_code(cal)
        rows = ev.observations(point, {"local_boundary": code}, inputs, DEADLINES) if code is not None else []
        return {"case_id": case_id(point), "calibration": cal, "rows": rows}

    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i, res in enumerate(pool.map(evaluate, points), 1):
            results.append(res)
            print(f"{tag} {design} [{i:02d}/49] {res['case_id']}", flush=True)
    (OUT / f"{tag}_{design}.json").write_text(json.dumps(results, default=str))


def residual_table(design: str) -> pd.DataFrame:
    rows = []
    for r in json.loads((OUT / f"phase_a_{design}.json").read_text()):
        cal = r["calibration"]
        if not cal["available"]:
            rows.append({"case_id": r["case_id"], "available": False})
            continue
        sel = cal["selection"]
        chosen = sel["candidate_boundaries"][str(sel["code"])]
        rows.append({"case_id": r["case_id"], "available": True, "code": sel["code"],
                     "residual_mv": chosen["midpoint_mv"], "halfwidth_mv": chosen["halfwidth_mv"]})
    return pd.DataFrame(rows)


def rows_frame(tag: str, design: str) -> pd.DataFrame:
    data = json.loads((OUT / f"{tag}_{design}.json").read_text())
    return pd.DataFrame([row for r in data for row in r["rows"]])


def fits(design: str) -> pd.DataFrame:
    res = residual_table(design)
    obs = rows_frame("phase_a", design)
    t35 = obs[obs.deadline_ns.eq(3.5)].merge(res, on="case_id")
    out = []
    for case, g in t35.groupby("case_id"):
        g = g[g.decision_time_ns.notna()]
        x = np.log(1.0 / (g.input_mv - g.residual_mv).abs())
        if len(g) >= 3:
            tau, t0 = np.polyfit(x, g.decision_time_ns, 1)
        else:
            tau, t0 = np.nan, np.nan
        out.append({"case_id": case, "tau_ns": tau, "t0_ns": t0, "fit_points": len(g)})
    return res.merge(pd.DataFrame(out), on="case_id", how="left")


def predict_outcome(v, m, tau, t0, deadline) -> str:
    if not (tau > 0):
        return "unresolved"
    if t0 + tau * np.log(1.0 / abs(v - m)) > deadline:
        return "unresolved"
    return "correct" if np.sign(v - m) == np.sign(v) else "wrong"


def register(batch: str, designs: list) -> None:
    registry = OUT / f"registered_predictions_{batch}.json"
    if registry.exists():
        raise SystemExit("Predictions already registered; never overwrite")
    already = registered_designs() & set(designs)
    if already:
        raise SystemExit(f"Already registered: {sorted(already)}")
    if any((OUT / f"phase_b_{d}.json").exists() for d in designs):
        raise SystemExit("Phase B output already exists for a design in this batch")
    preds, atlas = [], []
    for design in designs:
        f = fits(design)
        obs = rows_frame("phase_a", design)
        for row in f.itertuples():
            for v in HELD_INPUTS:
                if v == 0:
                    continue
                for d in DEADLINES_NS:
                    outcome = "calibration_unavailable" if not row.available else \
                        predict_outcome(v, row.residual_mv, row.tau_ns, row.t0_ns, d)
                    preds.append({"design_name": design, "case_id": row.case_id, "input_mv": v,
                                  "deadline_ns": d, "predicted": outcome})
        pf = pd.DataFrame([p for p in preds if p["design_name"] == design])
        all_available = bool(f.available.all())
        for d in DEADLINES_NS:
            for b in BANDS:
                fit_ok = bool(obs[obs.deadline_ns.eq(d) & obs.input_mv.abs().ge(b)].outcome.eq("correct").all()) \
                    and all_available
                held = pf[pf.deadline_ns.eq(d) & pf.input_mv.abs().ge(b)]
                ok = fit_ok and bool(held.predicted.eq("correct").all())
                atlas.append({"design_name": design, "deadline_ns": d, "band_mv": b, "predicted_qualifies": ok})
        print(design, "max|m| =", f.residual_mv.abs().max(), "calibration available", int(f.available.sum()), "/49")
    payload = {"registered_utc": datetime.now(timezone.utc).isoformat(),
               "rule": "wrong iff sign(v-m)!=sign(v); unresolved iff t0+tau*ln(1mV/|v-m|)>D; tau,t0 fit on |v|>=3 mV at 3.5 ns",
               "sample_predictions": preds, "atlas_predictions": atlas}
    text = json.dumps(payload, sort_keys=True)
    registry.write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    registry.with_suffix(".sha256").write_text(digest + "\n")
    print("registered", batch, designs, len(preds), "sample and", len(atlas), "atlas predictions; sha256", digest)


def evaluate() -> None:
    regs = registries()
    preds = pd.DataFrame([p for _, _, reg in regs for p in reg["sample_predictions"]])
    designs = [d for d in NEW_DESIGNS if d in set(preds.design_name)
               and (OUT / f"phase_b_{d}.json").exists()]
    preds = preds[preds.design_name.isin(designs)]
    obs = pd.concat([rows_frame("phase_b", d).assign(design_name=d) for d in designs])
    obs = obs[obs.deadline_ns.isin(DEADLINES_NS) & obs.input_mv.ne(0)]
    m = preds.merge(obs[["design_name", "case_id", "input_mv", "deadline_ns", "outcome"]],
                    on=["design_name", "case_id", "input_mv", "deadline_ns"], how="left", validate="one_to_one")
    m["outcome"] = m.outcome.fillna("calibration_unavailable")
    sample = {}
    for design, g in m.groupby("design_name"):
        sample[design] = {"agree": int(g.predicted.eq(g.outcome).sum()), "n": int(len(g)),
                          "by_deadline": {f"{d:g}": f"{int(h.predicted.eq(h.outcome).sum())}/{len(h)}"
                                          for d, h in g.groupby("deadline_ns")}}
    full = pd.concat([pd.concat([rows_frame("phase_a", d), rows_frame("phase_b", d)]).assign(design_name=d)
                      for d in designs])
    full = full[full.deadline_ns.isin(DEADLINES_NS) & full.input_mv.ne(0)]
    atlas = pd.DataFrame([a for _, _, reg in regs for a in reg["atlas_predictions"]])
    atlas = atlas[atlas.design_name.isin(designs)].reset_index(drop=True)
    observed = []
    for row in atlas.itertuples():
        f = residual_table(row.design_name)
        part = full[full.design_name.eq(row.design_name) & full.deadline_ns.eq(row.deadline_ns)
                    & full.input_mv.abs().ge(row.band_mv)]
        ok = bool(f.available.all()) and len(part) == 49 * 2 * sum(b >= row.band_mv for b in BANDS) \
            and bool(part.outcome.eq("correct").all())
        energy = float(part.core_energy_fj.mean()) if ok else None
        observed.append({"observed_qualifies": ok, "mean_core_energy_fj": energy})
    atlas = pd.concat([atlas, pd.DataFrame(observed)], axis=1)
    # Bands >= the smallest fit input are fully observed in phase A, so they are not predictions.
    # (batch1 registration also applied all-fit-input correctness to them, which was too strict.)
    atlas["predictive"] = atlas.band_mv.lt(min(abs(v) for v in FIT_INPUTS))
    scored = atlas[atlas.predictive]
    report = {"registrations": [{"file": n, "sha256": h, "registered_utc": reg["registered_utc"]}
                                for n, h, reg in regs],
              "evaluated_designs": designs,
              "sample_agreement": sample,
              "atlas_agreement_predictive_cells":
                  f"{int(scored.predicted_qualifies.eq(scored.observed_qualifies).sum())}/{len(scored)}",
              "atlas_disagreements": scored[scored.predicted_qualifies.ne(scored.observed_qualifies)].to_dict("records"),
              "disclosed_defect": "batch1 atlas rule required all fit inputs correct for every band; bands >= 3 mV "
                                  "are therefore excluded from scoring and reported as observed only",
              "qualifying_cells": atlas[atlas.observed_qualifies].to_dict("records")}
    atlas.to_csv(OUT / "r2_atlas_new_designs.csv", index=False)
    (OUT / "r2_evaluation.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "phase_a":
        run_phase(sys.argv[2], FIT_INPUTS, "phase_a")
    elif cmd == "phase_b":
        run_phase(sys.argv[2], HELD_INPUTS, "phase_b")
    elif cmd == "register":
        register(sys.argv[2], sys.argv[3].split(","))
    elif cmd == "evaluate":
        evaluate()
