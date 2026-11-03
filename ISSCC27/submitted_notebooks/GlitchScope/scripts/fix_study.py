"""How to fix: function-preserving edits for the best attributed cells of a benchmark.

    python scripts/fix_study.py <liberty> [bench] [n_vectors] [workers]

Uses the greedy joint fix set from data/bench/counterfactual_<bench>.json (run
scripts/counterfactual.py first) and writes data/bench/whatif_<bench>.json:
every evaluated edit, the best qualifying edit per cell, the combined edit set,
and the oracle suppression potential of each cell for comparison.
"""
import json, random, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs
from glitchscope.m2model import M2Model
from glitchscope.whatif import WhatIf

LIB = sys.argv[1]; BENCH = sys.argv[2] if len(sys.argv) > 2 else "mul4"
NV = int(sys.argv[3]) if len(sys.argv) > 3 else 300; W = int(sys.argv[4]) if len(sys.argv) > 4 else 0
cf = json.loads((ROOT / f"data/bench/counterfactual_{BENCH}.json").read_text())
cells = [c for c, _ in cf["greedy"]]
lib = parse_liberty_file(LIB); net = read_verilog(ROOT / f"bench/netlists/{BENCH}.v")
rnd = random.Random(7); vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(NV)]
t = time.time()
wi = WhatIf(net, lib, LIB, LibertyDelayProvider(lib), M2Model(), vecs,
            sim_kwargs=dict(default_input_slew_fs=ps_to_fs(40)), workers=W)
rows, best, comb = wi.suggest(cells)
out = dict(bench=BENCH, vectors=NV, cells=cells, potential={c: cf["single"].get(c) for c in cells},
           rows=rows, best=best, combined=comb, seconds=time.time() - t,
           E_total_fJ=wi.E_total, E_glitch_fJ=wi.E_glitch)
(ROOT / f"data/bench/whatif_{BENCH}.json").write_text(json.dumps(out, indent=1))
for c in cells:
    rs = sorted((r for r in rows if r["cell"] == c), key=lambda r: r["dE_total_fJ"])
    b = rs[0] if rs else None
    print(f"{c:6s} potential {100 * (cf['single'].get(c) or 0):5.1f}% | best edit {b['edit'] if b else '-':45s} "
          f"total {b['dE_total_pct'] if b else 0:+.2f}% glitch {b['dE_glitch_pct'] if b else 0:+.2f}%")
if comb:
    print(f"combined: total {comb['dE_total_pct']:+.2f}% glitch {comb['dE_glitch_pct']:+.2f}% "
          f"settle {comb['settle_before_ps']:.0f}->{comb['settle_after_ps']:.0f} ps  ({time.time() - t:.0f}s)")
