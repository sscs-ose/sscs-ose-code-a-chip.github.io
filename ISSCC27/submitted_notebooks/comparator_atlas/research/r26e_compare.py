"""r26e: does SPICE agree with the r26d segmentation prediction?

Usage: r26e_compare.py [binary_design] [segmented_design]   (default e5_k175 g5_k175)

Needs out/r26b mc_* for both designs, out/r26c/seeds_ and stats_ (r26c_stats.py) and
out/r26d/carry_<binary>.json (r26d_carry.py).  Writes out/r26e/compare_<seg>.json.

1. Prediction made before the segmented SPICE: the binary design's per-condition carry fit
   (mu, sigma0, sigma_u) with the 2-bit segmented switched-cell counts (r26d_segment seg_b2).
2. Observed: static and 1 ns pass counts of both designs (r26c stats).
3. Paired: the same seed has the same core mismatch draws in both designs, so per-seed |m|
   differences isolate the trim coding.
4. Step tails: local steps over 2 mV (the only way a seed can miss +-1 mV statically) by
   switched-cell class n (r26e_carry).
"""
import json
import math
import os
import statistics
import sys

import r26d_segment as SEG
import r26e_carry as CE

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "r26e")
STATS = os.path.join(HERE, "out", "r26c")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def over_band(mu, sd, t=SEG.BAND):
    """Length-biased P(step > t) for s ~ N(mu, sd^2): a seed lands in a step with probability proportional to s."""
    z = (mu - t) / sd
    return (mu * SEG.ND.cdf(z) + sd * SEG.ND.pdf(z)) / mu


def seeds(design):
    return {(r["cond"][0], r["seed"]): r for r in map(json.loads, open(os.path.join(STATS, "seeds_%s.jsonl" % design)))}


def final_m(r):
    return r.get("fine_m_mv", r["m_mv"])


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "e5_k175"
    seg = sys.argv[2] if len(sys.argv) > 2 else "g5_k175"
    os.makedirs(OUT, exist_ok=True)
    carry = json.load(open(os.path.join(SEG.CARRY, "carry_%s.json" % binary)))
    pred = {}
    for c in carry["conditions"]:
        mu = c["classes"]["1"]["mean_mv"]
        s0, su = c["fit_sigma0_mv"], c["fit_sigma_unit_mv"]
        pred[c["cond"][0]] = {k: c["n_seeds"] * SEG.predict(mu, s0, su, SEG.SCHEMES[k]) for k in ("binary", "seg_b2")}
    stats = {d: {tuple(c["cond"]): c for c in json.load(open(os.path.join(STATS, "stats_%s.json" % d)))["conditions"]}
             for d in (binary, seg)}
    sb, sg = seeds(binary), seeds(seg)
    rows = []
    tot = {"n": 0, "pred_binary": 0.0, "pred_seg": 0.0}
    for cond in stats[seg]:
        b, g = stats[binary][cond], stats[seg][cond]
        keys = sorted(k for k in sg if k[0] == cond[0] and k in sb)
        db = [abs(final_m(sb[k])) for k in keys]
        dg = [abs(final_m(sg[k])) for k in keys]
        row = {
            "cond": list(cond), "n": g["n"],
            "predicted_static_miss": {"binary": round(pred[cond[0]]["binary"], 3),
                                      "segmented": round(pred[cond[0]]["seg_b2"], 3)},
            "static_1mv": {binary: b["static_1mv"], seg: g["static_1mv"]},
            "pass_1mv_1ns": {binary: b["pass_1mv_1ns"], seg: g["pass_1mv_1ns"]},
            "rms_m_mv": {binary: b["rms_m_mv"], seg: g["rms_m_mv"]},
            "max_abs_m_mv": {binary: b["max_abs_m_mv"], seg: g["max_abs_m_mv"]},
            "paired": {"n": len(keys), "seg_smaller": sum(x < y for x, y in zip(dg, db)),
                       "binary_smaller": sum(y < x for x, y in zip(dg, db)),
                       "mean_diff_mv": round(statistics.mean(x - y for x, y in zip(dg, db)), 4)},
        }
        rows.append(row)
        tot["n"] += g["n"]
        tot["pred_binary"] += pred[cond[0]]["binary"]
        tot["pred_seg"] += pred[cond[0]]["seg_b2"]
    pooled = {}
    for d in (binary, seg):
        st = sum(r["static_1mv"][d] for r in rows)
        p1 = sum(r["pass_1mv_1ns"][d] for r in rows)
        pooled[d] = {"static_1mv": st, "static_ci95": wilson(st, tot["n"]),
                     "pass_1mv_1ns": p1, "pass_ci95": wilson(p1, tot["n"])}
    fit = {c["cond"][0]: c for c in carry["conditions"]}
    tails = {}
    for d in (binary, seg):
        res = CE.analyse(d)
        cls = {}
        for c in res["conditions"]:
            f = fit[c["cond"][0]]
            mu, s0, su = f["classes"]["1"]["mean_mv"], f["fit_sigma0_mv"], f["fit_sigma_unit_mv"]
            for n, v in c["classes"].items():
                e = cls.setdefault(n, {"count": 0, "over_2mv": 0, "law_over_2mv": 0.0})
                e["count"] += v["count"]
                e["over_2mv"] += v["over_2mv"]
                e["law_over_2mv"] += v["count"] * over_band(mu, math.sqrt(s0 ** 2 + int(n) * su ** 2))
        for e in cls.values():
            e["law_over_2mv"] = round(e["law_over_2mv"], 3)
        tails[d] = {"classes": cls, "pooled_normalized": res["pooled_normalized"],
                    "over_2mv": sum(e["over_2mv"] for e in cls.values()),
                    "law_over_2mv": round(sum(e["law_over_2mv"] for e in cls.values()), 3)}
    a, b = tails[binary]["over_2mv"], tails[seg]["over_2mv"]
    sign_p = sum(math.comb(a + b, i) for i in range(b + 1)) / 2 ** (a + b)
    out = {"binary": binary, "segmented": seg, "n_seeds": tot["n"],
           "predicted_static_miss_total": {"binary": round(tot["pred_binary"], 3),
                                           "segmented": round(tot["pred_seg"], 3)},
           "pooled": pooled, "rows": rows, "step_tails": tails,
           "tail_sign_test_p_one_sided": round(sign_p, 4)}
    with open(os.path.join(OUT, "compare_%s.json" % seg), "w", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("predicted misses / %d: binary %.2f  segmented %.2f" % (tot["n"], tot["pred_binary"], tot["pred_seg"]))
    print("steps > 2 mV observed / law:", {d: (tails[d]["over_2mv"], tails[d]["law_over_2mv"]) for d in (binary, seg)},
          "sign test p %.4f" % sign_p)
    for d in (binary, seg):
        cls = sorted(tails[d]["classes"].items(), key=lambda t: int(t[0]))
        print(d, pooled[d], {n: (c["count"], c["over_2mv"]) for n, c in cls})
    for r in rows:
        print(r["cond"][0], r["static_1mv"], r["pass_1mv_1ns"], r["rms_m_mv"], r["paired"])


if __name__ == "__main__":
    main()
