"""One-call glitch analysis of a user design.

    glitchscope --netlist design.v --vcd tb.vcd --lib tt.lib [--out dir]
    glitchscope --netlist comb.v --random-vectors 200 --lib tt.lib      (combinational, no testbench)

Inputs: Yosys-mapped SKY130 HD netlist (combinational or with dfxtp flops),
a testbench VCD containing the clock and primary inputs (RTL or gate-level,
zero-delay is fine) -- or, for combinational designs, random input vectors --
and the Liberty file.  Output: report.html (interactive), report.txt,
summary.json, per-cell / per-input / per-edit CSVs, glitch VCD and SAIF.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .liberty import parse_liberty_file, LibertyDelayProvider
from .verilog import read_design
from .seq import read_vcd, read_clk_to_q, build_cycles
from .sim import PulseSimulator
from .m2model import M2Model
from .analyze import EnergyModel, analyze
from .functional import evaluate_stable
from .model import ps_to_fs
from .export import ActivityRecorder
from .attribution import InterventionalAttribution, toggle_attribution, make_groups
from .whatif import WhatIf, recommend


def parse_groups(spec, net):
    """'hier' | 'level' | 'level:<bands>' | 'regex:<pattern with one capture group>'."""
    if not spec:
        return None, None
    if spec == "hier":
        return make_groups(net, "hier"), "Groups by hierarchical instance name"
    if spec.startswith("level"):
        bands = int(spec.split(":", 1)[1]) if ":" in spec else 12
        return make_groups(net, "level", bands=bands), f"Groups by logic depth ({bands} bands)"
    if spec.startswith("regex:"):
        pat = spec.split(":", 1)[1]
        return make_groups(net, "regex", pattern=pat), f"Groups by instance-name pattern {pat}"
    raise ValueError(f"unknown --groups spec {spec!r}")


def run_design(netlist, vcd, lib_path, model="M2", clock=None, input_slew_ps=40.0,
               clk_slew_ps=40.0, input_delay_ps=None, spice_scale=True, check_outputs=True,
               lib=None, attribution=True, top_k=6, perms=12, workers=1, groups=None,
               fixes=3, random_vectors=None, period_ps=2000.0, seed=1, max_screen=None, spef=None,
               sample=None, sample_seed=1):
    """Run the full analysis.  ``vcd=None`` with ``random_vectors=N`` drives a
    combinational design with N uniformly random input vectors (``seed``)."""
    lib = lib or parse_liberty_file(lib_path)
    design = read_design(netlist, lib)
    net = design.network
    dp = LibertyDelayProvider(lib)
    flop_d_cap = {}
    for f in design.flops:
        cap = lib.cells[f.libcell].pin_capacitance.get(f.d_pin, 0.0)
        flop_d_cap[f.d] = flop_d_cap.get(f.d, 0.0) + cap
    from .m2model import calibration_for
    cal = calibration_for(lib.name)
    m2 = M2Model(cal)
    wire = None
    if spef:
        from .spef import read_spef_caps
        wire = read_spef_caps(spef)
    sim = PulseSimulator(net, dp, model, r_filter=m2, default_input_slew_fs=ps_to_fs(input_slew_ps),
                         primary_output_load_ff_by_net=flop_d_cap, wire_cap_ff_by_net=wire)
    if vcd is None and design.flops:
        if not random_vectors:
            raise ValueError("provide --vcd or --random-vectors N")
        from .seq import random_waves
        waves, clock = random_waves(design, int(random_vectors), period_ps, seed=seed, clock=clock)
        c2q = read_clk_to_q(lib_path, {f.libcell for f in design.flops})
        init, cycles, edges = build_cycles(design, waves, lib, c2q, sim.loads, clock=clock,
                                           clk_slew_ps=clk_slew_ps,
                                           input_delay_ps=100.0 if input_delay_ps is None else input_delay_ps)
        check_outputs = False
    elif vcd is None:
        if not random_vectors:
            raise ValueError("provide --vcd or --random-vectors N")
        import random as _r
        rnd = _r.Random(seed)
        init = {p: 0 for p in net.primary_inputs}
        cycles = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(int(random_vectors))]
        period_fs = int(round(period_ps * 1000))
        edges = [k * period_fs for k in range(len(cycles) + 1)]
        waves = {}
        check_outputs = False
    else:
        waves, _ = read_vcd(vcd)
        c2q = read_clk_to_q(lib_path, {f.libcell for f in design.flops})
        init, cycles, edges = build_cycles(design, waves, lib, c2q, sim.loads, clock=clock,
                                           clk_slew_ps=clk_slew_ps, input_delay_ps=input_delay_ps)
    # cross-check: functional flop/output state vs testbench outputs after every edge
    mismatches = checked = 0
    if check_outputs:
        state = dict(init)
        for k, cyc in enumerate(cycles):
            for _, upd in cyc:
                state.update(upd)
            settled = evaluate_stable(net, state)
            t_check = edges[k + 1] - 1 if k + 1 < len(edges) else None
            if t_check is None:
                continue
            for o in design.real_outputs:
                if o in waves:
                    v = 0
                    for tt, vv in waves[o]:
                        if tt > t_check:
                            break
                        v = vv
                    checked += 1
                    mismatches += settled[o] != v
    em = EnergyModel(lib_path, net, m2_json=cal, spice_scale=spice_scale)
    rec = ActivityRecorder(net, edges[1] - edges[0], initial=init)
    total_cycles = len(cycles)
    prevs = None
    if sample and sample < len(cycles):
        from .sampling import stratified_sample, estimate
        idx, all_prevs, members, smp = stratified_sample(cycles, init, sample, seed=sample_seed)
        cycles = [cycles[k] for k in idx]
        prevs = [all_prevs[k] for k in idx]
    res = analyze(sim, em, cycles, initial=init, on_trace=rec, prevs=prevs)
    if prevs is not None:
        per = {k: (v["E_glitch"], v["E_fun"]) for k, v in zip(idx, res["per_vector"])}
        res["sampling"] = dict(estimate=estimate(per, members, smp, total_cycles), sampled=len(idx),
                               total=total_cycles, seed=sample_seed)
    res["_recorder"], res["_init_values"], res["_flops"] = rec, evaluate_stable(net, init), design.flops
    res["_libcell"] = {c.name: c.library_cell for c in net.cells}
    kw = dict(default_input_slew_fs=ps_to_fs(input_slew_ps), primary_output_load_ff_by_net=flop_d_cap,
              wire_cap_ff_by_net=wire)
    if attribution:
        ia = InterventionalAttribution(net, dp, m2, em, cycles, initial=init, sim_kwargs=kw, workers=workers,
                                       prevs=prevs)
        res["attribution"] = ia.run(top_k=top_k, perms=perms, max_screen=max_screen)
        gs, label = parse_groups(groups, net)
        if gs:
            gr = ia.run(top_k=min(top_k, len(gs)), perms=perms, groups=gs)
            gr["label"] = label
            res["group_attribution"] = gr
        if len(cycles) >= 3 * len(net.primary_inputs):
            res["data_attribution"] = toggle_attribution(net, cycles, init, ia.eg, prevs=prevs)
        else:   # regression on fewer samples than ~3x inputs would be noise
            res["data_attribution_skipped"] = (f"needs >= {3 * len(net.primary_inputs)} cycles/vectors "
                                               f"for {len(net.primary_inputs)} inputs; got {len(cycles)}")
        if fixes:
            order = [c for c, _ in res["attribution"]["greedy"]] + res["attribution"]["top"]
            targets = list(dict.fromkeys(order))[:fixes]
            wi = WhatIf(net, lib, lib_path, dp, m2, cycles, initial=init, sim_kwargs=kw, prevs=prevs,
                        spice_scale=spice_scale, workers=workers, m2_json=cal)
            rows, best, comb = wi.suggest(targets)
            res["whatif"] = dict(cells=targets, rows=rows, best=best, combined=comb, recommended=recommend(best, comb))
    import re as _re
    _m = _re.search(r"\bmodule\s+\\?([A-Za-z_][\w$]*)", Path(netlist).read_text(errors="replace"))
    res["design"] = dict(top=_m.group(1) if _m else Path(netlist).stem, cells=len(net.cells), flops=len(design.flops), cycles=len(cycles), total_cycles=total_cycles,
                         parasitics=(f"SPEF {Path(spef).name}: {len(wire)} nets, "
                                     f"{sum(wire.get(n, 0.0) for n in sim.loads):.0f} fF wire capacitance on logic nets")
                         if spef else "none (pin capacitance only)",
                         stimulus="testbench VCD" if vcd else f"{len(cycles)} random {'cycles' if design.flops else 'vectors'} (seed {seed})",
                         clock_period_ps=(edges[1] - edges[0]) / 1000, model=model,
                         output_check=dict(checked=checked, mismatches=mismatches),
                         library=lib.name, vdd=em.vdd,
                         calibration=str(Path(cal).relative_to(Path(cal).parents[2])) if cal else
                         "none: pulse filtering falls back to M1 (inertial) for every cell",
                         uncalibrated_cells=dict(m2.uncalibrated),
                         proxy_calibrated_cells=dict(m2.proxied))
    return res


def write_report(res, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    T, D = res["totals"], res["design"]
    summary = {"design": D, "totals": T, "counts": res["counts"]}
    if "sampling" in res:
        summary["sampling"] = res["sampling"]
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    A = res.get("attribution", {})
    gsp = A.get("single", {}); shap = A.get("shapley", {})
    cells = sorted(set(res["local"]) | set(res["causal"]) | set(gsp),
                   key=lambda c: (-gsp.get(c, 0), -res["local"].get(c, 0)))
    with open(out / "glitch_cells.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "suppression_potential_frac", "shapley_frac_topK", "consumed_glitch_fJ",
                    "structural_baseline_frac"])
        for c in cells:
            w.writerow([c, round(gsp.get(c, 0), 5), round(shap.get(c, 0), 5) if c in shap else "",
                        round(res["local"].get(c, 0), 4), round(res["gci"].get(c, 0), 5)])
    if "data_attribution" in res:
        with open(out / "glitch_inputs.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["input_or_state_bit", "glitch_fJ_per_toggle", "toggle_rate", "share_of_glitch_energy"])
            for n, d in res["data_attribution"].items():
                w.writerow([n, round(d["fJ_per_toggle"], 3), round(d["toggle_rate"], 4), round(d["share"], 4)])
        summary["data_attribution_top"] = dict(list(res["data_attribution"].items())[:10])
    if A:
        summary["attribution"] = {k: A[k] for k in ("top", "shapley", "joint_top", "sum_single_top", "greedy", "evaluations")}
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
    n = max(1, D["cycles"])
    lines = [
        f"GlitchScope report  ({D['model']}, {D['cells']} cells, {D['flops']} flops, {D['cycles']} "
        f"{'cycles' if D['flops'] or D['output_check']['checked'] else 'vectors'} @ {D['clock_period_ps']:.0f} ps)",
        (f"  output check vs testbench: {D['output_check']['checked'] - D['output_check']['mismatches']}/{D['output_check']['checked']} match"
         if D["output_check"]["checked"] else f"  stimulus: {D.get('stimulus', 'testbench VCD')} (no output check)"),
        f"  functional energy : {T['E_functional_fJ'] / n:8.1f} fJ/cycle",
        f"  glitch energy     : {T['E_glitch_fJ'] / n:8.1f} fJ/cycle  ({100 * T['glitch_fraction']:.1f} % of dynamic)",
    ]
    if "sampling" in res:
        E = res["sampling"]["estimate"]
        g, f_, r_ = E["E_glitch_fJ_per_cycle"], E["E_functional_fJ_per_cycle"], E["glitch_fraction"]
        lines += [f"  SAMPLED {res['sampling']['sampled']} of {res['sampling']['total']} cycles (stratified); "
                  f"estimates for the whole run, 95 % CI:",
                  f"      glitch {g[0]:.1f} fJ/cycle [{g[1]:.1f}, {g[2]:.1f}], functional {f_[0]:.1f} [{f_[1]:.1f}, {f_[2]:.1f}], "
                  f"glitch share {100 * r_[0]:.1f} % [{100 * r_[1]:.1f}, {100 * r_[2]:.1f}]"]
    lines += [
        f"  glitches          : generated {res['counts'].get('GENERATED', 0)}, propagated {res['counts'].get('PROPAGATED', 0)}, "
        f"merged {res['counts'].get('MERGED', 0)}, filtered {res['counts'].get('FILTERED', 0)}",
        "  top glitch CONSUMERS (where energy is burnt): " + ", ".join(
            f"{c} {100 * v / max(1e-12, T['E_glitch_fJ']):.1f}%" for c, v in sorted(res['local'].items(), key=lambda x: -x[1])[:5]),
    ]
    if A:
        top = A["top"]
        lines += [
            "  WHERE TO FIX (interventional suppression potential, % of glitch energy removed if the gate were glitch-free):",
            "      " + ", ".join(f"{c} {100 * A['single'][c]:.1f}%" for c in top),
            f"    fixing these {len(top)} together removes {100 * A['joint_top']:.1f}% "
            f"(naive sum of singles would claim {100 * A['sum_single_top']:.1f}%)",
            "    Shapley share of that joint saving: " + ", ".join(f"{c} {100 * A['shapley'][c]:.1f}%" for c in top),
            "    best joint fix set (greedy): " + " -> ".join(f"{c} ({100 * g:.1f}%)" for c, g in A["greedy"]),
        ]
    if "data_attribution_skipped" in res:
        lines.append("  input/state-bit attribution skipped: " + res["data_attribution_skipped"])
    if "data_attribution" in res:
        lines.append("  glitch energy by input/state toggles (fJ per toggle): " + ", ".join(
            f"{n} {d['fJ_per_toggle']:.1f}" for n, d in list(res["data_attribution"].items())[:6]))
    (out / "report.txt").write_text("\n".join(lines) + "\n")
    W = res.get("whatif")
    if W:
        with open(out / "fix_suggestions.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["for_cell", "edit", "kind", "dE_total_pct", "dE_glitch_pct", "dE_total_fJ",
                        "settle_before_ps", "settle_after_ps", "steps_resimulated", "qualifies"])
            for r in sorted(W["rows"], key=lambda r: r["dE_total_fJ"]):
                w.writerow([r["cell"], r["edit"], r["kind"], round(r["dE_total_pct"], 3), round(r["dE_glitch_pct"], 3),
                            round(r["dE_total_fJ"], 3), round(r["settle_before_ps"], 1), round(r["settle_after_ps"], 1),
                            r["steps_resimulated"], r.get("qualifies", False)])
        c = W.get("recommended")
        lines.append("  HOW TO FIX (function-preserving edits, exact re-simulation): " + (
            f"{c['edit']}  ->  total {c['dE_total_pct']:+.2f} %, glitch {c['dE_glitch_pct']:+.2f} %, "
            f"settle {c['settle_before_ps']:.0f}->{c['settle_after_ps']:.0f} ps" if c else
            "no evaluated resize / pin swap lowers total energy without slowing the design"))
    GA = res.get("group_attribution")
    if GA:
        lines.append(f"  GROUPS ({GA['label']}): " + ", ".join(f"{g} {100 * GA['single'][g]:.1f}%" for g in GA["top"]) +
                     f"; together {100 * GA['joint_top']:.1f}%")
    O = res.get("optimize")
    if O:
        g, o = O.get("glitch_aware"), O["original"]
        if g and g.get("total") and g["total"] < o["total"] - 1e-9:
            lines.append(f"  REDUCE IT (register placement, verified on every cycle, latency +{O['latency']}): "
                         f"total {o['total']:.1f} -> {g['total']:.1f} fJ/cycle "
                         f"({100 * (g['total'] / o['total'] - 1):+.1f} %), glitch {o['glitch']:.1f} -> {g['glitch']:.1f}, "
                         f"{o['flops']} -> {g['flops']} flops; wrote {out}/optimized.v")
            td = O.get("timing_driven")
            if td and td.get("total"):
                lines.append(f"    min-period retiming for comparison: {td['total']:.1f} fJ/cycle, {td['flops']} flops")
        else:
            lines.append("  REDUCE IT: no register placement lowers total energy here (extra registers cost more "
                         "than the glitches they remove); the design is left as it is")
    files = ["report.html", "report.txt", "summary.json", "glitch_cells.csv"]
    files += ["glitch_inputs.csv"] if "data_attribution" in res else []
    files += ["fix_suggestions.csv"] if W else []
    files += ["optimized.v", "optimize.json"] if O and (Path(out) / "optimized.v").exists() else []
    if "_recorder" in res:
        files += ["glitch_waves.vcd", "glitch_activity.saif"]
    from .htmlreport import build_report_data, write_html_report
    write_html_report(out / "report.html", build_report_data(res, whatif=W, groups=GA, files=files, optimize=O))
    if "_recorder" in res:
        res["_recorder"].write_vcd(out / "glitch_waves.vcd", res["_init_values"])
        res["_recorder"].write_saif(out / "glitch_activity.saif", res["_init_values"], design=res["design"].get("top", "top"),
                                   instance=res["design"].get("top", "top"), flops=res.get("_flops", ()))
        lines.append(f"  wrote {out}/glitch_waves.vcd (GTKWave) and glitch_activity.saif (OpenSTA read_saif)")
    lines.append(f"  open {out}/report.html in a browser for the interactive report")
    (out / "report.txt").write_text("\n".join(lines) + "\n")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="glitchscope", description=__doc__.split("\n")[0])
    ap.add_argument("--netlist", required=True); ap.add_argument("--vcd")
    ap.add_argument("--random-vectors", type=int, help="combinational designs without a testbench: N random vectors")
    ap.add_argument("--period-ps", type=float, default=2000.0, help="vector period with --random-vectors")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--lib", required=True); ap.add_argument("--model", default="M2", choices=["M0", "M1", "M2"])
    ap.add_argument("--clock"); ap.add_argument("--input-slew-ps", type=float, default=40.0)
    ap.add_argument("--input-delay-ps", type=float); ap.add_argument("--no-spice-scale", action="store_true")
    ap.add_argument("--out", default="glitchscope_out")
    ap.add_argument("--no-attribution", action="store_true", help="skip interventional attribution (faster)")
    ap.add_argument("--top-k", type=int, default=6); ap.add_argument("--perms", type=int, default=12)
    ap.add_argument("--workers", type=int, default=0, help="processes for attribution and what-ifs (0 = all CPUs)")
    ap.add_argument("--groups", help="also attribute groups: hier | level[:bands] | regex:<pattern>")
    ap.add_argument("--fixes", type=int, default=3, help="evaluate fix edits for the N best cells (0 = off)")
    ap.add_argument("--max-screen", type=int, help="cap exact single-cell evaluations (large designs)")
    ap.add_argument("--spef", help="post-layout parasitics: adds each net's wire capacitance to its load")
    ap.add_argument("--sample", type=int, help="simulate a stratified random sample of N cycles (long testbenches); "
                                                "energies are reported with 95 %% confidence intervals")
    ap.add_argument("--sample-seed", type=int, default=1)
    ap.add_argument("--optimize", action="store_true",
                    help="also write optimized.v: the register placement with the lowest measured total energy, "
                         "verified cycle by cycle against the original")
    ap.add_argument("--latency", type=int, default=0, help="with --optimize: extra pipeline stages allowed (default 0)")
    ap.add_argument("--clock-margin", type=float, default=0.15,
                    help="with --optimize: fraction of the clock period kept free for wires (default 0.15)")
    ap.add_argument("--opt-cycles", type=int, default=16, help="with --optimize: cycles measured per candidate")
    ap.add_argument("--opt-final", type=int, default=40, help="with --optimize: cycles for the reported comparison")
    ap.add_argument("--area-tie", type=float, default=0.05,
                    help="with --optimize: among placements within this fraction of the lowest energy, report the one "
                         "with the fewest flip-flops (0 = lowest energy only)")
    ap.add_argument("--opt-grid", type=int, default=10, help="with --optimize: cut positions per register bank")
    ap.add_argument("--keep-io-registers", action="store_true",
                    help="with --optimize: flip-flops at input and output ports stay where they are")
    a = ap.parse_args(argv)
    if not a.vcd and not a.random_vectors:
        ap.error("give --vcd (testbench) or --random-vectors N (combinational designs)")
    res = run_design(a.netlist, a.vcd, a.lib, a.model, a.clock, a.input_slew_ps,
                     input_delay_ps=a.input_delay_ps, spice_scale=not a.no_spice_scale,
                     attribution=not a.no_attribution, top_k=a.top_k, perms=a.perms, workers=a.workers,
                     groups=a.groups, fixes=a.fixes, random_vectors=a.random_vectors, period_ps=a.period_ps,
                     seed=a.seed, max_screen=a.max_screen, spef=a.spef, sample=a.sample, sample_seed=a.sample_seed)
    if a.optimize:
        res["optimize"] = run_optimize(a, res)
    print(write_report(res, a.out))


def run_optimize(a, res=None):
    from .optimize import GlitchFix, write_result
    fx = GlitchFix(a.netlist, a.lib, vcd=a.vcd, random_vectors=a.random_vectors,
                   period_ps=None if a.vcd else a.period_ps, latency=a.latency, clock=a.clock,
                   input_delay_ps=a.input_delay_ps, sample=a.opt_cycles, seed=a.seed, grid=a.opt_grid,
                   workdir=Path(a.out) / "optimize_work", log=lambda m: print(m, flush=True),
                   keep_io=a.keep_io_registers)
    T = fx.period_ps * (1 - a.clock_margin)
    print(f"optimizing register placement: {fx.n_banks()} bank(s), clock {fx.period_ps:.0f} ps "
          f"(pre-layout limit {T:.0f} ps)", flush=True)
    base, classic, best = fx.search(T=T)
    bc, bm = getattr(fx, "best_cuts", None), getattr(fx, "best_milp", None)
    base, minreg, classic, best, bc, bm = fx.remeasure([base, fx.min_register, classic, best, bc, bm], a.opt_final)
    best = fx.select([best, bc, bm, minreg, classic], tie=a.area_tie) or best     # references compete too
    if best is not None and best.energy and best.energy["total"] >= base.energy["total"]:
        best = None
    s = write_result(fx, base, classic, best, a.out, min_register=minreg)
    import shutil
    shutil.rmtree(Path(a.out) / "optimize_work", ignore_errors=True)
    return s


if __name__ == "__main__":
    main()
