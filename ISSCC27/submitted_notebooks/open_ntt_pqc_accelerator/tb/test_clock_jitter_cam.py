import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_clock_jitter_and_camouflage(dut):
    """Verify time-domain clock jitter modulation and dummy power camouflage toggling (N10)."""
    clock = Clock(dut.clk_in, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.enable_jitter.value = 0
    dut.enable_camou.value = 0
    dut.entropy_seed.value = 0
    dut.datapath_busy.value = 0
    await ClockCycles(dut.clk_in, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk_in, 2)

    # 1. Enable Jitter Phase Modulation
    dut.enable_jitter.value = 1
    dut.entropy_seed.value = 0xA7
    observed_phases = set()

    for _ in range(50):
        await RisingEdge(dut.clk_in)
        phase = int(dut.phase_state.value)
        observed_phases.add(phase)

    dut._log.info(f"Observed jitter phase taps: {observed_phases}")
    # Must observe multiple discrete delay taps
    assert len(observed_phases) >= 3, f"Expected at least 3 phase states, observed: {observed_phases}"

    # 2. Enable Power Camouflage
    dut.enable_camou.value = 1
    dut.datapath_busy.value = 0 # Idle mode -> dummy loads should toggle vigorously
    idle_toggles = []
    for _ in range(20):
        await RisingEdge(dut.clk_in)
        idle_toggles.append(int(dut.dummy_toggles.value))

    assert len(set(idle_toggles)) > 5, "Dummy power camouflage should dynamically switch loads during idle"
    dut._log.info("Clock jitter and power camouflage verification passed successfully!")
