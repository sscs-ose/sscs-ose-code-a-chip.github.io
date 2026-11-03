"""Generalization check: SidecarCIM schemes on Qwen/Qwen2.5-0.5B (Apache-2.0, not gated).

Target: the SwiGLU input projections mlp.gate_proj and mlp.up_proj (both read the post-RMSNorm
activation). They are treated as ONE matrix W = [gate^T | up^T] (d_model x 2*d_ff): one shared
activation code stream and one shared smoothing scale per input channel (folded into the
RMSNorm weight offline), same 32x8 tile mapping. No bias.
Data as llm_layer.py: calib = first 512 WikiText-2 train tokens, eval = first LONG_EVAL test
tokens in windows of WIN (first EVAL_TOKENS reported too); paired SE over windows vs FP32.
Alpha is picked on calib layer error from novelty_study.ALPHAS without clipping; the final
encode then adds wclip (saves runtime). Integer path checked tile by tile against
golden.dcim_dot + golden.sidecar_dot on sample tokens of every layer.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "6")                     # share the machine with flow runs

import json  # noqa: E402
import resource  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

from golden import SPEC  # noqa: E402
from llm_layer import (CALIB_TOKENS, EVAL_TOKENS, N_IN, OUT, WIDE, capture,  # noqa: E402
                       golden_check, int_forward, load_wikitext, rel_l2, smooth_scales)
from novelty_study import ALPHAS, B, encode2, paired, ppl, sigma_mask, topk_rows  # noqa: E402

MODEL = "Qwen/Qwen2.5-0.5B"
K = SPEC["outlier"]["budget_per_output"]
SIG = SPEC["outlier"]["threshold_sigma"]
WIN = 1024
LONG_EVAL = 4 * EVAL_TOKENS
THREADS = 6


def peak_gb():
    """Peak resident memory of this process (GB, Linux ru_maxrss in kB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
SCHEMES = [("W8A8", dict(B, wbits=WIDE, abits=WIDE, alpha=None)),
           ("W4A4", dict(B, alpha=None)),
           ("W4A4+mig", dict(B)),
           ("W4A4+mig+wclip", dict(B, wclip=True)),
           ("SidecarCIM", dict(B, k=K)),
           ("SidecarCIM+wclip", dict(B, k=K, wclip=True)),
           ("W4A4+mig+tile+wclip", dict(B, tile=True, wclip=True))]


# ---------------- encoding ----------------

def pick_encode(W, b, Xcal, cfg, n=N_IN):
    """Alpha by calib layer error (no clips), then final encode with the full cfg (tile height n)."""
    alpha = cfg["alpha"]
    if alpha == "pick":
        ref = Xcal @ W + b
        c0 = dict(cfg, wclip=False, aclip=False)
        alpha = min((rel_l2(int_forward(encode2(W, b, Xcal, c0, a, n), Xcal), ref), a)
                    for a in ALPHAS)[1]
    return encode2(W, b, Xcal, cfg, alpha, n)


def slim(enc):
    """Drop golden-only codes; store exact ints as int16 (int_forward casts to f64 per group)."""
    enc.pop("Wq", None)
    for key in ("Wc", "V"):
        a = enc[key]
        assert np.abs(a).max() < 2 ** 15 and np.array_equal(a, np.round(a))
        enc[key] = a.astype(np.int16)
    return enc


def trim():
    """Return freed heap to the OS (limits RSS growth between schemes)."""
    import ctypes
    import gc
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass


# ---------------- outlier statistics ----------------

def outlier_stats(W, Xcal, k=K, n=N_IN):
    """Activation and weight outlier stats, before and after alpha=1 migration."""
    d_in, d_out = W.shape
    ax = np.abs(Xcal).max(axis=0)
    sd = Xcal.std()
    top = np.argsort(-ax)[:5]

    def wstats(Wm):
        m = sigma_mask(Wm)
        seg = m.reshape(d_in // n, n, d_out).sum(axis=1)
        return {"pct_w_over_3sigma": round(100.0 * float(m.mean()), 4),
                "tile_col_max": int(seg.max()), "tile_col_mean": round(float(seg.mean()), 4),
                "pct_tile_cols_over_budget": round(100.0 * float((seg > k).mean()), 4)}

    s = smooth_scales(Xcal, W, 1.0)
    Ws = W * s[:, None]
    m = sigma_mask(Ws)
    sl = np.zeros((d_in // n, n, d_out), bool)
    np.put_along_axis(sl, topk_rows(np.abs(Ws), k), True, axis=1)
    cover = float((m & sl.reshape(d_in, d_out)).sum() / max(m.sum(), 1))
    return {"act_max_abs": round(float(ax.max()), 4), "act_std": round(float(sd), 4),
            "act_max_over_std": round(float(ax.max() / sd), 2),
            "act_pct_over_3sigma": round(100.0 * float((np.abs(Xcal) > SIG * sd).mean()), 4),
            "act_top_channels": [[int(c), round(float(ax[c]), 3)] for c in top],
            "weights_raw": wstats(W), "weights_mig_a1": wstats(Ws),
            "sidecar_3sigma_cover_pct_mig_a1": round(100.0 * cover, 3)}


# ---------------- model side ----------------

def make_qmlp(mlp, enc, d_ff):
    """MLP whose gate/up projections run through the integer path."""
    import torch

    class QMLP(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.orig = mlp

        def forward(self, x):
            sh = x.shape
            y = int_forward(enc, x.detach().reshape(-1, sh[-1]).double().numpy())
            y = torch.from_numpy(y).to(x.dtype).reshape(*sh[:-1], -1)
            return self.orig.down_proj(self.orig.act_fn(y[..., :d_ff]) * y[..., d_ff:])
    return QMLP()


def window_nll(model, windows, encs=None):
    """Mean NLL per window; encs maps layer index -> enc."""
    import torch
    layers = model.model.layers
    d_ff = model.config.intermediate_size
    saved = {}
    for i, enc in (encs or {}).items():
        saved[i] = layers[i].mlp
        layers[i].mlp = make_qmlp(saved[i], enc, d_ff)
    try:
        with torch.no_grad():
            out = [model(w[None, :], labels=w[None, :]).loss.item() for w in windows]
    finally:
        for i, mlp in saved.items():
            layers[i].mlp = mlp
    return np.array(out)


def layer_weights(model, i):
    """[gate^T | up^T] as (d_model, 2*d_ff) float64, zero bias."""
    mlp = model.model.layers[i].mlp
    W = np.concatenate([mlp.gate_proj.weight.detach().double().numpy().T,
                        mlp.up_proj.weight.detach().double().numpy().T], axis=1)
    return W, np.zeros(W.shape[1])


# ---------------- self-tests ----------------

def _selftest():
    rng = np.random.default_rng(13)
    d_in, d_ff = N_IN * 2, 8
    Wg, Wu = rng.normal(0, 0.1, (d_in, d_ff)), rng.normal(0, 0.1, (d_in, d_ff))
    Wg[3, 1] = 1.5
    X = rng.normal(0, 1, (30, d_in))
    X[:, 7] *= 30
    W, b = np.concatenate([Wg, Wu], axis=1), np.zeros(2 * d_ff)
    for name, cfg in SCHEMES:
        enc = pick_encode(W, b, X, cfg)
        assert enc["alpha"] is None or enc["alpha"] in ALPHAS
        assert golden_check(enc, X, [0, 1])
        y64 = int_forward(enc, X)
        assert np.array_equal(int_forward(slim(enc), X), y64)      # float32 storage exact
        # concatenated matrix = gate and up columns side by side
        assert y64.shape == (30, 2 * d_ff)
    st = outlier_stats(W, X)
    assert st["act_top_channels"][0][0] == 7 and st["act_max_over_std"] > 5
    assert st["weights_raw"]["tile_col_max"] >= 1
    print(f"qwen_eval self-test passed ({len(SCHEMES)} schemes)")


# ---------------- main ----------------

def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(THREADS)
    _selftest()
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).eval()
    L = model.config.num_hidden_layers
    ev = tok(load_wikitext("test", 80000))["input_ids"]
    ca = tok(load_wikitext("train", 20000))["input_ids"]
    assert len(ev) >= LONG_EVAL and len(ca) >= CALIB_TOKENS
    ev = torch.tensor(ev[:LONG_EVAL])
    wins = [ev[i:i + WIN] for i in range(0, LONG_EVAL, WIN)]
    n_short = EVAL_TOKENS // WIN
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    Xc = capture(model, names, [torch.tensor(ca[:CALIB_TOKENS])])
    Xe = capture(model, names, wins[:n_short])
    Xc, Xe = [Xc[n] for n in names], [Xe[n] for n in names]
    print(f"{MODEL}: {L} layers, W per layer {layer_weights(model, 0)[0].shape} (gate|up); "
          f"calib {CALIB_TOKENS} tok, eval {LONG_EVAL} tok ({len(wins)} windows of {WIN})")

    # outlier stats: Qwen layer 0 and all layers; GPT-2 h.0 on the same calib text
    st = {"qwen_layer0": outlier_stats(layer_weights(model, 0)[0], Xc[0])}
    per = [outlier_stats(layer_weights(model, i)[0], Xc[i]) for i in range(L)]
    st["qwen_all_layers"] = {
        "act_max_over_std_max": max(p["act_max_over_std"] for p in per),
        "act_max_over_std_median": float(np.median([p["act_max_over_std"] for p in per])),
        "act_max_abs_max": max(p["act_max_abs"] for p in per),
        "pct_w_over_3sigma_mean": round(float(np.mean([p["weights_raw"]["pct_w_over_3sigma"]
                                                        for p in per])), 4),
        "tile_col_max_raw": max(p["weights_raw"]["tile_col_max"] for p in per),
        "tile_col_max_mig_a1": max(p["weights_mig_a1"]["tile_col_max"] for p in per),
        "pct_tile_cols_over_budget_mig_a1_mean": round(float(np.mean(
            [p["weights_mig_a1"]["pct_tile_cols_over_budget"] for p in per])), 4),
        "sidecar_cover_pct_mig_a1_min": min(p["sidecar_3sigma_cover_pct_mig_a1"] for p in per),
        "per_layer_act_max_over_std": [p["act_max_over_std"] for p in per]}
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    gtok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    gpt = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    gl = SPEC["workload"]["layer"]
    gx = capture(gpt, [gl], [torch.tensor(gtok(load_wikitext("train", 20000))["input_ids"]
                                          [:CALIB_TOKENS])])[gl]
    st["gpt2_h0_c_fc"] = outlier_stats(gpt.get_submodule(gl).weight.detach().double().numpy(), gx)
    del gpt
    print("outlier stats:")
    print(json.dumps({k: v for k, v in st.items()}, indent=2))

    part = OUT / "qwen_partial.json"                     # resume after an interruption
    done = json.loads(part.read_text()) if part.exists() else {}
    nll_fp = np.array(done["nll_fp"]) if "nll_fp" in done else window_nll(model, wins)
    rows = done.get("rows", [])
    OUT.mkdir(parents=True, exist_ok=True)
    for name, cfg in SCHEMES:
        if any(r["scheme"] == name for r in rows):
            print(f"  resume: {name} already done", flush=True)
            continue
        encs, errs, alphas = {}, [], []
        for i in range(L):
            W, b = layer_weights(model, i)
            e = pick_encode(W, b, Xc[i], cfg)
            golden_check(e, Xe[i], [0, EVAL_TOKENS - 1] if i == 0 else [0])
            if i == 0:
                err_c0 = rel_l2(int_forward(e, Xc[0]), Xc[0] @ W)
            errs.append(rel_l2(int_forward(e, Xe[i]), Xe[i] @ W))
            alphas.append(e["alpha"])
            encs[i] = slim(e)
            trim()
        n0 = window_nll(model, wins, {0: encs[0]})
        nall = window_nll(model, wins, encs)
        d0, se0 = paired(n0, nll_fp)
        da, sea = paired(nall, nll_fp)
        ds0, ses0 = paired(n0[:n_short], nll_fp[:n_short])
        dsa, sesa = paired(nall[:n_short], nll_fp[:n_short])
        rows.append({"scheme": name, "cfg": cfg, "alpha_l0": alphas[0], "alphas_all": alphas,
                     "err_calib_l0": round(err_c0, 5), "err_eval_l0": round(errs[0], 5),
                     "mean_err_eval_all": round(float(np.mean(errs)), 5),
                     "ppl_l0_short": round(ppl(n0[:n_short]), 4),
                     "ppl_all_short": round(ppl(nall[:n_short]), 4),
                     "d_l0_short": ds0, "se_l0_short": ses0, "d_all_short": dsa,
                     "se_all_short": sesa,
                     "ppl_l0": round(ppl(n0), 4), "d_l0": d0, "se_l0": se0,
                     "ppl_all": round(ppl(nall), 4), "d_all": da, "se_all": sea})
        del encs, e
        trim()
        part.write_text(json.dumps({"nll_fp": nll_fp.tolist(), "rows": rows}))
        print(f"  done {name} ({time.time() - t0:.0f} s, peak RSS {peak_gb():.2f} GB)", flush=True)

    fp_s, fp_l = ppl(nll_fp[:n_short]), ppl(nll_fp)
    print(f"\nQwen2.5-0.5B, gate_proj+up_proj quantized. FP32 ppl: {EVAL_TOKENS} tok {fp_s:.4f}, "
          f"{LONG_EVAL} tok {fp_l:.4f}; FP32 window ppl "
          f"{[round(float(np.exp(v)), 3) for v in nll_fp]}")
    print(f"{'scheme':22s} {'a_L0':>5s} {'err_L0':>8s} {'err_all':>8s} | {EVAL_TOKENS} tok: "
          f"{'ppl_L0':>8s} {'ppl_all':>9s} | {LONG_EVAL} tok: {'ppl_L0':>8s} {'d±se':>15s} "
          f"{'ppl_all':>9s} {'d±se':>17s}")
    for r in rows:
        a = "-" if r["alpha_l0"] is None else f"{r['alpha_l0']:.2f}"
        print(f"{r['scheme']:22s} {a:>5s} {r['err_eval_l0']:8.5f} {r['mean_err_eval_all']:8.5f} | "
              f"{'':>9s} {r['ppl_l0_short']:8.4f} {r['ppl_all_short']:9.4f} | {'':>9s} "
              f"{r['ppl_l0']:8.4f} {r['d_l0']:+8.4f}±{r['se_l0']:.4f} {r['ppl_all']:9.4f} "
              f"{r['d_all']:+9.4f}±{r['se_all']:.4f}")

    OUT.mkdir(parents=True, exist_ok=True)
    out = {"model": MODEL, "target": "mlp.gate_proj + mlp.up_proj (one shared-input matrix)",
           "calib": f"WikiText-2 raw train, first {CALIB_TOKENS} tokens",
           "eval": f"WikiText-2 raw test, first {LONG_EVAL} tokens, windows of {WIN}",
           "alpha_pick": "calib layer error without clips, grid " + str(list(ALPHAS)),
           "ppl_fp32_short": round(fp_s, 4), "ppl_fp32": round(fp_l, 4),
           "fp32_window_ppl": [round(float(np.exp(v)), 3) for v in nll_fp],
           "outlier_stats": st, "rows": rows}
    (OUT / "qwen.json").write_text(json.dumps(out, indent=2))
    part.unlink()
    print(f"saved {OUT / 'qwen.json'} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
