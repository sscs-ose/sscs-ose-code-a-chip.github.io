"""Cycle-accurate model of the packed-pair, layer-fused NTT engine.

Storage: one single-port SRAM of 128 words x 24 bit; word w holds the coefficient pair (a[2w], a[2w+1]).
ML-KEM's NTT stops at len = 2, so bit 0 of a coefficient index is never a butterfly distance: in every layer
the partner of a[2w+h] is a[2(w+L/2)+h], the same half of another word. A pass fuses several layers: it
loads a group of words into a register bank, runs its layers there and stores the group back.

Hardware modelled cycle by cycle:
  * port      one SRAM access per cycle; a word read in cycle t is in the bank from cycle t+1,
              a store in cycle t writes the bank contents of cycle t
  * butterfly one issue per cycle, two stages (multiply | Barrett + add/subtract); operands are read in
              the issue cycle t, results are in the bank from cycle t+2. The inverse transform's scaling
              by 128^-1 is folded into the last layer: the upper output uses a pre-scaled twiddle, the
              lower output costs one extra multiplier issue ("scale").
  * banks     two banks of 8 words (16 coefficients) used in ping-pong
Two-lane variant (rtl/kyber_ntt_engine_packed2.sv, simulate(..., two_lane=True)): the two halves of a word
are independent butterfly streams with the same twiddle, so two butterfly units issue both halves of one
word butterfly per cycle; the layers are fused in two passes (forward {128,64,32} {16,8,4,2}, inverse
{2,4,8,16} {32,64,128}), 512 port accesses per transform, banks of 16 words.
The scheduler is greedy with a fixed priority (stores before loads, groups in order, butterflies in their
canonical order). Every hazard is checked: one port access and one multiplier issue per cycle, operand
readiness, bank reuse, and SRAM read-after-write across groups and passes.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import random

import mlkem_ref as ref

Q, Z, F_INV = ref.Q, ref.ZETAS, 3303          # 3303 = 128^-1 mod q (FIPS 203, Algorithm 10)
FWD_PASSES = [[128, 64, 32], [16, 8], [4, 2]]
INV_PASSES = [[2, 4], [8, 16], [32, 64, 128]]
FWD_PASSES_2 = [[128, 64, 32], [16, 8, 4, 2]]
INV_PASSES_2 = [[2, 4, 8, 16], [32, 64, 128]]
BU_LATENCY = 2                                 # issue in t, result readable in t + 2
N_BANKS = 2


def group_plan(passes, inverse):
    """Every group of every pass: its words (slot order) and its operations (layer order)."""
    plan = []
    for p, layers in enumerate(passes):
        dists = [L // 2 for L in layers]
        mask = sum(dists)
        for b in [b for b in range(128) if b & mask == 0]:
            words = [b + sum(d for k, d in enumerate(dists) if s >> k & 1) for s in range(2 ** len(dists))]
            slot = {w: s for s, w in enumerate(words)}
            ops = []
            for L in layers:
                for w in words:
                    if w & (L // 2):
                        continue
                    for h in (0, 1):
                        ops.append(("bf", L, slot[w], slot[w + L // 2], h, w))
                if inverse and L == 128:
                    for w in words:
                        if not w & 64:
                            ops += [("scale", L, slot[w], None, h, w) for h in (0, 1)]
            last = {}
            for k, op in enumerate(ops):
                for s in (op[2], op[3]):
                    if s is not None:
                        last[s] = k
            plan.append({"pass": p, "words": words, "ops": ops, "last_writer": last})
    return plan


def zeta_index(L, w, inverse):
    """FIPS 203 zeta index of the butterfly whose lower operand sits in word w (a shift, as in the RTL)."""
    blk = w // L                                   # = floor((2w + h) / (2L)) for h in {0, 1}
    return (256 // L - 1 - blk) if inverse else (128 // L + blk)


def simulate(f, inverse=False, two_lane=False, latency=BU_LATENCY):
    if two_lane:
        plan = group_plan(INV_PASSES_2 if inverse else FWD_PASSES_2, inverse)
    else:
        plan = group_plan(INV_PASSES if inverse else FWD_PASSES, inverse)
    lanes = 2 if two_lane else 1
    mem = [[f[2 * w], f[2 * w + 1]] for w in range(128)]
    stored_pass = [-1] * 128                        # pass that last stored each word (-1: the input)
    last_store = [-1] * 128
    bank_free = [0] * N_BANKS
    st = []
    t = g_load = g_comp = done = 0
    n_r = n_w = n_mul = 0
    trace = []
    while done < len(plan):
        port = mul = None
        # port: the oldest store whose slot is final, otherwise the next load
        for gi in range(len(st)):
            G = st[gi]
            for s in G["store_order"]:
                if s not in G["stored"] and G["final"].get(s) is not None and G["final"][s] <= t:
                    port = ("W", gi, s); break
            if port:
                break
        if port is None and g_load < len(plan):
            gp = plan[g_load]
            if g_load == len(st):
                st.append({"bank": g_load % N_BANKS, "buf": {}, "ready": {}, "loaded": 0, "issued": 0,
                           "final": {}, "stored": set(), "store_order": []})
            G = st[g_load]
            w = gp["words"][G["loaded"]]
            if bank_free[G["bank"]] <= t and stored_pass[w] == gp["pass"] - 1 and last_store[w] < t:
                port = ("R", g_load, G["loaded"])
        # multiplier: the next operation of the oldest group still computing, if its operands are ready
        if g_comp < len(st):
            G, gp = st[g_comp], plan[g_comp]
            if G["issued"] < len(gp["ops"]):
                kind, L, sa, sb, h, w = gp["ops"][G["issued"]]
                need = [(sa, h)] + ([(sb, h)] if sb is not None else [])
                if all(G["ready"].get(x, 10 ** 9) <= t for x in need):
                    mul = g_comp
        # apply the cycle
        if port:
            kind, gi, s = port
            G, gp = st[gi], plan[gi]
            w = gp["words"][s]
            if kind == "R":
                G["buf"][(s, 0)], G["buf"][(s, 1)] = mem[w]
                G["ready"][(s, 0)] = G["ready"][(s, 1)] = t + 1
                G["loaded"] += 1; n_r += 1
                if G["loaded"] == len(gp["words"]):
                    g_load += 1
            else:
                mem[w] = [G["buf"][(s, 0)], G["buf"][(s, 1)]]
                stored_pass[w], last_store[w] = gp["pass"], t
                G["stored"].add(s); n_w += 1
                if len(G["stored"]) == len(gp["words"]):
                    bank_free[G["bank"]] = t + 1; done += 1
        for _lane in range(lanes if mul is not None else 0):
            G, gp = st[mul], plan[mul]
            k = G["issued"]
            kind, L, sa, sb, h, w = gp["ops"][k]
            if not all(G["ready"].get(x, 10 ** 9) <= t for x in [(sa, h)] + ([(sb, h)] if sb is not None else [])):
                break                                  # (never taken: both halves of a word move together)
            a = G["buf"][(sa, h)]
            if kind == "scale":
                G["buf"][(sa, h)] = a * F_INV % Q
                G["ready"][(sa, h)] = t + latency
            else:
                b = G["buf"][(sb, h)]
                z = Z[zeta_index(L, w, inverse)]
                if not inverse:
                    tt = z * b % Q
                    na, nb = (a + tt) % Q, (a - tt) % Q
                else:
                    if L == 128:
                        z = z * F_INV % Q                 # pre-scaled twiddle of the last inverse layer
                    na, nb = (a + b) % Q, z * (b - a) % Q
                G["buf"][(sa, h)], G["buf"][(sb, h)] = na, nb
                G["ready"][(sa, h)] = G["ready"][(sb, h)] = t + latency
            G["issued"] += 1; n_mul += 1
            for s, kk in gp["last_writer"].items():   # a slot is final once its last writer has completed
                if kk == k:
                    G["final"][s] = max(G["ready"][(s, 0)], G["ready"][(s, 1)])
                    G["store_order"].append(s)
            if G["issued"] == len(gp["ops"]):
                g_comp += 1
                break
        trace.append((port, mul))
        t += 1
        if t > 50000:
            raise RuntimeError("the schedule does not terminate")
    out = [c for w in mem for c in w]
    return out, {"cycles": t, "reads": n_r, "writes": n_w, "multiplier_issues": n_mul, "trace": trace}


def check(n=50, seed=2027, **kw):
    rng = random.Random(seed)
    for _ in range(n):
        a = [rng.randrange(Q) for _ in range(256)]
        fwd, sf = simulate(a, **kw)
        assert fwd == ref.ntt(a), "forward transform differs from the golden model"
        inv, si = simulate(fwd, inverse=True, **kw)
        assert inv == a, "inverse transform differs from the golden model"
    return sf, si


if __name__ == "__main__":
    for label, kw in (("one lane, three passes", {}), ("two lanes, two passes", {"two_lane": True})):
        sf, si = check(**kw)
        for name, s in (("forward", sf), ("inverse", si)):
            print(f"{label}, {name}: {s['cycles']} cycles, {s['reads']} reads + {s['writes']} writes, "
                  f"{s['multiplier_issues']} half-butterfly issues")
