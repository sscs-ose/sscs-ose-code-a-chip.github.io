"""r26e: local trim step versus switched unit cells, binary against segmented.

Usage: r26e_carry.py <design> [<design> ...]

Like r26d_carry, but classes are the number n of unit cells that switch
between |c| and |c|+1, so binary (e5_*) and segmented (g5_*) designs share
one axis.  Binary: n = 2^j - 1.  Segmented (2 binary LSBs + thermometer
segments of 4 units): n = 1 or 3 inside a segment, 3 + 4 = 7 at every
segment boundary, so the largest binary classes (15, 31) disappear.
"""
import collections
import json
import os
import statistics
import sys

import r26d_carry as C

OUT = os.path.join(C.HERE, "out", "r26e")


def switched(design, a, b):
    lo = min(abs(a), abs(b))
    if design.startswith("g5"):
        return 7 if lo % 4 == 3 else (3 if lo % 2 == 1 else 1)
    return 2 ** C.toggled(a, b) - 1


def fit(classes):
    xs, ys, ws = [], [], []
    for n, steps in classes.items():
        if len(steps) < 5:
            continue
        xs.append(n)
        ys.append(statistics.pvariance(steps))
        ws.append(len(steps))
    sw = sum(ws)
    mx = sum(w * x for w, x in zip(ws, xs)) / sw
    my = sum(w * y for w, y in zip(ws, ys)) / sw
    sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
    sxy = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys))
    b = sxy / sxx
    return my - b * mx, b


def analyse(design):
    out = {"design": design, "conditions": []}
    pooled = collections.defaultdict(list)
    for cond, rows in C.load(design).items():
        classes = collections.defaultdict(list)
        for r in rows:
            c = sorted(int(k) for k in r["candidates"])
            if len(c) != 2 or c[1] - c[0] != 1:
                continue
            step = abs(r["candidates"][str(c[0])] - r["candidates"][str(c[1])])
            classes[switched(design, c[0], c[1])].append(step)
        mean1 = statistics.mean(classes[1])
        for n, v in classes.items():
            pooled[n].extend(s / mean1 for s in v)
        out["conditions"].append({
            "cond": list(cond),
            "n_seeds": len(rows),
            "classes": {
                str(n): {
                    "count": len(v),
                    "mean_mv": statistics.mean(v),
                    "sd_mv": statistics.pstdev(v),
                    "max_mv": max(v),
                    "over_2mv": sum(s > 2.0 for s in v),
                }
                for n, v in sorted(classes.items())
            },
        })
    a, b = fit(pooled)
    out["pooled_normalized"] = {
        "classes": {
            str(n): {"count": len(v), "sd_lsb": statistics.pstdev(v),
                     "max_lsb": max(v)}
            for n, v in sorted(pooled.items())
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
        for n, c in p["classes"].items():
            print("  n=%2s count=%3d sd=%.3f max=%.2f LSB" % (
                n, c["count"], c["sd_lsb"], c["max_lsb"]))


if __name__ == "__main__":
    main()
