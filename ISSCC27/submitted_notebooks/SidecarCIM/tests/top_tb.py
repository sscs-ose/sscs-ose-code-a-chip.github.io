"""Testbench for rtl/sidecarcim_top.v vs golden.sidecarcim_dot (bit-exact).

Protocol per the sidecarcim_top.v header: dense rows (w_load_*) and sidecar
columns (s_load_*, slots + shift S) may load in the same cycle; start is
ignored while either load_en or busy; start->valid = ABITS + PIPE_MERGE
edges; weights and slots survive rst, S resets to 0 (reload every sidecar
column after rst). PIPE_MERGE from env TOP_PIPE_MERGE (default 0), set by
tests/Makefile together with -Psidecarcim_top.PIPE_MERGE.
SBITS (width of S) from env TOP_SBITS (default unset = S 0..VB-1, the
original 4-bit S); set with -Psidecarcim_top.SBITS. S width, SMAX and YTW
come from golden.s_max / golden.merged_width(..., sbits).
Vectors: python/vectors/<TOP_VEC_PREFIX>*.npz (default sidecar_; SBITS=3
uses sidecar_s3_).
"""
import os
import time

import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

import core_tb as ctb

golden = ctb.golden
SPEC = ctb.SPEC
N_IN, N_OUT = ctb.N_IN, ctb.N_OUT
WBITS = SPEC["dense"]["weight_bits"]
ABITS = SPEC["dense"]["act_bits"]
VB = SPEC["outlier"]["weight_bits"]
K = int(os.environ.get("SIDECAR_K", SPEC["outlier"]["budget_per_output"]))
AW = ctb._clog2(N_IN)
SLW = AW + VB
_sb = os.environ.get("TOP_SBITS", "")
SB = int(_sb) if _sb else None            # golden sbits (None = original)
SBW = SB if SB is not None else ctb._clog2(VB)   # s_load_shift / S width
YTW = golden.merged_width(N_IN, WBITS, ABITS, VB, K, sbits=SB)
VP = os.environ.get("TOP_VEC_PREFIX", "sidecar_")   # vector file prefix
PIPE = int(os.environ.get("TOP_PIPE_MERGE", "0"))   # header PIPE_MERGE
assert PIPE in (0, 1), f"TOP_PIPE_MERGE={PIPE}"
LAT = ABITS + PIPE                        # start -> valid edges
VEC = ctb.VEC
CLK_NS = ctb.CLK_NS
VARIANT = ctb.VARIANT
VCD_RUN = ctb.VCD_RUN
VCD_CASES = ctb.VCD_CASES


# ---------- packing ----------

def pack_rows(w):
    return [sum(int(w[i, j]) << (j * WBITS) for j in range(N_OUT))
            for i in range(N_IN)]


def pack_x(x):
    return sum(int(x[i]) << (i * ABITS) for i in range(N_IN))


def pack_col(idx, val, j):
    """K slots of column j: row index in low AW bits, value (2's c.) high."""
    v = 0
    for s in range(K):
        sl = (int(idx[s, j]) & ((1 << AW) - 1)) | \
             ((int(val[s, j]) & ((1 << VB) - 1)) << AW)
        v |= sl << (s * SLW)
    return v


def unpack_y(v):
    m = (1 << YTW) - 1
    out = []
    for j in range(N_OUT):
        u = (v >> (j * YTW)) & m
        out.append(u - (1 << YTW) if u >> (YTW - 1) else u)
    return out


def gold(c):
    return [int(v) for v in golden.sidecarcim_dot(
        c["w"], c["x"], c["idx"], c["val"], c["S"], WBITS, ABITS, VB,
        sbits=SB)]


def load_set(name):
    d = np.load(VEC / f"{name}.npz")
    cases = {k: d[k] for k in ("w", "x", "idx", "val", "S", "y")}
    assert cases["idx"].shape[1] == K, f"{name}: K={cases['idx'].shape[1]}"
    n = len(cases["w"])
    g = np.stack([golden.sidecarcim_dot(
        cases["w"][c], cases["x"][c], cases["idx"][c], cases["val"][c],
        cases["S"][c], WBITS, ABITS, VB, sbits=SB) for c in range(n)])
    bad = np.flatnonzero(np.any(g != cases["y"], axis=1))
    assert bad.size == 0, f"{name}.npz stored y != golden at case {bad[0]}"
    names = d["names"] if "names" in d.files else None
    return cases, g, names


def case(name, c):
    d = np.load(VEC / f"{name}.npz")
    return {k: d[k][c] for k in ("w", "x", "idx", "val", "S")}


# ---------- driving ----------

async def setup(dut, check_y=False):
    """Reset (power-up at the first test). Resets S to 0, so callers
    reload every sidecar column afterwards (header rule). y=0 is checked
    only when check_y (powerup_reset_y)."""
    assert len(dut.y) == N_OUT * YTW, f"y width {len(dut.y)} != {N_OUT}*{YTW}"
    assert len(dut.s_load_slots) == K * SLW
    assert int(dut.PIPE_MERGE.value) == PIPE, \
        f"DUT PIPE_MERGE={int(dut.PIPE_MERGE.value)} != TOP_PIPE_MERGE={PIPE}"
    assert len(dut.s_load_shift) == SBW, \
        f"s_load_shift width {len(dut.s_load_shift)} != {SBW}"
    assert int(dut.SBITS.value) == SBW, \
        f"DUT SBITS={int(dut.SBITS.value)} != expected S width {SBW}"
    cocotb.start_soon(Clock(dut.clk, CLK_NS, "ns").start())
    dut.rst.value = 1
    for s in ("w_load_en", "w_load_addr", "w_load_row", "s_load_en",
              "s_load_col", "s_load_slots", "s_load_shift", "start", "x_in"):
        getattr(dut, s).value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await ReadOnly()
    assert int(dut.busy.value) == 0 and int(dut.valid.value) == 0
    if check_y:
        yv = dut.y.value
        assert yv.is_resolvable and int(yv) == 0, f"y after power-up rst = {yv}"
    await FallingEdge(dut.clk)


def col_items(c, cols):
    return [(j, pack_col(c["idx"], c["val"], j), int(c["S"][j])) for j in cols]


async def load(dut, rows=(), cols=(), start_held=False, check_idle=False):
    """rows: [(i, row)], cols: [(j, slots, S)]; one of each per cycle,
    both in the same cycle while both lists last."""
    rows, cols = list(rows), list(cols)
    for t in range(max(len(rows), len(cols))):
        if t < len(rows):
            dut.w_load_en.value = 1
            dut.w_load_addr.value = rows[t][0]
            dut.w_load_row.value = rows[t][1]
        else:
            dut.w_load_en.value = 0
        if t < len(cols):
            dut.s_load_en.value = 1
            dut.s_load_col.value = cols[t][0]
            dut.s_load_slots.value = cols[t][1]
            dut.s_load_shift.value = cols[t][2]
        else:
            dut.s_load_en.value = 0
        dut.start.value = 1 if start_held else 0
        await RisingEdge(dut.clk)
        if check_idle:
            await ReadOnly()
            assert int(dut.busy.value) == 0, f"start accepted during load t={t}"
            await FallingEdge(dut.clk)
    dut.w_load_en.value = 0
    dut.s_load_en.value = 0
    dut.start.value = 0


def bv_expect(c, nxt=False):
    """(busy, valid) after edge k+c, c = 1..LAT, start accepted at edge k.
    busy after k..k+ABITS-1. PIPE_MERGE=0: valid after k+ABITS.
    PIPE_MERGE=1: (0,0) after k+ABITS (merge stage), valid after k+ABITS+1.
    nxt: a new start is accepted at edge k+LAT (PIPE_MERGE=1 only: then
    busy=1 together with valid=1)."""
    if c < ABITS:
        return (1, 0)
    if c < LAT:
        return (0, 0)
    return (1 if nxt else 0, 1)


async def wait_valid(dut, tag="", nxt=False):
    """Right after start edge k: checks busy,valid after every edge
    k+1..k+LAT (bv_expect). Returns in ReadOnly after k+LAT."""
    for c in range(1, LAT + 1):
        await RisingEdge(dut.clk)
        await ReadOnly()
        bv = (int(dut.busy.value), int(dut.valid.value))
        assert bv == bv_expect(c, nxt), \
            f"{tag} edge k+{c}: busy,valid={bv} expected {bv_expect(c, nxt)}"


async def run_dot(dut, xint):
    dut.start.value = 1
    dut.x_in.value = xint
    await RisingEdge(dut.clk)           # start edge k
    dut.start.value = 0
    await ReadOnly()
    assert int(dut.busy.value) == 1, "busy not set at start edge"
    await wait_valid(dut)
    yv = int(dut.y.value)
    await FallingEdge(dut.clk)
    return unpack_y(yv)


async def valid_falls_after_load(dut, exp):
    """Called at the falling edge after a load edge e in DONE (no start
    pending). PIPE_MERGE=0: valid=0 after e. PIPE_MERGE=1 (header 'Idle'):
    valid=1 and y = finished result after e, valid=0 after e+1, y holds.
    Returns at a falling edge."""
    await ReadOnly()
    if PIPE == 0:
        assert int(dut.valid.value) == 0
        await FallingEdge(dut.clk)
        return
    bv = (int(dut.busy.value), int(dut.valid.value))
    assert bv == (0, 1), f"after load edge e: busy,valid={bv}"
    assert unpack_y(int(dut.y.value)) == exp, "y after load edge e"
    await RisingEdge(dut.clk)
    await ReadOnly()
    bv = (int(dut.busy.value), int(dut.valid.value))
    assert bv == (0, 0), f"after e+1: busy,valid={bv}"
    assert unpack_y(int(dut.y.value)) == exp, "y must hold after e+1"
    await FallingEdge(dut.clk)


async def load_case(dut, c, order=None):
    order = range(N_IN) if order is None else order
    rows = pack_rows(c["w"])
    await load(dut, [(int(i), rows[i]) for i in order],
               col_items(c, range(N_OUT)))


# ---------- vector tests ----------

def _order(mode, rng):
    if mode == "shuffle":
        return [int(i) for i in rng.permutation(N_IN)]
    if mode == "reverse":
        return list(range(N_IN - 1, -1, -1))
    return list(range(N_IN))


async def run_set(dut, name, mode, limit=None):
    cases, g, names = load_set(name)
    n = len(cases["w"]) if limit is None else min(limit, len(cases["w"]))
    await setup(dut)
    rng = np.random.default_rng(4321)
    fails, first = 0, None
    nrow_loads = ncol_loads = 0
    pw = pc = None
    t0 = time.time()
    for c in range(n):
        cc = {k: cases[k][c] for k in ("w", "x", "idx", "val", "S")}
        rows = []
        if pw is None or not np.array_equal(cc["w"], pw):
            packed = pack_rows(cc["w"])
            rows = [(i, packed[i]) for i in _order(mode, rng)]
            nrow_loads += 1
            pw = cc["w"]
        colkey = [(tuple(cc["idx"][:, j]), tuple(cc["val"][:, j]),
                   int(cc["S"][j])) for j in range(N_OUT)]
        cols = [j for j in range(N_OUT) if pc is None or colkey[j] != pc[j]]
        if mode == "shuffle":
            cols = [cols[i] for i in rng.permutation(len(cols))]
        ncol_loads += len(cols)
        pc = colkey
        await load(dut, rows, col_items(cc, cols))   # same-cycle loads
        got = await run_dot(dut, pack_x(cc["x"]))
        exp = [int(v) for v in g[c]]
        if got != exp:
            fails += 1
            if first is None:
                tag = name + (f" [{names[c]}]" if names is not None else "")
                first = (f"{tag} case {c}\n  x = {list(map(int, cc['x']))}\n"
                         f"  w = {[list(map(int, r)) for r in cc['w']]}\n"
                         f"  idx = {cc['idx'].tolist()}\n"
                         f"  val = {cc['val'].tolist()}\n"
                         f"  S = {cc['S'].tolist()}\n"
                         f"  expected y = {exp}\n  got y      = {got}")
                dut._log.error("FIRST FAIL\n" + first)
    dt = time.time() - t0
    dut._log.info(
        f"SUMMARY {VARIANT} {name}: {n - fails}/{n} pass, {nrow_loads} dense "
        f"loads ({mode}), {ncol_loads} sidecar column loads, {dt:.1f} s "
        f"wall, {n / dt:.1f} cases/s")
    assert fails == 0, f"{fails}/{n} mismatches; first:\n{first}"


async def corners(dut):
    await run_set(dut, VP + "corners", "natural")


async def random_10k(dut):
    await run_set(dut, VP + "random", "shuffle", ctb.random_limit())


async def real_layer(dut):
    lim = os.environ.get("TOP_REAL_LIMIT")
    await run_set(dut, VP + "real_layer", "reverse",
                  int(lim) if lim else None)


async def vcd_real_layer(dut):
    await run_set(dut, VP + "real_layer", "natural", VCD_CASES)


# ---------- protocol tests ----------

async def powerup_reset_y(dut):
    """Header: 'Reset: ... y=0, every S[j]=0'. Checked right after the
    power-up reset, before any load (was X before 7f67ae4)."""
    await setup(dut, check_y=True)


async def reset_after_load_y(dut):
    """After all columns are loaded, rst gives busy=0, valid=0, y=0."""
    c = case(VP + "random", 11)
    await setup(dut)
    await load_case(dut, c)
    assert await run_dot(dut, pack_x(c["x"])) == gold(c)
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert (int(dut.busy.value), int(dut.valid.value)) == (0, 0)
    assert int(dut.y.value) == 0
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def latency_and_hold(dut):
    c = case(VP + "random", 0)
    await setup(dut)
    await load_case(dut, c)
    exp = gold(c)
    assert await run_dot(dut, pack_x(c["x"])) == exp
    for _ in range(20):                 # idle in DONE, inputs wiggle
        dut.x_in.value = pack_x(c["x"][::-1])
        dut.w_load_addr.value = 3
        dut.s_load_col.value = 2
        dut.s_load_slots.value = (1 << (K * SLW)) - 1
        dut.s_load_shift.value = (1 << SBW) - 1
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert (int(dut.busy.value), int(dut.valid.value)) == (0, 1)
        assert unpack_y(int(dut.y.value)) == exp
        await FallingEdge(dut.clk)


async def start_ignored_during_loads(dut):
    """start held through: dense+sidecar same-cycle loads, dense-only loads,
    sidecar-only loads (in LOAD and in DONE) -> never accepted."""
    c = case(VP + "random", 1)
    rows = pack_rows(c["w"])
    await setup(dut)
    # 8 cycles both, then 24 dense-only
    await load(dut, [(i, rows[i]) for i in range(N_IN)],
               col_items(c, range(N_OUT)), start_held=True, check_idle=True)
    # sidecar-only, rewriting same values
    await load(dut, [], col_items(c, range(N_OUT)), start_held=True,
               check_idle=True)
    assert await run_dot(dut, pack_x(c["x"])) == gold(c)
    # in DONE: start with sidecar-only load -> leaves DONE, no compute
    await load(dut, [], col_items(c, [3]), start_held=True, check_idle=True)
    await valid_falls_after_load(dut, gold(c))
    # in DONE again: start with dense-only load
    assert await run_dot(dut, pack_x(c["x"])) == gold(c)
    await load(dut, [(5, rows[5])], [], start_held=True, check_idle=True)
    await valid_falls_after_load(dut, gold(c))
    # start right after the last load
    assert await run_dot(dut, pack_x(c["x"])) == gold(c)


async def loads_while_busy_ignored(dut):
    """Dense and sidecar loads (junk slots and S) on every compute edge."""
    c = case(VP + "random", 2)
    j2 = case(VP + "random", 3)
    jrows = pack_rows(j2["w"])
    await setup(dut)
    await load_case(dut, c)
    exp = gold(c)
    dut.start.value = 1
    dut.x_in.value = pack_x(c["x"])
    await RisingEdge(dut.clk)
    dut.start.value = 0
    for e in range(1, ABITS + 1):       # every edge with busy=1 before it
        dut.w_load_en.value = 1
        dut.w_load_addr.value = e % N_IN
        dut.w_load_row.value = jrows[e % N_IN]
        dut.s_load_en.value = 1
        dut.s_load_col.value = e % N_OUT
        dut.s_load_slots.value = pack_col(j2["idx"], j2["val"], e % N_OUT)
        dut.s_load_shift.value = (int(c["S"][e % N_OUT]) + 5) % (SMAX + 1)
        await RisingEdge(dut.clk)
    dut.w_load_en.value = 0
    dut.s_load_en.value = 0
    for _ in range(ABITS + 1, LAT + 1):  # PIPE_MERGE=1: output-register edge
        await RisingEdge(dut.clk)
    await ReadOnly()
    assert (int(dut.busy.value), int(dut.valid.value)) == (0, 1)
    assert unpack_y(int(dut.y.value)) == exp
    await FallingEdge(dut.clk)
    for xx in (c["x"], np.full(N_IN, 2**ABITS - 1, dtype=np.uint8)):
        cc = dict(c, x=xx)
        assert await run_dot(dut, pack_x(xx)) == gold(cc)


async def start_while_busy_ignored(dut):
    c = case(VP + "random", 4)
    x2 = case(VP + "random", 5)["x"]
    await setup(dut)
    await load_case(dut, c)
    dut.start.value = 1
    dut.x_in.value = pack_x(c["x"])
    await RisingEdge(dut.clk)
    dut.x_in.value = pack_x(x2)         # start stays high, new x
    for cc in range(1, LAT + 1):        # start held through edge k+ABITS
        await RisingEdge(dut.clk)       # (the last edge with busy=1 before)
        await ReadOnly()
        bv = (int(dut.busy.value), int(dut.valid.value))
        assert bv == bv_expect(cc), f"edge k+{cc}: busy,valid={bv}"
        if cc == LAT:
            break
        await FallingEdge(dut.clk)
        if cc == ABITS:
            dut.start.value = 0
    assert unpack_y(int(dut.y.value)) == gold(c)
    await FallingEdge(dut.clk)
    dut.start.value = 0


async def back_to_back(dut):
    """start held high: one dot every ABITS+1 cycles."""
    c = case(VP + "random", 6)
    xs = np.load(VEC / f"{VP}random.npz")["x"][:8]
    await setup(dut)
    await load_case(dut, c)
    dut.start.value = 1
    dut.x_in.value = pack_x(xs[0])
    await RisingEdge(dut.clk)
    for k in range(len(xs)):
        exp = gold(dict(c, x=xs[k]))
        dut.x_in.value = pack_x(xs[(k + 1) % len(xs)])
        await wait_valid(dut, f"dot {k}", nxt=bool(PIPE))
        assert unpack_y(int(dut.y.value)) == exp, f"dot {k}"
        if not PIPE:                    # PIPE_MERGE=1: k+LAT was the start
            await RisingEdge(dut.clk)   # next accepted start
            await ReadOnly()
            assert int(dut.busy.value) == 1
        await FallingEdge(dut.clk)
    dut.start.value = 0


async def reset_mid_compute(dut):
    """rst at k+1..k+ABITS-1 -> idle, y=0. Header (7f67ae4): weights and
    slots survive rst, every S[j] resets to 0. Checked by computing before
    any reload (expect golden with S=0), then reloading all sidecar
    columns (header rule after rst) and checking the full result."""
    c = case(VP + "random", 7)
    c2 = case(VP + "random", 8)
    exp = gold(c)
    exp_s0 = gold(dict(c, S=np.zeros(N_OUT, dtype=np.uint8)))
    await setup(dut)
    await load_case(dut, c)
    for stop in range(1, ABITS):         # rst while busy (pipe stage: below)
        dut.start.value = 1
        dut.x_in.value = pack_x(c["x"])
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
        assert (int(dut.busy.value), int(dut.valid.value)) == (0, 0)
        assert int(dut.y.value) == 0
        await FallingEdge(dut.clk)
        dut.rst.value = 0
        assert await run_dot(dut, pack_x(c["x"])) == exp_s0, \
            f"rst at k+{stop}: expected S=0, weights+slots kept"
        await load(dut, [], col_items(c, range(N_OUT)))   # reload S
        assert await run_dot(dut, pack_x(c["x"])) == exp, \
            f"rst at k+{stop}: after sidecar reload"
    await load_case(dut, c2)
    assert await run_dot(dut, pack_x(c2["x"])) == gold(c2)


async def column_reload(dut):
    """Single sidecar column (slots + S) and single dense row rewrites,
    shuffled, recompute after each; others retained."""
    c = case(VP + "random", 9)
    c2 = case(VP + "random", 10)
    await setup(dut)
    await load_case(dut, c)
    cur = {k: np.array(v, copy=True) for k, v in c.items()}
    rng = np.random.default_rng(11)
    for j in rng.permutation(N_OUT):
        cur["idx"][:, j] = c2["idx"][:, j]
        cur["val"][:, j] = c2["val"][:, j]
        cur["S"][j] = c2["S"][j]
        await load(dut, [], col_items(cur, [int(j)]))
        assert await run_dot(dut, pack_x(cur["x"])) == gold(cur), f"col {j}"
    for i in rng.permutation(N_IN)[:4]:
        cur["w"][i] = c2["w"][i]
        await load(dut, [(int(i), pack_rows(cur["w"])[i])], [])
        assert await run_dot(dut, pack_x(cur["x"])) == gold(cur), f"row {i}"


# ---------- directed: slot-width (VB) extremes ----------

VMIN, VMAX = -(1 << (VB - 1)), (1 << (VB - 1)) - 1
SMAX = golden.s_max(VB, SB)               # largest legal S
NS = SMAX + 1                             # legal S codes
WMAX, XMAX = 2**WBITS - 1, 2**ABITS - 1
DMAX = N_IN * WMAX * XMAX                 # dense max
YMAX = (DMAX << SMAX) + K * VMAX * XMAX   # largest legal merged y
YMIN = K * VMIN * XMAX                    # smallest legal merged y


def mkcase(w, x, per_slot, S, idx=None):
    """per_slot: K slot values (same in every column) or (K, N_OUT)."""
    v = np.asarray(per_slot, dtype=np.int64)
    if v.ndim == 1:
        v = np.repeat(v[:, None], N_OUT, axis=1)
    if idx is None:                       # distinct rows 0..K-1
        idx = np.repeat((np.arange(K) % N_IN)[:, None], N_OUT, axis=1)
    return {"w": np.broadcast_to(np.asarray(w, dtype=np.int64),
                                 (N_IN, N_OUT)).copy(),
            "x": np.broadcast_to(np.asarray(x, dtype=np.int64),
                                 (N_IN,)).copy(),
            "idx": np.asarray(idx, dtype=np.int64), "val": v,
            "S": np.broadcast_to(np.asarray(S, dtype=np.int64),
                                 (N_OUT,)).copy()}


async def vb_extremes(dut):
    """val VMIN/VMAX, S = 0..SMAX, max and min merged y. Expected from
    golden; the closed-form cases are also checked against formulas
    built from spec widths only (independent of golden)."""
    assert -(1 << (YTW - 1)) <= YMIN and YMAX < (1 << (YTW - 1))
    mixed = ([VMAX, VMIN] * K)[:K]
    rng = np.random.default_rng(1212)
    cases = [
        ("y_max", mkcase(WMAX, XMAX, [VMAX] * K, SMAX), YMAX),
        ("y_min", mkcase(0, XMAX, [VMIN] * K, SMAX), YMIN),
        ("dense_max_side_min", mkcase(WMAX, XMAX, [VMIN] * K, SMAX),
         (DMAX << SMAX) + YMIN),
        ("dup_row_min", mkcase(0, [XMAX] + [0] * (N_IN - 1), [VMIN] * K,
                               SMAX, idx=np.zeros((K, N_OUT))), YMIN),
        ("x_zero", mkcase(WMAX, 0, [VMIN] * K, SMAX), 0),
        ("x_msb_only", mkcase(0, 1 << (ABITS - 1), [VMIN] * K, SMAX),
         K * VMIN * (1 << (ABITS - 1))),
        ("mixed_S_down", mkcase(WMAX, XMAX, mixed,
                                [(SMAX - j) % NS for j in range(N_OUT)]),
         None),
    ]
    for t in range(-(-NS // N_OUT)):      # S sweep covers 0..SMAX
        S = [(t * N_OUT + j) % NS for j in range(N_OUT)]
        v = rng.choice([VMIN, VMAX], (K, N_OUT))
        cases.append((f"S_sweep_{t}", mkcase(
            rng.integers(0, WMAX + 1, (N_IN, N_OUT)),
            rng.integers(0, XMAX + 1, N_IN), v, S,
            idx=rng.integers(0, N_IN, (K, N_OUT))), None))
    pool = [VMIN, VMIN + 1, -1, 0, 1, VMAX - 1, VMAX]
    for t in range(24):                   # random extremes
        cases.append((f"rand_ext_{t}", mkcase(
            rng.integers(0, WMAX + 1, (N_IN, N_OUT)),
            rng.integers(0, XMAX + 1, N_IN), rng.choice(pool, (K, N_OUT)),
            rng.integers(0, SMAX + 1, N_OUT),
            idx=rng.integers(0, N_IN, (K, N_OUT))), None))
    await setup(dut)
    for name, c, closed in cases:
        exp = gold(c)
        if closed is not None:
            assert exp == [closed] * N_OUT, f"{name}: golden {exp} != {closed}"
        await load_case(dut, c)
        got = await run_dot(dut, pack_x(c["x"]))
        assert got == exp, (f"{name}: x={c['x'].tolist()} idx="
                            f"{c['idx'].tolist()} val={c['val'].tolist()} "
                            f"S={c['S'].tolist()}\n  expected {exp}\n"
                            f"  got      {got}")
    dut._log.info(f"SUMMARY {VARIANT} vb_extremes: {len(cases)}/{len(cases)}"
                  f" pass (VB={VB}, SMAX={SMAX}, YTW={YTW}, y max {YMAX},"
                  f" y min {YMIN})")


# ---------- directed: clock-gated storage (rtl/icg.v, CLK_GATE=1) ----------
# State (dense rows, slots, S) is read back through the ports: x one-hot
# at every row i (value 1) gives y[j] = (w[i][j] << S[j]) + the slots on
# row i, plus x all-max; each dot vs golden. States use w >= 1, val != 0
# and S >= 1, so a lost row, slot or S always shows.

def rand_state(rng):
    v = rng.integers(VMIN, VMAX, (K, N_OUT), endpoint=True)
    v[v == 0] = 1
    return {"w": rng.integers(1, WMAX + 1, (N_IN, N_OUT)),
            "x": np.zeros(N_IN, dtype=np.int64),
            "idx": rng.integers(0, N_IN, (K, N_OUT)), "val": v,
            "S": rng.integers(1, SMAX + 1, N_OUT)}


def s_zero(cur):
    return dict(cur, S=np.zeros(N_OUT, dtype=np.int64))


async def check_state(dut, cur, tag):
    xs = []
    for i in range(N_IN):
        x = np.zeros(N_IN, dtype=np.int64)
        x[i] = 1
        xs.append(x)
    xs.append(np.full(N_IN, XMAX, dtype=np.int64))
    for x in xs:
        exp = gold(dict(cur, x=x))
        got = await run_dot(dut, pack_x(x))
        assert got == exp, (
            f"{tag}: x={x.tolist()}\n  w={cur['w'].tolist()}\n"
            f"  idx={cur['idx'].tolist()} val={cur['val'].tolist()} "
            f"S={cur['S'].tolist()}\n  expected {exp}\n  got      {got}")


async def top_rst(dut, n=1):
    """rst for n edges (driven now: a falling edge or right after the last
    load edge); checks idle and y=0; returns at a falling edge."""
    dut.rst.value = 1
    for _ in range(n):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert (int(dut.busy.value), int(dut.valid.value)) == (0, 0)
        assert int(dut.y.value) == 0
        await FallingEdge(dut.clk)
    dut.rst.value = 0


def new_col(cur, j, rng):
    """Change column j: new slot rows, new nonzero values, new S >= 1."""
    cur["idx"][:, j] = (cur["idx"][:, j] + rng.integers(1, N_IN, K)) % N_IN
    for s in range(K):
        v = cur["val"][s, j]
        while v == 0 or v == cur["val"][s, j]:
            v = rng.integers(VMIN, VMAX, endpoint=True)
        cur["val"][s, j] = v
    cur["S"][j] = 1 + (cur["S"][j] + rng.integers(0, SMAX - 1)) % SMAX


def new_row(cur, i, rng):
    cur["w"][i] = 1 + (cur["w"][i] + rng.integers(0, WMAX - 1, N_OUT)) % WMAX


async def cg_top_rst_idle(dut):
    """rst while S is loaded and no load is pending (in DONE, 1 and 3
    edges; in LOAD): every S[j] -> 0, dense rows and slots survive."""
    rng = np.random.default_rng(401)
    cur = rand_state(rng)
    await setup(dut)
    await load_case(dut, cur)
    await check_state(dut, cur, "after load")
    for n in (1, 3):
        await top_rst(dut, n)
        await check_state(dut, s_zero(cur), f"rst {n} edge(s) in DONE")
        await load(dut, [], col_items(cur, range(N_OUT)))
        await check_state(dut, cur, f"S reloaded after rst {n}")
    await load(dut, [], col_items(cur, [2]))   # same value -> LOAD
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)                   # idle edge, nothing pending
    await FallingEdge(dut.clk)
    await top_rst(dut, 1)                       # in LOAD
    await check_state(dut, s_zero(cur), "rst in LOAD")


async def cg_top_load_before_rst(dut):
    """Loads on the edge right before rst (header: written; S then
    cleared by rst), all rows and columns streamed up to rst, and a load
    on the first edge after rst (S keeps that value)."""
    rng = np.random.default_rng(402)
    cur = rand_state(rng)
    await setup(dut)
    await load_case(dut, cur)
    for r, j in [(0, 0), (17, 5), (N_IN - 1, N_OUT - 1)]:
        new_row(cur, r, rng)
        new_col(cur, j, rng)
        await load(dut, [(r, pack_rows(cur["w"])[r])],
                   col_items(cur, [j]))         # same-cycle loads, edge e
        await top_rst(dut, 1)                   # rst edge e+1
        await check_state(dut, s_zero(cur),
                          f"row {r} + col {j} loaded at the edge before rst")
        await load(dut, [], col_items(cur, range(N_OUT)))
        await check_state(dut, cur, f"S reloaded (row {r}, col {j})")
    c2 = rand_state(rng)
    await load_case(dut, c2, order=[int(i) for i in rng.permutation(N_IN)])
    await top_rst(dut, 1)
    await check_state(dut, s_zero(c2), "all rows + columns streamed to rst")
    new_row(c2, 9, rng)
    new_col(c2, 3, rng)
    await top_rst(dut, 2)
    await load(dut, [(9, pack_rows(c2["w"])[9])], col_items(c2, [3]))
    exp = s_zero(c2)
    exp["S"][3] = c2["S"][3]
    await check_state(dut, exp, "load on the first edge after rst")


async def cg_top_single_write(dut):
    """Write one dense row, or one sidecar column (slots + S); everything
    else must hold. Every row and column, shuffled, full readback after
    each write."""
    rng = np.random.default_rng(403)
    cur = rand_state(rng)
    await setup(dut)
    await load_case(dut, cur)
    await check_state(dut, cur, "initial")
    for i in rng.permutation(N_IN):
        new_row(cur, int(i), rng)
        await load(dut, [(int(i), pack_rows(cur["w"])[int(i)])], [])
        await check_state(dut, cur, f"after write to dense row {int(i)}")
    for j in rng.permutation(N_OUT):
        new_col(cur, int(j), rng)
        await load(dut, [], col_items(cur, [int(j)]))
        await check_state(dut, cur, f"after write to sidecar column {int(j)}")


async def cg_top_enable_glitch(dut):
    """w_load_en, s_load_en and rst pulses that start and end inside one
    clock phase (high and low), every row and column, junk data: no edge
    sees them, so no row, slot or S may change (rst must not clear S)."""
    rng = np.random.default_rng(404)
    cur = rand_state(rng)
    junk = rand_state(rng)
    jrows = pack_rows(junk["w"])
    await setup(dut)
    await load_case(dut, cur)
    await check_state(dut, cur, "initial")
    for phase in ("high", "low"):
        for r in range(N_IN):
            dut.w_load_addr.value = r
            dut.w_load_row.value = jrows[r]
            await ctb.glitch(dut, [("w_load_en", 1)], phase)
        for j in range(N_OUT):
            dut.s_load_col.value = j
            dut.s_load_slots.value = pack_col(junk["idx"], junk["val"], j)
            dut.s_load_shift.value = int(junk["S"][j])
            await ctb.glitch(dut, [("s_load_en", 1)], phase)
        await ctb.glitch(dut, [("rst", 1)], phase)
        dut.s_load_col.value = 4
        await ctb.glitch(dut, [("rst", 1), ("s_load_en", 1)], phase)
        await check_state(dut, cur, f"after {phase}-phase pulses")


async def cg_top_back_to_back(dut):
    """All dense rows and all sidecar columns on consecutive edges (same
    cycles), both orders, three states; then every row and every column
    written twice on consecutive edges (junk then final)."""
    rng = np.random.default_rng(405)
    await setup(dut)
    for t in range(3):
        cur = rand_state(rng)
        for tag, ro, co in (("up", range(N_IN), range(N_OUT)),
                            ("down", range(N_IN - 1, -1, -1),
                             range(N_OUT - 1, -1, -1))):
            rows = pack_rows(cur["w"])
            await load(dut, [(i, rows[i]) for i in ro], col_items(cur, co))
            await check_state(dut, cur, f"b2b state {t} {tag}")
    fin = rand_state(rng)
    jnk = rand_state(rng)
    fr, jr = pack_rows(fin["w"]), pack_rows(jnk["w"])
    rows, cols = [], []
    for i in rng.permutation(N_IN):
        rows += [(int(i), jr[i]), (int(i), fr[i])]
    for j in rng.permutation(N_OUT):
        cols += col_items(jnk, [int(j)]) + col_items(fin, [int(j)])
    await load(dut, rows, cols)
    await check_state(dut, fin, "each row/column written twice back to back")


# ---------- directed: output pipeline (PIPE_MERGE), cycle-level model ----------
# Model of the header protocol, edge by edge. P0 part: LOAD / BUSY / DONE,
# busy after start edges k..k+ABITS-1, cv (both cores DONE) after k+ABITS;
# loads and start are ignored while busy; a load or start in DONE clears
# cv; rst -> LOAD, cv=0, S=0, weights and slots kept. PIPE_MERGE=0 port:
# valid=cv, y = result while cv (and 0 right after a rst edge).
# PIPE_MERGE=1 port ("PROTOCOL, PIPE_MERGE=1"): at every edge valid <= cv;
# y <= merge (= the DONE result) if cv, else y holds; rst clears both.
# Every edge checks busy, valid and y (y always when PIPE_MERGE=1).

class PipeModel:
    def __init__(self, cur):
        self.st = {k: np.array(v, dtype=np.int64, copy=True)
                   for k, v in cur.items() if k != "x"}
        self.phase, self.cnt = "LOAD", 0
        self.res = None                   # result of the current/last dot
        self.yq, self.vq = [0] * N_OUT, 0
        self.rst_edge = False

    @property
    def busy(self):
        return int(self.phase == "BUSY")

    @property
    def cv(self):
        return int(self.phase == "DONE")

    def accepts_start(self, start, wl, sl, rst):
        return bool(start and not rst and wl is None and sl is None
                    and self.phase != "BUSY")

    def edge(self, rst, start, x, wl, sl):
        """wl = (i, row values) or None; sl = (j, idx col, val col, S)."""
        cv0, res0, busy0 = self.cv, self.res, self.phase == "BUSY"
        self.rst_edge = bool(rst)
        if rst:
            assert wl is None and sl is None, "no load at the rst edge"
            self.phase, self.cnt = "LOAD", 0
            self.st["S"] = np.zeros(N_OUT, dtype=np.int64)
            self.yq, self.vq = [0] * N_OUT, 0
            return
        self.vq = cv0
        if cv0:
            self.yq = list(res0)
        if busy0:
            self.cnt += 1
            if self.cnt == ABITS:
                self.phase = "DONE"
        elif wl is not None or sl is not None:
            if wl is not None:
                self.st["w"][wl[0]] = wl[1]
            if sl is not None:
                j, ix, vl, s = sl
                self.st["idx"][:, j] = ix
                self.st["val"][:, j] = vl
                self.st["S"][j] = s
            self.phase = "LOAD"
        elif start:
            self.phase, self.cnt = "BUSY", 0
            self.res = gold(dict(self.st, x=np.asarray(x, dtype=np.int64)))

    def port(self):
        """Expected (busy, valid, y or None = don't care)."""
        if PIPE:
            return self.busy, self.vq, self.yq
        if self.rst_edge:
            return self.busy, 0, [0] * N_OUT
        return self.busy, self.cv, (self.res if self.cv else None)


def row_int(r):
    return sum(int(r[j]) << (j * WBITS) for j in range(N_OUT))


async def pipe_drive(dut, m, steps, xq, rng, tag):
    """Drive one edge per step from a falling edge; returns at a falling
    edge. step = dict(rst, start, wl, sl). x_in: next value of xq on an
    edge that accepts a start, random junk on every other edge. Returns
    the trace [(busy, valid)] after each edge."""
    trace = []
    xq = list(xq)
    for n, s in enumerate(steps):
        rst, start = int(s.get("rst", 0)), int(s.get("start", 0))
        wl, sl = s.get("wl"), s.get("sl")
        acc = m.accepts_start(start, wl, sl, rst)
        x = xq.pop(0) if acc else rng.integers(0, 2**ABITS, N_IN)
        dut.rst.value = rst
        dut.start.value = start
        dut.x_in.value = pack_x(x)
        dut.w_load_en.value = int(wl is not None)
        if wl is not None:
            dut.w_load_addr.value = int(wl[0])
            dut.w_load_row.value = row_int(wl[1])
        dut.s_load_en.value = int(sl is not None)
        if sl is not None:
            j, ix, vl, sh = sl
            col = {"idx": np.zeros((K, N_OUT), dtype=np.int64),
                   "val": np.zeros((K, N_OUT), dtype=np.int64)}
            col["idx"][:, j], col["val"][:, j] = ix, vl
            dut.s_load_col.value = int(j)
            dut.s_load_slots.value = pack_col(col["idx"], col["val"], j)
            dut.s_load_shift.value = int(sh)
        await RisingEdge(dut.clk)
        m.edge(rst, start, x, wl, sl)
        await ReadOnly()
        b, v = int(dut.busy.value), int(dut.valid.value)
        eb, ev, ey = m.port()
        msg = f"{tag} step {n} (rst={rst} start={start} wl={wl is not None}" \
              f" sl={sl is not None}): "
        assert (b, v) == (eb, ev), msg + f"busy,valid={(b, v)} exp {(eb, ev)}"
        if ey is not None:
            got = unpack_y(int(dut.y.value))
            assert got == list(ey), msg + f"y={got}\n  expected {list(ey)}"
        trace.append((b, v))
        await FallingEdge(dut.clk)
    for sig in ("rst", "start", "w_load_en", "s_load_en"):
        getattr(dut, sig).value = 0
    assert not xq, f"{tag}: {len(xq)} x values unused"
    return trace


async def pipe_start(dut, seed_case):
    """Reset, load a full case, return (model, case)."""
    c = case(VP + "random", seed_case)
    await setup(dut)
    await load_case(dut, c)
    return PipeModel(c), c


def idle(n):
    return [{} for _ in range(n)]


def new_sl(m, j, rng):
    """New column j: slot rows, nonzero values, S >= 1, all different."""
    ix = (m.st["idx"][:, j] + rng.integers(1, N_IN, K)) % N_IN
    vl = rng.integers(VMIN, VMAX, K, endpoint=True)
    vl[vl == 0] = 1
    vl[vl == m.st["val"][:, j]] = VMIN if VMIN not in m.st["val"][:, j] \
        else VMAX
    s = 1 + (int(m.st["S"][j]) + int(rng.integers(0, SMAX - 1))) % SMAX
    return (j, ix, vl, s)


def new_wl(m, i, rng):
    return (i, 1 + (m.st["w"][i] + rng.integers(0, WMAX - 1, N_OUT)) % WMAX)


def rises(tr):
    return [t for t, (_, v) in enumerate(tr) if v and
            (t == 0 or not tr[t - 1][1])]


async def pipe_b2b_overlap(dut):
    """Back-to-back dots (start held high, then start pulsed only on the
    accepting edges). PIPE_MERGE=1: valid=1 for one cycle per dot while
    the next dot is busy, y holds the last result in between, one dot
    every ABITS+1 edges; start -> valid = LAT edges."""
    rng = np.random.default_rng(501)
    m, c = await pipe_start(dut, 12)
    xs = list(np.load(VEC / f"{VP}random.npz")["x"][20:36])
    xs += [np.full(N_IN, XMAX), np.zeros(N_IN, dtype=np.int64)]
    nd, P = len(xs), ABITS + 1
    for mode in ("held", "pulsed"):
        steps = []
        for t in range(nd * P):
            st = 1 if (mode == "held" or t % P == 0) else 0
            steps.append({"start": st})
        steps += idle(P + 2)
        tr = await pipe_drive(dut, m, steps, xs, rng, f"b2b {mode}")
        tr = tr[1:]                       # from edge k+1 (k = first start)
        vidx = rises(tr)
        assert len(vidx) == nd, f"{mode}: {len(vidx)} valid pulses, exp {nd}"
        assert all(b - a == P for a, b in zip(vidx, vidx[1:])), vidx
        assert vidx[0] == LAT - 1, f"first valid after step {vidx[0]}"
        ov = sum(1 for b, v in tr if b and v)
        assert ov == (nd - 1 if PIPE else 0), f"{mode}: overlap {ov}"
        width = [sum(1 for t in range(a, a + P) if tr[t][1])
                 for a in vidx[:-1]]
        assert set(width) == {1}, f"{mode}: valid widths {width}"
        dut._log.info(f"SUMMARY {VARIANT} pipe_b2b_overlap {mode}: {nd} dots "
                      f"every {P} edges, latency {LAT}, valid&busy {ov} "
                      "cycles, every edge = model")


async def pipe_load_in_done(dut):
    """A load (sidecar column with new S, dense row, both, both + start)
    on the edge valid rises (d=0, PIPE_MERGE=1: k+ABITS+1) and 1..3 edges
    later. PIPE_MERGE=1: valid stays 1 after the load edge with the
    finished result (old S and accumulators), falls one edge later, y
    holds it until the next result. Then a dot on the new state."""
    rng = np.random.default_rng(502)
    m, c = await pipe_start(dut, 13)
    xs = list(np.load(VEC / f"{VP}random.npz")["x"][40:80])
    n = 0
    for kind in ("col", "row", "both", "both_start"):
        for d in range(4):
            j, i = int(rng.integers(N_OUT)), int(rng.integers(N_IN))
            steps = [{"start": 1}] + idle(LAT - 1 + d)
            ld = {}
            if kind != "row":
                ld["sl"] = new_sl(m, j, rng)
            if kind != "col":
                ld["wl"] = new_wl(m, i, rng)
            if kind == "both_start":
                ld["start"] = 1
            steps += [ld] + idle(4) + [{"start": 1}] + idle(LAT + 1)
            tr = await pipe_drive(dut, m, steps, xs[n:n + 2], rng,
                                  f"{kind} d={d}")
            e = LAT + d                   # step index of the load edge
            if PIPE:                      # explicit, besides the model
                assert tr[e] == (0, 1) and tr[e + 1] == (0, 0), \
                    f"{kind} d={d}: {tr[e]} {tr[e + 1]}"
            n += 2
    dut._log.info(f"SUMMARY {VARIANT} pipe_load_in_done: 16 load cases "
                  "(4 kinds x 4 edges), every edge = model")


async def pipe_rst_mid_pipeline(dut):
    """rst at every edge k+1..k+LAT+1 of a single dot, and at the edges
    around the overlap of back-to-back dots. After rst: busy=valid=0, y=0,
    no stale valid for 2*(ABITS+1) idle edges; then a dot with S=0
    (weights and slots kept), all columns reloaded, a dot again."""
    rng = np.random.default_rng(503)
    m, c = await pipe_start(dut, 14)
    xs = list(np.load(VEC / f"{VP}random.npz")["x"][100:200])
    P = ABITS + 1
    cols = [{"sl": (j, c["idx"][:, j], c["val"][:, j], int(c["S"][j]))}
            for j in range(N_OUT)]
    n = 0
    plans = [("single", s) for s in range(1, LAT + 2)]
    plans += [("b2b", P + s) for s in range(-1, 3)]
    for mode, at in plans:
        if mode == "single":
            steps = [{"start": 1}] + idle(at - 1)
            nx = 1
        else:
            steps = [{"start": 1} for _ in range(at)]
            nx = 1 + (at - 1) // P
        steps += [{"rst": 1}] + idle(2 * P)
        steps += [{"start": 1}] + idle(LAT + 1) + cols
        steps += [{"start": 1}] + idle(LAT + 1)
        tr = await pipe_drive(dut, m, steps, xs[n:n + nx + 2], rng,
                              f"rst {mode} at k+{at}")
        assert all(t == (0, 0) for t in tr[at:at + 1 + 2 * P]), \
            f"rst {mode} at k+{at}: {tr[at:at + 1 + 2 * P]}"
        n += nx + 2
    dut._log.info(f"SUMMARY {VARIANT} pipe_rst_mid_pipeline: {len(plans)} "
                  "rst points, every edge = model")


async def pipe_start_on_valid_edge(dut):
    """Second start pulse at edge k+LAT+d after a single dot started at k:
    d=0 is the exact edge valid rises (PIPE_MERGE=1: the start is accepted
    and valid=1 with busy=1); edges k+1..k+ABITS are busy (ignored); later
    edges are in DONE. Different x for both dots."""
    rng = np.random.default_rng(504)
    m, c = await pipe_start(dut, 15)
    xs = list(np.load(VEC / f"{VP}random.npz")["x"][200:260])
    n = 0
    for d in range(1 - LAT, 4):
        at = LAT + d                      # 1 .. LAT+3
        acc = at >= ABITS + 1             # edge k+ABITS: busy before it
        steps = [{"start": 1}] + idle(at - 1) + [{"start": 1}]
        steps += idle(LAT + 2)
        nx = 2 if acc else 1
        tr = await pipe_drive(dut, m, steps, xs[n:n + nx], rng,
                              f"2nd start at k+{at}")
        if PIPE and d == 0:
            assert tr[at] == (1, 1), f"k+{at}: {tr[at]}"
        r = rises(tr[1:])                 # from edge k+1 (k = first start)
        assert len(r) == nx, f"2nd start at k+{at}: valid rises {r}"
        n += nx
    dut._log.info(f"SUMMARY {VARIANT} pipe_start_on_valid_edge: second start "
                  f"at k+1..k+{LAT + 3}, every edge = model")


async def pipe_protocol_fuzz(dut):
    """3,000 random edges: start (60 %), dense and sidecar loads with new
    values (10 % each, may coincide), rst (0.5 %, never with a load), in
    every state. Every edge vs the model."""
    rng = np.random.default_rng(505)
    m, c = await pipe_start(dut, 16)
    steps = []
    for _ in range(3000):
        if rng.random() < 0.005:
            steps.append({"rst": 1})
            continue
        s = {"start": int(rng.random() < 0.6)}
        if rng.random() < 0.1:
            s["wl"] = (int(rng.integers(N_IN)),
                       rng.integers(0, WMAX + 1, N_OUT))
        if rng.random() < 0.1:
            j = int(rng.integers(N_OUT))
            if rng.random() < 0.3:
                vl = rng.choice([VMIN, VMIN + 1, -1, 0, 1, VMAX - 1, VMAX], K)
            else:
                vl = rng.integers(VMIN, VMAX, K, endpoint=True)
            s["sl"] = (j, rng.integers(0, N_IN, K), vl,
                       int(rng.integers(0, SMAX + 1)))
        steps.append(s)
    # one x per accepted start; count them with a dry run of the model
    dry = PipeModel(m.st)
    nx = 0
    for s in steps:
        a = dry.accepts_start(s.get("start", 0), s.get("wl"), s.get("sl"),
                              s.get("rst", 0))
        nx += a
        dry.edge(s.get("rst", 0), s.get("start", 0),
                 np.zeros(N_IN, dtype=np.int64), s.get("wl"), s.get("sl"))
    xs = [rng.integers(0, XMAX + 1, N_IN) for _ in range(nx)]
    tr = await pipe_drive(dut, m, steps, xs, rng, "fuzz")
    ov = sum(1 for b, v in tr if b and v)
    nr = sum(1 for s in steps if s.get("rst"))
    dut._log.info(f"SUMMARY {VARIANT} pipe_protocol_fuzz: {len(steps)} edges,"
                  f" {nx} starts accepted, {len(rises(tr))} valid pulses, "
                  f"valid&busy {ov} cycles, {nr} rst, every edge = model")
