#!/usr/bin/env python3
"""Final verification of one design (CLOSURE_BRIEF.md Sections 5-8 and amendments A1-A5).

    uv run python experiments/closure/run_final.py <design> [--parts parent,stress,...]

Writes results/closure/final/<design>/<part>.json and, when every part exists, the machine-readable
closure result results/closure/final/<design>/final_closure.json. Parts:

parent      all 45 conditions x four sequences, primary timing
stress      STRESS timing (command step at switch closure), cal_alt + pair, at tt, the three worst
            parent conditions and the three hot low-supply points
fine        staircase over 25 mV levels (L25), at tt and the three worst parent conditions
sens        clock edges 0.1/0.5 ns, phi/phib skew +-50 ps, Iref +-20 %, Cs +-10 %; cal_alt + pair at
            tt and the two worst parent conditions
stability   loop PM/GM and saturation margins, 45 conditions x {0.6, 0.9, 1.2} V
noise       held-sample noise (switch exactly kT/C, 1 mHz-50 GHz), 45 conditions x {0.6, 1.2} V
numerics    worst parent condition re-run with tmax 2 ps / reltol 1e-6 and with method=gear
devlimits   terminal voltages of every sampling-switch device at all 1.95 V and 125 C conditions,
            both timings, 0.1 ns edges
"""
from __future__ import annotations

import argparse
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import numpy as np

import designs
import noise
import parent_metric as pm
import shbench as sb
import stability

OUT = sb.REPO / "results" / "closure" / "final"
VLSB_MV = pm.VLSB * 1e3


def _save(d: str, part: str, obj) -> None:
    (OUT / d).mkdir(parents=True, exist_ok=True)
    (OUT / d / f"{part}.json").write_text(json.dumps(obj, indent=1, default=float))


def _load(d: str, part: str):
    p = OUT / d / f"{part}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def _strip(res: list[dict]) -> list[dict]:
    """Keep per-cycle data only for the worst condition (file size)."""
    worst = max(range(len(res)), key=lambda i: res[i]["max_abs_r_LSB"])
    return [r if i == worst else {k: v for k, v in r.items() if k != "cycles"} for i, r in enumerate(res)]


def worst_conditions(d: str, n: int) -> list[sb.PVT]:
    res = _load(d, "parent")
    order = sorted(res, key=lambda r: -r["max_abs_r_LSB"])
    return [sb.PVT(**r["pvt"]) for r in order[:n]]


def part_parent(des: sb.Design) -> list[dict]:
    return _strip(pm.evaluate_many(des, pm.FINAL_PVT, include=("cal_alt", "pair", "stair", "mem")))


def part_stress(des: sb.Design) -> list[dict]:
    pv = [sb.PVT()] + worst_conditions(des.name, 3) + pm.STRESS_EXTRA_PVT
    uniq = list(dict.fromkeys(pv))
    return _strip(pm.evaluate_many(des, uniq, include=("cal_alt", "pair"), tm=sb.STRESS))


def part_fine(des: sb.Design) -> list[dict]:
    pv = list(dict.fromkeys([sb.PVT()] + worst_conditions(des.name, 3)))
    seqs = pm.sequences(levels_stair=pm.L25)
    return _strip(pm.evaluate_many(des, pv, include=("cal_alt", "stair"), seqs=seqs))


def part_sens(des: sb.Design) -> dict:
    pv = list(dict.fromkeys([sb.PVT()] + worst_conditions(des.name, 2)))
    variants = {
        "edge_0.1ns": replace(des, name=des.name + "_e01", edge=0.1e-9),
        "edge_0.5ns": replace(des, name=des.name + "_e05", edge=0.5e-9),
        "skew_+50ps": replace(des, name=des.name + "_skp", skew=50e-12),
        "skew_-50ps": replace(des, name=des.name + "_skm", skew=-50e-12),
        "iref_+20%": replace(des, name=des.name + "_ip", iref=des.iref * 1.2),
        "iref_-20%": replace(des, name=des.name + "_im", iref=des.iref * 0.8),
        "cs_+10%": replace(des, name=des.name + "_cp", cs=des.cs * 1.1),
        "cs_-10%": replace(des, name=des.name + "_cm", cs=des.cs * 0.9),
    }
    return {k: _strip(pm.evaluate_many(v, pv, include=("cal_alt", "pair"))) for k, v in variants.items()}


def part_stability(des: sb.Design) -> list[dict]:
    jobs = [(p, lv) for p in pm.FINAL_PVT for lv in (0.6, 0.9, 1.2)]
    with ThreadPoolExecutor(max_workers=int(__import__("os").environ.get("CLOSURE_WORKERS", 11))) as ex:
        return list(ex.map(lambda j: stability.run(des, *j), jobs))


def part_noise(des: sb.Design) -> list[dict]:
    jobs = [(p, lv) for p in pm.FINAL_PVT for lv in (0.6, 1.2)]
    with ThreadPoolExecutor(max_workers=int(__import__("os").environ.get("CLOSURE_WORKERS", 11))) as ex:
        return list(ex.map(lambda j: noise.run(des, *j), jobs))


def part_numerics(des: sb.Design) -> dict:
    w = worst_conditions(des.name, 1)[0]
    ref = [r for r in _load(des.name, "parent") if sb.PVT(**r["pvt"]) == w][0]
    seq = ref["worst_cycle"]["seq"]
    inc = ("cal_alt", seq)
    out = {"condition": w.tag, "sequence": seq, "reference_max_abs_r_mV": ref["max_abs_r_mV"]}
    fine = sb.SimOpts(tmax=2e-12, reltol=1e-6, abstol=1e-15, tstep_out=2e-12)
    r1 = pm.evaluate_many(des, [w], include=inc, so=fine)[0]
    r2 = pm.evaluate_many(des, [w], include=inc, so=replace(sb.SimOpts(), method="gear"))[0]
    out["fine_max_abs_r_mV"] = r1["max_abs_r_mV"]
    out["delta_fine_mV"] = r1["max_abs_r_mV"] - ref["max_abs_r_mV"]
    if True:
        out["gear_max_abs_r_mV"] = r2["max_abs_r_mV"]
        out["delta_gear_mV"] = r2["max_abs_r_mV"] - ref["max_abs_r_mV"]
    return out


# sampling-switch device terminals (d, g, s, b) of sw_bootab.spice, as saved node names
BOOT_DEVICES = {
    "MS": ("out", "xsw.g", "samp", "0"), "MZA": ("vdd", "xsw.z2", "xsw.z1", "0"),
    "MZB": ("vdd", "xsw.z1", "xsw.z2", "0"), "MTN": ("vdd", "xsw.z1", "xsw.t", "0"),
    "MB0": ("xsw.bt", "phib", "0", "0"), "MGC": ("xsw.g", "vdd", "xsw.n1", "0"),
    "MG0": ("xsw.n1", "phib", "0", "0"), "MXP": ("xsw.x", "phi", "vdd", "vdd"),
    "MGT": ("xsw.g", "xsw.x", "xsw.t", "xsw.t"), "MXS": ("xsw.x", "phi", "xsw.bt", "0"),
    "MXB": ("xsw.x", "xsw.g", "xsw.bt", "0"), "MBI": ("out", "xsw.g", "xsw.bt", "0"),
}
PMOS = {"MXP", "MGT"}
PROBES = ("xsw.g", "xsw.t", "xsw.bt", "xsw.x", "xsw.z1", "xsw.z2", "xsw.n1", "phi", "phib", "vdd")


def _devlimit_one(des: sb.Design, p: sb.PVT, tm: sb.Timing) -> dict:
    d2 = replace(des, name=des.name + "_dl", edge=0.1e-9,
                 switch=replace(des.switch, probes=PROBES))
    w = sb.run_sequence(d2, p, pm.sequences()["cal_alt"], tm, sb.SimOpts(), "devlim")
    t = w["t"]
    sel = t >= 100e-9  # after the start-up cycle
    V = lambda n: np.zeros(sel.sum()) if n == "0" else w[n][sel]
    res = {}
    for dev, (dn, gn, sn, bn) in BOOT_DEVICES.items():
        vd, vg, vs, vb = V(dn), V(gn), V(sn), V(bn)
        if dev in PMOS:
            vsrc, vdrn = np.maximum(vd, vs), np.minimum(vd, vs)
        else:
            vsrc, vdrn = np.minimum(vd, vs), np.maximum(vd, vs)
        q = {"vgs": np.abs(vg - vsrc), "vgd": np.abs(vg - vdrn), "vds": np.abs(vd - vs), "vbs": vb - vsrc,
             "vgb": np.abs(vg - vb)}
        dt = float(np.median(np.diff(t)))
        ncyc = len(w["levels"]) - 1
        # "steady state" (amendment A3): value 1 ns before the end of each clock phase
        tt = t[sel]
        T, ta = tm.period, tm.tacq
        ends = [k * T + ta - 1e-9 for k in range(1, ncyc + 1)] + [(k + 1) * T - 1e-9 for k in range(1, ncyc + 1)]
        idx = np.searchsorted(tt, ends)
        idx = idx[idx < len(tt)]
        res[dev] = {}
        for k, v in q.items():
            if k == "vbs":
                sgn = -1.0 if dev not in PMOS else 1.0
                worst = float((sgn * v).max() * sgn)
                steady = float((sgn * v[idx]).max() * sgn)
                over = (sgn * v) > 1.95 + 0.01
            else:
                worst = float(v.max())
                steady = float(v[idx].max())
                over = v > 1.95 + 0.01
            res[dev][k] = {"worst_V": worst, "steady_V": steady,
                           "time_over_1.96V_ns_per_cycle": float(over.sum() * dt * 1e9 / ncyc)}
    return {"tag": p.tag, "timing": "stress" if tm.t_in > -1e-9 else "primary", "devices": res}


def part_devlimits(des: sb.Design) -> list[dict]:
    if des.switch.kind != "sub":
        return []
    pv = [p for p in pm.FINAL_PVT if p.vdd == 1.95 or p.temp == 125]
    jobs = [(p, tm) for p in pv for tm in (sb.Timing(), sb.STRESS)]
    with ThreadPoolExecutor(max_workers=int(__import__("os").environ.get("CLOSURE_WORKERS", 11))) as ex:
        return list(ex.map(lambda j: _devlimit_one(des, *j), jobs))


PARTS = {"parent": part_parent, "stress": part_stress, "fine": part_fine, "sens": part_sens,
         "stability": part_stability, "noise": part_noise, "numerics": part_numerics,
         "devlimits": part_devlimits}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--parts", default=",".join(PARTS))
    a = ap.parse_args()
    des = designs.DESIGNS[a.design]
    for part in a.parts.split(","):
        t0 = time.time()
        _save(des.name, part, PARTS[part](des))
        print(f"{part}: {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
