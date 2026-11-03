"""Extra runs: paired SEs at 8192 tokens, slot rules, calib-slice seeds, figure arrays.

Usage: python extras.py gpt2 | qwen | arrays | report   (each stage resumes from extras.json)
gpt2  : W4A4 naive (no migration) all 12 c_fc; SidecarCIM+wclip (side-mag-k2+wclip) vs
        per-tile-scale+wclip (W4A4+mig+tile+wclip) with paired difference; slot rules mag/greedy/
        hybrid at k=2 + wclip, all at 8192 test tokens (8 windows of 1024); then the three rules
        on two other 512-token calib slices (train tokens 1024:1536, 2048:2560) at 2048 tokens.
qwen  : same SidecarCIM+wclip vs per-tile+wclip pair on Qwen2.5-0.5B (24 layers), 8192 tokens.
arrays: python/out/arrays.npz for figures (activation per-channel max/std, 3sigma tile-column
        count histograms before/after alpha=1.0 migration).
Difference stats: dppl = ppl(a) - ppl(b) from per-window NLL, SE by leave-one-window-out jackknife
(also mean NLL difference per window with its SE). Same data/windows as novelty_study / qwen_eval.
"""
import json
import sys
import time

import numpy as np

from golden import SPEC
from llm_layer import (CALIB_TOKENS, N_IN, OUT, capture, fc_names, golden_check, load_wikitext,
                       smooth_scales)
from novelty_study import B, encode_pick2, paired, ppl, sigma_mask, window_nll

FILE = OUT / "extras.json"
ARR = OUT / "arrays.npz"
K = SPEC["outlier"]["budget_per_output"]
LONG = 8192
SHORT = SPEC["workload"]["eval_tokens"]
SLICES = (1024, 2048)                       # extra calib slices (train token offsets)
GP = {"w4a4_naive": dict(B, alpha=None),
      "side_mag_k2_wclip": dict(B, k=K, wclip=True),
      "tile_wclip": dict(B, tile=True, wclip=True),
      "side_greedy_k2_wclip": dict(B, k=K, sel="greedy", wclip=True),
      "side_hybrid_k2_wclip": dict(B, k=K, sel="hybrid", wclip=True)}
RULES = ("side_mag_k2_wclip", "side_greedy_k2_wclip", "side_hybrid_k2_wclip")


def diff_stats(a, b):
    """Paired difference of two schemes from per-window NLL arrays."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    d = a - b
    full = ppl(a) - ppl(b)
    loo = np.array([ppl(np.delete(a, i)) - ppl(np.delete(b, i)) for i in range(n)])
    se = float(np.sqrt((n - 1) / n * ((loo - loo.mean()) ** 2).sum()))
    se_d = float(d.std(ddof=1) / np.sqrt(n))
    return {"dppl": round(full, 4), "se_jackknife": round(se, 4),
            "mean_dnll": round(float(d.mean()), 5), "se_dnll": round(se_d, 5),
            "t": round(float(d.mean() / se_d), 2) if se_d > 0 else None, "windows": n}


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(res, indent=1))


def _selftest():
    a = np.array([3.0, 3.1, 3.2, 3.3])
    z = diff_stats(a, a)
    assert z["dppl"] == 0 and z["se_jackknife"] == 0
    s = diff_stats(a + 0.1, a)
    assert s["dppl"] > 0 and s["t"] is None or s["t"] > 5   # constant shift, zero spread
    r = diff_stats(np.array([3.0, 3.2, 3.1, 3.4]), np.array([3.1, 3.1, 3.0, 3.2]))
    assert r["windows"] == 4 and r["se_jackknife"] > 0
    print("extras self-test passed")


# ---------------- GPT-2 ----------------

def stage_gpt2():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    torch.set_num_threads(6)
    t0 = time.time()
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ctx = model.config.n_positions
    ev = torch.tensor(tok(load_wikitext("test", 80000))["input_ids"][:LONG])
    wins = [ev[i:i + ctx] for i in range(0, LONG, ctx)]
    ca = tok(load_wikitext("train", 20000))["input_ids"]
    names = fc_names(model)
    h0 = SPEC["workload"]["layer"]
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    res = load()
    U = res["units"]

    def run(key, cfg, calib_off, windows):
        """Encode all 12 layers (alpha picked per layer) and store per-window NLL."""
        if key in U:
            return
        Xc = capture(model, names, [torch.tensor(ca[calib_off:calib_off + CALIB_TOKENS])])
        Xe0 = capture(model, [h0], windows[:1])[h0]
        encs, alphas = {}, []
        for n in names:
            e = encode_pick2(Ws[n], bs[n], Xc[n], cfg)
            if n == h0:
                golden_check(e, Xe0, [0])
            encs[n] = e
            alphas.append(e["alpha"])
        U[key] = {"nll": window_nll(model, windows, encs).tolist(), "alphas": alphas}
        save(res)
        print(f"  {key} ({time.time() - t0:.0f} s)", flush=True)
        del encs

    if "fp32" not in U:
        U["fp32"] = {"nll": window_nll(model, wins).tolist()}
        save(res)
    for key, cfg in GP.items():
        run(key + "@8192", cfg, 0, wins)
    for off in SLICES:
        for key in RULES:
            run(f"{key}@2048@calib{off}", GP[key], off, wins[:SHORT // ctx])
    report()


# ---------------- Qwen ----------------

def stage_qwen():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import qwen_eval as q
    torch.set_num_threads(q.THREADS)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(q.MODEL)
    model = AutoModelForCausalLM.from_pretrained(q.MODEL, dtype=torch.float32).eval()
    L = model.config.num_hidden_layers
    ev = torch.tensor(tok(load_wikitext("test", 80000))["input_ids"][:LONG])
    wins = [ev[i:i + q.WIN] for i in range(0, LONG, q.WIN)]
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    Xc = capture(model, names, [torch.tensor(ca)])
    Xc = [Xc[n] for n in names]
    res = load()
    U = res["units"]
    if "qwen_fp32" not in U:
        U["qwen_fp32"] = {"nll": q.window_nll(model, wins).tolist()}
        save(res)
    cfgs = dict(q.SCHEMES)
    for key, name in (("qwen_side_mag_k2_wclip@8192", "SidecarCIM+wclip"),
                      ("qwen_tile_wclip@8192", "W4A4+mig+tile+wclip")):
        if key in U:
            continue
        encs, alphas = {}, []
        for i in range(L):
            W, b = q.layer_weights(model, i)
            e = q.pick_encode(W, b, Xc[i], cfgs[name])
            golden_check(e, Xc[i], [0])
            alphas.append(e["alpha"])
            encs[i] = q.slim(e)
            q.trim()
        U[key] = {"nll": q.window_nll(model, wins, encs).tolist(), "alphas": alphas}
        save(res)
        print(f"  {key} ({time.time() - t0:.0f} s, peak RSS {q.peak_gb():.2f} GB)", flush=True)
        del encs
        q.trim()
    report()


# ---------------- arrays ----------------

def tilecol_hist(W, s, nbin=16):
    """Histogram of 3sigma outlier counts per 32-input tile column (counts clipped at nbin-1)."""
    Wm = W * s[:, None]
    m = sigma_mask(Wm)
    cnt = m.reshape(W.shape[0] // N_IN, N_IN, W.shape[1]).sum(axis=1)
    return np.bincount(np.minimum(cnt, nbin - 1).ravel(), minlength=nbin), int(cnt.max())


def stage_arrays():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, GPT2LMHeadModel, GPT2TokenizerFast
    import qwen_eval as q
    torch.set_num_threads(6)
    arr = {"hist_bins": np.arange(16)}
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    names = fc_names(model)
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    Xc = capture(model, names, [torch.tensor(ca)])
    h0 = SPEC["workload"]["layer"]
    x = Xc[h0]
    arr["gpt2_h0_act_absmax"] = np.abs(x).max(axis=0).astype(np.float32)
    arr["gpt2_h0_act_std"] = x.std(axis=0).astype(np.float32)
    s0 = smooth_scales(x, model.get_submodule(h0).weight.detach().double().numpy(), 1.0)
    arr["gpt2_h0_act_absmax_mig_a1"] = (np.abs(x).max(axis=0) / s0).astype(np.float32)
    raw, mig, mx = [], [], []
    for n in names:
        W = model.get_submodule(n).weight.detach().double().numpy()
        s = smooth_scales(Xc[n], W, 1.0)
        hr, m1 = tilecol_hist(W, np.ones_like(s))
        hm, m2 = tilecol_hist(W, s)
        raw.append(hr), mig.append(hm), mx.append((m1, m2))
    arr["gpt2_tilecol3sig_hist_raw"] = np.array(raw)        # (12, 16)
    arr["gpt2_tilecol3sig_hist_mig_a1"] = np.array(mig)
    arr["gpt2_tilecol3sig_max_raw_mig"] = np.array(mx)      # (12, 2)
    arr["gpt2_h0_tilecol3sig_hist_raw"] = arr["gpt2_tilecol3sig_hist_raw"][0]
    arr["gpt2_h0_tilecol3sig_hist_mig_a1"] = arr["gpt2_tilecol3sig_hist_mig_a1"][0]
    del model
    qt = AutoTokenizer.from_pretrained(q.MODEL)
    qm = AutoModelForCausalLM.from_pretrained(q.MODEL, dtype=torch.float32).eval()
    L = qm.config.num_hidden_layers
    qn = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    Xq = capture(qm, qn, [torch.tensor(qt(load_wikitext("train", 20000))["input_ids"]
                                       [:CALIB_TOKENS])])
    arr["qwen_act_absmax"] = np.stack([np.abs(Xq[n]).max(axis=0) for n in qn]).astype(np.float32)
    arr["qwen_act_std"] = np.stack([Xq[n].std(axis=0) for n in qn]).astype(np.float32)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARR, **arr)
    for k, v in arr.items():
        print(f"  {k}: {v.shape}")
    print(f"saved {ARR}")


# ---------------- report ----------------

def report():
    res = load()
    U = res["units"]
    fp = np.array(U["fp32"]["nll"]) if "fp32" in U else None
    if fp is not None:
        print(f"\nGPT-2 8192 tok (8 windows), all 12 c_fc; FP32 ppl {ppl(fp):.4f}")
        for key in GP:
            u = U.get(key + "@8192")
            if u:
                d, se = paired(np.array(u["nll"]), fp)
                print(f"  {key:22s} ppl {ppl(np.array(u['nll'])):9.4f}  d {d:+9.4f} ± {se:.4f}")
        a, b = U.get("side_mag_k2_wclip@8192"), U.get("tile_wclip@8192")
        if a and b:
            print("  SidecarCIM+wclip - tile+wclip:", diff_stats(a["nll"], b["nll"]))
        for r in ("side_greedy_k2_wclip", "side_hybrid_k2_wclip"):
            c = U.get(r + "@8192")
            if a and c:
                print(f"  {r} - side_mag_k2_wclip:", diff_stats(c["nll"], a["nll"]))
        for off in SLICES:
            row = {r: U.get(f"{r}@2048@calib{off}") for r in RULES}
            if all(row.values()):
                print(f"  2048 tok, calib slice {off}:512: " + ", ".join(
                    f"{r} {ppl(np.array(v['nll'])):.4f}" for r, v in row.items()),
                    f"(FP32 {ppl(fp[:2]):.4f})")
    if "qwen_fp32" in U:
        qf = np.array(U["qwen_fp32"]["nll"])
        print(f"\nQwen2.5-0.5B 8192 tok (8 windows), 24 layers; FP32 ppl {ppl(qf):.4f}")
        for key in ("qwen_side_mag_k2_wclip@8192", "qwen_tile_wclip@8192"):
            if key in U:
                d, se = paired(np.array(U[key]["nll"]), qf)
                print(f"  {key:30s} ppl {ppl(np.array(U[key]['nll'])):9.4f}  d {d:+9.4f} ± {se:.4f}")
        if "qwen_side_mag_k2_wclip@8192" in U and "qwen_tile_wclip@8192" in U:
            print("  SidecarCIM+wclip - tile+wclip:", diff_stats(
                U["qwen_side_mag_k2_wclip@8192"]["nll"], U["qwen_tile_wclip@8192"]["nll"]))


if __name__ == "__main__":
    _selftest()
    {"gpt2": stage_gpt2, "qwen": stage_qwen, "arrays": stage_arrays,
     "report": report}[sys.argv[1]]()
