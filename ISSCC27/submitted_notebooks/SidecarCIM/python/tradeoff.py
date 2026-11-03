"""C2 trade-off curve: alpha x k on GPT-2 (all 12 mlp.c_fc), perplexity plus weight-outlier stats.

Setup = llm_layer.py: calib = first 512 WikiText-2 train tokens, eval = first 2048 test tokens
(grid) and 8192 tokens (k=2 row: best alpha and its neighbours). Magnitude top-k slots per tile
column, offline weight clip on, 4-bit dense, signed sidecar at spec width (12 bit; rerun Oct 12,
the 16-bit run is kept as tradeoff_vb16.json). k=0 = 4-bit + migration only
(no sidecar). Fixed alpha for all 12 layers (no per-layer pick).
Stats are pooled over all 12 layers' tile columns (32 inputs x 1 output), after migration (W*s):
  3sigma outliers = |w| > 3*std of its output channel (spec threshold_sigma);
  over budget     = tile columns with more than k such outliers (k=0: any);
  coverage        = share of all 3sigma outliers that sit in a sidecar slot;
  range_sigma     = mean over dense columns of 15*step/std = how many std the 4-bit range spans.
Results are checkpointed after every point (resume = rerun).
"""
import json
import time

import numpy as np

from golden import SPEC
from llm_layer import (AB, CALIB_TOKENS, N_IN, OUT, WB, capture, encode, fc_names,
                       golden_check, int_forward, load_wikitext, perplexity, rel_l2)

SIG = SPEC["outlier"]["threshold_sigma"]
EVAL_GRID, EVAL_LONG = SPEC["workload"]["eval_tokens"], 8192
ALPHAS = (0.5, 0.7, 0.85, 1.0, 1.25)
KS = (0, 1, 2, 4)
FILE = OUT / "tradeoff.json"


def layer_stats(W, enc, k):
    """Outlier stats of one migrated layer: per-tile-column counts and slot coverage."""
    Ws = W * enc["s"][:, None]
    d_in, d_out = Ws.shape
    n_rt = d_in // N_IN
    sm = np.abs(Ws) > SIG * Ws.std(axis=0, keepdims=True)
    cnt = sm.reshape(n_rt, N_IN, d_out).sum(axis=1)             # (n_rt, out)
    covered = 0
    if k:
        mask = np.zeros((n_rt, N_IN, d_out), bool)
        np.put_along_axis(mask, enc["idx"], True, axis=1)
        covered = int((sm & mask.reshape(d_in, d_out)).sum())
    step = enc["sw"][0]                                         # G=1: (out,)
    rng = float(np.mean(((1 << WB) - 1) * step / np.maximum(Ws.std(axis=0), 1e-30)))
    return cnt, int(sm.sum()), covered, rng


def pool(parts, k):
    """Merge per-layer stats into one record."""
    cnt = np.concatenate([p[0].ravel() for p in parts])
    n_out, cov = sum(p[1] for p in parts), sum(p[2] for p in parts)
    return {"mean_3sig_per_col": round(float(cnt.mean()), 4), "max_3sig_per_col": int(cnt.max()),
            "pct_cols_over_k": round(100.0 * float((cnt > k).mean()), 3),
            "pct_weights_3sig": round(100.0 * n_out / (cnt.size * N_IN), 4),
            "sidecar_3sig_cover_pct": round(100.0 * cov / max(n_out, 1), 3) if k else None,
            "range_sigma": round(float(np.mean([p[3] for p in parts])), 3)}


def build(Ws, bs, Xc, names, alpha, k):
    """Encode all layers at one (alpha, k) point; return encs and pooled stats."""
    cfg = dict(wbits=WB, abits=AB, alpha=alpha, k=k, tile=False, clip=True)
    encs, parts = {}, []
    for n in names:
        encs[n] = encode(Ws[n], bs[n], Xc[n], cfg, alpha)
        parts.append(layer_stats(Ws[n], encs[n], k))
    return encs, pool(parts, k)


def _selftest():
    rng = np.random.default_rng(3)
    d_in, d_out = N_IN * 2, 6
    W = rng.normal(0, 0.1, (d_in, d_out))
    W[3, 1], W[9, 1], W[40, 4] = 3.0, -3.0, 2.5            # 2 outliers in one tile column
    X = rng.normal(0, 1, (30, d_in))
    b = np.zeros(d_out)
    for k in (0, 1, 2):
        cfg = dict(wbits=WB, abits=AB, alpha=None, k=k, tile=False, clip=True)
        st = pool([layer_stats(W, encode(W, b, X, cfg, None), k)], k)
        assert st["max_3sig_per_col"] >= 2
        if k == 0:
            assert st["sidecar_3sig_cover_pct"] is None and st["pct_cols_over_k"] > 0
        elif k == 1:
            assert st["pct_cols_over_k"] > 0 and st["sidecar_3sig_cover_pct"] < 100.0
        else:
            assert st["sidecar_3sig_cover_pct"] == 100.0 and st["pct_cols_over_k"] == 0.0
    print("tradeoff self-test passed")


def main():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    torch.set_num_threads(6)
    _selftest()
    t0 = time.time()
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ctx = model.config.n_positions
    ev = tok(load_wikitext("test", 80000))["input_ids"]
    ca = tok(load_wikitext("train", 20000))["input_ids"]
    assert len(ev) >= EVAL_LONG and len(ca) >= CALIB_TOKENS
    ev = torch.tensor(ev[:EVAL_LONG])
    win_l = [ev[i:i + ctx] for i in range(0, EVAL_LONG, ctx)]
    win_g = win_l[:EVAL_GRID // ctx]
    names = fc_names(model)
    h0 = SPEC["workload"]["layer"]
    Xc = capture(model, names, [torch.tensor(ca[:CALIB_TOKENS])])
    Xe0 = capture(model, [h0], win_g)[h0]
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    res = {"grid": [], "long": []}
    if FILE.exists():
        res = json.loads(FILE.read_text())
    done = {(r["alpha"], r["k"]) for r in res["grid"]}
    ppl_fp_g, ppl_fp_l = perplexity(model, win_g), perplexity(model, win_l)
    print(f"FP32 ppl {ppl_fp_g:.4f} ({EVAL_GRID} tok), {ppl_fp_l:.4f} ({EVAL_LONG} tok)")

    def save():
        out = {"model": SPEC["workload"]["model"], "layers": "all 12 mlp.c_fc",
               "calib": f"WikiText-2 train first {CALIB_TOKENS} tokens",
               "eval_grid": f"WikiText-2 test first {EVAL_GRID} tokens",
               "eval_long": f"WikiText-2 test first {EVAL_LONG} tokens",
               "setup": "4-bit dense, magnitude top-k slots, weight clip on, fixed alpha all layers",
               "ppl_fp32_grid": round(ppl_fp_g, 4), "ppl_fp32_long": round(ppl_fp_l, 4),
               "grid": res["grid"], "long": res["long"]}
        FILE.write_text(json.dumps(out, indent=2))

    for a in ALPHAS:
        for k in KS:
            if (a, k) in done:
                continue
            encs, st = build(Ws, bs, Xc, names, a, k)
            golden_check(encs[h0], Xe0, [0])
            ppl = perplexity(model, win_g, encs)
            err = rel_l2(int_forward(encs[h0], Xe0), Xe0 @ Ws[h0] + bs[h0])
            res["grid"].append({"alpha": a, "k": k, "ppl": round(ppl, 4),
                                "err_h0": round(err, 5), **st})
            save()
            print(f"  alpha {a} k {k}: ppl {ppl:.4f} ({time.time() - t0:.0f} s)", flush=True)
            del encs

    # long eval: k=2 row, best alpha on the grid and its two neighbours
    row = {r["alpha"]: r["ppl"] for r in res["grid"] if r["k"] == 2}
    al = sorted(row)
    ib = min(range(len(al)), key=lambda i: row[al[i]])
    pick = al[max(0, ib - 1):ib + 2]
    print("long eval alphas", pick)
    done_l = {r["alpha"] for r in res["long"]}
    for a in pick:
        if a in done_l:
            continue
        encs, _ = build(Ws, bs, Xc, names, a, 2)
        res["long"].append({"alpha": a, "k": 2, "ppl": round(perplexity(model, win_l, encs), 4)})
        save()
        print(f"  long alpha {a}: ppl {res['long'][-1]['ppl']:.4f} ({time.time() - t0:.0f} s)",
              flush=True)
        del encs

    print(f"\n{'alpha':>5s} {'k':>2s} {'ppl2048':>9s} {'mean3s/col':>10s} {'max':>4s} "
          f"{'%over':>7s} {'cover%':>7s} {'range_sig':>9s}")
    for r in res["grid"]:
        cv = "-" if r["sidecar_3sig_cover_pct"] is None else f"{r['sidecar_3sig_cover_pct']:.2f}"
        print(f"{r['alpha']:5.2f} {r['k']:2d} {r['ppl']:9.4f} {r['mean_3sig_per_col']:10.4f} "
              f"{r['max_3sig_per_col']:4d} {r['pct_cols_over_k']:7.3f} {cv:>7s} "
              f"{r['range_sigma']:9.3f}")
    for r in res["long"]:
        print(f"long {EVAL_LONG} tok, k=2, alpha {r['alpha']}: ppl {r['ppl']:.4f} "
              f"(FP32 {ppl_fp_l:.4f})")
    print(f"saved {FILE} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
