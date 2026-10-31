"""Tile-size scaling: SidecarCIM accuracy when one array column spans R rows (R = 32..256).

Usage: python tile_scaling.py gpt2 | qwen | report   (each stage resumes from out/tile_scaling.json)
Protocol = alternatives.py / extras.py: GPT-2 all 12 c_fc; Qwen2.5-0.5B all 24 gate+up; calib =
first 512 WikiText-2 train tokens; eval = first 8192 test tokens (8 windows of 1024); per-window
NLL stored; paired SE vs FP32 (novelty_study.paired); difference vs the R=32, k=2 reference with
leave-one-window-out jackknife SE and t (extras.diff_stats). Alpha picked on calib per scheme and
layer (GPT-2: novelty_study.encode_pick2, Qwen: qwen_eval.pick_encode, as in alternatives.py);
weight clip search on; slot values VB = spec outlier.weight_bits (12); top-k |w| slots.
Per tile height R in RS (rows per array column = tile column):
  k2     k = 2 slots per R-row tile column (fixed hardware)
  kprop  k = 2*R/32 (2 slots per 32 rows: 2, 4, 8, 16); at R=32 this is the k2 run
  extra  (R, k) = (128, 4), (256, 4), (256, 8): intermediate budgets for the frontier
Frontier (report): per R, the smallest evaluated k whose diff vs R32,k2 has |t| < 2 or t <= -2
(not worse) on BOTH models.
  dense  W4A4+mig+wclip (no sidecar). Its weight scale is per output channel over all rows, so its
         encoding cannot depend on R: it is encoded at every R, golden-checked on R-row tiles and
         asserted identical (md5 of s, sx, zx, sw, zw, S, codes) to the R=32 encoding; the NLL is
         evaluated once (R=32) and reused.
Rows not a multiple of R (only Qwen d_model 896 at R=256): the existing code has no partial
tiles (every layer is a multiple of 32; encode reshapes into whole tiles). Here W is padded with
zero rows and X with zero columns up to a multiple of R, i.e. the last array tile is partly
filled (896 = 3*256 + 128 used rows; it gets the full k slots). Pad rows hold weight 0 (code zw)
and act 0 (code zx), so they add exactly 0, never displace a real slot (|w| = 0 sorts last) and
do not change migration scales, activation range, weight ranges or clipping. The encoding is
golden-checked on the padded R-row tiles, then the pad rows are dropped for the forward pass
(asserted exactly equal on the checked tokens).
Golden checks per layer and scheme: llm_layer.golden_check on R-row tiles (golden.dcim_dot via
quant.signed_dot, golden.sidecar_dot via quant.sidecar_signed, both take n_inputs from their
arguments), plus merge_check: golden.sidecarcim_dot per tile (raw macro output, fits
golden.merged_width(R, 4, 4, 12, k)) + off-macro zero-point correction, summed over tiles, equals
the integer path's merged y_int.
Gap closed = 100 * (d[dense, same R] - d[scheme]) / (d[dense, same R] - d[W8A8]); W8A8 d from
headline_vb<VB>.json (as in alternatives.py headline).
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "6")                     # share the machine with flow runs

import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

import qwen_eval as q  # noqa: E402
from alternatives import gap_pct, slot_stats  # noqa: E402
from extras import diff_stats  # noqa: E402
from golden import SPEC, merged_width, sidecarcim_dot  # noqa: E402
from llm_layer import (CALIB_TOKENS, N_IN, OUT, act_codes, capture, fc_names,  # noqa: E402
                       golden_check, int_forward, load_wikitext)
from novelty_study import B, encode_pick2, paired, ppl, sigma_mask, window_nll  # noqa: E402

FILE = OUT / "tile_scaling.json"
K = SPEC["outlier"]["budget_per_output"]
VB0 = SPEC["outlier"]["weight_bits"]
LONG = 8192
RS = (N_IN, 2 * N_IN, 4 * N_IN, 8 * N_IN)              # 32, 64, 128, 256
EXTRA = [(4 * N_IN, 4), (8 * N_IN, 4), (8 * N_IN, 8)]  # iso-accuracy frontier points


def kprop(R):
    """2 slots per 32 rows."""
    return K * R // N_IN


def runs():
    """(R, k) units in run order (EXTRA appended so older results resume); k = 0 is dense."""
    out = [(N_IN, K), (N_IN, 0)]
    for R in RS[1:]:
        out += [(R, K), (R, kprop(R)), (R, 0)]
    return out + [u for u in EXTRA if u not in out]


def shown():
    """Table order: by R, sidecar k ascending, dense last."""
    return sorted(runs(), key=lambda u: (u[0], u[1] == 0, u[1]))


def cfg_for(k):
    return dict(B, k=k, wclip=True, vb=VB0) if k else dict(B, wclip=True)


def ukey(m, R, k):
    return f"{m}|R{R}|k{k}"


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(res, indent=1))


# ---------------- tiles, padding, checks ----------------

def pad(A, axis, R):
    """Zero rows/cols along axis up to a multiple of R."""
    extra = (-A.shape[axis]) % R
    if not extra:
        return A
    w = [(0, 0)] * A.ndim
    w[axis] = (0, extra)
    return np.pad(A, w)


def strip(e, d_in):
    """Drop pad rows for the forward pass (they hold exact zeros)."""
    if e["Wc"].shape[1] == d_in:
        return e
    assert not e["Wc"][:, d_in:].any() and not e["V"][:, d_in:].any()
    e = dict(e)
    e["s"], e["Wq"] = e["s"][:d_in], e["Wq"][:d_in]
    e["Wc"], e["V"] = e["Wc"][:, :d_in], e["V"][:, :d_in]
    return e


def merge_check(e, X, t):
    """Per R-row tile: golden.sidecarcim_dot + zero-point correction, summed = integer path y_int."""
    cfg, n, k = e["cfg"], e["n"], e["cfg"]["k"]
    if not k:
        return
    wb, ab, vb = cfg["wbits"], cfg["abits"], cfg.get("vb", VB0)
    assert e["G"] == 1
    xq = act_codes(e, X[[t]])[0]
    zx, zw, S = np.int64(e["zx"]), e["zw"][0].astype(np.int64), e["S"][0]
    p2 = np.int64(1) << S
    y = np.zeros(zw.shape, np.int64)
    for r in range(e["Wq"].shape[0] // n):
        sl = slice(r * n, (r + 1) * n)
        w, x = e["Wq"][sl], xq[sl]
        raw = sidecarcim_dot(w, x, e["idx"][r], e["val"][r], S, wb, ab, vb)   # width asserted
        corr = zx * w.sum(axis=0) + zw * x.sum() - n * zw * zx
        y += raw - corr * p2 - zx * e["val"][r].sum(axis=0)
    xc = (xq - zx).astype(np.float64)
    y_int = (xc @ e["Wc"][0]) * p2 + xc @ e["V"][0]
    assert np.array_equal(y, y_int.astype(np.int64))


def check(e, Xp, tokens, d_in):
    """Golden tile checks on the padded encoding; stripped forward equals padded forward."""
    golden_check(e, Xp, tokens)
    merge_check(e, Xp, tokens[0])
    es = strip(e, d_in)
    assert np.array_equal(int_forward(es, Xp[tokens, :d_in]), int_forward(e, Xp[tokens]))


def enc_hash(e, d_in):
    """md5 of everything the forward pass uses (real rows)."""
    h = hashlib.md5()
    for a in (e["s"][:d_in], e["sw"], e["zw"], e["S"], e["Wc"][:, :d_in], e["V"][:, :d_in],
              [e["sx"], e["zx"], -1.0 if e["alpha"] is None else e["alpha"]]):
        h.update(np.ascontiguousarray(np.asarray(a, dtype=np.float64)).tobytes())
    return h.hexdigest()


def outlier_counts(W, e, d_in):
    """[3-sigma weights, of them in a slot, tile columns with > k of them, tile columns]."""
    n, k = e["n"], e["cfg"]["k"]
    sm = pad(sigma_mask(W * e["s"][:d_in, None]), 0, n)
    sm = sm.reshape(-1, n, sm.shape[1])
    cnt = sm.sum(axis=1)
    cov = 0
    if k:
        m = np.zeros(sm.shape, bool)
        np.put_along_axis(m, e["idx"], True, axis=1)
        cov = int((sm & m).sum())
    return np.array([int(sm.sum()), cov, int((cnt > k).sum()), cnt.size], np.int64)


def run_units(m, U, res, layers, get_wb, Xc, pick, nll_fn, ctoks, extra, t0):
    """Encode, check and evaluate every (R, k) unit of model m; save after each unit."""
    for R, k in runs():
        key = ukey(m, R, k)
        if key in U:
            continue
        encs, alphas, sl, hashes = {}, [], [], []
        cnt = np.zeros(4, np.int64)
        for li in layers:
            W, b = get_wb(li)
            d_in = W.shape[0]
            Xp = pad(Xc[li], 1, R)
            e = pick(pad(W, 0, R), b, Xp, cfg_for(k), R)
            check(e, Xp, ctoks, d_in)
            if extra and li in extra:
                check(e, pad(extra[li][0], 1, R), extra[li][1], d_in)
            alphas.append(e["alpha"])
            hashes.append(enc_hash(e, d_in))
            cnt += outlier_counts(W, e, d_in)
            if k:
                sl.append({"cfg": e["cfg"], "val": e["val"], "S": e["S"]})
            encs[li] = q.slim(strip(e, d_in))
            del e, Xp
            q.trim()
        u = {"R": R, "k": k, "alphas": alphas, "enc_md5": hashes,
             "tiles_per_layer": -(-d_in // R),
             "merged_width_bits": merged_width(R, B["wbits"], B["abits"], VB0, k) if k else None,
             "sigma3_weights": int(cnt[0]), "sigma3_in_slot_pct":
                 round(100.0 * cnt[1] / max(cnt[0], 1), 3) if k else None,
             "tilecols_over_k_pct": round(100.0 * cnt[2] / cnt[3], 3),
             **(slot_stats(sl) if k else {"sat_slots_pct": None, "mean_S": None})}
        if k == 0 and R != N_IN:
            ref = U[ukey(m, N_IN, 0)]
            assert hashes == ref["enc_md5"], "dense encoding depends on R"
            u["nll"] = ref["nll"]
            u["nll_reused_from"] = ukey(m, N_IN, 0) + " (identical encoding)"
        else:
            u["nll"] = nll_fn(encs).tolist()
        U[key] = u
        save(res)
        print(f"  {key} ({time.time() - t0:.0f} s, peak RSS {q.peak_gb():.2f} GB)", flush=True)
        del encs, sl
        q.trim()


# ---------------- self-test ----------------

def _selftest():
    rng = np.random.default_rng(17)
    d_in, d_out = 3 * N_IN, 12                          # 96 rows: R = 64 needs a partial tile
    W = rng.normal(0, 0.1, (d_in, d_out))
    W[5, 2], W[40, 7], W[41, 7], W[42, 7] = 2.0, -1.5, 1.4, 1.3
    b = rng.normal(0, 0.1, d_out)
    X = rng.normal(0, 1, (40, d_in))
    X[:, 3] *= 20
    assert runs()[:2] == [(32, 2), (32, 0)] and [kprop(R) for R in RS] == [2, 4, 8, 16]
    base = {}
    for pick in (encode_pick2, q.pick_encode):
        for R in (N_IN, 2 * N_IN):
            for k in (K, kprop(R), 0):
                Xp = pad(X, 1, R)
                e = pick(pad(W, 0, R), b, Xp, cfg_for(k), R)
                assert e["n"] == R and e["Wq"].shape[0] % R == 0
                if k:
                    assert e["idx"].shape == (e["Wq"].shape[0] // R, k, d_out)
                check(e, Xp, [0, 1, 39], d_in)
                es = strip(e, d_in)
                y = int_forward(es, X)
                assert np.array_equal(y, int_forward(e, Xp))
                assert np.array_equal(int_forward(q.slim(dict(es)), X), y)
                if R == N_IN:                            # no padding: default path unchanged
                    e0 = pick(W, b, X, cfg_for(k))
                    assert np.array_equal(e0["Wc"], e["Wc"]) and np.array_equal(e0["V"], e["V"])
                    assert e0["alpha"] == e["alpha"]
                if k == 0:
                    base.setdefault(pick, enc_hash(e, d_in))
                    assert enc_hash(e, d_in) == base[pick]   # dense does not depend on R
                c = outlier_counts(W, e, d_in)
                assert c[1] <= c[0] and c[2] <= c[3]
    # partial tile slots stay on real rows (pad rows are |w| = 0)
    e = encode_pick2(pad(W, 0, 64), b, pad(X, 1, 64), cfg_for(4), 64)
    assert e["idx"][1].max() < d_in - 64
    print(f"tile_scaling self-test passed (R {N_IN}/{2 * N_IN} incl. partial tile, "
          f"both alpha pickers, golden + merge checks)")


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
    run_units("gpt2", U, res, names, lambda n: (Ws[n], bs[n]), Xc, encode_pick2,
              lambda encs: window_nll(model, wins, encs), [0, 255, CALIB_TOKENS - 1],
              {h0: (Xe0, [0, 511, 1023])}, t0)
    report()


# ---------------- Qwen ----------------

def stage_qwen():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
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
    Xc = {i: Xc[n] for i, n in enumerate(names)}
    res = load()
    U = res["units"]
    if "qwen_fp32" not in U:
        U["qwen_fp32"] = {"nll": q.window_nll(model, wins).tolist()}
        save(res)
    run_units("qwen", U, res, list(range(L)), lambda i: q.layer_weights(model, i), Xc,
              q.pick_encode, lambda encs: q.window_nll(model, wins, encs),
              [0, 100, CALIB_TOKENS - 1], None, t0)
    report()


# ---------------- report ----------------

def label(R, k):
    if k == 0:
        return "dense W4A4+mig+wclip"
    if R == N_IN:
        return f"k={k} (reference; both series)"
    if k == K:
        return f"k={k} fixed"
    return f"k={k} (2 per 32 rows)" if k == kprop(R) else f"k={k} (frontier point)"


def not_worse(v):
    """|t| < 2 or significantly better vs the reference."""
    return v is not None and v["t"] is not None and (abs(v["t"]) < 2 or v["t"] <= -2)


def frontier(tables):
    """Per R: smallest evaluated k not worse than R32,k2 on every model in tables."""
    out = {}
    for R in RS:
        ks = sorted({r["k"] for t in tables.values() for r in t["rows"] if r["R"] == R and r["k"]})
        ok = None
        for k in ks:
            rs = [next((r for r in t["rows"] if (r["R"], r["k"]) == (R, k)), None)
                  for t in tables.values()]
            if all(r is not None and ((R, k) == (N_IN, K) or not_worse(r["vs_ref"]))
                   for r in rs):
                ok = k
                break
        out[str(R)] = {"k_min": ok, "k_evaluated": ks, "slots_per_32_rows":
                       None if ok is None else round(ok * N_IN / R, 3),
                       "t": {m: next((r["vs_ref"]["t"] if r["vs_ref"] else None)
                                     for r in t["rows"] if (r["R"], r["k"]) == (R, ok))
                             for m, t in tables.items()} if ok else None}
    return out


def report():
    res = load()
    U = res["units"]
    hl = json.loads((OUT / f"headline_vb{VB0}.json").read_text())["models"]
    alt = json.loads((OUT / "alternatives.json").read_text())["units"]
    res["tables"], text = {}, []
    for m, title in (("gpt2", "GPT-2, all 12 c_fc"), ("qwen", "Qwen2.5-0.5B, all 24 gate+up")):
        fpk = m + "_fp32"
        if fpk not in U:
            continue
        fp = np.array(U[fpk]["nll"])
        ref = U.get(ukey(m, N_IN, K))
        w8 = hl[m]["ends"]["W8A8"][0]
        rows = []
        for R, k in shown():
            u = U.get(ukey(m, R, k))
            if not u:
                continue
            a = np.array(u["nll"])
            d, se = paired(a, fp)
            dense = U.get(ukey(m, R, 0))
            gap = None
            if k and dense:
                gap = gap_pct(paired(np.array(dense["nll"]), fp)[0], d, w8)
            rows.append({"R": R, "k": k, "scheme": label(R, k), "ppl": round(ppl(a), 4),
                         "d": d, "se": se,
                         "vs_ref": diff_stats(a, ref["nll"]) if ref and (R, k) != (N_IN, K)
                         else None,
                         "gap_closed_pct_to_W8A8": gap, "sat_slots_pct": u["sat_slots_pct"],
                         "mean_S": u["mean_S"], "sigma3_in_slot_pct": u["sigma3_in_slot_pct"],
                         "tilecols_over_k_pct": u["tilecols_over_k_pct"],
                         "merged_width_bits": u["merged_width_bits"],
                         "nll_reused_from": u.get("nll_reused_from")})
        chk = {}
        for k, name in ((K, f"SidecarCIM+wclip k2,VB{VB0}"), (0, "W4A4+mig+wclip")):
            u, o = U.get(ukey(m, N_IN, k)), alt.get(f"{m}|{name}")
            if u and o:
                chk[name] = float(np.abs(np.array(u["nll"]) - np.array(o["nll"])).max())
        res["tables"][m] = {"fp32_ppl": round(ppl(fp), 4), "W8A8_d": w8, "rows": rows,
                            "check_R32_vs_alternatives_max_abs_dnll": chk}
        out = [f"\n{title}; 8192 tok (8 windows); FP32 ppl {ppl(fp):.4f}; "
               f"ref = R{N_IN} k{K}; gap to W8A8 (d {w8:+.4f}) from dense at same R",
               f"{'R':>4s} {'scheme':26s} {'ppl':>9s} {'d vs FP32 ±SE':>18s} "
               f"{'diff vs ref ±SE':>18s} {'t':>6s} {'gap%':>6s} {'sat%':>6s} "
               f"{'3s-in-slot%':>11s} {'cols>k%':>8s}"]
        for r in rows:
            v = r["vs_ref"]
            dv = f"{v['dppl']:+8.4f} ± {v['se_jackknife']:.4f}" if v else "(reference)"
            t = f"{v['t']:+6.2f}" if v and v["t"] is not None else ""
            g = "" if r["gap_closed_pct_to_W8A8"] is None else f"{r['gap_closed_pct_to_W8A8']:6.1f}"
            s = "" if r["sat_slots_pct"] is None else f"{r['sat_slots_pct']:6.3f}"
            c = "" if r["sigma3_in_slot_pct"] is None else f"{r['sigma3_in_slot_pct']:11.2f}"
            out.append(f"{r['R']:4d} {r['scheme']:26s} {r['ppl']:9.4f} {r['d']:+8.4f} ± "
                       f"{r['se']:.4f} {dv:>18s} {t:>6s} {g:>6s} {s:>6s} {c:>11s} "
                       f"{r['tilecols_over_k_pct']:8.2f}")
        out.append(f"check vs alternatives.json (R{N_IN}), max |dNLL|: {chk}")
        text.append("\n".join(out))
    if len(res["tables"]) == 2:
        res["frontier"] = {"rule": "per R, smallest evaluated k with diff vs R32,k2 |t| < 2 or "
                                   "t <= -2 (jackknife over 8 windows) on BOTH GPT-2 and Qwen",
                           "by_R": frontier(res["tables"])}
        text.append("\nfrontier (min k not worse than R32,k2 on both models): " + "; ".join(
            f"R{R}: k={f['k_min']} (evaluated {f['k_evaluated']}, t {f['t']})"
            for R, f in res["frontier"]["by_R"].items()))
    print("\n".join(text))
    save(res)


if __name__ == "__main__":
    _selftest()
    {"gpt2": stage_gpt2, "qwen": stage_qwen, "report": report}[sys.argv[1]]()
