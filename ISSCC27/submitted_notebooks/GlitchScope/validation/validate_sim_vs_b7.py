"""Re-run the closed B7 real-SKY130 sweep with the unified PulseSimulator.

Gate: M1 identical to B4 on all 30 cases; M0 identical to B3 on the 19 supported
cases; on the 11 B3 overtake cases M0 must report a NONPOSITIVE_WIDTH removal at U_X.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "validation/legacy_b7")]
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator, TransportTemporalOrderError
from glitchscope.inertial import InertialSimulator
from glitchscope.sim import PulseSimulator
from validate_real_sky130_b6 import build_net

lib = parse_liberty_file(sys.argv[1]); p = LibertyDelayProvider(lib)
B, X = "sky130_fd_sc_hd__buf_1", "sky130_fd_sc_hd__xor2_1"
xc = lib.cells[X]
ax = [a for a in xc.timing_arcs if a.related_pin == "A" and a.timing_sense == "positive_unate"][0]
bx = [a for a in xc.timing_arcs if a.related_pin == "B" and a.timing_sense == "negative_unate"][0]
common = sorted(set(map(float, ax.cell_rise.index_2)) & set(map(float, bx.cell_fall.index_2)))
loads = []
for raw in common:
    ff = raw * lib.capacitance_unit_ff
    if ff not in loads: loads.append(ff)
if len(loads) > 5:
    loads = [loads[i] for i in sorted(set([0, 1, len(loads)//2, len(loads)-2, len(loads)-1]))]
sig = lambda tr: [(e.time_fs, e.net, e.new_value, e.source_instance) for e in tr]
ep = [StimulusEpoch(ps_to_fs(100), {"S": 1}, 1)]
kw = dict(input_slew_fs_by_net={"S": ps_to_fs(10)})
n = m0_same = m0_over = m1_same = 0
for load in loads:
    for nchain in range(1, 7):
        net, _ = build_net(B, "X", X, "X", nchain); n += 1
        po = {"Y": load}
        got1 = PulseSimulator(net, p, "M1", primary_output_load_ff_by_net=po, **kw).run(ep)
        ref1, _ = InertialSimulator(net, p, auto_load_from_liberty=True, primary_output_load_ff_by_net=po, **kw).run(ep)
        m1_same += sig(ref1) == sig(got1["trace"])
        got0 = PulseSimulator(net, p, "M0", primary_output_load_ff_by_net=po, **kw).run(ep)
        try:
            ref0, _ = TransportSimulator(net, p, auto_load_from_liberty=True, primary_output_load_ff_by_net=po, **kw).run(ep)
            m0_same += sig(ref0) == sig(got0["trace"])
        except TransportTemporalOrderError:
            m0_over += any(s.instance == "U_X" and s.reason == "NONPOSITIVE_WIDTH" for s in got0["suppressed"])
print(f"cases={n} M1_identical={m1_same} M0_identical={m0_same} M0_overtake_removed={m0_over}")
ok = m1_same == n and m0_same + m0_over == n
print("SIM_VS_B7_PASS" if ok else "SIM_VS_B7_FAIL"); sys.exit(0 if ok else 1)
