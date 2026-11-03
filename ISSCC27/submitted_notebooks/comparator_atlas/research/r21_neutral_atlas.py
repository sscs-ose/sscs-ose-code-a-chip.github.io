"""r21: does the sealed three-design comparison survive a bin-neutral stress?

r20 found that the atlas width skew (w = W(1 +/- s)) is not design-neutral under the SKY130 binned
models: relative to an ideal skew (instance multiplier m = 1 +/- s, nominal W and junctions) it is
about 1.3x for the two 2 um designs and about 0.87x for lvt_balanced_4b (3 um pair straddles a W bin).
Here the three sealed designs are re-run over the same 49 conditions with the same local_boundary
calibration and the eight sampled inputs (+/-1, 3, 10, 30 mV), once with the atlas width skew (to check
that this harness reproduces the sealed counts) and once with the multiplier skew. Scored at 1 ns.
Local only; the sealed record is unchanged.
  python -B r21_neutral_atlas.py run <design> <width|mult>
  python -B r21_neutral_atlas.py refine            (every +/-1 mV, 1 ns point at 0.625 ps, all designs and modes)
  python -B r21_neutral_atlas.py score [refined]
SEALED holds the published counts, which include the sealed record's own numerical refinement.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r20_bin_stress  # noqa: E402,F401  (registers <design>__m and patches circuit_text)
import r2_prospective as R2  # noqa: E402
import pandas as pd  # noqa: E402

R2.OUT = R2.HERE / "out" / "r21"
R2.CACHE = R2.HERE / "cache" / "spice_r21"
R2.ThreadPoolExecutor = lambda max_workers: ThreadPoolExecutor(max_workers=5)
DESIGNS3 = ("baseline", "lvt_base_3b", "lvt_balanced_4b")
INPUTS = (-30, -10, -3, -1, 1, 3, 10, 30)
DEADLINE = 1.0
BANDS = (1.0, 3.0, 10.0, 30.0)
SEALED = {"baseline": (310, 16), "lvt_balanced_4b": (372, 29), "lvt_base_3b": (351, 18)}


def frame(design: str, mode: str) -> tuple[pd.DataFrame, int]:
    data = json.loads(path(design, mode).read_text())
    unavailable = sum(not r["calibration"]["available"] for r in data)
    rows = pd.DataFrame([row for r in data for row in r["rows"]])
    rows = rows[rows.deadline_ns.eq(DEADLINE)].copy()
    refined = R2.OUT / "refined.json"
    if REFINED and refined.exists():
        fine = {(r["case_id"], r["input_mv"]): r["fine_outcome"] for r in json.loads(refined.read_text())
                if r["mode"] == mode and r["design"] == design}
        rows["outcome"] = [fine.get((c, i), o) for c, i, o in zip(rows.case_id, rows.input_mv, rows.outcome)]
    return rows, unavailable


REFINED = False


def path(design: str, mode: str):
    return R2.OUT / f"{mode}_{design}{'__m' if mode == 'mult' else ''}.json"


def score() -> dict:
    out = {}
    for mode in ("width", "mult"):
        for design in DESIGNS3:
            if not path(design, mode).exists():
                continue
            rows, unavailable = frame(design, mode)
            ok = rows.outcome.eq("correct")
            full = int(rows.assign(ok=ok).groupby("case_id").ok.all().sum())
            bands = {}
            for band in BANDS:
                part = rows[rows.input_mv.abs().ge(band)]
                need = 49 * 2 * sum(b >= band for b in BANDS)
                feasible = unavailable == 0 and len(part) == need and bool(part.outcome.eq("correct").all())
                bands[f"{band:g}"] = {"correct": int(part.outcome.eq("correct").sum()), "points": need,
                                      "feasible": feasible,
                                      "mean_core_energy_fj": float(part.core_energy_fj.mean()) if feasible else None}
            out[f"{mode}|{design}"] = {"correct": int(ok.sum()), "points": 49 * len(INPUTS),
                                       "fully_passing_conditions": full, "calibration_unavailable": unavailable,
                                       "sealed": SEALED[design] if mode == "width" else None, "bands": bands}
            r = out[f"{mode}|{design}"]
            print(f"{mode:5s} {design:16s} {r['correct']}/{r['points']} full {full}/49 unavail {unavailable}"
                  f" sealed {r['sealed']} | " + " ".join(
                      f">={b}: {v['correct']}/{v['points']}{'*' if v['feasible'] else ''}" for b, v in bands.items()))
    for mode in ("width", "mult"):
        for band in BANDS:
            cands = [(v["bands"][f"{band:g}"]["mean_core_energy_fj"], k.split("|")[1]) for k, v in out.items()
                     if k.startswith(mode) and v["bands"][f"{band:g}"]["feasible"]]
            pick = min(cands)[1] if cands else None
            out.setdefault("selection", {})[f"{mode}|{band:g}"] = pick
            print(f"selection {mode} >= {band:g} mV: {pick}")
    (R2.OUT / f"r21_score{'_refined' if REFINED else ''}.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


REFINE_STEP_PS = 0.625


def refine(modes=("width", "mult")) -> None:
    """Re-simulate every +/-1 mV, 1 ns point of all three designs at 0.625 ps (same treatment for all).

    The sealed record refined all +/-1 mV points of the selected design but only extreme/near-margin points
    of the others; here every design gets the same single fine step. Results: out/r21/refined.json."""
    from dataclasses import asdict, fields as dc_fields
    from comparator_atlas.spice import Point, Simulator, measure
    names = [f.name for f in dc_fields(Point)]
    todo = []
    for mode in modes:
        for design in DESIGNS3:
            rows, _ = frame(design, mode)
            for row in rows[rows.input_mv.abs().eq(1.0)].to_dict("records"):
                kw = {k: row[k] for k in names if k in row}
                kw = {k: (None if isinstance(v, float) and v != v else v) for k, v in kw.items()}
                kw["trim_code"] = int(kw["trim_code"])
                todo.append((mode, design, row, Point(**{**kw, "max_step_ps": REFINE_STEP_PS})))
    print(f"refining {len(todo)} points at {REFINE_STEP_PS} ps", flush=True)
    pts = [p for *_, p in todo]
    with ThreadPoolExecutor(max_workers=14) as pool:
        traces = list(pool.map(lambda p: Simulator(R2.CACHE, workers=1).run_many([p])[0], pts))
    out = []
    for (mode, design, row, point), trace in zip(todo, traces):
        m = measure(trace, DEADLINE)
        out.append({"mode": mode, "design": design, "case_id": row["case_id"], "input_mv": row["input_mv"],
                    "coarse_outcome": row["outcome"], "fine_outcome": m.outcome,
                    "coarse_energy_fj": row["core_energy_fj"], "fine_energy_fj": m.core_energy_fj,
                    "point": asdict(point)})
    (R2.OUT / "refined.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    flips = [r for r in out if r["coarse_outcome"] != r["fine_outcome"]]
    for r in flips:
        print("flip", r["mode"], r["design"], r["case_id"], r["input_mv"], r["coarse_outcome"], "->", r["fine_outcome"])
    print(f"{len(flips)} flips of {len(out)}")


if __name__ == "__main__":
    if ARGS[0] == "refine":
        refine()
    elif ARGS[0] == "run":
        design, mode = ARGS[1], ARGS[2]
        assert design in DESIGNS3 and mode in ("width", "mult")
        R2.run_phase(design + ("__m" if mode == "mult" else ""), INPUTS, mode)
    elif ARGS[0] == "score":
        REFINED = len(ARGS) > 1 and ARGS[1] == "refined"
        score()
