"""Event-for-event equivalence of the M2 rollback (checkpoint/resume) simulator and the
reference restart-from-zero simulator, on random vectors of every benchmark.

    python scripts/check_rollback_equivalence.py <liberty> [n_vectors] [bench ...]
"""
import sys, random, time
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs, StimulusEpoch
from glitchscope.m2model import M2Model

LIB = sys.argv[1]
NV = int(sys.argv[2]) if len(sys.argv) > 2 else 60
BENCHES = sys.argv[3:] or ["c17", "rca8", "ks8", "cmp8", "mul4", "mac"]
from glitchscope.sim import PulseSimulator
dp = LibertyDelayProvider(parse_liberty_file(LIB))


def sig(res):
    return ([(e.event_id, e.time_fs, e.net, e.old_value, e.new_value, e.source_instance) for e in res["trace"]],
            [(s.instance, s.cause_fs, s.cancel_fs, s.reason) for s in res["suppressed"]])


bad_total = 0
for b in BENCHES:
    net = read_verilog(ROOT / f"bench/netlists/{b}.v")
    rnd = random.Random(11)
    kw = dict(r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40))
    fast = PulseSimulator(net, dp, "M2", rollback=True, checkpoint_every=4, **kw)
    ref = PulseSimulator(net, dp, "M2", rollback=False, **kw)
    prev = {p: 0 for p in net.primary_inputs}
    bad = rr = rf = 0; tf = tr = 0.0
    for k in range(NV):
        cur = {p: rnd.randint(0, 1) for p in net.primary_inputs}
        eps = [StimulusEpoch(100_000, cur, 1)]
        for s_ in (fast, ref):
            s_.network = replace(net, initial_inputs=dict(prev))
        t = time.time(); a = fast.run(eps); tf += time.time() - t
        t = time.time(); r = ref.run(eps); tr += time.time() - t
        bad += sig(a) != sig(r); rf += a["reruns"]; rr += r["reruns"]
        prev = cur
    bad_total += bad
    print(f"{b:10s} vectors={NV} mismatches={bad} reruns fast/ref={rf}/{rr} time fast/ref={tf:.1f}/{tr:.1f}s")
print("ALL EQUIVALENT" if bad_total == 0 else f"MISMATCHES: {bad_total}")
sys.exit(1 if bad_total else 0)
