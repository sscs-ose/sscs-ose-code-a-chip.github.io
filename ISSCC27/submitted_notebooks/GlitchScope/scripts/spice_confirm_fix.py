"""Transistor-level confirmation of an automatic fix: the original design and GlitchScope's
rewritten netlist are both simulated in ngspice with every SKY130 cell and real dfxtp
flip-flops, on exactly the stimulus GlitchScope measured them with, and the energy
saving predicted by GlitchScope is compared with the one SPICE measures.

SPICE gives the logic supply and the flip-flop supply separately; the clock pins are driven
by an ideal source, so the clock-network energy (pin capacitance plus clock tree, the same
analytic Liberty term in GlitchScope) is added identically to both sides.

    python scripts/spice_confirm_fix.py <liberty> <case> [n_cycles]
        case: a data/glitchfix/<case> study (original netlist from its config, optimized.v)
        -> data/glitchfix/<case>/spice_confirm.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402
from glitchscope.spice.netlist_sim import simulate_design  # noqa: E402
from glitchscope.spice.pulse_sweep import VDD  # noqa: E402

LIB, CASE = sys.argv[1], sys.argv[2]
NC = int(sys.argv[3]) if len(sys.argv) > 3 else 16
ONLY = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] != "-" else None   # run a subset (e.g. in parallel)
GS_ONLY = "--gs-only" in sys.argv          # recompute only GlitchScope's side, reusing the cached SPICE result
SKIP = 4                                     # cycles to fill the pipeline registers in SPICE
d = ROOT / "data/glitchfix" / CASE
cfg = json.loads((d / "optimize.json").read_text())["config"]
designs = {"original": ROOT / cfg["netlist"], "timing_driven": d / "timing_driven.v", "glitchscope": d / "optimized.v"}
res = d / "spice_confirm.json"
out = json.loads(res.read_text()) if res.exists() else {}
out.update(case=CASE, cycles=NC, period_ps=cfg["period_ps"])
for tag, path in designs.items():
    if ONLY and tag not in ONLY:
        continue
    fx = GlitchFix(path, LIB, random_vectors=SKIP + NC + 2, period_ps=cfg["period_ps"], sample=NC, grid=2,
                   log=lambda m: None)
    idx = list(range(SKIP + 1, SKIP + 1 + NC))
    fx.sample_idx = idx
    e = fx.original().energy                           # GlitchScope on exactly these cycles
    lc = fx.lib.cells[fx.design.flops[0].libcell]
    c_clk = lc.pin_capacitance.get(fx.design.flops[0].clk_pin, 0.0)
    e_clknet = len(fx.design.flops) * (1 + fx.fe.k_tree) * c_clk * fx.fe.vdd ** 2   # per cycle, fJ
    t0 = time.time()
    if GS_ONLY and tag in out and "spice" in out[tag]:      # model changed, SPICE did not: reuse it
        gs_comb = e["functional"] + e["glitch"]
        gs_ff = e["flop_clock"] + e["flop_data"] - e_clknet
        out[tag]["glitchscope"] = dict(logic=gs_comb, glitch=e["glitch"], flops=gs_ff, clock_network=e_clknet,
                                       total=gs_comb + gs_ff + e_clknet)
        res.write_text(json.dumps(out, indent=1))
        print(f"{tag:12s} GlitchScope logic {gs_comb:8.1f} ff {gs_ff:7.1f} (SPICE reused)", flush=True)
        continue
    rows = simulate_design(fx.design, fx.cycles0[:SKIP + 1 + NC], fx.edges0,
                           {pi: fx.init0[pi] for pi in fx.design.real_inputs}, cfg["period_ps"], step_ps=2.0,
                           save_nets=False)
    sp = rows[SKIP + 1:SKIP + 1 + NC]
    sp_comb = float(np.mean([r["E_fJ"] for r in sp]))
    sp_ff = float(np.mean([r["E_ff_fJ"] for r in sp]))
    gs_comb = e["functional"] + e["glitch"]
    gs_ff = e["flop_clock"] + e["flop_data"] - e_clknet           # flip-flop internal, as SPICE sees it
    out[tag] = dict(flops=len(fx.design.flops), spice_seconds=round(time.time() - t0),
                    spice=dict(logic=sp_comb, flops=sp_ff, clock_network=e_clknet, total=sp_comb + sp_ff + e_clknet),
                    glitchscope=dict(logic=gs_comb, glitch=e["glitch"], flops=gs_ff, clock_network=e_clknet,
                                     total=gs_comb + gs_ff + e_clknet))
    if res.exists():                                   # merge with a parallel run
        out = {**json.loads(res.read_text()), **{k: v for k, v in out.items() if k == tag}}
    res.write_text(json.dumps(out, indent=1))
    print(f"{tag:12s} SPICE logic {sp_comb:8.1f} ff {sp_ff:7.1f} | GlitchScope logic {gs_comb:8.1f} ff {gs_ff:7.1f} "
          f"| clock net {e_clknet:6.1f} fJ/cycle  ({out[tag]['spice_seconds']} s)", flush=True)
out = json.loads(res.read_text())
if all(t in out for t in designs):
    o = out["original"]
    for t in ("timing_driven", "glitchscope"):
        for k in ("spice", "glitchscope"):
            out[f"saving_{t}_{k}"] = 1 - out[t][k]["total"] / o[k]["total"]
        print(f"{t:14s} saving: SPICE {100 * out[f'saving_{t}_spice']:+.1f} %   GlitchScope {100 * out[f'saving_{t}_glitchscope']:+.1f} %")
    res.write_text(json.dumps(out, indent=1))
