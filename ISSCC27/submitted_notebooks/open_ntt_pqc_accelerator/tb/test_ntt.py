"""cocotb tests for the unified poly-mult engine (ntt_top):
   - forward NTT vs golden ntt_complete
   - full polynomial multiply vs schoolbook negacyclic
"""
import os
import sys
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ntt_golden import (  # noqa: E402
    ntt_complete, poly_mul_negacyclic, MONT_R,
    DIL_Q, DIL_ROOT, DIL_N,
)

OP_NTT, OP_NTTB, OP_INTT, OP_PWM, OP_SCALE, OP_SCALEB = range(6)
Q = DIL_Q
R2 = (MONT_R * MONT_R) % Q


async def reset(dut):
    try:
        clk = Clock(dut.clk, 10, unit="ns")
    except TypeError:
        clk = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clk.start())
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.op.value = 0
    dut.scale_const.value = 0
    dut.cmd_we.value = 0
    dut.cmd_addr.value = 0
    dut.cmd_wdata.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def write_region(dut, base, data):
    dut.cmd_we.value = 1
    for i, c in enumerate(data):
        dut.cmd_addr.value = base + i
        dut.cmd_wdata.value = c
        await RisingEdge(dut.clk)
    dut.cmd_we.value = 0


async def read_region(dut, base, n):
    vals = []
    dut.cmd_we.value = 0
    for i in range(n):
        dut.cmd_addr.value = base + i
        await RisingEdge(dut.clk)
        if i > 0:
            vals.append(int(dut.cmd_rdata.value))
    await RisingEdge(dut.clk)
    vals.append(int(dut.cmd_rdata.value))
    return vals


async def run_op(dut, opcode, const=0):
    dut.op.value = opcode
    dut.scale_const.value = const
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0
    await RisingEdge(dut.clk)
    timeout = 200000
    while int(dut.busy.value) == 1:
        await RisingEdge(dut.clk)
        timeout -= 1
        assert timeout > 0, "op %d timeout" % opcode
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_ntt_forward(dut):
    """Forward NTT on region A vs golden model (plain domain)."""
    q, root, n = DIL_Q, DIL_ROOT, DIL_N
    random.seed(3)
    await reset(dut)

    for trial in range(2):
        poly = [random.randrange(q) for _ in range(n)]
        expected = ntt_complete(poly, q, root)
        await write_region(dut, 0, poly)
        await run_op(dut, OP_NTT)
        got = await read_region(dut, 0, n)
        mism = sum(1 for i in range(n) if got[i] != expected[i])
        assert mism == 0, "trial %d: %d/%d NTT coeffs mismatch" % (trial, mism, n)
        dut._log.info("forward NTT trial %d OK, cycles=%d" % (trial, int(dut.cycles.value)))


@cocotb.test()
async def test_poly_mul(dut):
    """Full polynomial multiply (NTT + PWM + INTT + domain scaling) vs
    schoolbook negacyclic reference, entirely in hardware."""
    q, root, n = DIL_Q, DIL_ROOT, DIL_N
    random.seed(7)
    await reset(dut)

    for trial in range(2):
        a = [random.randrange(q) for _ in range(n)]
        b = [random.randrange(q) for _ in range(n)]
        expected = poly_mul_negacyclic(a, b, q)

        await write_region(dut, 0, a)      # region A
        await write_region(dut, n, b)      # region B

        await run_op(dut, OP_SCALE,  R2)   # A -> Montgomery domain
        await run_op(dut, OP_SCALEB, R2)   # B -> Montgomery domain
        await run_op(dut, OP_NTT)          # NTT(A)
        await run_op(dut, OP_NTTB)         # NTT(B)
        await run_op(dut, OP_PWM)          # A = A o B
        await run_op(dut, OP_INTT)         # INTT(A) incl. n^-1
        await run_op(dut, OP_SCALE, 1)     # A -> normal domain (from Montgomery)

        got = await read_region(dut, 0, n)
        mism = sum(1 for i in range(n) if got[i] != expected[i])
        assert mism == 0, "trial %d: %d/%d product coeffs mismatch (got %r exp %r)" % (
            trial, mism, n, got[:4], expected[:4])
        dut._log.info("poly-mult trial %d OK (matches schoolbook)" % trial)

    dut._log.info("unified poly-mult engine: all trials PASS")
