#!/usr/bin/env python3
"""Gate-level stimulus straight from a vector .npz (first N cases), same file format as gl_stim.py.
Usage: gl_stim_npz.py <kind: dense|dense8|top> <npz> <N> <outprefix> [wbits abits]
Per case: load all 32 weight rows (+ the 8 sidecar columns in the same cycles for 'top'),
start, wait ABITS edges. Unused fields keep their last value (as the cocotb tests do).
Also prints mean x-input toggle rate (bit flips per bit per case) and x/w one-density."""
import sys
import numpy as np

kind, npz, N, pre = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
d = np.load(npz)
w, x, y = d["w"][:N], d["x"][:N], d["y"][:N]
import os
PIPE = os.environ.get("PIPE", "0") == "1"
NI, NO = w.shape[1], w.shape[2]      # N_IN (32 or 128 ...), N_OUT
import re as _re
_m = _re.fullmatch(r"w(\d+)a(\d+)", kind)
WB = int(_m.group(1)) if _m else (8 if kind == "dense8" else 4)
AB = int(_m.group(2)) if _m else (8 if kind == "dense8" else 4)
import re
VB = int(re.search(r"outlier:\s+weight_bits:\s*(\d+)", open(__import__("pathlib").Path(__file__).resolve().parents[1] / "spec/spec.yaml").read()).group(1))
K = d["idx"].shape[1] if "idx" in d.files else 2
AW = (NI - 1).bit_length()
SBITS = int(os.environ.get("SBITS", "4"))      # width of the per-column shift S (RTL parameter SBITS)
SMAX = min(VB - 1, 2 ** SBITS - 1)
SLW, SBW = AW + VB, SBITS
YW = (NI * (2 ** WB - 1) * (2 ** AB - 1)).bit_length()
YTW = max(YW + SMAX + 1, VB + (K * (2 ** AB - 1)).bit_length()) + 1 if kind == "top" else 0
fields = [("rst", 1), ("w_load_en", 1), ("w_load_addr", AW), ("w_load_row", NO * WB)] if kind == "top" else \
         [("rst", 1), ("load_en", 1), ("load_addr", AW), ("load_row", NO * WB)]
if kind == "top":
    fields += [("s_load_en", 1), ("s_load_col", max(1, (NO - 1).bit_length())), ("s_load_slots", K * SLW), ("s_load_shift", SBW)]
fields += [("start", 1), ("x_in", NI * AB)]
yw = NO * (YTW if kind == "top" else YW)
nm = {f: i for i, (f, _) in enumerate(fields)}
pfx = "w_" if kind == "top" else ""
st = {f: 0 for f, _ in fields}
edges, exp = [], []


def edge(**kw):
    st.update(kw)
    edges.append(dict(st))


def ystr(vals, wd):
    return "".join(format(int(v) & ((1 << wd) - 1), "0%db" % wd) for v in reversed(vals))


busy, valid, ycur = 0, 0, None


hold_y = None


def rec(b, v, yv):
    global hold_y
    if hold_y is not None and (b, v) == (0, 0):
        # PIPE_MERGE=1: a load at edge e+1 clears the registered valid one edge later (valid stays 1 for that edge)
        exp.append((hold_y, "0", "1"))
        hold_y = None
        return
    hold_y = yv if (PIPE and v == 1) else None
    exp.append((yv if yv else "x" * yw, str(b), str(v)))


edge(rst=1); rec(0, 0, None)
edge(rst=1); rec(0, 0, None)
edge(rst=0); rec(0, 0, None)
for c in range(N):
    rows = [sum(int(w[c, i, j]) << (j * WB) for j in range(NO)) for i in range(NI)]
    cols = None
    if kind == "top":
        cols = []
        for j in range(NO):
            v = 0
            for s in range(K):
                sl = (int(d["idx"][c, s, j]) & ((1 << AW) - 1)) | ((int(d["val"][c, s, j]) & ((1 << VB) - 1)) << AW)
                v |= sl << (s * SLW)
            cols.append((j, v, int(d["S"][c, j])))
    for t in range(NI):
        kw = {pfx + "load_en": 1, pfx + "load_addr": t, pfx + "load_row": rows[t]}
        if cols and t < NO:
            kw.update(s_load_en=1, s_load_col=cols[t][0], s_load_slots=cols[t][1], s_load_shift=cols[t][2])
        elif cols:
            kw.update(s_load_en=0)
        edge(**kw); rec(0, 0, None)
    xi = sum(int(x[c, i]) << (i * AB) for i in range(NI))
    kw = {pfx + "load_en": 0, "start": 1, "x_in": xi}
    if cols:
        kw["s_load_en"] = 0
    edge(**kw); rec(1, 0, None)
    LAT = AB + (1 if PIPE else 0)      # PIPE_MERGE=1: valid and y one edge later (busy unchanged)
    for n in range(1, LAT + 1):
        edge(start=0)
        if n < AB:
            rec(1, 0, None)
        elif n < LAT:
            rec(0, 0, None)
        else:
            rec(0, 1, ystr(y[c], YTW if kind == "top" else YW))
HEX = sum(wd for _, wd in fields)
with open(pre + ".hex", "w") as f:
    for e in edges:
        v = 0
        for n_, wd in fields:
            v = (v << wd) | (e[n_] & ((1 << wd) - 1))
        f.write("%x\n" % v)
with open(pre + ".exp", "w") as f:
    for a, b, c_ in exp:
        f.write("%s %s %s\n" % (a, b, c_))
open(pre + ".info", "w").write(" ".join("%s=%d" % (n_, wd) for n_, wd in fields) + " y=%d busy=1 valid=1 edges=%d\n" % (yw, len(edges)))
# activity stats from the vectors
xb = np.unpackbits(x.astype(np.uint8)[..., None], axis=-1)[..., -AB:].reshape(N, -1)
wb = np.unpackbits(w.astype(np.uint8)[..., None], axis=-1)[..., -WB:]
tog = np.mean(xb[1:] != xb[:-1])
print("x_toggle_per_bit_per_case=%.4f x_ones=%.4f w_ones=%.4f edges=%d" % (tog, xb.mean(), wb.mean(), len(edges)))
