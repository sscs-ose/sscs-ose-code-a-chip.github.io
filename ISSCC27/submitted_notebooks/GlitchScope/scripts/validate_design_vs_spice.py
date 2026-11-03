"""Sequential design (MAC) : GlitchScope M0/M1/M2 vs transistor-level SPICE with real flops."""
import sys, json, time
from collections import Counter
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.verilog import read_design
from glitchscope.seq import read_vcd, read_clk_to_q, build_cycles
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.functional import evaluate_stable
from glitchscope.model import ps_to_fs, StimulusEpoch
from glitchscope.spice.netlist_sim import simulate_design
LIB, NL, VCD, N = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
lib = parse_liberty_file(LIB); dp = LibertyDelayProvider(lib); m2 = M2Model()
design = read_design(NL, lib); net = design.network
dcap = {f.d: lib.cells[f.libcell].pin_capacitance.get("D", 0.0) for f in design.flops}
mk = lambda m: PulseSimulator(net, dp, m, r_filter=m2, default_input_slew_fs=ps_to_fs(40), primary_output_load_ff_by_net=dcap)
waves, _ = read_vcd(VCD)
init, cycles, edges = build_cycles(design, waves, lib, read_clk_to_q(LIB, {f.libcell for f in design.flops}), mk("M1").loads)
period = (edges[1] - edges[0]) / 1000
skip = 3                                    # skip testbench reset cycles
state = dict(init)
for cyc in cycles[:skip]:
    for _, u in cyc: state.update(u)
cyc_sel = cycles[skip:skip + N]
import os
CELLS = "_pex" if "pex" in os.environ.get("GS_CELL_SPICE", "") else ""   # parasitic-extracted cell netlists
cache = ROOT / f"data/bench/spice_ref_{Path(NL).stem}_{N}{CELLS}.json"
t0 = time.time()
if cache.exists():
    ref = json.loads(cache.read_text())
else:
    # warm-up: hold the pre-window PI values for 2 cycles; flops must load the same state.
    # Use the testbench's own reset cycles so the SPICE flops reach `state`: we replay cycles[:skip] too.
    ref_all = simulate_design(design, cycles[:skip + N], edges, {pi: init[pi] for pi in design.real_inputs}, period, step_ps=2.0)
    ref = ref_all[skip:]
    cache.write_text(json.dumps(ref))
print(f"SPICE {time.time() - t0:.0f}s, {N} cycles, comb E/cycle={np.mean([r['E_fJ'] for r in ref]):.1f} fJ")
# required transitions per cycle
req, st = [], dict(state)
for cyc in cyc_sel:
    cur = dict(st)
    for _, u in cyc: cur.update(u)
    b, a = evaluate_stable(net, st), evaluate_stable(net, cur)
    req.append({n: int(b[n] != a[n]) for n in ref[0]["crossings"]}); st = cur
G_sp = sum(r["crossings"][n] - req[k][n] for k, r in enumerate(ref) for n in r["crossings"])
X_sp = sum(sum(r["crossings"].values()) for r in ref)
E_sp = np.array([r["E_fJ"] for r in ref])
print(f"SPICE transitions={X_sp} glitch transitions={G_sp}")
out = {"spice_glitch_transitions": G_sp, "spice_E_per_cycle": E_sp.mean()}
for m, cal in [("M0", False), ("M1", False), ("M2", False), ("M2", True)]:
    sim = mk(m); em = EnergyModel(LIB, net, spice_scale=cal)
    a = analyze(sim, em, cyc_sel, initial=state)
    E = np.array([v["E_fun"] + v["E_glitch"] for v in a["per_vector"]])
    g, prev = 0, dict(state)
    for k, cyc in enumerate(cyc_sel):
        sim.network = replace(net, initial_inputs=dict(prev))
        tr = sim.run([StimulusEpoch(100_000 + o, dict(u), k + 1) for o, u in cyc] or [StimulusEpoch(100_000, {}, k + 1)])["trace"]
        cnt = Counter(e.net for e in tr if e.source_instance != "$PI")
        g += sum(cnt.get(n, 0) - req[k][n] for n in req[k])
        for _, u in cyc: prev.update(u)
    tag = f"{m}+{'CAL' if cal else 'LIB'}"
    out[tag] = dict(E_ratio=E.sum() / E_sp.sum(), corr=float(np.corrcoef(E, E_sp)[0, 1]), glitch_ratio=g / max(1, G_sp))
    print(f"  {tag}: E/SPICE={E.sum() / E_sp.sum():.3f}  per-cycle corr={out[tag]['corr']:.3f}  glitch transitions={g} ({g / max(1, G_sp):.2f}x)")
(ROOT / f"data/bench/spice_validation_{Path(NL).stem}{CELLS}.json").write_text(json.dumps(out, indent=1, default=float))
