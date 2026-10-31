"""Edge studies C (narrow shift range) and D (pooled slots) for SidecarCIM, full test set.

Usage: python edge_variants.py calib            calib-only stats: S histograms, pool score choice
       python edge_variants.py gpt2 srange|pooled
       python edge_variants.py qwen srange|pooled
       python edge_variants.py report srange|pooled
Protocol = fulltest.py: GPT-2 all 12 c_fc (alpha picked on calib layer error with the scheme's
own cfg), Qwen2.5-0.5B all 24 gate+up (alpha picked without wclip, final encode with wclip);
calib = first 512 WikiText-2 train tokens; eval = every full 1024-token window of the test
split (GPT-2 280, Qwen 292); integer path golden-checked tile by tile. Reference = SidecarCIM+
wclip k2,VB12; its per-window NLL is read from out/fulltest.json (not rerun; this encoder
reproduces its encoding array-equal and its first windows' NLL exactly, checked in each run).
Stats = fulltest.compare (paired t, TOST +-0.25 ppl, 90 % CI).
C  srange: per-column shift S restricted to {base .. base + 2^sbits - 1} (within 0..VB-1).
   S_ideal = floor(log2(vmax * sw / max|slot|)) as now; S = clip(S_ideal, base, top).
   S > S_ideal: slot values clamp at +-vmax (saturation); S < S_ideal: coarser slot grid.
   base per layer offline = argmin over bases of the E[x^2]-weighted slot error on calib
   (dense codes do not depend on S, so this is the whole layer-error change).
D  pooled: each 32x8 tile has P slots shared by its 8 columns; a slot = (column id, row id,
   VB12 value). Slots = the P largest |w| (after migration) in the tile; |w| beat |w|/column
   std and the E[x^2]-weighted residual on calib layer error (both models, out/pooled.json
   "calib"). Per-column S as now (column without any slot: S = 0). Golden:
   pooled_sidecar_dot (bit-serial, MSB first) tile by tile.
"""
import json
import os
import sys
import time

import numpy as np

from fulltest import CHUNK, compare
from fulltest import FILE as FT_FILE
from fulltest import REF
from golden import SPEC
from llm_layer import (CALIB_TOKENS, N_IN, OUT, VB, act_codes, capture, fc_names,
                       golden_check, int_forward, int_parts, load_wikitext, mse_clip, rel_l2,
                       smooth_scales)
from novelty_study import ALPHAS, B, encode2, ppl, resid_score, select_rows, sigma_mask
from quant import qmax, quant_params, quantize_with, range_params, signed_dot

N_OUT = SPEC["array"]["n_outputs"]
K = SPEC["outlier"]["budget_per_output"]
EXACT = 2.0 ** 53
REF_CFG = dict(B, k=K, wclip=True, vb=12)
PSEL = "mag"                     # pool score: lowest mean calib layer error, both models
STUDIES = {
    "srange": [("SidecarCIM+wclip k2,VB12 S2b/layer", dict(REF_CFG, sbits=2, sbase="pick")),
               ("SidecarCIM+wclip k2,VB12 S3b/layer", dict(REF_CFG, sbits=3, sbase="pick"))],
    "pooled": [(f"SidecarCIM+wclip pool P{p},VB12", dict(REF_CFG, k=0, pool=p))
               for p in (16, 12, 10, 8)],
}


# ---------------- golden: pooled sidecar ----------------

def pooled_sidecar_dot(rows, cols, vals, x, abits, vbits, n_out=N_OUT):
    """Pooled sidecar of one tile: y[c] = sum over slots s with cols[s]=c of vals[s]*x[rows[s]].

    Bit-serial over x, MSB first, like golden.sidecar_dot: each input-bit cycle every slot adds
    its signed value to the accumulator of its column when its row's bit is 1, then shift.
    """
    rows, cols = np.asarray(rows, np.int64), np.asarray(cols, np.int64)
    vals, x = np.asarray(vals, np.int64), np.asarray(x, np.int64)
    assert vals.min() >= -(1 << (vbits - 1)) and vals.max() < (1 << (vbits - 1))
    assert rows.min() >= 0 and rows.max() < x.shape[0] and cols.min() >= 0 and cols.max() < n_out
    acc = np.zeros(n_out, np.int64)
    for a in range(abits - 1, -1, -1):
        part = np.zeros(n_out, np.int64)
        np.add.at(part, cols, vals * ((x[rows] >> a) & 1))
        acc = (acc << 1) + part
    return acc


def golden_check_pooled(enc, X, tokens):
    """Integer parts = golden dense (signed_dot) + pooled_sidecar_dot, tile by tile."""
    cfg, n = enc["cfg"], enc["n"]
    xq = act_codes(enc, X[tokens])
    D, Sd = int_parts(enc, xq)
    n_rt, n_ct = enc["prow"].shape[:2]
    vb = cfg["vb"]
    for i in range(len(tokens)):
        gd = np.zeros(D.shape[2], np.int64)
        gs = np.zeros_like(gd)
        for r in range(n_rt):
            sl = slice(r * n, (r + 1) * n)
            gd += signed_dot(enc["Wq"][sl], xq[i, sl], enc["zw"][0], enc["zx"], cfg["wbits"],
                             cfg["abits"])
            for c in range(n_ct):
                pr, pc, pv = enc["prow"][r, c], enc["pcol"][r, c], enc["pval"][r, c]
                y = pooled_sidecar_dot(pr, pc, pv, xq[i, sl], cfg["abits"], vb)
                cs = np.bincount(pc, weights=pv, minlength=N_OUT).astype(np.int64)
                gs[c * N_OUT:(c + 1) * N_OUT] += y - np.int64(enc["zx"]) * cs
        assert np.array_equal(gd, D[0, i].astype(np.int64))
        assert np.array_equal(gs, Sd[0, i].astype(np.int64))
    return True


# ---------------- encoding ----------------

def pool_mask(Ws, h, P, psel, wbits, n=N_IN):
    """P slots per n x N_OUT tile: (n_rt, n, d_out) bool, plus slot lists per tile."""
    d_in, d_out = Ws.shape
    n_rt, n_ct = d_in // n, d_out // N_OUT
    assert n_rt * n == d_in and n_ct * N_OUT == d_out
    if psel == "mag":
        sc = np.abs(Ws)
    elif psel == "z":
        sc = np.abs(Ws) / np.maximum(Ws.std(axis=0, keepdims=True), 1e-30)
    else:
        assert psel == "resid"
        sc = resid_score(Ws, h, 1, wbits)
    t = sc.reshape(n_rt, n, n_ct, N_OUT).transpose(0, 2, 1, 3).reshape(n_rt, n_ct, n * N_OUT)
    top = np.argsort(-t, axis=2, kind="stable")[:, :, :P]          # flat index row*8 + col
    mask = np.zeros((n_rt, n_ct, n * N_OUT), bool)
    np.put_along_axis(mask, top, True, axis=2)
    mask = mask.reshape(n_rt, n_ct, n, N_OUT).transpose(0, 2, 1, 3).reshape(n_rt, n, d_out)
    top = np.sort(top, axis=2)
    return mask, top // N_OUT, top % N_OUT


def encode3(W, b, Xcal, cfg, alpha, n=N_IN):
    """encode2 (G = 1, sel mag) plus restricted S range (sbits/sbase) or pooled slots (pool)."""
    assert not cfg["tile"] and not cfg["budget"] and not cfg["aclip"] and cfg["sel"] == "mag"
    d_in, d_out = W.shape
    n_rt = d_in // n
    wbits, abits, k = cfg["wbits"], cfg["abits"], cfg["k"]
    pool, sbits = cfg.get("pool"), cfg.get("sbits")
    vb = cfg.get("vb", VB)
    s = smooth_scales(Xcal, W, alpha) if alpha is not None else np.ones(d_in)
    Ws, Xs = W * s[:, None], Xcal / s[None, :]
    h = (Xs ** 2).mean(axis=0)
    if pool:
        assert k == 0
        mask3, prow, pcol = pool_mask(Ws, h, pool, cfg.get("psel", PSEL), wbits, n)
        idx = None
    else:
        idx = select_rows(Ws, h, k, "mag", 1, wbits, n)
        mask3 = np.zeros((n_rt, n, d_out), bool)
        np.put_along_axis(mask3, idx, True, axis=1)
    mask = mask3.reshape(1, d_in, d_out)
    dense = np.where(mask, 0.0, Ws.reshape(1, d_in, d_out))
    lo, hi = dense.min(axis=1), dense.max(axis=1)
    if cfg["wclip"]:
        lo, hi = mse_clip(dense, h.reshape(1, d_in)[:, :, None] * ~mask, lo, hi, wbits)
    sw, zw = range_params(lo, hi, wbits)
    Wq = quantize_with(dense, sw[:, None], zw[:, None], wbits)
    Wq = np.where(mask, zw[:, None, :], Wq)
    vmax = (1 << (vb - 1)) - 1
    has = mask.any(axis=1)                                          # (1, out)
    om = np.where(mask, np.abs(Ws.reshape(1, d_in, d_out)), 0.0).max(axis=1)
    S_id = np.clip(np.floor(np.log2(vmax * sw / np.maximum(om, 1e-30))), 0, vb - 1)
    S_id = np.where(has, S_id, 0).astype(np.int64)

    def slot_vals(S):
        unit = sw / 2.0 ** S                                        # (1, out)
        v = np.clip(np.round(Ws.reshape(1, d_in, d_out) / unit[:, None, :]), -vmax - 1, vmax)
        v = np.where(mask, v, 0.0)
        err = float((h.reshape(1, d_in, 1) * np.where(mask, Ws.reshape(1, d_in, d_out) -
                                                       unit[:, None, :] * v, 0.0) ** 2).sum())
        return v, err

    S, sinfo = S_id, None
    if sbits:
        width = 1 << sbits
        bases = list(range(0, vb - width + 1))
        if cfg["sbase"] == "pick":
            errs = [slot_vals(np.clip(S_id, bb, bb + width - 1))[1] for bb in bases]
            base = bases[int(np.argmin(errs))]
        else:
            base = int(cfg["sbase"])
        S = np.clip(S_id, base, base + width - 1)
        sinfo = {"base": base, "top": base + width - 1,
                 "cols": int(has.sum()),
                 "cols_S_raised": int(((S > S_id) & has).sum()),     # values may clamp
                 "cols_S_lowered": int(((S < S_id) & has).sum()),    # coarser slot grid
                 "slot_err_ratio": None}
    T = np.zeros_like(S)
    if cfg.get("tbits"):                 # sidecar-side shift for columns that need S < 0
        assert not sbits and not pool
        raw = np.floor(np.log2(vmax * sw / np.maximum(om, 1e-30)))
        T = np.where(has & (raw < 0), np.clip(-raw, 0, (1 << cfg["tbits"]) - 1), 0)
        T = T.astype(np.int64)
        sw_t = sw * 2.0 ** T                       # slot grid = sw * 2^T / 2^S (S = 0 there)

        def slot_vals(S, sw=sw_t):                 # noqa: F811 (same as above, coarser grid)
            unit = sw / 2.0 ** S
            v = np.clip(np.round(Ws.reshape(1, d_in, d_out) / unit[:, None, :]), -vmax - 1,
                        vmax)
            v = np.where(mask, v, 0.0)
            return v, 0.0
    V, err = slot_vals(S)
    if sbits:
        sinfo["slot_err_ratio"] = round(err / max(slot_vals(S_id)[1], 1e-300), 6)
    maxper = int(mask3.sum(axis=1).max())
    assert d_in * qmax(abits) * (qmax(wbits) * 2.0 ** S.max() +
                                 maxper * vmax * 2.0 ** T.max()) < EXACT
    Vm = V                                         # slot mantissas (VB bits)
    V = Vm * 2.0 ** T[:, None, :]                  # effective values (C << T), exact
    sx, zx = quant_params(Xs, abits)
    enc = dict(cfg=cfg, alpha=alpha, s=s, sx=float(sx), zx=int(zx), sw=sw, zw=zw, S=S, G=1, n=n,
               Wq=Wq.reshape(d_in, d_out), b=b, Wc=(Wq - zw[:, None, :]).astype(np.float64),
               V=V, S_ideal=S_id, sinfo=sinfo, T=T)
    V3 = Vm.reshape(n_rt, n, d_out)
    if pool:
        n_ct = d_out // N_OUT
        V4 = V3.reshape(n_rt, n, n_ct, N_OUT)
        rr, cc = np.arange(n_rt)[:, None, None], np.arange(n_ct)[None, :, None]
        enc.update(prow=prow, pcol=pcol, pval=V4[rr, prow, cc, pcol].astype(np.int64),
                   idx=np.zeros((n_rt, 0, d_out), np.int64), val=np.zeros((n_rt, 0, d_out),
                                                                          np.int64))
    else:
        enc.update(idx=idx, val=np.take_along_axis(V3, idx, axis=1).astype(np.int64))
    sm = sigma_mask(Ws)
    enc["slot_stats"] = slot_stats(dict(enc, V=Vm), mask3, sm, vb)
    if cfg.get("tbits"):
        enc["slot_stats"]["T_hist"] = {int(a): int(c) for a, c in
                                       zip(*np.unique(T[has], return_counts=True))}
    return enc


def slot_stats(enc, mask3, sm, vb):
    """Saturation, S use, 3-sigma cover and (pooled) slots per tile column."""
    v = enc["V"][0][mask3.reshape(-1, mask3.shape[2])]
    lim = (1 << (vb - 1)) - 1
    per = mask3.sum(axis=1)                                         # (n_rt, out)
    has = per.sum(axis=0) > 0
    smt = sm.reshape(mask3.shape)
    sig_per = smt.sum(axis=1)

    def hist(a):
        return {int(x): int(c) for x, c in zip(*np.unique(a, return_counts=True))}
    return {"slots": int(mask3.sum()), "sat_slots": int(((v >= lim) | (v <= -lim - 1)).sum()),
            "S_hist": hist(enc["S"][0][has]), "S_ideal_hist": hist(enc["S_ideal"][0][has]),
            "sigma3_weights": int(sm.sum()),
            "sigma3_covered_pct": round(100.0 * float((smt & mask3).sum()) / max(sm.sum(), 1), 3),
            "tilecols_sigma3_over_k2_pct": round(100.0 * float((sig_per > K).mean()), 4),
            "tilecol_slots_hist": hist(per), "tilecol_slots_max": int(per.max())}


def pick_gpt2(W, b, Xc, cfg):
    """= novelty_study.encode_pick2 with encode3."""
    if cfg["alpha"] != "pick":
        return encode3(W, b, Xc, cfg, cfg["alpha"])
    ref = Xc @ W + b
    a = min((rel_l2(int_forward(encode3(W, b, Xc, cfg, a), Xc), ref), a) for a in ALPHAS)[1]
    return encode3(W, b, Xc, cfg, a)


def pick_qwen(W, b, Xc, cfg):
    """= qwen_eval.pick_encode with encode3 (alpha without wclip, final with wclip)."""
    alpha = cfg["alpha"]
    if alpha == "pick":
        ref = Xc @ W + b
        c0 = dict(cfg, wclip=False)
        alpha = min((rel_l2(int_forward(encode3(W, b, Xc, c0, a), Xc), ref), a)
                    for a in ALPHAS)[1]
    return encode3(W, b, Xc, cfg, alpha)


def sig(e):
    """Hash of everything the integer path uses (alpha, scales, codes, slots, S)."""
    import hashlib
    h = hashlib.sha1(repr((e["alpha"], e["sx"], e["zx"])).encode())
    for key in ("s", "sw", "zw", "S", "Wc", "V"):
        h.update(np.ascontiguousarray(np.asarray(e[key], np.float64)).tobytes())
    return h.hexdigest()


def golden_check_tshift(enc, X, tokens):
    """Sidecar-side shift: integer sidecar part = sum over tiles of golden.sidecar_dot(.., T)
    minus the zero-point term (zx * sum(val)) << T; dense part as golden_check."""
    from golden import sidecar_dot
    T = np.asarray(enc["T"])[0]
    n_rt = enc["Wq"].shape[0] // enc["n"]
    Vm = np.zeros_like(np.asarray(enc["V"], np.float64)).reshape(n_rt, enc["n"], -1)
    np.put_along_axis(Vm, enc["idx"], enc["val"].astype(np.float64), axis=1)
    golden_check(dict(enc, V=Vm.reshape(np.asarray(enc["V"]).shape)), X, tokens)  # mantissas
    assert np.array_equal(np.asarray(enc["V"], np.float64),
                          Vm.reshape(np.asarray(enc["V"]).shape) * 2.0 ** T[None, None, :])
    cfg, n = enc["cfg"], enc["n"]
    xq = act_codes(enc, X[tokens])
    _, Sd = int_parts(enc, xq)
    for i in range(len(tokens)):
        gs = np.zeros(Sd.shape[2], np.int64)
        for r in range(n_rt):
            xt = xq[i, r * n:(r + 1) * n]
            gs += sidecar_dot(enc["idx"][r], enc["val"][r], xt, cfg["abits"], cfg["vb"], T) - \
                ((np.int64(enc["zx"]) * enc["val"][r].sum(axis=0)) << T)
        assert np.array_equal(gs, Sd[0, i].astype(np.int64))
    return True


def check(enc, X, tokens):
    if enc["cfg"].get("pool"):
        return golden_check_pooled(enc, X, tokens)
    if enc["cfg"].get("tbits"):
        return golden_check_tshift(enc, X, tokens)
    return golden_check(enc, X, tokens)


def same_enc(e, e2):
    """encode3 == encode2 on every array the integer path and golden use."""
    for key in ("s", "sw", "zw", "S", "Wq", "Wc", "V", "idx", "val"):
        assert np.array_equal(np.asarray(e[key]), np.asarray(e2[key])), key
    assert e["sx"] == e2["sx"] and e["zx"] == e2["zx"]
    return True


# ---------------- self-test ----------------

def _selftest():
    rng = np.random.default_rng(23)
    d_in, d_out = N_IN * 3, 16
    W = rng.normal(0, 0.1, (d_in, d_out))
    W[5, 2], W[6, 2], W[7, 2], W[40, 9] = 2.0, 1.8, -1.7, -1.5
    W[70, 13] = 0.9
    b = rng.normal(0, 0.1, d_out)
    X = rng.normal(0, 1, (50, d_in))
    X[:, 3] *= 20
    # pooled golden with k slots per column == golden.sidecar_dot
    from golden import sidecar_dot
    for _ in range(50):
        idx = rng.integers(0, N_IN, (K, N_OUT))
        val = rng.integers(-2048, 2048, (K, N_OUT))
        x = rng.integers(0, 16, N_IN)
        cols = np.repeat(np.arange(N_OUT)[None, :], K, axis=0)
        assert np.array_equal(pooled_sidecar_dot(idx.ravel(), cols.ravel(), val.ravel(), x, 4, 12),
                              sidecar_dot(idx, val, x, 4, 12))
        rows = rng.integers(0, N_IN, 12)
        cols = rng.integers(0, N_OUT, 12)
        vals = rng.integers(-2048, 2048, 12)
        ref = np.zeros(N_OUT, np.int64)
        for r, c, v in zip(rows, cols, vals):
            ref[c] += v * x[r]
        assert np.array_equal(pooled_sidecar_dot(rows, cols, vals, x, 4, 12), ref)
    # encode3 reference mode == encode2 (all alphas)
    for a in ALPHAS:
        assert same_enc(encode3(W, b, X, REF_CFG, a), encode2(W, b, X, REF_CFG, a))
    for name, cfg in STUDIES["srange"] + STUDIES["pooled"]:
        for pick in (pick_gpt2, pick_qwen):
            e = pick(W, b, X, cfg)
            assert check(e, X, [0, 1, 49])
            xd = e["sx"] * (act_codes(e, X) - e["zx"])
            wd = e["sw"][0] * e["Wc"][0] + e["V"][0] * e["sw"][0] / 2.0 ** e["S"][0]
            assert np.allclose(int_forward(e, X), xd @ wd + b)
            if cfg.get("sbits"):
                si = e["sinfo"]
                assert si["base"] <= e["S"].min() and e["S"].max() <= si["top"] <= 11
            if cfg.get("pool"):
                assert e["slot_stats"]["slots"] == cfg["pool"] * (d_in // N_IN) * (d_out // N_OUT)
                assert e["pval"].shape == (d_in // N_IN, d_out // N_OUT, cfg["pool"])
    # a wide S range never changes S; 2-bit S with a forced base raises/lowers as expected
    e = encode3(W, b, X, dict(REF_CFG, sbits=4, sbase=0), 1.0)
    assert np.array_equal(e["S"], encode2(W, b, X, REF_CFG, 1.0)["S"])
    e = encode3(W, b, X, dict(REF_CFG, sbits=2, sbase=8), 1.0)
    assert e["S"].min() >= 8 and e["sinfo"]["cols_S_raised"] > 0
    # pool of 16 per 8 columns catches the planted column-2 cluster (3 slots in one column)
    e = encode3(W, b, X, dict(REF_CFG, k=0, pool=16), 1.0)
    assert e["slot_stats"]["tilecol_slots_max"] >= 3
    # sidecar-side shift: a weight ~1e4 dense steps needs T > 0; exact vs dequant formula
    W2 = W.copy()
    W2[9, 4] = 3000.0
    e = encode3(W2, b, X, dict(REF_CFG, tbits=3), None)
    assert e["T"].max() > 0 and check(e, X, [0, 1, 49])
    xd = e["sx"] * (act_codes(e, X) - e["zx"])
    wd = e["sw"][0] * e["Wc"][0] + e["V"][0] * e["sw"][0] / 2.0 ** e["S"][0]
    assert np.allclose(int_forward(e, X), xd @ wd + b)
    e0 = encode3(W2, b, X, REF_CFG, None)                          # no T: the slot saturates
    assert rel_l2(int_forward(e, X), X @ W2 + b) < rel_l2(int_forward(e0, X), X @ W2 + b)
    assert same_enc(encode3(W, b, X, dict(REF_CFG, tbits=3), 1.0), encode2(W, b, X, REF_CFG, 1.0))
    print("edge_variants self-test passed")


# ---------------- storage ----------------

def fpath(study):
    return OUT / f"{study}.json"


def load(study):
    f = fpath(study)
    return json.loads(f.read_text()) if f.exists() else {"units": {}}


def save(study, res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = fpath(study).with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, fpath(study))


def ft_units():
    return json.loads(FT_FILE.read_text())["units"]


def run_unit(study, res, key, wins, idx, nll_fn, t0):
    U = res["units"]
    u = U.setdefault(key, {"nll": [], "win_idx": []})
    done = len(u["nll"])
    assert u["win_idx"] == list(idx[:done])
    for s in range(done, len(idx), CHUNK):
        part = list(idx[s:s + CHUNK])
        u["nll"] += nll_fn([wins[i] for i in part]).tolist()
        u["win_idx"] += [int(i) for i in part]
        save(study, res)
        print(f"    {key}: {len(u['nll'])}/{len(idx)} ({time.time() - t0:.0f} s)", flush=True)
    return u


def agg_stats(encs):
    """Sum slot stats over layers; keep per-layer srange info."""
    st = [e["slot_stats"] for e in encs]
    out = {"slots": sum(s["slots"] for s in st), "sat_slots": sum(s["sat_slots"] for s in st)}
    out["sat_slots_pct"] = round(100.0 * out["sat_slots"] / max(out["slots"], 1), 5)
    for h in ("S_hist", "S_ideal_hist", "tilecol_slots_hist"):
        tot = {}
        for s in st:
            for a, c in s[h].items():
                tot[int(a)] = tot.get(int(a), 0) + c
        out[h] = dict(sorted(tot.items()))
    sg = sum(s["sigma3_weights"] for s in st)
    out["sigma3_covered_pct"] = round(sum(s["sigma3_covered_pct"] * s["sigma3_weights"]
                                          for s in st) / max(sg, 1), 3)
    out["tilecol_slots_max"] = max(s["tilecol_slots_max"] for s in st)
    si = [e["sinfo"] for e in encs if e["sinfo"]]
    if si:
        out["per_layer_base"] = [s["base"] for s in si]
        out["cols"] = sum(s["cols"] for s in si)
        out["cols_S_raised"] = sum(s["cols_S_raised"] for s in si)
        out["cols_S_lowered"] = sum(s["cols_S_lowered"] for s in si)
        out["cols_S_raised_pct"] = round(100.0 * out["cols_S_raised"] / out["cols"], 4)
        out["cols_S_lowered_pct"] = round(100.0 * out["cols_S_lowered"] / out["cols"], 4)
        out["slot_err_ratio_per_layer"] = [s["slot_err_ratio"] for s in si]
    return out


# ---------------- model setups ----------------

def gpt2_setup():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    torch.set_num_threads(6)
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ids = tok(load_wikitext("test", 10 ** 9))["input_ids"]
    ev = torch.tensor(ids)
    nw = len(ids) // 1024
    wins = [ev[i * 1024:(i + 1) * 1024] for i in range(nw)]
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    names = fc_names(model)
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    Xc = capture(model, names, [torch.tensor(ca)])
    layers = [(n, Ws[n], bs[n], Xc[n]) for n in names]
    return model, wins, layers


def qwen_layers():
    from fulltest import qwen_setup
    q, model, ids, wins, Xc, L = qwen_setup()
    return q, model, wins, L, Xc


# ---------------- stages ----------------

def calib():
    """Calib-only: reference S histograms, encode3 == encode2, pool score choice (P = 16)."""
    out = {}
    model, wins, layers = gpt2_setup()
    import novelty_study as ns
    rows = []
    for n, W, b, Xc in layers:
        e_ref = pick_gpt2(W, b, Xc, REF_CFG)
        assert same_enc(e_ref, ns.encode_pick2(W, b, Xc, REF_CFG))
        a = e_ref["alpha"]
        ref = Xc @ W + b
        r = {"layer": n, "alpha": a, "S_ref": e_ref["slot_stats"]["S_hist"],
             "err_k2": rel_l2(int_forward(e_ref, Xc), ref)}
        for ps in ("mag", "z", "resid"):
            e = encode3(W, b, Xc, dict(REF_CFG, k=0, pool=16, psel=ps), a)
            r[f"err_pool16_{ps}"] = rel_l2(int_forward(e, Xc), ref)
        rows.append(r)
        print(n, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()},
              flush=True)
    out["gpt2"] = rows
    del model
    q, model, wins, L, Xc = qwen_layers()
    rows = []
    for i in range(L):
        W, b = q.layer_weights(model, i)
        e_ref = pick_qwen(W, b, Xc[i], REF_CFG)
        if i < 2:
            assert same_enc(e_ref, q.pick_encode(W, b, Xc[i], REF_CFG))
        a = e_ref["alpha"]
        ref = Xc[i] @ W
        r = {"layer": i, "alpha": a, "S_ref": e_ref["slot_stats"]["S_hist"],
             "err_k2": rel_l2(int_forward(e_ref, Xc[i]), ref)}
        for ps in ("mag", "z", "resid"):
            e = encode3(W, b, Xc[i], dict(REF_CFG, k=0, pool=16, psel=ps), a)
            r[f"err_pool16_{ps}"] = rel_l2(int_forward(e, Xc[i]), ref)
        rows.append(r)
        print(i, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()},
              flush=True)
        q.trim()
    out["qwen"] = rows
    summ = {}
    for m in ("gpt2", "qwen"):
        summ[m] = {k: round(float(np.mean([r[k] for r in out[m]])), 6)
                   for k in ("err_k2", "err_pool16_mag", "err_pool16_z", "err_pool16_resid")}
        tot = {}
        for r in out[m]:
            for s, c in r["S_ref"].items():
                tot[int(s)] = tot.get(int(s), 0) + c
        summ[m]["S_ref_hist_all_layers"] = dict(sorted(tot.items()))
    out["summary"] = summ
    print(json.dumps(summ, indent=1))
    for study in ("srange", "pooled"):
        res = load(study)
        res["calib"] = {"note": "calib-only (512 train tokens), alpha = reference pick; "
                                "rel L2 layer error of each scheme; P=16 pool score candidates",
                        "summary": summ, "per_layer": out}
        save(study, res)


def stage(model_key, study):
    t0 = time.time()
    res = load(study)
    U = res["units"]
    FT = ft_units()
    ref_key = f"{model_key}|{REF}"
    ref_nll = FT[ref_key]["nll"]
    if model_key == "gpt2":
        model, wins, layers = gpt2_setup()
        from novelty_study import window_nll
        nll = lambda ws, encs=None: window_nll(model, ws, encs)      # noqa: E731
        pick, names = pick_gpt2, [n for n, *_ in layers]
        get = lambda i: layers[i][1:]                                # noqa: E731
        L, slim, trim = len(layers), (lambda e: e), (lambda: None)
        enc_key = lambda i: names[i]                                 # noqa: E731
    else:
        q, model, wins, L, Xc = qwen_layers()
        nll = lambda ws, encs=None: q.window_nll(model, ws, encs)    # noqa: E731
        pick, slim, trim = pick_qwen, q.slim, q.trim

        def get(i):
            W, b = q.layer_weights(model, i)
            return W, b, Xc[i]
        enc_key = lambda i: i                                        # noqa: E731
    idx = list(range(len(wins)))
    assert FT[ref_key]["win_idx"] == idx
    res[f"{model_key}_meta"] = {"windows": len(wins), "ctx": len(wins[0]),
                                "reference_nll_from": "out/fulltest.json " + ref_key}
    # reference encodings (signatures); check that encode3 reproduces the reference NLL
    encs, ref_sig = {}, []
    for i in range(L):
        W, b, X = get(i)
        e = pick(W, b, X, REF_CFG)
        check(e, X, [0, CALIB_TOKENS - 1])
        ref_sig.append(sig(e))
        encs[enc_key(i)] = slim(e)
        trim()
    if f"{model_key}_refcheck" not in res:
        got = nll(wins[:2], encs)
        dmax = float(np.abs(got - np.array(ref_nll[:2])).max())
        res[f"{model_key}_refcheck"] = {"windows": 2, "max_abs_dnll": dmax}
        save(study, res)
        print(f"  ref check {model_key}: max |dNLL| over 2 windows = {dmax:.2e}", flush=True)
        assert dmax < 1e-9
    del encs
    trim()
    for name, cfg in STUDIES[study]:
        key = f"{model_key}|{name}"
        u = U.get(key)
        if u and len(u["nll"]) == len(idx):
            continue
        t1 = time.time()
        encs, alphas, stl, same = {}, [], [], True
        for i in range(L):
            W, b, X = get(i)
            e = pick(W, b, X, cfg)
            check(e, X, [0, 255, CALIB_TOKENS - 1])
            alphas.append(e["alpha"])
            stl.append({"slot_stats": e["slot_stats"], "sinfo": e["sinfo"]})
            same = same and sig(e) == ref_sig[i]
            encs[enc_key(i)] = slim(e)
            trim()
        te = time.time() - t1
        st = agg_stats(stl)
        print(f"  {key}: encoded in {te:.0f} s; identical to reference: {same}; "
              f"{json.dumps(st)[:400]}", flush=True)
        if same:        # every layer array-identical to the reference: same NLL, not rerun
            u = U[key] = {"nll": list(ref_nll), "win_idx": list(idx),
                          "identical_to_reference": True}
        else:
            u = run_unit(study, res, key, wins, idx, lambda w, e=encs: nll(w, e), t0)
        u.update(alphas=alphas, encode_sec=round(te, 1), sec=round(time.time() - t1, 1),
                 stats=st)
        save(study, res)
        del encs
        trim()
    report(study)


def report(study):
    res = load(study)
    U = res["units"]
    FT = ft_units()
    res["method"] = __doc__.strip()
    res["reference"] = REF
    res["tables"] = {}
    for m in ("gpt2", "qwen"):
        ref = FT.get(f"{m}|{REF}")
        fp = FT.get(f"{m}|FP32")
        rows = []
        if not ref:
            continue
        n = len(ref["nll"])
        fpn = np.array(fp["nll"][:n])
        rows.append({"scheme": REF + " (fulltest.json)", "ppl": round(ppl(np.array(ref["nll"])), 4),
                     "d_vs_fp32": round(ppl(np.array(ref["nll"])) - ppl(fpn), 4)})
        for name, cfg in STUDIES[study]:
            u = U.get(f"{m}|{name}")
            if not u or len(u["nll"]) < n:
                continue
            a = np.array(u["nll"][:n])
            if u.get("identical_to_reference"):
                vs = {"windows": n, "dppl": 0.0, "ci90_dppl": [0.0, 0.0], "p_two_sided": 1.0,
                      "tost_p": 0.0, "equivalent": True, "different": False,
                      "verdict": "identical encoding in every layer (diff exactly 0)"}
            else:
                vs = compare(a, ref["nll"][:n])
            rows.append({"scheme": name, "windows": n, "ppl": round(ppl(a), 4),
                         "d_vs_fp32": round(ppl(a) - ppl(fpn), 4),
                         "vs_sidecar": vs, "stats": u.get("stats")})
        res["tables"][m] = {"windows": n, "fp32_ppl": round(ppl(fpn), 4), "rows": rows}
        print(f"\n{m}: {n} windows, FP32 {ppl(fpn):.3f}")
        for r in rows:
            v = r.get("vs_sidecar")
            s = r.get("stats") or {}
            extra = (f" sat {s.get('sat_slots_pct')}% raised {s.get('cols_S_raised_pct')}% "
                     f"lowered {s.get('cols_S_lowered_pct')}% cover3s {s.get('sigma3_covered_pct')}"
                     if s else "")
            if v:
                print(f"  {r['scheme']:40s} {r['ppl']:8.3f} d {r['d_vs_fp32']:+.3f} diff "
                      f"{v['dppl']:+.3f} CI [{v['ci90_dppl'][0]:+.3f},{v['ci90_dppl'][1]:+.3f}] "
                      f"p {v['p_two_sided']:.3g} TOST {v['tost_p']:.3g} {v['verdict']}{extra}")
            else:
                print(f"  {r['scheme']:40s} {r['ppl']:8.3f} d {r['d_vs_fp32']:+.3f} (reference)")
    save(study, res)


if __name__ == "__main__":
    _selftest()
    st = sys.argv[1]
    if st == "calib":
        calib()
    elif st == "report":
        report(sys.argv[2])
    else:
        stage(st, sys.argv[2])
