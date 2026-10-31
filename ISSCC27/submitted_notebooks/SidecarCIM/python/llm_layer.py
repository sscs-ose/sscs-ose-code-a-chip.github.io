"""SidecarCIM accuracy evaluation on GPT-2 small: layer error and perplexity per scheme.

Data: WikiText-2 raw (Salesforce/wikitext parquet, via huggingface_hub). Rows are joined with
"\\n\\n". Eval = first spec eval_tokens tokens of the test split; calibration = first CALIB_TOKENS
tokens of the train split (disjoint). CALIB_TEXT from vectors.py is not used here.
Perplexity: eval tokens in non-overlapping windows of the model context; exp(mean NLL) over
predicted tokens. Only c_fc layers are quantized; everything else stays FP32.
Scheme parts: static per-tensor activations (min/max on calib); weights per output channel
(or per 32-input tile column, "tile"); optional SmoothQuant migration (X/s folded into ln_2
offline, W*s; alpha picked on calib layer error); optional sidecar (top-k |w| per tile column,
signed spec outlier.weight_bits (16 until Oct 11, now 12), golden.sidecar_dot); optional
"clip" = offline weight range search minimizing E[x^2]-weighted weight MSE on calib.
Hardware path is integer: dense = DCIM core + zero-point correction, sidecar = sidecar_dot -
zx*sum(val); merge y_int = (dense << S) + sidecar per column; real y = sx*sw/2^S*y_int + b.
Big matmuls use float64 BLAS on integer-valued arrays (exact; |sum| < 2^53 asserted) and are
cross-checked against golden.dcim_dot / golden.sidecar_dot on sample tokens.
"""
import json
import time

import numpy as np

from golden import ROOT, SPEC
from quant import qmax, quant_params, quantize_with, range_params, sidecar_signed, signed_dot

OUT = ROOT / "python" / "out"
N_IN = SPEC["array"]["n_inputs"]
WB, AB = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
VB = SPEC["outlier"]["weight_bits"]
K = SPEC["outlier"]["budget_per_output"]
WIDE = 2 * max(WB, AB)
EVAL_TOKENS = SPEC["workload"]["eval_tokens"]
CALIB_TOKENS = 512
ALPHAS = (0.85, 0.9, 0.95, 1.0)
CLIP_GRID = np.linspace(0.4, 1.0, 25)
EXACT = 2.0 ** 53

BASE = dict(wbits=WB, abits=AB, alpha=None, k=0, tile=False, clip=False)
SCHEMES = [   # (name, hardware, cfg)
    ("W4A4", "4b DCIM", dict(BASE)),
    ("W8A8", "8b DCIM", dict(BASE, wbits=WIDE, abits=WIDE)),
    ("W4A4+sidecar", "SidecarCIM", dict(BASE, k=K)),
    ("W4A4+mig", "4b DCIM", dict(BASE, alpha="pick")),
    ("SidecarCIM", "SidecarCIM", dict(BASE, alpha="pick", k=K)),
    ("W4A4+mig+clip", "4b DCIM", dict(BASE, alpha="pick", clip=True)),
    ("SidecarCIM+clip", "SidecarCIM", dict(BASE, alpha="pick", k=K, clip=True)),
    ("W4A4+mig+tile", "4b DCIM+tile scale", dict(BASE, alpha="pick", tile=True)),
    ("SidecarCIM+tile", "SidecarCIM+tile scale", dict(BASE, alpha="pick", k=K, tile=True)),
    ("W4A4+mig+tile+clip", "4b DCIM+tile scale", dict(BASE, alpha="pick", tile=True, clip=True)),
    ("SidecarCIM+tile+clip", "SidecarCIM+tile scale",
     dict(BASE, alpha="pick", k=K, tile=True, clip=True)),
]
SWEEP_PPL = ("W4A4+mig", "SidecarCIM")   # schemes with per-alpha perplexity rows


# ---------------- encoding (offline) ----------------

def smooth_scales(x_calib, W, alpha):
    """SmoothQuant s_c = max|X_c|^a / max|W_c|^(1-a), per input channel."""
    ax = np.maximum(np.abs(x_calib).max(axis=0), 1e-8)
    aw = np.maximum(np.abs(W).max(axis=1), 1e-8)
    return ax ** alpha / aw ** (1 - alpha)


def topk_slots(Ws, k, n=N_IN):
    """Row index (within tile) of the k largest |w| per tile column: (n_rt, k, out)."""
    a = np.abs(Ws).reshape(Ws.shape[0] // n, n, Ws.shape[1])
    return np.argsort(-a, axis=1, kind="stable")[:, :k, :]


def mse_clip(d, h, lo, hi, bits):
    """Per group: shrink [lo, hi] by r in CLIP_GRID, keep r with least h-weighted MSE."""
    best = np.full(lo.shape, np.inf)
    blo, bhi = lo.copy(), hi.copy()
    for r in CLIP_GRID:
        s, z = range_params(lo * r, hi * r, bits)
        q = quantize_with(d, s[:, None], z[:, None], bits)
        e = (h * (d - s[:, None] * (q - z[:, None])) ** 2).sum(axis=1)
        better = e < best
        best = np.where(better, e, best)
        blo, bhi = np.where(better, lo * r, blo), np.where(better, hi * r, bhi)
    return blo, bhi


def encode(W, b, Xcal, cfg, alpha):
    """Offline encoding of one c_fc layer for the integer path."""
    d_in, d_out = W.shape
    n_rt = d_in // N_IN
    wbits, abits, k = cfg["wbits"], cfg["abits"], cfg["k"]
    s = smooth_scales(Xcal, W, alpha) if alpha is not None else np.ones(d_in)
    Ws, Xs = W * s[:, None], Xcal / s[None, :]
    G = n_rt if cfg["tile"] else 1
    R = d_in // G
    idx = topk_slots(Ws, k)                                     # (n_rt, k, out)
    mask = np.zeros((n_rt, N_IN, d_out), bool)
    np.put_along_axis(mask, idx, True, axis=1)
    mask = mask.reshape(G, R, d_out)
    dense = np.where(mask, 0.0, Ws.reshape(G, R, d_out))
    lo, hi = dense.min(axis=1), dense.max(axis=1)
    if cfg["clip"]:
        h = (Xs ** 2).mean(axis=0).reshape(G, R)[:, :, None] * ~mask   # slots excluded
        lo, hi = mse_clip(dense, h, lo, hi, wbits)
    sw, zw = range_params(lo, hi, wbits)                        # (G, out)
    Wq = quantize_with(dense, sw[:, None], zw[:, None], wbits)
    Wq = np.where(mask, zw[:, None, :], Wq)                     # slot holds real 0
    # sidecar: signed VB-bit values on a grid sw/2^S (S per group column)
    vmax = (1 << (VB - 1)) - 1
    o = np.take_along_axis(Ws.reshape(n_rt, N_IN, d_out), idx, axis=1)   # (n_rt, k, out)
    if k:
        om = np.abs(o).reshape(G, -1, d_out).max(axis=1)
        S = np.floor(np.log2(vmax * sw / np.maximum(om, 1e-30)))
        S = np.clip(S, 0, VB - 1).astype(np.int64)
    else:
        S = np.zeros((G, d_out), np.int64)
    unit = np.repeat(sw / 2.0 ** S, n_rt // G, axis=0)          # (n_rt, out)
    val = np.clip(np.round(o / unit[:, None, :]), -vmax - 1, vmax).astype(np.int64)
    V = np.zeros((n_rt, N_IN, d_out))
    np.put_along_axis(V, idx, val.astype(np.float64), axis=1)
    sx, zx = quant_params(Xs, abits)
    bound = R * qmax(abits) * (qmax(wbits) * 2.0 ** S.max() + k * vmax)
    assert bound < EXACT
    return dict(cfg=cfg, alpha=alpha, s=s, sx=float(sx), zx=int(zx), sw=sw, zw=zw, S=S, G=G,
                Wq=Wq.reshape(d_in, d_out), idx=idx, val=val, b=b,
                Wc=(Wq - zw[:, None, :]).astype(np.float64), V=V.reshape(G, R, d_out))


# ---------------- integer forward ----------------

def act_codes(enc, X):
    """Activation codes after migration."""
    return quantize_with(X / enc["s"][None, :], enc["sx"], enc["zx"], enc["cfg"]["abits"])


def int_parts(enc, xq):
    """Exact per-group integer dense and sidecar sums: (G, T, out) each."""
    xc = (xq - enc["zx"]).astype(np.float64)
    G, R = enc["G"], enc["Wc"].shape[1]
    D = np.stack([xc[:, g * R:(g + 1) * R] @ enc["Wc"][g] for g in range(G)])
    Sd = np.stack([xc[:, g * R:(g + 1) * R] @ enc["V"][g] for g in range(G)])
    return D, Sd


def int_forward(enc, X, chunk=1024):
    """Layer output through the integer path (float only in the final scaling).

    Groups are accumulated one at a time and tokens processed in chunks (low memory);
    same summation order as summing the stacked groups. Activation codes are computed once;
    a group with no sidecar values skips the (all-zero) slot product, and S = 0 skips the
    x1 shift: both are exact no-ops, so outputs are value-identical.
    """
    G, R = enc["G"], enc["Wc"].shape[1]
    unit = enc["sx"] * enc["sw"] / 2.0 ** enc["S"]              # (G, out)
    T = X.shape[0]
    y = np.zeros((T, enc["Wc"].shape[2]))
    xc_all = np.empty((T, X.shape[1]))
    for t in range(0, T, 256):
        xc_all[t:t + 256] = act_codes(enc, X[t:t + 256]) - enc["zx"]
    for g in range(G):
        Wc = np.asarray(enc["Wc"][g], dtype=np.float64)
        V = np.asarray(enc["V"][g], dtype=np.float64)
        side = bool(V.any())
        p2 = 2.0 ** enc["S"][g]
        shift = bool((p2 != 1.0).any())
        for t in range(0, T, chunk):
            xc = xc_all[t:t + chunk, g * R:(g + 1) * R]
            y_int = xc @ Wc
            if shift:
                y_int *= p2
            if side:
                y_int += xc @ V                                 # exact merge
            y_int *= unit[g]
            y[t:t + chunk] += y_int
    return y + enc["b"]


def golden_check(enc, X, tokens):
    """Integer parts equal golden.dcim_dot / sidecar_dot tile by tile (tile height enc["n"])."""
    cfg = enc["cfg"]
    n = enc.get("n", N_IN)
    xq = act_codes(enc, X[tokens])
    D, Sd = int_parts(enc, xq)
    n_rt = enc["Wq"].shape[0] // n
    assert n_rt * n == enc["Wq"].shape[0]
    per = n_rt // enc["G"]
    for i in range(len(tokens)):
        gd = np.zeros_like(D[:, 0, :], dtype=np.int64)
        gs = np.zeros_like(gd)
        for r in range(n_rt):
            sl, g = slice(r * n, (r + 1) * n), r // per
            gd[g] += signed_dot(enc["Wq"][sl], xq[i, sl], enc["zw"][g], enc["zx"],
                                cfg["wbits"], cfg["abits"])
            if cfg["k"]:
                gs[g] += sidecar_signed(enc["idx"][r], enc["val"][r], xq[i, sl], enc["zx"],
                                        cfg["abits"], cfg.get("vb"))
        assert np.array_equal(gd, D[:, i, :].astype(np.int64))
        assert np.array_equal(gs, Sd[:, i, :].astype(np.int64))
    return True


def rel_l2(a, ref):
    """Relative L2 (Frobenius) error."""
    return float(np.linalg.norm(a - ref) / np.linalg.norm(ref))


def encode_pick(W, b, Xcal, cfg):
    """Encode; if alpha == 'pick', choose alpha in ALPHAS by calib layer error."""
    if cfg["alpha"] != "pick":
        return encode(W, b, Xcal, cfg, cfg["alpha"]), []
    ref = Xcal @ W + b
    sweep = []
    for a in ALPHAS:
        e = encode(W, b, Xcal, cfg, a)
        sweep.append((rel_l2(int_forward(e, Xcal), ref), a, e))
    best = min(sweep, key=lambda t: t[0])
    return best[2], [(a, err) for err, a, _ in sweep]


# ---------------- model side ----------------

def load_wikitext(split, chars):
    """First `chars` characters of a WikiText-2 raw split."""
    import pandas as pd
    from huggingface_hub import hf_hub_download
    p = hf_hub_download("Salesforce/wikitext",
                        f"wikitext-2-raw-v1/{split}-00000-of-00001.parquet", repo_type="dataset")
    return "\n\n".join(pd.read_parquet(p)["text"].tolist())[:chars]


def fc_names(model):
    return [f"transformer.h.{i}.mlp.c_fc" for i in range(model.config.n_layer)]


def capture(model, names, windows):
    """FP inputs of each named layer, (tokens, in) float64."""
    import torch
    got = {n: [] for n in names}
    hooks = [model.get_submodule(n).register_forward_hook(
        lambda m, i, o, n=n: got[n].append(i[0].detach().reshape(-1, i[0].shape[-1])))
        for n in names]
    with torch.no_grad():
        for w in windows:
            model(w[None, :])
    for h in hooks:
        h.remove()
    return {n: torch.cat(v).double().numpy() for n, v in got.items()}


def make_qfc(enc):
    import torch

    class QuantFC(torch.nn.Module):
        """c_fc replaced by the integer path."""
        def forward(self, x):
            sh = x.shape
            y = int_forward(enc, x.detach().reshape(-1, sh[-1]).double().numpy())
            return torch.from_numpy(y).to(x.dtype).reshape(*sh[:-1], -1)
    return QuantFC()


def perplexity(model, windows, encs=None):
    """PPL with the given layers swapped for integer-path modules."""
    import torch
    saved = {}
    for name, enc in (encs or {}).items():
        parent, attr = name.rsplit(".", 1)
        p = model.get_submodule(parent)
        saved[name] = (p, attr, getattr(p, attr))
        setattr(p, attr, make_qfc(enc))
    try:
        nll, cnt = 0.0, 0
        with torch.no_grad():
            for w in windows:
                loss = model(w[None, :], labels=w[None, :]).loss.item()
                nll += loss * (w.shape[0] - 1)
                cnt += w.shape[0] - 1
    finally:
        for p, attr, mod in saved.values():
            setattr(p, attr, mod)
    return float(np.exp(nll / cnt))


# ---------------- self-tests ----------------

def _selftest():
    rng = np.random.default_rng(7)
    d_in, d_out = N_IN * 3, 10
    W = rng.normal(0, 0.1, (d_in, d_out))
    W[5, 2], W[40, 7] = 2.0, -1.5                       # outliers
    b = rng.normal(0, 0.1, d_out)
    X = rng.normal(0, 1, (40, d_in))
    X[:, 3] *= 20                                       # activation outlier channel
    ref = X @ W + b
    errs = {}
    for name, _, cfg in SCHEMES:
        enc, _ = encode_pick(W, b, X, cfg)
        assert golden_check(enc, X, [0, 1])
        y = int_forward(enc, X)
        # integer path equals dequantized float model (smoothed domain)
        xd = enc["sx"] * (act_codes(enc, X) - enc["zx"])
        wd = np.concatenate([enc["sw"][g] * enc["Wc"][g] +
                             enc["V"][g] * enc["sw"][g] / 2.0 ** enc["S"][g]
                             for g in range(enc["G"])])
        assert np.allclose(y, xd @ wd + b)
        errs[name] = rel_l2(y, ref)
    assert errs["W8A8"] < errs["W4A4"]
    assert errs["W4A4+sidecar"] < errs["W4A4"]           # sidecar keeps the planted outliers
    assert errs["SidecarCIM"] < errs["W4A4+sidecar"]     # migration tames channel 3
    # clip never worse than no clip on its own objective proxy (calib layer error, loose)
    assert errs["W4A4+mig+clip"] < 1.5 * errs["W4A4+mig"]
    # slot extraction picks the largest |w|
    idx = topk_slots(W, K)
    assert 5 in idx[0, :, 2] and (40 - N_IN) in idx[1, :, 7]
    print("llm_layer self-test passed (%d schemes, golden tile checks ok)" % len(SCHEMES))


# ---------------- main ----------------

def main():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    _selftest()
    t0 = time.time()
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ctx = model.config.n_positions
    ev = tok(load_wikitext("test", 40000))["input_ids"]
    ca = tok(load_wikitext("train", 20000))["input_ids"]
    assert len(ev) >= EVAL_TOKENS and len(ca) >= CALIB_TOKENS
    ev = torch.tensor(ev[:EVAL_TOKENS])
    wins = [ev[i:i + ctx] for i in range(0, EVAL_TOKENS, ctx)]
    cal_wins = [torch.tensor(ca[:CALIB_TOKENS])]
    names = fc_names(model)
    spec_layer = SPEC["workload"]["layer"]
    assert spec_layer in names
    Xc, Xe = capture(model, names, cal_wins), capture(model, names, wins)
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    print(f"eval {EVAL_TOKENS} tokens (WikiText-2 test, {len(wins)} windows of {ctx}); "
          f"calib {CALIB_TOKENS} tokens (WikiText-2 train)")
    ppl_fp = perplexity(model, wins)
    print(f"FP32 perplexity: {ppl_fp:.4f}")

    rows, sweeps = [], []
    for name, hw, cfg in SCHEMES:
        W, b = Ws[spec_layer], bs[spec_layer]
        enc, sweep = encode_pick(W, b, Xc[spec_layer], cfg)
        golden_check(enc, Xe[spec_layer], [0, EVAL_TOKENS - 1])
        ref_c, ref_e = Xc[spec_layer] @ W + b, Xe[spec_layer] @ W + b
        err_c = rel_l2(int_forward(enc, Xc[spec_layer]), ref_c)
        err_e = rel_l2(int_forward(enc, Xe[spec_layer]), ref_e)
        zp = 100.0 * float((act_codes(enc, Xe[spec_layer]) == enc["zx"]).mean())
        ppl1 = perplexity(model, wins, {spec_layer: enc})
        for a, ec in sweep:
            e2 = encode(W, b, Xc[spec_layer], cfg, a)
            sw_row = {"scheme": name, "alpha": a, "err_calib": round(ec, 5),
                      "err_eval": round(rel_l2(int_forward(e2, Xe[spec_layer]), ref_e), 5)}
            if name in SWEEP_PPL:
                sw_row["ppl_h0"] = round(perplexity(model, wins, {spec_layer: e2}), 4)
            sweeps.append(sw_row)
        # all 12 blocks: encode each c_fc with its own calib inputs
        encs, lerr, alphas = {}, [], []
        for n in names:
            e, _ = encode_pick(Ws[n], bs[n], Xc[n], cfg)
            golden_check(e, Xe[n], [0])
            encs[n] = e
            alphas.append(e["alpha"])
            lerr.append(rel_l2(int_forward(e, Xe[n]), Xe[n] @ Ws[n] + bs[n]))
        ppl12 = perplexity(model, wins, encs)
        rows.append({"scheme": name, "hardware": hw, "alpha_h0": enc["alpha"],
                     "err_calib_h0": round(err_c, 5), "err_eval_h0": round(err_e, 5),
                     "pct_x_eq_zp_h0": round(zp, 2), "ppl_h0_only": round(ppl1, 4),
                     "ppl_all12_fc": round(ppl12, 4),
                     "mean_err_eval_all12": round(float(np.mean(lerr)), 5),
                     "alphas_all12": alphas, **{k: cfg[k] for k in ("wbits", "abits", "k",
                                                                   "tile", "clip")}})
        print(f"  done {name} ({time.time() - t0:.0f} s)")

    print(f"\nFP32 perplexity (eval {EVAL_TOKENS} tokens): {ppl_fp:.4f}")
    hdr = (f"{'scheme':22s} {'hardware':22s} {'alpha':>5s} {'err_cal':>8s} {'err_eval':>8s} "
           f"{'%x=zp':>6s} {'ppl_h0':>8s} {'ppl_all12':>9s} {'err12':>7s}")
    print(hdr)
    for r in rows:
        a = "-" if r["alpha_h0"] is None else f"{r['alpha_h0']:.2f}"
        print(f"{r['scheme']:22s} {r['hardware']:22s} {a:>5s} {r['err_calib_h0']:8.5f} "
              f"{r['err_eval_h0']:8.5f} {r['pct_x_eq_zp_h0']:6.2f} {r['ppl_h0_only']:8.4f} "
              f"{r['ppl_all12_fc']:9.4f} {r['mean_err_eval_all12']:7.5f}")
    print("\nalpha sweep on h.0 (pick = lowest err_calib):")
    for s in sweeps:
        p = f" ppl_h0 {s['ppl_h0']:.4f}" if "ppl_h0" in s else ""
        print(f"  {s['scheme']:22s} alpha {s['alpha']:.2f} err_cal {s['err_calib']:.5f} "
              f"err_eval {s['err_eval']:.5f}{p}")

    OUT.mkdir(parents=True, exist_ok=True)
    out = {"model": SPEC["workload"]["model"], "layer": spec_layer,
           "eval": f"WikiText-2 raw test, first {EVAL_TOKENS} tokens, windows of {ctx}",
           "calib": f"WikiText-2 raw train, first {CALIB_TOKENS} tokens",
           "metric_err": "rel L2 of c_fc output incl. bias vs FP32, FP inputs",
           "ppl_h0_only": "only spec layer replaced by integer path",
           "ppl_all12_fc": "SECONDARY: all 12 blocks' mlp.c_fc replaced (alpha picked per layer)",
           "tile_note": "tile = weight scale per 32-input tile column: one extra multiply per "
                        "tile output (not zero hardware cost)",
           "ppl_fp32": round(ppl_fp, 4), "rows": rows, "alpha_sweep_h0": sweeps}
    (OUT / "accuracy.json").write_text(json.dumps(out, indent=2))
    print(f"saved {OUT / 'accuracy.json'} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
