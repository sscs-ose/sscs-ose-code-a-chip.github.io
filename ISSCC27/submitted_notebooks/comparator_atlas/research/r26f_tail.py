"""r26f (C): why the Gaussian carry law under-predicts steps over 2 mV by about 1.8x (r26e: binary 10 vs 5.8,
segmented 3 vs 1.6).

Usage: r26f_tail.py [binary_design] [segmented_design]   (default e5_k175 g5_k175); writes out/r26f/tail_<seg>.json

Data: every Monte Carlo seed whose two trim candidates are adjacent codes gives one local step s (mV), with
switched-cell class n (r26e_carry.switched). Three things the r26d/r26e law handled only approximately:
  1. length bias: a seed lands in a step with probability proportional to its width, so the observed density is
     s f(s) / E[s], and its mean exceeds the true mean by var/mean (more for high-variance classes);
  2. quantization: both boundaries come from the same 15/64 mV (q) grid, so a true step s is observed as
     floor(s/q) or floor(s/q)+1 grid units with hat-kernel probabilities (exact for a uniform grid phase);
  3. a systematic per-switched-cell step drift delta: E[s | n] = m_c (1 + delta (n - 1)).
Model per condition c: s ~ N(m_c (1 + delta (n - 1)), s0_c^2 + n su_c^2), observed length-biased and quantized.
Fitted by binned maximum likelihood (closed-form partial Gaussian moments, Nelder-Mead, no scipy).
Tests: likelihood ratio for delta = 0 (shared delta, profile likelihood); out-of-sample prediction of the
other design's over-2 mV count (fit binary, predict segmented, and the reverse, which extrapolates in n);
predicted static misses (r26d formula: P(miss) = sum_codes E[(s - 2)+] / sum_codes E[s]) under each model.
Pooled normalized kurtosis is reported to show the shape is Gaussian (no heavy tail needed).
"""
import collections
import json
import math
import os
import sys

import r26d_carry as C
import r26d_segment as SEG
import r26e_carry as CE

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "r26f")
Q = 15 / 64
BAND = SEG.BAND
SQ2 = math.sqrt(2.0)
IPI = 1 / math.sqrt(2 * math.pi)


def Phi(z):
    return 0.5 * (1 + math.erf(z / SQ2))


def phi(z):
    return IPI * math.exp(-0.5 * z * z) if z * z < 1400 else 0.0


def moments(mu, sd, a, b):
    """Integrals over [a, b] of the N(mu, sd^2) density times 1, s, s^2."""
    za, zb = (a - mu) / sd, (b - mu) / sd
    dP = Phi(zb) - Phi(za)
    pa, pb = phi(za), phi(zb)
    zpa = za * pa if math.isfinite(za) else 0.0
    zpb = zb * pb if math.isfinite(zb) else 0.0
    m0 = dP
    m1 = mu * dP - sd * (pb - pa)
    m2 = (mu * mu + sd * sd) * dP - 2 * mu * sd * (pb - pa) - sd * sd * (zpb - zpa)
    return m0, m1, m2


def p_obs(k, mu, sd, q=Q):
    """P(observed = k grid units) for a length-biased N(mu, sd^2) step: integral of (s / mu) f(s) hat(s/q - k)."""
    lo = moments(mu, sd, (k - 1) * q, k * q)   # weight s/q - (k-1)
    hi = moments(mu, sd, k * q, (k + 1) * q)   # weight (k+1) - s/q
    v = (lo[2] / q - (k - 1) * lo[1]) + ((k + 1) * hi[1] - hi[2] / q)
    return max(v / mu, 1e-300)


def p_over(mu, sd, kmin=9):
    """P(observed >= kmin grid units), i.e. observed step > 2 mV for kmin = 9 (8 q = 1.875, 9 q = 2.109)."""
    ramp = moments(mu, sd, (kmin - 1) * Q, kmin * Q)
    top = moments(mu, sd, kmin * Q, math.inf)
    return (ramp[2] / Q - (kmin - 1) * ramp[1] + top[1]) / mu


def excess(mu, sd, t=BAND):
    z = (mu - t) / sd
    return (mu - t) * Phi(z) + sd * phi(z)


def data(design):
    """{cond: {n: Counter(h)}}, h = step in half-grid units q/2 (odd h: the few seeds refined on a q/2 grid)."""
    out = {}
    for cond, rows in C.load(design).items():
        cls = collections.defaultdict(collections.Counter)
        for r in rows:
            c = sorted(int(x) for x in r["candidates"])
            if len(c) != 2 or c[1] - c[0] != 1:
                continue
            s = abs(r["candidates"][str(c[0])] - r["candidates"][str(c[1])])
            h = round(2 * s / Q)
            assert abs(h * Q / 2 - s) < 1e-9, s
            cls[CE.switched(design, c[0], c[1])][h] += 1
        out[cond[0]] = cls
    return out


def nll(params, cls, delta):
    m, ls0, lsu = params
    s0, su = math.exp(ls0), math.exp(lsu)
    if m <= 0.2:
        return 1e12
    t = 0.0
    for n, hist in cls.items():
        mu, sd = m * (1 + delta * (n - 1)), math.sqrt(s0 * s0 + n * su * su)
        for h, cnt in hist.items():
            p = p_obs(h // 2, mu, sd) if h % 2 == 0 else p_obs(h, mu, sd, Q / 2)
            t -= cnt * math.log(p)
    return t


def nelder_mead(f, x0, step, iters=600, tol=1e-9):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step[j] if j == i else 0.0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        cen = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        xr = [cen[j] + (cen[j] - pts[-1][j]) for j in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [cen[j] + 2 * (cen[j] - pts[-1][j]) for j in range(n)]
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [cen[j] + 0.5 * (pts[-1][j] - cen[j]) for j in range(n)]
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [[pts[0][j] + 0.5 * (p[j] - pts[0][j]) for j in range(n)] for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    i = min(range(n + 1), key=lambda i: vals[i])
    return pts[i], vals[i]


def fit_cond(cls, delta, x0=None):
    if x0 is None:
        k1 = cls[1]
        m = sum(h * c for h, c in k1.items()) / sum(k1.values()) * Q / 2
        x0 = [m, math.log(0.12), math.log(0.08)]
    best = (x0, nll(x0, cls, delta))
    for _ in range(3):  # restarts from the best point
        x, v = nelder_mead(lambda p: nll(p, cls, delta), best[0], [0.05, 0.3, 0.3])
        if v < best[1] - 1e-7:
            best = (x, v)
        else:
            break
    return best


def fit_design(d, delta):
    params, tot = {}, 0.0
    for cond, cls in d.items():
        x, v = fit_cond(cls, delta)
        params[cond] = {"m_mv": x[0], "s0_mv": math.exp(x[1]), "su_mv": math.exp(x[2])}
        tot += v
    return params, tot


def profile(d, lo=-0.02, hi=0.06):
    """Golden-section ML for a shared delta, then the 95 % profile-likelihood interval."""
    cache = {}

    def f(x):
        key = round(x, 6)
        if key not in cache:
            cache[key] = fit_design(d, x)[1]
        return cache[key]

    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c1, c2 = b - g * (b - a), a + g * (b - a)
    for _ in range(26):
        if f(c1) < f(c2):
            b, c2 = c2, c1
            c1 = b - g * (b - a)
        else:
            a, c1 = c1, c2
            c2 = a + g * (b - a)
    dhat = (a + b) / 2
    vhat = f(dhat)

    def bound(x0, x1):  # root of f - vhat - 1.92 between x0 (inside) and x1 (outside)
        for _ in range(22):
            xm = (x0 + x1) / 2
            if f(xm) - vhat < 1.92:
                x0 = xm
            else:
                x1 = xm
        return (x0 + x1) / 2

    return dhat, vhat, [bound(dhat, lo - 0.05), bound(dhat, hi + 0.05)]


def predict_over(target, params, delta):
    t = 0.0
    for cond, cls in target.items():
        p = params[cond]
        for n, hist in cls.items():
            mu = p["m_mv"] * (1 + delta * (n - 1))
            sd = math.sqrt(p["s0_mv"] ** 2 + n * p["su_mv"] ** 2)
            t += sum(hist.values()) * p_over(mu, sd)
    return t


def observed_over(target):
    return sum(c for cls in target.values() for hist in cls.values() for h, c in hist.items() if h * Q / 2 > BAND)


def predict_miss(params, delta, units, n_seeds):
    t = 0.0
    for p in params.values():
        num = den = 0.0
        for n in units:
            mu = p["m_mv"] * (1 + delta * (n - 1))
            sd = math.sqrt(p["s0_mv"] ** 2 + n * p["su_mv"] ** 2)
            num += excess(mu, sd)
            den += mu
        t += n_seeds * num / den
    return t


def poisson_upper(k, lam):
    """P(X >= k) for X ~ Poisson(lam)."""
    return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k))


def kurtosis(d, params, delta):
    zs = []
    for cond, cls in d.items():
        p = params[cond]
        for n, hist in cls.items():
            mu = p["m_mv"] * (1 + delta * (n - 1))
            sd = math.sqrt(p["s0_mv"] ** 2 + n * p["su_mv"] ** 2)
            zs += [(h * Q / 2 - mu) / sd for h, c in hist.items() for _ in range(c)]
    m = sum(zs) / len(zs)
    v = sum((z - m) ** 2 for z in zs) / len(zs)
    return sum((z - m) ** 4 for z in zs) / len(zs) / v ** 2


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "e5_k175"
    seg = sys.argv[2] if len(sys.argv) > 2 else "g5_k175"
    os.makedirs(OUT, exist_ok=True)
    D = {binary: data(binary), seg: data(seg)}
    n_seeds = {x: sum(1 for _ in open(os.path.join(SEG.STATS, f"seeds_{x}.jsonl"))) for x in D}
    units = {binary: SEG.SCHEMES["binary"], seg: SEG.SCHEMES["seg_b2"]}
    res = {"q_mv": Q, "band_mv": BAND, "designs": {}, "transfer": {}}
    fits = {}
    for x, d in D.items():
        p0, v0 = fit_design(d, 0.0)
        dhat, vhat, ci = profile(d)
        p1, _ = fit_design(d, dhat)
        per = {}
        for cond, cls in d.items():
            (x4, v4) = nelder_mead(lambda p: nll(p[:3], cls, p[3]),
                                   [p1[cond]["m_mv"], math.log(p1[cond]["s0_mv"]), math.log(p1[cond]["su_mv"]), dhat],
                                   [0.05, 0.3, 0.3, 0.01], iters=1500)
            per[cond] = round(x4[3], 4)
        fits[x] = {"delta0": p0, "delta": p1, "dhat": dhat}
        lr = 2 * (v0 - vhat)
        res["designs"][x] = {
            "steps": sum(sum(h.values()) for cls in d.values() for h in cls.values()),
            "over_2mv_observed": observed_over(d),
            "delta_hat": round(dhat, 4), "delta_ci95": [round(c, 4) for c in ci],
            "lr_delta0": round(lr, 2), "p_delta0": round(math.erfc(math.sqrt(lr / 2)), 6),
            "delta_per_condition": per,
            "kurtosis_normalized": round(kurtosis(d, p1, dhat), 3),
            "params_delta0": {c: {k: round(v, 4) for k, v in p.items()} for c, p in p0.items()},
            "params_delta": {c: {k: round(v, 4) for k, v in p.items()} for c, p in p1.items()},
        }
    joint = {(x, cond): cls for x, d in D.items() for cond, cls in d.items()}
    v0 = fit_design(joint, 0.0)[1]
    dj, vj, cij = profile(joint)
    lr = 2 * (v0 - vj)
    signs = [v for r in res["designs"].values() for v in r["delta_per_condition"].values()]
    res["joint"] = {"delta_hat": round(dj, 4), "delta_ci95": [round(c, 4) for c in cij], "lr_delta0": round(lr, 2),
                    "p_delta0": round(math.erfc(math.sqrt(lr / 2)), 6),
                    "per_condition_positive": sum(v > 0 for v in signs), "per_condition_total": len(signs),
                    "sign_test_p_one_sided": round(0.5 ** len(signs) * sum(math.comb(len(signs), i) for i in range(
                        sum(v > 0 for v in signs), len(signs) + 1)), 5)}
    print("joint", res["joint"])
    for src in D:
        for tgt in D:
            row = {"observed": observed_over(D[tgt])}
            for name, key in (("delta0", 0.0), ("delta", fits[src]["dhat"])):
                lam = predict_over(D[tgt], fits[src][name], key)
                row[name] = {"predicted": round(lam, 3), "p_ge_observed": round(poisson_upper(row["observed"], lam), 4),
                             "static_miss_predicted": round(predict_miss(fits[src][name], key, units[tgt],
                                                                         n_seeds[tgt] / len(D[tgt])), 3)}
            res["transfer"][f"{src}->{tgt}"] = row
    res["n_seeds"] = n_seeds
    path = os.path.join(OUT, f"tail_{seg}.json")
    with open(path, "w", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for x, r in res["designs"].items():
        print(x, {k: r[k] for k in ("steps", "over_2mv_observed", "delta_hat", "delta_ci95", "lr_delta0", "p_delta0",
                                    "kurtosis_normalized", "delta_per_condition")})
    for k, r in res["transfer"].items():
        print(k, r)


if __name__ == "__main__":
    main()
