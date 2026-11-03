"""r26d: static-miss model of the trim step and a segmentation prediction (no new SPICE).

Usage: r26d_segment.py <design> [<design> ...]   (needs out/r26d/carry_<design>.json and out/r26c/stats)

A seed lands uniformly in its local step s (probability proportional to s), and the nearer code misses the
+-1 mV band with probability max(0, 1 - 2/s). With 31 magnitude transitions t, the static miss fraction is

    sum_t E[(s_t - 2)+] / sum_t E[s_t],  s_t ~ N(mu, sigma0^2 + n_t sigma_u^2)

where n_t is the number of unit cells switched at transition t and mu, sigma0, sigma_u come from the
per-condition carry fit (r26d_carry.py). Binary coding switches n = 2^j - 1 cells when j bits toggle (15 at
7->8, 31 at 15->16). Segmenting the magnitude into B binary LSBs plus thermometer MSB cells of 2^B units
caps n at 2^(B+1) - 1; full thermometer coding switches one unit per step. "no_quant" drops sigma0 (mostly
the 0.2 mV bisection quantization of the measured candidates) as an optimistic bound.
"""
import json
import math
import os
import sys
from statistics import NormalDist

ND = NormalDist()
BAND = 2.0
HERE = os.path.dirname(os.path.abspath(__file__))
CARRY = os.path.join(HERE, "out", "r26d")
STATS = os.path.join(HERE, "out", "r26c")


def excess(mu, sd, t=BAND):
    z = (mu - t) / sd
    return (mu - t) * ND.cdf(z) + sd * ND.pdf(z)


def units_binary(c):
    return 2 ** bin(c ^ (c + 1)).count("1") - 1


def units_segmented(c, b):
    low = (1 << b) - 1
    return 2 ** (b + 1) - 1 if (c & low) == low else units_binary(c)


SCHEMES = {
    "binary": [units_binary(c) for c in range(31)],
    "seg_b3": [units_segmented(c, 3) for c in range(31)],
    "seg_b2": [units_segmented(c, 2) for c in range(31)],
    "seg_b1": [units_segmented(c, 1) for c in range(31)],
    "thermometer": [1] * 31,
}


def predict(mu, s0, su, units):
    return sum(excess(mu, math.sqrt(s0 ** 2 + n * su ** 2)) for n in units) / (len(units) * mu)


def observed(design):
    path = os.path.join(STATS, "seeds_%s.jsonl" % design)
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path):
        r = json.loads(line)
        key = r["cond"][0]
        n, miss = out.get(key, (0, 0))
        m = r.get("fine_m_mv", r["m_mv"])
        out[key] = (n + 1, miss + (not (r["covered"] and abs(m) <= 1.0)))
    return out


def analyse(design):
    carry = json.load(open(os.path.join(CARRY, "carry_%s.json" % design)))
    obs = observed(design)
    rows = []
    for c in carry["conditions"]:
        mu = c["classes"]["1"]["mean_mv"]
        s0, su = c["fit_sigma0_mv"], c["fit_sigma_unit_mv"]
        n = c["n_seeds"]
        row = {"cond": c["cond"], "n_seeds": n, "mu_mv": mu, "sigma0_mv": s0, "sigma_unit_mv": su,
               "observed_static_miss": obs.get(c["cond"][0], (n, None))[1], "predicted_miss": {},
               "predicted_miss_no_quant": {}}
        for name, units in SCHEMES.items():
            row["predicted_miss"][name] = n * predict(mu, s0, su, units)
            row["predicted_miss_no_quant"][name] = n * predict(mu, 0.0, su, units)
        rows.append(row)
    return {"design": design, "band_mv": BAND, "rows": rows}


def main():
    os.makedirs(CARRY, exist_ok=True)
    for design in sys.argv[1:]:
        res = analyse(design)
        with open(os.path.join(CARRY, "segment_%s.json" % design), "w", newline="\n") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
            fh.write("\n")
        for r in res["rows"]:
            print(design, r["cond"][0], "obs", r["observed_static_miss"],
                  " ".join("%s %.2f/%.2f" % (k, v, r["predicted_miss_no_quant"][k])
                           for k, v in r["predicted_miss"].items()))


if __name__ == "__main__":
    main()
