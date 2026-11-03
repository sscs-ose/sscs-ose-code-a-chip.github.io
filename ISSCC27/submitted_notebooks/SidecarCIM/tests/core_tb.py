"""Shared cocotb testbench for cores with the dcim_core port/handshake
(rtl/dcim_core.v, rtl/mac_baseline.v), checked against python/golden.py.

Test modules call configure(latency) and wrap the async functions below
in @cocotb.test. latency = edges from the start edge k until valid=1.
Vectors come from python/vectors/*.npz; expected values are recomputed
with golden.dcim_dot and the stored y is checked against golden too.
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
import golden  # noqa: E402

SPEC = golden.SPEC
N_IN = SPEC["array"]["n_inputs"]
N_OUT = SPEC["array"]["n_outputs"]
# Widths: DCIM_WBITS / DCIM_ABITS (set by tests/Makefile together with the
# matching -P overrides), else the spec dense widths; configure() can
# override again. setup() checks them against the DUT port widths.
WBITS = int(os.environ.get("DCIM_WBITS") or SPEC["dense"]["weight_bits"])
ABITS = int(os.environ.get("DCIM_ABITS") or SPEC["dense"]["act_bits"])
# Vector family (e.g. "w8a4_"): bulk sets and the protocol-test cases.
VEC_PREFIX = os.environ.get("DCIM_VEC_PREFIX", "")
VEC = ROOT / "python" / "vectors"
VARIANT = os.environ.get("DCIM_VARIANT", "default")
CLK_NS = 20  # spec flow.clock_period_ns
VCD_RUN = os.environ.get("DCIM_VCD") is not None
VCD_CASES = 100
EDGE_CHECK_MAX = 8   # bulk runs check every edge up to this latency
LAT = None           # set by configure()
XBIT = False         # check the dcim_core xbit bit-plane tap


def _clog2(v):
    return (int(v) - 1).bit_length()


YW = _clog2(N_IN * (2**WBITS - 1) * (2**ABITS - 1) + 1)


def configure(latency, wbits=None, abits=None, xbit=False):
    """latency: start edge k -> valid after edge k+latency.
    wbits/abits: override spec dense bits (e.g. dcim_8bit).
    xbit: check xbit = bit ABITS-1-n of x before edge k+1+n."""
    global LAT, WBITS, ABITS, YW, XBIT
    LAT = int(latency)
    if wbits is not None:
        WBITS = int(wbits)
    if abits is not None:
        ABITS = int(abits)
    YW = _clog2(N_IN * (2**WBITS - 1) * (2**ABITS - 1) + 1)
    XBIT = bool(xbit)


def random_limit():
    lim = os.environ.get("DCIM_RANDOM_LIMIT")
    return int(lim) if lim else None


# ---------- helpers ----------

def pack_rows(w):
    """(N_IN, N_OUT) -> list of N_IN load_row ints (column 0 in LSBs)."""
    return [sum(int(w[i, j]) << (j * WBITS) for j in range(N_OUT))
            for i in range(N_IN)]


def pack_x(x):
    return sum(int(x[i]) << (i * ABITS) for i in range(N_IN))


def unpack_y(v):
    m = (1 << YW) - 1
    return [(v >> (j * YW)) & m for j in range(N_OUT)]


def gold(w, x):
    return [int(v) for v in golden.dcim_dot(w, x, WBITS, ABITS)]


def load_set(name):
    d = np.load(VEC / f"{name}.npz")
    w, x, y = d["w"], d["x"], d["y"]
    g = np.stack([golden.dcim_dot(w[c], x[c], WBITS, ABITS)
                  for c in range(len(w))])
    bad = np.flatnonzero(np.any(g != y, axis=1))
    assert bad.size == 0, (
        f"{name}.npz stored y disagrees with golden at case {bad[0]}")
    names = d["names"] if "names" in d.files else None
    return w, x, g, names


def _case(name, c):
    """Case c of VEC_PREFIX + name (protocol tests)."""
    d = np.load(VEC / f"{VEC_PREFIX}{name}.npz")
    w, x = d["w"][c], d["x"][c]
    return w, x, gold(w, x)


async def setup(dut):
    assert LAT is not None, "configure(latency) not called"
    assert len(dut.load_row) == N_OUT * WBITS
    assert len(dut.x_in) == N_IN * ABITS
    assert len(dut.y) == N_OUT * YW
    if os.environ.get("DCIM_WBITS"):       # env widths: also check the params
        for p, v in (("WBITS", WBITS), ("ABITS", ABITS)):
            assert int(getattr(dut, p).value) == v, f"{p} param != {v}"
    cocotb.start_soon(Clock(dut.clk, CLK_NS, "ns").start())
    dut.rst.value = 1
    dut.load_en.value = 0
    dut.load_addr.value = 0
    dut.load_row.value = 0
    dut.start.value = 0
    dut.x_in.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await ReadOnly()
    assert int(dut.busy.value) == 0 and int(dut.valid.value) == 0
    assert int(dut.y.value) == 0
    await FallingEdge(dut.clk)


async def load_weights(dut, rows, order=None):
    """Write rows; returns with load_en=0 driven (next edge is free)."""
    for i in (range(N_IN) if order is None else order):
        dut.load_en.value = 1
        dut.load_addr.value = int(i)
        dut.load_row.value = rows[i]
        await RisingEdge(dut.clk)
    dut.load_en.value = 0


async def _bv(dut):
    return int(dut.busy.value), int(dut.valid.value)


def xplane(xint, a):
    """Bit a of every x[i], packed as an N_IN-bit int (row 0 in LSB)."""
    p = 0
    for i in range(N_IN):
        p |= ((xint >> (i * ABITS + a)) & 1) << i
    return p


def _check_xbit(dut, xint, c, tag):
    """After edge k+c (c = 0..ABITS-1) xbit feeds edge k+1+c: bit ABITS-1-c."""
    a = ABITS - 1 - c
    got, exp = int(dut.xbit.value), xplane(xint, a)
    assert got == exp, (f"{tag} xbit after edge k+{c} (bit {a}): "
                        f"got {got:#0{N_IN // 4 + 2}x} exp {exp:#0{N_IN // 4 + 2}x}")


async def wait_valid(dut, per_edge, tag="", xint=None):
    """Called right after the start edge k (writes done). Checks busy=1,
    valid=0 after k+1..k+LAT-1 (every edge, or only k+LAT-1 when skipping
    ahead) and busy=0,valid=1 after k+LAT. If XBIT and xint is given,
    also checks xbit after edges k..k+ABITS-1 (per_edge only).
    Returns in ReadOnly after edge k+LAT."""
    chk = XBIT and xint is not None and per_edge
    if chk:
        await ReadOnly()
        _check_xbit(dut, xint, 0, tag)
    if per_edge:
        for c in range(1, LAT):
            await RisingEdge(dut.clk)
            await ReadOnly()
            b, v = await _bv(dut)
            assert (b, v) == (1, 0), f"{tag} edge k+{c}: busy={b} valid={v}"
            if chk and c < ABITS:
                _check_xbit(dut, xint, c, tag)
    else:
        # jump to mid high phase after edge k+LAT-1 (no edge race)
        await Timer((LAT - 1) * CLK_NS + CLK_NS // 4, "ns")
        b, v = await _bv(dut)
        assert (b, v) == (1, 0), f"{tag} edge k+{LAT - 1}: busy={b} valid={v}"
    await RisingEdge(dut.clk)
    await ReadOnly()
    b, v = await _bv(dut)
    assert (b, v) == (0, 1), f"{tag} edge k+{LAT}: busy={b} valid={v}"


async def run_dot(dut, xint, per_edge=None):
    """Start at the next edge k, check exact latency, return y after
    edge k+LAT, then step to the falling edge."""
    if per_edge is None:
        per_edge = LAT <= EDGE_CHECK_MAX
    dut.start.value = 1
    dut.x_in.value = xint
    await RisingEdge(dut.clk)           # edge k: start sampled
    dut.start.value = 0
    await wait_valid(dut, per_edge, xint=xint)
    yv = int(dut.y.value)
    await FallingEdge(dut.clk)
    return yv


def fmt_case(tag, c, w, x, exp, got):
    return (f"{tag} case {c}\n  x = {list(map(int, x))}\n"
            f"  w (rows) = {[list(map(int, r)) for r in w]}\n"
            f"  expected y = {list(map(int, exp))}\n  got y      = {got}")


async def run_set(dut, name, order_mode, limit=None):
    w, x, g, names = load_set(name)
    n = len(w) if limit is None else min(limit, len(w))
    await setup(dut)
    rng = np.random.default_rng(1234)
    fails, first, reloads = 0, None, 0
    prev = None
    t0 = time.time()
    for c in range(n):
        if prev is None or not np.array_equal(w[c], prev):
            if order_mode == "shuffle":
                order = rng.permutation(N_IN)
            elif order_mode == "reverse":
                order = range(N_IN - 1, -1, -1)
            else:
                order = None
            await load_weights(dut, pack_rows(w[c]), order)
            reloads += 1
            prev = w[c]
        got = unpack_y(await run_dot(dut, pack_x(x[c])))
        if got != [int(v) for v in g[c]]:
            fails += 1
            if first is None:
                tag = name + (f" [{names[c]}]" if names is not None else "")
                first = fmt_case(tag, c, w[c], x[c], g[c], got)
                dut._log.error("FIRST FAIL\n" + first)
    dt = time.time() - t0
    dut._log.info(
        f"SUMMARY {VARIANT} {name}: {n - fails}/{n} pass, {reloads} weight "
        f"loads ({order_mode} order), {dt:.1f} s wall, {n / dt:.1f} cases/s")
    assert fails == 0, f"{fails}/{n} mismatches; first:\n{first}"


# ---------- vector tests ----------

# prefix selects the vector family: "" (4-bit), "dense8_" (W8A8),
# "w8a4_" / "w6a4_" / "w7a4_" (dcim_core WBITS=8/6/7, ABITS=4),
# "w4a8_" (WBITS=4, ABITS=8)

async def corners(dut, prefix=""):
    """All corner cases, natural row order."""
    await run_set(dut, prefix + "corners", "natural")


async def random_10k(dut, prefix=""):
    """All 10,000 random cases (or DCIM_RANDOM_LIMIT), shuffled rows."""
    await run_set(dut, prefix + "random", "shuffle", random_limit())


async def real_layer(dut, prefix=""):
    """All 4,096 real GPT-2 layer cases (or DCIM_REAL_LIMIT), reverse
    row order."""
    lim = os.environ.get("DCIM_REAL_LIMIT")
    await run_set(dut, prefix + "real_layer", "reverse",
                  int(lim) if lim else None)


async def vcd_real_layer(dut, prefix=""):
    """First VCD_CASES real-layer cases, for the power VCD."""
    await run_set(dut, prefix + "real_layer", "natural", VCD_CASES)


# ---------- protocol tests (every edge checked) ----------

async def latency_and_hold(dut):
    """start->valid = LAT edges; y/valid hold in DONE while idle."""
    w, x, exp = _case("random", 0)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    assert unpack_y(await run_dot(dut, pack_x(x), per_edge=True)) == exp
    for _ in range(20):                    # idle in DONE, inputs wiggle
        dut.x_in.value = pack_x(x[::-1])
        dut.load_addr.value = 3
        dut.load_row.value = (1 << (N_OUT * WBITS)) - 1
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.valid.value) == 1 and int(dut.busy.value) == 0
        assert unpack_y(int(dut.y.value)) == exp
        await FallingEdge(dut.clk)


async def back_to_back(dut):
    """start held high: accepted every LAT+1 cycles from DONE."""
    xs_d = np.load(VEC / f"{VEC_PREFIX}random.npz")["x"][:8]
    w, _, _ = _case("random", 1)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    dut.start.value = 1
    dut.x_in.value = pack_x(xs_d[0])
    await RisingEdge(dut.clk)                  # first start edge
    for k in range(len(xs_d)):
        exp = gold(w, xs_d[k])
        dut.x_in.value = pack_x(xs_d[(k + 1) % len(xs_d)])  # ignored while busy
        await wait_valid(dut, True, f"dot {k}", xint=pack_x(xs_d[k]))
        assert unpack_y(int(dut.y.value)) == exp, f"back-to-back dot {k}"
        # next edge is the next accepted start (start still high, in DONE)
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.busy.value) == 1 and int(dut.y.value) == 0
        await FallingEdge(dut.clk)
    dut.start.value = 0


async def start_with_load_ignored(dut):
    """start=1 together with load_en=1 is ignored (in LOAD and in DONE)."""
    w, x, exp = _case("random", 2)
    rows = pack_rows(w)
    await setup(dut)
    dut.start.value = 1
    dut.x_in.value = pack_x(x)
    for i in range(N_IN):
        dut.load_en.value = 1
        dut.load_addr.value = i
        dut.load_row.value = rows[i]
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.busy.value) == 0 and int(dut.valid.value) == 0
        await FallingEdge(dut.clk)
    dut.load_en.value = 0
    dut.start.value = 0
    assert unpack_y(await run_dot(dut, pack_x(x), per_edge=True)) == exp
    # in DONE: start+load rewrites a row (same value), leaves DONE, no compute
    dut.start.value = 1
    dut.load_en.value = 1
    dut.load_addr.value = 5
    dut.load_row.value = rows[5]
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.busy.value) == 0 and int(dut.valid.value) == 0
    assert unpack_y(int(dut.y.value)) == exp, "y must keep value after load"
    await FallingEdge(dut.clk)
    dut.load_en.value = 0
    dut.start.value = 0
    assert unpack_y(await run_dot(dut, pack_x(x))) == exp


async def load_while_busy_ignored(dut):
    """load_en during COMPUTE (every edge, incl. last) changes no weight."""
    w, x, exp = _case("random", 3)
    w2, _, _ = _case("random", 4)
    junk = pack_rows(w2)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    dut.start.value = 1
    dut.x_in.value = pack_x(x)
    await RisingEdge(dut.clk)                  # start edge
    dut.start.value = 0
    for c in range(1, LAT + 1):
        dut.load_en.value = 1
        dut.load_addr.value = c % N_IN
        dut.load_row.value = junk[c % N_IN]
        await RisingEdge(dut.clk)
        await ReadOnly()
        await FallingEdge(dut.clk)
    dut.load_en.value = 0
    assert int(dut.valid.value) == 1
    assert unpack_y(int(dut.y.value)) == exp
    for xi in [x, np.full(N_IN, 2**ABITS - 1, dtype=np.uint8)]:
        assert unpack_y(await run_dot(dut, pack_x(xi))) == gold(w, xi)


async def start_while_busy_ignored(dut):
    """start held + new x_in during COMPUTE: no restart, same result."""
    w, x, exp = _case("random", 5)
    _, x2, _ = _case("random", 6)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    dut.start.value = 1
    dut.x_in.value = pack_x(x)
    await RisingEdge(dut.clk)
    dut.x_in.value = pack_x(x2)               # start stays high, new x
    await wait_valid(dut, True, xint=pack_x(x))
    assert unpack_y(int(dut.y.value)) == exp
    await FallingEdge(dut.clk)
    dut.start.value = 0


async def reset_mid_compute(dut):
    """rst during COMPUTE -> LOAD, busy=0, valid=0, y=0; then works again."""
    w, x, exp = _case("random", 7)
    w2, x2, exp2 = _case("random", 8)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    stops = sorted({1, LAT // 2, LAT - 1}) if LAT > 1 else []
    for stop in stops:                         # reset after `stop` edges
        dut.start.value = 1
        dut.x_in.value = pack_x(x)
        await RisingEdge(dut.clk)
        dut.start.value = 0
        for _ in range(stop):
            await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.busy.value) == 1
        await FallingEdge(dut.clk)
        dut.rst.value = 1
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.busy.value) == 0 and int(dut.valid.value) == 0
        assert int(dut.y.value) == 0
        await FallingEdge(dut.clk)
        dut.rst.value = 0
        # header: weights are NOT reset -> previous rows still hold
        assert unpack_y(await run_dot(dut, pack_x(x))) == exp, \
            f"after reset at edge k+{stop}"
    await load_weights(dut, pack_rows(w2))
    assert unpack_y(await run_dot(dut, pack_x(x2))) == exp2


async def full_scale(dut):
    """Directed: all-max w with all-max x and with x[i] = (37*i+5) mod 2^ABITS
    (every bit-plane exercised at any ABITS); expected from golden."""
    wmax = np.full((N_IN, N_OUT), 2**WBITS - 1, dtype=np.int64)
    xs = [np.full(N_IN, 2**ABITS - 1, dtype=np.int64),
          np.array([(37 * i + 5) % 2**ABITS for i in range(N_IN)])]
    w2 = np.array([[(11 * i + 7 * j + 3) % 2**WBITS for j in range(N_OUT)]
                   for i in range(N_IN)])
    await setup(dut)
    for w in (wmax, w2):
        await load_weights(dut, pack_rows(w))
        for x in xs:
            assert unpack_y(await run_dot(dut, pack_x(x))) == gold(w, x)


async def partial_reload(dut):
    """Rewriting one row in shuffled order between dots; others retained."""
    w, x, _ = _case("random", 9)
    w2, _, _ = _case("random", 10)
    await setup(dut)
    rng = np.random.default_rng(7)
    await load_weights(dut, pack_rows(w), rng.permutation(N_IN))
    cur = w.copy()
    for i in rng.permutation(N_IN)[:8]:
        cur[i] = w2[i]
        await load_weights(dut, pack_rows(cur), [i])
        assert unpack_y(await run_dot(dut, pack_x(x))) == gold(cur, x), \
            f"row {i}"


# ---------- directed: clock-gated storage (rtl/icg.v, CLK_GATE=1) ----------
# Storage is read back through the ports: x one-hot at row i (value 1)
# gives y[j] = w[i][j], so 32 dots return the whole weight array.

def _rand_w(rng):
    return rng.integers(0, 2**WBITS, (N_IN, N_OUT)).astype(np.int64)


def _differ(old, rng):
    """New values that differ from old in every entry."""
    return (old + rng.integers(1, 2**WBITS, old.shape)) % 2**WBITS


def _row(wr):
    return sum(int(wr[j]) << (j * WBITS) for j in range(N_OUT))


async def readback(dut):
    w = np.zeros((N_IN, N_OUT), dtype=np.int64)
    for i in range(N_IN):
        x = np.zeros(N_IN, dtype=np.int64)
        x[i] = 1
        w[i] = unpack_y(await run_dot(dut, pack_x(x)))
    return w


async def check_rows(dut, exp, tag):
    """Full readback == exp; reports the rows that differ."""
    got = await readback(dut)
    bad = sorted({int(i) for i in np.argwhere(got != exp)[:, 0]})
    assert not bad, (f"{tag}: rows {bad} differ; row {bad[0]} expected "
                     f"{exp[bad[0]].tolist()} got {got[bad[0]].tolist()}")


async def load_seq(dut, seq):
    """[(addr, row values)] one per edge, back to back; ends with
    load_en=0 driven (next edge free)."""
    for a, wr in seq:
        dut.load_en.value = 1
        dut.load_addr.value = int(a)
        dut.load_row.value = _row(wr)
        await RisingEdge(dut.clk)
    dut.load_en.value = 0


async def rst_edges(dut, n=1):
    """rst for n edges, driven from a falling edge (or right after the
    last load edge); checks idle and y=0; returns at a falling edge."""
    dut.rst.value = 1
    for _ in range(n):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert (int(dut.busy.value), int(dut.valid.value)) == (0, 0)
        assert int(dut.y.value) == 0
        await FallingEdge(dut.clk)
    dut.rst.value = 0


async def cg_rst_idle(dut):
    """rst with no load pending (in DONE and in LOAD, 1 and 3 edges):
    every row survives."""
    rng = np.random.default_rng(301)
    w = _rand_w(rng)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    await check_rows(dut, w, "after load")
    await rst_edges(dut, 1)                 # in DONE
    await check_rows(dut, w, "rst 1 edge in DONE")
    await rst_edges(dut, 3)
    await check_rows(dut, w, "rst 3 edges in DONE")
    await load_seq(dut, [(4, w[4])])        # same value -> state LOAD
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)               # idle edge, nothing pending
    await FallingEdge(dut.clk)
    await rst_edges(dut, 1)                 # in LOAD
    await check_rows(dut, w, "rst 1 edge in LOAD")


async def cg_load_before_rst(dut):
    """Header: a row whose load_en edge is the edge right before the rst
    edge is written. Single rows, all rows streamed up to rst, and a load
    on the first edge after rst."""
    rng = np.random.default_rng(302)
    w = _rand_w(rng)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    for r in [0, 13, N_IN - 1]:
        w[r] = _differ(w[r], rng)
        await load_seq(dut, [(r, w[r])])    # load_en edge e
        await rst_edges(dut, 1)             # rst edge e+1
        await check_rows(dut, w, f"row {r} loaded at the edge before rst")
    w2 = _rand_w(rng)
    await load_seq(dut, [(int(i), w2[i]) for i in rng.permutation(N_IN)])
    await rst_edges(dut, 1)
    await check_rows(dut, w2, "32 rows streamed up to the rst edge")
    w2[7] = _differ(w2[7], rng)
    w2[8] = _differ(w2[8], rng)
    await load_seq(dut, [(7, w2[7])])
    await rst_edges(dut, 2)
    await load_seq(dut, [(8, w2[8])])       # first edge after rst
    await check_rows(dut, w2, "load before rst + load after rst")


async def cg_single_row_write(dut):
    """Write row i (new value in every column); every other row must hold
    (a gated row must not be written by another row's write). All rows,
    shuffled, full readback after each write."""
    rng = np.random.default_rng(303)
    w = _rand_w(rng)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    await check_rows(dut, w, "initial")
    for i in rng.permutation(N_IN):
        w[i] = _differ(w[i], rng)
        await load_seq(dut, [(int(i), w[i])])
        await check_rows(dut, w, f"after write to row {int(i)}")


async def glitch(dut, sigs, phase):
    """Pulse signals to the given values and back to 0 inside one clock
    phase, so no edge sees them. Called at a falling edge; returns at the
    next falling edge."""
    q = max(1, CLK_NS // 6)
    if phase == "high":
        await RisingEdge(dut.clk)
    await Timer(q, "ns")
    for s, v in sigs:
        getattr(dut, s).value = v
    await Timer(q, "ns")
    for s, _ in sigs:
        getattr(dut, s).value = 0
    if phase == "low":
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)


async def cg_enable_glitch(dut):
    """load_en pulses that start and end inside one clock phase (high and
    low), for every row, with junk data: no edge sees load_en=1, so no
    row may change. A gate without its latch (clk & en) writes on a
    high-phase pulse when en comes combinationally from the ports."""
    rng = np.random.default_rng(304)
    w = _rand_w(rng)
    junk = pack_rows(_rand_w(rng))
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    await check_rows(dut, w, "initial")
    for phase in ("high", "low"):
        for r in range(N_IN):
            dut.load_addr.value = r
            dut.load_row.value = junk[r]
            await glitch(dut, [("load_en", 1)], phase)
        await check_rows(dut, w, f"after {phase}-phase load_en pulses")


async def cg_back_to_back_loads(dut):
    """Every row loaded on consecutive edges (several patterns, both
    orders), then every row written twice on consecutive edges (junk then
    final); full readback after each."""
    rng = np.random.default_rng(305)
    m = 2**WBITS - 1
    ii, jj = np.meshgrid(np.arange(N_IN), np.arange(N_OUT), indexing="ij")
    wa = _rand_w(rng)
    pats = [("random", wa), ("max", np.full((N_IN, N_OUT), m)),
            ("checker", np.where((ii + jj) % 2 == 0, m, 0)),
            ("complement", m - wa), ("zero", np.zeros((N_IN, N_OUT)))]
    await setup(dut)
    for name, w in pats:
        w = np.asarray(w, dtype=np.int64)
        for tag, order in (("up", range(N_IN)),
                           ("down", range(N_IN - 1, -1, -1))):
            await load_seq(dut, [(i, w[i]) for i in order])
            await check_rows(dut, w, f"b2b {name} {tag}")
    wf = _rand_w(rng)
    seq = []
    for i in rng.permutation(N_IN):
        seq += [(int(i), _differ(wf[i], rng)), (int(i), wf[i])]
    await load_seq(dut, seq)
    await check_rows(dut, wf, "each row written twice back to back")


def _row_handle(dut, i):
    try:
        base = dut.u_core            # dcim_8bit wraps dcim_core
    except AttributeError:
        base = dut
    return base.g_row[i].row


async def cg_write_edge_whitebox(dut, lag):
    """White-box: a stored row changes exactly at the header's write edge.
    lag=1 (dcim_core/dcim_8bit, registered write port: written at the edge
    after the load_en edge), lag=0 (mac_baseline: written at the load_en
    edge). Checked in ReadOnly right after each edge (clock high)."""
    rng = np.random.default_rng(306)
    w = _rand_w(rng)
    await setup(dut)
    await load_weights(dut, pack_rows(w))
    await check_rows(dut, w, "initial")
    rows = pack_rows(w)
    for r in rng.permutation(N_IN)[:8]:
        r = int(r)
        h = _row_handle(dut, r)
        new = _row(_differ(w[r], rng))
        dut.load_en.value = 1
        dut.load_addr.value = r
        dut.load_row.value = new
        await RisingEdge(dut.clk)           # load_en edge a
        dut.load_en.value = 0
        await ReadOnly()
        got = int(h.value)
        assert got == (new if lag == 0 else rows[r]), (
            f"row {r} right after load edge a: got {got:#x}, old "
            f"{rows[r]:#x}, new {new:#x} (header lag {lag})")
        await RisingEdge(dut.clk)           # edge a+1
        await ReadOnly()
        got = int(h.value)
        assert got == new, f"row {r} after edge a+1: {got:#x} != {new:#x}"
        await FallingEdge(dut.clk)
        rows[r] = new
