import hashlib
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.aclk, 10, units="ns").start())


async def reset_dut(dut):
    dut.aresetn.value = 0
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.s_axis_tkeep.value = 0
    dut.s_axis_tlast.value = 0
    dut.m_axis_tready.value = 0
    for _ in range(5):
        await RisingEdge(dut.aclk)
    dut.aresetn.value = 1
    for _ in range(3):
        await RisingEdge(dut.aclk)


async def send_message(dut, msg, bubbles=False):
    n = len(msg)
    if n == 0:
        dut.s_axis_tdata.value = 0
        dut.s_axis_tkeep.value = 0
        dut.s_axis_tlast.value = 1
        dut.s_axis_tvalid.value = 1
        while True:
            await RisingEdge(dut.aclk)
            if int(dut.s_axis_tready.value) == 1:
                break
        dut.s_axis_tvalid.value = 0
        dut.s_axis_tlast.value = 0
        return

    num_words = (n + 3) // 4
    for w in range(num_words):
        word = 0
        keep = 0
        for b in range(4):
            i = w * 4 + b
            if i < n:
                word |= msg[i] << (24 - 8 * b)
                keep |= 1 << (3 - b)

        if bubbles and random.random() < 0.3:
            dut.s_axis_tvalid.value = 0
            for _ in range(random.randint(1, 3)):
                await RisingEdge(dut.aclk)

        dut.s_axis_tdata.value = word
        dut.s_axis_tkeep.value = keep
        dut.s_axis_tlast.value = 1 if w == num_words - 1 else 0
        dut.s_axis_tvalid.value = 1
        while True:
            await RisingEdge(dut.aclk)
            if int(dut.s_axis_tready.value) == 1:
                break

    dut.s_axis_tvalid.value = 0
    dut.s_axis_tlast.value = 0
    dut.s_axis_tkeep.value = 0


async def recv_digest(dut, backpressure=False):
    words = []
    dut.m_axis_tready.value = 1
    while len(words) < 8:
        await RisingEdge(dut.aclk)
        if int(dut.m_axis_tvalid.value) == 1 and int(dut.m_axis_tready.value) == 1:
            words.append(int(dut.m_axis_tdata.value))
            if backpressure and len(words) in (2, 5):
                dut.m_axis_tready.value = 0
                for _ in range(random.randint(2, 5)):
                    await RisingEdge(dut.aclk)
                dut.m_axis_tready.value = 1
    dut.m_axis_tready.value = 0
    return b"".join(x.to_bytes(4, "big") for x in words)


async def run_case(dut, msg, bubbles=False, backpressure=False):
    sink = cocotb.start_soon(recv_digest(dut, backpressure))
    await send_message(dut, msg, bubbles)
    got = await sink
    exp = hashlib.sha256(bytes(msg)).digest()
    assert got == exp, (
        f"digest mismatch for {len(msg)}-byte message\n"
        f"  expected {exp.hex()}\n  got      {got.hex()}"
    )
    for _ in range(4):
        await RisingEdge(dut.aclk)


KNOWN = [
    b"",
    b"abc",
    b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
    b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno"
    b"ijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
    bytes(range(256)),
    b"a" * 1000000,
]


@cocotb.test()
async def test_known_vectors(dut):
    await start_clock(dut)
    await reset_dut(dut)
    for msg in KNOWN:
        await run_case(dut, msg)


@cocotb.test()
async def test_boundary_lengths(dut):
    await start_clock(dut)
    await reset_dut(dut)
    for n in [1, 2, 3, 4, 5, 31, 32, 33, 54, 55, 56, 57, 63, 64, 65,
              111, 112, 113, 119, 120, 121, 127, 128, 200, 255, 256, 257]:
        msg = bytes((i * 7 + 3) & 0xFF for i in range(n))
        await run_case(dut, msg)


@cocotb.test()
async def test_random(dut):
    await start_clock(dut)
    await reset_dut(dut)
    rng = random.Random(0xC0FFEE)
    for _ in range(40):
        n = rng.randint(0, 300)
        msg = bytes(rng.randrange(256) for _ in range(n))
        await run_case(dut, msg)


@cocotb.test()
async def test_ingress_bubbles(dut):
    await start_clock(dut)
    await reset_dut(dut)
    rng = random.Random(1)
    random.seed(1)
    for _ in range(15):
        n = rng.randint(1, 200)
        msg = bytes(rng.randrange(256) for _ in range(n))
        await run_case(dut, msg, bubbles=True)


@cocotb.test()
async def test_egress_backpressure(dut):
    await start_clock(dut)
    await reset_dut(dut)
    rng = random.Random(2)
    random.seed(2)
    for _ in range(15):
        n = rng.randint(1, 200)
        msg = bytes(rng.randrange(256) for _ in range(n))
        await run_case(dut, msg, backpressure=True)
