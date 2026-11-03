"""Write DCIM test vectors to python/vectors/ and a small outlier-statistics preview.

Files (all integer arrays): w (cases, n_inputs, n_outputs), x (cases, n_inputs),
y (cases, n_outputs) = golden.dcim_dot(w, x). Unsigned codes, as the dense core sees them.
Real-layer data: GPT-2 small layer from spec, activations captured at that layer's input
(output of ln_2 for h.0.mlp.c_fc) on CALIB_TEXT below. CALIB_TEXT is a short, fixed,
hand-written English paragraph for the first vector set; the accuracy runs use WikiText-2.
"""
import json
import sys
from pathlib import Path

import numpy as np

from golden import ROOT, SPEC, dcim_dot, sidecarcim_dot
from quant import dequantize, qmax, quantize, signed_dot

OUT = ROOT / "python" / "vectors"
N_IN, N_OUT = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
WB, AB = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
N_RANDOM = 10000
N_REAL = 4096
SEED = 2026
VB = SPEC["outlier"]["weight_bits"]
K = SPEC["outlier"]["budget_per_output"]
WIDE = 2 * max(WB, AB)                       # uniform 8-bit DCIM baseline
DENSE_A4 = (8, 6)                            # dense W8A4 / W6A4 at the same throughput (+mig+wclip)

# Fixed calibration text (hand-written for this project; no external source).
CALIB_TEXT = (
    "The small town sat beside a slow river, and every morning the baker opened his shop "
    "before the sun came up. Children walked to school along the stone bridge, stopping to "
    "watch the boats drift past. In the afternoon the library filled with students who read "
    "about history, science, and distant countries. Nobody in the town was rich, but most "
    "people had enough, and neighbors helped each other when the winter was hard. One year a "
    "young engineer arrived with plans to build a new mill that would run on water and wind. "
    "Some people worried that the machines would change their quiet way of life, while others "
    "hoped for better jobs and warmer homes. After many long meetings, the town agreed to try "
    "the idea for one season and then decide together what to do next."
)


# ---------------- helpers ----------------

def code_dtype(bits):
    """Smallest unsigned dtype for codes."""
    return np.uint8 if bits <= 8 else np.uint16


def expected(w, x, wbits=WB, abits=AB):
    """Golden y for a batch: (cases, n_out) int32."""
    y = np.stack([dcim_dot(wi, xi, wbits, abits) for wi, xi in zip(w, x)])
    assert y.max() < 2**31
    return y.astype(np.int32)


def save_if_changed(path, **arrays):
    """Write npz unless an identical file (same keys, dtypes, values) exists: keeps bytes stable."""
    path = Path(path)
    if path.exists():
        with np.load(path) as d:
            same = set(d.files) == set(arrays) and all(
                d[k].dtype == np.asarray(v).dtype and np.array_equal(d[k], v)
                for k, v in arrays.items())
        if same:
            print(f"  {path.name}: unchanged, kept")
            return
    np.savez_compressed(path, **arrays)


def save_npz(path, w, x, y, wbits=WB, abits=AB, **extra):
    """Save one vector file with integer dtypes (code dtype from the widths)."""
    save_if_changed(path, w=w.astype(code_dtype(wbits)), x=x.astype(code_dtype(abits)),
                    y=y.astype(np.int32), **extra)


# ---------------- corner cases ----------------

def corner_cases(n=N_IN, m=N_OUT, wbits=WB, abits=AB):
    """Hand-picked edge cases; returns (w, x, names)."""
    wm, am = qmax(wbits), qmax(abits)
    walt0 = sum(1 << b for b in range(0, wbits, 2))   # 0101...
    aalt0 = sum(1 << b for b in range(0, abits, 2))
    walt1, aalt1 = wm ^ walt0, am ^ aalt0              # 1010...
    W0, X0 = np.zeros((n, m), np.int64), np.zeros(n, np.int64)
    ii, jj = np.meshgrid(np.arange(n), np.arange(m), indexing="ij")
    cases = []

    def add(name, w, x):
        cases.append((name, np.asarray(w, np.int64), np.asarray(x, np.int64)))

    add("zeros", W0, X0)
    add("all_max", W0 + wm, X0 + am)
    add("w_max_x_zero", W0 + wm, X0)
    add("w_zero_x_max", W0, X0 + am)
    for r, c in ((0, 0), (0, m - 1), (n - 1, 0), (n - 1, m - 1)):
        w = W0.copy()
        w[r, c] = wm
        add(f"single_w_r{r}_c{c}", w, X0 + am)
    for r in (0, n - 1):
        x = X0.copy()
        x[r] = am
        add(f"single_x_r{r}", W0 + wm, x)
    for c in range(m):
        w = W0.copy()
        w[:, c] = wm
        add(f"single_col_c{c}", w, X0 + am)
    add("alt_checker", np.where((ii + jj) % 2, walt1, walt0), np.where(np.arange(n) % 2, aalt1, aalt0))
    add("alt_checker_inv", np.where((ii + jj) % 2, walt0, walt1), np.where(np.arange(n) % 2, aalt0, aalt1))
    add("alt1_alt1", W0 + walt1, X0 + aalt1)
    add("alt0_alt0", W0 + walt0, X0 + aalt0)
    add("alt1_alt0", W0 + walt1, X0 + aalt0)
    for b in range(wbits):
        add(f"w_bitplane{b}", W0 + (1 << b), X0 + am)
    for a in range(abits):
        add(f"x_bitplane{a}", W0 + wm, X0 + (1 << a))
    add("ramp", (ii * m + jj) % (wm + 1), np.arange(n) % (am + 1))
    add("ramp_rev", wm - (ii * m + jj) % (wm + 1), am - np.arange(n) % (am + 1))
    add("diag", np.where(jj == ii % m, wm, 0), np.arange(n) % (am + 1))
    names = [c[0] for c in cases]
    return np.stack([c[1] for c in cases]), np.stack([c[2] for c in cases]), names


# ---------------- random cases ----------------

def random_cases(count, seed=SEED, n=N_IN, m=N_OUT, wbits=WB, abits=AB):
    """Uniform random codes, fixed seed."""
    rng = np.random.default_rng(seed)
    w = rng.integers(0, qmax(wbits) + 1, (count, n, m))
    x = rng.integers(0, qmax(abits) + 1, (count, n))
    return w, x


# ---------------- real GPT-2 layer ----------------

def load_layer():
    """GPT-2 layer weight (in, out), bias (out,), input activations (tokens, in) as float64."""
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast

    name = SPEC["workload"]["model"]
    tok = GPT2TokenizerFast.from_pretrained(name)
    model = GPT2LMHeadModel.from_pretrained(name).eval()
    layer = model.get_submodule(SPEC["workload"]["layer"])
    grab = {}
    hook = layer.register_forward_hook(lambda mod, inp, out: grab.update(a=inp[0].detach()))
    with torch.no_grad():
        model(**tok(CALIB_TEXT, return_tensors="pt"))
    hook.remove()
    W = layer.weight.detach().double().numpy()          # Conv1D: (in, out)
    b = layer.bias.detach().double().numpy()
    acts = grab["a"][0].double().numpy()                 # (tokens, in)
    return W, b, acts


def tile(Wq, tr, tc, n=N_IN, m=N_OUT):
    """Tile (row-tile tr, col-tile tc) of a code matrix."""
    return Wq[tr * n:(tr + 1) * n, tc * m:(tc + 1) * m]


def real_layer_cases(Wq, xq_all, count, seed=SEED, n=N_IN, m=N_OUT):
    """Random (tile, token) pairs from quantized weights/activations."""
    d_in, d_out = Wq.shape
    assert d_in % n == 0 and d_out % m == 0
    rng = np.random.default_rng(seed)
    tr = rng.integers(0, d_in // n, count)
    tc = rng.integers(0, d_out // m, count)
    tk = rng.integers(0, xq_all.shape[0], count)
    w = np.stack([tile(Wq, r, c, n, m) for r, c in zip(tr, tc)])
    x = np.stack([xq_all[k, r * n:(r + 1) * n] for k, r in zip(tk, tr)])
    return w, x, tr, tc, tk


def layer_int_dot(xq, Wq, zx, zw, wbits, abits, n=N_IN):
    """Full-layer signed integer dot for one token, tile by tile through the DCIM core."""
    acc = np.zeros(Wq.shape[1], np.int64)
    for r in range(Wq.shape[0] // n):
        acc += signed_dot(Wq[r * n:(r + 1) * n], xq[r * n:(r + 1) * n], zw, zx, wbits, abits)
    return acc


def rel_l2(a, ref):
    """Relative L2 (Frobenius) error."""
    return float(np.linalg.norm(a - ref) / np.linalg.norm(ref))


def outlier_stats(W, b, acts, n=N_IN):
    """Outlier counts (|w| > k*std) and quantization-error preview."""
    k = SPEC["outlier"]["threshold_sigma"]
    budget = SPEC["outlier"]["budget_per_output"]
    s = {"layer": SPEC["workload"]["layer"], "threshold_sigma": k,
         "budget_per_output": budget, "weight_shape_in_out": list(W.shape),
         "calib_tokens": int(acts.shape[0]), "rule": "|w| > k*std (std about 0 mean not removed)"}
    masks = {"per_channel": np.abs(W) > k * W.std(axis=0, keepdims=True),
             "global": np.abs(W) > k * W.std()}
    for key, mask in masks.items():
        col = mask.sum(axis=0)                                    # per output channel, all inputs
        seg = mask.reshape(W.shape[0] // n, n, W.shape[1]).sum(axis=1)   # per tile column
        s[key] = {
            "pct_outlier_weights": round(100.0 * mask.mean(), 4),
            "per_output_channel_full_column": {
                "max": int(col.max()), "mean": round(float(col.mean()), 3),
                "pct_channels_over_budget": round(100.0 * (col > budget).mean(), 2)},
            "per_tile_column_n_inputs": {
                "max": int(seg.max()), "mean": round(float(seg.mean()), 4),
                "pct_over_budget": round(100.0 * (seg > budget).mean(), 4),
                "histogram": np.bincount(seg.ravel()).tolist()},
        }
    # activation preview (per tensor)
    sa = acts.std()
    s["activations_preview"] = {
        "max_abs": round(float(np.abs(acts).max()), 4), "std": round(float(sa), 4),
        "pct_over_k_sigma": round(100.0 * (np.abs(acts) > k * sa).mean(), 4),
        "top_dims_by_max_abs": np.argsort(-np.abs(acts).max(axis=0))[:5].tolist()}
    # quantization error preview: float layer output incl. bias vs. dequantized
    y_ref = acts @ W + b
    wide = 2 * max(WB, AB)
    err = {}
    for wbits, abits in ((WB, AB), (WB, None), (None, AB), (wide, wide)):
        Wd = W if wbits is None else dequantize(*quantize(W, wbits, axis=0))
        Ad = acts if abits is None else dequantize(*quantize(acts, abits))
        tag = f"W{wbits or 'fp'}A{abits or 'fp'}"
        err[tag] = round(rel_l2(Ad @ Wd + b, y_ref), 5)
    s["preview_rel_l2_layer_output_error"] = err
    s["preview_note"] = ("PREVIEW ONLY: uniform min/max quantization, per-output-channel "
                         "weights, per-tensor activations, on CALIB_TEXT; not the Layer 2 eval")
    return s


# ---------------- SidecarCIM (dense + sidecar merge) vectors ----------------

def side_expected(w, x, idx, val, S, wbits=WB, abits=AB, sbits=None):
    """Golden Y = (dcim_dot << S) + sidecar_dot for a batch: (cases, n_out) int32."""
    y = np.stack([sidecarcim_dot(*c, wbits, abits, sbits=sbits)
                  for c in zip(w, x, idx, val, S)])
    assert y.min() >= -2**31 and y.max() < 2**31
    return y.astype(np.int32)


def save_side(path, w, x, idx, val, S, y, **extra):
    """Sidecar vector file: w, x, idx, S unsigned; val int16; y int32."""
    save_if_changed(path, w=w.astype(np.uint8), x=x.astype(np.uint8), idx=idx.astype(np.uint8),
                    val=val.astype(np.int16), S=S.astype(np.uint8), y=y.astype(np.int32), **extra)


def sidecar_corner_cases(n=N_IN, m=N_OUT, wbits=WB, abits=AB, k=K, vb=VB, sm=None):
    """Sidecar and merge edge cases; returns (w, x, idx, val, S, names).

    sm: largest S (default vb-1; 7 for the 3-bit S of rtl SBITS=3).
    """
    sm = vb - 1 if sm is None else sm
    rng = np.random.default_rng(SEED + 1)
    wm, am = qmax(wbits), qmax(abits)
    lo, hi = -(1 << (vb - 1)), (1 << (vb - 1)) - 1
    cases = []

    def rw():
        return rng.integers(0, wm + 1, (n, m))

    def rx():
        return rng.integers(0, am + 1, n)

    def ri():
        return rng.integers(0, n, (k, m))

    def rv():
        return rng.integers(lo, hi + 1, (k, m))

    def rs():
        return rng.integers(0, sm + 1, m)

    def full(v, shape):
        return np.full(shape, v, np.int64)

    def add(name, w, x, idx, val, S):
        cases.append((name, *(np.asarray(a, np.int64) for a in (w, x, idx, val, S))))

    add("empty_slots", rw(), rx(), ri(), full(0, (k, m)), rs())
    add("empty_slots_dense_max_S_max", full(wm, (n, m)), full(am, n), ri(), full(0, (k, m)),
        full(sm, m))
    add("dup_rows", rw(), rx(), np.tile(rng.integers(0, n, m), (k, 1)), rv(), rs())
    add("dup_rows_val_max", full(0, (n, m)), full(am, n), np.tile(np.arange(m) % n, (k, 1)),
        full(hi, (k, m)), full(0, m))
    add("rows_first_last", rw(), rx(), np.where(np.arange(k)[:, None] % 2, n - 1, 0) +
        np.zeros((k, m), np.int64), rv(), rs())
    add("val_min_x_max", full(0, (n, m)), full(am, n), ri(), full(lo, (k, m)), full(0, m))
    add("val_max_x_max", full(0, (n, m)), full(am, n), ri(), full(hi, (k, m)), full(0, m))
    for s in (0, sm):
        add(f"S{s}_dense_max_side_max", full(wm, (n, m)), full(am, n), ri(), full(hi, (k, m)),
            full(s, m))
        add(f"S{s}_dense_max_side_min", full(wm, (n, m)), full(am, n), ri(), full(lo, (k, m)),
            full(s, m))
    add("neg_only_side", rw(), rx(), ri(), rng.integers(lo, 0, (k, m)), rs())
    add("neg_only_side_dense_zero", full(0, (n, m)), rx(), ri(), rng.integers(lo, 0, (k, m)), rs())
    add("x_zero", rw(), full(0, n), ri(), rv(), rs())
    add("x_max", rw(), full(am, n), ri(), rv(), rs())
    add("slot_on_nonzero_dense", full(wm, (n, m)), rx(), ri(), rv(), rs())
    add("S_ramp", rw(), rx(), ri(), rv(), np.arange(m) % (sm + 1))
    add("S_ramp_rev", rw(), rx(), ri(), rv(), (sm - np.arange(m)) % (sm + 1))
    for a in range(abits):
        add(f"x_bitplane{a}", rw(), full(1 << a, n), ri(), rv(), rs())
    # slot extremes mixed across slots (slot s: hi if s even else lo, and reversed), S max
    mix = np.where(np.arange(k)[:, None] % 2, lo, hi) + np.zeros((k, m), np.int64)
    add("slots_max_min_S_max", full(wm, (n, m)), full(am, n), ri(), mix, full(sm, m))
    add("slots_min_max_S_max", full(wm, (n, m)), full(am, n), ri(), lo + hi - mix,
        full(sm, m))
    add("dup_rows_val_min", full(0, (n, m)), full(am, n), np.tile(np.arange(m) % n, (k, 1)),
        full(lo, (k, m)), full(0, m))
    add("S_max_dense_zero_side_min", full(0, (n, m)), full(am, n), ri(), full(lo, (k, m)),
        full(sm, m))
    names = [c[0] for c in cases]
    return tuple(np.stack([c[i] for c in cases]) for i in range(1, 6)) + (names,)


def sat_pct(val, vb=VB):
    """% of slot values at the signed vb-bit limit (v >= 2^(vb-1)-1 or v <= -2^(vb-1))."""
    v = np.asarray(val)
    return 100.0 * float(((v >= (1 << (vb - 1)) - 1) | (v <= -(1 << (vb - 1)))).mean())


def sidecar_random_cases(count, seed=SEED, n=N_IN, m=N_OUT, wbits=WB, abits=AB, k=K, vb=VB,
                         sm=None):
    """Random codes, slots (about 30 % empty) and shifts, fixed seed."""
    rng = np.random.default_rng(seed)
    w = rng.integers(0, qmax(wbits) + 1, (count, n, m))
    x = rng.integers(0, qmax(abits) + 1, (count, n))
    idx = rng.integers(0, n, (count, k, m))
    val = rng.integers(-(1 << (vb - 1)), 1 << (vb - 1), (count, k, m))
    val[rng.random((count, k, m)) < 0.3] = 0
    S = rng.integers(0, vb if sm is None else sm + 1, (count, m))
    return w, x, idx, val, S


def enc_cases(enc, xq_all, count, seed=SEED, n=N_IN, m=N_OUT):
    """Random (tile, token) cases from an llm_layer-style encoding, incl. slots and per-column S."""
    Wq = enc["Wq"]
    w, x, tr, tc, tk = real_layer_cases(Wq, xq_all, count, seed, n, m)
    per = (Wq.shape[0] // n) // enc["G"]
    cols = [slice(c * m, (c + 1) * m) for c in tc]
    idx = np.stack([enc["idx"][r][:, cs] for r, cs in zip(tr, cols)])
    val = np.stack([enc["val"][r][:, cs] for r, cs in zip(tr, cols)])
    S = np.stack([enc["S"][r // per][cs] for r, cs in zip(tr, cols)])
    zw = np.stack([enc["zw"][r // per][cs] for r, cs in zip(tr, cols)])
    return w, x, idx, val, S, zw, tr, tc, tk


def check_merge_identity(w, x, idx, val, S, zw, zx, y):
    """Raw macro Y minus outside-macro correction == (signed dense << S) + signed sidecar."""
    n = w.shape[1]
    corr = ((zw * x.sum(axis=1)[:, None] + zx * w.sum(axis=1) - n * zx * zw) << S) + \
        zx * val.sum(axis=1)
    xc = x - zx
    dense = np.einsum("ci,cij->cj", xc, w - zw[:, None, :])
    side = (np.take_along_axis(xc[:, :, None], idx.transpose(0, 2, 1).reshape(len(x), -1, 1),
                               axis=1).reshape(len(x), w.shape[2], -1)
            * val.transpose(0, 2, 1)).sum(axis=2)
    assert np.array_equal(y.astype(np.int64) - corr, (dense << S) + side)


def final_encodings(extra=()):
    """Final SidecarCIM (mag top-k, alpha 1.0, weight clip) and W8A8 encodings of the spec layer.

    Calib: first 512 WikiText-2 train tokens; x codes from the first EVAL_TOKENS test tokens.
    extra: dense weight widths wb for WbA4+mig+wclip, encoded as alternatives.py does
    (encode_pick2, alpha picked on calib layer error); returned as {wb: (enc, x codes)}.
    """
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast

    from llm_layer import CALIB_TOKENS, EVAL_TOKENS, act_codes, capture, load_wikitext
    from llm_layer import golden_check
    from novelty_study import B, encode2, encode_pick2
    name, layer = SPEC["workload"]["model"], SPEC["workload"]["layer"]
    tok = GPT2TokenizerFast.from_pretrained(name)
    model = GPT2LMHeadModel.from_pretrained(name).eval()
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    ev = tok(load_wikitext("test", 40000))["input_ids"][:EVAL_TOKENS]
    Xc = capture(model, [layer], [torch.tensor(ca)])[layer]
    Xe = capture(model, [layer], [torch.tensor(ev[i:i + 1024]) for i in range(0, len(ev), 1024)])[layer]
    mod = model.get_submodule(layer)
    W = mod.weight.detach().double().numpy()
    b = mod.bias.detach().double().numpy()
    side = encode2(W, b, Xc, dict(B, k=K, wclip=True), 1.0)
    w8 = encode2(W, b, Xc, dict(B, wbits=WIDE, abits=WIDE, alpha=None), None)
    dense = {}
    for wb in extra:
        e = encode_pick2(W, b, Xc, dict(B, wbits=wb, wclip=True))
        assert golden_check(e, Xc, [0, CALIB_TOKENS - 1]) and golden_check(e, Xe, [0, 1023, -1])
        dense[wb] = (e, act_codes(e, Xe))
    if extra:
        return side, act_codes(side, Xe), w8, act_codes(w8, Xe), dense
    return side, act_codes(side, Xe), w8, act_codes(w8, Xe)


DENSE_EXTRA = ((7, 4), (4, 8))               # dense W7A4 and W4A8
DENSE_W4A4 = ((4, 4),)                       # W4A4+mig+wclip (energy of the 4-bit DCIM row;
                                             # real_layer.npz stays the naive W4A4 encoding)


def dense_extra_encodings(pairs):
    """WbAa+mig+wclip encodings of the spec layer (encode_pick2, as fulltest.py), with x codes.

    Calib: first 512 WikiText-2 train tokens; x codes from the first EVAL_TOKENS test tokens.
    """
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast

    from llm_layer import CALIB_TOKENS, EVAL_TOKENS, act_codes, capture, load_wikitext
    from llm_layer import golden_check
    from novelty_study import B, encode_pick2
    name, layer = SPEC["workload"]["model"], SPEC["workload"]["layer"]
    tok = GPT2TokenizerFast.from_pretrained(name)
    model = GPT2LMHeadModel.from_pretrained(name).eval()
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    ev = tok(load_wikitext("test", 40000))["input_ids"][:EVAL_TOKENS]
    Xc = capture(model, [layer], [torch.tensor(ca)])[layer]
    Xe = capture(model, [layer], [torch.tensor(ev[i:i + 1024])
                                  for i in range(0, len(ev), 1024)])[layer]
    mod = model.get_submodule(layer)
    W = mod.weight.detach().double().numpy()
    b = mod.bias.detach().double().numpy()
    out = {}
    for wb, ab in pairs:
        e = encode_pick2(W, b, Xc, dict(B, wbits=wb, abits=ab, wclip=True))
        assert golden_check(e, Xc, [0, CALIB_TOKENS - 1]) and golden_check(e, Xe, [0, 1023, -1])
        out[(wb, ab)] = (e, act_codes(e, Xe))
    return out


def write_dense_extra(pairs=DENSE_EXTRA):
    """w7a4_* / w4a8_* (or w4a4_*) {corners, random, real_layer}.npz for dcim_core (WBITS, ABITS)."""
    encs = dense_extra_encodings(pairs)
    for wb, ab in pairs:
        tag = f"w{wb}a{ab}"
        w, x, names = corner_cases(wbits=wb, abits=ab)
        y = expected(w, x, wb, ab)
        assert np.all(y[names.index("all_max")] == N_IN * qmax(wb) * qmax(ab))
        assert np.all(y[names.index(f"w_bitplane{wb - 1}")] == N_IN * qmax(ab) << (wb - 1))
        assert np.all(y[names.index(f"x_bitplane{ab - 1}")] == N_IN * qmax(wb) << (ab - 1))
        save_npz(OUT / f"{tag}_corners.npz", w, x, y, wb, ab, names=np.array(names))
        print(f"{tag}_corners.npz: {w.shape[0]} cases, max y {y.max()}")
        w, x = random_cases(N_RANDOM, wbits=wb, abits=ab)
        save_npz(OUT / f"{tag}_random.npz", w, x, expected(w, x, wb, ab), wb, ab)
        print(f"{tag}_random.npz: {w.shape[0]} cases (seed {SEED})")
        e, xqd = encs[(wb, ab)]
        assert e["G"] == 1 and e["Wq"].max() <= qmax(wb) and xqd.max() <= qmax(ab)
        w, x, tr, tc, tk = real_layer_cases(e["Wq"], xqd, N_REAL)
        y = expected(w, x, wb, ab)
        zx, zw = e["zx"], e["zw"][0]
        zc = zw[tc[:, None] * N_OUT + np.arange(N_OUT)]
        sgn = np.einsum("ci,cij->cj", x - zx, w - zc[:, None, :])
        corr = zc * x.sum(axis=1)[:, None] + zx * w.sum(axis=1) - N_IN * zx * zc
        assert np.array_equal(y.astype(np.int64) - corr, sgn)
        save_npz(OUT / f"{tag}_real_layer.npz", w, x, y, wb, ab, tile_row=tr.astype(np.int32),
                 tile_col=tc.astype(np.int32), token=tk.astype(np.int32),
                 zw=zw.astype(np.int32), zx=np.int32(zx))
        print(f"{tag}_real_layer.npz: {w.shape[0]} cases (W{wb}A{ab}+mig+wclip, alpha "
              f"{e['alpha']}; w 0..{w.max()}, x 0..{x.max()}, y max {y.max()})")


S3_BITS = 3                                  # rtl SBITS=3: S in 0..7


def write_s3():
    """sidecar_s3_{corners,random,real_layer}.npz: sidecar sets for a 3-bit S (0..7).

    Corners/random: same generators with S max 7 (seeds as the sidecar_* files). Real layer:
    the sidecar_real_layer.npz cases (final encoding, S already within 0..7), y re-checked with
    golden.sidecarcim_dot(sbits=3). No model needed.
    """
    sm = (1 << S3_BITS) - 1
    w, x, idx, val, S, names = sidecar_corner_cases(sm=sm)
    y = side_expected(w, x, idx, val, S, sbits=S3_BITS)
    lo, hi = -(1 << (VB - 1)), (1 << (VB - 1)) - 1
    dmax, sx = N_IN * qmax(WB) * qmax(AB), K * qmax(AB)
    assert S.max() == sm and S.min() == 0
    assert np.all(y[names.index(f"S{sm}_dense_max_side_max")] == (dmax << sm) + hi * sx)
    assert np.all(y[names.index(f"S{sm}_dense_max_side_min")] == (dmax << sm) + lo * sx)
    assert y.max() == (dmax << sm) + hi * sx
    save_side(OUT / "sidecar_s3_corners.npz", w, x, idx, val, S, y, names=np.array(names))
    print(f"sidecar_s3_corners.npz: {w.shape[0]} cases, S 0..{sm}, max y {y.max()}")
    w, x, idx, val, S = sidecar_random_cases(N_RANDOM, sm=sm)
    assert S.max() == sm
    save_side(OUT / "sidecar_s3_random.npz", w, x, idx, val, S,
              side_expected(w, x, idx, val, S, sbits=S3_BITS))
    print(f"sidecar_s3_random.npz: {w.shape[0]} cases (seed {SEED}), S 0..{S.max()}")
    with np.load(OUT / "sidecar_real_layer.npz") as d:
        arr = {f: d[f] for f in d.files}
    assert arr["S"].max() <= sm
    y = side_expected(*(arr[f].astype(np.int64) for f in ("w", "x", "idx", "val", "S")),
                      sbits=S3_BITS)
    assert np.array_equal(y, arr["y"])
    save_if_changed(OUT / "sidecar_s3_real_layer.npz", **arr)
    print(f"sidecar_s3_real_layer.npz: {len(y)} cases = sidecar_real_layer.npz "
          f"(S {arr['S'].min()}..{arr['S'].max()}), y re-checked with sbits={S3_BITS}")


# ---------------- self-tests ----------------

def _test_sidecar_vectors():
    w, x, idx, val, S, names = sidecar_corner_cases()
    assert len(names) == len(set(names)) == w.shape[0]
    y = side_expected(w, x, idx, val, S)
    lo, hi = -(1 << (VB - 1)), (1 << (VB - 1)) - 1
    dmax = N_IN * qmax(WB) * qmax(AB)
    sx = K * qmax(AB)
    assert np.all(y[names.index("val_min_x_max")] == lo * sx)
    assert np.all(y[names.index(f"S{VB - 1}_dense_max_side_max")] == (dmax << (VB - 1)) + hi * sx)
    assert np.all(y[names.index(f"S{VB - 1}_dense_max_side_min")] == (dmax << (VB - 1)) + lo * sx)
    assert np.all(y[names.index("x_zero")] == 0)
    assert np.all(y[names.index("neg_only_side_dense_zero")] <= 0)
    mix = sum(hi if s % 2 == 0 else lo for s in range(K)) * qmax(AB)
    assert np.all(y[names.index("slots_max_min_S_max")] == (dmax << (VB - 1)) + mix)
    assert np.all(y[names.index("slots_min_max_S_max")] ==
                  (dmax << (VB - 1)) + (lo + hi) * sx - mix)
    assert np.all(y[names.index("dup_rows_val_min")] == lo * sx)
    assert np.all(y[names.index("S_max_dense_zero_side_min")] == lo * sx)
    # every slot sees both VB-bit extremes; S spans 0..VB-1; max Y = dense max << S max + side max
    for s in range(K):
        assert val[:, s].min() == lo and val[:, s].max() == hi
    assert S.max() == VB - 1 and S.min() == 0
    assert y.max() == (dmax << (VB - 1)) + hi * sx
    r1 = sidecar_random_cases(30)
    r2 = sidecar_random_cases(30)
    assert all(np.array_equal(a, b) for a, b in zip(r1, r2))
    ref = (np.einsum("ci,cij->cj", r1[1], r1[0]) << r1[4]) + \
        (np.take_along_axis(np.repeat(r1[1][:, :, None], N_OUT, axis=2), r1[2], axis=1) * r1[3]).sum(1)
    assert np.array_equal(side_expected(*r1), ref)
    # synthetic encoding: tiles, slots, S and the merge identity
    from novelty_study import B, encode2
    rng = np.random.default_rng(5)
    W = rng.normal(0, 0.1, (N_IN * 3, N_OUT * 4))
    W[4, 3] = 3.0
    X = rng.normal(0, 1, (20, N_IN * 3))
    enc = encode2(W, np.zeros(W.shape[1]), X, dict(B, k=K, wclip=True), 1.0)
    from llm_layer import act_codes
    xq = act_codes(enc, X)
    w, x, idx, val, S, zw, tr, tc, tk = enc_cases(enc, xq, 50)
    check_merge_identity(w, x, idx, val, S, zw, enc["zx"], side_expected(w, x, idx, val, S))
    print(f"  sidecar vectors ok ({len(names)} corners, random deterministic, merge identity)")


def _test_corners():
    w, x, names = corner_cases()
    assert w.shape[1:] == (N_IN, N_OUT) and x.shape[1:] == (N_IN,)
    assert len(names) == len(set(names)) == w.shape[0]
    assert w.min() >= 0 and w.max() == qmax(WB) and x.max() == qmax(AB)
    y = expected(w, x)
    assert y[names.index("zeros")].max() == 0
    assert np.all(y[names.index("all_max")] == N_IN * qmax(WB) * qmax(AB))
    print(f"  corner_cases ok ({len(names)} cases)")


def _test_random():
    w1, x1 = random_cases(50)
    w2, x2 = random_cases(50)
    assert np.array_equal(w1, w2) and np.array_equal(x1, x2)
    assert np.array_equal(expected(w1, x1), np.einsum("cij,ci->cj", w1, x1))
    print("  random_cases deterministic, expected == x @ w")


def _test_save_roundtrip(tmp):
    w, x = random_cases(5)
    y = expected(w, x)
    save_npz(tmp, w, x, y)
    d = np.load(tmp)
    assert np.array_equal(d["w"], w) and np.array_equal(d["x"], x) and np.array_equal(d["y"], y)
    assert d["w"].dtype.kind == "u" and d["y"].dtype == np.int32
    Path(tmp).unlink()
    print("  save_npz round trip ok")


def _test_real_layer_synthetic():
    rng = np.random.default_rng(3)
    W = rng.normal(0, 1, (N_IN * 3, N_OUT * 5))
    A = rng.normal(0, 1, (7, N_IN * 3))
    Wq, sw, zw = quantize(W, WB, axis=0)
    xq, sx, zx = quantize(A, AB)
    w, x, tr, tc, tk = real_layer_cases(Wq, xq, 20)
    for i in range(20):
        assert np.array_equal(w[i], tile(Wq, tr[i], tc[i]))
        assert np.array_equal(x[i], xq[tk[i], tr[i] * N_IN:(tr[i] + 1) * N_IN])
    y = layer_int_dot(xq[0], Wq, zx, zw, WB, AB)
    assert np.array_equal(y, (xq[0] - zx) @ (Wq - zw))
    assert np.allclose(sx * sw * y, dequantize(xq[0], sx, zx) @ dequantize(Wq, sw, zw))
    print("  real_layer_cases / tile / layer_int_dot ok (synthetic)")


def _test_stats_synthetic():
    rng = np.random.default_rng(4)
    W = rng.normal(0, 1, (N_IN * 2, N_OUT * 2))
    W[0, 0] = 100.0
    s = outlier_stats(W, np.zeros(W.shape[1]), rng.normal(0, 1, (5, W.shape[0])))
    assert s["global"]["per_tile_column_n_inputs"]["max"] >= 1
    e = s["preview_rel_l2_layer_output_error"]
    wide = 2 * max(WB, AB)
    assert 0 < e[f"W{wide}A{wide}"] < e[f"W{WB}A{AB}"]
    print("  outlier_stats ok (synthetic)")


def _selftest():
    _test_corners()
    _test_random()
    _test_save_roundtrip(OUT / "_tmp_selftest.npz")
    _test_real_layer_synthetic()
    _test_stats_synthetic()
    _test_sidecar_vectors()
    w, x, names = corner_cases(wbits=WIDE, abits=WIDE)
    assert np.all(expected(w, x, WIDE, WIDE)[names.index("all_max")] == N_IN * qmax(WIDE) ** 2)
    print(f"  dense{WIDE} corners ok ({len(names)} cases)")
    for wb in DENSE_A4:
        w, x, names = corner_cases(wbits=wb, abits=AB)
        y = expected(w, x, wb, AB)
        assert w.max() == qmax(wb) and x.max() == qmax(AB)
        assert np.all(y[names.index("all_max")] == N_IN * qmax(wb) * qmax(AB))
        assert np.all(y[names.index(f"w_bitplane{wb - 1}")] == N_IN * qmax(AB) << (wb - 1))
        r1, r2 = random_cases(20, wbits=wb), random_cases(20, wbits=wb)
        assert all(np.array_equal(a, b) for a, b in zip(r1, r2)) and r1[0].max() <= qmax(wb)
        assert np.array_equal(expected(*r1, wb, AB), np.einsum("cij,ci->cj", r1[0], r1[1]))
        print(f"  w{wb}a{AB} corners ok ({len(names)} cases), random deterministic")
    print("vectors self-test passed")


# ---------------- main ----------------

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _selftest()

    w, x, names = corner_cases()
    save_npz(OUT / "corners.npz", w, x, expected(w, x), names=np.array(names))
    print(f"corners.npz: {w.shape[0]} cases")

    w, x = random_cases(N_RANDOM)
    save_npz(OUT / "random.npz", w, x, expected(w, x))
    print(f"random.npz: {w.shape[0]} cases (seed {SEED})")

    W, b, acts = load_layer()
    print(f"loaded {SPEC['workload']['layer']}: W {W.shape}, acts {acts.shape} (tokens, in)")
    Wq, sw, zw = quantize(W, WB, axis=0)                 # per output channel
    xq, sx, zx = quantize(acts, AB)                      # per tensor
    # check: tile-by-tile integer path == dequantized float path (token 0 and last)
    for t in (0, acts.shape[0] - 1):
        yi = layer_int_dot(xq[t], Wq, zx, zw, WB, AB)
        assert np.allclose(sx * sw * yi, dequantize(xq[t], sx, zx) @ dequantize(Wq, sw, zw))
    print("full-layer integer path (DCIM tiles + zero-point correction) matches dequant matmul")
    w, x, tr, tc, tk = real_layer_cases(Wq, xq, N_REAL)
    save_npz(OUT / "real_layer.npz", w, x, expected(w, x), tile_row=tr.astype(np.int32),
             tile_col=tc.astype(np.int32), token=tk.astype(np.int32),
             zw=zw.astype(np.int32), zx=np.int32(zx))
    print(f"real_layer.npz: {w.shape[0]} cases from {(W.shape[0] // N_IN) * (W.shape[1] // N_OUT)}"
          f" tiles x {acts.shape[0]} tokens (seed {SEED})")

    s = outlier_stats(W, b, acts)
    (OUT / "outlier_stats.json").write_text(json.dumps(s, indent=2))
    print("outlier stats preview:")
    print(json.dumps(s, indent=2))

    # SidecarCIM macro vectors (raw Y = (dcim_dot << S) + sidecar_dot)
    w, x, idx, val, S, names = sidecar_corner_cases()
    save_side(OUT / "sidecar_corners.npz", w, x, idx, val, S, side_expected(w, x, idx, val, S),
              names=np.array(names))
    print(f"sidecar_corners.npz: {w.shape[0]} cases")
    w, x, idx, val, S = sidecar_random_cases(N_RANDOM)
    save_side(OUT / "sidecar_random.npz", w, x, idx, val, S, side_expected(w, x, idx, val, S))
    print(f"sidecar_random.npz: {w.shape[0]} cases (seed {SEED})")
    enc, xq, enc8, xq8, dense_a4 = final_encodings(DENSE_A4)
    w, x, idx, val, S, zw, tr, tc, tk = enc_cases(enc, xq, N_REAL)
    y = side_expected(w, x, idx, val, S)
    check_merge_identity(w, x, idx, val, S, zw, enc["zx"], y)
    save_side(OUT / "sidecar_real_layer.npz", w, x, idx, val, S, y, tile_row=tr.astype(np.int32),
              tile_col=tc.astype(np.int32), token=tk.astype(np.int32), zw=zw.astype(np.int32),
              zx=np.int32(enc["zx"]))
    assert enc["cfg"].get("vb", VB) == VB and val.min() >= -(1 << (VB - 1)) and \
        val.max() < (1 << (VB - 1))
    print(f"sidecar_real_layer.npz: {w.shape[0]} cases (final SidecarCIM encoding, VB={VB}: "
          f"top-{K} |w|, alpha 1.0, weight clip; S range {S.min()}..{S.max()}; "
          f"{100.0 * (val != 0).mean():.1f} % slots used; merge identity checked)")
    print(f"  slot saturation (|val| at the {VB}-bit limit, as alternatives.slot_stats): "
          f"vectors {sat_pct(val, VB):.4f} % of all slots, "
          f"{sat_pct(val[val != 0], VB):.4f} % of used slots; "
          f"whole h.0 encoding {sat_pct(enc['val'], VB):.4f} % of all slots")
    write_s3()                                   # 3-bit S sets (rtl SBITS=3)
    write_dense_extra(DENSE_EXTRA + DENSE_W4A4)  # w7a4_* / w4a8_* / w4a4_*

    # uniform wide (8-bit) DCIM vectors
    w, x, names = corner_cases(wbits=WIDE, abits=WIDE)
    save_npz(OUT / f"dense{WIDE}_corners.npz", w, x, expected(w, x, WIDE, WIDE),
             names=np.array(names))
    print(f"dense{WIDE}_corners.npz: {w.shape[0]} cases")
    w, x = random_cases(N_RANDOM, wbits=WIDE, abits=WIDE)
    save_npz(OUT / f"dense{WIDE}_random.npz", w, x, expected(w, x, WIDE, WIDE))
    print(f"dense{WIDE}_random.npz: {w.shape[0]} cases (seed {SEED})")
    w, x, tr, tc, tk = real_layer_cases(enc8["Wq"], xq8, N_REAL)
    save_npz(OUT / f"dense{WIDE}_real_layer.npz", w, x, expected(w, x, WIDE, WIDE),
             tile_row=tr.astype(np.int32), tile_col=tc.astype(np.int32),
             token=tk.astype(np.int32), zw=enc8["zw"][0].astype(np.int32),
             zx=np.int32(enc8["zx"]))
    print(f"dense{WIDE}_real_layer.npz: {w.shape[0]} cases (W{WIDE}A{WIDE} encoding)")

    # dense WbA4 baselines at the same throughput (dcim_core WBITS=wb, ABITS=4): W8A4 / W6A4 +mig+wclip
    alt = ROOT / "python" / "out" / "alternatives.json"
    alt = json.loads(alt.read_text())["units"] if alt.exists() else {}
    for wb in DENSE_A4:
        tag = f"w{wb}a{AB}"
        w, x, names = corner_cases(wbits=wb, abits=AB)
        save_npz(OUT / f"{tag}_corners.npz", w, x, expected(w, x, wb, AB), wb, AB,
                 names=np.array(names))
        print(f"{tag}_corners.npz: {w.shape[0]} cases")
        w, x = random_cases(N_RANDOM, wbits=wb, abits=AB)
        save_npz(OUT / f"{tag}_random.npz", w, x, expected(w, x, wb, AB), wb, AB)
        print(f"{tag}_random.npz: {w.shape[0]} cases (seed {SEED})")
        e, xqd = dense_a4[wb]
        assert e["G"] == 1 and e["Wq"].max() <= qmax(wb) and xqd.max() <= qmax(AB)
        a_ref = alt.get(f"gpt2|W{wb}A{AB}+mig+wclip", {}).get("alphas", [None])[0]
        assert a_ref is None or a_ref == e["alpha"], (a_ref, e["alpha"])
        w, x, tr, tc, tk = real_layer_cases(e["Wq"], xqd, N_REAL)
        y = expected(w, x, wb, AB)
        zx, zw = e["zx"], e["zw"][0]
        # signed tile dot = raw y minus zero-point terms (done outside the macro)
        zc = zw[tc[:, None] * N_OUT + np.arange(N_OUT)]             # (cases, n_out)
        sgn = np.einsum("ci,cij->cj", x - zx, w - zc[:, None, :])
        corr = zc * x.sum(axis=1)[:, None] + zx * w.sum(axis=1) - N_IN * zx * zc
        assert np.array_equal(y.astype(np.int64) - corr, sgn)
        save_npz(OUT / f"{tag}_real_layer.npz", w, x, y, wb, AB, tile_row=tr.astype(np.int32),
                 tile_col=tc.astype(np.int32), token=tk.astype(np.int32),
                 zw=zw.astype(np.int32), zx=np.int32(zx))
        print(f"{tag}_real_layer.npz: {w.shape[0]} cases (W{wb}A{AB}+mig+wclip encoding, alpha "
              f"{e['alpha']} (alternatives.json: {a_ref}); w codes 0..{w.max()}, x 0..{x.max()})")

    total = 0
    for f in ("corners.npz", "random.npz", "real_layer.npz", "sidecar_corners.npz",
              "sidecar_random.npz", "sidecar_real_layer.npz", f"dense{WIDE}_corners.npz",
              f"dense{WIDE}_random.npz", f"dense{WIDE}_real_layer.npz") + tuple(
              f"w{wb}a{AB}_{p}.npz" for wb in DENSE_A4
              for p in ("corners", "random", "real_layer")) + tuple(
              f"sidecar_s3_{p}.npz" for p in ("corners", "random", "real_layer")) + tuple(
              f"w{wb}a{ab}_{p}.npz" for wb, ab in DENSE_EXTRA + DENSE_W4A4
              for p in ("corners", "random", "real_layer")):
        sz = (OUT / f).stat().st_size
        total += sz
        print(f"  {f}: {sz / 1e6:.3f} MB")
    print(f"total npz size: {total / 1e6:.3f} MB")


if __name__ == "__main__":
    if sys.argv[1:] == ["s3"]:                  # only the 3-bit S sets (no model load)
        _test_sidecar_vectors()
        sys.exit(write_s3())
    if sys.argv[1:] == ["dense_extra"]:         # only the w7a4_* / w4a8_* sets
        sys.exit(write_dense_extra())
    if sys.argv[1:] == ["w4a4"]:                # only the w4a4_* (W4A4+mig+wclip) sets
        sys.exit(write_dense_extra(DENSE_W4A4))
    sys.exit(main())
