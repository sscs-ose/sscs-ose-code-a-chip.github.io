"""Large-design study on the c6288-style 16x16 NOR array multiplier (2368 cells).

    python scripts/arraymul_study.py <liberty> [n_vectors] [workers]

Writes data/bench/arraymul16_study.json incrementally (one key per stage):
baseline (M0/M1/M2 energy split, runtime), row-group and depth-band
interventional attribution (+ Shapley / greedy), screened single-cell potentials
vs the structural ranking, and what-if fixes for the best single cells.
"""
import json, random, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.sim import PulseSimulator
from glitchscope.attribution import InterventionalAttribution, make_groups
from glitchscope.whatif import WhatIf

LIB = sys.argv[1]
NV = int(sys.argv[2]) if len(sys.argv) > 2 else 24
W = int(sys.argv[3]) if len(sys.argv) > 3 else 0
OUT = ROOT / "data/bench/arraymul16_study.json"
data = json.loads(OUT.read_text()) if OUT.exists() else {}


def save(key, val):
    data[key] = val
    OUT.write_text(json.dumps(data, indent=1))
    print(f"[{time.strftime('%H:%M:%S')}] saved {key}", flush=True)


lib = parse_liberty_file(LIB)
net = read_verilog(ROOT / "bench/netlists/arraymul16.v")
dp = LibertyDelayProvider(lib)
em = EnergyModel(LIB, net, spice_scale=True)
rnd = random.Random(7)
vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(NV)]
kw = dict(default_input_slew_fs=ps_to_fs(40))

if "models" not in data:
    models = {}
    for m in ("M0", "M1", "M2"):
        t = time.time()
        sim = PulseSimulator(net, dp, m, r_filter=M2Model(), **kw)
        r = analyze(sim, em, vecs)
        models[m] = dict(totals=r["totals"], counts=r["counts"], seconds=time.time() - t)
        print(m, f"{time.time() - t:.0f}s glitch={r['totals']['glitch_fraction']:.3f}", flush=True)
    save("models", dict(cells=len(net.cells), vectors=NV, **models))

t = time.time()
ia = InterventionalAttribution(net, dp, M2Model(), em, vecs, sim_kwargs=kw, workers=W)
base_s = time.time() - t
print(f"baseline {base_s:.0f}s, workers={ia.workers}", flush=True)


def pack(r, t0):
    keep = ("single", "top", "shapley", "joint_top", "sum_single_top", "greedy", "structural",
            "evaluations", "screened", "certified", "units", "group_sizes")
    return dict({k: r[k] for k in keep}, seconds=time.time() - t0)


if "rows" not in data:
    t = time.time()
    g = make_groups(net, "regex", pattern=r"^(pp|r\d\d|rf)")
    save("rows", pack(ia.run(top_k=6, perms=4, greedy_k=4, candidates=6, groups=g), t))
if "levels" not in data:
    t = time.time()
    g = make_groups(net, "level", bands=12)
    save("levels", pack(ia.run(top_k=4, perms=0, greedy_k=3, candidates=6, groups=g), t))
if "cells" not in data:
    t = time.time()
    r = ia.run(top_k=6, perms=0, greedy_k=-1, candidates=6, max_screen=12)
    struct_top = sorted(r["structural"], key=lambda c: -r["structural"][c])[:6]
    sg = dict(zip(struct_top, ia.gains([{c} for c in struct_top])))
    out = pack(r, t)
    out["structural"] = {c: r["structural"][c] for c in sorted(r["structural"], key=lambda c: -r["structural"][c])[:30]}
    out["structural_top_gain"] = sg
    out["bounds_top"] = sorted(ia._bounds.values(), reverse=True)[:30]
    save("cells", out)
if "whatif" not in data:
    t = time.time()
    top = data["cells"]["top"][:4]
    wi = WhatIf(net, lib, LIB, dp, M2Model(), vecs, sim_kwargs=kw, workers=W)
    rows, best, comb = wi.suggest(top)
    save("whatif", dict(cells=top, rows=rows, best=best, combined=comb, seconds=time.time() - t,
                        E_total_fJ=wi.E_total, E_glitch_fJ=wi.E_glitch))
print("done", flush=True)
