"""Review Oct 15: extra dense points and calibration-slice spread on the full test set.

Usage: python fulltest_extra.py gpt2 dense | qwen dense     W7A4+mig+wclip, W4A8+mig+wclip
       python fulltest_extra.py gpt2 calib | qwen calib     REF, W6A4, W8A4 on 2 more calib slices
       python fulltest_extra.py report
Writes out/fulltest_extra.json in the fulltest.json schema (units -> per-window NLL; tables[m].rows
with scheme, ppl, d_vs_fp32, se_vs_fp32, vs_sidecar{dppl, ci90_dppl, p_two_sided, tost_p, ...}).
Protocol = fulltest.py exactly (same windows, encoders, golden checks, stats; FP32 and the
reference NLL for calib slice 0 are read from out/fulltest.json, which is not modified).
dense: W7A4 (the iso-accuracy dense point between W6A4 and W8A4) and W4A8 (4-bit weights,
  8-bit inputs: dcim_core WBITS=4, ABITS=8), both + migration + weight clip, alpha picked as
  in fulltest.py, compared with SidecarCIM+wclip k2,VB12 (slice 0).
calib: slice 0 = first 512 WikiText-2 train tokens (fulltest.json); slices 1, 2 = train tokens
  1024:1536 and 2048:2560 (the extras.py SLICES). For each slice the reference and W6A4 / W8A4
  are re-encoded on that slice (alpha re-picked) and compared paired within the slice.
  Spread = the per-slice differences, their mean and range.
"""
import json
import os
import sys
import time

import numpy as np

from fulltest import CHUNK, MARGIN, REF, compare, model_table
from fulltest import FILE as FT_FILE
from golden import SPEC
from llm_layer import CALIB_TOKENS, OUT, capture, fc_names, golden_check, load_wikitext
from novelty_study import B, encode_pick2, paired, ppl

FILE = OUT / "fulltest_extra.json"
K = SPEC["outlier"]["budget_per_output"]
REF_CFG = dict(B, k=K, wclip=True, vb=12)
DENSE = [("W7A4+mig+wclip", dict(B, wbits=7, wclip=True)),
         ("W4A8+mig+wclip", dict(B, abits=8, wclip=True))]
CALIB_RIVALS = [(REF, REF_CFG),
                ("W6A4+mig+wclip", dict(B, wbits=6, wclip=True)),
                ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True))]
SLICES = (1024, 2048)                     # train token offsets of calib slices 1, 2


EXIT_BUSY = 75                            # exit code: a container started, rerun later


def wait_no_docker():
    """With EDGE_NODOCKER=1 (big models): if any container (LibreLane job) runs, exit with
    EXIT_BUSY so the model's memory is freed; the queue reruns the stage later and it resumes
    from the saved checkpoint."""
    import subprocess
    if os.environ.get("EDGE_NODOCKER") != "1":
        return
    try:
        r = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60)
        busy = bool(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        busy = False                           # no docker CLI: nothing to wait for
    if busy:
        print(f"  a docker container is running: exit {EXIT_BUSY} to free memory "
              f"({time.strftime('%H:%M:%S')})", flush=True)
        sys.exit(EXIT_BUSY)


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


def ft_units():
    return json.loads(FT_FILE.read_text())["units"]


def run_unit(res, key, wins, idx, nll_fn, t0):
    u = res["units"].setdefault(key, {"nll": [], "win_idx": []})
    done = len(u["nll"])
    assert u["win_idx"] == list(idx[:done])
    for s in range(done, len(idx), CHUNK):
        wait_no_docker()
        part = list(idx[s:s + CHUNK])
        u["nll"] += nll_fn([wins[i] for i in part]).tolist()
        u["win_idx"] += [int(i) for i in part]
        save(res)
        print(f"    {key}: {len(u['nll'])}/{len(idx)} ({time.time() - t0:.0f} s)", flush=True)
    return u


# ---------------- model setups (calib slice by offset) ----------------

def gpt2_setup(offsets):
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    torch.set_num_threads(6)
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    ev = torch.tensor(ids)
    wins = [ev[i * 1024:(i + 1) * 1024] for i in range(len(ids) // 1024)]
    tr = tok(load_wikitext("train", 20000))["input_ids"]
    names = fc_names(model)
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    Xc = {}
    for off in offsets:
        assert len(tr) >= off + CALIB_TOKENS
        Xc[off] = capture(model, names, [torch.tensor(tr[off:off + CALIB_TOKENS])])
    h0 = SPEC["workload"]["layer"]
    Xe0 = capture(model, [h0], wins[:1])[h0]

    def encode(cfg, off):
        encs, alphas = {}, []
        for n in names:
            e = encode_pick2(Ws[n], bs[n], Xc[off][n], cfg)
            golden_check(e, Xc[off][n], [0, 255, CALIB_TOKENS - 1])
            if n == h0:
                golden_check(e, Xe0, [0, 511, 1023])
            encs[n] = e
            alphas.append(e["alpha"])
        return encs, alphas
    from novelty_study import window_nll
    return wins, encode, (lambda w, encs: window_nll(model, w, encs)), (lambda: None)


def qwen_setup(offsets):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import qwen_eval as q
    torch.set_num_threads(q.THREADS)
    tok = AutoTokenizer.from_pretrained(q.MODEL)
    model = AutoModelForCausalLM.from_pretrained(q.MODEL, dtype=torch.float32).eval()
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    ev = torch.tensor(ids)
    wins = [ev[i * q.WIN:(i + 1) * q.WIN] for i in range(len(ids) // q.WIN)]
    tr = tok(load_wikitext("train", 20000))["input_ids"]
    L = model.config.num_hidden_layers
    names = [f"model.layers.{i}.mlp.gate_proj" for i in range(L)]
    Xc = {}
    for off in offsets:
        assert len(tr) >= off + CALIB_TOKENS
        X = capture(model, names, [torch.tensor(tr[off:off + CALIB_TOKENS])])
        Xc[off] = [X[n] for n in names]

    def encode(cfg, off):
        encs, alphas = {}, []
        for i in range(L):
            W, b = q.layer_weights(model, i)
            e = q.pick_encode(W, b, Xc[off][i], cfg)
            golden_check(e, Xc[off][i], [0, 100, CALIB_TOKENS - 1])
            alphas.append(e["alpha"])
            encs[i] = q.slim(e)
            q.trim()
        return encs, alphas
    return wins, encode, (lambda w, encs: q.window_nll(model, w, encs)), q.trim


# ---------------- stages ----------------

def stage(m, what):
    t0 = time.time()
    FT = ft_units()
    offsets = [0] if what == "dense" else list(SLICES)
    wins, encode, nll, trim = (gpt2_setup if m == "gpt2" else qwen_setup)(offsets)
    idx = list(range(len(wins)))
    assert FT[f"{m}|FP32"]["win_idx"] == idx
    res = load()
    jobs = ([(f"{m}|{n}", c, 0) for n, c in DENSE] if what == "dense" else
            [(f"{m}|calib{off}|{n}", c, off) for off in SLICES for n, c in CALIB_RIVALS])
    for key, cfg, off in jobs:
        u = res["units"].get(key)
        if u and len(u["nll"]) == len(idx):
            continue
        t1 = time.time()
        wait_no_docker()
        encs, alphas = encode(cfg, off)
        te = time.time() - t1
        print(f"  {key}: encoded in {te:.0f} s, alphas {alphas[:4]}...", flush=True)
        u = run_unit(res, key, wins, idx, lambda w, e=encs: nll(w, e), t0)
        u.update(alphas=alphas, encode_sec=round(te, 1), sec=round(time.time() - t1, 1),
                 calib_train_offset=off)
        save(res)
        del encs
        trim()
    report()


def report():
    res = load()
    FT = ft_units()
    U = res["units"]
    res["method"] = __doc__.strip()
    res["reference"] = REF
    res["tables"] = {}
    res["calib_spread"] = {}
    for m in ("gpt2", "qwen"):
        # dense table in fulltest.json schema: FP32 + REF from fulltest.json, new rows here
        merged = {f"{m}|FP32": FT[f"{m}|FP32"], f"{m}|{REF}": FT[f"{m}|{REF}"]}
        merged.update({k: v for k, v in U.items() if k.startswith(m + "|") and "|calib" not in k})
        import fulltest
        old = fulltest.SCHEMES
        fulltest.SCHEMES = [(REF, REF_CFG)] + DENSE
        try:
            tab = model_table(merged, m)
        finally:
            fulltest.SCHEMES = old
        if tab and len(tab["rows"]) > 2:
            res["tables"][m] = tab
            print(f"\n{m} dense extra ({tab['windows']} windows):")
            for r in tab["rows"]:
                v = r.get("vs_sidecar", {})
                print(f"  {r['scheme']:26s} {r['ppl']:8.3f} d {r.get('d_vs_fp32', 0):+.3f} "
                      f"diff {v.get('dppl', 0):+.3f} CI {v.get('ci90_dppl')} p "
                      f"{v.get('p_two_sided')} TOST {v.get('tost_p')} {v.get('verdict', '')}")
        # calibration spread: per slice, rival vs REF of the same slice
        fp = np.array(FT[f"{m}|FP32"]["nll"])
        sl = {0: {n: FT.get(f"{m}|{n}") for n, _ in CALIB_RIVALS}}
        for off in SLICES:
            sl[off] = {n: U.get(f"{m}|calib{off}|{n}") for n, _ in CALIB_RIVALS}
        out = {"slices": {}, "margin_ppl": MARGIN}
        for off, d in sl.items():
            if not all(d[n] and len(d[n]["nll"]) == len(fp) for n, _ in CALIB_RIVALS):
                continue
            ref = np.array(d[REF]["nll"])
            row = {"calib_train_tokens": [off, off + CALIB_TOKENS],
                   "ref_ppl": round(ppl(ref), 4), "ref_d_vs_fp32": paired(ref, fp)[0]}
            for n, _ in CALIB_RIVALS[1:]:
                c = compare(d[n]["nll"], ref)
                row[n] = {"ppl": round(ppl(np.array(d[n]["nll"])), 4), "dppl": c["dppl"],
                          "ci90_dppl": c["ci90_dppl"], "p_two_sided": c["p_two_sided"],
                          "tost_p": c["tost_p"], "verdict": c["verdict"]}
            out["slices"][str(off)] = row
        if len(out["slices"]) > 1:
            for n, _ in CALIB_RIVALS[1:]:
                v = [s[n]["dppl"] for s in out["slices"].values()]
                out[n + " spread"] = {"dppl_per_slice": v, "mean": round(float(np.mean(v)), 4),
                                      "min": min(v), "max": max(v),
                                      "sd": round(float(np.std(v, ddof=1)), 4),
                                      "max_p": max(s[n]["p_two_sided"]
                                                   for s in out["slices"].values())}
            r = [s["ref_d_vs_fp32"] for s in out["slices"].values()]
            out["ref_d_vs_fp32_per_slice"] = r
            res["calib_spread"][m] = out
            print(f"\n{m} calibration spread ({len(out['slices'])} slices):")
            for off, s in out["slices"].items():
                print(f"  slice {off}: ref ppl {s['ref_ppl']} (d {s['ref_d_vs_fp32']:+.3f}); " +
                      "; ".join(f"{n} {s[n]['dppl']:+.3f} {s[n]['ci90_dppl']} p "
                                f"{s[n]['p_two_sided']:.3g} TOST {s[n]['tost_p']:.3g}"
                                for n, _ in CALIB_RIVALS[1:]))
    save(res)


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report()
    else:
        stage(sys.argv[1], sys.argv[2])
