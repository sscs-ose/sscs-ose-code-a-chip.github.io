"""Event-for-event equivalence of the compiled core and the Python engine, and speed-up.

Compares every trace field (ids, times, epochs, parents), every suppressed-pulse
field, the event metadata of every fired event and the M2 re-run count, for M0, M1
and M2, with and without ideal-cell interventions, on random vectors of every
benchmark.

    python scripts/check_native_equivalence.py <liberty> [n_vectors] [bench ...]
"""
import random
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model  # noqa: E402
from glitchscope.model import StimulusEpoch, ps_to_fs  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.verilog import read_design, read_verilog  # noqa: E402


def sig(res):
    tr = [(e.event_id, e.time_fs, e.epoch_id, e.net, e.old_value, e.new_value, e.source_instance,
           e.parent_event_ids) for e in res["trace"]]
    sup = [tuple(s.__dict__.values()) for s in res["suppressed"]]
    ids = {e.event_id for e in res["trace"]}
    meta = {k: tuple(v.__dict__.values()) for k, v in res["meta"].items() if k in ids}
    fin = {k: v for k, v in res["final"].items()}
    return tr, sup, meta, res.get("reruns", 0), fin


def compare(net, dp, model, nv, seed, ideal_frac=0.0, multi=False, rollback=True, **kw):
    rnd = random.Random(seed)
    cells = [c.name for c in net.cells]
    ideal = frozenset(rnd.sample(cells, int(len(cells) * ideal_frac))) if ideal_frac else frozenset()
    if model == "M2":
        kw["r_filter"] = M2Model()
    py = PulseSimulator(net, dp, model, rollback=rollback, engine="python", ideal_cells=ideal, **kw)
    nat = PulseSimulator(net, dp, model, rollback=rollback, engine="native", ideal_cells=ideal, **kw)
    prev = {p: 0 for p in net.primary_inputs}
    bad = 0
    tp = tn = 0.0
    for k in range(nv):
        cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
        if multi:   # two sub-steps: half the inputs early, the rest 150 ps later
            ks = sorted(cur)
            eps = [StimulusEpoch(100_000, {p: cur[p] for p in ks[::2]}, k + 1),
                   StimulusEpoch(250_000, {p: cur[p] for p in ks[1::2]}, k + 1)]
        else:
            eps = [StimulusEpoch(100_000, cur, k + 1)]
        for s_ in (py, nat):
            s_.network = replace(net, initial_inputs=dict(prev))
        t = time.perf_counter(); a = py.run(eps); tp += time.perf_counter() - t
        t = time.perf_counter(); b = nat.run(eps); tn += time.perf_counter() - t
        assert b.get("engine") == "native"
        if sig(a) != sig(b):
            bad += 1
            if bad == 1:
                sa, sb = sig(a), sig(b)
                for name, x, y in zip(("trace", "suppressed", "meta", "reruns", "final"), sa, sb):
                    if x != y:
                        print(f"   first mismatch in {name} (vector {k})")
        prev = cur
    return bad, tp, tn


def main():
    lib_path = sys.argv[1]
    nv = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    benches = sys.argv[3:] or ["c17", "rca8", "ks8", "cmp8", "mul4", "mac", "arraymul16"]
    dp = LibertyDelayProvider(parse_liberty_file(lib_path))
    total = 0
    for b in benches:
        try:
            net = read_verilog(ROOT / f"bench/netlists/{b}.v")
        except ValueError:          # sequential: simulate the combinational core
            net = read_design(ROOT / f"bench/netlists/{b}.v", dp.lib).network
        n = max(4, nv // 4) if b == "arraymul16" else nv
        for model, frac, multi, rb in (("M0", 0, False, True), ("M1", 0, False, True), ("M2", 0, False, True),
                                       ("M2", 0, False, False), ("M2", 0, True, True), ("M2", 0.2, False, True),
                                       ("M1", 0.2, True, True)):
            bad, tp, tn = compare(net, dp, model, n, seed=7, ideal_frac=frac, multi=multi, rollback=rb,
                                  default_input_slew_fs=ps_to_fs(40))
            total += bad
            tag = f"{model}{' ideal20%' if frac else ''}{' 2-step' if multi else ''}{' no-rollback' if not rb else ''}"
            print(f"{b:10s} {tag:18s} vectors={n:3d} mismatches={bad}  python {tp:7.2f}s  native {tn:6.3f}s"
                  f"  x{tp / max(tn, 1e-9):5.1f}", flush=True)
    print("ALL EQUIVALENT" if total == 0 else f"MISMATCHES: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
