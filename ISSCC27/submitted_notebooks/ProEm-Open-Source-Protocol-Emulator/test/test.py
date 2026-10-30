# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: test/test.py
# Type: Test, pin level (cocotb, runs on RTL and on the gate-level netlist)
# Device under test: tt_um_vertrex_star_proem (src/top/tt_um_vertrex_star_proem.sv)
# Author: Paul Vincent Bezzina
# Language: Python (cocotb)
# Description:
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

INS_R = 8
SYNC, ASYNC, GENERATE, RECOVER = 0, 1, 2, 3


class Link:
    def __init__(self, dut, channel=0):
        self.dut = dut
        self.channel = channel
        self.got = [[], []]
        self.status = [[], []]
        self.events = []

    def op(self, code, n=0):
        return (code << 4) | (self.channel << 3) | (n & 7)

    def start(self, val, cyc, cap, wr, pin=0):
        return [self.op(1), (wr << 7) | (cap << 6) | (cyc & 15), pin & 7, val & 0xFF]

    def hdr(self, n, val, cyc, cap, wr, grp=0, sr=0, any_value=0):
        return [self.op(2, n), (wr << 7) | (cap << 6) | (grp << 4) | (cyc & 15), (sr << 7) | (any_value << 6), val & 0xFF]

    def branch(self, rule, hit, miss, src, block, mask, value):
        return [self.op(0xF, rule), (hit << 6) | (miss << 4) | (src << 3) | (block & 7), mask & 0xFF, value & 0xFF]

    def main(self, bits, direction, we=0, ack=0, pin=0, sr=0):
        return [self.op(3), (direction << 6) | (we << 5) | (ack << 4) | (sr << 3) | (pin & 7), (bits >> 8) & 0xFF, bits & 0xFF]

    def order(self, msb):
        return [self.op(6, msb)]

    def run(self, mode=0):
        return [self.op(7, mode)]

    def line(self, code, pin_a, stuff=0, pin_b=0, inv=0, sany=0):
        v = (code << 13) | (inv << 12) | ((pin_a & 7) << 8) | (sany << 7) | ((stuff & 15) << 3) | (pin_b & 7)
        return [self.op(0xA), (v >> 8) & 0xFF, v & 0xFF]

    def clock(self, src, div, pin=0, edge=0, idle=0, etk=0):
        v = (src << 30) | (edge << 28) | (idle << 27) | ((pin & 7) << 24) | (etk << 22) | (div & 0xFFFF)
        return [self.op(0xB), (v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF]

    def out(self, drive, idle=0, pair=0, eop=0, i2c=0, cshigh=0):
        return [self.op(0xD), (drive << 6) | (idle << 5) | (pair << 4) | (eop << 3) | (i2c << 2) | (cshigh << 1)]

    def data(self, length, val):
        return [self.op(0xC, length - 1), val & 0xFF]

    async def send_byte(self, b):
        bits = [0] + [(b >> i) & 1 for i in range(8)] + [1, 1]
        for level in bits:
            self.dut.ui_in.value = level
            await ClockCycles(self.dut.clk, INS_R)

    async def send(self, program):
        for b in program:
            await self.send_byte(b)
        await ClockCycles(self.dut.clk, 8)

    async def monitor(self):
        state = 0
        count = 0
        bit = 0
        value = 0
        pending = []
        while True:
            await RisingEdge(self.dut.clk)
            try:
                level = int(self.dut.uo_out.value) & 1
            except ValueError:
                continue
            if state == 0:
                if not level:
                    state = 1
                    count = INS_R // 2
                continue
            count -= 1
            if count > 0:
                continue
            if state == 1:
                if level:
                    state = 0
                else:
                    state = 2
                    bit = 0
                    value = 0
                    count = INS_R
            elif state == 2:
                value |= level << bit
                bit += 1
                count = INS_R
                if bit == 8:
                    state = 3
            else:
                state = 0
                pending.append(value)
                if len(pending) == 2:
                    head, val = pending
                    pending = []
                    if (head & 0xC0) == 0xC0:
                        self.events.append(val)
                    else:
                        c = (head >> 5) & 1
                        length = head & 15
                        if length == 15:
                            self.status[c].append(val)
                        else:
                            self.got[c].append((length, val))

    async def quiet(self, limit=200000):
        idle = 0
        for _ in range(limit):
            await RisingEdge(self.dut.clk)
            try:
                level = int(self.dut.uo_out.value) & 1
            except ValueError:
                level = 1
            idle = idle + 1 if level else 0
            if idle > 30 * INS_R:
                return


async def power_on(dut):
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 1
    dut.ext_in.value = 0xFF
    dut.loop_uart.value = 0
    dut.loop_select.value = 0
    dut.i2c_bridge.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 20)
    link = Link(dut)
    cocotb.start_soon(link.monitor())
    await link.send_byte(0x55)
    await ClockCycles(dut.clk, 8)
    return link


@cocotb.test()
async def test_autobaud_and_errors(dut):
    link = await power_on(dut)
    assert (int(dut.uo_out.value) >> 1) & 1 == 1, "BAUD_LOCKED did not go high after 0x55"
    assert int(dut.uio_oe.value) == 0, "outputs must be off after reset"
    await link.send([0xF7, 0, 0, 0])
    await link.quiet()
    dut._log.info(f"link events {link.events}")
    assert link.events and (link.events[0] & 2), f"an invalid BRANCH index (7) should give cmd_error, got {link.events}"


@cocotb.test()
async def test_uart_loopback(dut):
    link = await power_on(dut)
    dut.loop_uart.value = 1
    r = 16
    link.channel = 0
    await link.send(link.line(0, 0) + link.clock(ASYNC, r) + link.start(0x00, 1, 0, 0, 0) + link.main(9, 0) + link.run(0))
    link.channel = 1
    program = link.line(0, 0) + link.clock(ASYNC, r) + link.out(3, 1) + link.start(0x00, 1, 0, 1) + link.main(9, 1)
    for ch in b"Hi!":
        program += link.data(8, ch) + link.data(1, 1)
    await link.send(program + link.run(0))
    assert (int(dut.uio_oe.value) >> 3) & 1 == 1, "B_DATA should be driven"
    await ClockCycles(dut.clk, 3 * 10 * r + 200)
    await link.quiet()
    dut._log.info(f"A read {link.got[0]}, status A {link.status[0]}, B {link.status[1]}")
    expected = []
    for ch in b"Hi!":
        expected += [(8, ch), (1, 1)]
    assert link.got[0] == expected, f"channel A read {link.got[0]}"
    assert link.status[0] == [1, 1, 1], f"channel A status {link.status[0]}"
    assert link.status[1] == [1, 1, 1], f"channel B status {link.status[1]}"


@cocotb.test()
async def test_spi_loopback(dut):
    link = await power_on(dut)
    dut.loop_select.value = 1
    link.channel = 1
    await link.send(link.order(1) + link.line(0, 0) + link.clock(SYNC, 0, 2, 0) + link.start(0, 0, 0, 0, 6) + link.main(16, 0, 0, 0, 0) + link.run(0))
    link.channel = 0
    await link.send(link.order(1) + link.line(0, 0) + link.clock(GENERATE, 4, 2, 0, 0) + link.out(3, 0) + link.start(0, 0, 0, 1) + link.main(16, 1) + link.data(8, 0xA5) + link.data(8, 0x3C) + link.run(0))
    await ClockCycles(dut.clk, 400)
    await link.quiet()
    dut._log.info(f"B read {link.got[1]}, status A {link.status[0]}, B {link.status[1]}")
    assert link.got[1] == [(8, 0xA5), (8, 0x3C)], f"channel B read {link.got[1]}"
    assert link.status[0] == [1], f"channel A status {link.status[0]}"
    assert link.status[1] == [1], f"channel B status {link.status[1]}"


@cocotb.test()
async def test_i2c_target_loopback(dut):
    link = await power_on(dut)
    dut.i2c_bridge.value = 1
    link.channel = 1
    await link.send(link.order(1) + link.line(0, 0) + link.clock(SYNC, 0, 2, 0) + link.out(2, 0, 0, 0, 1) + link.start(0, 0, 0, 0)
                    + link.hdr(1, 0x42, 7, 0, 0) + link.hdr(2, 0, 1, 1, 0, 0, 0, 1) + link.hdr(3, 0, 1, 0, 1)
                    + link.branch(0, 2, 1, 0, 2, 0x01, 0x01) + link.main(64, 2, 1, 1, 0) + link.run(0))
    link.channel = 0
    await link.send(link.order(1) + link.line(0, 0) + link.clock(GENERATE, 60, 2, 0, 1) + link.out(2, 1, 0, 0, 1)
                    + link.start(0x84, 8, 0, 1) + link.hdr(1, 0, 1, 0, 0) + link.main(16, 1, 0, 1)
                    + link.data(8, 0x11) + link.data(8, 0x22) + link.run(2))
    await ClockCycles(dut.clk, 6000)
    await link.quiet()
    dut._log.info(f"target read {link.got[1]}, status A {link.status[0]}, B {link.status[1]}")
    assert link.got[1] == [(1, 0), (8, 0x11), (8, 0x22)], f"target read {link.got[1]}"
    assert link.status[0] == [1], f"controller status {link.status[0]}"
    assert link.status[1] == [1], f"target status {link.status[1]}"


import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "host"))
import proem_host as ph


async def uart_receiver(dut, pin, clocks_per_bit, heard):
    while True:
        await RisingEdge(dut.clk)
        line_level = (int(dut.uio_out.value) >> pin) & 1 if (int(dut.uio_oe.value) >> pin) & 1 else 1
        if line_level == 0:
            await ClockCycles(dut.clk, clocks_per_bit // 2)
            value = 0
            for i in range(8):
                await ClockCycles(dut.clk, clocks_per_bit)
                value |= ((int(dut.uio_out.value) >> pin) & 1) << i
            await ClockCycles(dut.clk, clocks_per_bit)
            if (int(dut.uio_out.value) >> pin) & 1:
                heard.append(value)


@cocotb.test()
async def test_send_uart_A0000(dut):
    link = await power_on(dut)
    baud = 115200
    message = b"A0000"
    first, rest = ph.uart_tx(0, baud, message)
    dut._log.info("first batch: " + " ".join(f"{b:02X}" for b in first))
    dut._log.info("then:        " + " ".join(f"{b:02X}" for b in rest))
    heard = []
    cocotb.start_soon(uart_receiver(dut, 0, ph.uart_divider(baud), heard))
    await link.send(first)
    await link.send(rest)
    await ClockCycles(dut.clk, len(message) * 10 * ph.uart_divider(baud) + 2000)
    await link.quiet()
    dut._log.info(f"receiver on uio[0] heard {bytes(heard)}, status {link.status[0]}")
    assert bytes(heard) == message
    assert link.status[0] == [1] * len(message)


@cocotb.test()
async def test_crc_append_and_check(dut):
    link = await power_on(dut)
    dut.loop_uart.value = 1
    r = 16
    payload = [0x31, 0xC5]
    bits = [(b >> k) & 1 for b in payload for k in range(8)]
    crc = ph.crc_wire(bits, 8, 0x07)
    crc_byte = sum(((crc >> (7 - k)) & 1) << k for k in range(8))
    for residue, good in ((0x00, 1), (0x5A, 0)):
        link.got = [[], []]
        link.status = [[], []]
        link.channel = 0
        await link.send(link.line(0, 0) + link.clock(ASYNC, r) + link.start(0x00, 1, 0, 0, 0) + link.main(24, 0)
                        + ph.crc_a(0, 8, 0x07) + ph.crc_b(0, check=1, residue=residue) + link.run(0))
        link.channel = 1
        await link.send(link.line(0, 0) + link.clock(ASYNC, r) + link.out(3, 1) + link.start(0x00, 1, 0, 1) + link.main(16, 1)
                        + ph.crc_a(1, 8, 0x07) + ph.crc_b(1, append=1) + link.data(8, payload[0]) + link.data(8, payload[1]) + link.run(2))
        await ClockCycles(dut.clk, 30 * r + 200)
        await link.quiet()
        dut._log.info(f"A read {link.got[0]}, status A {link.status[0]}, B {link.status[1]}")
        assert link.got[0] == [(8, payload[0]), (8, payload[1]), (8, crc_byte), (14, 2 | good)], f"channel A read {link.got[0]}"
        assert link.status[0] == [1], f"channel A status {link.status[0]}"
        assert link.status[1] == [1], f"channel B status {link.status[1]}"
