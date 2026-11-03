"""Head-to-head with GLOW (Liu et al., ICCAD 2026; github.com/ETHZ-DYNAMO/GLOW-ICCAD26):
GLOW chooses the retiming, GlitchScope measures and verifies it in the same setting as
scripts/retiming_benchmarks.py, next to exact minimum-register retiming and GlitchScope's
own placement.

GLOW needs Gurobi (free academic licence), so the comparison runs in three steps:

  1. export   python scripts/glow_compare.py export <liberty> <name> [--factor F]
              -> data/glow/<name>@<F>/{<name>.dot, probs.json, run_glow.sh, map.json}
  2. GLOW     bash data/glow/<name>@<F>/run_glow.sh <path to GLOW checkout>
              (runs glow.py twice: GLOW's own switching estimate, and with GlitchScope's
              simulated toggle rates; writes glow_est.dot / glow_sim.dot and their logs)
  3. import   python scripts/glow_compare.py import <liberty> <name> [--factor F]
              -> data/glow/<name>@<F>/result.json and a printed comparison

<name> is a netlist in bench/external/netlists (bench/fetch_benchmarks.py) or bench/layout.

What GLOW is given: the same retiming graph GlitchScope uses (one node per cell, sources
and sinks with lag 0, register counts per edge), each cell's worst input-to-output delay
from GlitchScope's static timing at the actual loads (ns; one delay per cell, as in
GlitchScope's own MILP, which keeps GLOW's model free of node splitting — pass
--pin-delays for per-pin delays), Liberty input capacitances (fF), the flip-flop's input
capacitance and clock-to-Q, the target period, per-arc sensitivities and per-node toggle
rates from zero-delay simulation of random vectors (GLOW's translator computes
sensitivities from toggle counts in the same way).  GLOW's chosen lags are then written
as a netlist by GlitchScope, verified cycle by cycle and measured exactly like every other
placement (event simulation with M2 pulse filtering, flip-flop and clock-tree energy).
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402

NET = ROOT / "bench/external/netlists"
OUT = ROOT / "data/glow"


def netlist(name):
    for p in (NET / f"{name}.v", ROOT / f"bench/layout/{name}.v", Path(name)):
        if p.exists():
            return p
    raise FileNotFoundError(f"{name}: not in {NET} or bench/layout (run bench/fetch_benchmarks.py)")


def setting(lib, name, factor, cycles=40, sample=16):
    """GlitchFix in exactly the setting of scripts/retiming_benchmarks.py (same target, stimulus, sample)."""
    from glitchscope.milp_retime import model_arrival
    path = netlist(name)
    probe = GlitchFix(path, lib, random_vectors=cycles, period_ps=10000, sample=4, grid=4, log=lambda m: None)
    t_min = probe.min_period()
    if factor <= 0:
        t = model_arrival(probe.rg, probe._delays, [e[3] for e in probe.rg.edges], probe.c2q_ps,
                          probe.timing.in_delay)
        T = round(max(t[:probe.rg.C]) + probe.timing.setup + 1.0, 1)
    else:
        T = round(factor * t_min, 1)
    fx = GlitchFix(path, lib, random_vectors=cycles, period_ps=T, sample=sample, grid=4, log=lambda m: print(m, flush=True))
    return fx, T, t_min


def node_names(rg):
    names = []
    for i in range(rg.n):
        if i < rg.C:
            names.append(f"c{i}")
        elif rg.is_source(i):
            names.append(f"pi{i - rg.C}")
        else:
            names.append(f"po{i - rg.C - len(rg.sources)}")
    return names


def toggle_stats(fx, n_vec=400, seed=7):
    """Zero-delay simulation of random values at every retiming source: per-arc sensitivity
    P(output toggles | input pin toggles) and per-node toggle rate."""
    from glitchscope.functional import evaluate_stable
    rg, net = fx.rg, fx.design.network
    rnd = random.Random(seed)
    srcs = list(dict.fromkeys(list(fx.design.real_inputs) + [f.q for f in fx.design.flops]))
    fixed = dict(net.initial_inputs)                 # constants keep their value

    def vec():
        return {**fixed, **{s: rnd.randint(0, 1) for s in srcs}}
    prev = evaluate_stable(net, vec())
    tog_out = [0] * rg.C
    tog_in, both = {}, {}
    src_tog = {}
    for _ in range(n_vec):
        cur = evaluate_stable(net, vec())
        for s in srcs:
            src_tog[s] = src_tog.get(s, 0) + (cur[s] != prev[s])
        for i, c in enumerate(rg.cells):
            o = cur[c.output] != prev[c.output]
            tog_out[i] += o
            for pin, n in c.inputs.items():
                t = cur[n] != prev[n]
                tog_in[(i, pin)] = tog_in.get((i, pin), 0) + t
                both[(i, pin)] = both.get((i, pin), 0) + (t and o)
        prev = cur
    sens = {k: (both[k] / tog_in[k] if tog_in[k] else 0.0) for k in tog_in}
    rate = [t / n_vec for t in tog_out]
    pi_rate = {s: src_tog.get(s, 0) / n_vec for s in srcs}
    return sens, rate, pi_rate


def export(a):
    fx, T, t_min = setting(a.lib, a.name, a.factor)
    rg, lib = fx.rg, fx.lib
    d = OUT / f"{a.name}@{a.factor}"
    d.mkdir(parents=True, exist_ok=True)
    names = node_names(rg)
    cu = lib.capacitance_unit_ff
    _, SL, _ = fx.timing.analyze([e[3] for e in rg.edges])
    sens, rate, pi_rate = toggle_stats(fx)
    inc = {}
    for u, v, pin, w in rg.edges:
        inc.setdefault(v, []).append((u, pin, w))
    ff = lib.cells[fx.ffcell] if fx.ffcell else None
    cap_ff = ff.pin_capacitance.get(ff.seq["next_state"], 0.0) if ff else 2.0
    pin_index = {}
    lines = ["digraph G {"]
    for i in range(rg.n):
        if i < rg.C:
            c = rg.cells[i]
            lc = lib.cells[c.library_cell]
            pins = sorted(c.inputs)
            pin_index[i] = {p: k for k, p in enumerate(pins)}
            caps = {str(k): round(lc.pin_capacitance.get(p, 0.0), 5) for k, p in enumerate(pins)}
            dl = {}
            for u, pin, _ in inc.get(i, []):
                (ar, af), _ = fx.timing._arc_out(i, pin, (0.0, 0.0), SL[u])
                dl[pin] = max(ar, af) / 1000.0
            worst = max(dl.values()) if dl else 0.0
            delays = {str(k): {"0": round(dl.get(p, worst) if a.pin_delays else worst, 5)} for k, p in enumerate(pins)}
            sen = {str(k): {"0": round(sens.get((i, p), 0.0), 4)} for k, p in enumerate(pins)}
            info = {"INPUT_CAPs": caps, "DELAYs": delays, "SENSITIVITY": sen}
        elif rg.is_source(i):
            info = {"INPUT_CAPs": {}, "DELAYs": {}, "SENSITIVITY": {}}
        else:                                         # sink: output port (no load) or a fixed flip-flop input
            kind = rg.sinks[i - rg.C - len(rg.sources)][0]
            info = {"INPUT_CAPs": {"0": round(0.0 if kind == "po" else cap_ff, 5)}, "DELAYs": {}, "SENSITIVITY": {}}
        lines.append(f'    {names[i]} [comment="{json.dumps(info).replace(chr(34), chr(92) + chr(34))}"];')
    seen = {}
    for u, v, pin, w in rg.edges:
        ip = pin_index[v][pin] if v < rg.C else 0
        key = (u, v)
        if key in seen and seen[key] != w:
            print(f"warning: {names[u]}->{names[v]} on two pins with different registers ({seen[key]}, {w})")
        seen[key] = w
        lines.append(f'    {names[u]} -> {names[v]} [comment="{ip}-0-{w}"];')
    lines.append("}")
    dot = d / f"{a.name}.dot"
    dot.write_text("\n".join(lines) + "\n")
    probs = {"TOGGLE_RATE": {names[i]: {"0": round(rate[i], 4)} for i in range(rg.C)}}
    for j, s in enumerate(rg.sources):
        probs["TOGGLE_RATE"][names[rg.C + j]] = {"0": round(pi_rate.get(s, 0.5), 4)}
    (d / "probs.json").write_text(json.dumps(probs))
    # Energy calibration, so GLOW's objective charges what GlitchScope measures: GLOW
    # counts switch x capacitance; an energy E corresponds to E / (V^2 / 2) of capacitance.
    # Per arc: the cell's Liberty internal energy per output transition (mean of rise and
    # fall, 40 ps input slew, actual load); per flip-flop and cycle: the flip-flop's data
    # and clock energy including its share of the clock tree (seqpower, as in GlitchFix).
    from glitchscope.analyze import EnergyModel
    from glitchscope.liberty_power import internal_energy_pj
    em = EnergyModel(a.lib, fx.design.network)
    half_v2 = 0.5 * em.vdd ** 2
    arc = {}
    for i, c in enumerate(rg.cells):
        load = fx.loads0.get(c.output, 0.0)
        arc[names[i]] = {}
        for k, pin in enumerate(sorted(c.inputs)):
            tabs = em.power.get(c.library_cell, {}).get((c.library_output_pin, pin))
            e = 0.0
            if tabs:
                e = 0.5 * sum(internal_energy_pj(tabs, rise, 40000 / em._tu_fs, load / em._cu_ff) * em._eu_fj
                              for rise in (True, False))
            arc[names[i]][str(k)] = {"0": round(max(e, 0.0) / half_v2, 5)}
    (d / "internal_caps.json").write_text(json.dumps(arc))
    e_reg = fx.register_energy(fx.original())
    cap_ff_int = e_reg / half_v2
    # same timing constraint as GlitchScope's retiming models: arrival <= T - setup
    theta, c2q = (T - fx.timing.setup) / 1000.0, fx.c2q_ps / 1000.0
    pi_p = round(sum(pi_rate.values()) / max(1, len(pi_rate)), 3)
    res = a.resolution
    run = f"""#!/bin/bash
# GLOW on {a.name} (target {theta:.3f} ns = {'own period' if a.factor <= 0 else f'{a.factor} x T_min'}).
# Usage: bash run_glow.sh <GLOW checkout>   (needs gurobipy with a full licence)
set -euo pipefail
G=${{1:?path to GLOW-ICCAD26 checkout}}
D=$(cd "$(dirname "$0")" && pwd)
# Energy model: --internal_caps_file (cell internal energy per arc) and --cap_internal_FF
# (flip-flop + clock-tree energy per cycle, {e_reg:.1f} fJ) in GLOW's capacitance units (fF).
COMMON="--theta {theta:.4f} --cap_in_FF {cap_ff:.5f} --cap_internal_FF {cap_ff_int:.4f} --internal_caps_file $D/internal_caps.json --clk2q_time {c2q:.4f} --resolution {res} --probs_PIs {pi_p} --time_limit {a.time_limit}"
# 1) GLOW's own switching estimate (sensitivities)
python "$G/glow.py" --dot "$D/{a.name}.dot" $COMMON --output_dot "$D/glow_est.dot" --lp_file "$D/glow_est.lp" --time_log "$D/glow_est.time" | tee "$D/glow_est.log"
# 2) with GlitchScope's simulated toggle rates
python "$G/glow.py" --dot "$D/{a.name}.dot" $COMMON --probs_sim_file "$D/probs.json" --output_dot "$D/glow_sim.dot" --lp_file "$D/glow_sim.lp" --time_log "$D/glow_sim.time" | tee "$D/glow_sim.log"
rm -f "$D"/*.lp
"""
    (d / "run_glow.sh").write_text(run)
    (d / "map.json").write_text(json.dumps(dict(name=a.name, factor=a.factor, target_ps=T, period_min_ps=t_min,
                                                cells=rg.C, sources=len(rg.sources), sinks=len(rg.sinks),
                                                c2q_ps=fx.c2q_ps, cap_in_FF_fF=cap_ff, resolution_ns=res,
                                                pin_delays=a.pin_delays, e_reg_fJ=e_reg, cap_internal_FF_fF=cap_ff_int,
                                                names=names), indent=0))
    print(f"wrote {dot} ({rg.C} cells, {len(rg.edges)} edges), probs.json, run_glow.sh; target {theta:.3f} ns")


def read_lags(dot_path, names):
    """Lags from GLOW's output DOT (node label retiming="k"); split nodes (<n>_in*/_out*) map back."""
    import re
    idx = {n: i for i, n in enumerate(names)}
    r = [None] * len(names)
    for m in re.finditer(r'^\s*"?(\w+)"?\s*\[label=.*?retiming=\D{0,3}?(-?\d+)', Path(dot_path).read_text(), re.M):
        n, k = m.group(1), int(m.group(2))
        base = re.sub(r"_(in|out)\d+$", "", n)
        if base in idx:
            if r[idx[base]] is not None and r[idx[base]] != k:
                raise ValueError(f"{base}: split nodes with different lags")
            r[idx[base]] = k
    missing = [names[i] for i, x in enumerate(r) if x is None]
    if missing:
        raise ValueError(f"{len(missing)} nodes without a lag in {dot_path}, e.g. {missing[:5]}")
    return r


def do_import(a):
    d = OUT / f"{a.name}@{a.factor}"
    meta = json.loads((d / "map.json").read_text())
    fx, T, t_min = setting(a.lib, a.name, a.factor)
    if abs(T - meta["target_ps"]) > 0.5:
        print(f"warning: target {T} ps differs from the exported {meta['target_ps']} ps")
    rg = fx.rg
    base = fx.original()
    classic = fx.classic_min_area(T, time_limit=300.0)
    out = dict(name=a.name, factor=a.factor, target_ps=T, cells=rg.C, original=base.row(),
               min_register=classic.row() if classic is not None and classic.energy else None)
    for tag in ("est", "sim", "west", "wsim"):        # w*: warm-started from minimum-register lags
        p = d / f"glow_{tag}.dot"
        if not p.exists():
            continue
        r = read_lags(p, meta["names"])
        for i in range(rg.C, rg.n):                 # sources and sinks: lag 0 (GLOW fixes them too)
            if r[i] != 0:
                raise ValueError(f"GLOW moved boundary node {meta['names'][i]} (lag {r[i]})")
        r = [r[i] if i < rg.C else rg.lag_fixed.get(i, 0) for i in range(rg.n)]
        c = fx.candidate(r, f"GLOW ({tag})")
        if c.note:
            print(f"GLOW ({tag}): not measurable: {c.note}")
            out[f"glow_{tag}"] = dict(note=c.note, period_ps=c.period_ps, flops=c.n_flops)
            continue
        fx.measure(c)
        out[f"glow_{tag}"] = c.row()
        import os
        if os.environ.get("GS_SAVE_NETLISTS") and getattr(c, "text", None):
            sd = Path(os.environ["GS_SAVE_NETLISTS"]) / f"{a.name}@{a.factor}"
            sd.mkdir(parents=True, exist_ok=True)
            (sd / f"glow_{tag}.v").write_text(c.text)
        out[f"glow_{tag}"]["meets_target"] = c.period_ps <= T     # GlitchScope's own static timing
        t = d / f"glow_{tag}.time"
        if t.exists():
            out[f"glow_{tag}"]["solver_time"] = t.read_text().strip()[:200]
    ref = ROOT / "data/benchmarks/retiming.json"
    if ref.exists():
        R = json.loads(ref.read_text()).get(f"{a.name}@{a.factor}")
        if R:
            out["glitchscope_from_retiming_json"] = R.get("glitchscope")
    (d / "result.json").write_text(json.dumps(out, indent=1))
    print(f"\n{a.name} @ {'own clock' if a.factor <= 0 else f'{a.factor} x T_min'}: target {T:.0f} ps")
    print(f"{'placement':28s}{'total fJ':>11s}{'glitch fJ':>11s}{'flops':>7s}{'period ps':>11s}  verified")
    for k in ("original", "min_register", "glow_est", "glow_sim", "glitchscope_from_retiming_json"):
        r = out.get(k)
        if r and "total" in r:
            print(f"{k:28s}{r['total']:11.1f}{r.get('glitch', 0):11.1f}{r['flops']:7d}{r['period_ps']:11.0f}  {r.get('verified')}")
        elif r:
            print(f"{k:28s}  {r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("export", "import"))
    ap.add_argument("lib")
    ap.add_argument("name")
    ap.add_argument("--factor", type=float, default=0.0, help="0 = the design's own period (default); else F x T_min")
    ap.add_argument("--resolution", type=float, default=0.05, help="GLOW time step (ns)")
    ap.add_argument("--time-limit", type=float, default=3600)
    ap.add_argument("--pin-delays", action="store_true", help="per-pin delays (GLOW splits nodes; larger MILP)")
    a = ap.parse_args()
    (export if a.step == "export" else do_import)(a)


if __name__ == "__main__":
    main()
