"""Layout in the loop: what the wiring of an extracted layout does to a design, and the lumped output capacitance that
stands for it in the flow (flow.Spec.c_wire, flow.wire_spec).

    caps_of(pex)              capacitors of an extracted netlist (C elements; junction capacitance is already in the
                              schematic netlist through ad/as/pd/ps)
    with_caps(net, caps, k)   a schematic netlist with those capacitors added, scaled by k
    sensitivity(...)          which capacitors matter: each group added alone at one corner
    fit_c_wire(...)           the lumped output capacitance that reproduces the extraction's effect on bandwidth
    budget(...)               the largest v_out wiring a design tolerates
    search(...)               the capacitors added to a run's verified designs, in pick-rule order
    check(...)                the full gate on one design with the capacitors added, at one or more scales
    gate_with_caps(...)       the gate at one corner with the capacitors added
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import os
from pathlib import Path
import vga_flow as vf, evaluator as ev, flow, report as rep, layout_flow as lf


def caps_of(pex):
    """Capacitors (node a, node b, farads) of an extracted netlist."""
    out = []
    for line in Path(pex).read_text().splitlines():
        t = line.split()
        if len(t) >= 4 and t[0][:1].upper() == "C":
            v = lf._si(t[3])
            if v > 0:
                out.append((t[1], t[2], v))
    return out


def with_caps(net, caps, k, name="vga_core_12t"):
    """The netlist text with every capacitor added inside the subcircuit, scaled by k."""
    lines = [f"Cw{i} {a} {b} {k * v:.6g}" for i, (a, b, v) in enumerate(caps)]
    head, sep, tail = net.rpartition(".ends")
    return head + "\n".join(lines) + "\n" + sep + tail


def rule_order(ver, spec):
    """Every design that passes every corner, in pick-rule order (the flow's _pick applied repeatedly)."""
    left, out = [v for v in ver if v["passed"]], []
    while left:
        tmax = max(flow._targets_v(v, spec) for v in left)
        ps = [v for v in left if flow._targets_v(v, spec) == tmax]
        n0 = min(v["vrms"] for v in ps)
        p = flow._tie_pick([v for v in ps if v["vrms"] <= n0 * (1 + flow.NOISE_TIE)])
        out.append(p); left.remove(p)
    return out


def hot_corners(spec):
    return [(c, t, 1.8) for c, t in spec.corners if t == 85] + [(c, t, v) for c, t, v in spec.combos if t == 85]


def _screen_job(args):
    """One design with the wiring capacitance added, at the given corners: pass/fail per corner (no noise)."""
    p, caps, k, corners, spec = args
    tmp = vf.WORK / f"wc_{os.getpid()}.spice"
    tmp.write_text(with_caps(rep.subckt(p, "vga_core_12t"), caps, k))
    rows = []
    for c, t, v in corners:
        r = flow.spice_gate(dict(p, vdd=v, subckt=(str(tmp), "vga_core_12t")), c, t, spec, noise=False)
        r["corner"] = f"{c}/{t:g}/{v:g}V"
        ok, why = flow.corner_pass(r, spec)
        rows.append(dict(corner=r["corner"], ok=ok, why=why, bw_min=r["bw_min"], range_db=r["range_db"], vds_min=r["vds_min"]))
    return rows


def search(R12, SPEC, BASE, caps, k=1.0, procs=2):
    """The extracted capacitors added to a run's verified designs in pick-rule order: each screened at the hot corners,
    the first that passes there gets the full gate; stops at the first design that passes it."""
    import multiprocessing as mp
    order = rule_order(R12["verified"], SPEC)
    hc = hot_corners(SPEC)
    print(f"{len(order)} verified designs in pick-rule order; hot-corner screen at {len(hc)} corners with wiring caps x{k:g}",
          flush=True)
    out = dict(k=k, hot_corners=[f"{c}/{t:g}/{v:g}V" for c, t, v in hc], designs=[], new_pick=None)
    with mp.Pool(procs, initializer=flow._verify_init) as pool:
        i = 0
        while i < len(order) and out["new_pick"] is None:
            batch = order[i:i + procs]
            res = pool.map(_screen_job, [(ev.materialise(BASE, v["point"]), caps, k, hc, SPEC) for v in batch])
            for rank, (v, rows) in enumerate(zip(batch, res), start=i + 1):
                ok = all(r["ok"] for r in rows)
                d = dict(rank=rank, point=v["point"], vrms=v["vrms"], vn_1k=v["vn_1k"], area=flow.gate_area(v["point"]),
                         schematic_bw_min=v["bw_min"], i_eff_max=v["i_eff_max"], hot_pass=ok,
                         hot_bw_min=min(r["bw_min"] for r in rows), hot_fails={r["corner"]: r["why"] for r in rows if not r["ok"]})
                out["designs"].append(d)
                print(f"rank {rank}: {1e6*v['vrms']:.2f} uV, area {d['area']:.0f} um2, schematic bw {v['bw_min']/1e3:.2f} kHz -> "
                      f"hot {'PASS' if ok else 'FAIL'} (min bw {d['hot_bw_min']/1e3:.2f} kHz) {v['point']}", flush=True)
            for d in out["designs"][i:]:
                if d["hot_pass"] and out["new_pick"] is None:
                    p = ev.materialise(BASE, d["point"])
                    tmp = vf.WORK / "wc_full.spice"
                    tmp.write_text(with_caps(rep.subckt(p, "vga_core_12t"), caps, k))
                    v = flow.verify_netlist(tmp, p, SPEC)
                    d["full_pass"], d["full_fails"], d["full_bw_min"] = v["passed"], v["fails"], v["bw_min"]
                    print(f"  rank {d['rank']} full 24-corner gate with caps: {'PASS' if v['passed'] else 'FAIL ' + str(v['fails'])}, "
                          f"min bw {v['bw_min']/1e3:.2f} kHz", flush=True)
                    if v["passed"]:
                        out["new_pick"] = d
                    i += procs
    return out


def _budget_job(args):
    p, caps, k, corners, spec = args
    cs = [(a, b, v * (k if "v_out" in (a, b) else 1.0)) for a, b, v in caps]
    return k, _screen_job((p, cs, 1.0, corners, spec))


def budget(PV, SPEC, BASE, caps, ks=(0.3, 0.4, 0.5, 0.6, 0.7, 0.8), procs=2):
    """Largest output-wiring capacitance the pick tolerates: the capacitors touching v_out scaled by k (the others as
    extracted), screened at the hot corners."""
    import multiprocessing as mp
    p = ev.materialise(BASE, PV["point"])
    hc = hot_corners(SPEC)
    c_out = sum(v for a, b, v in caps if "v_out" in (a, b))
    out = dict(point=PV["point"], c_out_extracted_ff=1e15 * c_out, runs=[])
    with mp.Pool(procs, initializer=flow._verify_init) as pool:
        for k, rows in pool.imap(_budget_job, [(p, caps, k, hc, SPEC) for k in ks]):
            ok = all(r["ok"] for r in rows)
            out["runs"].append(dict(k=k, c_out_ff=1e15 * k * c_out, hot_pass=ok, hot_bw_min=min(r["bw_min"] for r in rows),
                                    fails={r["corner"]: r["why"] for r in rows if not r["ok"]}))
            print(f"v_out wiring x{k:g} ({1e15*k*c_out:.0f} fF): hot corners {'PASS' if ok else 'FAIL'}, "
                  f"min bw {min(r['bw_min'] for r in rows)/1e3:.2f} kHz", flush=True)
    ok = [r["c_out_ff"] for r in out["runs"] if r["hot_pass"]]
    out["budget_ff"] = max(ok) if ok else None
    return out


def fit_c_wire(p, spec, caps, corner=None, lo=0.0, hi=1e-12, tol=5e-15):
    """The lumped output capacitance (added to C_L) that reproduces what the extracted capacitors do to the pick's
    bandwidth at its bandwidth-critical corner: bisection on the lowest-gain-step f_-3dB. Returns farads and the
    matched bandwidths."""
    c, t, v = corner
    tmp = vf.WORK / "fit.spice"
    tmp.write_text(with_caps(rep.subckt(p, "vga_core_12t"), caps, 1.0))
    q = dict(p, vdd=v, corner=c, temp=t)
    step = ev.VSTEPS[-1]
    target = vf.bandwidth(dict(q, subckt=(str(tmp), "vga_core_12t")), step, spec.CL)["f3db"]
    f = lambda cw: vf.bandwidth(q, step, spec.CL + cw)["f3db"]
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > target else (lo, mid)
    return dict(c_wire=(lo + hi) / 2, corner=f"{c}/{t:g}/{v:g}V", step_v=step, bw_extracted=target,
                bw_schematic=f(0.0), bw_lumped=f((lo + hi) / 2))


def fit_to_netlist(p, spec, netlist, corner, lo=0.0, hi=1e-12, tol=5e-15):
    """The lumped output capacitance that makes the schematic reproduce an extracted netlist's lowest-gain-step
    bandwidth at one corner (bisection, as fit_c_wire): the final layout's wiring expressed in the units of the flow's
    allowance (spec.c_wire)."""
    c, t, v = corner
    q = dict(p, vdd=v, corner=c, temp=t)
    step = ev.VSTEPS[-1]
    target = vf.bandwidth(dict(q, subckt=(str(netlist), "vga_core_12t")), step, spec.CL)["f3db"]
    f = lambda cw: vf.bandwidth(q, step, spec.CL + cw)["f3db"]
    if not f(hi) <= target <= f(lo):
        raise ValueError(f"extracted bandwidth {target:.0f} Hz outside the range the bisection covers "
                         f"({f(hi):.0f}-{f(lo):.0f} Hz for {1e15*lo:.0f}-{1e15*hi:.0f} fF)")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > target else (lo, mid)
    return dict(c_equiv=(lo + hi) / 2, corner=f"{c}/{t:g}/{v:g}V", step_v=step, bw_extracted=target,
                bw_schematic=f(0.0), bw_allowance=f(spec.c_wire), c_allowance=spec.c_wire)


def sensitivity(p, spec, caps, corner):
    """Which extracted capacitors matter: the gate at one corner with each group of them added alone."""
    has = lambda c, n: n in (c[0], c[1])
    groups = {"none": [], "all": caps,
              "touching v_out": [c for c in caps if has(c, "v_out")],
              "v_out to the supply rails": [c for c in caps if has(c, "v_out") and (has(c, "gnd") or has(c, "vdd"))],
              "v_out to net4 (coupling)": [c for c in caps if has(c, "v_out") and has(c, "net4")],
              "net4, not v_out": [c for c in caps if has(c, "net4") and not has(c, "v_out")],
              "net2, net3, net5 only": [c for c in caps if any(has(c, n) for n in ("net2", "net3", "net5"))
                                        and not has(c, "v_out") and not has(c, "net4")]}
    c, t, v = corner
    tmp = vf.WORK / "sens.spice"
    out = []
    for g, cs in groups.items():
        tmp.write_text(with_caps(rep.subckt(p, "vga_core_12t"), cs, 1.0))
        r = flow.spice_gate(dict(p, vdd=v, subckt=(str(tmp), "vga_core_12t")), c, t, spec, noise=False)
        out.append(dict(group=g, c_sum_ff=1e15 * sum(x[2] for x in cs), range_db=r["range_db"], bw_curve=r["bw_curve"],
                        av_steps_db=r["av_steps_db"], passes=flow.corner_pass(r, spec)[0]))
        print(f"{g:28s} {out[-1]['c_sum_ff']:6.0f} fF  range {r['range_db']:5.1f} dB  lowest-step f-3dB {r['bw_curve'][-1]/1e3:.2f} kHz", flush=True)
    return dict(corner=f"{c}/{t:g}/{v:g}V", groups=out)


def check(p, spec, caps, scales=(1.0,), base_corners=None):
    """The full SPICE gate (every corner of `spec`, noise at tt) on design p with every extracted capacitor added, at
    each scale. spec.c_wire is dropped: the capacitors replace the lumped allowance."""
    from dataclasses import asdict
    chk = flow.Spec(**{**asdict(spec), "c_wire": 0.0})
    base_bw = {r["corner"]: r["bw_min"] for r in (base_corners or [])}
    node = {}
    for a, b, v in caps:
        for n in (a, b):
            node[n] = node.get(n, 0.0) + v
    out = dict(n_caps=len(caps), node_ff={n: 1e15 * v for n, v in node.items()}, runs={})
    tmp = vf.WORK / "wc_check.spice"
    for k in scales:
        tmp.write_text(with_caps(rep.subckt(p, "vga_core_12t"), caps, k))
        v = flow.verify_netlist(tmp, p, chk)
        worst = min(v["corners"], key=lambda r: r["bw_min"])
        out["runs"][f"{k:g}"] = dict(passed=v["passed"], fails=v["fails"], bw_min=v["bw_min"], worst_corner=worst["corner"],
                                    bw_drop_worst=(1 - worst["bw_min"] / base_bw[worst["corner"]]) if worst["corner"] in base_bw else None,
                                    vds_min=v["vds_min"], vrms=v["vrms"], range_min=v["range_min"], i_eff_max=v["i_eff_max"],
                                    corners=[dict(corner=r["corner"], bw_min=r["bw_min"], vds_min=r["vds_min"],
                                                  range_db=r["range_db"], bw_curve=r["bw_curve"]) for r in v["corners"]])
    return out


def gate_with_caps(p, spec, caps, corner, k=1.0):
    """flow.spice_gate at one corner on design p with the extracted capacitors added (scaled by k); spec.c_wire dropped."""
    from dataclasses import asdict
    chk = flow.Spec(**{**asdict(spec), "c_wire": 0.0})
    c, t, v = corner
    tmp = vf.WORK / "wc_gate.spice"
    tmp.write_text(with_caps(rep.subckt(p, "vga_core_12t"), caps, k))
    return flow.spice_gate(dict(p, vdd=v, subckt=(str(tmp), "vga_core_12t")), c, t, chk, noise=False)
