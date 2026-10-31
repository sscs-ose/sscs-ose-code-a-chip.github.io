"""Bit-plane statistics of real activation codes for the bit-skipping (early termination) study.

Codes = 4-bit activation codes of GPT-2 c_fc inputs on the first spec eval_tokens WikiText-2 test
tokens (scale/zero point from the 512-token calib split, as llm_layer.encode). Two encodings:
  final   = SidecarCIM: migration alpha 1.0 (X / s, s from smooth_scales), per-tensor 4-bit codes
  nomig   = plain W4A4: no migration (s = 1)
Per 32-row input tile (one token, 32 consecutive input channels) and per code format:
  raw  : unsigned code x, P = 4 planes
  sm   : sign-magnitude of v = x - zp, magnitude planes P = bit_length(max |v|) (sign rides
         with each row, not a skippable plane); at zp 8, x=0 gives |v|=8 and forces P = 4
  sm3  : as sm but |v| clamped to 3 bits (P = 3; costs one code level at the extreme)
  tc   : two's complement of v = x - zp in P bits (smallest P holding [-zp, 15-zp]);
         "strict" skips planes that are all zero across the 32 rows;
  tcse : same code, but skips top planes that are pure sign extension for every row
         (value fits in P-j bits); exact if the lowest kept top plane becomes the sign plane.
Skipping = bit-serial MSB first, drop leading planes that are zero for all 32 rows (exact).
Reported: skip_j = fraction of tiles whose top j planes are all skippable; ones = mean 1-bits per
code (sm: magnitude only; sm_sign adds the sign bit); cycles = mean planes still processed per
dot product (floor 0 when the whole tile is skippable) vs P without skipping.
"""
import json
import time

import numpy as np

from golden import SPEC
from llm_layer import (CALIB_TOKENS, N_IN, OUT, WB, AB, capture, encode, fc_names,
                       load_wikitext, smooth_scales)
from quant import qmax, quant_params, quantize_with

EVAL_TOKENS = SPEC["workload"]["eval_tokens"]
NB = AB
FILE = OUT / "bitplane.json"
FMTS = ("raw", "sm", "sm3", "tc", "tcse")
BL = np.array([int(v).bit_length() for v in range(1 << 8)])      # bit_length lookup
PC = np.array([bin(v).count("1") for v in range(1 << 8)])        # popcount lookup


def formats(zp, nb=NB):
    """Plane count P per format for zero point zp."""
    vmax = max(zp, qmax(nb) - zp)
    ptc = 1
    while not (-(1 << (ptc - 1)) <= -zp and qmax(nb) - zp <= (1 << (ptc - 1)) - 1):
        ptc += 1
    return {"raw": nb, "sm": max(BL[vmax], 1), "sm3": nb - 1, "tc": ptc, "tcse": ptc}


def tcbits(v):
    """Bits of the shortest two's complement form (0 for v == 0)."""
    return np.where(v == 0, 0, np.where(v > 0, BL[np.abs(v)] + 1, BL[np.abs(v) - 1] + 1))


def tile_cycles(x, zp, nb=NB):
    """Planes still processed per tile for each format, x: (T, n_rt, 32) codes. -> dict of (T, n_rt)."""
    v = x - zp
    P = formats(zp, nb)
    mx = x.max(axis=2)
    ms = np.abs(v).max(axis=2)
    ms3 = np.minimum(np.abs(v), qmax(nb - 1)).max(axis=2)
    neg = (v < 0).any(axis=2)
    return {"raw": BL[mx],
            "sm": BL[ms],
            "sm3": BL[ms3],
            "tc": np.where(neg, P["tc"], BL[v.max(axis=2).clip(0)]),
            "tcse": tcbits(v).max(axis=2)}, P


def ones(x, zp, nb=NB):
    """Mean 1-bits per code (toggle proxy) per format; sm_sign includes the sign bit."""
    v = x - zp
    P = formats(zp, nb)
    return {"raw": float(PC[x].mean()), "sm": float(PC[np.abs(v)].mean()),
            "sm_sign": float((PC[np.abs(v)] + (v < 0)).mean()),
            "sm3": float(PC[np.minimum(np.abs(v), qmax(nb - 1))].mean()),
            "sm3_sign": float((PC[np.minimum(np.abs(v), qmax(nb - 1))] + (v < 0)).mean()),
            "tc": float(PC[v & ((1 << P["tc"]) - 1)].mean())}


def stats(codes, zp, nb=NB):
    """Skip fractions, mean cycles and 1-bit counts for (T, d_in) codes."""
    T, d = codes.shape
    x = codes.reshape(T, d // N_IN, N_IN).astype(np.int64)
    cyc, P = tile_cycles(x, zp, nb)
    out = {"zp": int(zp), "pct_x_eq_zp": round(100.0 * float((codes == zp).mean()), 2),
           "planes": {k: int(p) for k, p in P.items()}}
    out["sm3_clamped_pct"] = round(100.0 * float((np.abs(codes - zp) > qmax(nb - 1)).mean()), 3)
    for f in FMTS:
        c = cyc[f]
        out[f] = {"P": int(P[f]),
                  "skip": [round(float((c <= P[f] - j).mean()), 4) if j <= P[f] else None
                           for j in range(1, nb + 1)],
                  "cycles": round(float(c.mean()), 4),
                  "tiles_all_skipped": round(float((c == 0).mean()), 4)}
    out["ones"] = {k: round(v, 4) for k, v in ones(x, zp, nb).items()}
    return out


# ---------------- slow reference for the self-test ----------------

def ref_cycles(tile, zp, fmt, nb=NB):
    """Explicit bit-plane loop: planes left after dropping skippable leading ones."""
    v = [int(a) - zp for a in tile]
    P = formats(zp, nb)[fmt]
    if fmt == "raw":
        rows = [int(a) for a in tile]
    elif fmt in ("sm", "sm3"):
        rows = [abs(a) if fmt == "sm" else min(abs(a), qmax(nb - 1)) for a in v]
    else:
        rows = [a & ((1 << P) - 1) for a in v]
    if fmt == "tcse":                       # shortest signed width holding every row
        for w in range(P + 1):
            lo, hi = (0, 1) if w == 0 else (-(1 << (w - 1)), 1 << (w - 1))
            if all(lo <= a < hi for a in v):
                return w
        return P
    left = P
    for t in range(P - 1, -1, -1):          # plane t is the current top plane
        if not all(((r >> t) & 1) == 0 for r in rows):
            break
        left -= 1
    return left


def _selftest():
    rng = np.random.default_rng(5)
    for zp in (0, 3, 8, 12):
        base = np.clip(zp + rng.integers(-2, 3, size=(60, N_IN)) * rng.integers(0, 3, (60, 1)),
                       0, 15)
        base = np.concatenate([base, rng.integers(0, 16, (30, N_IN)), np.full((2, N_IN), zp)])
        cyc, P = tile_cycles(base[:, None, :].astype(np.int64), zp)
        for f in FMTS:
            for i in range(base.shape[0]):
                r = ref_cycles(base[i], zp, f)
                assert cyc[f][i, 0] == r, (zp, f, i, cyc[f][i, 0], r)
        s = stats(base, zp)
        assert all(s[f]["skip"][0] >= s[f]["skip"][1] for f in ("raw", "sm") if s[f]["skip"][1])
        assert s["raw"]["cycles"] <= 4 and s["pct_x_eq_zp"] >= 0
    # all-zero-point tile: sm/tc skip everything, raw does not unless zp == 0
    x = np.full((1, 1, N_IN), 8)
    c, _ = tile_cycles(x, 8)
    assert c["sm"][0, 0] == 0 and c["raw"][0, 0] == 4 and c["tcse"][0, 0] == 0
    assert c["tc"][0, 0] == 0
    print("bitplane self-test passed")


def codes_for(Xc, Xe, W, alpha):
    """4-bit codes and zero point of eval inputs (calib range after migration by alpha)."""
    s = np.ones(Xc.shape[1]) if alpha is None else smooth_scales(Xc, W, alpha)
    sx, zx = quant_params(Xc / s[None, :], NB)
    return quantize_with(Xe / s[None, :], sx, zx, NB), int(zx)


def pooled(per_layer):
    """Mean over layers (equal token counts) of the numeric stats."""
    keys = per_layer[0]
    out = {"layers": len(per_layer)}
    for f in FMTS:
        sk = []
        for j in range(NB):
            vals = [p[f]["skip"][j] for p in per_layer]
            sk.append(None if any(v is None for v in vals) else round(float(np.mean(vals)), 4))
        out[f] = {"P": [p[f]["P"] for p in per_layer], "skip": sk,
                  "cycles": round(float(np.mean([p[f]["cycles"] for p in per_layer])), 4),
                  "tiles_all_skipped": round(float(np.mean(
                      [p[f]["tiles_all_skipped"] for p in per_layer])), 4)}
    out["ones"] = {k: round(float(np.mean([p["ones"][k] for p in per_layer])), 4)
                   for k in keys["ones"]}
    out["pct_x_eq_zp"] = round(float(np.mean([p["pct_x_eq_zp"] for p in per_layer])), 2)
    out["sm3_clamped_pct"] = round(float(np.mean([p["sm3_clamped_pct"] for p in per_layer])), 3)
    out["zp"] = [p["zp"] for p in per_layer]
    return out


def main():
    import torch
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    torch.set_num_threads(6)
    _selftest()
    t0 = time.time()
    tok = GPT2TokenizerFast.from_pretrained(SPEC["workload"]["model"])
    model = GPT2LMHeadModel.from_pretrained(SPEC["workload"]["model"]).eval()
    ctx = model.config.n_positions
    ev = tok(load_wikitext("test", 40000))["input_ids"][:EVAL_TOKENS]
    ca = tok(load_wikitext("train", 20000))["input_ids"][:CALIB_TOKENS]
    ev = torch.tensor(ev)
    wins = [ev[i:i + ctx] for i in range(0, EVAL_TOKENS, ctx)]
    names = fc_names(model)
    h0 = SPEC["workload"]["layer"]
    Xc = capture(model, names, [torch.tensor(ca)])
    Xe = capture(model, names, wins)
    Ws = {n: model.get_submodule(n).weight.detach().double().numpy() for n in names}
    bs = {n: model.get_submodule(n).bias.detach().double().numpy() for n in names}
    # cross-check codes against the real encoding (final: top-2 sidecar, clip, alpha 1.0)
    cfg = dict(wbits=WB, abits=AB, alpha=1.0, k=SPEC["outlier"]["budget_per_output"],
               tile=False, clip=True)
    e = encode(Ws[h0], bs[h0], Xc[h0], cfg, 1.0)
    q, z = codes_for(Xc[h0], Xe[h0], Ws[h0], 1.0)
    from llm_layer import act_codes
    assert z == e["zx"] and np.array_equal(q, act_codes(e, Xe[h0]))
    del e
    res = {"eval": f"WikiText-2 test first {EVAL_TOKENS} tokens, {NB}-bit codes, 32-row tiles",
           "calib": f"WikiText-2 train first {CALIB_TOKENS} tokens",
           "formats": {"raw": "unsigned code", "sm": "sign-magnitude of x-zp (magnitude planes)",
                       "sm3": "sign-magnitude, magnitude clamped to 3 bits (x=0 -> -7 at zp 8)",
                       "tc": "two's complement x-zp, strict all-zero planes",
                       "tcse": "two's complement x-zp, sign-extension planes also skipped"},
           "enc": {}}
    for tag, alpha in (("final_alpha1.0", 1.0), ("nomig", None)):
        per = {}
        for n in names:
            codes, zp = codes_for(Xc[n], Xe[n], Ws[n], alpha)
            per[n] = stats(codes, zp)
        res["enc"][tag] = {"h0": per[h0], "all12": pooled(list(per.values())),
                           "per_layer": {n.split(".")[2]: per[n] for n in names}}
        print(f"  {tag} done ({time.time() - t0:.0f} s)", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(res, indent=2))
    show(res)
    print(f"saved {FILE} ({time.time() - t0:.0f} s)")


def show(res):
    """Print compact tables."""
    for tag, d in res["enc"].items():
        for scope, r in (("h.0", d["h0"]), ("all 12 layers (mean)", d["all12"])):
            print(f"\n{tag}  {scope}  zp={r['zp']}  %x==zp {r['pct_x_eq_zp']}  "
                  f"%|v|>7 {r['sm3_clamped_pct']}")
            print(f"{'format':6s} {'P':>3s} {'skip1':>7s} {'skip2':>7s} {'skip3':>7s} {'skip4':>7s}"
                  f" {'cycles':>7s} {'all_skip':>8s}")
            for f in FMTS:
                s = r[f]
                P = s["P"] if isinstance(s["P"], int) else sorted(set(s["P"]))
                sk = ["   -   " if v is None else f"{v:7.4f}" for v in s["skip"]]
                print(f"{f:6s} {str(P):>3s} {' '.join(sk)} {s['cycles']:7.3f} "
                      f"{s['tiles_all_skipped']:8.4f}")
            print("ones/code:", r["ones"])


if __name__ == "__main__":
    main()
