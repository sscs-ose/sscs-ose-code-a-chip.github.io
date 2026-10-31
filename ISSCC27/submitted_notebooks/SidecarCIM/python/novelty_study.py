"""Design study for SidecarCIM: slot selection, budget-aware migration, activation clip.

Same data split and metrics as llm_layer.py (WikiText-2: calib = first 512 train tokens,
eval = first eval_tokens test tokens; h.0 layer error, ppl with only h.0 c_fc replaced,
ppl with all 12 c_fc replaced = main model-scale number). Final table re-runs the key
schemes on LONG_EVAL tokens with a paired noise estimate (per-window NLL differences).
Slot selection (same hardware and slot format as golden.sidecar_dot, slot holds the full weight):
  mag    = top-k |w| per tile column (current SidecarCIM)
  resid  = top-k of E[x^2]*(w - deq(q(w)))^2 (quant without slots)
  greedy = k rounds; each round every tile column takes the slot with the largest drop in
           its group's E[x^2]-weighted squared error (incl. the range shrink when an extreme
           is removed); ranges are re-fit between rounds
  hybrid = |w| > 3 sigma (per channel, after migration) first, by |w|; rest by resid score
budget = per-input-channel smoothing scale shrunk (x BUDGET_STEP per round) on rows that make a
  tile column exceed k values over 3 sigma, until none does (or BUDGET_ITERS rounds).
wclip = offline weight range search (llm_layer.mse_clip); aclip = activation range shrink r
  picked by calib layer error. Alpha is picked on calib from ALPHAS (aclip applied after).
"""
import json
import time

import numpy as np

from golden import SPEC
from llm_layer import (AB, CALIB_TOKENS, EVAL_TOKENS, N_IN, OUT, VB, WB, WIDE, act_codes,
                       capture, fc_names, golden_check, int_forward, load_wikitext, make_qfc,
                       mse_clip, rel_l2, smooth_scales)
from quant import qmax, quant_params, quantize_with, range_params

K = SPEC["outlier"]["budget_per_output"]
SIG = SPEC["outlier"]["threshold_sigma"]
KS = (1, K, 2 * K)
ALPHAS = (0.85, 0.9, 0.95, 1.0, 1.1, 1.25, 1.5)
ACLIP_GRID = np.linspace(0.5, 1.0, 11)
BUDGET_STEP, BUDGET_ITERS = 0.9, 60
LONG_EVAL = 4 * EVAL_TOKENS
EXACT = 2.0 ** 53

B = dict(wbits=WB, abits=AB, alpha="pick", k=0, sel="mag", tile=False, wclip=False,
         aclip=False, budget=False)
SCHEMES = [("W8A8", dict(B, wbits=WIDE, abits=WIDE, alpha=None)),
           ("W4A4+mig", dict(B)),
           ("W4A4+mig+wclip", dict(B, wclip=True)),
           ("W4A4+mig+tile+wclip", dict(B, tile=True, wclip=True))]
for _k in KS:
    for _s in ("mag", "resid", "greedy", "hybrid"):
        SCHEMES.append((f"side-{_s}-k{_k}", dict(B, k=_k, sel=_s)))
SCHEMES += [("side-mag-k%d+wclip" % K, dict(B, k=K, wclip=True)),
            ("side-greedy-k%d+wclip" % K, dict(B, k=K, sel="greedy", wclip=True)),
            ("side-hybrid-k%d+wclip" % K, dict(B, k=K, sel="hybrid", wclip=True)),
            ("side-mag-k%d+budget" % K, dict(B, k=K, budget=True)),
            ("side-greedy-k%d+budget" % K, dict(B, k=K, sel="greedy", budget=True)),
            ("side-hybrid-k%d+budget" % K, dict(B, k=K, sel="hybrid", budget=True)),
            ("W4A4+mig+wclip+aclip", dict(B, wclip=True, aclip=True)),
            ("W4A4+mig+tile+wclip+aclip", dict(B, tile=True, wclip=True, aclip=True)),
            ("side-mag-k%d+wclip+aclip" % K, dict(B, k=K, wclip=True, aclip=True)),
            ("side-greedy-k%d+wclip+aclip" % K, dict(B, k=K, sel="greedy", wclip=True,
                                                     aclip=True)),
            ("side-hybrid-k%d+wclip+aclip" % K, dict(B, k=K, sel="hybrid", wclip=True,
                                                     aclip=True))]
OLD = {"side-mag-k%d" % K: "SidecarCIM", "side-mag-k%d+wclip" % K: "SidecarCIM+wclip"}


# ---------------- weight helpers ----------------

def werr(D, h, sw, zw, wbits):
    """E[x^2]-weighted squared error of each entry; D (G, R, out), h (G, R, 1)."""
    q = quantize_with(D, sw[:, None], zw[:, None], wbits)
    return h * (D - sw[:, None] * (q - zw[:, None])) ** 2


def sigma_mask(Ws):
    """|w| > SIG * std (per output channel)."""
    return np.abs(Ws) > SIG * Ws.std(axis=0, keepdims=True)


def resid_score(Ws, h, G, wbits):
    """Weighted residual of plain quantization (no slots), (d_in, out)."""
    d_in, d_out = Ws.shape
    D = Ws.reshape(G, d_in // G, d_out)
    sw, zw = range_params(D.min(axis=1), D.max(axis=1), wbits)
    return werr(D, h.reshape(G, -1, 1), sw, zw, wbits).reshape(d_in, d_out)


def topk_rows(score, k, n=N_IN):
    """Rows (within tile) of the k largest scores per tile column: (n_rt, k, out)."""
    a = score.reshape(score.shape[0] // n, n, score.shape[1])
    return np.argsort(-a, axis=1, kind="stable")[:, :k, :]


def greedy_rows(Ws, h, k, G, wbits, n=N_IN):
    """Greedy slot choice (see module docstring)."""
    d_in, d_out = Ws.shape
    n_rt, R = d_in // n, d_in // G
    h3 = h.reshape(G, R, 1)
    chosen = np.zeros((d_in, d_out), bool)
    gi, oi = np.arange(G)[:, None], np.arange(d_out)[None, :]
    for _ in range(k):
        D = np.where(chosen, 0.0, Ws).reshape(G, R, d_out)
        sw, zw = range_params(D.min(axis=1), D.max(axis=1), wbits)
        err = werr(D, h3, sw, zw, wbits)
        E = err.sum(axis=1)
        gain = err.copy()
        for pos in (D.argmax(axis=1), D.argmin(axis=1)):    # removing an extreme shrinks range
            D2 = D.copy()
            D2[gi, pos, oi] = 0.0
            s2, z2 = range_params(D2.min(axis=1), D2.max(axis=1), wbits)
            gain[gi, pos, oi] = E - werr(D2, h3, s2, z2, wbits).sum(axis=1)
        g = np.where(chosen, -np.inf, gain.reshape(d_in, d_out)).reshape(n_rt, n, d_out)
        pick = g.argmax(axis=1)
        c3 = chosen.reshape(n_rt, n, d_out)
        c3[np.arange(n_rt)[:, None], pick, oi] = True
    c3 = chosen.reshape(n_rt, n, d_out)
    return np.argsort(~c3, axis=1, kind="stable")[:, :k, :]


def select_rows(Ws, h, k, sel, G, wbits, n=N_IN):
    """Slot rows per tile column (tile height n) for a selection mode."""
    if sel == "mag":
        return topk_rows(np.abs(Ws), k, n)
    if sel == "greedy":
        return greedy_rows(Ws, h, k, G, wbits, n)
    r = resid_score(Ws, h, G, wbits)
    if sel == "resid":
        return topk_rows(r, k, n)
    assert sel == "hybrid"
    a = np.abs(Ws)
    score = np.where(sigma_mask(Ws), 2.0 + a / a.max(), r / max(r.max(), 1e-300))
    return topk_rows(score, k, n)


def budget_scales(Xcal, W, alpha, k, n=N_IN):
    """Per-channel smoothing scales with no tile column over k sigma-outliers (if reachable)."""
    s = smooth_scales(Xcal, W, alpha)
    s0 = s.copy()
    n_rt, d_out = W.shape[0] // n, W.shape[1]
    first = None
    for it in range(BUDGET_ITERS + 1):
        m = sigma_mask(W * s[:, None]).reshape(n_rt, n, d_out)
        viol = m.sum(axis=1) > k
        if first is None:
            first = int(viol.sum())
        if not viol.any() or it == BUDGET_ITERS:
            break
        bad = (m & viol[:, None, :]).any(axis=2).reshape(-1)
        s = np.where(bad, s * BUDGET_STEP, s)
    r = s / s0
    return s, {"viol_cols_before": first, "viol_cols_after": int(viol.sum()), "rounds": it,
               "rows_changed": int((r < 1).sum()), "min_scale_ratio": round(float(r.min()), 4)}


# ---------------- encoding ----------------

def encode2(W, b, Xcal, cfg, alpha, n=N_IN):
    """Offline encoding, same dict layout as llm_layer.encode (works with int_forward).

    n: tile height (rows per tile column; default spec n_inputs); d_in must be a multiple.
    """
    d_in, d_out = W.shape
    assert d_in % n == 0
    n_rt = d_in // n
    wbits, abits, k = cfg["wbits"], cfg["abits"], cfg["k"]
    vb = cfg.get("vb", VB)                      # slot value bits (default: spec)
    binfo = None
    if alpha is None:
        s = np.ones(d_in)
    elif cfg["budget"]:
        s, binfo = budget_scales(Xcal, W, alpha, k, n)
    else:
        s = smooth_scales(Xcal, W, alpha)
    Ws, Xs = W * s[:, None], Xcal / s[None, :]
    h = (Xs ** 2).mean(axis=0)
    G = n_rt if cfg["tile"] else 1
    R = d_in // G
    idx = (select_rows(Ws, h, k, cfg["sel"], G, wbits, n) if k
           else np.zeros((n_rt, 0, d_out), int))
    mask = np.zeros((n_rt, n, d_out), bool)
    np.put_along_axis(mask, idx, True, axis=1)
    cover = None
    if k:
        sm = sigma_mask(Ws)
        cover = round(100.0 * float((sm & mask.reshape(d_in, d_out)).sum() / max(sm.sum(), 1)), 3)
    mask = mask.reshape(G, R, d_out)
    dense = np.where(mask, 0.0, Ws.reshape(G, R, d_out))
    lo, hi = dense.min(axis=1), dense.max(axis=1)
    if cfg["wclip"]:
        lo, hi = mse_clip(dense, h.reshape(G, R)[:, :, None] * ~mask, lo, hi, wbits)
    sw, zw = range_params(lo, hi, wbits)
    Wq = quantize_with(dense, sw[:, None], zw[:, None], wbits)
    Wq = np.where(mask, zw[:, None, :], Wq)
    vmax = (1 << (vb - 1)) - 1
    o = np.take_along_axis(Ws.reshape(n_rt, n, d_out), idx, axis=1)
    if k:
        om = np.abs(o).reshape(G, -1, d_out).max(axis=1)
        S = np.clip(np.floor(np.log2(vmax * sw / np.maximum(om, 1e-30))), 0, vb - 1)
        S = S.astype(np.int64)
    else:
        S = np.zeros((G, d_out), np.int64)
    unit = np.repeat(sw / 2.0 ** S, n_rt // G, axis=0)
    val = np.clip(np.round(o / unit[:, None, :]), -vmax - 1, vmax).astype(np.int64)
    V = np.zeros((n_rt, n, d_out))
    np.put_along_axis(V, idx, val.astype(np.float64), axis=1)
    sx, zx = quant_params(Xs, abits)
    assert R * qmax(abits) * (qmax(wbits) * 2.0 ** S.max() + k * vmax) < EXACT
    enc = dict(cfg=cfg, alpha=alpha, s=s, sx=float(sx), zx=int(zx), sw=sw, zw=zw, S=S, G=G, n=n,
               Wq=Wq.reshape(d_in, d_out), idx=idx, val=val, b=b,
               Wc=(Wq - zw[:, None, :]).astype(np.float64), V=V.reshape(G, R, d_out),
               budget=binfo, sigma_cover_pct=cover, aclip_r=1.0)
    if cfg["aclip"]:
        ref = Xcal @ W + b
        lo_x, hi_x = Xs.min(), Xs.max()
        best = None
        for r in ACLIP_GRID:
            enc["sx"], enc["zx"] = (float(v) for v in range_params(lo_x * r, hi_x * r, abits))
            enc["zx"] = int(enc["zx"])
            e = rel_l2(int_forward(enc, Xcal), ref)
            if best is None or e < best[0]:
                best = (e, r, enc["sx"], enc["zx"])
        _, enc["aclip_r"], enc["sx"], enc["zx"] = best
        enc["aclip_r"] = float(enc["aclip_r"])
    return enc


def encode_pick2(W, b, Xcal, cfg, n=N_IN):
    """Pick alpha on calib layer error (without aclip), then final encode (tile height n)."""
    if cfg["alpha"] != "pick":
        return encode2(W, b, Xcal, cfg, cfg["alpha"], n)
    ref = Xcal @ W + b
    c0 = dict(cfg, aclip=False)
    errs = [(rel_l2(int_forward(encode2(W, b, Xcal, c0, a, n), Xcal), ref), a) for a in ALPHAS]
    a = min(errs)[1]
    return encode2(W, b, Xcal, cfg, a, n)


# ---------------- perplexity with per-window NLL ----------------

def window_nll(model, windows, encs=None):
    """Mean NLL per window with given layers swapped for integer-path modules."""
    import torch
    saved = []
    for name, enc in (encs or {}).items():
        parent, attr = name.rsplit(".", 1)
        p = model.get_submodule(parent)
        saved.append((p, attr, getattr(p, attr)))
        setattr(p, attr, make_qfc(enc))
    try:
        with torch.no_grad():
            out = [model(w[None, :], labels=w[None, :]).loss.item() for w in windows]
    finally:
        for p, attr, mod in saved:
            setattr(p, attr, mod)
    return np.array(out)


def ppl(nll):
    return float(np.exp(nll.mean()))


def paired(nll, nll_fp):
    """Delta ppl vs FP32 and its standard error from per-window NLL differences."""
    d = nll - nll_fp
    se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float("nan")
    p = ppl(nll)
    return round(p - ppl(nll_fp), 4), round(float(p * se), 4)


# ---------------- self-tests ----------------

def _selftest():
    rng = np.random.default_rng(11)
    d_in, d_out = N_IN * 3, 12
    W = rng.normal(0, 0.1, (d_in, d_out))
    W[5, 2], W[6, 2], W[7, 2], W[40, 7] = 2.0, 1.8, -1.7, -1.5
    b = rng.normal(0, 0.1, d_out)
    X = rng.normal(0, 1, (60, d_in))
    X[:, 3] *= 20
    h = (X ** 2).mean(axis=0)
    for sel in ("mag", "resid", "greedy", "hybrid"):
        for G in (1, d_in // N_IN):
            idx = select_rows(W, h, K, sel, G, WB)
            assert idx.shape == (d_in // N_IN, K, d_out)
            assert all(len(set(idx[r, :, j])) == K for r in range(idx.shape[0])
                       for j in range(d_out))
    # hybrid keeps sigma outliers when they fit
    sm = sigma_mask(W).reshape(-1, N_IN, d_out)
    idx = select_rows(W, h, K, "hybrid", 1, WB)
    for r in range(sm.shape[0]):
        for j in range(d_out):
            rows = set(np.flatnonzero(sm[r, :, j]))
            if len(rows) <= K:
                assert rows <= set(idx[r, :, j])
    # greedy beats or ties no-sidecar weighted error; budget scales remove violations
    D = W.reshape(1, d_in, d_out)
    sw, zw = range_params(D.min(axis=1), D.max(axis=1), WB)
    e0 = werr(D, h.reshape(1, -1, 1), sw, zw, WB).sum()
    idx = greedy_rows(W, h, K, 1, WB)
    m = np.zeros((d_in // N_IN, N_IN, d_out), bool)
    np.put_along_axis(m, idx, True, axis=1)
    D1 = np.where(m.reshape(1, d_in, d_out), 0.0, D)
    s1, z1 = range_params(D1.min(axis=1), D1.max(axis=1), WB)
    e1 = (werr(D1, h.reshape(1, -1, 1), s1, z1, WB) * ~m.reshape(1, d_in, d_out)).sum()
    assert e1 < e0
    _, info = budget_scales(X, W, 1.0, 1)
    assert info["viol_cols_after"] <= info["viol_cols_before"]
    # every config: golden tile check, integer == dequant float, aclip never worse on calib
    ref = X @ W + b
    for name, cfg in SCHEMES:
        enc = encode_pick2(W, b, X, cfg)
        assert golden_check(enc, X, [0, 1])
        xd = enc["sx"] * (act_codes(enc, X) - enc["zx"])
        wd = np.concatenate([enc["sw"][g] * enc["Wc"][g] + enc["V"][g] * enc["sw"][g] /
                             2.0 ** enc["S"][g] for g in range(enc["G"])])
        assert np.allclose(int_forward(enc, X), xd @ wd + b)
        if cfg["aclip"]:
            e_no = encode2(W, b, X, dict(cfg, aclip=False), enc["alpha"])
            assert rel_l2(int_forward(enc, X), ref) <= rel_l2(int_forward(e_no, X), ref) + 1e-12
    print(f"novelty_study self-test passed ({len(SCHEMES)} schemes)")


# ---------------- main ----------------

def main():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    _selftest()
    t0 = time.time()
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ctx = model.config.n_positions
    ev = tok(load_wikitext("test", 80000))["input_ids"]
    ca = tok(load_wikitext("train", 20000))["input_ids"]
    assert len(ev) >= LONG_EVAL and len(ca) >= CALIB_TOKENS
    ev = torch.tensor(ev[:LONG_EVAL])
    wins_long = [ev[i:i + ctx] for i in range(0, LONG_EVAL, ctx)]
    wins = wins_long[:EVAL_TOKENS // ctx]                       # same 2048 tokens as llm_layer
    names = fc_names(model)
    h0 = SPEC["workload"]["layer"]
    Xc = capture(model, names, [torch.tensor(ca[:CALIB_TOKENS])])
    Xe = capture(model, names, wins)
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    nll_fp = window_nll(model, wins)
    print(f"eval {EVAL_TOKENS} tok ({len(wins)} windows), long eval {LONG_EVAL} tok "
          f"({len(wins_long)} windows), calib {CALIB_TOKENS} tok; FP32 ppl {ppl(nll_fp):.4f}")

    rows = []
    for name, cfg in SCHEMES:
        encs, alphas, ec, ee = {}, [], [], []
        for n in names:
            e = encode_pick2(Ws[n], bs[n], Xc[n], cfg)
            golden_check(e, Xe[n], [0] if n != h0 else [0, EVAL_TOKENS - 1])
            encs[n] = e
            alphas.append(e["alpha"])
            ec.append(rel_l2(int_forward(e, Xc[n]), Xc[n] @ Ws[n] + bs[n]))
            ee.append(rel_l2(int_forward(e, Xe[n]), Xe[n] @ Ws[n] + bs[n]))
        e0 = encs[h0]
        n1 = window_nll(model, wins, {h0: e0})
        n12 = window_nll(model, wins, encs)
        rows.append({"scheme": name, "alias": OLD.get(name, ""), "cfg": cfg,
                     "alpha_h0": e0["alpha"], "alphas_all12": alphas,
                     "err_calib_h0": round(ec[names.index(h0)], 5),
                     "err_eval_h0": round(ee[names.index(h0)], 5),
                     "mean_err_calib_all12": round(float(np.mean(ec)), 5),
                     "mean_err_eval_all12": round(float(np.mean(ee)), 5),
                     "ppl_h0": round(ppl(n1), 4), "ppl_all12": round(ppl(n12), 4),
                     "sigma_cover_pct_h0": e0["sigma_cover_pct"], "budget_h0": e0["budget"],
                     "aclip_r_h0": e0["aclip_r"]})
        del encs
        print(f"  done {name} ({time.time() - t0:.0f} s)", flush=True)

    # best new variant: k <= budget, not the existing SidecarCIM rows, lowest mean calib err
    new = [r for r in rows if 0 < r["cfg"]["k"] <= K and r["scheme"] not in OLD]
    best = min(new, key=lambda r: r["mean_err_calib_all12"])
    final_names = ["W8A8", "W4A4+mig", "W4A4+mig+wclip", "side-mag-k%d" % K,
                   "side-mag-k%d+wclip" % K, best["scheme"], "W4A4+mig+tile+wclip",
                   "W4A4+mig+tile+wclip+aclip"]
    final_names = list(dict.fromkeys(final_names))
    nll_fp_l = window_nll(model, wins_long)
    final = [{"scheme": "FP32", "ppl_h0": round(ppl(nll_fp_l), 4),
              "ppl_all12": round(ppl(nll_fp_l), 4),
              "fp32_window_ppl": [round(float(np.exp(v)), 3) for v in nll_fp_l]}]
    by = {r["scheme"]: r for r in rows}
    for name in final_names:
        r = by[name]
        encs = {}
        for i, n in enumerate(names):                          # re-encode with picked alphas
            encs[n] = encode2(Ws[n], bs[n], Xc[n], r["cfg"], r["alphas_all12"][i])
        n1 = window_nll(model, wins_long, {h0: encs[h0]})
        n12 = window_nll(model, wins_long, encs)
        d1, se1 = paired(n1, nll_fp_l)
        d12, se12 = paired(n12, nll_fp_l)
        final.append({"scheme": name, "alias": OLD.get(name, ""), "ppl_h0": round(ppl(n1), 4),
                      "d_h0": d1, "se_h0": se1, "ppl_all12": round(ppl(n12), 4),
                      "d_all12": d12, "se_all12": se12})
        del encs
        print(f"  long eval done {name} ({time.time() - t0:.0f} s)", flush=True)

    print(f"\nMain table (eval {EVAL_TOKENS} tokens; FP32 ppl {ppl(nll_fp):.4f})")
    print(f"{'scheme':30s} {'alias':16s} {'a_h0':>5s} {'err_h0':>8s} {'err12_cal':>9s} "
          f"{'err12_ev':>8s} {'ppl_h0':>8s} {'ppl_all12':>9s} {'3s_cov%':>7s}")
    for r in rows:
        a = "-" if r["alpha_h0"] is None else f"{r['alpha_h0']:.2f}"
        cv = "-" if r["sigma_cover_pct_h0"] is None else f"{r['sigma_cover_pct_h0']:.1f}"
        print(f"{r['scheme']:30s} {r['alias']:16s} {a:>5s} {r['err_eval_h0']:8.5f} "
              f"{r['mean_err_calib_all12']:9.5f} {r['mean_err_eval_all12']:8.5f} "
              f"{r['ppl_h0']:8.4f} {r['ppl_all12']:9.4f} {cv:>7s}")
    print("\nbudget-aware migration (h.0):")
    for r in rows:
        if r["budget_h0"]:
            print(f"  {r['scheme']:30s} {r['budget_h0']}")
    print(f"\nbest new variant (k <= {K}, by mean calib err over 12 layers): {best['scheme']}")
    print(f"\nFinal table (long eval {LONG_EVAL} tokens, {len(wins_long)} windows; "
          f"d = ppl - FP32 ppl, se = paired std error over windows)")
    print(f"{'scheme':30s} {'alias':16s} {'ppl_h0':>8s} {'d_h0':>7s} {'se_h0':>6s} "
          f"{'ppl_all12':>9s} {'d_all12':>8s} {'se_all12':>8s}")
    for r in final:
        if r["scheme"] == "FP32":
            print(f"{'FP32':30s} {'':16s} {r['ppl_h0']:8.4f} {'':>7s} {'':>6s} "
                  f"{r['ppl_all12']:9.4f}   window ppl {r['fp32_window_ppl']}")
            continue
        print(f"{r['scheme']:30s} {r['alias']:16s} {r['ppl_h0']:8.4f} {r['d_h0']:7.4f} "
              f"{r['se_h0']:6.4f} {r['ppl_all12']:9.4f} {r['d_all12']:8.4f} {r['se_all12']:8.4f}")

    OUT.mkdir(parents=True, exist_ok=True)
    out = {"eval_tokens": EVAL_TOKENS, "long_eval_tokens": LONG_EVAL, "calib_tokens": CALIB_TOKENS,
           "alphas": list(ALPHAS), "aclip_grid": ACLIP_GRID.tolist(),
           "budget": {"step": BUDGET_STEP, "iters": BUDGET_ITERS},
           "best_new_variant": best["scheme"], "fp32_ppl_eval": round(ppl(nll_fp), 4),
           "rows": rows, "final_long_eval": final}
    (OUT / "novelty.json").write_text(json.dumps(out, indent=2))
    print(f"saved {OUT / 'novelty.json'} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
