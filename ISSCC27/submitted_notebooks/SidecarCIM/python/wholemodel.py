"""Study E: whole-model coverage; every linear layer except the LM head in the integer path.

Usage: python wholemodel.py gpt2|qwen all [N]          all four layer types, FP32 + 5 schemes
       python wholemodel.py gpt2|qwen types [N]        one layer type at a time (REF, W6A4, W8A4)
       python wholemodel.py gpt2|qwen allbut <type> [N]  all types except <type>
       python wholemodel.py report
Layer types (one shared-input matrix each, like qwen_eval's [gate|up]):
  attn_qkv  GPT-2 attn.c_attn; Qwen [q_proj | k_proj | v_proj] (one activation stream, biases kept)
  attn_o    GPT-2 attn.c_proj; Qwen o_proj
  mlp_in    GPT-2 mlp.c_fc;    Qwen [gate_proj | up_proj]   (= the fulltest.py layers)
  mlp_down  GPT-2 mlp.c_proj;  Qwen down_proj  (input = post-activation, the large outliers)
Grouped modules (Qwen q/k/v, gate/up) share one integer forward per input tensor; each module
returns its column slice. Encoders and protocol = fulltest.py (GPT-2 encode_pick2, Qwen
qwen_eval.pick_encode; migration + wclip, alpha picked per layer on calib layer error, k2 VB12;
calib = first 512 WikiText-2 train tokens, FP inputs; golden tile checks on 3 calib tokens per
layer). Migration is applied in the integer path (X / s before the activation quantizer), so it
needs no fold into a preceding norm. Windows: 1024-token windows of the WikiText-2 test split,
the same as fulltest.py; N evenly spaced windows when N is given (stated in the output). FP32
per-window NLL comes from out/fulltest.json. Per-type layer error = rel L2 of each layer output
(incl. bias) on the FP inputs of the first 256 test tokens.
"""
import json
import os
import sys
import time

import numpy as np

from fulltest import CHUNK, compare
from fulltest_extra import wait_no_docker
from fulltest import FILE as FT_FILE
from golden import SPEC
from llm_layer import (CALIB_TOKENS, OUT, WIDE, capture, golden_check, int_forward,
                       load_wikitext, rel_l2)
from novelty_study import B, encode_pick2, paired, ppl

FILE = OUT / "wholemodel.json"
K = SPEC["outlier"]["budget_per_output"]
REF = "SidecarCIM+wclip k2,VB12"
SCHEMES = [(REF, dict(B, k=K, wclip=True, vb=12)),
           ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True)),
           ("W6A4+mig+wclip", dict(B, wbits=6, wclip=True)),
           ("W4A4+mig+wclip", dict(B, wclip=True)),
           ("W8A8", dict(B, wbits=WIDE, abits=WIDE, alpha=None))]
TYPE_SCHEMES = (REF, "W6A4+mig+wclip", "W8A4+mig+wclip")
TYPES = ("attn_qkv", "attn_o", "mlp_in", "mlp_down")
XE_TOKENS = 256                 # first test tokens used for the per-type layer error


# ---------------- model description ----------------

def groups(model, m):
    """[(type, layer index, [module names], [out sizes])] for every quantized matrix."""
    out = []
    if m == "gpt2":
        for i in range(model.config.n_layer):
            p = f"transformer.h.{i}."
            for t, n in (("attn_qkv", "attn.c_attn"), ("attn_o", "attn.c_proj"),
                         ("mlp_in", "mlp.c_fc"), ("mlp_down", "mlp.c_proj")):
                mod = model.get_submodule(p + n)
                out.append((t, i, [p + n], [mod.weight.shape[1]]))
    else:
        for i in range(model.config.num_hidden_layers):
            p = f"model.layers.{i}."
            qkv = ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj"]
            for t, ns in (("attn_qkv", qkv),
                          ("attn_o", ["self_attn.o_proj"]),
                          ("mlp_in", ["mlp.gate_proj", "mlp.up_proj"]),
                          ("mlp_down", ["mlp.down_proj"])):
                mods = [model.get_submodule(p + n) for n in ns]
                out.append((t, i, [p + n for n in ns], [x.out_features for x in mods]))
    return out


def weights(model, names):
    """(W (in, out), b (out,)) float64 of a module group (columns concatenated)."""
    Ws, bs = [], []
    for n in names:
        mod = model.get_submodule(n)
        w = mod.weight.detach().double().numpy()
        if type(mod).__name__ != "Conv1D":           # nn.Linear: (out, in)
            w = w.T
        Ws.append(w)
        bs.append(mod.bias.detach().double().numpy() if mod.bias is not None
                  else np.zeros(w.shape[1]))
    return np.concatenate(Ws, axis=1), np.concatenate(bs)


class Shared:
    """One integer forward per input tensor for a module group."""

    def __init__(self, enc):
        self.enc, self.x, self.y = enc, None, None

    def __call__(self, x):
        import torch
        if self.x is not x:
            sh = x.shape
            y = int_forward(self.enc, x.detach().reshape(-1, sh[-1]).double().numpy())
            self.x, self.y = x, torch.from_numpy(y).to(x.dtype).reshape(*sh[:-1], -1)
        return self.y


def part(shared, lo, hi):
    import torch

    class Part(torch.nn.Module):
        def forward(self, x):
            return shared(x)[..., lo:hi]
    return Part()


def window_nll(model, wins, encs, grp):
    """Per-window mean NLL with the given groups (key -> enc) swapped for the integer path."""
    import torch
    saved = []
    for g in grp:
        key = f"{g[0]}.{g[1]}"
        if key not in encs:
            continue
        sh = Shared(encs[key])
        lo = 0
        for n, o in zip(g[2], g[3]):
            parent, attr = n.rsplit(".", 1)
            pm = model.get_submodule(parent)
            saved.append((pm, attr, getattr(pm, attr)))
            setattr(pm, attr, part(sh, lo, lo + o))
            lo += o
    try:
        with torch.no_grad():
            out = [model(w[None, :], labels=w[None, :]).loss.item() for w in wins]
    finally:
        for pm, attr, mod in saved:
            setattr(pm, attr, mod)
    return np.array(out)


# ---------------- setup ----------------

def setup(m):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(6)
    hf = SPEC["workload"]["model"] if m == "gpt2" else "Qwen/Qwen2.5-0.5B"
    tok = AutoTokenizer.from_pretrained(hf)
    model = AutoModelForCausalLM.from_pretrained(hf, dtype=torch.float32).eval()
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    ev = torch.tensor(ids)
    wins = [ev[i * 1024:(i + 1) * 1024] for i in range(len(ids) // 1024)]
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    grp = groups(model, m)
    first = [g[2][0] for g in grp]
    Xc = capture(model, first, [torch.tensor(ca)])
    Xe = capture(model, first, [wins[0][:XE_TOKENS]])
    return model, wins, grp, Xc, Xe


def encode_group(m, model, g, Xc, cfg):
    import qwen_eval as q
    W, b = weights(model, g[2])
    X = Xc[g[2][0]]
    e = encode_pick2(W, b, X, cfg) if m == "gpt2" else q.pick_encode(W, b, X, cfg)
    golden_check(e, X, [0, 255, CALIB_TOKENS - 1])
    return e, W, b


# ---------------- storage ----------------

def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


# ---------------- stages ----------------

def stage(m, mode, arg=None, n_win=None):
    import qwen_eval as q
    t0 = time.time()
    model, wins, grp, Xc, Xe = setup(m)
    nw = len(wins)
    n_win = nw if n_win is None else min(n_win, nw)
    idx = sorted({int(round(v)) for v in np.linspace(0, nw - 1, n_win)})
    FT = json.loads(FT_FILE.read_text())["units"]
    assert FT[f"{m}|FP32"]["win_idx"][:nw] == list(range(nw))
    res = load()
    meta = res.setdefault("meta", {}).setdefault(m, {})
    meta.update({"windows_total": nw, f"{mode}_windows": len(idx),
                 f"{mode}_win_idx_first_last": [idx[0], idx[-1]],
                 "quantized_groups": len(grp),
                 "types": {t: sum(1 for g in grp if g[0] == t) for t in TYPES}})
    if mode == "all":
        jobs = [(f"{m}|all|{n}", n, c, TYPES) for n, c in SCHEMES]
    elif mode == "types":
        jobs = [(f"{m}|only_{t}|{n}", n, c, (t,)) for n, c in SCHEMES for t in TYPES
                if n in TYPE_SCHEMES]
    else:
        assert mode == "allbut" and arg in TYPES
        keep = tuple(t for t in TYPES if t != arg)
        jobs = [(f"{m}|allbut_{arg}|{n}", n, c, keep) for n, c in SCHEMES]
    U = res["units"]
    cache = {}
    for key, name, cfg, types in jobs:
        u = U.get(key)
        if u and len(u["nll"]) == len(idx):
            continue
        t1 = time.time()
        wait_no_docker()
        if name not in cache:                      # encode every group once per scheme
            cache.clear()
            q.trim()
            encs, err, alphas = {}, {t: [] for t in TYPES}, {t: [] for t in TYPES}
            for g in grp:
                e, W, b = encode_group(m, model, g, Xc, cfg)
                X = Xe[g[2][0]]
                err[g[0]].append(rel_l2(int_forward(e, X), X @ W + b))
                alphas[g[0]].append(e["alpha"])
                encs[f"{g[0]}.{g[1]}"] = q.slim(e)
            cache[name] = encs
            res.setdefault("layer_error", {}).setdefault(m, {})[name] = {
                t: {"mean": round(float(np.mean(v)), 5), "max": round(float(np.max(v)), 5),
                    "per_layer": [round(x, 5) for x in v]} for t, v in err.items()}
            res.setdefault("alphas", {}).setdefault(m, {})[name] = alphas
            save(res)
            print(f"  {m} {name}: encoded {len(grp)} groups in {time.time() - t1:.0f} s; "
                  f"layer err " + ", ".join(f"{t} {np.mean(v):.4f}/{np.max(v):.4f}"
                                            for t, v in err.items()), flush=True)
        encs = {k: v for k, v in cache[name].items() if k.split(".")[0] in types}
        u = U.setdefault(key, {"nll": [], "win_idx": []})
        done = len(u["nll"])
        assert u["win_idx"] == idx[:done]
        for s in range(done, len(idx), CHUNK):
            wait_no_docker()
            pt = idx[s:s + CHUNK]
            u["nll"] += window_nll(model, [wins[i] for i in pt], encs, grp).tolist()
            u["win_idx"] += pt
            save(res)
            print(f"    {key}: {len(u['nll'])}/{len(idx)} ({time.time() - t0:.0f} s)", flush=True)
        u["sec"] = round(time.time() - t1, 1)
        save(res)
    report()


def diag(m, typ="mlp_down"):
    """Slot diagnostics of one layer type under SidecarCIM: S, saturation, slot/step ratio."""
    import qwen_eval as q
    model, wins, grp, Xc, Xe = setup(m)
    cfg = dict(SCHEMES)[REF]
    vmax = (1 << (cfg["vb"] - 1)) - 1
    rows = []
    for g in grp:
        if g[0] != typ:
            continue
        e, W, b = encode_group(m, model, g, Xc, cfg)
        X = Xe[g[2][0]]
        v = np.asarray(e["val"])
        S = np.asarray(e["S"])[0]
        Ws = W * e["s"][:, None]
        step = e["sw"][0]                                  # dense step per column
        ratio = np.abs(Ws).max(axis=0) / step              # largest |w| in dense steps
        rows.append({"layer": g[1], "alpha": e["alpha"],
                     "err": round(rel_l2(int_forward(e, X), X @ W + b), 5),
                     "S_hist": {int(a): int(c) for a, c in zip(*np.unique(S, return_counts=True))},
                     "sat_slots_pct": round(100.0 * float(((v >= vmax) | (v <= -vmax - 1)).mean()),
                                            4),
                     "cols_S0_pct": round(100.0 * float((S == 0).mean()), 3),
                     "max_w_over_step": round(float(ratio.max()), 1),
                     "cols_w_over_vmax_steps_pct": round(100.0 * float((ratio > vmax).mean()), 3),
                     "act_max_over_std": round(float(np.abs(Xc[g[2][0]]).max() /
                                                     Xc[g[2][0]].std()), 1)})
        print(rows[-1], flush=True)
        q.trim()
    res = load()
    res.setdefault("diag", {})[f"{m}|{typ}|{REF}"] = rows
    save(res)


def report():
    res = load()
    U = res["units"]
    FT = json.loads(FT_FILE.read_text())["units"]
    res["method"] = __doc__.strip()
    res["tables"] = {}
    for key in sorted({k.rsplit("|", 1)[0] for k in U}):
        m = key.split("|")[0]
        ref = U.get(f"{key}|{REF}")
        if not ref:
            continue
        n = len(ref["nll"])
        idx = ref["win_idx"]
        fpn = np.array(FT[f"{m}|FP32"]["nll"])[idx]
        rows = [{"scheme": "FP32", "ppl": round(ppl(fpn), 4)}]
        for name, _ in SCHEMES:
            u = U.get(f"{key}|{name}")
            if not u or len(u["nll"]) < n:
                continue
            a = np.array(u["nll"][:n])
            assert u["win_idx"][:n] == idx
            d, se = paired(a, fpn)
            row = {"scheme": name, "ppl": round(ppl(a), 4), "d_vs_fp32": d, "se_vs_fp32": se}
            if name != REF:
                row["vs_sidecar"] = compare(a, ref["nll"][:n])
            rows.append(row)
        res["tables"][key] = {"windows": n, "rows": rows}
        print(f"\n{key}: {n} windows; FP32 {ppl(fpn):.3f}")
        for r in rows:
            v = r.get("vs_sidecar")
            d = f"{r['d_vs_fp32']:+.3f}±{r['se_vs_fp32']:.3f}" if "d_vs_fp32" in r else ""
            s = (f"diff {v['dppl']:+.3f} [{v['ci90_dppl'][0]:+.3f},{v['ci90_dppl'][1]:+.3f}] "
                 f"p {v['p_two_sided']:.3g} TOST {v['tost_p']:.3g}" if v else "")
            print(f"  {r['scheme']:26s} {r['ppl']:10.3f} {d:16s} {s}")
    save(res)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "report":
        report()
    elif a[1] == "diag":
        diag(a[0], a[2] if len(a) > 2 else "mlp_down")
    elif a[1] == "allbut":
        stage(a[0], "allbut", a[2], int(a[3]) if len(a) > 3 else None)
    else:
        stage(a[0], a[1], None, int(a[2]) if len(a) > 2 else None)
