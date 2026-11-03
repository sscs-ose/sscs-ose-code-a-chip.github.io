"""r26d: local trim step versus the number of toggled magnitude bits.

Usage: r26d_carry.py <design> [<design> ...]

Each Monte Carlo seed lands between two adjacent codes (its two candidates).
The local step is the offset difference between them.  Moving between |c| and
|c|+1 toggles j magnitude bits and switches n = 2^j - 1 unit cells, so with
independent unit-cell mismatch the step variance should grow as
sigma0^2 + n * sigma_u^2.  sigma0 holds the bisection quantization
(2 * tol^2 / 12) and any common term.  Seeds land in a step with probability
proportional to its width, so the class means are length-biased.
"""
import collections
import glob
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "r26d")
SRC = os.path.join(HERE, "out", "r26b")


def toggled(a, b):
    return bin(abs(a) ^ abs(b)).count("1")


def load(design):
    conds = {}
    for f in sorted(glob.glob(os.path.join(SRC, "mc_*_%s.jsonl" % design))):
        rows = [json.loads(line) for line in open(f)]
        if len(rows) < 100:  # incomplete run
            continue
        conds[tuple(rows[0]["cond"])] = rows
    return conds


def fit(classes):
    # weighted least squares of var = a + b * n, weights = count
    xs, ys, ws = [], [], []
    for j, steps in classes.items():
        if len(steps) < 5:
            continue
        xs.append(2 ** j - 1)
        ys.append(statistics.pvariance(steps))
        ws.append(len(steps))
    sw = sum(ws)
    mx = sum(w * x for w, x in zip(ws, xs)) / sw
    my = sum(w * y for w, y in zip(ws, ys)) / sw
    sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
    sxy = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys))
    b = sxy / sxx
    a = my - b * mx
    return a, b


def analyse(design):
    out = {"design": design, "conditions": []}
    pooled = collections.defaultdict(list)
    for cond, rows in load(design).items():
        classes = collections.defaultdict(list)
        for r in rows:
            c = sorted(int(k) for k in r["candidates"])
            if len(c) != 2 or c[1] - c[0] != 1:
                continue
            step = abs(r["candidates"][str(c[0])] - r["candidates"][str(c[1])])
            classes[toggled(c[0], c[1])].append(step)
        mean1 = statistics.mean(classes[1])
        for j, v in classes.items():
            pooled[j].extend(s / mean1 for s in v)
        a, b = fit(classes)
        out["conditions"].append({
            "cond": list(cond),
            "n_seeds": len(rows),
            "classes": {
                str(j): {
                    "units": 2 ** j - 1,
                    "count": len(v),
                    "mean_mv": statistics.mean(v),
                    "sd_mv": statistics.pstdev(v),
                    "max_mv": max(v),
                    "over_2mv": sum(s > 2.0 for s in v),
                }
                for j, v in sorted(classes.items())
            },
            "fit_sigma0_mv": max(a, 0.0) ** 0.5,
            "fit_sigma_unit_mv": max(b, 0.0) ** 0.5,
        })
    a, b = fit(pooled)
    out["pooled_normalized"] = {
        "classes": {
            str(j): {"count": len(v), "sd_lsb": statistics.pstdev(v)}
            for j, v in sorted(pooled.items())
        },
        "fit_sigma0_lsb": max(a, 0.0) ** 0.5,
        "fit_sigma_unit_lsb": max(b, 0.0) ** 0.5,
    }
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for design in sys.argv[1:]:
        res = analyse(design)
        path = os.path.join(OUT, "carry_%s.json" % design)
        with open(path, "w", newline="\n") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
            fh.write("\n")
        p = res["pooled_normalized"]
        print(design, "sigma0 %.3f LSB  sigma_unit %.3f LSB" % (
            p["fit_sigma0_lsb"], p["fit_sigma_unit_lsb"]))
        for j, c in p["classes"].items():
            print("  j=%s n=%3d sd=%.3f LSB" % (j, c["count"], c["sd_lsb"]))


if __name__ == "__main__":
    main()
