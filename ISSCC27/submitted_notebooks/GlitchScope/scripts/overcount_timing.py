"""Timing view of the M2 over-count on the 8x8 NOR-array multiplier: ngspice with every net
saved for a few vectors, 50 % crossing *times* and pulse peaks per net, compared with the
M2 event times.

  1. timing drift: for nets with exactly one transition in both, t_M2 - t_SPICE vs depth;
  2. at gates where M2 creates a pulse that SPICE does not show although every input has
     the same number of transitions in both: the input skew seen by M2 and by SPICE, and
     the peak the SPICE output reaches.

    python scripts/overcount_timing.py <liberty> [n_vectors]   -> data/m2/overcount_timing.json
"""
import json
import random
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model  # noqa: E402
from glitchscope.model import StimulusEpoch, ps_to_fs  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.spice.netlist_sim import build_deck, _sp  # noqa: E402
from glitchscope.spice.pulse_sweep import _env, VDD, LIB_SLEW_FRAC  # noqa: E402
from glitchscope.verilog import read_verilog  # noqa: E402

PERIOD, SLEW, T_PI = 7000.0, 40.0, 100.0


def main():
    lib, nv = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4
    net = read_verilog(ROOT / "bench/netlists/arraymul8.v")
    rnd = random.Random(11)
    vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(20)][:nv]
    init = dict(net.initial_inputs)
    with tempfile.TemporaryDirectory(prefix="gs_ot_") as td:
        td = Path(td)
        deck, nets = build_deck(net, vecs, init, PERIOD, SLEW, td / "wave.txt", step_ps=1.0)
        (td / "deck.sp").write_text(deck)
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        r = subprocess.run([_env("GS_NGSPICE"), "-b", "deck.sp"], cwd=td, capture_output=True, text=True)
        if not (td / "wave.txt").exists():
            raise RuntimeError(r.stdout[-1500:] + r.stderr[-1500:])
        d = np.loadtxt(td / "wave.txt", skiprows=1)
    t = d[:, 0] * 1e12
    tr = SLEW / LIB_SLEW_FRAC
    sp_x, sp_peak = {}, {}
    for k in range(nv):
        t0 = (k + 1) * PERIOD + tr / 2                  # 50 % point of the input ramps
        m = (t >= (k + 1) * PERIOD) & (t < (k + 2) * PERIOD)
        tt = t[m] - t0
        for j, n in enumerate(nets):
            v = d[m, 2 + j]
            s = np.sign(v - VDD / 2)
            idx = np.nonzero(np.diff(s) != 0)[0]
            xs = [float(tt[i] + (VDD / 2 - v[i]) / (v[i + 1] - v[i]) * (tt[i + 1] - tt[i])) for i in idx]
            sp_x[(k, n)] = xs
            v0 = v[0]
            sp_peak[(k, n)] = float(np.max(np.abs(v - v0)) / VDD)    # largest excursion from the start value
    dp = LibertyDelayProvider(parse_liberty_file(lib))
    sim = PulseSimulator(net, dp, "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(SLEW))
    drv = {c.output: c for c in net.cells}
    dep = {}

    def depth(n):
        if n not in drv:
            return 0
        if n not in dep:
            dep[n] = 1 + max(depth(x) for x in drv[n].inputs.values())
        return dep[n]
    m2_x = {}
    prev = dict(init)
    for k, vec in enumerate(vecs):
        sim.network = replace(net, initial_inputs=dict(prev))
        trc = sim.run([StimulusEpoch(int(T_PI * 1000), dict(vec), k + 1)])["trace"]
        by = defaultdict(list)
        for e in trc:
            by[e.net].append(e.time_fs / 1000 - T_PI)
        for n in nets:
            m2_x[(k, n)] = sorted(by.get(n, []))
        for pi in net.primary_inputs:
            m2_x[(k, pi)] = sorted(by.get(pi, []))
        prev = {**prev, **vec}
    # 1. drift
    drift = defaultdict(list)
    for (k, n), xs in sp_x.items():
        ms = m2_x.get((k, n), [])
        if len(xs) == 1 and len(ms) == 1:
            drift[depth(n)].append(ms[0] - xs[0])
    drift_s = {dd: dict(n=len(v), median_ps=float(np.median(v)), p10=float(np.percentile(v, 10)),
                        p90=float(np.percentile(v, 90))) for dd, v in sorted(drift.items())}
    print("timing error t_M2 - t_SPICE (ps) of single transitions, by depth (n, median, p10, p90):")
    for dd, s in drift_s.items():
        if dd % 4 == 0 or dd < 4:
            print(f"  depth {dd:2d}: n={s['n']:4d}  {s['median_ps']:7.1f}  [{s['p10']:7.1f}, {s['p90']:7.1f}]")
    # 2. created pulses
    created = []
    for (k, n), xs in sp_x.items():
        c = drv[n]
        ms = m2_x.get((k, n), [])
        if len(ms) <= len(xs):
            continue
        ins = list(c.inputs.values())
        if any(len(m2_x.get((k, i), [])) != len(sp_x.get((k, i), m2_x.get((k, i), []))) for i in ins):
            continue
        if len(ins) != 2 or any(len(m2_x.get((k, i), [])) != 1 for i in ins):
            continue
        a, b = ins
        created.append(dict(k=k, net=n, cell=c.library_cell.split("__")[-1], depth=depth(n),
                            skew_m2=m2_x[(k, b)][0] - m2_x[(k, a)][0],
                            skew_spice=sp_x[(k, b)][0] - sp_x[(k, a)][0],
                            m2_out=len(ms), spice_out=len(xs), spice_peak=sp_peak[(k, n)]))
    if created:
        sm = np.array([abs(r["skew_m2"]) for r in created])
        ss = np.array([abs(r["skew_spice"]) for r in created])
        pk = np.array([r["spice_peak"] for r in created if r["spice_out"] == 0])
        print(f"\ncreated pulses at 2-input gates with one transition per input: {len(created)}")
        print(f"  |input skew| M2 median {np.median(sm):.0f} ps, SPICE median {np.median(ss):.0f} ps; "
              f"SPICE skew smaller in {np.mean(ss < sm) * 100:.0f} % (median ratio {np.median(ss / np.maximum(sm, 1)):.2f})")
        if len(pk):
            print(f"  SPICE output peak where SPICE shows no crossing: median {np.median(pk):.2f} VDD, "
                  f">0.3 VDD in {np.mean(pk > 0.3) * 100:.0f} %")
    out = dict(vectors=nv, drift_by_depth=drift_s, created=created)
    (ROOT / "data/m2/overcount_timing.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
