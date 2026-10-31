"""cocotb tests for rtl/sidecarcim_top.v vs golden.sidecarcim_dot.

Shared testbench: tests/top_tb.py. K from env SIDECAR_K (spec default);
PARALLEL / USE_LATCH are set by the Makefile (-P overrides).
Tests run in file order; powerup_reset_y must stay first (true power-up).
"""
import cocotb

import top_tb as tb

V = tb.VCD_RUN


# y=0 right after power-up reset (S reset to 0 since 7f67ae4; was X).
# Must be the first test (state persists across tests in one simulation).
@cocotb.test(skip=V)
async def powerup_reset_y(dut):
    await tb.powerup_reset_y(dut)


@cocotb.test(skip=V)
async def corners(dut):
    await tb.corners(dut)


@cocotb.test(skip=V)
async def random_10k(dut):
    await tb.random_10k(dut)


@cocotb.test(skip=V)
async def real_layer(dut):
    await tb.real_layer(dut)


@cocotb.test(skip=not V)
async def vcd_real_layer(dut):
    await tb.vcd_real_layer(dut)


@cocotb.test(skip=V)
async def reset_after_load_y(dut):
    await tb.reset_after_load_y(dut)


@cocotb.test(skip=V)
async def latency_and_hold(dut):
    await tb.latency_and_hold(dut)


@cocotb.test(skip=V)
async def start_ignored_during_loads(dut):
    await tb.start_ignored_during_loads(dut)


@cocotb.test(skip=V)
async def loads_while_busy_ignored(dut):
    await tb.loads_while_busy_ignored(dut)


@cocotb.test(skip=V)
async def start_while_busy_ignored(dut):
    await tb.start_while_busy_ignored(dut)


@cocotb.test(skip=V)
async def back_to_back(dut):
    await tb.back_to_back(dut)


@cocotb.test(skip=V)
async def reset_mid_compute(dut):
    await tb.reset_mid_compute(dut)


@cocotb.test(skip=V)
async def column_reload(dut):
    await tb.column_reload(dut)


# Directed VB extremes: val min/max, S = 0..VB-1, max/min merged y.
@cocotb.test(skip=V)
async def vb_extremes(dut):
    await tb.vb_extremes(dut)


# Clock-gated storage (rtl/icg.v): directed tests, see top_tb.py.
@cocotb.test(skip=V)
async def cg_top_rst_idle(dut):
    await tb.cg_top_rst_idle(dut)


@cocotb.test(skip=V)
async def cg_top_load_before_rst(dut):
    await tb.cg_top_load_before_rst(dut)


@cocotb.test(skip=V)
async def cg_top_single_write(dut):
    await tb.cg_top_single_write(dut)


@cocotb.test(skip=V)
async def cg_top_enable_glitch(dut):
    await tb.cg_top_enable_glitch(dut)


@cocotb.test(skip=V)
async def cg_top_back_to_back(dut):
    await tb.cg_top_back_to_back(dut)


# Output pipeline (PIPE_MERGE, latency ABITS + PIPE_MERGE): every edge vs a
# cycle-level model of the header protocol. Run on every top build; with
# PIPE_MERGE=0 they check the same model without the output register.
@cocotb.test(skip=V)
async def pipe_b2b_overlap(dut):
    await tb.pipe_b2b_overlap(dut)


@cocotb.test(skip=V)
async def pipe_load_in_done(dut):
    await tb.pipe_load_in_done(dut)


@cocotb.test(skip=V)
async def pipe_rst_mid_pipeline(dut):
    await tb.pipe_rst_mid_pipeline(dut)


@cocotb.test(skip=V)
async def pipe_start_on_valid_edge(dut):
    await tb.pipe_start_on_valid_edge(dut)


@cocotb.test(skip=V)
async def pipe_protocol_fuzz(dut):
    await tb.pipe_protocol_fuzz(dut)
