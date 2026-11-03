"""Glitch energy and the automatic fix under local process variation (mismatch).

Every combinational cell instance gets its own delay factor 1 + sigma_cell * N(0, 1),
with sigma_cell the relative delay sigma of that cell type measured by SPICE Monte Carlo
on the PDK's mismatch models (scripts/mismatch_sigma.py).  Each random die is applied to
the original multiplier and to the two retimed versions (same instances, same factors:
paired comparison), on the same stimulus as section 11, and measured with M2.
``--sigma-scale k`` multiplies all sigmas (e.g. to emulate low supply voltage).

    python scripts/mismatch_study.py <liberty> [n_dies] [--sigma-scale k ...]
        -> data/mismatch/study.json
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402

DESIGNS = {"original": ROOT / "bench/layout/mul16_v0.v",
           "timing_driven": ROOT / "data/glitchfix/mul16_r/timing_driven.v",
           "glitchscope": ROOT / "data/glitchfix/mul16_r/optimized.v"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("dies", nargs="?", type=int, default=30)
    ap.add_argument("--sigma-scale", type=float, nargs="+", default=[1.0, 3.0])
    a = ap.parse_args()
    sig = json.loads((ROOT / "data/mismatch/sigma.json").read_text())
    default = float(np.mean([v["rel_sigma"] for v in sig.values()]))
    fxs = {k: GlitchFix(p, a.lib, random_vectors=40, period_ps=15000, sample=16, grid=2, log=lambda m: None)
           for k, p in DESIGNS.items()}
    names = [c.name for c in fxs["original"].design.network.cells]
    kind = {c.name: c.library_cell.split("__")[-1] for c in fxs["original"].design.network.cells}
    out = dict(cells=len(names), sigma_cell={k: v["rel_sigma"] for k, v in sig.items()}, runs={})
    for k, fx in fxs.items():                       # nominal
        fx.delay_scale = None
        out.setdefault("nominal", {})[k] = fx.original().energy
    for ss in a.sigma_scale:
        rows = []
        t0 = time.time()
        for die in range(a.dies):
            rnd = random.Random(1000 * die + 7)
            scale = {n: max(0.5, 1.0 + ss * sig.get(kind[n], {}).get("rel_sigma", default) * rnd.gauss(0, 1))
                     for n in names}
            row = {}
            for k, fx in fxs.items():
                fx.delay_scale = scale
                e = fx.original().energy
                row[k] = dict(total=e["total"], glitch=e["glitch"])
            rows.append(row)
        tot = {k: np.array([r[k]["total"] for r in rows]) for k in DESIGNS}
        gl = {k: np.array([r[k]["glitch"] for r in rows]) for k in DESIGNS}
        sav = {k: 1 - tot[k] / tot["original"] for k in ("timing_driven", "glitchscope")}
        summ = dict(sigma_scale=ss, dies=a.dies, seconds=round(time.time() - t0, 1),
                    total_mean={k: float(v.mean()) for k, v in tot.items()},
                    total_sd={k: float(v.std(ddof=1)) for k, v in tot.items()},
                    glitch_mean={k: float(v.mean()) for k, v in gl.items()},
                    glitch_sd={k: float(v.std(ddof=1)) for k, v in gl.items()},
                    saving_mean={k: float(v.mean()) for k, v in sav.items()},
                    saving_min={k: float(v.min()) for k, v in sav.items()},
                    glitchscope_beats_timing=int(np.sum(tot["glitchscope"] < tot["timing_driven"])), rows=rows)
        out["runs"][str(ss)] = summ
        (ROOT / "data/mismatch/study.json").write_text(json.dumps(out, indent=1))
        o = tot["original"]
        print(f"sigma x{ss}: original {o.mean() / 1e3:.1f} +- {o.std(ddof=1) / 1e3:.2f} pJ "
              f"(nominal {out['nominal']['original']['total'] / 1e3:.1f}); saving timing-driven "
              f"{100 * sav['timing_driven'].mean():.1f} % (min {100 * sav['timing_driven'].min():.1f}), GlitchScope "
              f"{100 * sav['glitchscope'].mean():.1f} % (min {100 * sav['glitchscope'].min():.1f}); GlitchScope better on "
              f"{summ['glitchscope_beats_timing']}/{a.dies} dies  ({summ['seconds']:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
