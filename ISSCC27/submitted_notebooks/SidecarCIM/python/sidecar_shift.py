"""Study G: a sidecar-side shift T to rescue down_proj (Y = (D << S) + (C << T)).

Usage: python sidecar_shift.py gpt2|qwen down [N]   only mlp_down quantized (6 schemes)
       python sidecar_shift.py gpt2|qwen all [N]    all linear layers but the LM head (T3 only;
                                                    the other schemes come from wholemodel.json)
       python sidecar_shift.py report
Variant: per column, S = floor(log2(vmax * sw / max|slot|)) as now; where that is < 0 (the
largest slot exceeds vmax dense steps, the case that saturates today), S = 0 and the sidecar
sum is shifted left by T = min(-S_ideal, 2^tbits - 1) instead (tbits = 3: T 0..7), so the
12-bit mantissas sit on a grid sw * 2^T. Columns with S_ideal >= 0 are unchanged (T = 0), so
the variant equals SidecarCIM wherever SidecarCIM does not saturate. Hardware: a second
barrel shifter (0..7) on the sidecar sum (17 b -> 24 b); merged width golden.merged_width(...,
tbits=3). Golden: golden.sidecar_dot(..., T) tile by tile (edge_variants.golden_check_tshift)
on 3 calib tokens of every quantized matrix.
Protocol = wholemodel.py / fulltest.py (layer types, encoders, mig + wclip, alpha per layer,
calib = first 512 WikiText-2 train tokens, 1024-token test windows; N evenly spaced windows
if given, the same window set as wholemodel.json for the same N). FP32 NLL from fulltest.json.
"""
import json
import os
import sys
import time

import numpy as np

from fulltest import CHUNK, compare
from fulltest import FILE as FT_FILE
from fulltest_extra import wait_no_docker
from golden import SPEC
from llm_layer import CALIB_TOKENS, OUT, int_forward, rel_l2
from novelty_study import paired, ppl
import wholemodel as wm

FILE = OUT / "sidecar_shift.json"
K = SPEC["outlier"]["budget_per_output"]
REF = wm.REF
T3 = "SidecarCIM+T3 k2,VB12"
T3K4 = "SidecarCIM+T3 k4,VB12"
CFG = dict(wm.SCHEMES)
CFG[T3] = dict(CFG[REF], tbits=3)
CFG[T3K4] = dict(CFG[REF], k=4, tbits=3)
DOWN = [REF, T3, T3K4, "W6A4+mig+wclip", "W8A4+mig+wclip", "W8A8"]
ALL = [T3]


def load():
    return json.loads(FILE.read_text()) if FILE.exists() else {"units": {}}


def save(res):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1))
    os.replace(tmp, FILE)


def slim32(e):
    """Golden-only codes dropped; Wc int16, V int32 (C << T exceeds int16)."""
    e.pop("Wq", None)
    assert np.abs(e["Wc"]).max() < 2 ** 15 and np.abs(e["V"]).max() < 2 ** 31
    e["Wc"] = np.asarray(e["Wc"]).astype(np.int16)
    e["V"] = np.asarray(e["V"]).astype(np.int32)
    return e


def encode(m, model, g, Xc, name):
    import edge_variants as ev
    cfg = CFG[name]
    if not cfg.get("tbits"):
        return wm.encode_group(m, model, g, Xc, cfg)
    W, b = wm.weights(model, g[2])
    X = Xc[g[2][0]]
    e = (ev.pick_gpt2 if m == "gpt2" else ev.pick_qwen)(W, b, X, cfg)
    ev.check(e, X, [0, 255, CALIB_TOKENS - 1])
    return e, W, b


def stage(m, mode, n_win=None):
    import qwen_eval as q
    t0 = time.time()
    model, wins, grp, Xc, Xe = wm.setup(m)
    nw = len(wins)
    n_win = nw if n_win is None else min(n_win, nw)
    idx = sorted({int(round(v)) for v in np.linspace(0, nw - 1, n_win)})
    types = ("mlp_down",) if mode == "down" else wm.TYPES
    res = load()
    res.setdefault("meta", {})[f"{m}|{mode}"] = {"windows": len(idx), "windows_total": nw,
                                                 "win_idx_first_last": [idx[0], idx[-1]]}
    U = res["units"]
    for name in (DOWN if mode == "down" else ALL):
        key = f"{m}|{mode}|{name}"
        u = U.get(key)
        if u and len(u["nll"]) == len(idx):
            continue
        wait_no_docker()
        t1 = time.time()
        encs, st = {}, {t: {"err": [], "T_hist": {}, "sat": 0, "slots": 0} for t in types}
        for g in grp:
            if g[0] not in types:
                continue
            e, W, b = encode(m, model, g, Xc, name)
            X = Xe[g[2][0]]
            s = st[g[0]]
            s["err"].append(round(rel_l2(int_forward(e, X), X @ W + b), 5))
            ss = e.get("slot_stats") or {}
            for a, c in ss.get("T_hist", {}).items():
                s["T_hist"][int(a)] = s["T_hist"].get(int(a), 0) + c
            s["sat"] += ss.get("sat_slots", 0)
            s["slots"] += ss.get("slots", 0)
            encs[f"{g[0]}.{g[1]}"] = slim32(e)
            del W
            q.trim()
        for t, s in st.items():
            s["err_mean"] = round(float(np.mean(s["err"])), 5)
            s["err_max"] = round(float(np.max(s["err"])), 5)
        res.setdefault("layer_stats", {})[key] = st
        save(res)
        print(f"  {key}: encoded in {time.time() - t1:.0f} s; " +
              "; ".join(f"{t} err {s['err_mean']}/{s['err_max']} T {s['T_hist']} sat {s['sat']}"
                        for t, s in st.items()), flush=True)
        u = U.setdefault(key, {"nll": [], "win_idx": []})
        done = len(u["nll"])
        assert u["win_idx"] == idx[:done]
        for s0 in range(done, len(idx), CHUNK):
            wait_no_docker()
            pt = idx[s0:s0 + CHUNK]
            u["nll"] += wm.window_nll(model, [wins[i] for i in pt], encs, grp).tolist()
            u["win_idx"] += pt
            save(res)
            print(f"    {key}: {len(u['nll'])}/{len(idx)} ({time.time() - t0:.0f} s)",
                  flush=True)
        u["sec"] = round(time.time() - t1, 1)
        save(res)
        del encs
        q.trim()
    report()


def report():
    res = load()
    U = dict(res["units"])
    W = json.loads(wm.FILE.read_text())["units"] if wm.FILE.exists() else {}
    FT = json.loads(FT_FILE.read_text())["units"]
    res["method"] = __doc__.strip()
    res["tables"] = {}
    for m in ("gpt2", "qwen"):
        for mode in ("down", "all"):
            src = {}
            for name in DOWN + ["W4A4+mig+wclip"]:
                k1 = f"{m}|{mode}|{name}"
                if k1 in U:
                    src[name] = (U[k1], "sidecar_shift.json")
                elif mode == "all" and f"{m}|all|{name}" in W:
                    src[name] = (W[f"{m}|all|{name}"], "wholemodel.json")
            if REF not in src:
                continue
            ref = src[REF][0]
            n = len(ref["nll"])
            idx = ref["win_idx"]
            fpn = np.array(FT[f"{m}|FP32"]["nll"])[idx]
            rows = [{"scheme": "FP32", "ppl": round(ppl(fpn), 4)}]
            for name, (u, f) in src.items():
                if len(u["nll"]) < n or u["win_idx"][:n] != idx:
                    continue
                a = np.array(u["nll"][:n])
                d, se = paired(a, fpn)
                row = {"scheme": name, "ppl": round(ppl(a), 4), "d_vs_fp32": d,
                       "se_vs_fp32": se, "source": f,
                       "layer_stats": res.get("layer_stats", {}).get(f"{m}|{mode}|{name}")}
                if name != REF:
                    row["vs_sidecar"] = compare(a, ref["nll"][:n])
                if name != T3 and T3 in src and len(src[T3][0]["nll"]) >= n:
                    row["vs_T3"] = compare(a, src[T3][0]["nll"][:n])
                rows.append(row)
            res["tables"][f"{m}|{mode}"] = {"windows": n, "rows": rows}
            print(f"\n{m} {mode}: {n} windows; FP32 {ppl(fpn):.3f}")
            for r in rows:
                v, t = r.get("vs_sidecar"), r.get("vs_T3")
                d = f"{r['d_vs_fp32']:+10.3f}" if "d_vs_fp32" in r else ""
                s = f" vs SidecarCIM {v['dppl']:+.3f} p {v['p_two_sided']:.2g}" if v else ""
                s += f" | vs T3 {t['dppl']:+.3f} p {t['p_two_sided']:.2g}" if t else ""
                print(f"  {r['scheme']:24s} {r['ppl']:11.3f} {d}{s}")
    save(res)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "report":
        report()
    else:
        stage(a[0], a[1], int(a[2]) if len(a) > 2 else None)
