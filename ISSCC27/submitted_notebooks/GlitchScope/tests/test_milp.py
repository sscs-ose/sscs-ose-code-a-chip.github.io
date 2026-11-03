"""Exact min-register retiming, FEAS, and the measurement-calibrated MILP."""
from pathlib import Path

from glitchscope.test_support import lib_path_or_none

ROOT = Path(__file__).resolve().parents[1]


def _fx(**kw):
    from glitchscope.optimize import GlitchFix
    return GlitchFix(ROOT / "bench/netlists/mac.v", lib_path_or_none(), vcd=ROOT / "bench/sim/mac.vcd",
                     sample=6, grid=4, log=lambda m: None, **kw)


def test_min_area_feas_and_calibrated_milp():
    try:
        import scipy.optimize  # noqa: F401
    except ImportError:
        return
    if not lib_path_or_none():
        return
    from glitchscope.milp_retime import feas, min_area, model_arrival
    from glitchscope.retime import is_legal, retimed_weights
    fx = _fx()
    tmin = fx.min_period()
    assert tmin is not None
    T = 1.2 * tmin
    d = fx._delays
    r_feas = feas(fx.rg, d, T, fx.c2q_ps, fx.timing.setup, fx.timing.in_delay)
    r_min = min_area(fx.rg, d, T, fx.c2q_ps, fx.timing.setup, max_hist=fx.M_EVAL - 1)
    for r in (r_feas, r_min):
        assert r is not None and is_legal(fx.rg, r)
        w = retimed_weights(fx.rg, r)
        t = model_arrival(fx.rg, d, w, fx.c2q_ps, fx.timing.in_delay)
        assert max(t[:fx.rg.C]) <= T - fx.timing.setup + 1e-6        # meets the period in the model
    flops = lambda r: fx.candidate(r, "x").n_flops                     # noqa: E731
    assert flops(r_min) <= flops(r_feas)                               # minimum registers
    base = fx.original()
    best = fx.milp_search(T, base=base, iters=1, reg_weights=(1.0,), time_limit=30)
    assert best is not None and best.verified and best.energy["total"] > 0


def test_neighbourhood_milp_stays_near_centre():
    try:
        import scipy.optimize  # noqa: F401
    except ImportError:
        return
    if not lib_path_or_none():
        return
    from glitchscope.milp_retime import min_area, solve
    from glitchscope.retime import is_legal
    fx = _fx()
    T = 1.2 * fx.min_period()
    d = fx._delays
    r0 = min_area(fx.rg, d, T, fx.c2q_ps, fx.timing.setup, max_hist=fx.M_EVAL - 1)
    alpha = [1.0] * fx.rg.C
    r = solve(fx.rg, d, alpha, 50.0, T, fx.c2q_ps, fx.timing.setup, in_delay=fx.timing.in_delay,
              max_hist=fx.M_EVAL - 1, time_limit=30, center=r0, radius=1)
    assert r is not None and is_legal(fx.rg, r)
    assert max(abs(a - b) for a, b in zip(r[:fx.rg.C], r0[:fx.rg.C])) <= 1
