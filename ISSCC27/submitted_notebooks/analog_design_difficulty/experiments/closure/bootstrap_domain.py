#!/usr/bin/env python3
"""Bootstrapped-switch terminal voltages against the SKY130 compact-model domain.

    uv run python experiments/closure/bootstrap_domain.py diag   <design> <corner> <vdd> <temp> [primary|stress] [edge_ns]
    uv run python experiments/closure/bootstrap_domain.py domain <design> [--edge-ns 0.1]

The published SPICE-model domain of the SKY130 1.8 V MOS devices (SkyWater PDK documentation,
"Operating Voltages where SPICE models are valid") is, for sky130_fd_pr__nfet_01v8,
VDS 0..1.95 V, VGS 0..1.95 V, VBS +0.3..-1.95 V, and for sky130_fd_pr__pfet_01v8 the mirror
(VDS 0..-1.95 V, VGS 0..-1.95 V, VBS -0.1..+1.95 V). Source is the lower (NMOS) / higher (PMOS)
of the two channel terminals at each instant, as in run_final.py's devlimits.

diag    one sequential run (cal_alt) with every internal switch node saved; prints, for every device
        and terminal quantity, the peak, its time inside the clock period, and all node voltages there.
summary re-print the summary of a saved domain JSON.
domain  every device/terminal quantity checked against the domain above (no steady/transient split)
        over the conditions of run_final.py devlimits (all 1.95 V and all 125 C), both timings.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import numpy as np

import designs
import parent_metric as pm
import shbench as sb

OUT = sb.REPO / "results" / "closure" / "bootstrap_domain"
VMAX = 1.95
TOL = 1e-3       # reporting tolerance, as in assemble_final.py (1 mV)
VBS_FWD = {"n": 0.3, "p": 0.1}   # allowed forward body-source bias in the model domain (1.8 V devices)
# published SPICE-model domain per device class: (max |VDS|, max |VGS|, max reverse |VBS|, max forward VBS)
DOMAIN = {
    "sky130_fd_pr__nfet_01v8": (1.95, 1.95, 1.95, 0.3), "sky130_fd_pr__pfet_01v8": (1.95, 1.95, 1.95, 0.1),
    "sky130_fd_pr__nfet_01v8_lvt": (1.95, 1.95, 1.95, 0.3), "sky130_fd_pr__pfet_01v8_lvt": (1.95, 1.95, 1.95, 0.1),
    "sky130_fd_pr__nfet_03v3_nvt": (3.3, 3.3, 3.3, 0.0),
    "sky130_fd_pr__nfet_g5v0d10v5": (11.0, 5.5, 5.5, 0.0), "sky130_fd_pr__pfet_g5v0d10v5": (11.0, 5.5, 5.5, 0.0),
}


def devices_for(des: sb.Design) -> dict[str, tuple[str, str, str, str, str]]:
    """(d, g, s, b, type) of every MOS in the switch subcircuit, parsed from its netlist."""
    text = (sb.NETLISTS / des.switch.subckt_file).read_text().splitlines()
    ports = None
    devs = {}
    for ln in text:
        f = ln.split()
        if not f or f[0].startswith("*"):
            continue
        if f[0].lower() == ".subckt":
            ports = [p for p in f[2:] if "=" not in p]
            continue
        if f[0].upper().startswith("XM"):
            # map subckt port names to bench nets, internal nodes to xsw.<node>
            bench = dict(zip(ports, ["out", "samp", "phi", "phib", "vdd", "0"]))
            nodes = [bench.get(n, f"xsw.{n}") for n in f[1:5]]
            typ = "p" if "pfet" in f[5] else "n"
            devs[f[0][1:]] = (*nodes, typ, f[5])
    return devs


def internal_nodes(devs) -> tuple[str, ...]:
    nodes = {n for d in devs.values() for n in d[:4] if n.startswith("xsw.")}
    nodes |= {n for d in devs.values() for n in d[:4] if n in ("phi", "phib")}
    return tuple(sorted(nodes)) + ("phi", "phib", "vdd")


def run(des: sb.Design, p: sb.PVT, tm: sb.Timing, edge: float, so: sb.SimOpts = sb.SimOpts(), ncyc: int = 0):
    devs = devices_for(des)
    d2 = replace(des, name=des.name + "_bd", edge=edge, switch=replace(des.switch, probes=internal_nodes(devs)))
    seq = pm.sequences()["cal_alt"]
    w = sb.run_sequence(d2, p, seq[:ncyc] if ncyc else seq, tm, so, "bdom")
    return w, devs


def quantities(w, dev, sel):
    dn, gn, sn, bn, typ, _ = dev
    V = lambda n: np.zeros(sel.sum()) if n == "0" else w[n][sel]
    vd, vg, vs, vb = V(dn), V(gn), V(sn), V(bn)
    if typ == "n":
        vsrc, vdrn = np.minimum(vd, vs), np.maximum(vd, vs)
        # model-domain coordinates, sign as in the PDK table (NMOS positive VGS/VDS, negative VBS)
        vgs, vds, vbs = vg - vsrc, vdrn - vsrc, vb - vsrc
    else:
        vsrc, vdrn = np.maximum(vd, vs), np.minimum(vd, vs)
        vgs, vds, vbs = vsrc - vg, vsrc - vdrn, vsrc - vb   # magnitudes in the PMOS sign convention
    return {"vgs": vgs, "vgd": (vg - vdrn) if typ == "n" else (vdrn - vg), "vds": vds, "vbs": vbs,
            "vgb": np.abs(vg - vb)}


def domain_check(w, devs, tm: sb.Timing) -> dict:
    t = w["t"]
    sel = t >= tm.period          # after the start-up cycle
    tt = t[sel]
    dt = float(np.median(np.diff(t)))
    ncyc = len(w["levels"]) - 1
    out = {}
    for name, dev in devs.items():
        q = quantities(w, dev, sel)
        typ = dev[4]
        vds_max, vgs_max, vbs_rev, vbs_fwd = DOMAIN[dev[5]]
        lim = {"vgs": vgs_max, "vgd": vgs_max, "vds": vds_max}
        r = {"model": dev[5], "limits": {"vgs": vgs_max, "vds": vds_max, "vbs": [-vbs_rev, vbs_fwd]}}
        for k in ("vgs", "vgd", "vds"):
            v = q[k]
            over = v > lim[k] + TOL
            i = int(np.argmax(v))
            r[k] = {"max_V": float(v[i]), "t_in_period_ns": float((tt[i] % tm.period) * 1e9),
                    "ns_over_per_cycle": float(over.sum() * dt * 1e9 / ncyc)}
        # body bias, positive = forward: NMOS vb - vsrc in [-1.95, +0.3]; PMOS vsrc - vb in [-1.95, +0.1]
        # (the PDK's PMOS VBS = -0.1..+1.95 with VBS = vb - vs)
        v = q["vbs"]
        lo, hi = -vbs_rev, vbs_fwd
        imin, imax = int(np.argmin(v)), int(np.argmax(v))
        over = (v < lo - TOL) | (v > hi + TOL)
        r["vbs"] = {"min_V": float(v[imin]), "max_V": float(v[imax]), "allowed": [lo, hi],
                    "ns_over_per_cycle": float(over.sum() * dt * 1e9 / ncyc)}
        g = q["vgb"]
        r["vgb"] = {"max_V": float(g.max())}
        r["in_domain"] = all(r[k]["max_V"] <= lim[k] + TOL for k in ("vgs", "vgd", "vds")) and not over.any()
        out[name] = r
    return out


def diag(a) -> None:
    des = designs.DESIGNS[a.design]
    p = sb.PVT(a.corner, a.vdd, a.temp)
    tm = sb.STRESS if a.timing == "stress" else sb.Timing()
    edge = a.edge_ns * 1e-9
    so = sb.SimOpts(tmax=a.tmax_ps * 1e-12, tstep_out=a.tmax_ps * 1e-12, reltol=a.reltol)
    w, devs = run(des, p, tm, edge, so, a.ncyc)
    t = w["t"]
    sel = t >= tm.period
    tt = t[sel]
    nodes = internal_nodes(devs) + ("out", "samp")
    for name, dev in devs.items():
        q = quantities(w, dev, sel)
        for k in ("vgs", "vgd", "vds"):
            v = q[k]
            i = int(np.argmax(v))
            if v[i] <= VMAX + TOL and not a.all:
                continue
            k_cyc = int(tt[i] // tm.period)
            snap = " ".join(f"{n.replace('xsw.', '')}={w[n][sel][i]:.3f}" for n in nodes)
            print(f"{name:4s} {k:3s} max {v[i]:.3f} V  t={tt[i]*1e9:.3f} ns (cycle {k_cyc}, "
                  f"{(tt[i] % tm.period)*1e9:.3f} ns in period; level {w['levels'][k_cyc-1]:.2f}->{w['levels'][k_cyc]:.2f})"
                  f"  ns>1.95/cyc {float((v > VMAX + TOL).sum()*np.median(np.diff(t))*1e9/(len(w['levels'])-1)):.3f}\n      {snap}")
    if a.dump:
        t0, t1 = a.dump
        m = (t >= t0 * 1e-9) & (t <= t1 * 1e-9)
        cols = ["t"] + list(nodes)
        np.savetxt(sys.stdout, np.column_stack([t[m] * 1e9] + [w[n][m] for n in nodes]), fmt="%.4f",
                   header=" ".join(c.replace("xsw.", "") for c in cols))


def domain(a) -> None:
    des = designs.DESIGNS[a.design]
    pv = [p for p in pm.FINAL_PVT if p.vdd == 1.95 or p.temp == 125]
    jobs = [(p, tm) for p in pv for tm in (sb.Timing(), sb.STRESS)]

    def one(j):
        p, tm = j
        w, devs = run(des, p, tm, a.edge_ns * 1e-9)
        return {"tag": p.tag, "timing": "stress" if tm.t_in > -1e-9 else "primary",
                "devices": domain_check(w, devs, tm)}

    with ThreadPoolExecutor(max_workers=int(os.environ.get("CLOSURE_WORKERS", 11))) as ex:
        res = list(ex.map(one, jobs))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{des.name}_edge{a.edge_ns:g}ns.json").write_text(json.dumps(res, indent=1))
    summarize(res)


def summarize(res) -> None:
    worst = {}
    for r in res:
        for n, q in r["devices"].items():
            for k in ("vgs", "vgd", "vds"):
                key = (n, k)
                if key not in worst or q[k]["max_V"] > worst[key][0]:
                    lk = q.get("limits", {}).get("vgs" if k == "vgd" else k, VMAX)
                    worst[key] = (q[k]["max_V"], q[k]["ns_over_per_cycle"], f"{r['tag']}/{r['timing']}", lk)
            for lab, val, sgn in (("vbs_min", q["vbs"]["min_V"], -1), ("vbs_fwd", q["vbs"]["max_V"], 1)):
                key = (n, lab)
                if key not in worst or sgn * val > sgn * worst[key][0]:
                    worst[key] = (val, q["vbs"]["ns_over_per_cycle"], f"{r['tag']}/{r['timing']}",
                                  q["vbs"]["allowed"])
    n_out = sum(not q["in_domain"] for r in res for q in r["devices"].values())
    print(f"device-condition pairs outside the model domain: {n_out} / {sum(len(r['devices']) for r in res)}")
    for (n, k), (v, o, tag, *al) in sorted(worst.items()):
        if k == "vbs_min":
            bad = v < al[0][0] - TOL
        elif k == "vbs_fwd":
            bad = v > al[0][1] + TOL
        else:
            bad = v > (al[0] if al else VMAX) + TOL
        flag = "OUT" if bad else ""
        print(f"  {n:4s} {k:8s} {v:+.3f} V  {o:.3f} ns/cyc  {tag} {flag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diag")
    d.add_argument("design"); d.add_argument("corner"); d.add_argument("vdd", type=float)
    d.add_argument("temp", type=float); d.add_argument("timing", nargs="?", default="primary")
    d.add_argument("edge_ns", nargs="?", type=float, default=0.1)
    d.add_argument("--tmax-ps", type=float, default=5.0)
    d.add_argument("--reltol", type=float, default=1e-5)
    d.add_argument("--all", action="store_true")
    d.add_argument("--ncyc", type=int, default=0, help="run only the first N levels of cal_alt (numerics checks)")
    d.add_argument("--dump", nargs=2, type=float, metavar=("T0_NS", "T1_NS"))
    m = sub.add_parser("domain")
    m.add_argument("design"); m.add_argument("--edge-ns", type=float, default=0.1)
    s = sub.add_parser("summary")
    s.add_argument("json")
    a = ap.parse_args()
    if a.cmd == "summary":
        summarize(json.loads(open(a.json).read()))
        return
    {"diag": diag, "domain": domain}[a.cmd](a)


if __name__ == "__main__":
    main()
