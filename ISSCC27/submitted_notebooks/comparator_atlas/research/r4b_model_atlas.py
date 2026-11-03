"""R4b: model-predicted atlas and continuous minimum-input curve vs. the checked atlas."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r1_trim_floor as r1  # noqa: E402

DEADLINES = (0.25, 0.35, 0.5, 0.75, 1.0, 2.0)
BANDS = (0.25, 0.5, 1.0, 3.0, 10.0, 30.0)


def main() -> int:
    df = pd.read_csv(r1.OUT / "r4_samples.csv")
    df = df[df.input_mv.ne(0)]
    cond = df.drop_duplicates(["design_name", "case_id"])
    cells, curves = [], {}
    for design, g in df.groupby("design_name"):
        c = cond[cond.design_name.eq(design)]
        for d in DEADLINES:
            # Conditions with non-physical (tau <= 0) fits are treated as never resolving in time.
            need = np.where(c.tau_ps > 0, c.residual_mv.abs() + np.exp(-(d - c.t0_ns) / (c.tau_ps / 1000)), np.inf)
            curves.setdefault(design, {})[f"{d:g}ns"] = float(np.max(need))
            for b in BANDS:
                part = g[g.input_mv.abs().ge(b)]
                obs_ok = bool(part[f"obs_{d:g}"].eq("correct").all())
                pred_ok = bool(
                    ((part.t_pred_ns <= d)
                     & (np.sign(part.input_mv - part.residual_mv) == np.sign(part.input_mv))).all())
                cells.append({"design": design, "deadline_ns": d, "band_mv": b,
                              "observed_qualifies": obs_ok, "model_qualifies": pred_ok,
                              "curve_qualifies": bool(np.max(need) <= b)})
    cells = pd.DataFrame(cells)
    report = {
        "cells": len(cells),
        "model_vs_observed_agree": int(cells.observed_qualifies.eq(cells.model_qualifies).sum()),
        "curve_vs_observed_agree": int(cells.observed_qualifies.eq(cells.curve_qualifies).sum()),
        "disagreements": cells[cells.observed_qualifies.ne(cells.model_qualifies)
                               | cells.observed_qualifies.ne(cells.curve_qualifies)].to_dict("records"),
        "continuous_min_input_mv": curves,
    }
    (r1.OUT / "r4b_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

