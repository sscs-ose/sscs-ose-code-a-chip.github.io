"""cocotb testbench for twiddle_gen (N4)."""
import os
import sys
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ntt_golden import DIL_Q, DIL_ROOT, DIL_N, _zetas_complete_mont


@cocotb.test()
async def test_twiddle_gen_stages(dut):
    """Test stage seed initialization and stepping in on-the-fly generator."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.init_stage.value = 0
    dut.stage_idx.value = 0
    dut.step_valid.value = 0
    dut.seed_in.value = 0

    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    zetas = _zetas_complete_mont(DIL_ROOT, DIL_N, DIL_Q)

    # Test stage 0 seed initialization
    dut.stage_idx.value = 0
    dut.init_stage.value = 1
    await RisingEdge(dut.clk)
    dut.init_stage.value = 0
    await RisingEdge(dut.clk)

    assert int(dut.ready.value) == 1, "twiddle_gen not ready after init"
    assert int(dut.zeta_out.value) == zetas[1], f"Stage 0 seed mismatch: got {hex(int(dut.zeta_out.value))}, expected {hex(zetas[1])}"

    # Test stepping
    dut.step_valid.value = 1
    await RisingEdge(dut.clk)
    dut.step_valid.value = 0

    for _ in range(10):
        await RisingEdge(dut.clk)
        if int(dut.ready.value) == 1:
            break

    assert int(dut.ready.value) == 1, "twiddle_gen did not become ready after step"
    dut._log.info("twiddle_gen stage and step verification passed!")
