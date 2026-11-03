"""r25 report: paired comparison r22 (4b) / r24c (4b + equalize) / r25 (5b + equalize, trim_l 1) at the hot
corners, and r3 (4b) / r25 at TT 1.8 V 27 C (seeds 0-39).

  python -B r25_report.py      # writes out/r25/r25_report.json
"""
import glob
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SETS = {"r22 4b": "out/r22/mc_{c}_lvt_balanced_4b_*.jsonl", "r24c 4b+eq": "out/r24/fixmc_{c}_lvt_balanced_4b.jsonl",
        "r25 5b+eq": "out/r25/mc_{c}_eq5_l100.jsonl"}


def load(pat):
    rows = {}
    for f in glob.glob(str(HERE / pat)):
        for ln in Path(f).read_text().splitlines():
            r = json.loads(ln)
            rows[r["seed"]] = r
    return rows


def summary(rows):
    rs = [rows[s] for s in sorted(rows)]
    m = np.abs([r["m_mv"] for r in rs])

    def ok(v, dl):
        es = [e for r in rs for e in r["evals"] if abs(e["v_mv"]) == v and e["deadline_ns"] == dl]
        return sum(e["outcome"] == "correct" for e in es), len(es)

    one = [e for r in rs for e in r["evals"] if abs(e["v_mv"]) == 1 and e["deadline_ns"] == 1.0]
    return {"n": len(rs), "covered": sum(r["covered"] for r in rs),
            "uncovered": [r["seed"] for r in rs if not r["covered"]],
            "seed3_13_m": [round(rows[s]["m_mv"], 2) for s in (3, 13) if s in rows],
            "abs_m_rms": float(np.sqrt(np.mean(m ** 2))), "abs_m_max": float(m.max()),
            "abs_m_le_1": int((m <= 1.0).sum()),
            "pm1_1ns": ok(1, 1.0), "pm1_3p5ns": ok(1, 3.5), "pm3_1ns": ok(3, 1.0), "pm0p5_3p5ns": ok(0.5, 3.5),
            "pm1_1ns_wrong": sum(e["outcome"] == "wrong" for e in one),
            "pm1_1ns_unresolved": sum(e["outcome"] == "unresolved" for e in one)}


def main():
    rep = {}
    for c in ("sf1.95V125C", "ff1.95V125C"):
        for k, pat in SETS.items():
            rows = load(pat.format(c=c))
            if len(rows) == 40:
                rep[f"{c} {k}"] = summary(rows)
                print(f"{c} {k}: {rep[f'{c} {k}']}")
    tt = {"r3 4b": {s: r for s, r in load("out/r3/mc_lvt_balanced_4b_*.jsonl").items() if s < 40},
          "r25 5b+eq": load("out/r25/mc_tt1.8V27C_eq5_l100.jsonl")}
    for k, rows in tt.items():
        rep[f"tt1.8V27C {k}"] = summary(rows)
        print(f"tt1.8V27C {k}: {rep[f'tt1.8V27C {k}']}")
    (HERE / "out" / "r25" / "r25_report.json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
