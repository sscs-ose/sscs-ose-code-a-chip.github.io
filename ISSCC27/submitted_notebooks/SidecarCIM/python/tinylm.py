"""Edge study A: SidecarCIM on tiny on-device LMs (TinyStories, GPT-Neo), TinyStories validation.

Usage: python tinylm.py time <size>        1-window timing (FP32 + SidecarCIM) for 1m/3m/8m/33m
       python tinylm.py stats              weight/activation outlier statistics (all sizes + GPT-2)
       python tinylm.py eval <size> [N]    FP32 + 5 schemes on N windows (default: all)
       python tinylm.py report
Models: roneneldan/TinyStories-{1M,3M,8M,33M} (GPT-Neo; d_model 64/128/256/768). Quantized
layers: every transformer.h.i.mlp.c_fc (MLP input projection, same class as GPT-2 c_fc).
Data (roneneldan/TinyStories): eval = the validation split (data/validation parquet), each story
tokenized and followed by <|endoftext|>, concatenated, cut into consecutive non-overlapping
WIN-token windows (partial tail dropped); calib = the first 512 tokens of the train split built
the same way (first row group of data/train-00000, disjoint from validation).
Schemes = fulltest.py (migration + wclip, alpha picked on calib layer error per layer, VB12):
FP32, W4A4+mig+wclip, W6A4+mig+wclip, W8A4+mig+wclip, W8A8, SidecarCIM+wclip k2,VB12. Integer
path golden-checked tile by tile on calib tokens. Stats vs SidecarCIM = fulltest.compare (paired
over windows, TOST margin +-0.25 ppl as asked; also the same RELATIVE margin as GPT-2's,
0.25 / 31.86 of the reference ppl, because TinyStories ppl is far lower).
Outlier stats (per c_fc, on calib): sigma = std of each output channel (as sigma_mask) and,
separately, std inside each 32-row tile column; % of |w| > 3 sigma (Gaussian: 0.27 %),
3-sigma weights per 32-row tile column (max, % of tile columns over k = 2), excess kurtosis,
max |w| / sigma; activations max/std; before and after alpha = 1 migration.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "6")          # small matmuls: do not oversubscribe shared CPUs

import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

from fulltest import compare  # noqa: E402
from golden import ROOT, SPEC  # noqa: E402
from llm_layer import (CALIB_TOKENS, N_IN, OUT, WIDE, capture, golden_check,  # noqa: E402
                       smooth_scales)
from novelty_study import B, encode_pick2, paired, ppl, sigma_mask, window_nll  # noqa: E402

FILE = OUT / "tinylm.json"
K = SPEC["outlier"]["budget_per_output"]
SIG = SPEC["outlier"]["threshold_sigma"]
WIN = 512
CHUNK = 64
SIZES = {"1m": "roneneldan/TinyStories-1M", "3m": "roneneldan/TinyStories-3M",
         "8m": "roneneldan/TinyStories-8M", "33m": "roneneldan/TinyStories-33M"}
DATA = "roneneldan/TinyStories"
VAL = "data/validation-00000-of-00001-869c898b519ad725.parquet"
TRAIN0 = "data/train-00000-of-00004-2d5a1467fff1081b.parquet"
REF = "SidecarCIM+wclip k2,VB12"
GPT2_REF_PPL = 31.860                       # fulltest.json GPT-2 reference ppl (rel. margin)
SCHEMES = [
    (REF, dict(B, k=K, wclip=True, vb=12)),
    ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True)),
    ("W6A4+mig+wclip", dict(B, wbits=6, wclip=True)),
    ("W4A4+mig+wclip", dict(B, wclip=True)),
    ("W8A8", dict(B, wbits=WIDE, abits=WIDE, alpha=None)),
]
THREADS = 6


# ---------------- data ----------------

def val_ids(tok):
    import pandas as pd
    from huggingface_hub import hf_hub_download
    p = hf_hub_download(DATA, VAL, repo_type="dataset")
    texts = pd.read_parquet(p)["text"].tolist()
    ids = []
    for t in tok(texts)["input_ids"]:
        ids += t + [tok.eos_token_id]
    return ids, len(texts)


def calib_ids(tok):
    """First CALIB_TOKENS train tokens (first row group of shard 0 only; cached locally)."""
    cache = ROOT.parent / ".cache" / "sidecarcim" / "tinystories_train_head.json"
    cache = cache if cache.parent.parent.exists() else OUT / ".tinystories_train_head.json"
    if cache.exists():
        texts = json.loads(cache.read_text())
    else:
        import pyarrow.parquet as pq
        from huggingface_hub import HfFileSystem
        with HfFileSystem().open(f"datasets/{DATA}/{TRAIN0}", "rb") as f:
            texts = pq.ParquetFile(f).read_row_group(0, columns=["text"]).column(0).to_pylist()[:50]
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(texts))
    ids = []
    for t in tok(texts)["input_ids"]:
        ids += t + [tok.eos_token_id]
    assert len(ids) >= CALIB_TOKENS
    return ids[:CALIB_TOKENS]


def setup(size):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(THREADS)
    tok = AutoTokenizer.from_pretrained(SIZES[size])
    model = AutoModelForCausalLM.from_pretrained(SIZES[size], dtype=torch.float32).eval()
    ids, n_stories = val_ids(tok)
    ev = torch.tensor(ids)
    nw = len(ids) // WIN
    wins = [ev[i * WIN:(i + 1) * WIN] for i in range(nw)]
    ca = calib_ids(tok)
    names = [f"transformer.h.{i}.mlp.c_fc" for i in range(model.config.num_layers)]
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy().T.copy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    Xc = capture(model, names, [torch.tensor(ca)])
    meta = {"hf_id": SIZES[size], "d_model": model.config.hidden_size,
            "layers": model.config.num_layers, "c_fc_shape": list(Ws[names[0]].shape),
            "params": sum(p.numel() for p in model.parameters()),
            "val_stories": n_stories, "val_tokens": len(ids), "windows_total": nw, "ctx": WIN,
            "dropped_tail_tokens": len(ids) - nw * WIN}
    return model, wins, names, Ws, bs, Xc, meta


# ---------------- storage ----------------

def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


def encode_all(names, Ws, bs, Xc, cfg):
    encs, alphas = {}, []
    for n in names:
        e = encode_pick2(Ws[n], bs[n], Xc[n], cfg)
        golden_check(e, Xc[n], [0, 255, CALIB_TOKENS - 1])
        encs[n] = e
        alphas.append(e["alpha"])
    return encs, alphas


# ---------------- outlier statistics ----------------

def wstats(W, n=N_IN):
    d_in, d_out = W.shape
    m = sigma_mask(W)                                   # sigma per output channel
    seg = m.reshape(d_in // n, n, d_out).sum(axis=1)
    T = W.reshape(d_in // n, n, d_out)
    mt = np.abs(T) > SIG * T.std(axis=1, keepdims=True)  # sigma inside each 32-row tile column
    segt = mt.sum(axis=1)
    z = (W - W.mean(axis=0)) / W.std(axis=0)
    return {"pct_w_over_3sigma": round(100.0 * float(m.mean()), 4),
            "tilecol_max": int(seg.max()), "tilecol_mean": round(float(seg.mean()), 4),
            "pct_tilecols_over_k2": round(100.0 * float((seg > K).mean()), 4),
            "pct_w_over_3sigma_tilestd": round(100.0 * float(mt.mean()), 4),
            "tilecol_max_tilestd": int(segt.max()),
            "pct_tilecols_over_k2_tilestd": round(100.0 * float((segt > K).mean()), 4),
            "excess_kurtosis_mean": round(float((z ** 4).mean(axis=0).mean() - 3.0), 3),
            "max_abs_over_sigma": round(float((np.abs(W) / W.std(axis=0)).max()), 2)}


def layer_stats(W, X):
    ax = np.abs(X).max(axis=0)
    sd = X.std()
    s = smooth_scales(X, W, 1.0)
    return {"act_max_over_std": round(float(ax.max() / sd), 2),
            "act_pct_over_3sigma": round(100.0 * float((np.abs(X) > SIG * sd).mean()), 4),
            "weights_raw": wstats(W), "weights_mig_a1": wstats(W * s[:, None])}


def summarize(per):
    keys = list(per[0]["weights_raw"].keys())
    out = {"act_max_over_std_max": max(p["act_max_over_std"] for p in per),
           "act_max_over_std_median": float(np.median([p["act_max_over_std"] for p in per]))}
    for w in ("weights_raw", "weights_mig_a1"):
        out[w] = {}
        for k in keys:
            v = [p[w][k] for p in per]
            out[w][k] = max(v) if ("max" in k) else round(float(np.mean(v)), 4)
    return out


def stage_stats():
    import torch
    res = load()
    st = {"gaussian_pct_over_3sigma": 0.27, "note": "mean over layers; *max* keys = max"}
    for size in SIZES:
        model, wins, names, Ws, bs, Xc, meta = setup(size)
        per = [layer_stats(Ws[n], Xc[n]) for n in names]
        st[f"tinystories-{size}"] = {"per_layer": per, "summary": summarize(per)}
        res.setdefault("meta", {})[size] = meta
        print(size, json.dumps(st[f"tinystories-{size}"]["summary"]), flush=True)
        del model
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    from llm_layer import fc_names, load_wikitext
    tok = GPT2TokenizerFast.from_pretrained("gpt2")
    gpt = GPT2LMHeadModel.from_pretrained("gpt2").eval()
    names = fc_names(gpt)
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    Xc = capture(gpt, names, [torch.tensor(ca)])
    per = [layer_stats(gpt.get_submodule(n).weight.detach().double().numpy(), Xc[n])
           for n in names]
    st["gpt2"] = {"per_layer": per, "summary": summarize(per),
                  "calib": "WikiText-2 train, first 512 tokens"}
    print("gpt2", json.dumps(st["gpt2"]["summary"]), flush=True)
    res["outlier_stats"] = st
    save(res)


# ---------------- eval ----------------

def stage_time(size):
    t0 = time.time()
    model, wins, names, Ws, bs, Xc, meta = setup(size)
    ts = time.time() - t0
    t1 = time.time()
    window_nll(model, wins[:4])
    tf = (time.time() - t1) / 4
    t1 = time.time()
    encs, _ = encode_all(names, Ws, bs, Xc, dict(SCHEMES)[REF])
    te = time.time() - t1
    t1 = time.time()
    window_nll(model, wins[:4], encs)
    tq = (time.time() - t1) / 4
    est = dict(meta, setup_sec=round(ts, 1), fp32_sec_per_window=round(tf, 3),
               quant_sec_per_window=round(tq, 3), encode_sec=round(te, 1))
    est["full_set_hours"] = round(meta["windows_total"] * (tf + len(SCHEMES) * tq) / 3600, 2)
    res = load()
    res.setdefault("timing", {})[size] = est
    save(res)
    print(json.dumps(est, indent=1))


def stage_eval(size, n_win=None):
    t0 = time.time()
    model, wins, names, Ws, bs, Xc, meta = setup(size)
    nw = len(wins)
    n_win = nw if n_win is None else min(n_win, nw)
    idx = sorted({int(round(v)) for v in np.linspace(0, nw - 1, n_win)})
    res = load()
    res.setdefault("meta", {})[size] = dict(meta, windows_used=len(idx),
                                            selection="all" if len(idx) == nw else
                                            "evenly spaced (np.linspace)")
    U = res["units"]

    def run(key, fn):
        u = U.setdefault(key, {"nll": [], "win_idx": []})
        done = len(u["nll"])
        assert u["win_idx"] == idx[:done]
        for s in range(done, len(idx), CHUNK):
            part = idx[s:s + CHUNK]
            u["nll"] += fn([wins[i] for i in part]).tolist()
            u["win_idx"] += part
            save(res)
        print(f"  {key}: {len(u['nll'])} windows ({time.time() - t0:.0f} s)", flush=True)
        return u

    t1 = time.time()
    u = run(f"{size}|FP32", lambda w: window_nll(model, w))
    u.setdefault("sec", round(time.time() - t1, 1))
    for name, cfg in SCHEMES:
        key = f"{size}|{name}"
        if key in U and len(U[key]["nll"]) == len(idx):
            continue
        t1 = time.time()
        encs, alphas = encode_all(names, Ws, bs, Xc, cfg)
        u = run(key, lambda w: window_nll(model, w, encs))
        u.update(alphas=alphas, sec=round(time.time() - t1, 1))
        if cfg["k"]:
            v = np.concatenate([np.asarray(e["val"]).ravel() for e in encs.values()])
            S = np.concatenate([np.asarray(e["S"]).ravel() for e in encs.values()])
            u["sat_slots_pct"] = round(100.0 * float(((v >= 2047) | (v <= -2048)).mean()), 4)
            u["S_hist"] = {int(a): int(c) for a, c in zip(*np.unique(S, return_counts=True))}
            u["sigma3_cover_pct"] = [e["sigma_cover_pct"] for e in encs.values()]
        save(res)
    report()


def report():
    res = load()
    U = res["units"]
    res["method"] = __doc__.strip()
    res["tables"] = {}
    for size in SIZES:
        fp = U.get(f"{size}|FP32")
        ref = U.get(f"{size}|{REF}")
        if not fp or not ref:
            continue
        n = min(len(fp["nll"]), len(ref["nll"]))
        fpn = np.array(fp["nll"][:n])
        P = ppl(np.array(ref["nll"][:n]))
        rel = round(0.25 * P / GPT2_REF_PPL, 4)
        rows = [{"scheme": "FP32", "ppl": round(ppl(fpn), 4),
                 "vs_sidecar": compare(fpn, ref["nll"][:n])}]
        for name, _ in SCHEMES:
            u = U.get(f"{size}|{name}")
            if not u or len(u["nll"]) < n:
                continue
            a = np.array(u["nll"][:n])
            d, se = paired(a, fpn)
            row = {"scheme": name, "ppl": round(ppl(a), 4), "d_vs_fp32": d, "se_vs_fp32": se,
                   "rel_d_vs_fp32_pct": round(100.0 * d / ppl(fpn), 3)}
            if name != REF:
                row["vs_sidecar"] = compare(a, ref["nll"][:n])
                row["vs_sidecar_rel_margin"] = compare(a, ref["nll"][:n], margin=rel)
            else:
                row.update({k: u[k] for k in ("sat_slots_pct", "S_hist") if k in u})
            rows.append(row)
        res["tables"][size] = {"windows": n, "rel_margin_ppl": rel, "rows": rows}
        print(f"\nTinyStories-{size.upper()}: {n} windows of {WIN}; FP32 {ppl(fpn):.4f}; "
              f"rel margin ±{rel}")
        for r in rows:
            v = r.get("vs_sidecar")
            dfp = (f"{r['d_vs_fp32']:+.4f}±{r['se_vs_fp32']:.4f} ({r['rel_d_vs_fp32_pct']:+.2f}%)"
                   if "d_vs_fp32" in r else "")
            if r["scheme"] == REF:
                print(f"  {r['scheme']:26s} {r['ppl']:8.4f} {dfp}  (reference)")
                continue
            vr = r.get("vs_sidecar_rel_margin", {})
            print(f"  {r['scheme']:26s} {r['ppl']:8.4f} {dfp:28s} diff {v['dppl']:+.4f} "
                  f"[{v['ci90_dppl'][0]:+.4f},{v['ci90_dppl'][1]:+.4f}] p {v['p_two_sided']:.3g} "
                  f"TOST0.25 p {v['tost_p']:.3g} | rel TOST p {vr.get('tost_p', float('nan')):.3g}")
    save(res)


if __name__ == "__main__":
    st = sys.argv[1]
    if st == "time":
        stage_time(sys.argv[2])
    elif st == "stats":
        stage_stats()
    elif st == "eval":
        stage_eval(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
    else:
        report()
