"""cocotb tests for rtl/dcim_8bit.v (dcim_core, WBITS = ABITS = 8).

Protocol per the dcim_8bit.v / dcim_core.v headers: start->valid = 8 edges;
xbit checked on every dot product. Expected values from golden.dcim_dot.
Vectors: python/vectors/dense8_{corners,random,real_layer}.npz.
Protocol tests reuse 4-bit codes from random.npz (valid 8-bit inputs);
full_scale and dense8 vectors cover the high bit-planes.
"""
import cocotb

import core_tb as tb

tb.configure(8, wbits=8, abits=8, xbit=True)
V = tb.VCD_RUN
LAG = 1  # header: row written at the edge after its load_en edge
P = "dense8_"


@cocotb.test(skip=V)
async def corners(dut):
    await tb.corners(dut, P)


@cocotb.test(skip=V)
async def random_10k(dut):
    await tb.random_10k(dut, P)


@cocotb.test(skip=V)
async def real_layer(dut):
    await tb.real_layer(dut, P)


@cocotb.test(skip=not V)
async def vcd_real_layer(dut):
    await tb.vcd_real_layer(dut, P)


@cocotb.test(skip=V)
async def latency_and_hold(dut):
    await tb.latency_and_hold(dut)


@cocotb.test(skip=V)
async def back_to_back(dut):
    await tb.back_to_back(dut)


@cocotb.test(skip=V)
async def start_with_load_ignored(dut):
    await tb.start_with_load_ignored(dut)


@cocotb.test(skip=V)
async def load_while_busy_ignored(dut):
    await tb.load_while_busy_ignored(dut)


@cocotb.test(skip=V)
async def start_while_busy_ignored(dut):
    await tb.start_while_busy_ignored(dut)


@cocotb.test(skip=V)
async def reset_mid_compute(dut):
    await tb.reset_mid_compute(dut)


@cocotb.test(skip=V)
async def full_scale(dut):
    await tb.full_scale(dut)


@cocotb.test(skip=V)
async def partial_reload(dut):
    await tb.partial_reload(dut)


# Clock-gated storage (rtl/icg.v): directed tests, see core_tb.py.
@cocotb.test(skip=V)
async def cg_rst_idle(dut):
    await tb.cg_rst_idle(dut)


@cocotb.test(skip=V)
async def cg_load_before_rst(dut):
    await tb.cg_load_before_rst(dut)


@cocotb.test(skip=V)
async def cg_single_row_write(dut):
    await tb.cg_single_row_write(dut)


@cocotb.test(skip=V)
async def cg_enable_glitch(dut):
    await tb.cg_enable_glitch(dut)


@cocotb.test(skip=V)
async def cg_back_to_back_loads(dut):
    await tb.cg_back_to_back_loads(dut)


@cocotb.test(skip=V)
async def cg_write_edge_whitebox(dut):
    await tb.cg_write_edge_whitebox(dut, LAG)
