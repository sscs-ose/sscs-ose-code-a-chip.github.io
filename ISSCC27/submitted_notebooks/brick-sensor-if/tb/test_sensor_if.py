"""cocotb tests for brick_sensor_if (SPI master + CAN framer)."""
import os
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


async def wait_sticky(dut, mask, timeout_us=5000):
    for _ in range(timeout_us):
        s = await read_reg(dut, 0x1)
        if s & mask:
            return s
        await Timer(1, unit="us")
    raise AssertionError(f"timeout waiting for status bits {mask:#x}")


@cocotb.test()
async def test_spi_loopback(dut):
    """8-byte loopback: MISO tied to MOSI, RX buffer must equal TX buffer."""
    await reset_dut(dut)
    pattern = [0xA5, 0x3C, 0xF0, 0x0F, 0x55, 0xAA, 0x12, 0x34]
    for i, b in enumerate(pattern):
        await write_reg(dut, 0x8 + i, b)
    await write_reg(dut, 0x2, 4)   # clkdiv -> SCLK = 100MHz/(2*5) = 10 MHz
    await write_reg(dut, 0x3, 8)   # 8 bytes
    await write_reg(dut, 0x0, 0x01)  # start SPI
    s = await read_reg(dut, 0x1)
    assert s & 0x01, "spi_busy should assert right after start"
    await wait_sticky(dut, 0x04)
    for i, b in enumerate(pattern):
        got = await read_reg(dut, 0x8 + i)
        assert got == b, f"byte {i}: got {got:#x}, want {b:#x}"
    # W1C clear
    await write_reg(dut, 0x1, 0x04)
    assert await read_reg(dut, 0x1) & 0x04 == 0


@cocotb.test()
async def test_spi_short_len(dut):
    """3-byte transfer only shifts 3 bytes; CS deasserts afterwards."""
    await reset_dut(dut)
    for i in range(8):
        await write_reg(dut, 0x8 + i, 0x10 + i)
    await write_reg(dut, 0x2, 2)
    await write_reg(dut, 0x3, 3)
    await write_reg(dut, 0x0, 0x01)
    await wait_sticky(dut, 0x04)
    assert int(dut.spi_cs_n_o.value) == 1, "CS_N should be high after transfer"
    for i in range(3):
        assert await read_reg(dut, 0x8 + i) == 0x10 + i


@cocotb.test()
async def test_can_frame_basic(dut):
    """Capture the TX bitstream and compare against the Python golden model."""
    await reset_dut(dut)
    can_id, dlc = 0x2A5, 8
    data = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
    bitdiv = 9  # 100 ns per CAN bit
    await write_reg(dut, 0x4, can_id & 0xFF)
    await write_reg(dut, 0x5, (can_id >> 8) & 0x7)
    await write_reg(dut, 0x6, dlc)
    await write_reg(dut, 0x7, bitdiv)
    for i, b in enumerate(data):
        await write_reg(dut, 0x8 + i, b)
    expected = build_can_frame(can_id, dlc, data)

    await write_reg(dut, 0x0, 0x02)  # start CAN
    s = await read_reg(dut, 0x1)
    assert s & 0x02, "can_busy should assert right after start"

    await FallingEdge(dut.can_tx_o)  # SOF
    got = []
    for i in range(len(expected)):
        await Timer(50 if i == 0 else 100, unit="ns")  # mid-bit sample
        got.append(int(dut.can_tx_o.value))
    assert got == expected, (
        "bitstream mismatch at " +
        ", ".join(str(i) for i, (a, b) in enumerate(zip(got, expected)) if a != b)
    )
    await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_can_frame_stuffing(dut):
    """Worst-case stuffing pattern (0xFF bytes, max ID) must still match."""
    await reset_dut(dut)
    can_id, dlc = 0x7FF, 8
    data = [0xFF] * 8
    bitdiv = 4  # 50 ns per CAN bit
    await write_reg(dut, 0x4, can_id & 0xFF)
    await write_reg(dut, 0x5, (can_id >> 8) & 0x7)
    await write_reg(dut, 0x6, dlc)
    await write_reg(dut, 0x7, bitdiv)
    for i, b in enumerate(data):
        await write_reg(dut, 0x8 + i, b)
    expected = build_can_frame(can_id, dlc, data)
    assert len(expected) > 34 + 8 * dlc + 13, "test pattern should force stuff bits"

    await write_reg(dut, 0x0, 0x02)
    await FallingEdge(dut.can_tx_o)
    got = []
    for i in range(len(expected)):
        await Timer(25 if i == 0 else 50, unit="ns")
        got.append(int(dut.can_tx_o.value))
    assert got == expected
    await wait_sticky(dut, 0x08)


@cocotb.test()
async def test_can_short_dlc(dut):
    """DLC=2 frame: shorter payload, correct CRC over fewer bytes."""
    await reset_dut(dut)
    can_id, dlc = 0x100, 2
    data = [0xDE, 0xAD]
    bitdiv = 9
    await write_reg(dut, 0x4, can_id & 0xFF)
    await write_reg(dut, 0x5, (can_id >> 8) & 0x7)
    await write_reg(dut, 0x6, dlc)
    await write_reg(dut, 0x7, bitdiv)
    for i, b in enumerate(data):
        await write_reg(dut, 0x8 + i, b)
    expected = build_can_frame(can_id, dlc, data)
    await write_reg(dut, 0x0, 0x02)
    await FallingEdge(dut.can_tx_o)
    got = []
    for i in range(len(expected)):
        await Timer(50 if i == 0 else 100, unit="ns")
        got.append(int(dut.can_tx_o.value))
    assert got == expected
    await wait_sticky(dut, 0x08)
