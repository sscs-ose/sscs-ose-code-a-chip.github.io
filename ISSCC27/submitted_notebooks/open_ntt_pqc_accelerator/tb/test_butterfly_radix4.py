"""cocotb testbench for butterfly_radix4 module."""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_radix4_butterfly(dut):
    """Test 4-point Radix-4 butterfly arithmetic datapath."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.a0.value = 0
    dut.a1.value = 0
    dut.a2.value = 0
    dut.a3.value = 0
    dut.zeta1.value = 0
    dut.zeta2.value = 0
    dut.zeta3.value = 0

    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    Q = 8380417

    for trial in range(50):
        a0 = random.randrange(Q)
        a1 = random.randrange(Q)
        a2 = random.randrange(Q)
        a3 = random.randrange(Q)
        z1 = random.randrange(Q)
        z2 = random.randrange(Q)
        z3 = random.randrange(Q)

        dut.a0.value = a0
        dut.a1.value = a1
        dut.a2.value = a2
        dut.a3.value = a3
        dut.zeta1.value = z1
        dut.zeta2.value = z2
        dut.zeta3.value = z3
        dut.in_valid.value = 1
        await RisingEdge(dut.clk)
        dut.in_valid.value = 0

        # Wait for out_valid (2 cycles: 1 for multiplier, 1 for stage 2)
        while int(dut.out_valid.value) == 0:
            await RisingEdge(dut.clk)

        y0 = int(dut.y0.value)
        y1 = int(dut.y1.value)
        y2 = int(dut.y2.value)
        y3 = int(dut.y3.value)

        assert 0 <= y0 < Q
        assert 0 <= y1 < Q
        assert 0 <= y2 < Q
        assert 0 <= y3 < Q

    dut._log.info("50/50 Radix-4 butterfly tests PASSED.")
