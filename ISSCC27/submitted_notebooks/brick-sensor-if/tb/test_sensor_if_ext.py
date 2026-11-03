"""Extended cocotb tests: randomized + edge cases for brick_sensor_if."""
import os
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "golden"))

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from can_golden import build_can_frame

CLK_NS = 10


async def write_reg(dut, addr, data):
    dut.addr.value = addr
    dut.wdata.value = data
    dut.we.value = 1
    await RisingEdge(dut.clk)
    dut.we.value = 0
    await RisingEdge(dut.clk)


async def read_reg(dut, addr):
    dut.addr.value = addr
    dut.re.value = 1
    await RisingEdge(dut.clk)
    dut.re.value = 0
    await Timer(1, unit="ns")
    return int(dut.rdata.value)


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.we.value = 0
    dut.re.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    await Timer(50, unit="ns")


async def wait_sticky(dut, mask, timeout_us=20000):
    for _ in range(timeout_us):
        s = await read_reg(dut, 0x1)
        if s & mask:
            return s
        await Timer(1, unit="us")
    raise AssertionError(f"timeout waiting for status bits {mask:#x}")


async def prog_can(dut, can_id, dlc, data, bitdiv=9):
    await write_reg(dut, 0x4, can_id & 0xFF)
    await write_reg(dut, 0x5, (can_id >> 8) & 0x7)
    await write_reg(dut, 0x6, dlc)
    await write_reg(dut, 0x7, bitdiv)
    for i, b in enumerate(data):
        await write_reg(dut, 0x8 + i, b)


async def capture_can(dut, nbits, half_bit_ns):
    """Sample can_tx_o mid-bit, starting from the SOF falling edge."""
    await FallingEdge(dut.can_tx_o)  # SOF
    got = []
    for i in range(nbits):
        await Timer(half_bit_ns if i == 0 else 2 * half_bit_ns, unit="ns")
        got.append(int(dut.can_tx_o.value))
    return got


@cocotb.test()
async def test_can_randomized(dut):
    """40 seeded-random frames vs the Python golden model."""
    await reset_dut(dut)
    rng = random.Random(0xC0DE)
    await write_reg(dut, 0x7, 4)  # bitdiv=4 -> 50 ns/bit
    for trial in range(40):
        can_id = rng.randrange(0, 2048)
        dlc = rng.randrange(0, 9)
        data = [rng.randrange(0, 256) for _ in range(dlc)]
        await prog_can(dut, can_id, dlc, data, bitdiv=4)
        expected = build_can_frame(can_id, dlc, data)
        await write_reg(dut, 0x1, 0x0C)  # clear stickies
        await write_reg(dut, 0x0, 0x02)  # start CAN
        got = await capture_can(dut, len(expected), 25)
        assert got == expected, f"trial {trial}: id={can_id:#x} dlc={dlc} mismatch"
        await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_can_dlc_sweep(dut):
    """DLC 0..8, including the empty-payload frame."""
    await reset_dut(dut)
    rng = random.Random(7)
    for dlc in range(9):
        data = [rng.randrange(0, 256) for _ in range(dlc)]
        await prog_can(dut, 0x123, dlc, data, bitdiv=9)
        expected = build_can_frame(0x123, dlc, data)
        await write_reg(dut, 0x1, 0x0C)
        await write_reg(dut, 0x0, 0x02)
        got = await capture_can(dut, len(expected), 50)
        assert got == expected, f"DLC={dlc} mismatch"
        await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_can_id_edges(dut):
    """ID 0x000 (all-dominant) and 0x7FF (all-recessive) extremes."""
    await reset_dut(dut)
    for can_id in (0x000, 0x7FF):
        data = [0x00, 0xFF, 0x55, 0xAA]
        await prog_can(dut, can_id, 4, data, bitdiv=9)
        expected = build_can_frame(can_id, 4, data)
        await write_reg(dut, 0x1, 0x0C)
        await write_reg(dut, 0x0, 0x02)
        got = await capture_can(dut, len(expected), 50)
        assert got == expected, f"ID={can_id:#x} mismatch"
        await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_can_dlc_clamp(dut):
    """DLC=15 programmed -> framer clamps to 8 data bytes."""
    await reset_dut(dut)
    data = [0x10 + i for i in range(8)]
    await prog_can(dut, 0x200, 15, data, bitdiv=9)
    expected = build_can_frame(0x200, 8, data)
    await write_reg(dut, 0x0, 0x02)
    got = await capture_can(dut, len(expected), 50)
    assert got == expected, "DLC clamp mismatch"
    await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_spi_len_sweep(dut):
    """Loopback for every length 1..8, plus len=0 clamped to 8."""
    await reset_dut(dut)
    await write_reg(dut, 0x2, 2)
    for length in list(range(1, 9)) + [0]:
        want_len = 8 if length == 0 else length
        pattern = [(0x30 + length + i) & 0xFF for i in range(8)]
        for i, b in enumerate(pattern):
            await write_reg(dut, 0x8 + i, b)
        await write_reg(dut, 0x3, length)
        await write_reg(dut, 0x1, 0x04)
        await write_reg(dut, 0x0, 0x01)
        await wait_sticky(dut, 0x04)
        for i in range(want_len):
            got = await read_reg(dut, 0x8 + i)
            assert got == pattern[i], f"len={length} byte {i}: {got:#x} != {pattern[i]:#x}"


@cocotb.test()
async def test_busy_reject(dut):
    """A start pulse while busy must be ignored (no restart, no hang)."""
    await reset_dut(dut)
    for i in range(8):
        await write_reg(dut, 0x8 + i, i)
    await write_reg(dut, 0x2, 9)   # slow SPI so busy lasts a while
    await write_reg(dut, 0x3, 8)
    await write_reg(dut, 0x0, 0x01)
    await Timer(500, unit="ns")
    assert await read_reg(dut, 0x1) & 0x01, "SPI should still be busy"
    await write_reg(dut, 0x0, 0x01)  # ignored: busy
    await wait_sticky(dut, 0x04)
    # exactly one transfer happened: loopback data intact
    for i in range(8):
        assert await read_reg(dut, 0x8 + i) == i

    # same for CAN
    await prog_can(dut, 0x100, 8, [0xAA] * 8, bitdiv=49)  # slow CAN
    await write_reg(dut, 0x0, 0x02)
    await Timer(2, unit="us")
    assert await read_reg(dut, 0x1) & 0x02, "CAN should still be busy"
    await write_reg(dut, 0x0, 0x02)  # ignored: busy
    await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_reset_mid_transfer(dut):
    """Async reset mid-SPI and mid-CAN: busy clears, block recovers."""
    await reset_dut(dut)
    for i in range(8):
        await write_reg(dut, 0x8 + i, 0xA5)
    await write_reg(dut, 0x2, 49)
    await write_reg(dut, 0x3, 8)
    await write_reg(dut, 0x0, 0x01)
    await Timer(1, unit="us")
    assert await read_reg(dut, 0x1) & 0x01
    dut.rst_n.value = 0
    await Timer(100, unit="ns")
    dut.rst_n.value = 1
    await Timer(100, unit="ns")
    s = await read_reg(dut, 0x1)
    assert s & 0x03 == 0, f"busy bits should clear after reset, got {s:#x}"
    assert int(dut.spi_cs_n_o.value) == 1, "CS_N should idle high after reset"
    assert int(dut.can_tx_o.value) == 1, "CAN TX should idle recessive after reset"
    # and the block still works afterwards
    for i in range(8):
        await write_reg(dut, 0x8 + i, 0x3C)
    await write_reg(dut, 0x2, 2)
    await write_reg(dut, 0x0, 0x01)
    await wait_sticky(dut, 0x04)
    assert await read_reg(dut, 0x8) == 0x3C


@cocotb.test()
async def test_back_to_back(dut):
    """SPI read then CAN transmit then SPI again, no idle gaps needed."""
    await reset_dut(dut)
    await write_reg(dut, 0x2, 2)
    await write_reg(dut, 0x3, 8)
    # round 1: SPI loopback fills dbuf
    for i in range(8):
        await write_reg(dut, 0x8 + i, 0xC0 + i)
    await write_reg(dut, 0x0, 0x01)
    await wait_sticky(dut, 0x04)
    # round 2: immediately transmit dbuf over CAN
    await prog_can(dut, 0x321, 8, [], bitdiv=4)  # config regs only; dbuf kept
    expected = build_can_frame(0x321, 8, [0xC0 + i for i in range(8)])
    await write_reg(dut, 0x1, 0x0C)
    await write_reg(dut, 0x0, 0x02)
    got = await capture_can(dut, len(expected), 25)
    assert got == expected
    await wait_sticky(dut, 0x08)
    # round 3: SPI again right away
    await write_reg(dut, 0x0, 0x01)
    await wait_sticky(dut, 0x04)
    for i in range(8):
        assert await read_reg(dut, 0x8 + i) == 0xC0 + i
