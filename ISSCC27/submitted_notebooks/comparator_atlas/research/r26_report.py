"""r26 report: paired MC of the scaled designs against r22 (4b) and r25 (5b + equalize, k 1), with the untrimmed
offset sigma (the same z draw scaled by each design's PDK sigma).

  python -B r26_report.py      # writes out/r26/r26_report.json
"""
import glob
import json
from pathlib import Path

import numpy as np

from r25_report import load, summary

HERE = Path(__file__).resolve().parent
REF = {"r22 4b": "out/r22/mc_{c}_lvt_balanced_4b_*.jsonl", "r25 s5_k100": "out/r25/mc_{c}_eq5_l100.jsonl"}


def main():
    rep = {}
    for c in ("sf1.95V125C", "ff1.95V125C", "tt1.8V27C"):
        sets = dict(REF)
        if c.startswith("tt"):
            sets["r22 4b"] = "out/r3/mc_lvt_balanced_4b_*.jsonl"
        for f in sorted(glob.glob(str(HERE / "out" / "r26" / f"mc_{c}_*.jsonl"))):
            sets["r26 " + Path(f).stem.split("_", 2)[2]] = str(Path(f).relative_to(HERE))
        for k, pat in sets.items():
            rows = {s: r for s, r in load(pat.format(c=c)).items() if s < 40}
            if len(rows) != 40:
                continue
            s = summary(rows)
            s["b0_sigma_mv"] = float(np.std([r["b0_mv"] for r in rows.values()]))
            rep[f"{c} {k}"] = s
            print(f"{c} {k}: cov {s['covered']} pm1 {s['pm1_1ns']} pm3 {s['pm3_1ns']} |m|max {s['abs_m_max']:.2f} "
                  f"rms {s['abs_m_rms']:.2f} s3/13 {s['seed3_13_m']} sigma_b0 {s['b0_sigma_mv']:.1f}", flush=True)
    (HERE / "out" / "r26" / "r26_report.json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
