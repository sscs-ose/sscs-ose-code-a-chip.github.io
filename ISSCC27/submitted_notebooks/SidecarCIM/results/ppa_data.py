"""Loaders joining ppa.csv with accuracy JSON, one record per circuit."""
import csv
import os

import numpy as np

import plot_common as pc


def load_csv(name):
    with open(os.path.join(pc.HERE, name)) as f:
        return list(csv.DictReader(f))


def ppa():
    out = {}
    for r in load_csv("ppa.csv"):
        d = {}
        for k, v in r.items():
            try:
                d[k] = float(v)
            except ValueError:
                d[k] = v
        out[r["design"]] = d
    return out


def _ppl(nll):
    return float(np.exp(np.mean(nll)))


def _paired(nll, fp):
    nll, fp = np.asarray(nll), np.asarray(fp)
    d = nll - fp
    se = d.std(ddof=1) / np.sqrt(len(d))
    p = _ppl(nll)
    return p - _ppl(fp), float(p * se)


def _diff(a, b):
    """Paired difference of perplexities: (dppl, jackknife SE, t on dNLL)."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    loo = np.array([_ppl(np.delete(a, i)) - _ppl(np.delete(b, i))
                    for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((loo - loo.mean()) ** 2).sum()))
    d = a - b
    t = float(d.mean() / (d.std(ddof=1) / np.sqrt(n)))
    return _ppl(a) - _ppl(b), se, t


def extras():
    """Paired stats from python/out/extras.json (per-window NLL, 8192 tok)."""
    U = pc.load("extras.json")["units"]
    fp = U["fp32"]["nll"]
    out = {"gpt2_naive": _paired(U["w4a4_naive@8192"]["nll"], fp)}
    out["gpt2_side_vs_tile"] = _diff(U["side_mag_k2_wclip@8192"]["nll"],
                                     U["tile_wclip@8192"]["nll"])
    out["qwen_side_vs_tile"] = _diff(
        U["qwen_side_mag_k2_wclip@8192"]["nll"],
        U["qwen_tile_wclip@8192"]["nll"])
    mag = U["side_mag_k2_wclip@8192"]["nll"]
    for r in ("greedy", "hybrid"):
        out["gpt2_%s_vs_mag" % r] = _diff(
            U["side_%s_k2_wclip@8192" % r]["nll"], mag)
    out["calib_slices"] = {
        off: {r: _ppl(U["side_%s_k2_wclip@2048@calib%d" % (r, off)]["nll"])
              for r in ("mag", "greedy", "hybrid")} for off in (1024, 2048)}
    return out


REF = "SidecarCIM+wclip k2,VB12"   # fulltest.json reference scheme
# Headline build: merge output register (PIPE_MERGE=1) and 3-bit shift S
# (SBITS=3). S <= 7 in every column of both models (srange.json), so its
# accuracy is bit-identical to REF. Earlier builds stay as variants.
HEAD = "sidecarcim_top_ff_pipe_s3"
PIPE4 = "sidecarcim_top_ff_pipe"      # PIPE_MERGE=1, 4-bit S
NOPIPE = "sidecarcim_top_ff"          # PIPE_MERGE=0 (zero latency), 4-bit S
PAR = "sidecarcim_top_ff_par"         # PARALLEL=1, PIPE_MERGE=0


def fulltest():
    """Full WikiText-2 test split (GPT-2 280, Qwen 292 windows):
    {model: {scheme: row}} from fulltest.json plus the dense W7A4 and
    W4A8 rows of fulltest_extra.json (same windows, same reference).
    Rows carry d_vs_fp32, se_vs_fp32 (paired SE) and vs_sidecar (paired
    t-test p, TOST +-margin, 90 % CI), all against REF."""
    ft = pc.load("fulltest.json")
    out = {m: {r["scheme"]: r for r in t["rows"]}
           for m, t in ft["tables"].items()}
    fx = pc.load("fulltest_extra.json")
    for m, t in fx["tables"].items():
        rows = {r["scheme"]: r for r in t["rows"]}
        # same reference run: the SidecarCIM loss must agree
        d_ref = rows[REF]["d_vs_fp32"] - out[m][REF]["d_vs_fp32"]
        assert abs(d_ref) < 1e-3, m
        for s in ("W7A4+mig+wclip", "W4A8+mig+wclip"):
            out[m][s] = rows[s]
    for m in out:
        assert REF in out[m], (m, REF)
    return out


def circuits():
    """Ordered list of laid-out circuits with ppa row and accuracy.

    g / q = (perplexity increase over FP32, paired SE) on the full test
    split (fulltest.json); g_vs / q_vs = the paired comparison against
    SidecarCIM (None for SidecarCIM itself). MAC baseline and 4-bit DCIM
    compute the same 4-bit dot products, so both carry the 4-bit +
    migration + clip accuracy; g_naive / q_naive = naive 4-bit, which was
    only run on the 8-window (8192-token) evaluation (extras/qwen.json).
    """
    p = ppa()
    ft = fulltest()
    q8 = pc.by_scheme(pc.load("qwen.json")["rows"])
    naive = (extras()["gpt2_naive"], (q8["W4A4"]["d_all"],
                                      q8["W4A4"]["se_all"]))

    def acc(s):
        out = []
        for m in ("gpt2", "qwen"):
            r = ft[m][s]
            out += [(r["d_vs_fp32"], r["se_vs_fp32"]), r.get("vs_sidecar")]
        return out

    W4 = "W4A4+mig+wclip"
    rows = [
        ("MAC baseline", "mac_baseline", W4, True),
        ("4-bit DCIM (FF)", "dcim_core_ff", W4, True),
        ("Dense W6A4 (FF)", "dcim_w6a4_ff", "W6A4+mig+wclip", False),
        ("SidecarCIM (FF, merge reg., 3-bit S)", HEAD, REF, False),
        ("SidecarCIM variant: merge reg., 4-bit S", PIPE4, REF, False),
        ("SidecarCIM variant: no merge reg.", NOPIPE, REF, False),
        ("SidecarCIM variant: parallel, no merge reg.", PAR, REF, False),
        ("Dense W7A4 (FF)", "dcim_w7a4_ff", "W7A4+mig+wclip", False),
        ("Dense W8A4 (FF)", "dcim_w8a4_ff", "W8A4+mig+wclip", False),
        ("Dense W4A8 (FF)", "dcim_w4a8_ff", "W4A8+mig+wclip", False),
        ("8-bit DCIM (FF)", "dcim_8bit_ff", "W8A8", False),
    ]
    out = []
    for lab, key, sch, nv in rows:
        if key not in p:          # designs missing from ppa.csv are skipped
            continue
        g, gv, q, qv = acc(sch)
        out.append(dict(label=lab, key=key, ppa=p[key], scheme=sch, g=g,
                        q=q, g_vs=gv, q_vs=qv,
                        g_naive=naive[0] if nv else None,
                        q_naive=naive[1] if nv else None))
    return out


def dense_line(cs, xkey, idx):
    """Straight line through dense W6A4 and W8A4 in (cost, ppl loss):
    (line value at SidecarCIM's cost, SidecarCIM's loss, fraction of the
    W6->W8 cost step at which SidecarCIM sits). W7A4 is a measured point
    in the tables but not part of this line."""
    w6, w8, sc = (cs[k] for k in ("dcim_w6a4_ff", "dcim_w8a4_ff", HEAD))
    x6, x8, xs = (c["ppa"][xkey] for c in (w6, w8, sc))
    y6, y8 = w6[idx][0], w8[idx][0]
    fr = (xs - x6) / (x8 - x6)
    return y6 + fr * (y8 - y6), sc[idx][0], fr


def derived():
    """Gap-closing and same-throughput numbers of SidecarCIM.

    Accuracy-gap closure on the full test: from 4-bit DCIM + migration +
    clip to W8A8. Cost-gap shares: from 4-bit to 8-bit DCIM. Same
    throughput rivals: dense W6A4, W7A4 and W8A4 (one MVM per 5 cycles
    back to back, like SidecarCIM, which has 5 cycles of latency)."""
    cs = {c["key"]: c for c in circuits()}
    d4, sc, d8 = (cs["dcim_core_ff"], cs[HEAD],
                  cs["dcim_8bit_ff"])
    out = {}
    for m, idx in (("GPT-2", "g"), ("Qwen", "q")):
        a4, a8, asc = d4[idx][0], d8[idx][0], sc[idx][0]
        out[("mc", m)] = 100 * (a4 - asc) / (a4 - a8)
    E, A = "energy_per_dot_pj_est", "area_um2"
    out["energy"] = 100 * (sc["ppa"][E] - d4["ppa"][E]) / \
        (d8["ppa"][E] - d4["ppa"][E])
    out["area"] = 100 * (sc["ppa"][A] - d4["ppa"][A]) / \
        (d8["ppa"][A] - d4["ppa"][A])
    if "dcim_w8a4_ff" in cs and "dcim_w6a4_ff" in cs:
        w6, w8 = cs["dcim_w6a4_ff"], cs["dcim_w8a4_ff"]
        w7 = cs["dcim_w7a4_ff"]
        for k, nm in ((E, "energy"), (A, "area")):
            out["w8_over_sc_" + nm] = 100 * (w8["ppa"][k] / sc["ppa"][k] - 1)
            out["w7_over_sc_" + nm] = 100 * (w7["ppa"][k] / sc["ppa"][k] - 1)
            out["sc_over_w6_" + nm] = 100 * (sc["ppa"][k] / w6["ppa"][k] - 1)
            for m, idx in (("GPT-2", "g"), ("Qwen", "q")):
                out[("line", nm, m)] = dense_line(cs, k, idx)
        for m, idx in (("GPT-2", "g"), ("Qwen", "q")):
            out[("vs_w6", m)] = w6[idx + "_vs"]
            out[("vs_w8", m)] = w8[idx + "_vs"]
            out[("vs_w7", m)] = w7[idx + "_vs"]
    return out
