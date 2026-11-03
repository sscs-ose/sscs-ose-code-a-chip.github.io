"""Smoke timing of M0/M1/M2 on the small benchmarks:  python scripts/bench_smoke.py [<liberty>]"""
import sys, time, random
sys.path.insert(0, '.')
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import StimulusEpoch, ps_to_fs
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.test_support import lib_path_or_none
lib = parse_liberty_file(sys.argv[1] if len(sys.argv) > 1 else lib_path_or_none())   # <liberty> or GS_LIB / tools.env
dp = LibertyDelayProvider(lib); m2 = M2Model()
for t in ['c17','rca8','ks8','cmp8','mul4']:
    net = read_verilog(f'bench/netlists/{t}.v'); rnd = random.Random(1)
    eps = [StimulusEpoch(ps_to_fs(1000 + 3000*k), {pi: rnd.randint(0,1) for pi in net.primary_inputs}, k+1) for k in range(200)]
    for m in ['M0','M1','M2']:
        t0=time.time(); r = PulseSimulator(net, dp, m, r_filter=m2, default_input_slew_fs=ps_to_fs(40)).run(eps)
        ev = sum(1 for e in r['trace'] if e.source_instance != '$PI')
        print(f"{t:5s} {m} cell_events={ev:5d} suppressed={len(r['suppressed']):4d} reruns={r['reruns']} {time.time()-t0:.1f}s")
print('uncalibrated', m2.uncalibrated)
