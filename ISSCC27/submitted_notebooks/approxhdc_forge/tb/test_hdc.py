"""cocotb testbench: the generated RTL must match hdc_model.py bit for bit.

Configuration comes from the HDC_CFG environment variable (JSON of rtlgen.RTLConfig).
Checked on every sample: the P query bits of every slice (both passes), all C distances,
the prediction, whether a learning update happened, and (after learning) every counter.
"""
import json
import os
import pathlib
import sys

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import data  # noqa: E402
import hdc_model as H  # noqa: E402
from rtlgen import RTLConfig  # noqa: E402

CFG = RTLConfig(**json.loads(os.environ.get("HDC_CFG", "{}")))
N_RAND = int(os.environ.get("N_RAND", 200))
N_REAL = int(os.environ.get("N_REAL", 50))
N_STREAM = int(os.environ.get("N_STREAM", 150))
WS = CFG.w if CFG.learn else 1
LO, HI = -(1 << (WS - 1)), (1 << (WS - 1)) - 1
AW = int(np.log2(CFG.D)) + 1
IM = H.item_memory(CFG.F, CFG.Q, CFG.seed)
SIM = H.Similarity(CFG.variant, CFG.knob)


# ------------------------------------------------------------------ model side
def new_learner():
    mode = "error" if CFG.learn == 2 else "bundle"
    return H.OnlineLearner(CFG.C, CFG.D, max(CFG.w, 2), mode, IM.T, SIM, CFG.k, CFG.seed)


def set_state(L, arr):
    """Load counters (learn on) or prototype bits (learn off) into the model learner."""
    if CFG.learn:
        L.cnt[:] = arr
        for c in range(CFG.C):
            p = (L.cnt[c] > 0) | ((L.cnt[c] == 0) & L.T)
            L.proto[c] = p
            L.protop[c] = H.pack(p.astype(np.uint8))
    else:
        L.proto[:] = arr
        L.protop[:] = H.pack(arr.astype(np.uint8))


def model_state(L):
    return L.cnt.copy() if CFG.learn else L.proto.astype(np.int64)


def random_state(rng):
    if CFG.learn:
        v = rng.integers(LO, HI + 1, size=(CFG.C, CFG.D))
        special = rng.choice([LO, HI, 0, 1, -1], size=v.shape)
        return np.where(rng.random(v.shape) < 0.3, special, v).astype(np.int16)
    return rng.integers(0, 2, size=(CFG.C, CFG.D)).astype(np.uint8)


def encode(x):
    q = H.encode(np.asarray(x)[None], IM)[0][:CFG.D]
    return q, H.pack(q)


# ------------------------------------------------------------------- ring <-> words
def to_words(arr):
    words = []
    for s in range(CFG.S):
        v = 0
        for c in range(CFG.C):
            for i in range(CFG.P):
                v |= (int(arr[c, s * CFG.P + i]) & ((1 << WS) - 1)) << ((c * CFG.P + i) * WS)
        words.append(v)
    return words


def from_words(words):
    arr = np.zeros((CFG.C, CFG.D), dtype=np.int64)
    for s, v in enumerate(words):
        for c in range(CFG.C):
            for i in range(CFG.P):
                f = (v >> ((c * CFG.P + i) * WS)) & ((1 << WS) - 1)
                if CFG.learn and f >> (WS - 1):
                    f -= 1 << WS
                arr[c, s * CFG.P + i] = f
    return arr


# --------------------------------------------------------------------- DUT driver
class Driver:
    def __init__(self, dut):
        self.dut = dut
        self.commits = []

    async def reset(self):
        d = self.dut
        cocotb.start_soon(Clock(d.clk, 10, unit="ns").start())
        for sig in (d.start, d.learn, d.upd_err, d.label, d.feat_we, d.feat_addr, d.feat_data,
                    d.load_we, d.rot, d.load_data):
            sig.value = 0
        d.rst.value = 1
        await RisingEdge(d.clk)
        await RisingEdge(d.clk)
        d.rst.value = 0
        await RisingEdge(d.clk)
        while int(d.busy.value):
            await RisingEdge(d.clk)
        cocotb.start_soon(self._monitor())

    async def _monitor(self):
        d = self.dut
        while True:
            await RisingEdge(d.dbg_commit)
            await ReadOnly()
            self.commits.append((int(d.dbg_pass2.value), d.dbg_q.value.to_unsigned()))

    async def load(self, arr):
        d = self.dut
        d.load_we.value = 1
        for w in to_words(arr):
            d.load_data.value = w
            await RisingEdge(d.clk)
        d.load_we.value = 0

    async def read(self):
        d = self.dut
        d.rot.value = 1
        words = []
        for _ in range(CFG.S):
            await ReadOnly()
            words.append(d.head.value.to_unsigned())
            await RisingEdge(d.clk)
        d.rot.value = 0
        return from_words(words)

    async def run(self, x, label, learn=0, upd_err=0):
        d = self.dut
        d.feat_we.value = 1
        for f, v in enumerate(x):
            d.feat_addr.value = f
            d.feat_data.value = int(v)
            await RisingEdge(d.clk)
        d.feat_we.value = 0
        self.commits = []
        d.label.value, d.learn.value, d.upd_err.value = int(label), learn, upd_err
        d.start.value = 1
        await RisingEdge(d.clk)
        d.start.value = 0
        await RisingEdge(d.done)
        await ReadOnly()
        flat = d.dist_flat.value.to_unsigned()
        dist = [(flat >> (c * AW)) & ((1 << AW) - 1) for c in range(CFG.C)]
        res = int(d.pred.value), int(d.learned.value), dist, list(self.commits)
        await RisingEdge(d.clk)
        return res


def slice_words(q):
    return [sum(int(b) << i for i, b in enumerate(q[s * CFG.P:(s + 1) * CFG.P]))
            for s in range(CFG.S)]


async def check_sample(drv, L, x, y, learn, upd_err, tag):
    """Run one sample on the DUT and the model (test-then-train) and compare everything."""
    q, qp = encode(x)
    exp_dist = [int(v) for v in SIM.distance(qp, L.protop)]
    if learn and CFG.learn:
        L.mode = "error" if (upd_err and CFG.learn == 2) else "bundle"
        exp_pred = L.step(q, qp, int(y))
        exp_learned = int(L.mode == "bundle" or exp_pred != int(y))
    else:
        exp_pred, exp_learned = int(H.classify(qp, L.protop, SIM)), 0
    pred, learned, dist, commits = await drv.run(x, y, learn, upd_err)
    qs = slice_words(q)
    exp_commits = [(0, qs[s]) for s in range(CFG.SC)] + ([(1, w) for w in qs] if exp_learned else [])
    assert commits == exp_commits, f"{tag}: query slices differ"
    assert dist == exp_dist, f"{tag}: distances {dist} != model {exp_dist}"
    assert pred == exp_pred, f"{tag}: pred {pred} != model {exp_pred}"
    assert learned == exp_learned, f"{tag}: learned {learned} != model {exp_learned}"


async def check_state(drv, L, tag):
    got = await drv.read()
    exp = model_state(L)
    bad = np.argwhere(got != exp)
    assert len(bad) == 0, (f"{tag}: {len(bad)} state mismatches, first at class/dim {bad[0]}: "
                           f"rtl {got[tuple(bad[0])]} model {exp[tuple(bad[0])]}")


def real_data():
    d = data.load(CFG.F, CFG.Q)
    return d


# -------------------------------------------------------------------------- tests
@cocotb.test()
async def test_reset_and_ties(dut):
    """After reset the state is all zero; prototypes are the tie vector T (learn on) or 0,
    so every distance is equal and the argmin tie must pick class 0."""
    drv = Driver(dut)
    await drv.reset()
    L = new_learner()
    set_state(L, np.zeros((CFG.C, CFG.D), dtype=np.int16 if CFG.learn else np.uint8))
    await check_state(drv, L, "reset")
    rng = np.random.default_rng(1)
    for n in range(5):
        x = rng.integers(0, CFG.Q, CFG.F)
        await check_sample(drv, L, x, rng.integers(CFG.C), 0, 0, f"tie#{n}")


@cocotb.test()
async def test_random_inference(dut):
    """Random features against random prototypes / counters (incl. rails and zeros)."""
    drv = Driver(dut)
    await drv.reset()
    rng = np.random.default_rng(2)
    L = new_learner()
    for n in range(N_RAND):
        if n % 25 == 0:
            st = random_state(rng)
            set_state(L, st)
            await drv.load(st)
        x = rng.integers(0, CFG.Q, CFG.F)
        await check_sample(drv, L, x, rng.integers(CFG.C), 0, 0, f"rand#{n}")
    await check_state(drv, L, "after random inference")


@cocotb.test()
async def test_real_inference(dut):
    """Real UCI-HAR validation windows against prototypes trained by the model."""
    drv = Driver(dut)
    await drv.reset()
    d = real_data()
    im_q = H.encode(d["train"][0], IM)
    wt = CFG.w if CFG.learn else 16
    T = H.train(im_q, d["train"][1], CFG.D, wt, "error", IM.T, SIM, 0, CFG.seed, error_epochs=1)
    L = new_learner()
    set_state(L, T.cnt.copy() if CFG.learn else T.proto.copy())
    await drv.load(model_state(L))
    Xv, yv, _ = d["val"]
    hits = 0
    for n in range(N_REAL):
        await check_sample(drv, L, Xv[n * 7], yv[n * 7], 0, 0, f"real#{n}")
        hits += int(H.classify(encode(Xv[n * 7])[1], L.protop, SIM) == yv[n * 7])
    dut._log.info(f"real-sample accuracy on {N_REAL} windows: {hits / N_REAL:.2f}")


@cocotb.test(skip=CFG.learn == 0)
async def test_learning_stream(dut):
    """Test-then-train stream from random counters: bundle-all, then error-driven updates.
    Full counter state is compared every 10 samples."""
    drv = Driver(dut)
    await drv.reset()
    rng = np.random.default_rng(3)
    d = real_data()
    Xt, yt, _ = d["train"]
    L = new_learner()
    st = random_state(rng)
    set_state(L, st)
    await drv.load(st)
    for n in range(N_STREAM):
        upd_err = int(CFG.learn == 2 and n >= N_STREAM // 3)
        if n % 2:
            i = rng.integers(len(yt))
            x, y = Xt[i], yt[i]
        else:
            x, y = rng.integers(0, CFG.Q, CFG.F), rng.integers(CFG.C)
        await check_sample(drv, L, x, y, 1, upd_err, f"stream#{n}")
        if n % 10 == 9:
            await check_state(drv, L, f"stream#{n}")
    await check_state(drv, L, "stream end")


@cocotb.test(skip=CFG.learn == 0)
async def test_saturation_directed(dut):
    """Counters at both rails, pushed further in both directions, plus the error-driven
    'prediction correct -> no update' case."""
    drv = Driver(dut)
    await drv.reset()
    rng = np.random.default_rng(4)
    L = new_learner()
    x = rng.integers(0, CFG.Q, CFG.F)
    for rail in (HI, LO):
        for upd_err in ((0, 1) if CFG.learn == 2 else (0,)):
            st = np.full((CFG.C, CFG.D), rail, dtype=np.int16)
            set_state(L, st)
            await drv.load(st)
            # all prototypes equal -> pred 0; label 3 forces an error-driven update of 3 and 0
            for rep in range(3):
                await check_sample(drv, L, x, 3, 1, upd_err, f"rail{rail}/err{upd_err}/rep{rep}")
            await check_state(drv, L, f"rail{rail}/err{upd_err}")
    if CFG.learn == 2:   # correct prediction -> no update, no stochastic-event increment
        st = random_state(rng)
        set_state(L, st)
        await drv.load(st)
        q, qp = encode(x)
        y = int(H.classify(qp, L.protop, SIM))
        await check_sample(drv, L, x, y, 1, 1, "no-update")
        await check_state(drv, L, "no-update")
