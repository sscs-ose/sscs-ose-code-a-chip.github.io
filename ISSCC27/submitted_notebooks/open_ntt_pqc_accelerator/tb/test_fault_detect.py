"""cocotb testbench for fault_detect module."""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_fault_detection_security(dut):
    """Test real-time fault detection and tamper containment under normal and faulted conditions."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.check_en.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    dut.a_out.value = 0
    dut.b_out.value = 0

    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    Q = 8380417

    # 1. Normal valid operation: a_in + b_in == a_out + b_out (mod Q)
    dut.check_en.value = 1
    dut.a_in.value = 1000
    dut.b_in.value = 2000
    dut.a_out.value = 1500
    dut.b_out.value = 1500
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert int(dut.fault_alert.value) == 0, "False positive fault detected!"

    # 2. Injected glitch fault: mismatch in sum invariant
    dut.a_out.value = 1500
    dut.b_out.value = 999999  # Corrupted by laser / glitch
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert int(dut.fault_alert.value) == 1, "Fault injection was not caught by detector!"
    assert int(dut.tamper_lock.value) == 1, "Tamper lock was not engaged!"
    assert int(dut.fault_count.value) >= 1

    dut._log.info("Fault detection & tamper containment verified successfully!")
