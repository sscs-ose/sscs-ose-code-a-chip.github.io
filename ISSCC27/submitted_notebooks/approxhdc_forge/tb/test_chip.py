"""cocotb test of the chip top (rtlgen.generate_chip): the narrow staged load port must
deliver ring words intact, and the chip must classify / learn exactly like the model.
Uses the same HDC_CFG environment variable as test_hdc.py.
"""
import math
import os

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from test_hdc import CFG, SIM, encode, new_learner, random_state, set_state, to_words, H

IOW = 32


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, int(os.environ.get("HDC_CLK_NS", 10)), unit="ns").start())
    for s in (dut.start, dut.learn, dut.upd_err, dut.label, dut.feat_we, dut.feat_addr,
              dut.feat_data, dut.ld_shift, dut.ld_data, dut.load_we):
        s.value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    while int(dut.busy.value):
        await RisingEdge(dut.clk)


async def load(dut, arr):
    rw = CFG.C * CFG.P * (CFG.w if CFG.learn else 1)
    nchunk = math.ceil(rw / IOW)
    for word in to_words(arr):
        dut.ld_shift.value = 1
        for c in range(nchunk):          # lowest chunk first; it ends up at the bottom
            dut.ld_data.value = (word >> (c * IOW)) & ((1 << IOW) - 1)
            await RisingEdge(dut.clk)
        dut.ld_shift.value = 0
        dut.load_we.value = 1
        await RisingEdge(dut.clk)
        dut.load_we.value = 0


async def run(dut, x, y, learn, upd_err):
    dut.feat_we.value = 1
    for f, v in enumerate(x):
        dut.feat_addr.value, dut.feat_data.value = f, int(v)
        await RisingEdge(dut.clk)
    dut.feat_we.value = 0
    dut.label.value, dut.learn.value, dut.upd_err.value, dut.start.value = int(y), learn, upd_err, 1
    await RisingEdge(dut.clk)
    dut.start.value = 0
    await RisingEdge(dut.done)
    res = int(dut.pred.value), int(dut.learned.value)
    await RisingEdge(dut.clk)
    return res


@cocotb.test()
async def test_chip_load_and_run(dut):
    await reset(dut)
    rng = np.random.default_rng(7)
    L = new_learner()
    st = random_state(rng)
    set_state(L, st)
    await load(dut, st)
    for n in range(40):
        x, y = rng.integers(0, CFG.Q, CFG.F), int(rng.integers(CFG.C))
        learn = int(CFG.learn > 0 and n >= 20)
        upd_err = int(CFG.learn == 2 and n >= 30)
        q, qp = encode(x)
        if learn:
            L.mode = "error" if upd_err else "bundle"
            exp = L.step(q, qp, y)
            exp_l = int(L.mode == "bundle" or exp != y)
        else:
            exp, exp_l = int(H.classify(qp, L.protop, SIM)), 0
        got = await run(dut, x, y, learn, upd_err)
        assert got == (exp, exp_l), f"chip sample {n}: rtl {got} model {(exp, exp_l)}"
