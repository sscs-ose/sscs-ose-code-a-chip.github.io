#!/usr/bin/env python3
"""results/energy_activity.csv: same post-layout netlist, real GPT-2 activity vs random inputs.
real = power_real.rpt (first 100 cases of the design's migrated real-layer set, driven by
flow/gl_stim_npz.py); random = power_random.rpt (first 100 cases of the *_random.npz). Both: compute
window only. dcim_core_ff real = w4a4_real_layer.npz (W4A4+mig+wclip, the encoding of the 4-bit row);
its earlier run on the naive W4A4 real_layer.npz (no migration) is kept as stimulus real_nomig
(power_real_nomig.rpt), a labelled extra row that no table reads as the 4-bit energy.
Toggle stats from the first 100 vector cases: x_in bit flips per bit between consecutive cases;
ones density of x and w bits."""
import csv
import re
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "flow"))
PER = int(re.search(r"clock_period_ns:\s*(\d+)", (ROOT / "spec/spec.yaml").read_text()).group(1))
CYC = {"dcim_w7a4_ff": 4, "dcim_w4a8_ff": 8, "sidecarcim_top_ff_pipe_s3": 5, "sidecarcim_top_ff_pipe": 5, "dcim_w8a4_ff": 4, "dcim_w6a4_ff": 4, "dcim_core_ff": 4, "sidecarcim_top_ff": 4, "dcim_8bit_ff": 8}
VEC = {"dcim_w7a4_ff": ("w7a4_real_layer", "w7a4_random", 4),
       "dcim_w4a8_ff": ("w4a8_real_layer", "w4a8_random", 8),
       "sidecarcim_top_ff_pipe_s3": ("sidecar_s3_real_layer", "sidecar_s3_random", 4),
       "sidecarcim_top_ff_pipe": ("sidecar_real_layer", "sidecar_random", 4),
       "dcim_core_ff": ("w4a4_real_layer", "random", 4),
       "dcim_w8a4_ff": ("w8a4_real_layer", "w8a4_random", 4),
       "dcim_w6a4_ff": ("w6a4_real_layer", "w6a4_random", 4), "sidecarcim_top_ff": ("sidecar_real_layer", "sidecar_random", 4),
       "dcim_8bit_ff": ("dense8_real_layer", "dense8_random", 8)}


def power_mw(rpt):
    for l in rpt.read_text().splitlines():
        if l.startswith("Total"):
            return float(re.findall(r"[-+]?\d+\.\d+e[-+]\d+", l)[3]) * 1e3


def bits(a, n):
    return np.unpackbits(a.astype(np.uint8)[..., None], axis=-1)[..., -n:]


# extra labelled rows: design -> [(stimulus, vector file, report)]
EXTRA = {"dcim_core_ff": [("real_nomig", "real_layer", "power_real_nomig.rpt")]}
rows = []
WB = {"dcim_w7a4_ff": 7, "dcim_w4a8_ff": 4, "dcim_w8a4_ff": 8, "dcim_w6a4_ff": 6}
for d, (real, rnd, nb) in VEC.items():
    runs = sorted((ROOT / "flow" / d / "runs").glob("RUN_*")) if (ROOT / "flow" / d / "runs").exists() else []
    if not runs:
        continue
    run = runs[-1]
    for stim, vf, rpt in [("real", real, "power_real.rpt"), ("random", rnd, "power_random.rpt")] + EXTRA.get(d, []):
        if not (run / rpt).exists() or not (ROOT / "python" / "vectors" / (vf + ".npz")).exists():
            continue
        z = np.load(ROOT / "python" / "vectors" / (vf + ".npz"))
        x, w = z["x"][:100], z["w"][:100]
        xb = bits(x, nb).reshape(100, -1)
        p = power_mw(run / rpt)
        e = p * CYC[d] * PER
        rows.append({"design": d, "stimulus": stim, "power_mw_est": float("%.4g" % p),
                     "energy_per_dot_pj_est": round(e, 1), "energy_per_mac_fj_est": round(e * 1000 / 256, 1),
                     "x_toggle_per_bit_per_case": round(float(np.mean(xb[1:] != xb[:-1])), 4),
                     "x_ones_frac": round(float(xb.mean()), 4), "w_ones_frac": round(float(bits(w, WB.get(d, nb)).mean()), 4),
                     "cases": 100, "run_dir": str(run.relative_to(ROOT))})
with open(ROOT / "results" / "energy_activity.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)
print(open(ROOT / "results" / "energy_activity.csv").read())
