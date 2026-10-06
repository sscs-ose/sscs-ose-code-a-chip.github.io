import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

Q_DILITHIUM = 8380417

@cocotb.test()
async def test_poly_sampler_rejection_and_cbd(dut):
    """Verify hardware Rejection Sampler and Centered Binomial Distribution (CBD) Generator (N12)."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.mode_cbd.value = 0
    dut.eta_param.value = 2
    dut.in_valid.value = 0
    dut.in_data.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # 1. Test Uniform Rejection Sampling (mode_cbd = 0)
    # Send a valid candidate (< Q)
    dut.mode_cbd.value = 0
    dut.in_valid.value = 1
    dut.in_data.value = 5000000
    await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    assert dut.out_valid.value == 1, "Candidate < Q must be accepted"
    assert int(dut.out_coeff.value) == 5000000
    assert dut.out_rejected.value == 0

    # Send an invalid candidate (>= Q, e.g., 9,000,000)
    dut.in_valid.value = 1
    dut.in_data.value = 9000000
    await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    assert dut.out_valid.value == 0, "Candidate >= Q must be rejected"
    assert dut.out_rejected.value == 1, "out_rejected must pulse high"
    dut._log.info("Rejection sampling verification passed!")

    # 2. Test Centered Binomial Distribution (mode_cbd = 1, eta = 2)
    dut.mode_cbd.value = 1
    dut.eta_param.value = 2 # eta = 2: bits[0..1] - bits[2..3] in {-2..2}

    # Case A: a=1+1=2, b=0+0=0 -> diff = +2
    dut.in_valid.value = 1
    dut.in_data.value = 0b0011 # bits[1:0]=2'b11, bits[3:2]=2'b00
    await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    assert dut.out_valid.value == 1
    assert int(dut.out_coeff.value) == 2, f"Expected 2, got {int(dut.out_coeff.value)}"

    # Case B: a=0+0=0, b=1+1=2 -> diff = -2 -> Q - 2 mod Q
    dut.in_valid.value = 1
    dut.in_data.value = 0b1100 # bits[1:0]=2'b00, bits[3:2]=2'b11
    await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    assert dut.out_valid.value == 1
    expected_neg2 = Q_DILITHIUM - 2
    assert int(dut.out_coeff.value) == expected_neg2, f"Expected {expected_neg2}, got {int(dut.out_coeff.value)}"

    dut._log.info("CBD noise generation verification passed successfully!")
