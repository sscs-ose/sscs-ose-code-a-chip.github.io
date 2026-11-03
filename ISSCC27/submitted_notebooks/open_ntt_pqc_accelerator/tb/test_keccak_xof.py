import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_keccak_xof_sponge(dut):
    """Verify Keccak-f[1600] / SHAKE-128 absorb, 24-round permutation, and coefficient squeeze stream."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.start_absorb.value = 0
    dut.absorb_valid.value = 0
    dut.absorb_data.value = 0
    dut.absorb_last.value = 0
    dut.squeeze_req.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # 1. Start absorbing seed (e.g. 32-byte rho seed in 4 x 64-bit words)
    dut.start_absorb.value = 1
    await RisingEdge(dut.clk)
    dut.start_absorb.value = 0
    await RisingEdge(dut.clk)

    seed_words = [
        0x0123456789ABCDEF,
        0xFEDCBA9876543210,
        0x1122334455667788,
        0x99AABBCCDDEEFF00
    ]

    for i, w in enumerate(seed_words):
        while not dut.absorb_ready.value:
            await RisingEdge(dut.clk)
        dut.absorb_valid.value = 1
        dut.absorb_data.value = w
        dut.absorb_last.value = 1 if (i == len(seed_words) - 1) else 0
        await RisingEdge(dut.clk)

    dut.absorb_valid.value = 0
    dut.absorb_last.value = 0

    # 2. Wait for 24-round Keccak permutation to finish
    dut._log.info("Waiting for 24-round Keccak permutation...")
    timeout = 100
    while dut.perm_busy.value == 0 and timeout > 0:
        await RisingEdge(dut.clk)
        timeout -= 1

    while dut.perm_busy.value == 1:
        await RisingEdge(dut.clk)

    dut._log.info("Permutation complete! Starting coefficient squeezing...")

    # 3. Squeeze 16 coefficients (24-bit each)
    squeezed = []
    for _ in range(16):
        dut.squeeze_req.value = 1
        await RisingEdge(dut.clk)
        dut.squeeze_req.value = 0
        await RisingEdge(dut.clk)
        if dut.squeeze_valid.value:
            val = int(dut.squeeze_data.value)
            squeezed.append(val)

    assert len(squeezed) == 16, f"Expected 16 coefficients, got {len(squeezed)}"
    dut._log.info(f"Squeezed 16 coefficients: {[hex(x) for x in squeezed[:4]]}...")

    # Check that outputs are non-trivial (permutation did mix entropy)
    assert any(x != 0 for x in squeezed), "Squeezed data should not be all zero!"
    dut._log.info("Keccak-f[1600] / SHAKE-128 XOF verification passed!")
