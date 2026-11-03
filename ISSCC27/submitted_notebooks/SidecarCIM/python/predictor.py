"""Study I: does migrated-weight kurtosis predict the sidecar gain over W6A4? More open models.

Usage: python predictor.py eval <key> [N]   FP32, W6A4, SidecarCIM k2 VB12, W8A4 (+mig+wclip)
       python predictor.py stats <key>      outlier statistics (tinylm.layer_stats, calib)
       python predictor.py fit              all models (this file + sizetrend.json trend)
Models (not gated): EleutherAI/pythia-160m / 410m / 1b (GPT-NeoX, mlp.dense_h_to_4h),
facebook/opt-125m / 350m (fc1). Protocol = the GPT-2 path of fulltest.py for a single MLP
input projection per layer (encode_pick2: migration + wclip, alpha picked on calib layer error
per layer; golden tile checks on 3 calib tokens per layer; the layer swapped for the integer
path with llm_layer.make_qfc), WikiText-2: calib = first 512 train tokens, eval = consecutive
1024-token windows of the test split (N evenly spaced if given; stated). Stats = fulltest.compare.
Sink check: windows whose NLL exceeds FP32 by > 2 nats are counted ("bad windows"); a bimodal
count would call for the sink rule used for SmolLM2-1.7B (not needed if 0).
gain = ppl(W6A4) - ppl(SidecarCIM), paired; positive = the sidecar is better.
fit: Spearman rank correlation of gain (absolute and relative to the SidecarCIM ppl) with each
statistic, the single threshold on each statistic that best separates gain > 0 from gain < 0
(midpoints between sorted values; ties broken by the lower threshold), its misclassified models,
and the leave-one-out accuracy of that threshold rule. Nothing is tuned beyond this.
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
from golden import SPEC  # noqa: E402
from llm_layer import CALIB_TOKENS, OUT, capture, golden_check, load_wikitext  # noqa: E402
from novelty_study import B, encode_pick2, paired, ppl, window_nll  # noqa: E402
from qwen_eval import slim, trim  # noqa: E402

FILE = OUT / "predictor.json"
K = SPEC["outlier"]["budget_per_output"]
WIN = 1024
MODELS = {"pythia-160m": ("EleutherAI/pythia-160m", "gpt_neox.layers.{}.mlp.dense_h_to_4h"),
          "pythia-410m": ("EleutherAI/pythia-410m", "gpt_neox.layers.{}.mlp.dense_h_to_4h"),
          "pythia-1b": ("EleutherAI/pythia-1b", "gpt_neox.layers.{}.mlp.dense_h_to_4h"),
          "opt-125m": ("facebook/opt-125m", "model.decoder.layers.{}.fc1"),
          "opt-350m": ("facebook/opt-350m", "model.decoder.layers.{}.fc1")}
# study J (prospective test): models the predictor has never seen. kind: "linear" (nn.Linear
# MLP input), "conv1d" (GPT-2 Conv1D, weight already (in, out)), "gateup" (Llama/Qwen: one
# [gate|up] matrix per layer, the fulltest.py Qwen path: alpha picked without clip)
NEW = {"gpt2-medium": ("gpt2-medium", "conv1d", "transformer.h.{}.mlp.c_fc"),
       "gpt2-large": ("gpt2-large", "conv1d", "transformer.h.{}.mlp.c_fc"),
       "opt-1.3b": ("facebook/opt-1.3b", "linear", "model.decoder.layers.{}.fc1"),
       "bloom-560m": ("bigscience/bloom-560m", "linear", "transformer.h.{}.mlp.dense_h_to_4h"),
       "bloom-1b1": ("bigscience/bloom-1b1", "linear", "transformer.h.{}.mlp.dense_h_to_4h"),
       "qwen2.5-1.5b": ("Qwen/Qwen2.5-1.5B", "gateup", "model.layers.{}.mlp.gate_proj"),
       "tinyllama-1.1b": ("TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T", "gateup",
                          "model.layers.{}.mlp.gate_proj"),
       "phi-1.5": ("microsoft/phi-1_5", "linear", "model.layers.{}.mlp.fc1")}


def spec(key):
    """(hf id, kind, module-name pattern) of a model."""
    if key in NEW:
        return NEW[key]
    return MODELS[key][0], "linear", MODELS[key][1]


REF = "SidecarCIM+wclip k2,VB12"
W6 = "W6A4+mig+wclip"
SCHEMES = [(REF, dict(B, k=K, wclip=True, vb=12)),
           (W6, dict(B, wbits=6, wclip=True)),
           ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True))]
SCHEMES_J = SCHEMES + [("W4A4+mig+wclip", dict(B, wclip=True))]   # study J adds W4A4
PROSPECTIVE = OUT / "predictor_prospective.json"
# gate|up models above 1B: free each layer's FP gate/up weights once it is encoded (the
# integer path replaces them), so one process evaluates one quantized scheme
LOWMEM = os.environ.get("PREDICTOR_LOWMEM") == "1"
# frozen before study J from the 14-model fit (predictor.json fit_14_models): split values
# and the uncertain band for activation max/std, all fixed before evaluation
KURT_SPLIT, ACT_SPLIT, ACT_BAND = 8.8792, 60.235, (58.0, 92.0)
# models to evaluate, chosen from the screening statistics only: the one predicted-positive
# model, the two uncertain models that best separate the two statistics (gpt2-medium: act in the
# band; bloom-1b1: kurtosis high, act low), and the clearest predicted-negative control
EVAL_PLAN = [("qwen2.5-1.5b", 96), ("gpt2-medium", None), ("bloom-1b1", 140), ("gpt2-large", 140)]


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


def setup(key, test=True):
    """Model, test windows, per-layer weight getter, calib inputs. Weights are built per layer on
    demand (float64), so big models do not hold all of them at once."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import qwen_eval as q
    torch.set_num_threads(6)
    hf, kind, pat = spec(key)
    tok = AutoTokenizer.from_pretrained(hf)
    model = AutoModelForCausalLM.from_pretrained(hf, dtype=torch.float32).eval()
    ids, wins = [], []
    if test:
        ids = tok(load_wikitext("test", 10 ** 9), add_special_tokens=False)["input_ids"]
        ev = torch.tensor(ids)
        wins = [ev[i * WIN:(i + 1) * WIN] for i in range(len(ids) // WIN)]
    ca = tok(load_wikitext("train", 20000), add_special_tokens=False)["input_ids"][:CALIB_TOKENS]
    L = model.config.num_hidden_layers
    names = [pat.format(i) for i in range(L)]
    X = capture(model, names, [torch.tensor(ca)])
    Xc = {n: X[n] for n in names}

    def get(n):
        """(W (in, out), b) float64 of layer n."""
        if kind == "gateup":
            return q.layer_weights(model, names.index(n))
        mod = model.get_submodule(n)
        w = mod.weight.detach().double().numpy()
        w = w.copy() if kind == "conv1d" else w.T.copy()
        b = (mod.bias.detach().double().numpy() if mod.bias is not None
             else np.zeros(w.shape[1]))
        return w, b
    W0, _ = get(names[0])
    meta = {"hf_id": hf, "kind": kind, "params": sum(p.numel() for p in model.parameters()),
            "layers": L, "fc_shape": list(W0.shape), "test_tokens": len(ids),
            "windows_total": len(wins), "ctx": WIN}
    return model, wins, names, get, kind, Xc, meta


def stage_eval(key, n_win=None, schemes=None):
    import qwen_eval as q
    t0 = time.time()
    model, wins, names, get, kind, Xc, meta = setup(key)
    nw = len(wins)
    n_win = nw if n_win is None else min(n_win, nw)
    idx = sorted({int(round(v)) for v in np.linspace(0, nw - 1, n_win)})
    res = load()
    res.setdefault("meta", {})[key] = dict(meta, windows_used=len(idx),
                                           selection="all" if len(idx) == nw else
                                           "evenly spaced (np.linspace)")
    U = res["units"]
    if kind == "gateup":
        nll = lambda w, encs=None: q.window_nll(model, w, encs)    # noqa: E731
    else:
        nll = lambda w, encs=None: window_nll(model, w, encs)      # noqa: E731

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

    run(f"{key}|FP32", lambda w: nll(w))
    for name, cfg in (schemes or SCHEMES):
        k = f"{key}|{name}"
        if k in U and len(U[k]["nll"]) == len(idx):
            continue
        wait_no_docker()
        t1 = time.time()
        encs, alphas = {}, []
        for i, n in enumerate(names):
            W, b = get(n)
            e = (q.pick_encode(W, b, Xc[n], cfg) if kind == "gateup"
                 else encode_pick2(W, b, Xc[n], cfg))
            golden_check(e, Xc[n], [0, 255, CALIB_TOKENS - 1])
            alphas.append(e["alpha"])
            encs[i if kind == "gateup" else n] = slim(e)   # int16 codes, no golden-only arrays
            del W, e
            if LOWMEM and kind == "gateup":
                import torch
                mlp = model.model.layers[i].mlp
                for lin in (mlp.gate_proj, mlp.up_proj):
                    lin.weight = torch.nn.Parameter(torch.empty(0), requires_grad=False)
            trim()
        print(f"  {k}: encoded in {time.time() - t1:.0f} s", flush=True)
        u = run(k, lambda w, e=encs: nll(w, e))
        u.update(alphas=alphas, sec=round(time.time() - t1, 1))
        save(res)
        del encs
        trim()
        if LOWMEM and kind == "gateup":         # FP weights are gone: next scheme, new process
            return
    if key not in res.get("outlier_stats", {}):
        stage_stats(key, (model, wins, names, get, kind, Xc, meta))
    fit()


def stage_stats(key, ctx=None):
    from tinylm import layer_stats, summarize
    model, wins, names, get, kind, Xc, meta = ctx or setup(key, test=False)
    per = []
    for n in names:
        W, _ = get(n)
        per.append(layer_stats(W, Xc[n]))
        del W
    res = load()
    res.setdefault("outlier_stats", {})[key] = {
        "summary": summarize(per), "per_layer": per, "params": meta["params"],
        "kind": kind, "hf_id": meta["hf_id"]}
    save(res)
    print(key, json.dumps(summarize(per)), flush=True)
    return summarize(per), meta


def points():
    """One row per model: gain over W6A4 and outlier stats (this file + sizetrend trend)."""
    res = load()
    U = res["units"]
    rows = []
    for key in list(MODELS) + list(NEW):
        fp, ref, w6 = (U.get(f"{key}|{n}") for n in ("FP32", REF, W6))
        st = res.get("outlier_stats", {}).get(key)
        if not (fp and ref and w6 and st) or len(w6["nll"]) < len(ref["nll"]) or \
                len(ref["nll"]) < len(fp["nll"]):
            continue
        n = len(fp["nll"])
        f, r, w = (np.array(u["nll"][:n]) for u in (fp, ref, w6))
        c = compare(w, r)
        row = {"model": key, "params": st["params"], "source": "predictor.json",
               "prospective": key in NEW,
               "dataset": "WikiText-2 test", "windows": n, "fp32_ppl": round(ppl(f), 4),
               "sidecar_d_vs_fp32": paired(r, f)[0], "w6a4_d_vs_fp32": paired(w, f)[0],
               "gain_over_W6A4_ppl": c["dppl"], "gain_ci90": c["ci90_dppl"],
               "p": c["p_two_sided"],
               "gain_over_W6A4_rel_pct": round(100.0 * c["dppl"] / ppl(r), 3),
               "bad_windows": {nm: int((np.array(U[f"{key}|{nm}"]["nll"][:n]) - f > 2).sum())
                               for nm, _ in SCHEMES if f"{key}|{nm}" in U}}
        w8 = U.get(f"{key}|W8A4+mig+wclip")
        if w8 and len(w8["nll"]) >= n:
            row["w8a4_d_vs_fp32"] = paired(np.array(w8["nll"][:n]), f)[0]
        s = st["summary"]
        row.update(act_max_over_std_max=s["act_max_over_std_max"],
                   w_kurtosis_mig=s["weights_mig_a1"]["excess_kurtosis_mean"],
                   w_kurtosis_raw=s["weights_raw"]["excess_kurtosis_mean"],
                   pct_tilecols_over_k2_mig=s["weights_mig_a1"]["pct_tilecols_over_k2"])
        rows.append(row)
    st = OUT / "sizetrend.json"
    if st.exists():
        for t in json.loads(st.read_text()).get("trend", []):
            if t["model"] == "smollm2-1.7b" and not t.get("sink_rule"):
                continue                          # invalid without the sink rule (study H)
            rows.append(dict(t, source="sizetrend.json"))
    return rows


def spearman(x, y):
    def rank(a):
        a = np.asarray(a, float)
        o = np.argsort(a, kind="stable")
        r = np.empty(len(a))
        r[o] = np.arange(len(a))
        for v in np.unique(a):                    # average ties
            m = a == v
            r[m] = r[m].mean()
        return r
    rx, ry = rank(x), rank(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def best_threshold(x, pos):
    """Threshold t (rule: x > t -> gain > 0) with the fewest errors; also the reverse rule."""
    xs = np.sort(np.unique(x))
    cands = [xs[0] - 1.0] + [(a + b) / 2 for a, b in zip(xs[:-1], xs[1:])] + [xs[-1] + 1.0]
    best = None
    for t in cands:
        for sign in (1, -1):
            pred = (x > t) if sign == 1 else (x <= t)
            err = int((pred != pos).sum())
            if best is None or err < best[0]:
                best = (err, float(t), sign)
    return best


def fit():
    rows = points()
    out = {"points": rows, "stats": {}}
    if len(rows) < 3:
        save(dict(load(), fit=out))
        return
    pos = np.array([r["gain_over_W6A4_ppl"] > 0 for r in rows])
    for stat in ("w_kurtosis_mig", "w_kurtosis_raw", "act_max_over_std_max",
                 "pct_tilecols_over_k2_mig", "params"):
        have = [r for r in rows if r.get(stat) is not None]
        x = np.array([float(r[stat]) for r in have])
        p = np.array([r["gain_over_W6A4_ppl"] > 0 for r in have])
        g = np.array([r["gain_over_W6A4_ppl"] for r in have])
        gr = np.array([r["gain_over_W6A4_rel_pct"] for r in have])
        err, t, sign = best_threshold(x, p)
        pred = (x > t) if sign == 1 else (x <= t)
        loo = 0
        for i in range(len(x)):                    # leave-one-out accuracy of the threshold rule
            m = np.arange(len(x)) != i
            _, ti, si = best_threshold(x[m], p[m])
            loo += int(((x[i] > ti) if si == 1 else (x[i] <= ti)) == p[i])
        out["stats"][stat] = {
            "n": len(x), "spearman_gain": round(spearman(x, g), 3),
            "spearman_gain_rel": round(spearman(x, gr), 3),
            "threshold": round(t, 4), "rule": f"gain > 0 if {stat} {'>' if sign == 1 else '<='} "
                                              f"{round(t, 4)}",
            "errors": err, "misclassified": [have[i]["model"] for i in np.flatnonzero(pred != p)],
            "loo_accuracy": f"{loo}/{len(x)}"}
    out["n_models"] = len(rows)
    out["n_gain_positive"] = int(pos.sum())
    res = load()
    if "fit" in res and "fit_14_models" not in res:
        res["fit_14_models"] = res["fit"]          # keep the fit made before study J
    res["fit"] = out
    res["method"] = __doc__.strip()
    save(res)
    print(f"{'model':16s} {'params':>13s} {'gain/W6':>9s} {'p':>8s} {'kurt mig':>8s} "
          f"{'act max/std':>11s} {'%tc>2':>7s}  source")
    for r in sorted(rows, key=lambda r: r["params"]):
        print(f"{r['model']:16s} {r['params']:13,d} {r['gain_over_W6A4_ppl']:+9.3f} "
              f"{r['p']:8.2g} {r.get('w_kurtosis_mig')!s:>8s} "
              f"{r.get('act_max_over_std_max')!s:>11s}"
              f" {r.get('pct_tilecols_over_k2_mig')!s:>7s}  {r['source']}")
    for k, v in out["stats"].items():
        print(k, json.dumps(v))


def predict_sign(kurt, act):
    """Frozen rule (written before any study-J evaluation)."""
    if ACT_BAND[0] <= act <= ACT_BAND[1]:
        return "uncertain"
    up_k, up_a = kurt > KURT_SPLIT, act > ACT_SPLIT
    if up_k and up_a:
        return "gain > 0"
    if not up_k and not up_a:
        return "gain < 0"
    return "uncertain"


def stage_score():
    """Frozen predictions (predictor_prospective.json) against the measured gains."""
    pro = json.loads(PROSPECTIVE.read_text())
    rows = {r["model"]: r for r in points() if r.get("prospective")}
    rules = ("prediction", "prediction_act_split_71_92", "prediction_kurtosis_only")
    out = {"predictions_written": pro["written"], "alpha": 0.05,
           "outcome_rule": "gain > 0 or gain < 0 if the paired two-sided p < 0.05, else "
                           "no significant difference", "models": [], "tally": {}}
    for m in pro["models"]:
        r = rows.get(m["model"])
        if not r:
            continue
        g, pv = r["gain_over_W6A4_ppl"], r["p"]
        outcome = ("no significant difference" if pv >= 0.05 else
                   "gain > 0" if g > 0 else "gain < 0")
        e = {"model": m["model"], "gain_over_W6A4_ppl": g, "gain_ci90": r["gain_ci90"],
             "p": pv, "windows": r["windows"], "outcome": outcome,
             "outcome_sign": "gain > 0" if g > 0 else "gain < 0"}
        for rule in rules:
            pred = m[rule]
            e[rule] = pred
            if pred == "uncertain":
                verdict = "no call"
            elif outcome == "no significant difference":
                verdict = "sign " + ("agrees" if pred == e["outcome_sign"] else "disagrees") + \
                    ", not significant"
            else:
                verdict = "hit" if pred == outcome else "miss"
            e[rule + "_verdict"] = verdict
            t = out["tally"].setdefault(rule, {})
            t[verdict] = t.get(verdict, 0) + 1
        out["models"].append(e)
    res = load()
    res["prospective_score"] = out
    save(res)
    print(json.dumps(out, indent=1))


def stage_predict():
    """Write predictor_prospective.json from the screening statistics only (no test data)."""
    res = load()
    st = res.get("outlier_stats", {})
    rows = []
    for key in NEW:
        if key not in st:
            continue
        sm = st[key]["summary"]
        kurt = sm["weights_mig_a1"]["excess_kurtosis_mean"]
        act = sm["act_max_over_std_max"]
        rows.append({"model": key, "hf_id": NEW[key][0], "params": st[key]["params"],
                     "w_kurtosis_mig": kurt, "act_max_over_std_max": act,
                     "w_kurtosis_raw": sm["weights_raw"]["excess_kurtosis_mean"],
                     "pct_tilecols_over_k2_mig": sm["weights_mig_a1"]["pct_tilecols_over_k2"],
                     "prediction": predict_sign(kurt, act),
                     "prediction_act_split_71_92": ("gain > 0" if act > 92.0 else
                                                    "gain < 0" if act < 71.0 else "uncertain"),
                     "prediction_kurtosis_only": "gain > 0" if kurt > KURT_SPLIT else "gain < 0",
                     "margin": round(min(kurt / KURT_SPLIT, act / ACT_BAND[1]), 3)})
    out = {"written": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "rule": (f"gain = ppl(W6A4) - ppl(SidecarCIM). Predict gain > 0 if migrated-weight "
                    f"kurtosis > {KURT_SPLIT} and act max/std > {ACT_SPLIT}; gain < 0 if both are "
                    f"below; uncertain if they disagree or act max/std is within "
                    f"{ACT_BAND[0]}..{ACT_BAND[1]}. Splits frozen from the 14-model fit."),
           "statistics": "tinylm.layer_stats on the MLP-input layers, first 512 WikiText-2 train "
                         "tokens (calibration only; no test data used)",
           "margin": "min(kurtosis / kurtosis split, act max/std / upper band edge); > 1 = "
                     "clearly above the split",
           "other_rules": {
               "prediction_act_split_71_92": "act max/std alone: gain > 0 above 92, gain < 0 "
                                             "below 71, uncertain in between (the split used in "
                                             "the paper: largest ratio of a model that does not "
                                             "gain, smallest of one that does)",
               "prediction_kurtosis_only": f"kurtosis alone: gain > 0 above {KURT_SPLIT}"},
           "evaluation_plan": EVAL_PLAN,
           "models": sorted(rows, key=lambda r: -r["margin"])}
    PROSPECTIVE.write_text(json.dumps(out, indent=1))
    for r in out["models"]:
        print(f"{r['model']:16s} kurt {r['w_kurtosis_mig']:8.3f} "
              f"act {r['act_max_over_std_max']:8.2f} margin {r['margin']:6.3f} -> "
              f"{r['prediction']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "eval":
        stage_eval(a[1], int(a[2]) if len(a) > 2 else None)
    elif a[0] == "stats":
        stage_stats(a[1])
    elif a[0] == "screen":                         # statistics only, calibration data only
        for key in a[1:]:
            stage_stats(key)
            trim()
    elif a[0] == "predict":
        stage_predict()
    elif a[0] == "score":
        stage_score()
    elif a[0] == "evalj":                          # study J: + W4A4
        stage_eval(a[1], int(a[2]) if len(a) > 2 else None, SCHEMES_J)
    else:
        fit()
