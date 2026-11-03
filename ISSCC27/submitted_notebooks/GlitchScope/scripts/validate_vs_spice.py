"""Whole-circuit SPICE reference vs GlitchScope M0/M1/M2 (energy + transition counts)."""
import sys, time, random, json
from dataclasses import replace
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs, StimulusEpoch
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.spice.netlist_sim import simulate
from glitchscope.functional import evaluate_stable
LIB, bench, NV = sys.argv[1], sys.argv[2], int(sys.argv[3])
PERIOD = float(sys.argv[4]) if len(sys.argv) > 4 else 3000.0   # ps per vector: must exceed the settling time
_p = Path(bench)
if _p.suffix == ".v" and _p.exists():          # any netlist path (e.g. a mapped ISCAS'85 circuit)
    net, bench = read_verilog(_p), _p.stem
else:
    net = read_verilog(ROOT / f"bench/netlists/{bench}.v")
rnd = random.Random(11)
vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(NV)]
init = dict(net.initial_inputs)
import os
CELLS = "_pex" if "pex" in os.environ.get("GS_CELL_SPICE", "") else ""   # parasitic-extracted cell netlists
cache = ROOT / (f"data/bench/spice_ref_{bench}_{NV}{CELLS}.json" if PERIOD == 3000.0 else
               f"data/bench/spice_ref_{bench}_{NV}_{PERIOD:.0f}ps{CELLS}.json")
t0 = time.time()
if cache.exists():
    ref = json.loads(cache.read_text())
else:
    ref = simulate(net, vecs, init, period_ps=PERIOD); cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(ref))
ts = time.time() - t0
E_sp = np.array([r["E_fJ"] for r in ref]); X_sp = sum(sum(r["crossings"].values()) for r in ref)
dp = LibertyDelayProvider(parse_liberty_file(LIB)); m2 = M2Model()
EMS = {"LIB": EnergyModel(LIB, net), "CAL": EnergyModel(LIB, net, spice_scale=True)}
# functionally required transitions per vector and SPICE excess (glitch) transitions
req, pv = [], dict(init)
for vec in vecs:
    cur = {**pv, **vec}; b, a = evaluate_stable(net, pv), evaluate_stable(net, cur)
    req.append({n: int(b[n] != a[n]) for n in ref[0]["crossings"]}); pv = cur
G_sp = sum(r["crossings"][n] - req[k][n] for k, r in enumerate(ref) for n in r["crossings"])
res = {"spice_glitch_transitions": G_sp, "bench": bench, "vectors": NV, "spice_secs": round(ts, 1), "E_spice_fJ_per_vec": E_sp.mean(),
       "spice_transitions": X_sp}
print(f"{bench}: SPICE {ts:.0f}s  E/vec={E_sp.mean():.1f} fJ  transitions={X_sp}  glitch transitions={G_sp}")
for m, ek in [("M0", "LIB"), ("M1", "LIB"), ("M2", "LIB"), ("M2", "CAL")]:
    sim = PulseSimulator(net, dp, m, r_filter=m2, default_input_slew_fs=ps_to_fs(40))
    a = analyze(sim, EMS[ek], vecs)
    E = np.array([v["E_fun"] + v["E_glitch"] for v in a["per_vector"]])
    # transition counts per vector per net
    prev, match, tot, n_tr, g_tr = dict(init), 0, 0, 0, 0
    for k, vec in enumerate(vecs):
        sim.network = replace(net, initial_inputs=dict(prev))
        tr = sim.run([StimulusEpoch(100_000, dict(vec), k + 1)])["trace"]
        cnt = Counter(e.net for e in tr if e.source_instance != "$PI")
        for n, x in ref[k]["crossings"].items():
            tot += 1; match += cnt.get(n, 0) == x; n_tr += cnt.get(n, 0); g_tr += cnt.get(n, 0) - req[k][n]
        prev = {**prev, **vec}
    ratio = E.sum() / E_sp.sum()
    corr = float(np.corrcoef(E, E_sp)[0, 1])
    res[f"{m}_{ek}"] = dict(E_ratio=ratio, E_corr=corr, transitions=n_tr, transition_ratio=n_tr / X_sp,
                  net_vector_exact_match=match / tot, glitch_transitions=g_tr,
                        glitch_transition_ratio=g_tr / max(1, G_sp))
    print(f"  {m}+{ek}: E_total/SPICE={ratio:.3f}  per-vector corr={corr:.3f}  transitions={n_tr} "
          f"({n_tr / X_sp:.2f}x)  glitch={g_tr} ({g_tr / max(1, G_sp):.2f}x)  exact per-net count match={match / tot:.3f}")
(ROOT / "data/bench").mkdir(exist_ok=True, parents=True)
res["period_ps"] = PERIOD
res["library"] = Path(LIB).name if "spice" in Path(LIB).name else "liberty"
tag = ("_charlib" if "spice" in Path(LIB).name else "") + CELLS   # SPICE re-characterised library / PEX cells
res["cells"] = "pex" if CELLS else "schematic"
(ROOT / f"data/bench/spice_validation_{bench}{tag}.json").write_text(json.dumps(res, indent=1, default=float))
