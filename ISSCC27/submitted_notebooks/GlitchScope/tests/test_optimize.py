"""Register placement (retiming / pipelining): legal, function-preserving, verified."""
from pathlib import Path

from glitchscope.test_support import lib_path_or_none

ROOT = Path(__file__).resolve().parents[1]


def test_min_cut_matches_fallback():
    from glitchscope import retime
    # diamond s -> a -> {b, c} -> d -> t; cutting a's output costs 1, cutting b and c costs 2
    N, s, t = 6, 4, 5
    rows, cols, caps = [], [], []
    for a, b, c in [(s, 0, 10), (0, 1, 1), (0, 2, 1), (1, 3, 1), (2, 3, 1), (3, t, 10)]:
        rows.append(a); cols.append(b); caps.append(c)
    import sys
    side = retime._min_cut_source_side(N, rows, cols, caps, s, t)
    assert side[s] and not side[t] and side[0] and not side[1] and not side[2]
    saved = sys.modules.get("scipy.sparse.csgraph")
    sys.modules["scipy.sparse.csgraph"] = None          # force the pure-Python fallback
    try:
        assert retime._min_cut_source_side(N, rows, cols, caps, s, t) == side
    finally:
        if saved is not None:
            sys.modules["scipy.sparse.csgraph"] = saved
        else:
            del sys.modules["scipy.sparse.csgraph"]


def _fix(netlist, **kw):
    from glitchscope.optimize import GlitchFix
    return GlitchFix(ROOT / netlist, lib_path_or_none(), **kw)


def test_identity_and_loop_retiming_verified():
    if not lib_path_or_none():
        return
    from glitchscope.retime import fixed_lags
    fx = _fix("bench/netlists/mac.v", vcd=ROOT / "bench/sim/mac.vcd", sample=8, grid=6)
    r = [0] * fx.rg.n
    for v, x in fixed_lags(fx.rg, 0).items():
        r[v] = x
    ident = fx.measure(fx.candidate(r, "identity"))
    base = fx.original()
    assert ident.verified and abs(ident.energy["total"] - base.energy["total"]) < 1e-6
    # move the input registers into the multiplier (accumulator loop stays legal)
    moved = [c for c in fx.from_thresholds([0.35 * fx.dcrit], "x") if c.n_flops != len(fx.design.flops)]
    assert moved
    c = fx.measure(moved[0])
    assert c.verified and c.mismatches == 0 and c.energy["glitch"] < base.energy["glitch"]


def test_pipelining_adds_latency_and_verifies():
    if not lib_path_or_none():
        return
    fx = _fix("bench/netlists/mul4.v", random_vectors=60, period_ps=2000, latency=1, sample=8, grid=6)
    for wdw in (0.0, 0.1 * fx.dcrit):
        cands = fx.from_thresholds([0.5 * fx.dcrit], "p", window=wdw)
        assert cands
        c = fx.measure(cands[0])
        assert c.verified and c.n_flops > 0
        assert "gsreg_" in c.text and "module mul4" in c.text
        # ports are declared with exactly the spelling the connections use (no vector ports)
        assert "input \\a[0] ;" in c.text and "input [" not in c.text and "output [" not in c.text
    _, _, p = fx.timing.analyze(cands[0].weights)
    assert p < fx.timing.analyze([e[3] for e in fx.rg.edges])[2]       # pipelined: shorter critical path
