"""cocotb testbench for mask module (N5)."""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_masking_shares(dut):
    """Test first-order share splitting and recombination for polynomial coefficients."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.enable.value = 1
    dut.split_valid.value = 0
    dut.combine_valid.value = 0
    dut.coeff_in.value = 0
    dut.rand_mask.value = 0
    dut.share0_in.value = 0
    dut.share1_in.value = 0

    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    Q = 8380417

    # Run 100 randomized split & combine trials
    for trial in range(100):
        coeff = random.randrange(Q)
        rand_m = random.randrange(Q)

        dut.coeff_in.value = coeff
        dut.rand_mask.value = rand_m
        dut.split_valid.value = 1
        await RisingEdge(dut.clk)
        dut.split_valid.value = 0
        await RisingEdge(dut.clk)

        assert int(dut.split_done.value) == 1
        s0 = int(dut.share0_out.value)
        s1 = int(dut.share1_out.value)

        # Verify shares sum up to original modulo Q
        assert (s0 + s1) % Q == coeff, f"Share split failed: ({s0} + {s1}) % {Q} != {coeff}"

        # Test hardware recombination
        dut.share0_in.value = s0
        dut.share1_in.value = s1
        dut.combine_valid.value = 1
        await RisingEdge(dut.clk)
        dut.combine_valid.value = 0
        await RisingEdge(dut.clk)

        assert int(dut.combine_done.value) == 1
        recombined = int(dut.coeff_out.value)
        assert recombined == coeff, f"Share combine failed: {recombined} != {coeff}"

    dut._log.info("100/100 Masking share split & combine tests PASSED.")
