"""cocotb testbench for perf_counters module."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_performance_counters(dut):
    """Test cycle profiling and Hamming distance toggle accumulation."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.sample_en.value = 0
    dut.is_busy.value = 0
    dut.is_stall.value = 0
    dut.coeff_bus.value = 0

    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    dut.sample_en.value = 1
    dut.is_busy.value = 1

    # Transition 1: 0x000000 -> 0x00000F (4 bits toggled)
    dut.coeff_bus.value = 0x00000F
    await RisingEdge(dut.clk)

    # Transition 2: 0x00000F -> 0x0000FF (4 more bits toggled)
    dut.coeff_bus.value = 0x0000FF
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert int(dut.compute_cycles.value) >= 2
    assert int(dut.toggle_count.value) == 8, f"Expected 8 toggles, got {int(dut.toggle_count.value)}"

    dut._log.info("Performance & toggle counters verified successfully!")
