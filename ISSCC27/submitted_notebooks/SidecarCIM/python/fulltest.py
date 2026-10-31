"""The main schemes on the full WikiText-2 test set, with paired tests and TOST.

Usage: python fulltest.py gpt2          all full 1024-token windows of the test split
       python fulltest.py time_qwen     1-window timing of Qwen2.5-0.5B (FP32 + one scheme)
       python fulltest.py qwen N        N evenly spaced windows of the Qwen test split
       python fulltest.py report        tables + stats from out/fulltest.json (no evals)
Each stage resumes from out/fulltest.json (per-window NLL saved every CHUNK windows).
Protocol = alternatives.py: GPT-2 all 12 c_fc; Qwen all 24 gate+up; calib = first 512
WikiText-2 train tokens; alpha picked on calib layer error per layer; integer path golden-checked.
Eval = consecutive non-overlapping 1024-token windows of the whole test split (the partial last
window is dropped); per-window mean NLL. The first 8 GPT-2 windows are the 8192 tokens used by
alternatives.json / novelty.json (checked).
Stats vs the reference (SidecarCIM+wclip k2,VB12), paired over windows, d_i = NLL_i - NLL_ref,i:
  t-test: t = mean(d) / (sd(d)/sqrt(n)), df = n-1, two-sided p (Student t).
  TOST: margin M = 0.25 ppl (fixed before any full-test data was seen). |ppl - ppl_ref| < M
  <=> mean(d) in (ln(1 - M/P), ln(1 + M/P)), P = ref ppl; two one-sided t-tests, p = max of the two.
  Verdict "equivalent within +-0.25 ppl (TOST p<0.05)" if p < 0.05, else "not shown equivalent".
  90 % CI of the ppl difference = P*(exp(mean(d) +- t_.95 se) - 1) (TOST <=> CI inside +-M).
"""
import json
import math
import os
import sys
import time

import numpy as np

from extras import diff_stats
from golden import SPEC
from llm_layer import CALIB_TOKENS, OUT, WIDE, capture, fc_names, golden_check, load_wikitext
from novelty_study import B, encode_pick2, paired, ppl, window_nll

FILE = OUT / "fulltest.json"
K = SPEC["outlier"]["budget_per_output"]
MARGIN = 0.25                    # ppl; fixed before the full-test run
ALPHA = 0.05
CTX = 1024
CHUNK = 16                       # windows per saved chunk
REF = "SidecarCIM+wclip k2,VB12"
RIVAL = "W4A4+mig+tile+wclip"
# (name, cfg); order = priority
SCHEMES = [
    (REF, dict(B, k=K, wclip=True, vb=12)),
    (RIVAL, dict(B, tile=True, wclip=True)),
    ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True)),
    ("W6A4+mig+wclip", dict(B, wbits=6, wclip=True)),
    ("W4A4+mig+wclip", dict(B, wclip=True)),
    ("W8A8", dict(B, wbits=WIDE, abits=WIDE, alpha=None)),
    ("SidecarCIM+wclip k2,VB16", dict(B, k=K, wclip=True, vb=16)),
]


# ---------------- Student t (no scipy) ----------------

def _betacf(a, b, x):
    """Continued fraction for the regularized incomplete beta (Lentz)."""
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        for num in (m * (b - m) * x / ((a + m2 - 1) * (a + m2)),
                    -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))):
            d = 1.0 + num * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + num / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < 1e-15:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + \
        b * math.log(1.0 - x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lb) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lb) * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    """P(T <= t), Student t with df degrees of freedom."""
    tail = 0.5 * betainc(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t > 0 else tail


def t_sf(t, df):
    """P(T > t), accurate in the far tail."""
    tail = 0.5 * betainc(df / 2.0, 0.5, df / (df + t * t))
    return tail if t > 0 else 1.0 - tail


def t_ppf(p, df):
    """Quantile of Student t (bisection)."""
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def compare(a, ref, margin=MARGIN):
    """Paired t-test and TOST of scheme a vs ref (per-window NLL arrays)."""
    a, ref = np.asarray(a, float), np.asarray(ref, float)
    n = len(a)
    d = a - ref
    m, se = float(d.mean()), float(d.std(ddof=1) / np.sqrt(n))
    df = n - 1
    P = ppl(ref)
    t = m / se
    p = 2.0 * t_sf(abs(t), df)
    lo, hi = math.log(1.0 - margin / P), math.log(1.0 + margin / P)
    p_lo = t_sf((m - lo) / se, df)              # H0: diff <= -M
    p_hi = t_sf(-(m - hi) / se, df)             # H0: diff >= +M
    p_tost = max(p_lo, p_hi)
    tq = t_ppf(1.0 - ALPHA, df)
    ci = [P * (math.exp(m - tq * se) - 1.0), P * (math.exp(m + tq * se) - 1.0)]
    js = diff_stats(a, ref)
    return {"windows": n, "df": df, "dppl": round(ppl(a) - P, 4),
            "se_jackknife": js["se_jackknife"], "mean_dnll": round(m, 6),
            "se_dnll": round(se, 6), "t": round(t, 3), "p_two_sided": float(f"{p:.4g}"),
            "tost_margin_ppl": margin, "tost_p": float(f"{p_tost:.4g}"),
            "ci90_dppl": [round(c, 4) for c in ci],
            "equivalent": bool(p_tost < ALPHA),
            "verdict": (f"equivalent within ±{margin} ppl (TOST p<{ALPHA})" if p_tost < ALPHA
                        else "not shown equivalent"),
            "different": bool(p < ALPHA)}


def _selftest():
    # Cauchy (df=1): P(|T| > t) = 1 - 2 atan(t) / pi
    for t in (0.5, 2.0, 7.0):
        assert abs(2 * (1 - t_cdf(t, 1)) - (1 - 2 * math.atan(t) / math.pi)) < 1e-10
    # df=2 closed form: cdf = 1/2 + t / (2 sqrt(2 + t^2))
    for t in (-3.0, 0.3, 4.0):
        assert abs(t_cdf(t, 2) - (0.5 + t / (2 * math.sqrt(2 + t * t)))) < 1e-10
    # df=7 critical value 2.3646 (two-sided 0.05); large df -> normal
    assert abs(t_ppf(0.975, 7) - 2.364624) < 1e-5
    assert abs(t_cdf(1.959964, 10 ** 6) - 0.975) < 1e-5
    for t in (-2.0, 0.7, 3.0, 40.0):
        assert abs(t_sf(t, 9) + t_cdf(t, 9) - 1.0) < 1e-12
    assert 0 < t_sf(40.0, 9) < 1e-10                       # far tail does not underflow to 0
    rng = np.random.default_rng(1)
    ref = 3.4 + rng.normal(0, 0.1, 300)
    same = ref + rng.normal(0, 0.002, 300)       # tiny paired noise: equivalent
    far = ref + 0.05 + rng.normal(0, 0.002, 300)  # ~ +1.5 ppl: different, not equivalent
    c1, c2 = compare(same, ref), compare(far, ref)
    assert c1["equivalent"] and not c1["different"] and c1["ci90_dppl"][0] > -MARGIN
    assert not c2["equivalent"] and c2["different"] and c2["dppl"] > 1.0
    # TOST <=> 90 % CI inside the margin
    for c in (c1, c2):
        assert c["equivalent"] == (-MARGIN < c["ci90_dppl"][0] and c["ci90_dppl"][1] < MARGIN)
    print("fulltest self-test passed (t cdf/ppf, paired t, TOST)")


# ---------------- storage ----------------

def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


def run_unit(res, key, wins, idx, nll_fn, t0):
    """Evaluate windows idx (resume from saved prefix), saving every CHUNK windows."""
    U = res["units"]
    u = U.setdefault(key, {"nll": [], "win_idx": []})
    done = len(u["nll"])
    assert u["win_idx"] == list(idx[:done])
    for s in range(done, len(idx), CHUNK):
        part = list(idx[s:s + CHUNK])
        u["nll"] += nll_fn([wins[i] for i in part]).tolist()
        u["win_idx"] += [int(i) for i in part]
        save(res)
        print(f"    {key}: {len(u['nll'])}/{len(idx)} windows ({time.time() - t0:.0f} s)",
              flush=True)
    return u


# ---------------- GPT-2 ----------------

def stage_gpt2():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    torch.set_num_threads(6)
    t0 = time.time()
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    assert model.config.n_positions == CTX
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    old = tok(load_wikitext("test", 80000))["input_ids"][:8192]
    assert ids[:8192] == old                     # first 8 windows = alternatives.json eval
    ev = torch.tensor(ids)
    nw = len(ids) // CTX
    wins = [ev[i * CTX:(i + 1) * CTX] for i in range(nw)]
    idx = list(range(nw))
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    names = fc_names(model)
    h0 = SPEC["workload"]["layer"]
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    Xc = capture(model, names, [torch.tensor(ca)])
    Xe0 = capture(model, [h0], wins[:1])[h0]
    res = load()
    res["gpt2_meta"] = {"test_tokens": len(ids), "windows": nw, "ctx": CTX,
                        "dropped_tail_tokens": len(ids) - nw * CTX}
    print(f"GPT-2: {len(ids)} test tokens -> {nw} windows of {CTX}", flush=True)
    t1 = time.time()
    run_unit(res, "gpt2|FP32", wins, idx, lambda w: window_nll(model, w), t0)
    res["units"]["gpt2|FP32"]["sec"] = round(time.time() - t1, 1)
    save(res)
    for name, cfg in SCHEMES:
        key = "gpt2|" + name
        u = res["units"].get(key)
        if u and len(u["nll"]) == nw:
            continue
        t1 = time.time()
        encs, alphas = {}, []
        for n in names:
            e = encode_pick2(Ws[n], bs[n], Xc[n], cfg)
            golden_check(e, Xc[n], [0, 255, CALIB_TOKENS - 1])
            if n == h0:
                golden_check(e, Xe0, [0, 511, 1023])
            encs[n] = e
            alphas.append(e["alpha"])
        te = time.time() - t1
        u = run_unit(res, key, wins, idx, lambda w, e=encs: window_nll(model, w, e), t0)
        u["alphas"], u["encode_sec"] = alphas, round(te, 1)
        u["sec"] = round(time.time() - t1, 1)
        save(res)
        print(f"  {key} done ({u['sec']:.0f} s, encode {te:.0f} s)", flush=True)
        del encs
    report()


# ---------------- Qwen ----------------

def qwen_setup():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import qwen_eval as q
    torch.set_num_threads(q.THREADS)
    tok = AutoTokenizer.from_pretrained(q.MODEL)
    model = AutoModelForCausalLM.from_pretrained(q.MODEL, dtype=torch.float32).eval()
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    old = tok(load_wikitext("test", 80000))["input_ids"][:8192]
    assert ids[:8192] == old
    ev = torch.tensor(ids)
    nw = len(ids) // q.WIN
    wins = [ev[i * q.WIN:(i + 1) * q.WIN] for i in range(nw)]
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    L = model.config.num_hidden_layers
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    Xc = capture(model, names, [torch.tensor(ca)])
    return q, model, ids, wins, [Xc[n] for n in names], L


def qwen_encode(q, model, Xc, L, cfg):
    encs, alphas = {}, []
    for i in range(L):
        W, b = q.layer_weights(model, i)
        e = q.pick_encode(W, b, Xc[i], cfg)
        golden_check(e, Xc[i], [0, 100, CALIB_TOKENS - 1])
        alphas.append(e["alpha"])
        encs[i] = q.slim(e)
        q.trim()
    return encs, alphas


def stage_time_qwen():
    """Time 1 window for FP32 and the reference scheme; estimate the full-set run."""
    t0 = time.time()
    q, model, ids, wins, Xc, L = qwen_setup()
    t_setup = time.time() - t0
    t1 = time.time()
    q.window_nll(model, wins[:1])
    t_fp = time.time() - t1
    t1 = time.time()
    encs, _ = qwen_encode(q, model, Xc, L, dict(SCHEMES)[REF])
    t_enc = time.time() - t1
    t1 = time.time()
    q.window_nll(model, wins[:1], encs)
    t_q = time.time() - t1
    n_s = len(SCHEMES)
    est = {"test_tokens": len(ids), "windows": len(wins), "setup_sec": round(t_setup, 1),
           "fp32_sec_per_window": round(t_fp, 2), "quant_sec_per_window": round(t_q, 2),
           "encode_sec_per_scheme": round(t_enc, 1), "schemes": n_s,
           "peak_rss_gb": round(q.peak_gb(), 2)}
    est["full_set_hours"] = round((len(wins) * (t_fp + n_s * t_q) + n_s * t_enc) / 3600, 2)
    est["hours_per_100_windows"] = round(100 * (t_fp + n_s * t_q) / 3600, 2)
    res = load()
    res["qwen_timing"] = est
    save(res)
    print(json.dumps(est, indent=1))


def stage_qwen(n_win):
    t0 = time.time()
    q, model, ids, wins, Xc, L = qwen_setup()
    nw = len(wins)
    n_win = min(n_win, nw)
    idx = sorted({int(round(v)) for v in np.linspace(0, nw - 1, n_win)})
    res = load()
    meta = res.get("qwen_meta")
    if meta:                                    # resume with the same window set
        assert meta["win_idx"] == idx, "window set changed; use the stored N"
    res["qwen_meta"] = {"test_tokens": len(ids), "windows_total": nw, "ctx": q.WIN,
                        "windows_used": len(idx), "win_idx": idx,
                        "selection": "evenly spaced over the test split (np.linspace)"}
    save(res)
    print(f"Qwen: {len(ids)} test tokens -> {nw} windows; using {len(idx)}", flush=True)
    t1 = time.time()
    u = run_unit(res, "qwen|FP32", wins, idx, lambda w: q.window_nll(model, w), t0)
    u["sec"] = round(time.time() - t1, 1)
    save(res)
    for name, cfg in SCHEMES:
        key = "qwen|" + name
        u = res["units"].get(key)
        if u and len(u["nll"]) == len(idx):
            continue
        t1 = time.time()
        encs, alphas = qwen_encode(q, model, Xc, L, cfg)
        te = time.time() - t1
        u = run_unit(res, key, wins, idx, lambda w, e=encs: q.window_nll(model, w, e), t0)
        u["alphas"], u["encode_sec"] = alphas, round(te, 1)
        u["sec"] = round(time.time() - t1, 1)
        save(res)
        print(f"  {key} done ({u['sec']:.0f} s, encode {te:.0f} s, peak RSS "
              f"{q.peak_gb():.2f} GB)", flush=True)
        del encs
        q.trim()
    report()


# ---------------- report ----------------

def model_table(U, m):
    fp = U.get(m + "|FP32")
    ref = U.get(m + "|" + REF)
    if not fp or not ref:
        return None
    n = min(len(fp["nll"]), len(ref["nll"]))
    fpn = np.array(fp["nll"][:n])
    rows = [{"scheme": "FP32", "windows": n, "ppl": round(ppl(fpn), 4)}]
    for name, _ in SCHEMES:
        u = U.get(m + "|" + name)
        if not u or len(u["nll"]) < n:
            continue
        a = np.array(u["nll"][:n])
        d, se = paired(a, fpn)
        row = {"scheme": name, "windows": n, "ppl": round(ppl(a), 4), "d_vs_fp32": d,
               "se_vs_fp32": se, "alpha_layer0": u["alphas"][0] if "alphas" in u else None}
        if name != REF:
            row["vs_sidecar"] = compare(a, ref["nll"][:n])
        rows.append(row)
    vs_fp = compare(fpn, ref["nll"][:n])
    rows[0]["vs_sidecar"] = vs_fp
    return {"windows": n, "win_idx_first_last": [fp["win_idx"][0], fp["win_idx"][n - 1]],
            "rows": rows}


def first8(U, m):
    """df=7 stats on the 8 alternatives.json windows (windows 0..7 of the test split)."""
    ref = U.get(m + "|" + REF)
    if not ref or ref["win_idx"][:8] != list(range(8)):
        return None
    out = {}
    for name, _ in [("FP32", None)] + SCHEMES:
        u = U.get(m + "|" + name)
        if name != REF and u and u["win_idx"][:8] == list(range(8)):
            out[name] = compare(u["nll"][:8], ref["nll"][:8])
    return out


def fmt(tab, title):
    lines = [f"\n{title}: {tab['windows']} windows of {CTX} tokens; reference = {REF}",
             f"{'scheme':26s} {'ppl':>8s} {'d vs FP32':>16s} {'diff vs sidecar':>18s} "
             f"{'90% CI':>18s} {'t':>7s} {'p':>9s} {'TOST p':>9s}  verdict"]
    for r in tab["rows"]:
        dfp = f"{r['d_vs_fp32']:+7.3f}±{r['se_vs_fp32']:.3f}" if "d_vs_fp32" in r else ""
        v = r.get("vs_sidecar")
        if v:
            ci = f"[{v['ci90_dppl'][0]:+.3f},{v['ci90_dppl'][1]:+.3f}]"
            lines.append(f"{r['scheme']:26s} {r['ppl']:8.3f} {dfp:>16s} "
                         f"{v['dppl']:+8.3f}±{v['se_jackknife']:.3f} {ci:>18s} {v['t']:+7.2f} "
                         f"{v['p_two_sided']:9.3g} {v['tost_p']:9.3g}  {v['verdict']}")
        else:
            lines.append(f"{r['scheme']:26s} {r['ppl']:8.3f} {dfp:>16s} {'(reference)':>18s}")
    return "\n".join(lines)


def report():
    res = load()
    U = res["units"]
    res["method"] = __doc__.split("Stats vs")[1].strip()
    res["reference"] = REF
    res["tables"] = {}
    for m, title in (("gpt2", "GPT-2, full WikiText-2 test, all 12 c_fc"),
                     ("qwen", "Qwen2.5-0.5B, WikiText-2 test windows, all 24 gate+up")):
        tab = model_table(U, m)
        if tab:
            res["tables"][m] = tab
            print(fmt(tab, title))
    for m in ("gpt2", "qwen"):
        f8 = first8(U, m)
        if not f8:
            continue
        res[m + "_first8_windows_df7"] = f8
        print(f"\n{m} first 8 windows (= alternatives.json eval), df = 7:")
        for k, v in f8.items():
            print(f"  {k:26s} diff {v['dppl']:+.3f}  t {v['t']:+.2f}  p {v['p_two_sided']:.3g}"
                  f"  TOST p {v['tost_p']:.3g}  {v['verdict']}")
    checks(res)
    save(res)


def checks(res):
    """First-8-window NLL vs the stored alternatives.json / novelty.json runs."""
    U = res["units"]
    alt = OUT / "alternatives.json"
    if not alt.exists():
        return
    A = json.loads(alt.read_text())["units"]
    out = {}
    ex = OUT / "extras.json"
    E = json.loads(ex.read_text())["units"] if ex.exists() else {}
    for m, tile_old in (("gpt2", "tile_wclip@8192"), ("qwen", "qwen_tile_wclip@8192")):
        alias = {"FP32": (A, m + "_fp32"), RIVAL: (E, tile_old),
                 "SidecarCIM+wclip k2,VB16": (A, m + "|SidecarCIM+wclip (k2,VB16)")}
        for n in ["FP32"] + [s for s, _ in SCHEMES]:
            src, old = alias.get(n, (A, f"{m}|{n}"))
            u = U.get(f"{m}|{n}")
            if u and old in src and u["win_idx"][:8] == list(range(8)):
                out[f"{m}|{n}"] = float(np.abs(np.array(u["nll"][:8]) -
                                               np.array(src[old]["nll"])).max())
    nov = OUT / "novelty.json"
    u = U.get("gpt2|W8A8")
    if nov.exists() and u and len(u["nll"]) >= 8:
        r = {x["scheme"]: x for x in json.loads(nov.read_text())["final_long_eval"]}
        out["gpt2|W8A8 first-8 ppl - novelty.json ppl_all12"] = \
            abs(ppl(np.array(u["nll"][:8])) - r["W8A8"]["ppl_all12"])
    res["consistency_max_abs_dnll_vs_8window_runs"] = out
    for k, v in out.items():
        print(f"  check {k}: {v:.2e}")


if __name__ == "__main__":
    _selftest()
    st = sys.argv[1]
    if st == "qwen":
        stage_qwen(int(sys.argv[2]))
    else:
        {"gpt2": stage_gpt2, "time_qwen": stage_time_qwen, "report": report}[st]()
