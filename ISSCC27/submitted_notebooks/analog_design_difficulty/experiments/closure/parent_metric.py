#!/usr/bin/env python3
"""Parent metric of the restart (CLOSURE_BRIEF.md, Section 2) on the sequential bench.

``evaluate(design, pvt)`` runs the declared sequences for one PVT condition, derives the
terminal two-point correction from the same-level repeated samples at 0.6 V and 1.2 V
(per window), applies it unchanged to every counted cycle of every sequence, and returns
the residuals, the diagnostic components, and PASS/FAIL against VLSB.
"""
from __future__ import annotations

import itertools
from dataclasses import replace

import numpy as np

import shbench as sb

VLSB = 0.6 / 1024
LO, HI = 0.6, 1.2
L7 = [round(0.6 + 0.1 * i, 3) for i in range(7)]
L13 = [round(0.6 + 0.05 * i, 3) for i in range(13)]
L25 = [round(0.6 + 0.025 * i, 4) for i in range(25)]


def de_bruijn(symbols: list[float], n: int) -> list[float]:
    """Linear de Bruijn sequence: every length-n word over ``symbols`` appears once."""
    k = len(symbols)
    a = [0] * k * n
    seq: list[int] = []

    def db(t: int, p: int) -> None:
        if t > n:
            if n % p == 0:
                seq.extend(a[1:p + 1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)

    db(1, 1)
    seq = seq + seq[:n - 1]
    return [symbols[i] for i in seq]


def sequences(levels_stair: list[float] = L13) -> dict[str, list[float]]:
    """Declared sequences; element 0 of each is the start-up cycle (never counted)."""
    cal = [LO] + [LO] * 4 + [HI] * 4 + [LO, HI] * 6
    pair = de_bruijn(L7, 2)            # 50 levels -> 49 counted (previous, target) pairs
    stair = [levels_stair[0]] + levels_stair + levels_stair[-2::-1]
    mem = de_bruijn([LO, 0.9, HI], 3)  # 29 levels -> 28 counted cycles
    return {"cal_alt": cal, "pair": pair, "stair": stair, "mem": mem}


CAL_LO_IDX = (3, 4)   # cycles 3-4 of cal_alt: 3rd and 4th repeated sample at 0.6 V
CAL_HI_IDX = (7, 8)   # cycles 7-8: 3rd and 4th repeated sample at 1.2 V


def cycle_values(w: dict) -> list[dict]:
    """Per-cycle read-out of one sequential run (cycle 0 included, flagged)."""
    tm = w["timing"]
    T, tacq = tm["period"], tm["tacq"]
    out = []
    for k, u in enumerate(w["levels"]):
        t_o = k * T + tacq
        t_next = (k + 1) * T
        pre = sb.window_mean(w, t_o - 1.0e-9, t_o - 0.2e-9)
        y_e = sb.window_mean(w, t_o + 10e-9, t_o + 20e-9)
        y_l = sb.window_mean(w, t_next - 6e-9, t_next - 1e-9)
        lo_e, hi_e = sb.window_extremes(w, t_o + 10e-9, t_o + 20e-9)
        lo_l, hi_l = sb.window_extremes(w, t_next - 6e-9, t_next - 1e-9)
        out.append({"k": k, "u": u, "prev": w["levels"][k - 1] if k else None,
                    "pre": pre, "yE": y_e, "yL": y_l,
                    "ppE": hi_e - lo_e, "ppL": hi_l - lo_l})
    return out


def _line(vals: dict, key: str) -> tuple[float, float]:
    lo = np.mean([vals[i][key] - LO for i in CAL_LO_IDX])
    hi = np.mean([vals[i][key] - HI for i in CAL_HI_IDX])
    return float(lo), float((hi - lo) / (HI - LO))


def evaluate(design: sb.Design, pvt: sb.PVT, tm: sb.Timing = sb.Timing(), so: sb.SimOpts = sb.SimOpts(),
             seqs: dict[str, list[float]] | None = None, include: tuple[str, ...] | None = None,
             cal_only_from: dict | None = None) -> dict:
    seqs = seqs or sequences()
    if include is not None:
        seqs = {k: v for k, v in seqs.items() if k in include or k == "cal_alt"}
    runs = sb.run_many([(design, pvt, lv, tm, so, name) for name, lv in seqs.items()])
    data = {name: cycle_values(w) for name, w in zip(seqs, runs)}
    current = float(np.mean([sb.supply_current(w) for w in runs]))
    return summarize(data, current, design.name, pvt, cal_only_from)


def summarize(data: dict, current: float, name: str, pvt: sb.PVT, cal_only_from: dict | None = None) -> dict:
    cal = data["cal_alt"]
    # terminal lines (offset at 0.6 V, gain error) for each window and for the components
    lines = {w: _line(cal, w) for w in ("yE", "yL", "pre")}
    if cal_only_from is not None:
        lines = cal_only_from
    # component quantities per cycle: S = pre - u, P = yE - pre, H = yL - yE
    def comp(c: dict) -> dict[str, float]:
        oE, gE = lines["yE"]; oL, gL = lines["yL"]; oS, gS = lines["pre"]
        rE = c["yE"] - c["u"] - oE - gE * (c["u"] - LO)
        rL = c["yL"] - c["u"] - oL - gL * (c["u"] - LO)
        rS = c["pre"] - c["u"] - oS - gS * (c["u"] - LO)
        return {"rE": rE, "rL": rL, "rS": rS, "rP": rE - rS, "rH": rL - rE}
    cycles = []
    for seq, vals in data.items():
        for c in vals:
            if c["k"] == 0:
                continue
            cycles.append({"seq": seq, **c, **comp(c)})
    arr = lambda key: np.array([c[key] for c in cycles])
    rE, rL = arr("rE"), arr("rL")
    worst_idx = int(np.argmax(np.maximum(abs(rE), abs(rL))))
    maxr = float(max(abs(rE).max(), abs(rL).max()))
    comps = {k: float(abs(arr(k)).max()) for k in ("rS", "rP", "rH")}
    # history term: spread of the pre-opening residual over previous states, per target
    hist = 0.0
    for u in set(arr("u")):
        s = [c["rS"] for c in cycles if c["u"] == u]
        if len(s) > 1:
            hist = max(hist, max(s) - min(s))
    pp = float(max(arr("ppE").max(), arr("ppL").max()))
    res = {
        "design": name, "pvt": {"corner": pvt.corner, "vdd": pvt.vdd, "temp": pvt.temp}, "tag": pvt.tag,
        "VLSB_mV": VLSB * 1e3,
        "max_abs_r_mV": maxr * 1e3, "max_abs_r_LSB": maxr / VLSB,
        "max_abs_rE_mV": float(abs(rE).max()) * 1e3, "max_abs_rL_mV": float(abs(rL).max()) * 1e3,
        "components_mV": {k: v * 1e3 for k, v in comps.items()},
        "history_spread_rS_mV": hist * 1e3,
        "sum_component_max_mV": (comps["rS"] + comps["rP"] + comps["rH"]) * 1e3,
        "offset_mV": {k: v[0] * 1e3 for k, v in lines.items()},
        "gain_err_mV_per_V": {k: v[1] * 1e3 for k, v in lines.items()},
        "max_window_pp_mV": pp * 1e3,
        "supply_current_uA": current * 1e6,
        "worst_cycle": {k: (float(v) if isinstance(v, (float, np.floating)) else v)
                        for k, v in cycles[worst_idx].items()},
        "pass": bool(maxr <= VLSB),
        "n_cycles": len(cycles),
    }
    # Historical field name retained for compatibility with saved records. True means
    # a passing result exceeds the conservative no-cancellation bound and needs paired
    # analysis; it does not establish cancellation reliance. False alone is not a PASS.
    res["cancellation_reliant"] = bool(res["sum_component_max_mV"] > VLSB * 1e3 and res["pass"])
    res["lines"] = {k: list(v) for k, v in lines.items()}
    res["cycles"] = [{k: (round(float(v), 9) if isinstance(v, (float, np.floating)) else v) for k, v in c.items()}
                     for c in cycles]
    return res


# Amendment A1: supply set {1.60, 1.80, 1.95} V
SCREEN_PVT = [
    sb.PVT("tt", 1.80, 27), sb.PVT("ss", 1.60, -40), sb.PVT("ff", 1.95, 125),
    sb.PVT("sf", 1.60, -40), sb.PVT("fs", 1.60, -40), sb.PVT("sf", 1.95, 125), sb.PVT("fs", 1.95, 125),
]
# hot, low-supply points added to the stress checks after the driver study (design-study record)
STRESS_EXTRA_PVT = [sb.PVT("ss", 1.60, 125), sb.PVT("fs", 1.60, 125), sb.PVT("tt", 1.60, 125)]
SUPPLIES = (1.60, 1.80, 1.95)
FINAL_PVT = [sb.PVT(c, v, t) for c in ("tt", "ss", "ff", "sf", "fs") for v in SUPPLIES
             for t in (-40, 27, 125)]


def evaluate_many(design: sb.Design, pvts: list[sb.PVT], include: tuple[str, ...] = ("cal_alt", "pair"),
                  tm: sb.Timing = sb.Timing(), so: sb.SimOpts = sb.SimOpts(),
                  seqs: dict[str, list[float]] | None = None) -> list[dict]:
    """Run ``include`` sequences at every PVT condition in one job pool and summarize per condition."""
    seqs = seqs or sequences()
    names = [n for n in seqs if n in include or n == "cal_alt"]
    jobs = [(design, p, seqs[n], tm, so, n) for p in pvts for n in names]
    runs = sb.run_many(jobs)
    out = []
    for i, p in enumerate(pvts):
        ws = runs[i * len(names):(i + 1) * len(names)]
        data = {n: cycle_values(w) for n, w in zip(names, ws)}
        cur = float(np.mean([sb.supply_current(w) for w in ws]))
        out.append(summarize(data, cur, design.name, p))
    return out


GUARD_LSB = 0.85  # screening advancement guard (CLOSURE_BRIEF.md Section 5)


def table(results: list[dict]) -> str:
    rows = ["| condition | max|r| (LSB) | rE / rL (mV) | rS / rP / rH max (mV) | hist (mV) | offset E (mV) | gain E (mV/V) | I (uA) | PASS |",
            "|---|---:|---|---|---:|---:|---:|---:|---|"]
    for r in results:
        c = r["components_mV"]
        rows.append(f"| {r['tag']} | {r['max_abs_r_LSB']:.2f} | {r['max_abs_rE_mV']:.3f} / {r['max_abs_rL_mV']:.3f} | "
                    f"{c['rS']:.3f} / {c['rP']:.3f} / {c['rH']:.3f} | {r['history_spread_rS_mV']:.3f} | "
                    f"{r['offset_mV']['yE']:.2f} | {r['gain_err_mV_per_V']['yE']:.1f} | {r['supply_current_uA']:.0f} | "
                    f"{'PASS' if r['pass'] else 'FAIL'}{'' if r['max_abs_r_LSB'] <= GUARD_LSB else ' (outside 0.85 guard)'} |")
    return "\n".join(rows)
