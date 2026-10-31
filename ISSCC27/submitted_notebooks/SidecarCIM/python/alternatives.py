"""Dense wider-weight alternatives and the sidecar slot-width sweep.

Usage: python alternatives.py gpt2 | qwen | report   (each stage resumes from out/alternatives.json)
       python alternatives.py headline   (out/headline_vb<spec VB>.json from saved results only)
Protocol = extras.py: GPT-2 all 12 c_fc; Qwen2.5-0.5B all 24 gate+up; calib = first 512 train
tokens; eval = first 8192 test tokens (8 windows of 1024); per-window NLL stored; paired SE vs
FP32 (novelty_study.paired) and paired difference vs the reference (extras.diff_stats).
Schemes (all with weight clip search; per-output-channel weight scale, per-tensor act scale):
  ref   SidecarCIM+wclip   W4A4 + migration + k=2 magnitude slots, VB=16 (design before the
        Oct 11 spec change 16 -> 12; pinned to 16 so it still matches extras.json)
  A     dense W5A4 / W6A4 (+W4A4 / W8A4 reference) with migration, no sidecar; W5A4 / W6A4
        without migration (GPT-2 only)
  B     SidecarCIM+wclip with slot value bits VB in {12, 10, 8} (shift S so the largest slot
        fills VB bits; cfg["vb"], default = spec outlier.weight_bits, now 12)
  C     k=1, VB=16 (pinned)
Alpha is picked on calib layer error per scheme (as in extras). Integer path is golden-checked
tile by tile (golden.dcim_dot / golden.sidecar_dot with the scheme's own slot width).
"""
import json
import sys
import time

import numpy as np

from extras import diff_stats
from golden import SPEC
from llm_layer import CALIB_TOKENS, OUT, capture, fc_names, golden_check, load_wikitext
from novelty_study import B, encode_pick2, paired, ppl, window_nll

FILE = OUT / "alternatives.json"
K = SPEC["outlier"]["budget_per_output"]
VB0 = SPEC["outlier"]["weight_bits"]
LONG = 8192
REF = "SidecarCIM+wclip (k2,VB16)"
VB_REF = 16                                     # width of the extras.json runs
# (name, cfg, gpt2_only); order = priority
SCHEMES = [
    (REF, dict(B, k=K, wclip=True, vb=VB_REF), False),
    ("W5A4+mig+wclip", dict(B, wbits=5, wclip=True), False),
    ("W6A4+mig+wclip", dict(B, wbits=6, wclip=True), False),
    ("SidecarCIM+wclip k2,VB12", dict(B, k=K, wclip=True, vb=12), False),
    ("SidecarCIM+wclip k2,VB10", dict(B, k=K, wclip=True, vb=10), False),
    ("SidecarCIM+wclip k2,VB8", dict(B, k=K, wclip=True, vb=8), False),
    ("SidecarCIM+wclip k1,VB16", dict(B, k=1, wclip=True, vb=VB_REF), False),
    ("W4A4+mig+wclip", dict(B, wclip=True), False),
    ("W8A4+mig+wclip", dict(B, wbits=8, wclip=True), False),
    ("W5A4+wclip (no mig)", dict(B, wbits=5, alpha=None, wclip=True), True),
    ("W6A4+wclip (no mig)", dict(B, wbits=6, alpha=None, wclip=True), True),
]


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(res, indent=1))


def slot_stats(encs):
    """Slot saturation % (value at the VB-bit limit) and mean shift S over layers."""
    sat, n, s = 0, 0, []
    for e in encs:
        if not e["cfg"]["k"]:
            continue
        vb = e["cfg"].get("vb", VB0)
        v = np.asarray(e["val"])
        sat += int(((v >= (1 << (vb - 1)) - 1) | (v <= -(1 << (vb - 1)))).sum())
        n += v.size
        s.append(float(np.mean(e["S"])))
    return {"sat_slots_pct": round(100.0 * sat / n, 4) if n else None,
            "mean_S": round(float(np.mean(s)), 3) if s else None}


def _selftest():
    rng = np.random.default_rng(5)
    d_in, d_out = 64, 12
    W = rng.normal(0, 0.1, (d_in, d_out))
    W[5, 2], W[40, 7] = 2.0, -1.5
    b = rng.normal(0, 0.1, d_out)
    X = rng.normal(0, 1, (40, d_in))
    X[:, 3] *= 20
    encs = {}
    for name, cfg, _ in SCHEMES:
        e = encode_pick2(W, b, X, cfg)
        assert golden_check(e, X, [0, 1])
        if cfg["k"]:
            vb = cfg["vb"]
            assert e["val"].min() >= -(1 << (vb - 1)) and e["val"].max() < (1 << (vb - 1))
            assert e["S"].max() <= vb - 1
        assert e["Wq"].max() <= (1 << cfg["wbits"]) - 1
        encs[name] = e
    # default vb (spec width) == the k2 scheme of that width; labels match their widths
    e0 = encode_pick2(W, b, X, dict(B, k=K, wclip=True))
    same = [n for n, c, _ in SCHEMES if c["k"] == K and c.get("vb") == VB0]
    assert len(same) == 1
    assert np.array_equal(e0["val"], encs[same[0]]["val"]) and \
        np.array_equal(e0["S"], encs[same[0]]["S"])
    for name, cfg, _ in SCHEMES:
        if cfg["k"]:
            assert f"VB{cfg['vb']}" in name
    assert slot_stats([encs[REF]])["sat_slots_pct"] is not None
    print(f"alternatives self-test passed ({len(SCHEMES)} schemes)")


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
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    names = fc_names(model)
    h0 = SPEC["workload"]["layer"]
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    Xc = capture(model, names, [torch.tensor(ca)])
    Xe0 = capture(model, [h0], wins[:1])[h0]
    res = load()
    U = res["units"]
    if "gpt2_fp32" not in U:
        U["gpt2_fp32"] = {"nll": window_nll(model, wins).tolist()}
        save(res)
    for name, cfg, _ in SCHEMES:
        key = "gpt2|" + name
        if key in U:
            continue
        encs, alphas = {}, []
        for n in names:
            e = encode_pick2(Ws[n], bs[n], Xc[n], cfg)
            golden_check(e, Xc[n], [0, 255, CALIB_TOKENS - 1])
            if n == h0:
                golden_check(e, Xe0, [0, 511, 1023])
            encs[n] = e
            alphas.append(e["alpha"])
        U[key] = {"nll": window_nll(model, wins, encs).tolist(), "alphas": alphas,
                  **slot_stats(list(encs.values()))}
        save(res)
        print(f"  {key} ({time.time() - t0:.0f} s)", flush=True)
        del encs
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
    for name, cfg, gpt2_only in SCHEMES:
        key = "qwen|" + name
        if gpt2_only or key in U:
            continue
        encs, alphas, sl = {}, [], []
        for i in range(L):
            W, b = q.layer_weights(model, i)
            e = q.pick_encode(W, b, Xc[i], cfg)
            golden_check(e, Xc[i], [0, 100, CALIB_TOKENS - 1])
            alphas.append(e["alpha"])
            sl.append({"cfg": e["cfg"], "val": e["val"], "S": e["S"]})
            encs[i] = q.slim(e)
            q.trim()
        U[key] = {"nll": q.window_nll(model, wins, encs).tolist(), "alphas": alphas,
                  **slot_stats(sl)}
        save(res)
        print(f"  {key} ({time.time() - t0:.0f} s, peak RSS {q.peak_gb():.2f} GB)", flush=True)
        del encs, sl
        q.trim()
    report()


# ---------------- report ----------------

def table(U, prefix, fp_key, schemes):
    """Rows per scheme: ppl, d +- paired SE vs FP32, difference vs REF +- SE, t."""
    fp = np.array(U[fp_key]["nll"])
    ref = U.get(prefix + REF)
    rows = []
    for name in schemes:
        u = U.get(prefix + name)
        if not u:
            continue
        a = np.array(u["nll"])
        d, se = paired(a, fp)
        row = {"scheme": name, "ppl": round(ppl(a), 4), "d": d, "se": se,
               "alpha_h0": u["alphas"][0], "sat_slots_pct": u.get("sat_slots_pct"),
               "mean_S": u.get("mean_S")}
        if ref:
            row["vs_ref"] = diff_stats(a, ref["nll"]) if name != REF else None
        rows.append(row)
    return round(ppl(fp), 4), rows


def fmt(fp_ppl, rows, title):
    out = [f"\n{title}; FP32 ppl {fp_ppl:.4f}; ref = {REF}",
           f"{'scheme':28s} {'ppl':>9s} {'d vs FP32 (±paired SE)':>24s} "
           f"{'diff vs ref (±SE)':>21s} {'t':>6s} {'sat%':>6s}"]
    for r in rows:
        v = r.get("vs_ref")
        dv = f"{v['dppl']:+9.4f} ± {v['se_jackknife']:.4f}" if v else "(reference)"
        t = f"{v['t']:+6.2f}" if v and v["t"] is not None else ""
        sat = "" if r["sat_slots_pct"] is None else f"{r['sat_slots_pct']:6.3f}"
        out.append(f"{r['scheme']:28s} {r['ppl']:9.4f} {r['d']:+12.4f} ± {r['se']:.4f} "
                   f"{dv:>21s} {t:>6s} {sat:>6s}")
    return "\n".join(out)


def report():
    res = load()
    U = res["units"]
    res["tables"] = {}
    text = []
    for prefix, fp_key, title, g2 in (
            ("gpt2|", "gpt2_fp32", "GPT-2 8192 tok (8 windows), all 12 c_fc", True),
            ("qwen|", "qwen_fp32", "Qwen2.5-0.5B 8192 tok (8 windows), all 24 gate+up", False)):
        if fp_key not in U:
            continue
        names = [n for n, _, only in SCHEMES if g2 or not only]
        fp_ppl, rows = table(U, prefix, fp_key, names)
        res["tables"][prefix.rstrip("|")] = {"fp32_ppl": fp_ppl, "rows": rows}
        text.append(fmt(fp_ppl, rows, title))
    print("\n".join(text))
    save(res)
    # same-width k2 scheme must match the extras run (extras_vb16.json = VB16, extras.json = spec)
    for fname, vb in (("extras_vb16.json", VB_REF), ("extras.json", VB0)):
        ex = OUT / fname
        if not ex.exists():
            continue
        eu = json.loads(ex.read_text())["units"]
        name = REF if vb == VB_REF else f"SidecarCIM+wclip k2,VB{vb}"
        for k_new, k_old in (("gpt2|" + name, "side_mag_k2_wclip@8192"),
                             ("qwen|" + name, "qwen_side_mag_k2_wclip@8192")):
            if k_new in U and k_old in eu:
                dmax = np.abs(np.array(U[k_new]["nll"]) - np.array(eu[k_old]["nll"])).max()
                print(f"check {k_new} vs {fname} {k_old}: max |dNLL| = {dmax:.2e}")


# ---------------- headline (spec width) ----------------

def gap_pct(base, side, top):
    """% of the base -> top d-gap closed by side (d = ppl - FP32 ppl)."""
    return round(100.0 * (base - side) / (base - top), 2)


def headline():
    """out/headline_vb<VB>.json: spec-width sidecar d and gap closed; no new evals.

    Same formula as results/ppa_data.derived (the 84.7 % / 83.4 % VB16 figures): 4-bit end =
    W4A4+mig+wclip, 8-bit end = W8A8 (GPT-2 novelty.json final_long_eval d_all12, Qwen qwen.json
    d_all; same 8192-token data). Also given with W8A4+mig+wclip (alternatives.json) as 8-bit end.
    """
    T = load()["tables"]
    sch = f"SidecarCIM+wclip k2,VB{VB0}"
    nov = {r["scheme"]: r for r in json.loads((OUT / "novelty.json").read_text())
           ["final_long_eval"][1:]}
    qw = {r["scheme"]: r for r in json.loads((OUT / "qwen.json").read_text())["rows"]}
    w8a8 = {"gpt2": (nov["W8A8"]["d_all12"], nov["W8A8"]["se_all12"], "novelty.json"),
            "qwen": (qw["W8A8"]["d_all"], qw["W8A8"]["se_all"], "qwen.json")}
    out = {"source": "python/out/alternatives.json (+ novelty.json / qwen.json for W8A8); "
                     "written by python/alternatives.py headline; no LLM eval rerun",
           "spec_outlier_weight_bits": VB0, "scheme": sch,
           "eval": "WikiText-2 test, first 8192 tokens, 8 windows; d = ppl - FP32 ppl, "
                   "SE = paired over windows (novelty_study.paired)",
           "formula": "gap_closed_pct = 100 * (d[W4A4+mig+wclip] - d[scheme]) / "
                      "(d[W4A4+mig+wclip] - d[8-bit end])",
           "formula_note": "the 84.7 % (GPT-2) / 83.4 % (Qwen) VB16 figures "
                           "(results/ppa_data.derived) use 8-bit end = W8A8; the W8A4+mig+wclip "
                           "end is given as a second, separate number",
           "models": {}}
    for m in ("gpt2", "qwen"):
        rows = {r["scheme"]: r for r in T[m]["rows"]}
        v, r16 = rows[sch], rows[REF]
        base, top4 = rows["W4A4+mig+wclip"]["d"], rows["W8A4+mig+wclip"]["d"]
        d8, se8, src8 = w8a8[m]
        if m == "gpt2":
            assert abs(nov["W4A4+mig+wclip"]["d_all12"] - base) < 1e-3
        else:
            assert abs(qw["W4A4+mig+wclip"]["d_all"] - base) < 1e-3
        out["models"][m] = {
            "fp32_ppl": T[m]["fp32_ppl"], "ppl": v["ppl"], "d_vs_fp32": v["d"],
            "se": v["se"], "sat_slots_pct": v["sat_slots_pct"], "mean_S": v["mean_S"],
            "vs_VB16": v["vs_ref"],
            "ends": {"W4A4+mig+wclip": [base, rows["W4A4+mig+wclip"]["se"]],
                     "W8A8": [d8, se8, src8],
                     "W8A4+mig+wclip": [top4, rows["W8A4+mig+wclip"]["se"]]},
            "gap_closed_pct_to_W8A8": gap_pct(base, v["d"], d8),
            "gap_closed_pct_to_W8A4_mig_wclip": gap_pct(base, v["d"], top4),
            "VB16_same_formula": {"d_vs_fp32": r16["d"], "se": r16["se"],
                                  "gap_closed_pct_to_W8A8": gap_pct(base, r16["d"], d8),
                                  "gap_closed_pct_to_W8A4_mig_wclip":
                                      gap_pct(base, r16["d"], top4)}}
    (OUT / f"headline_vb{VB0}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["models"], indent=1))


if __name__ == "__main__":
    _selftest()
    {"gpt2": stage_gpt2, "qwen": stage_qwen, "report": report,
     "headline": headline}[sys.argv[1]]()
