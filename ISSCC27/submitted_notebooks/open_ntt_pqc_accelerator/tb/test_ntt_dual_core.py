import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_dual_core_modes(dut):
    """Verify Reconfigurable Dual-Core NTT engine: Concurrent 2X Mode & Lockstep Fault Mode (N11)."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.lockstep_mode.value = 0
    dut.fault_inject_c1.value = 0
    dut.start.value = 0
    dut.mode_gs.value = 0
    dut.c0_a_in.value = 0
    dut.c0_b_in.value = 0
    dut.c0_twiddle.value = 0
    dut.c1_a_in.value = 0
    dut.c1_b_in.value = 0
    dut.c1_twiddle.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # 1. Test Concurrent 2X Mode (lockstep_mode = 0)
    # Core 0: (A=1000, B=2000, W=3000)
    # Core 1: (A=5000, B=6000, W=7000)
    dut.lockstep_mode.value = 0
    dut.c0_a_in.value = 1000
    dut.c0_b_in.value = 2000
    dut.c0_twiddle.value = 3000
    dut.c1_a_in.value = 5000
    dut.c1_b_in.value = 6000
    dut.c1_twiddle.value = 7000
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    while not dut.done.value:
        await RisingEdge(dut.clk)

    c0_out_a = int(dut.c0_a_out.value)
    c1_out_a = int(dut.c1_a_out.value)
    dut._log.info(f"Concurrent Mode Results: Core0_A={c0_out_a}, Core1_A={c1_out_a}")
    assert c0_out_a != c1_out_a, "Concurrent mode should compute distinct outputs for distinct inputs"
    assert dut.lockstep_alarm.value == 0, "No alarm expected in concurrent mode"

    # 2. Test Lockstep Mode (lockstep_mode = 1) - Healthy Operation
    dut.lockstep_mode.value = 1
    dut.fault_inject_c1.value = 0
    dut.c0_a_in.value = 12345
    dut.c0_b_in.value = 67890
    dut.c0_twiddle.value = 45678
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    while not dut.done.value:
        await RisingEdge(dut.clk)

    assert int(dut.c0_a_out.value) == int(dut.c1_a_out.value), "Lockstep outputs must match identically"
    assert int(dut.c0_b_out.value) == int(dut.c1_b_out.value), "Lockstep outputs must match identically"
    assert dut.lockstep_alarm.value == 0, "No alarm expected during healthy lockstep execution"
    dut._log.info("Healthy Lockstep execution verified: Core 0 and Core 1 are cycle-identical.")

    # 3. Test Lockstep Mode with Injected Fault (FIA Containment)
    dut.fault_inject_c1.value = 1 # Inject single-bit glitch into shadow core
    dut.c0_a_in.value = 99999
    dut.c0_b_in.value = 88888
    dut.c0_twiddle.value = 77777
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    while not dut.done.value:
        await RisingEdge(dut.clk)

    assert dut.lockstep_alarm.value == 1, "Lockstep comparator must raise alarm on divergence!"
    dut._log.info("Lockstep fault containment verified: alarm successfully fired on discrepancy!")
