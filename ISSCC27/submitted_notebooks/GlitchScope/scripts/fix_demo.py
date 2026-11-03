"""Actionable-fix demo: path-balance the top glitch CAUSE vs the top glitch CONSUMER.

For a target cell, GlitchScope's lineage tells us which input pin starts its
glitches (leading edge) and the median skew to the pin that ends them.  The fix
inserts a chain of buf_1 on that input (for this cell only) to cancel the skew.
We then re-run the whole analysis (same vectors) and report the change in
glitch, functional and total energy (buffers' own energy included) and in
worst-case settle time.
"""
import sys, random, json, statistics
from dataclasses import replace
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.verilog import read_verilog
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs, Cell, StimulusEpoch
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.classify import extract_pulses
from glitchscope.functional import evaluate_stable

LIB = sys.argv[1]; BENCH = sys.argv[2]; NV = int(sys.argv[3]) if len(sys.argv) > 3 else 300
lib = parse_liberty_file(LIB); dp = LibertyDelayProvider(lib); m2 = M2Model()
BUF = "sky130_fd_sc_hd__buf_1"


def evaluate(net, vecs):
    sim = PulseSimulator(net, dp, "M2", r_filter=m2, default_input_slew_fs=ps_to_fs(40))
    a = analyze(sim, EnergyModel(LIB, net, spice_scale=True), vecs)
    # worst settle time over all vectors (last event after the input change)
    prev, worst = dict(net.initial_inputs), 0
    for k, v in enumerate(vecs, 1):
        sim.network = replace(net, initial_inputs=dict(prev))
        tr = sim.run([StimulusEpoch(100_000, dict(v), k)])["trace"]
        if tr:
            worst = max(worst, tr[-1].time_fs - 100_000)
        prev = {**prev, **v}
    return a, worst / 1000


def skew_profile(net, vecs, target):
    """(lead pin, median skew ps) of glitches GENERATED at `target`."""
    sim = PulseSimulator(net, dp, "M2", r_filter=m2, default_input_slew_fs=ps_to_fs(40))
    prev = dict(net.initial_inputs); skews = defaultdict(list)
    for k, v in enumerate(vecs, 1):
        cur = {**prev, **v}
        sim.network = replace(net, initial_inputs=dict(prev))
        r = sim.run([StimulusEpoch(100_000, dict(v), k)])
        ev = {e.event_id: e for e in r["trace"]}
        for p in extract_pulses(r["trace"], {k: evaluate_stable(net, prev)}, {k: evaluate_stable(net, cur)}):
            a, b = ev[p.start_event_id], ev[p.end_event_id]
            if a.source_instance != target:
                continue
            ma, mb = r["meta"][a.event_id], r["meta"][b.event_id]
            if ma.related_pin != mb.related_pin:
                skews[ma.related_pin].append((mb.cause_fs - ma.cause_fs) / 1000)
        for s in r["suppressed"]:
            pass
        prev = cur
    if not skews:
        return None, 0.0
    pin = max(skews, key=lambda p: len(skews[p]))
    return pin, statistics.median(skews[pin])


def insert_buffers(net, target, pin, n):
    cells, tgt = [], None
    for c in net.cells:
        if c.name == target:
            tgt = c
        else:
            cells.append(c)
    src = tgt.inputs[pin]
    for i in range(n):
        out = f"{target}_bal{i}"
        cells.append(Cell(f"{target}_BAL{i}", "BUF", {"A": src}, out, 1000, 1000, library_cell=BUF, library_output_pin="X"))
        src = out
    cells.append(replace(tgt, inputs={**tgt.inputs, pin: src}))
    return replace(net, cells=cells)


net = read_verilog(ROOT / f"bench/netlists/{BENCH}.v")
rnd = random.Random(7); vecs = [{pi: rnd.randint(0, 1) for pi in net.primary_inputs} for _ in range(NV)]
base, base_t = evaluate(net, vecs)
cause = next(iter(base["gci"]))
consumer = max(base["local"], key=base["local"].get)
# typical buffer delay at a single-fanout load
d_buf = 50.0
T0 = base["totals"]
print(f"{BENCH}: baseline glitch {T0['E_glitch_fJ'] / NV:.1f} fJ/vec, total {T0['E_total_fJ'] / NV:.1f} fJ/vec, settle {base_t:.0f} ps")
out = {"bench": BENCH, "baseline": dict(glitch=T0["E_glitch_fJ"] / NV, total=T0["E_total_fJ"] / NV, settle_ps=base_t)}
for label, target in (("top CAUSE (GlitchScope)", cause), ("top CONSUMER (toggle counting)", consumer)):
    pin, skew = skew_profile(net, vecs, target)
    if pin is None:
        print(f"  {label} {target}: generates no glitches itself -> balancing its inputs cannot help (no fix possible)")
        out[label] = dict(target=target, fix="none: cell only consumes propagated glitches")
        continue
    n = max(1, min(4, round(skew / d_buf)))
    fixed = insert_buffers(net, target, pin, n)
    a, t = evaluate(fixed, vecs)
    T = a["totals"]
    dg = 100 * (T["E_glitch_fJ"] - T0["E_glitch_fJ"]) / T0["E_glitch_fJ"]
    dt = 100 * (T["E_total_fJ"] - T0["E_total_fJ"]) / T0["E_total_fJ"]
    print(f"  {label} {target}: +{n} buf on pin {pin} (median skew {skew:.0f} ps) -> glitch {dg:+.1f} %, "
          f"total {dt:+.1f} %, settle {t:.0f} ps")
    out[label] = dict(target=target, pin=pin, skew_ps=skew, n_buf=n, d_glitch_pct=dg, d_total_pct=dt, settle_ps=t)
(ROOT / f"data/bench/fix_demo_{BENCH}.json").write_text(json.dumps(out, indent=1))

# ---- ideal source suppression: every pulse at the target cell is filtered at birth
def ideal(net, vecs, target):
    rf = lambda c, pol, s, d: 50.0 if c.name == target else m2(c, pol, s, d)
    sim = PulseSimulator(net, dp, "M2", r_filter=rf, default_input_slew_fs=ps_to_fs(40))
    return analyze(sim, EnergyModel(LIB, net, spice_scale=True), vecs)["totals"]["E_glitch_fJ"]

print("  ideal suppression at one cell (upper bound of any local fix):")
ranked_c = list(base["gci"])[:5]
ranked_l = sorted(base["local"], key=base["local"].get, reverse=True)[:5]
res_i = {}
for label, cells in (("cause-ranked", ranked_c), ("consumer-ranked", ranked_l)):
    for c in cells[:3]:
        if c in res_i:
            continue
        g = ideal(net, vecs, c)
        res_i[c] = 100 * (T0["E_glitch_fJ"] - g) / T0["E_glitch_fJ"]
    print(f"    {label:16s}: " + ", ".join(f"{c} saves {res_i[c]:.1f}% (GCI {100 * base['gci'].get(c, 0):.1f}%)" for c in cells[:3]))
out["ideal"] = {"saving_pct": res_i, "cause_ranked": ranked_c[:3], "consumer_ranked": ranked_l[:3],
                "gci_pct": {c: 100 * base["gci"].get(c, 0) for c in res_i}}
(ROOT / f"data/bench/fix_demo_{BENCH}.json").write_text(json.dumps(out, indent=1))
