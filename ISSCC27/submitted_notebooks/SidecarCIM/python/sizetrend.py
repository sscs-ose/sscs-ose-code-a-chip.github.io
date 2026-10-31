"""Study F: model-size trend. Where does the sidecar start to matter?

Usage: python sizetrend.py time <key>          1-window timing (FP32 + SidecarCIM)
       python sizetrend.py eval <key> [N]      FP32 + 4 schemes on N windows (default: all)
       python sizetrend.py stats               outlier statistics (SmolLM2 x3, GPT-2, Qwen)
       python sizetrend.py report
Models: HuggingFaceTB/SmolLM2-{135M,360M,1.7B} (Llama, Apache-2.0, not gated). New points use the
Qwen protocol of fulltest.py: the MLP input projections [gate_proj | up_proj] of every layer
as one shared-input matrix (qwen_eval.layer_weights / window_nll / pick_encode: alpha picked
on calib layer error without clip, final encode with wclip), golden tile checks on 3 calib
tokens per layer. Calib = first 512 WikiText-2 train tokens; eval = consecutive 1024-token
windows of the WikiText-2 test split (N evenly spaced if N is given; stated in the output).
Schemes: FP32, W4A4 / W6A4 / W8A4 + mig + wclip, SidecarCIM+wclip k2,VB12. Stats vs SidecarCIM
= fulltest.compare (paired t, TOST ±0.25 ppl).
Other points in the report (not rerun): GPT-2 and Qwen2.5-0.5B from out/fulltest.json (same
data and protocol), TinyStories-1M..33M from out/tinylm.json (TinyStories validation, 512-token
windows, a different dataset: shown, flagged).
Outlier stats (tinylm.layer_stats, on the MLP-input layers, calib tokens): activation max/std,
weight excess kurtosis, % |w| > 3 sigma, % of 32-row tile columns with > 2 such weights.
Trend: gain_over_W6A4 = ppl(W6A4) - ppl(SidecarCIM), paired; positive = the sidecar is better.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "6")

import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

from fulltest import CHUNK, compare  # noqa: E402
from fulltest_extra import wait_no_docker  # noqa: E402
from fulltest import FILE as FT_FILE  # noqa: E402
from golden import SPEC  # noqa: E402
from llm_layer import CALIB_TOKENS, OUT, capture, golden_check, load_wikitext  # noqa: E402
from novelty_study import B, paired, ppl  # noqa: E402

FILE = OUT / "sizetrend.json"
K = SPEC["outlier"]["budget_per_output"]
WIN = 1024
MODELS = {"smollm2-135m": "HuggingFaceTB/SmolLM2-135M",
          "smollm2-360m": "HuggingFaceTB/SmolLM2-360M",
          "smollm2-1.7b": "HuggingFaceTB/SmolLM2-1.7B"}
REF = "SidecarCIM+wclip k2,VB12"
W6 = "W6A4+mig+wclip"
SCHEMES = [(REF, dict(B, k=K, wclip=True, vb=12)),
           (W6, dict(B, wbits=6, wclip=True)),
           ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True)),
           ("W4A4+mig+wclip", dict(B, wclip=True))]


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


def setup(hf):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(6)
    tok = AutoTokenizer.from_pretrained(hf)
    model = AutoModelForCausalLM.from_pretrained(hf, dtype=torch.float32).eval()
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    ev = torch.tensor(ids)
    wins = [ev[i * WIN:(i + 1) * WIN] for i in range(len(ids) // WIN)]
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    L = model.config.num_hidden_layers
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    X = capture(model, names, [torch.tensor(ca)])
    meta = {"hf_id": hf, "params": sum(p.numel() for p in model.parameters()),
            "d_model": model.config.hidden_size, "d_ff": model.config.intermediate_size,
            "layers": L, "test_tokens": len(ids), "windows_total": len(wins), "ctx": WIN}
    return model, wins, [X[n] for n in names], meta


LOWMEM = os.environ.get("SIZETREND_LOWMEM") == "1"   # 1.7B: free gate/up after encoding
# layers kept in FP (e.g. "7": the layer whose MLP creates the attention-sink activation)
FPLAYERS = sorted(int(v) for v in os.environ.get("SIZETREND_FPLAYERS", "").split(",") if v)
SUFFIX = "|fp" + "-".join(map(str, FPLAYERS)) if FPLAYERS else ""
# sink rule: the first token of each window (the attention-sink token) runs its MLP-input
# projections with the original weights; every other token goes through the integer path
SINKFP = os.environ.get("SIZETREND_SINKFP") == "1"
if SINKFP:
    SUFFIX += "|sink0fp"
SINK_Y = {}                      # first token id -> [layer -> FP gate|up output of token 0]
SINK_CUR = [None]                # first token id of the window being evaluated


def encode_all(model, Xc, cfg):
    """Encode every layer's [gate|up]. LOWMEM: the FP gate/up weights of a layer are freed right
    after it is encoded (the integer path replaces them), so one process encodes one scheme."""
    import torch
    import qwen_eval as q
    encs, alphas = {}, []
    for i in range(len(Xc)):
        if i in FPLAYERS:
            continue
        W, b = q.layer_weights(model, i)
        e = q.pick_encode(W, b, Xc[i], cfg)
        golden_check(e, Xc[i], [0, 255, CALIB_TOKENS - 1])
        alphas.append(e["alpha"])
        encs[i] = q.slim(e)
        del W, e
        if LOWMEM:
            mlp = model.model.layers[i].mlp
            for lin in (mlp.gate_proj, mlp.up_proj):
                lin.weight = torch.nn.Parameter(torch.empty(0), requires_grad=False)
        q.trim()
    return encs, alphas


def sink_window_nll(model, windows, encs):
    """qwen_eval.window_nll, but token 0 of each window uses the original gate/up weights."""
    import torch
    from llm_layer import int_forward
    layers = model.model.layers
    d_ff = model.config.intermediate_size

    def qmlp(mlp, enc, i):
        class QMLP(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.orig = mlp

            def forward(self, x):
                sh = x.shape
                y = int_forward(enc, x.detach().reshape(-1, sh[-1]).double().numpy())
                y = torch.from_numpy(y).to(x.dtype).reshape(*sh[:-1], -1)
                y[:, 0, :] = SINK_Y[SINK_CUR[0]][i].to(x.dtype)        # sink token in FP
                return self.orig.down_proj(self.orig.act_fn(y[..., :d_ff]) * y[..., d_ff:])
        return QMLP()
    saved = {}
    for i, enc in encs.items():
        saved[i] = layers[i].mlp
        layers[i].mlp = qmlp(saved[i], enc, i)
    try:
        with torch.no_grad():
            out = []
            for w in windows:
                SINK_CUR[0] = int(w[0])
                out.append(model(w[None, :], labels=w[None, :]).loss.item())
    finally:
        for i, mlp in saved.items():
            layers[i].mlp = mlp
    return np.array(out)


def sink_precompute(model, first_ids):
    """FP gate|up outputs of token 0 for each distinct first token. Token 0 attends only to
    itself and, under the sink rule, every layer it passes is FP, so a 1-token FP forward
    gives exactly its values inside any window."""
    import torch
    layers = model.model.layers
    for t in sorted(set(first_ids)):
        got = {}
        hooks = []
        for i, lay in enumerate(layers):
            for j, lin in enumerate((lay.mlp.gate_proj, lay.mlp.up_proj)):
                hooks.append(lin.register_forward_hook(
                    lambda m, a, o, i=i, j=j: got.__setitem__((i, j), o[0, 0].detach().clone())))
        with torch.no_grad():
            model(torch.tensor([[t]]))
        for h in hooks:
            h.remove()
        SINK_Y[t] = {i: torch.cat([got[(i, 0)], got[(i, 1)]]) for i in range(len(layers))}


def stage_time(key):
    import qwen_eval as q
    t0 = time.time()
    model, wins, Xc, meta = setup(MODELS[key])
    ts = time.time() - t0
    t1 = time.time()
    q.window_nll(model, wins[:1])
    tf = time.time() - t1
    t1 = time.time()
    encs, _ = encode_all(model, Xc, dict(SCHEMES)[REF])
    te = time.time() - t1
    t1 = time.time()
    q.window_nll(model, wins[:1], encs)
    tq = time.time() - t1
    est = dict(meta, setup_sec=round(ts, 1), fp32_sec_per_window=round(tf, 2),
               quant_sec_per_window=round(tq, 2), encode_sec=round(te, 1),
               peak_rss_gb=round(q.peak_gb(), 2))
    est["full_set_hours"] = round((meta["windows_total"] * (tf + len(SCHEMES) * tq) +
                                   len(SCHEMES) * te) / 3600, 2)
    res = load()
    res.setdefault("timing", {})[key] = est
    save(res)
    print(json.dumps(est, indent=1))


def stage_eval(key, n_win=None):
    import qwen_eval as q
    t0 = time.time()
    model, wins, Xc, meta = setup(MODELS[key])
    nw = len(wins)
    n_win = nw if n_win is None else min(n_win, nw)
    idx = sorted({int(round(v)) for v in np.linspace(0, nw - 1, n_win)})
    res = load()
    res.setdefault("meta", {})[key] = dict(meta, windows_used=len(idx),
                                           selection="all" if len(idx) == nw else
                                           "evenly spaced (np.linspace)")
    U = res["units"]

    def run(k, fn):
        u = U.setdefault(k, {"nll": [], "win_idx": []})
        done = len(u["nll"])
        assert u["win_idx"] == idx[:done]
        for s in range(done, len(idx), CHUNK):
            wait_no_docker()
            pt = idx[s:s + CHUNK]
            u["nll"] += fn([wins[i] for i in pt]).tolist()
            u["win_idx"] += pt
            save(res)
            print(f"    {k}: {len(u['nll'])}/{len(idx)} ({time.time() - t0:.0f} s)", flush=True)
        return u

    run(f"{key}|FP32", lambda w: q.window_nll(model, w))
    if SINKFP:                      # before any FP weight is freed
        sink_precompute(model, [int(wins[i][0]) for i in idx])
    for name, cfg in SCHEMES:
        if os.environ.get("SIZETREND_ONLY") not in (None, "", name):
            continue
        k = f"{key}|{name}{SUFFIX}"
        if k in U and len(U[k]["nll"]) == len(idx):
            continue
        t1 = time.time()
        wait_no_docker()
        encs, alphas = encode_all(model, Xc, cfg)
        print(f"  {k}: encoded in {time.time() - t1:.0f} s, peak RSS {q.peak_gb():.1f} GB",
              flush=True)
        u = run(k, lambda w, e=encs: (sink_window_nll(model, w, e) if SINKFP
                                      else q.window_nll(model, w, e)))
        u.update(alphas=alphas, sec=round(time.time() - t1, 1))
        save(res)
        del encs
        q.trim()
        if LOWMEM:                      # FP weights are gone: next scheme in a new process
            break
    report()


def stage_diag(key):
    """Per layer and scheme (one layer encoded at a time): layer error on calib and on the first
    256 test tokens, alpha, slot saturation, largest |w| (after migration) in dense steps."""
    import qwen_eval as q
    from llm_layer import int_forward, rel_l2
    model, wins, Xc, meta = setup(MODELS[key])
    L = len(Xc)
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    Xe = capture(model, names, [wins[0][:256]])
    Xe = [Xe[n] for n in names]
    out = {}
    for name, cfg in SCHEMES:
        rows = []
        for i in range(L):
            W, b = q.layer_weights(model, i)
            e = q.pick_encode(W, b, Xc[i], cfg)
            Ws = W * e["s"][:, None]
            step = e["sw"][0]
            v = np.asarray(e["val"])
            vb = cfg.get("vb", 12)
            rows.append({"layer": i, "alpha": e["alpha"],
                         "err_calib": round(rel_l2(int_forward(e, Xc[i]), Xc[i] @ W), 5),
                         "err_test": round(rel_l2(int_forward(e, Xe[i]), Xe[i] @ W), 5),
                         "max_w_over_step": round(float((np.abs(Ws).max(axis=0) / step).max()), 1),
                         "sat_slots": int(((v >= (1 << (vb - 1)) - 1) |
                                           (v <= -(1 << (vb - 1)))).sum()) if v.size else 0,
                         "act_max_over_std_test": round(float(np.abs(Xe[i]).max() /
                                                              Xe[i].std()), 1)})
            del e, W, Ws
            q.trim()
        out[name] = rows
        worst = max(rows, key=lambda r: r["err_test"])
        print(f"{name}: worst layer {worst}", flush=True)
    res = load()
    res.setdefault("diag", {})[key] = out
    save(res)


def stage_anomaly(key, n_bad=2, n_good=1):
    """Failing vs normal windows: per layer and scheme, layer error on that window's FP inputs,
    % activation codes outside the calib range (clipped), max |x/s| over the calib max."""
    import qwen_eval as q
    from llm_layer import int_forward, rel_l2
    res = load()
    U = res["units"]
    ref = U[f"{key}|{REF}"]
    nll = np.array(ref["nll"])
    order = np.argsort(-nll)
    bad = [ref["win_idx"][i] for i in order[:n_bad]]
    good = [ref["win_idx"][i] for i in order[::-1][:n_good]]
    model, wins, Xc, meta = setup(MODELS[key])
    L = len(Xc)
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    sel = bad + good
    Xw = [capture(model, names, [wins[w]]) for w in sel]
    out = {"bad_windows": bad, "good_windows": good,
           "nll": {str(w): {n: float(U[f"{key}|{n}"]["nll"][U[f"{key}|{n}"]["win_idx"].index(w)])
                            for n, _ in SCHEMES if f"{key}|{n}" in U} for w in sel},
           "layers": {}}
    for name, cfg in SCHEMES[:3]:                       # SidecarCIM, W6A4, W8A4
        rows = []
        for i in range(L):
            W, b = q.layer_weights(model, i)
            e = q.pick_encode(W, b, Xc[i], cfg)
            qa = (1 << cfg["abits"]) - 1
            lo_c, hi_c = (0 - e["zx"]) * e["sx"], (qa - e["zx"]) * e["sx"]   # calib range of X/s
            r = {"layer": i, "alpha": e["alpha"]}
            for w, X in zip(sel, Xw):
                x = X[names[i]]
                xs = x / e["s"][None, :]
                clip = (xs < lo_c - e["sx"] / 2) | (xs > hi_c + e["sx"] / 2)
                r[str(w)] = {"err": round(rel_l2(int_forward(e, x), x @ W), 4),
                             "pct_clipped": round(100.0 * float(clip.mean()), 4),
                             "max_over_calib": round(float(np.abs(xs).max() /
                                                           max(abs(lo_c), abs(hi_c))), 2)}
            rows.append(r)
            del e, W
            q.trim()
        out["layers"][name] = rows
        worst = sorted(rows, key=lambda r: -r[str(bad[0])]["err"])[:3]
        print(name, "worst layers on bad window", bad[0], ":",
              [(r["layer"], r[str(bad[0])], r[str(good[0])]["err"]) for r in worst], flush=True)
    res = load()
    res.setdefault("anomaly", {})[key] = out
    save(res)


def stage_cascade(key, name):
    """Where does a failing window diverge? FP vs quantized-path inputs of every MLP (one bad,
    one good window), plus the NLL of both, for one scheme (one process; LOWMEM-safe)."""
    import qwen_eval as q
    res = load()
    an = res["anomaly"][key]
    sel = [an["bad_windows"][0], an["good_windows"][0]]
    model, wins, Xc, meta = setup(MODELS[key])
    L = len(Xc)

    def mlp_inputs(encs=None):
        got = {}
        layers = model.model.layers

        def grab(i):
            def hook(m, args, kwargs):
                h = args[0] if args else kwargs["hidden_states"]
                got.setdefault(i, []).append(h.detach().reshape(-1, h.shape[-1]).clone())
            return hook
        hooks = [layers[i].register_forward_pre_hook(grab(i), with_kwargs=True)
                 for i in range(L)]
        nll = q.window_nll(model, [wins[w] for w in sel], encs)
        for h in hooks:
            h.remove()
        return got, nll
    fp, nll_fp = mlp_inputs()                      # residual stream entering each block
    encs, _ = encode_all(model, Xc, dict(SCHEMES)[name])
    qq, nll_q = mlp_inputs(encs)
    rows = []
    for i in range(L):
        r = {"layer": i}
        for j, w in enumerate(sel):
            a, b = fp[i][j].double(), qq[i][j].double()
            r[str(w)] = {"rel_diff": round(float((a - b).norm() / a.norm()), 5),
                         "fp_max": round(float(a.abs().max()), 1),
                         "q_max": round(float(b.abs().max()), 1),
                         "worst_token": int((a - b).norm(dim=-1).argmax())}
        rows.append(r)
    out = {"windows": sel, "nll_fp": nll_fp.tolist(), "nll_q": nll_q.tolist(), "layers": rows}
    res = load()
    res.setdefault("cascade", {}).setdefault(key, {})[name + SUFFIX] = out
    save(res)
    print(name, "NLL fp", nll_fp, "q", nll_q, flush=True)
    for r in rows:
        print(f"  L{r['layer']:2d} " + "  ".join(
            f"w{w}: diff {r[str(w)]['rel_diff']:.4f} max fp {r[str(w)]['fp_max']} "
            f"q {r[str(w)]['q_max']} tok {r[str(w)]['worst_token']}" for w in sel), flush=True)


def stage_stats():
    import torch
    from tinylm import layer_stats, summarize
    import qwen_eval as q
    res = load()
    st = res.setdefault("outlier_stats", {})
    for key, hf in list(MODELS.items()) + [("qwen2.5-0.5b", "Qwen/Qwen2.5-0.5B")]:
        model, wins, Xc, meta = setup(hf)
        per = [layer_stats(q.layer_weights(model, i)[0], Xc[i]) for i in range(len(Xc))]
        st[key] = {"params": meta["params"], "summary": summarize(per), "per_layer": per,
                   "layers": "mlp gate|up"}
        print(key, json.dumps(st[key]["summary"]), flush=True)
        del model
        save(res)
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    from llm_layer import fc_names
    tok = GPT2TokenizerFast.from_pretrained("gpt2")
    gpt = GPT2LMHeadModel.from_pretrained("gpt2").eval()
    names = fc_names(gpt)
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    X = capture(gpt, names, [torch.tensor(ca)])
    per = [layer_stats(gpt.get_submodule(n).weight.detach().double().numpy(), X[n])
           for n in names]
    st["gpt2"] = {"params": sum(p.numel() for p in gpt.parameters()),
                  "summary": summarize(per), "per_layer": per, "layers": "mlp c_fc"}
    print("gpt2", json.dumps(st["gpt2"]["summary"]), flush=True)
    save(res)


def table(nll, ref_key, fp_key, names, idx=None):
    fp = np.array(nll[fp_key]["nll"])
    ref = np.array(nll[ref_key]["nll"])
    if idx is not None:
        fp = fp[idx]
    rows = {"FP32": {"ppl": round(ppl(fp), 4)}}
    for name, k in names:
        if k not in nll or len(nll[k]["nll"]) < len(ref):
            continue
        a = np.array(nll[k]["nll"][:len(ref)])
        d, se = paired(a, fp)
        r = {"ppl": round(ppl(a), 4), "d_vs_fp32": d, "se_vs_fp32": se,
             "rel_d_pct": round(100.0 * d / ppl(fp), 3)}
        if k != ref_key:
            r["vs_sidecar"] = compare(a, ref)
        rows[name] = r
    return {"windows": len(ref), "rows": rows}


def report():
    res = load()
    U = res["units"]
    FT = json.loads(FT_FILE.read_text())["units"]
    names = [REF, W6, "W8A4+mig+wclip", "W4A4+mig+wclip"]
    pts = {}
    for key in MODELS:
        if f"{key}|{REF}" in U:
            idx = U[f"{key}|{REF}"]["win_idx"]
            sub = {k: v for k, v in U.items() if k.startswith(key + "|")}
            sub[f"{key}|FP32"] = {"nll": list(np.array(U[f"{key}|FP32"]["nll"])[
                [U[f"{key}|FP32"]["win_idx"].index(i) for i in idx]])}
            sf = "|sink0fp" if f"{key}|{REF}|sink0fp" in U else ""   # 1.7B: sink rule (H)
            pts[key] = dict(table(sub, f"{key}|{REF}{sf}", f"{key}|FP32",
                                  [(n, f"{key}|{n}{sf}") for n in names]),
                            dataset="WikiText-2 test" + (
                                "; sink rule: token 0 of each window keeps its FP MLP-input "
                                "outputs (all schemes)" if sf else ""),
                            params=res["meta"][key]["params"], sink_rule=bool(sf))
    for m, p in (("gpt2", 124439808), ("qwen", 494032768)):
        pts[{"gpt2": "gpt2", "qwen": "qwen2.5-0.5b"}[m]] = dict(
            table(FT, f"{m}|{REF}", f"{m}|FP32", [(n, f"{m}|{n}") for n in names]),
            dataset="WikiText-2 test (fulltest.json)", params=p)
    tl = OUT / "tinylm.json"
    if tl.exists():
        T = json.loads(tl.read_text())
        for size in ("1m", "3m", "8m", "33m"):
            if f"{size}|{REF}" in T["units"]:
                pts[f"tinystories-{size}"] = dict(
                    table(T["units"], f"{size}|{REF}", f"{size}|FP32",
                          [(n, f"{size}|{n}") for n in names]),
                    dataset="TinyStories validation (tinylm.json, 512-token windows)",
                    params=T["meta"][size]["params"])
    st = res.get("outlier_stats", {})
    trend = []
    for k, v in sorted(pts.items(), key=lambda kv: kv[1]["params"]):
        r = v["rows"]
        if W6 not in r:
            continue
        g = r[W6]["vs_sidecar"]
        o = st.get(k, {}).get("summary") or (
            json.loads(tl.read_text())["outlier_stats"].get(k, {}).get("summary")
            if tl.exists() else None)
        trend.append({"model": k, "params": v["params"], "dataset": v["dataset"],
                      "sink_rule": v.get("sink_rule", False),
                      "windows": v["windows"], "fp32_ppl": r["FP32"]["ppl"],
                      "sidecar_d_vs_fp32": r[REF]["d_vs_fp32"],
                      "gain_over_W6A4_ppl": round(g["dppl"], 4),
                      "gain_over_W6A4_rel_pct": round(100.0 * g["dppl"] / r[REF]["ppl"], 3),
                      "gain_ci90": [round(g["ci90_dppl"][0], 4), round(g["ci90_dppl"][1], 4)],
                      "p": g["p_two_sided"],
                      "act_max_over_std_max": o and o["act_max_over_std_max"],
                      "w_kurtosis_mig": o and o["weights_mig_a1"]["excess_kurtosis_mean"],
                      "w_kurtosis_raw": o and o["weights_raw"]["excess_kurtosis_mean"],
                      "pct_tilecols_over_k2_mig":
                          o and o["weights_mig_a1"]["pct_tilecols_over_k2"]})
    res["method"] = __doc__.strip()
    res["points"] = pts
    res["trend"] = trend
    save(res)
    print(f"{'model':16s} {'params':>12s} {'FP32':>8s} {'side d':>8s} {'gain/W6':>9s} "
          f"{'rel%':>6s} {'p':>9s} {'act max/std':>11s} {'kurt mig':>8s} {'%tc>2':>7s}")
    for t in trend:
        print(f"{t['model']:16s} {t['params']:12,d} {t['fp32_ppl']:8.3f} "
              f"{t['sidecar_d_vs_fp32']:+8.3f} {t['gain_over_W6A4_ppl']:+9.3f} "
              f"{t['gain_over_W6A4_rel_pct']:+6.2f} {t['p']:9.2g} {t['act_max_over_std_max']} "
              f"{t['w_kurtosis_mig']} {t['pct_tilecols_over_k2_mig']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "time":
        stage_time(a[1])
    elif a[0] == "eval":
        stage_eval(a[1], int(a[2]) if len(a) > 2 else None)
    elif a[0] == "stats":
        stage_stats()
    elif a[0] == "diag":
        stage_diag(a[1])
    elif a[0] == "anomaly":
        stage_anomaly(a[1])
    elif a[0] == "cascade":
        stage_cascade(a[1], a[2])
    else:
        report()
