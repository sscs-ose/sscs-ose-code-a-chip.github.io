"""cocotb testbench for banked_mem_ctrl module."""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_banked_memory_parallel(dut):
    """Test concurrent 4-way parallel read/write across memory banks."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.rd_en.value = 0
    dut.wr_en.value = 0
    dut.raddr0.value = 0
    dut.raddr1.value = 0
    dut.raddr2.value = 0
    dut.raddr3.value = 0
    dut.waddr0.value = 0
    dut.waddr1.value = 0
    dut.waddr2.value = 0
    dut.waddr3.value = 0
    dut.wdata0.value = 0
    dut.wdata1.value = 0
    dut.wdata2.value = 0
    dut.wdata3.value = 0

    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Write to 4 bank slots simultaneously
    test_vals = [0x123456, 0x654321, 0xABCDEF, 0xFEDCBA]
    dut.wr_en.value = 1
    dut.waddr0.value = 0
    dut.waddr1.value = 1
    dut.waddr2.value = 2
    dut.waddr3.value = 3
    dut.wdata0.value = test_vals[0]
    dut.wdata1.value = test_vals[1]
    dut.wdata2.value = test_vals[2]
    dut.wdata3.value = test_vals[3]
    await RisingEdge(dut.clk)
    dut.wr_en.value = 0

    # Read back 4 bank slots simultaneously
    dut.rd_en.value = 1
    dut.raddr0.value = 0
    dut.raddr1.value = 1
    dut.raddr2.value = 2
    dut.raddr3.value = 3
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert int(dut.rd_valid.value) == 1
    assert int(dut.rdata0.value) == test_vals[0]
    assert int(dut.rdata1.value) == test_vals[1]
    assert int(dut.rdata2.value) == test_vals[2]
    assert int(dut.rdata3.value) == test_vals[3]

    dut._log.info("4-Bank concurrent parallel read/write PASSED.")
