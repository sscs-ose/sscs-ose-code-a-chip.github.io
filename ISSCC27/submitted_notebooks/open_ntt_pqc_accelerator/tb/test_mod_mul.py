"""cocotb test: Montgomery multiplier RTL vs Python golden model."""
import os
import sys
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ntt_golden import montmul, DIL_Q  # noqa: E402


@cocotb.test()
async def test_mod_mul_random(dut):
    """Drive random operands, one per cycle, check pipelined result vs golden."""
    q = DIL_Q
    random.seed(1)

    try:
        clk = Clock(dut.clk, 10, unit="ns")     # cocotb >= 2.0
    except TypeError:
        clk = Clock(dut.clk, 10, units="ns")    # cocotb 1.x
    cocotb.start_soon(clk.start())

    # Reset
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.a.value = 0
    dut.b.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    N = 2000
    inputs = [(random.randrange(q), random.randrange(q)) for _ in range(N)]
    expected = [montmul(a, b, q) for (a, b) in inputs]

    # 1-cycle latency: feed operands, sample result on the following edge.
    got = []
    for i in range(N):
        a, b = inputs[i]
        dut.a.value = a
        dut.b.value = b
        dut.in_valid.value = 1
        await RisingEdge(dut.clk)
        if i >= 1:  # first valid result appears one cycle after first input
            got.append(int(dut.result.value))

    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    got.append(int(dut.result.value))

    fails = 0
    for i in range(N):
        if got[i] != expected[i]:
            fails += 1
            if fails <= 5:
                a, b = inputs[i]
                dut._log.error(
                    "mismatch i=%d a=%d b=%d got=%d exp=%d" % (i, a, b, got[i], expected[i])
                )
    assert fails == 0, "%d/%d Montgomery products mismatch" % (fails, N)
    dut._log.info("mod_mul: %d/%d Montgomery products match golden model" % (N, N))
