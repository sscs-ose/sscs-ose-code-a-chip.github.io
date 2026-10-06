"""cocotb test: NTT butterfly RTL vs Python golden model (streaming)."""
import os
import sys
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ntt_golden import montmul, modadd, modsub, DIL_Q  # noqa: E402

LATENCY = 2  # butterfly pipeline depth


async def _run(dut, mode_gs):
    q = DIL_Q
    random.seed(2 if mode_gs == 0 else 5)

    dut.mode_gs.value = mode_gs
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)

    N = 1500
    vecs = [(random.randrange(q), random.randrange(q), random.randrange(q)) for _ in range(N)]
    exp = []
    for a, b, z in vecs:
        if mode_gs == 0:
            t = montmul(z, b, q)
            exp.append((modadd(a, t, q), modsub(a, t, q)))
        else:
            u = modadd(a, b, q)
            v = modsub(a, b, q)
            exp.append((u, montmul(z, v, q)))

    got = []

    async def collect():
        while len(got) < N:
            await RisingEdge(dut.clk)
            if dut.out_valid.value == 1:
                got.append((int(dut.a_out.value), int(dut.b_out.value)))

    collector = cocotb.start_soon(collect())

    for a, b, z in vecs:
        dut.a_in.value = a
        dut.b_in.value = b
        dut.zeta.value = z
        dut.in_valid.value = 1
        await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    for _ in range(LATENCY + 2):
        await RisingEdge(dut.clk)

    await collector

    fails = 0
    for i in range(N):
        if got[i] != exp[i]:
            fails += 1
            if fails <= 5:
                dut._log.error("mode_gs=%d i=%d got=%s exp=%s" % (mode_gs, i, got[i], exp[i]))
    assert fails == 0, "mode_gs=%d: %d/%d butterflies mismatch" % (mode_gs, fails, N)
    dut._log.info("butterfly mode_gs=%d: %d/%d results match golden model" % (mode_gs, N, N))


@cocotb.test()
async def test_butterfly_random(dut):
    try:
        clk = Clock(dut.clk, 10, unit="ns")
    except TypeError:
        clk = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.mode_gs.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    dut.zeta.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    await _run(dut, 0)   # Cooley-Tukey (forward)
    await _run(dut, 1)   # Gentleman-Sande (inverse)
