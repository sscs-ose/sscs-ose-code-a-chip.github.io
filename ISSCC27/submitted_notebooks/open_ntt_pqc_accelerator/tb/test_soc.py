"""cocotb testbench for open_ntt_soc (N3)."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_pcpi_custom_instruction(dut):
    """Test RISC-V PCPI custom0 instruction trigger and execution handshake."""
    clk = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clk.start())

    dut.rst_n.value = 0
    dut.pcpi_valid.value = 0
    dut.pcpi_insn.value = 0
    dut.pcpi_rs1.value = 0
    dut.pcpi_rs2.value = 0
    dut.cpu_wb_cyc.value = 0
    dut.cpu_wb_stb.value = 0
    dut.cpu_wb_we.value = 0
    dut.cpu_wb_addr.value = 0
    dut.cpu_wb_wdata.value = 0

    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Issue custom0 instruction (opcode 7'b0001011 = 0x0B)
    # rs1 = 0x1000 (pointer), rs2 = 0x0 (OP_NTT)
    dut.pcpi_valid.value = 1
    dut.pcpi_insn.value = 0x0000000B  # custom0
    dut.pcpi_rs1.value = 0x00001000
    dut.pcpi_rs2.value = 0x00000000   # OP_NTT
    await RisingEdge(dut.clk)

    # CPU PCPI handshake
    assert int(dut.pcpi_wait.value) == 1, "PCPI wait was not asserted by accelerator"
    dut.pcpi_valid.value = 0

    # Wait for completion (ntt execution takes cycles)
    cycles_waited = 0
    while int(dut.pcpi_ready.value) == 0:
        await RisingEdge(dut.clk)
        cycles_waited += 1
        if cycles_waited > 20000:
            raise TimeoutError("Accelerator PCPI ready timeout")

    assert int(dut.pcpi_wr.value) == 1, "PCPI write-back signal not asserted"
    ret_cycles = int(dut.pcpi_rd.value)
    dut._log.info(f"Custom instruction completed in {ret_cycles} cycles (pcpi_ready received)!")
