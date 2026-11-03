"""Where does M2 over-count glitches?  Per-net, per-vector comparison against the cached
whole-circuit ngspice references of section 5.

For every gate output and input vector the M2 transition count is compared with SPICE's
50 % crossing count.  An over-count is "created" at a gate when every input of that gate
matches SPICE in that vector but the output does not, and "inherited" when an input
already over-counts.  Created over-counts are then characterised by what the gate saw in
the M2 trace: the gate type, the number of input events, the shortest spacing between two
input events on *different* pins (near-simultaneous switching) and whether the surplus
output pulse came from one input pin or from two.

    python scripts/overcount_diagnosis.py <liberty>        -> data/m2/overcount_diagnosis.json
"""
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.functional import evaluate_stable  # noqa: E402
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model  # noqa: E402
from glitchscope.model import StimulusEpoch, ps_to_fs  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.verilog import read_verilog  # noqa: E402

CASES = {"arraymul8": (ROOT / "bench/netlists/arraymul8.v", 20, "data/bench/spice_ref_arraymul8_20_7000ps.json"),
         "c432": (ROOT / "bench/external/netlists/c432.v", 30, "data/bench/spice_ref_c432_30_6000ps.json"),
         "c880": (ROOT / "bench/external/netlists/c880.v", 30, "data/bench/spice_ref_c880_30_6000ps.json"),
         "ks8": (ROOT / "bench/netlists/ks8.v", 40, "data/bench/spice_ref_ks8_40.json"),
         "rca8": (ROOT / "bench/netlists/rca8.v", 60, "data/bench/spice_ref_rca8_60.json")}


def depth_of(net):
    drv = {c.output: c for c in net.cells}
    memo = {}

    def d(n):
        if n not in drv:
            return 0
        if n not in memo:
            memo[n] = 1 + max((d(x) for x in drv[n].inputs.values()), default=0)
        return memo[n]
    return {c.output: d(c.output) for c in net.cells}


def run(lib, name):
    path, nv, refp = CASES[name]
    if not path.exists() or not (ROOT / refp).exists():
        return None
    net = read_verilog(path)
    ref = json.loads((ROOT / refp).read_text())
    rnd = random.Random(11)
    vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(nv)]
    dp = LibertyDelayProvider(parse_liberty_file(lib))
    sim = PulseSimulator(net, dp, "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40))
    drv = {c.output: c for c in net.cells}
    dep = depth_of(net)
    tpd = {}
    prev = dict(net.initial_inputs)
    rows = []                      # one per (vector, gate output)
    for k, vec in enumerate(vecs):
        sim.network = replace(net, initial_inputs=dict(prev))
        tr = sim.run([StimulusEpoch(100_000, dict(vec), k + 1)])["trace"]
        cnt = Counter(e.net for e in tr if e.source_instance != "$PI")
        ev_by_net = defaultdict(list)
        for e in tr:
            ev_by_net[e.net].append(e)
        b, a = evaluate_stable(net, prev), evaluate_stable(net, {**prev, **vec})
        sp = ref[k]["crossings"]
        for n, x in sp.items():
            c = drv.get(n)
            if c is None:
                continue
            m = cnt.get(n, 0)
            ins = list(c.inputs.values())
            in_err = any(cnt.get(i, 0) != sp.get(i, cnt.get(i, 0)) for i in ins if i in sp)
            # input events seen by this gate: spacing between events on different pins
            evs = sorted((e.time_fs, i) for i in ins for e in ev_by_net.get(i, []))
            gaps = [t2 - t1 for (t1, p1), (t2, p2) in zip(evs, evs[1:]) if p1 != p2]
            out_ev = ev_by_net.get(n, [])
            src = Counter()
            pin_of = {e.event_id: e.net for i in ins for e in ev_by_net.get(i, [])}
            for e in out_ev:
                for pid in e.parent_event_ids:
                    if pid in pin_of:
                        src[pin_of[pid]] += 1
            rows.append(dict(k=k, net=n, cell=c.library_cell.split("__")[-1], depth=dep[n], m2=m, spice=x,
                             req=int(b[n] != a[n]), inputs_match=not in_err, n_in_events=len(evs),
                             min_diff_pin_gap_ps=(min(gaps) / 1000 if gaps else None),
                             out_pins=len(src)))
        prev = {**prev, **vec}
    return rows


def summarise(rows):
    tot_over = sum(max(0, r["m2"] - r["spice"]) for r in rows)
    tot_under = sum(max(0, r["spice"] - r["m2"]) for r in rows)
    created = [r for r in rows if r["inputs_match"] and r["m2"] > r["spice"]]
    created_under = [r for r in rows if r["inputs_match"] and r["m2"] < r["spice"]]
    clean = [r for r in rows if r["inputs_match"]]
    s = dict(net_vectors=len(rows), m2_transitions=sum(r["m2"] for r in rows),
             spice_transitions=sum(r["spice"] for r in rows), over=tot_over, under=tot_under,
             created_over_events=len(created), created_over_transitions=sum(r["m2"] - r["spice"] for r in created),
             created_under_events=len(created_under),
             clean_gate_vectors=len(clean))
    # by cell: rate of created over-count among gate-vectors whose inputs match SPICE and that toggle at all
    by = defaultdict(lambda: [0, 0, 0])
    for r in clean:
        if r["m2"] == 0 and r["spice"] == 0:
            continue
        b = by[r["cell"]]
        b[0] += 1
        b[1] += r["m2"] > r["spice"]
        b[2] += r["m2"] < r["spice"]
    s["by_cell"] = {c: dict(active=v[0], over=v[1], under=v[2]) for c, v in sorted(by.items(), key=lambda x: -x[1][1])}
    # created over-counts: one input pin vs two, near-simultaneous input switching
    s["created_by_out_pins"] = dict(Counter(min(r["out_pins"], 3) for r in created))
    gaps = [r["min_diff_pin_gap_ps"] for r in created if r["min_diff_pin_gap_ps"] is not None]
    ok = [r["min_diff_pin_gap_ps"] for r in clean if r["m2"] == r["spice"] and r["m2"] > r["req"]
          and r["min_diff_pin_gap_ps"] is not None]
    s["created_min_gap_ps_median"] = float(np.median(gaps)) if gaps else None
    s["correct_glitchy_min_gap_ps_median"] = float(np.median(ok)) if ok else None
    s["created_gap_lt_20ps_share"] = float(np.mean(np.array(gaps) < 20)) if gaps else None
    s["correct_gap_lt_20ps_share"] = float(np.mean(np.array(ok) < 20)) if ok else None
    # excess by depth (all, created or inherited)
    dd = defaultdict(lambda: [0, 0])
    for r in rows:
        dd[r["depth"]][0] += r["m2"]
        dd[r["depth"]][1] += r["spice"]
    s["by_depth"] = {d: dict(m2=v[0], spice=v[1]) for d, v in sorted(dd.items())}
    # M2 count vs SPICE count on gate-vectors with matching inputs (does M2 over-count trains?)
    tr = defaultdict(lambda: [0, 0])
    for r in clean:
        if r["spice"] or r["m2"]:
            tr[min(r["spice"], 6)][0] += 1
            tr[min(r["spice"], 6)][1] += r["m2"] - r["spice"]
    s["clean_excess_by_spice_count"] = {k: dict(n=v[0], mean_excess=v[1] / v[0]) for k, v in sorted(tr.items())}
    return s


def main():
    lib = sys.argv[1]
    out = {}
    for name in (sys.argv[2:] or CASES):
        rows = run(lib, name)
        if rows is None:
            print(name, "skipped (netlist or SPICE reference missing)")
            continue
        s = summarise(rows)
        out[name] = s
        print(f"\n== {name}: M2 {s['m2_transitions']} vs SPICE {s['spice_transitions']} transitions; "
              f"over {s['over']}, under {s['under']}")
        print(f"  created at a gate with all inputs matching SPICE: {s['created_over_events']} gate-vectors, "
              f"{s['created_over_transitions']} transitions; created under-counts {s['created_under_events']}")
        print("  created by #input pins causing the output events:", s["created_by_out_pins"])
        print(f"  min spacing of different-pin input events: created {s['created_min_gap_ps_median']} ps "
              f"vs correct glitchy {s['correct_glitchy_min_gap_ps_median']} ps;  <20 ps share "
              f"{s['created_gap_lt_20ps_share']} vs {s['correct_gap_lt_20ps_share']}")
        print("  by cell (active / over / under):", {c: (v['active'], v['over'], v['under']) for c, v in list(s['by_cell'].items())[:8]})
        print("  clean gates, mean excess by SPICE count:", {k: (v['n'], round(v['mean_excess'], 2)) for k, v in s['clean_excess_by_spice_count'].items()})
        print("  by depth M2/SPICE:", {d: round(v['m2'] / max(1, v['spice']), 2) for d, v in s['by_depth'].items()})
    p = ROOT / "data/m2/overcount_diagnosis.json"
    p.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
