"""Local circuit code adapted from silk/examples/stdcells.py.

Source revision: 3252db2f37f71c0b3f8c19174f57f206e4fa1cc7
Copyright (c) 2026 Levant Labs. MIT license; see LICENSE.
These 1.8 V cell-test recipes use Silk sources, probes, metrics, and specs.
"""


import itertools


import numpy as np


from silk.elements import elements


from silk import sources


from silk.simulation import Transient
from silk.metrics import propagation_delay, sample


_VDD = 1.8


_TT_WIN = 3e-9          # per-combination hold (a gate settles in well under 1 ns)


_C_LOAD = 15e-15        # Assumed output capacitance for the cell tests.


def attach_truth_test(mod, *, in_ports, out_port, fn, w=_TT_WIN, with_levels=False):
    """Walk every input combination in one transient; output must equal ``fn``.

    ``fn`` takes one argument per input bit (in ``in_ports`` order) and returns the
    expected output bit. The metric samples the output near the end of each
    window and counts disagreements; one "0 mismatches" spec covers the table.
    With ``with_levels``, also report the lowest high voltage and highest low
    voltage across the input combinations.
    """
    combos = list(itertools.product((0, 1), repeat=len(in_ports)))
    # Silk API: register this reusable test on the circuit.
    tb = mod.create_test("truth")
    mut = {"VDD": "VDD", "VSS": "0"}
    for p in in_ports:
        mut[p] = p.lower()
    mut[out_port] = out_port.lower()
    tb.add_module_under_test(mut)
    tb.add_source(sources.VoltageSource("vdd", positive="VDD", negative="0",
                                        dc=_VDD))
    for i, p in enumerate(in_ports):
        levels = [c[i] for c in combos]
        # Silk API: generate each input lane from its truth-table bits.
        tb.add_source(sources.voltage.bitpattern(
            p.lower(), p=p.lower(), n="0", bits=levels,
            v1=0, v2=_VDD, ui=w, td=0, tr=100e-12, tf=100e-12))
    tb.add(elements.capacitor("cload", p=out_port.lower(), n="0",
                                      value=_C_LOAD))
    tb.add_sim_type(Transient(step=50e-12, stop=len(combos) * w, maxstep=200e-12))
    out = tb.probe(out_port.lower())
    tb.add_metric("truth_mismatches", _truth_mismatches, sig=out,
                  combos=combos, fn=fn, w=w)
    tb.add_spec(f"{mod.module_name} truth table exact (0 mismatches)",
                "truth_mismatches", "==", 0.0)
    if with_levels:
        tb.add_metric("voh_mv", _level, sig=out, combos=combos, fn=fn, w=w, high=True)
        tb.add_metric("vol_mv", _level, sig=out, combos=combos, fn=fn, w=w, high=False)
        # Each measured logic level must remain on its side of the threshold.
        tb.add_spec(f"{mod.module_name} VOH > VDD/2", "voh_mv", ">", _VDD / 2 * 1e3)
        tb.add_spec(f"{mod.module_name} VOL < VDD/2", "vol_mv", "<", _VDD / 2 * 1e3)
    return tb


def _truth_mismatches(sig, combos, fn, w, *, vdd=_VDD):
    times = (np.arange(len(combos)) + 0.9) * w
    # Silk API: sample the analog output; Python compares it with VDD/2.
    actual = sample(sig, x_new=times).y > vdd/2
    expected = [bool(fn(*combo)) for combo in combos]
    return float(np.count_nonzero(actual != expected))


def _level(sig, combos, fn, w, high):
    """Use native sampling, then select the worst expected high or low level."""
    times = [(i + 0.9) * w for i, combo in enumerate(combos) if bool(fn(*combo)) == high]
    if not times:
        return float("nan")
    values = sample(sig, x_new=times).y
    return float((np.min(values) if high else np.max(values)) * 1e3)


DELAY_METRIC = "tp_ps"


_DLY_STOP = 10e-9


_DLY_RISE, _DLY_FALL = 2e-9, 6e-9      # toggled input's edges


def attach_delay_test(mod, *, in_ports, out_port, toggle, hold, name="delay"):
    """Toggle one input past a clean edge; measure input->output tp (ps).

    The toggled input pulses 0->1->0; the others are held at their
    **non-controlling** level (``hold``) so the edge propagates. tp is the mean
    of the two 50%-crossing delays (rise-driven and fall-driven).
    """
    # Silk API: register this reusable test on the circuit.
    tb = mod.create_test(name)
    mut = {"VDD": "VDD", "VSS": "0"}
    for p in in_ports:
        mut[p] = p.lower()
    mut[out_port] = out_port.lower()
    tb.add_module_under_test(mut)
    tb.add_source(sources.VoltageSource("vdd", positive="VDD", negative="0",
                                        dc=_VDD))
    for p in in_ports:
        if p == toggle:
            tb.add_source(sources.VoltageSource(
                p.lower(), positive=p.lower(), negative="0", dc=0,
                pulse=sources.Pulse(v1=0, v2=_VDD, td=_DLY_RISE, tr=50e-12,
                                    tf=50e-12, pw=_DLY_FALL - _DLY_RISE, per=1.0)))
        else:
            tb.add_source(sources.VoltageSource(
                p.lower(), positive=p.lower(), negative="0",
                dc=_VDD if hold[p] else 0.0))
    tb.add(elements.capacitor("cload", p=out_port.lower(), n="0",
                                      value=_C_LOAD))
    tb.add_sim_type(Transient(step=5e-12, stop=_DLY_STOP, maxstep=20e-12))
    in_probe = tb.probe(toggle.lower())
    out_probe = tb.probe(out_port.lower())
    tb.add_metric(DELAY_METRIC, _gate_tp, sig_in=in_probe, sig_out=out_probe)
    tb.add_spec(f"{mod.module_name} tp measured (< 1 ns)", DELAY_METRIC, "<", 1000.0)
    return tb


def _gate_tp(sig_in, sig_out):
    """Mean of rise-driven and fall-driven native propagation delays, in ps."""
    delays = [propagation_delay(sig_in, sig_out, in_threshold=_VDD/2,
                               out_threshold=_VDD/2, in_edge=edge, out_edge='any')
              for edge in ('rising', 'falling')]
    return float(np.mean(delays) * 1e12)


_CLKQ_RISE_METRIC = "clk_q_rise_ps"


_CLKQ_FALL_METRIC = "clk_q_fall_ps"


_CAP_ERR_METRIC = "capture_errors"


_CLKQ_MAX_PS = 1000.0


_TIM_EDGES = (4e-9, 12e-9, 20e-9)


_TIM_D_FALL = 9e-9


_TIM_D_RISE = 17e-9


_TIM_STOP = 25e-9


def attach_dff_timing_test(mod):
    """Clk-to-Q (rise and fall) and functional capture, in one transient.

    Clear, release, then capture 1 (edge 0), 0 (edge 1), 1 (edge 2) with D held
    stable well before each edge. This measures output delay, not setup time.
    """
    # Silk API: register this reusable test on the circuit.
    tb = mod.create_test("timing")
    tb.add_module_under_test({"VDD": "VDD", "VSS": "0", "D": "d", "CLK": "clk",
                              "CLRB": "clrb", "Q": "q", "QB": "qb"})
    tb.add_source(sources.VoltageSource("vdd", positive="VDD", negative="0",
                                        dc=_VDD))
    tb.add_source(sources.VoltageSource(
        "clk", positive="clk", negative="0", dc=0,
        pulse=sources.Pulse(v1=0, v2=_VDD, td=_TIM_EDGES[0], tr=50e-12,
                            tf=50e-12, pw=4e-9, per=8e-9)))
    tb.add_source(sources.VoltageSource(
        "clrb", positive="clrb", negative="0", dc=0,
        pwl=sources.PWL().add(0, 0).add(3e-9, 0).add(3.1e-9, _VDD)))
    tb.add_source(sources.VoltageSource(
        "d", positive="d", negative="0", dc=0,
        pwl=sources.PWL().add(0, _VDD).add(_TIM_D_FALL, _VDD)
        .add(_TIM_D_FALL + 50e-12, 0).add(_TIM_D_RISE, 0)
        .add(_TIM_D_RISE + 50e-12, _VDD).add(_TIM_STOP, _VDD)))
    tb.add_sim_type(Transient(step=20e-12, stop=_TIM_STOP, maxstep=50e-12))
    clk, q = tb.probe("clk"), tb.probe("q")
    # Silk API: measure crossing delay in seconds; metric arithmetic converts to ps.
    for name, edge, start in (("rise", "rising", _TIM_EDGES[0]),
                              ("fall", "falling", _TIM_EDGES[1])):
        delay = tb.add_metric(
            f"clk_q_{name}_s", propagation_delay, sig_in=clk, sig_out=q,
            in_threshold=_VDD/2, out_threshold=_VDD/2,
            in_edge="rising", out_edge=edge, start=start-1e-9)
        tb.add_metric(f"clk_q_{name}_ps", delay * 1e12)
    tb.add_metric(_CAP_ERR_METRIC, _capture_errors, sig=q)
    tb.add_spec(f"clk-Q rise < {_CLKQ_MAX_PS:.0f} ps", _CLKQ_RISE_METRIC, "<",
                _CLKQ_MAX_PS)
    tb.add_spec(f"clk-Q fall < {_CLKQ_MAX_PS:.0f} ps", _CLKQ_FALL_METRIC, "<",
                _CLKQ_MAX_PS)
    tb.add_spec("captures D on every edge (0 errors)", _CAP_ERR_METRIC, "==", 0.0)
    return tb


def _capture_errors(sig):
    """Illustrate native sampling followed by a simple voltage threshold."""
    # Silk API: sample the analog output; Python compares it with VDD/2.
    actual = sample(sig, x_new=np.asarray(_TIM_EDGES) + 3e-9).y > _VDD/2
    return float(np.count_nonzero(actual != (1, 0, 1)))
