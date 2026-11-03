"""Signed circuit constraints for surrogate search and independent EM acceptance."""
import math

LIMITS = dict(zt_dbohm=59.0, bw_ghz=32.0, peak_db=1.0, gd_pp_ps=10.0, noise_pa=21.3, power_mw=28.2)


def constraints(p, m):
    """Signed normalized constraints: all <=0 iff the complete design passes.

    Accept raw tia_sim output or measured_metrics. Missing/nonfinite values
    fail. Headroom violation must be strictly below 1mV; all four Jc are 1..3.
    """
    bad = (1e6,) * 15
    if not isinstance(m, dict):
        return bad
    try:
        values = [float(m[k]) for k in LIMITS]
        if not all(math.isfinite(v) for v in values):
            return bad
        jc, headroom = m.get('jc'), m.get('headroom_v')
        if jc is None or headroom is None:
            import tia_sim as T
            op = m.get('op')
            if not isinstance(op, dict) or not op:
                return bad
            if jc is None:
                jc = T.jc_of(p, op)
            if headroom is None:
                headroom = T.headroom(op)
        jc, headroom = [float(v) for v in jc], float(headroom)
        if len(jc) != 4 or not all(math.isfinite(v) for v in jc + [headroom]) or headroom < 0:
            return bad
        return tuple([(59. - values[0]), (32. - values[1]) / 5.,
                      values[2] - 1., (values[3] - 10.) / 5.,
                      (values[4] - 21.3) / 5., (values[5] - 28.2) / 5.,
                      (headroom - (1e-3 - 1e-12)) / .1]
                     + [1. - j for j in jc] + [(j - 3.) / 3. for j in jc])
    except (KeyError, TypeError, ValueError, OverflowError):
        return bad

def feasible(p, m):
    return all(v <= 0 for v in constraints(p, m))

def score(p, m):
    """Feasibility barrier; bandwidth decides between strictly feasible rows."""
    c = constraints(p, m)
    if any(v > 0 for v in c):
        return 1000. + sum(max(0., v) + max(0., v) ** 2 for v in c)
    return -float(m['bw_ghz'])
