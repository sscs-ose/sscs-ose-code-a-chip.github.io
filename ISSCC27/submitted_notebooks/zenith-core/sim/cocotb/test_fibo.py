import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

ROOT = Path(__file__).resolve().parents[2]
STATES = ["FETCH", "WAIT", "DECODE", "EXEC", "MEM", "WB"]
N_OUT = 14
LOOP_LEN = 7
CPI = 6


def hex_path():
    env = os.environ.get("ZC_HEX")
    if env:
        return Path(env)
    return ROOT / "programs" / "fibo.hex"


def load_hex(path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path} no existe: compilar programs/fibo.asm con JoJoP_IDE (Compilar .bin)"
        )
    words = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("//"):
            words.append(int(ln, 16))
    return words


def fib_sequence(n):
    a, b, out = 0, 1, []
    for _ in range(n):
        out.append(a)
        a, b = b, a + b
    return out


async def instruction_memory(dut, rom):
    while True:
        await FallingEdge(dut.clk)
        pc = int(dut.pc_out.value)
        dut.instruction_in.value = rom[pc] if pc < len(rom) else 0


@cocotb.test()
async def fibonacci_from_hex(dut):
    path = hex_path()
    rom = load_hex(path)
    dut._log.info(f"programa: {path.name}  ({len(rom)} palabras)")
    for k, w in enumerate(rom):
        dut._log.info(f"ROM[{k}] = {w:04x}")

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(instruction_memory(dut, rom))
    dut.rst_n.value = 0
    dut.instruction_in.value = 0
    dut.mem_rdata.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    trace, outs = [], []
    for cyc in range(700):
        await RisingEdge(dut.clk)
        state = int(dut.debug_state.value)
        instr = int(dut.debug_instr.value)
        gpio = int(dut.gpio_out.value)
        trace.append(
            {
                "cycle": cyc,
                "pc": int(dut.pc_out.value),
                "state": state,
                "gpio": gpio,
                "regs": [0] + [int(dut.regs[i].value) for i in range(1, 8)],
            }
        )
        if state == 5 and (instr >> 13) == 0b110:
            outs.append({"cycle": cyc, "value": gpio})

    values = [o["value"] for o in outs]
    dut._log.info(f"OUT por GPIO ({len(values)}): {values}")

    assert len(values) == N_OUT, f"{len(values)} instrucciones OUT, esperadas {N_OUT}"
    assert values == fib_sequence(N_OUT), f"secuencia {values}"
    dut._log.info("secuencia 0 1 1 2 3 5 ... 233  OK")

    gaps = {b["cycle"] - a["cycle"] for a, b in zip(outs, outs[1:])}
    assert gaps == {LOOP_LEN * CPI}, f"ciclos entre OUT: {sorted(gaps)}"
    dut._log.info(f"{LOOP_LEN} instrucciones x {CPI} ciclos = {LOOP_LEN * CPI} ciclos por iteracion  OK")

    done = len(rom) - 1
    assert int(dut.pc_out.value) == done, f"PC final {int(dut.pc_out.value)}"
    assert int(dut.gpio_out.value) == 233
    dut._log.info(f"PC detenido en {done} (done), gpio_out = 233  OK")

    outdir = Path(os.environ.get("ZC_OUTDIR", ROOT / "build" / "cocotb"))
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "fibo_trace.json", "w", encoding="utf-8") as f:
        json.dump(
            {"hex": path.name, "rom": rom, "states": STATES, "trace": trace, "outs": outs},
            f,
        )
