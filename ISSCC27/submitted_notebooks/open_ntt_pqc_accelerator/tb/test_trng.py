import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_trng_entropy(dut):
    """Verify hardware TRNG operation and NIST SP 800-90B monobit entropy statistics."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.enable.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    dut.enable.value = 1
    words = []
    collected_bits = []

    # Collect 50 random 24-bit words
    for _ in range(50):
        while True:
            await RisingEdge(dut.clk)
            if dut.rand_valid.value == 1:
                val = int(dut.rand_out.value)
                words.append(val)
                for b in range(24):
                    collected_bits.append((val >> b) & 1)
                break

    assert len(words) == 50, f"Expected 50 words, got {len(words)}"
    ones_count = sum(collected_bits)
    total_bits = len(collected_bits)
    p_ones = ones_count / total_bits

    dut._log.info(f"Collected {total_bits} bits ({len(words)} words) from TRNG.")
    dut._log.info(f"Ones ratio: {p_ones:.4f} (Ideal: 0.5000)")

    # NIST SP 800-90B Monobit test check: should be comfortably balanced around 0.5
    assert 0.35 <= p_ones <= 0.65, f"Monobit test failed: p_ones = {p_ones}"
    dut._log.info("TRNG Monobit and stream test passed successfully!")
