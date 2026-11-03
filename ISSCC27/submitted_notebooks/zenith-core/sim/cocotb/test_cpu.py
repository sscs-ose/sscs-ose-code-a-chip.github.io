import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

PROGRAM = [
    0b000_001_000_000_0101,
    0b000_010_000_000_0011,
    0b001_011_001_010_0000,
    0b001_100_001_010_0010,
    0b001_101_001_010_0100,
    0b001_110_001_010_0110,
    0b110_000_001_000_0000,
    0b100_100_100_000_0001,
    0x0000,
    0b111_000_000_000_0000,
]
LISTING = [
    "ADDI r1, r0, 5",
    "ADDI r2, r0, 3",
    "ADD  r3, r1, r2",
    "SUB  r4, r1, r2",
    "AND  r5, r1, r2",
    "OR   r6, r1, r2",
    "OUT  r1",
    "BEQ  r4, r4, +1",
    "NOP",
    "JUMP 0",
]
EXPECTED_REGS = {1: 5, 2: 3, 3: 8, 4: 2, 5: 1, 6: 7}
STATES = ["FETCH", "WAIT", "DECODE", "EXEC", "MEM", "WB"]


async def instruction_memory(dut):
    while True:
        await FallingEdge(dut.clk)
        pc = int(dut.pc_out.value)
        dut.instruction_in.value = PROGRAM[pc] if pc < len(PROGRAM) else 0


async def reset(dut):
    dut.rst_n.value = 0
    dut.instruction_in.value = 0
    dut.mem_rdata.value = 0xAB
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(instruction_memory(dut))
    await reset(dut)


@cocotb.test()
async def alu_and_gpio(dut):
    await start(dut)
    trace = []
    retired = []
    last_pc = None
    for cyc in range(160):
        await RisingEdge(dut.clk)
        state = int(dut.debug_state.value)
        pc = int(dut.pc_out.value)
        trace.append(
            {
                "cycle": cyc,
                "pc": pc,
                "state": state,
                "gpio": int(dut.gpio_out.value),
                "regs": [0] + [int(dut.regs[i].value) for i in range(1, 8)],
            }
        )
        if state == 0 and pc != last_pc and pc < len(PROGRAM):
            retired.append(pc)
        last_pc = pc

    for r, v in EXPECTED_REGS.items():
        got = int(dut.regs[r].value)
        assert got == v, f"r{r} = {got}, expected {v}"
        dut._log.info(f"r{r} = {got}  (expected {v})  OK")

    assert int(dut.gpio_out.value) == 5, "gpio_out should be 5 after OUT r1"
    dut._log.info(f"gpio_out = 0x{int(dut.gpio_out.value):02X}  OK")

    assert 8 not in retired, "NOP at address 8 must be skipped by the taken BEQ"
    dut._log.info(f"PC sequence = {retired[:12]}  (address 8 skipped)  OK")

    default = Path(__file__).resolve().parents[2] / "build" / "cocotb" / "cocotb_trace.json"
    out = Path(os.environ.get("ZC_TRACE", default))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"program": LISTING, "states": STATES, "trace": trace}, f)


@cocotb.test()
async def reset_state(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(instruction_memory(dut))
    await reset(dut)
    await ClockCycles(dut.clk, 20)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    assert int(dut.pc_out.value) == 0
    assert int(dut.gpio_out.value) == 0
    assert int(dut.regs[1].value) == 0
    dut._log.info("asynchronous reset clears pc, gpio_out and registers  OK")
