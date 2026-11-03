"""Local circuit code adapted from silk/examples/stdcells.py.

Source revision: 3252db2f37f71c0b3f8c19174f57f206e4fa1cc7
Copyright (c) 2026 Levant Labs. MIT license; see LICENSE.
Circuit definitions are local to this demo; simulation uses Silk APIs.
"""


import numpy as np
from silk.metrics import sample
from silk.signals import Signal


from silk import Module, Port


from circuits.process import SKY130


_VDD = 1.8


_L = 0.15              # channel length (um) — min-L: these are speed cells


_WN = 1.0             # unit NMOS width (um)


_WP = 2.0             # unit PMOS width (um) — ~2x for mobility-matched rise/fall


_STACK_WIDEN = {1: 1, 2: 2, 3: 3}


_CELL_VARIANTS = {
    "inverter": ("x1",), "nand2": ("x1",), "nand3": ("x1",),
    "dff": ("x1",), "mux2": ("tg",),
}

# Nominal delays for the simple behavioral cell models, in picoseconds.
_TP_NOM_PS = {"inverter": 50.0, "nand2": 49.0, "nand3": 55.0, "mux2": 78.0}


_CLKQ_NOM_PS = 106.0             # DFF clk-to-Q (avg of rise/fall) for the twin


def _require_variant(variant, cell):
    allowed = _CELL_VARIANTS[cell]
    if variant not in allowed:
        raise ValueError(f"unknown {cell} variant {variant!r}; implemented: {allowed}")


def _make_comb_model(in_ports, out_port, boolfn):
    """A behavioral model for a combinational cell: boolean ``boolfn`` of the
    thresholded inputs, emitted rail-to-rail, delayed by ``params['tp_s']``.

    ``boolfn`` takes numpy bool arrays (one per input port, in order) and returns
    a numpy bool array. This model uses ideal voltage levels and a fixed delay;
    transistor simulation is needed to check electrical behavior.
    """
    def model(ports, t, params):
        vdd = float(params["vdd"])
        args = [np.asarray(getattr(ports, p).v, dtype=float) > vdd / 2 for p in in_ports]
        out = np.where(boolfn(*args), vdd, 0.0)
        # Silk API: sample the waveform at delayed times, holding its endpoints.
        wave = Signal(out_port, 'tran', 'time', 'voltage', t, out)
        getattr(ports, out_port).v = sample(wave, x_new=t-float(params['tp_s'])).y
    return model


def _dff_model(ports, t, params):
    """Behavioral D flip-flop: capture D on CLK rising edges, async CLRB clear,
    output delayed by ``params['tcq_s']`` (the measured clk-to-Q).

    Whole-array model for feed-forward use. It does not define a causal
    composed feedback loop; that requires sample execution and explicit delays.
    """
    vdd = float(params["vdd"])
    clk = np.asarray(ports.CLK.v, dtype=float) > vdd / 2
    d = np.asarray(ports.D.v, dtype=float) > vdd / 2
    clrb = np.asarray(ports.CLRB.v, dtype=float) > vdd / 2
    q_bool = np.zeros(len(t), dtype=bool)
    state = False
    for i in range(len(t)):
        if not clrb[i]:
            state = False
        elif clk[i] and i > 0 and not clk[i - 1]:      # rising edge
            state = bool(d[i])
        q_bool[i] = state
    tcq = float(params["tcq_s"])
    wave = Signal('Q', 'tran', 'time', 'voltage', t, np.where(q_bool, vdd, 0.0))
    # Silk API: apply the fixed clock-to-Q delay to the captured bit waveform.
    ports.Q.v = sample(wave, x_new=t-tcq).y
    ports.QB.v = vdd - ports.Q.v


def inverter(a: int) -> int:
    return 1 - a


def nand2(a: int, b: int) -> int:
    return 1 - (a & b)


def nand3(a: int, b: int, c: int) -> int:
    return 1 - (a & b & c)


def mux2(a: int, b: int, s: int) -> int:
    return b if s else a


def build_inverter(*, tech=SKY130, variant="x1", wn=_WN, wp=_WP, l=_L, m=1, name="inv",
                   with_tests=True) -> Module:
    """CMOS inverter: ``Y = NOT A``. Pull-up PMOS over pull-down NMOS.

    ``m`` places identical FETs in parallel to scale the drive strength.
    The segmented driver uses this multiplier for its output slices. ``name`` sets
    the ``module_name``: independently built bodies in the same parent need
    distinct names (or native variants=True). Silk refuses conflicting
    definitions rather than silently selecting one.
    """
    pdk = tech.load()
    _require_variant(variant, "inverter")
    m_mod = Module(tech.label, "/tmp", f"{name}.cir", pdk_details=pdk,
                   module_name=name)
    m_mod.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(),
        "A": Port.analog_input(), "Y": Port.analog_output(),
    })
    # Silk API: devices created in this block belong to this module.
    # The demo Technology mapping selects the PDK factory and dimensions.
    with m_mod:
        getattr(pdk, tech.pmos)("MP", d="Y", g="A", s="VDD", b="VDD", w=tech.width(wp), l=tech.length(l), m=m)
        getattr(pdk, tech.nmos)("MN", d="Y", g="A", s="VSS", b="VSS", w=tech.width(wn), l=tech.length(l), m=m)
    # Silk API: attach a simple logic-and-delay model for behavioral simulation.
    m_mod.set_behavioral_model(_make_comb_model(["A"], "Y", lambda a: ~a),
                               params={"vdd": _VDD, "tp_s": _TP_NOM_PS["inverter"] * 1e-12})
    if with_tests:
        from characterization.testbenches import (
            attach_truth_test, attach_delay_test, attach_dff_timing_test,
        )
        attach_truth_test(m_mod, in_ports=["A"], out_port="Y", fn=inverter)
        attach_delay_test(m_mod, in_ports=["A"], out_port="Y", toggle="A", hold={})
    return m_mod


def build_nand2(*, tech=SKY130, variant="x1", wn=_WN, wp=_WP, l=_L, with_tests=True) -> Module:
    """2-input NAND: ``Y = NOT(A AND B)``. PMOS parallel, NMOS series (2x wide)."""
    pdk = tech.load()
    _require_variant(variant, "nand2")
    m = Module(tech.label, "/tmp", "nand2.cir", pdk_details=pdk,
               module_name="nand2")
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(),
        "A": Port.analog_input(), "B": Port.analog_input(),
        "Y": Port.analog_output(),
    })
    ws = wn * _STACK_WIDEN[2]
    with m:
        getattr(pdk, tech.pmos)("MPA", d="Y", g="A", s="VDD", b="VDD", w=tech.width(wp), l=tech.length(l))
        getattr(pdk, tech.pmos)("MPB", d="Y", g="B", s="VDD", b="VDD", w=tech.width(wp), l=tech.length(l))
        getattr(pdk, tech.nmos)("MNA", d="Y", g="A", s="nx", b="VSS", w=tech.width(ws), l=tech.length(l))
        getattr(pdk, tech.nmos)("MNB", d="nx", g="B", s="VSS", b="VSS", w=tech.width(ws), l=tech.length(l))
    m.set_behavioral_model(
        _make_comb_model(["A", "B"], "Y", lambda a, b: ~(a & b)),
        params={"vdd": _VDD, "tp_s": _TP_NOM_PS["nand2"] * 1e-12})
    if with_tests:
        from characterization.testbenches import (
            attach_truth_test, attach_delay_test, attach_dff_timing_test,
        )
        attach_truth_test(m, in_ports=["A", "B"], out_port="Y",
                          fn=nand2)
        attach_delay_test(m, in_ports=["A", "B"], out_port="Y", toggle="A",
                          hold={"B": 1})
    return m


def build_nand3(*, tech=SKY130, variant="x1", wn=_WN, wp=_WP, l=_L, with_tests=True) -> Module:
    """3-input NAND: ``Y = NOT(A AND B AND C)``. NMOS triple stack (3x wide)."""
    pdk = tech.load()
    _require_variant(variant, "nand3")
    m = Module(tech.label, "/tmp", "nand3.cir", pdk_details=pdk,
               module_name="nand3")
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(),
        "A": Port.analog_input(), "B": Port.analog_input(),
        "C": Port.analog_input(), "Y": Port.analog_output(),
    })
    ws = wn * _STACK_WIDEN[3]
    with m:
        getattr(pdk, tech.pmos)("MPA", d="Y", g="A", s="VDD", b="VDD", w=tech.width(wp), l=tech.length(l))
        getattr(pdk, tech.pmos)("MPB", d="Y", g="B", s="VDD", b="VDD", w=tech.width(wp), l=tech.length(l))
        getattr(pdk, tech.pmos)("MPC", d="Y", g="C", s="VDD", b="VDD", w=tech.width(wp), l=tech.length(l))
        getattr(pdk, tech.nmos)("MNA", d="Y", g="A", s="nx1", b="VSS", w=tech.width(ws), l=tech.length(l))
        getattr(pdk, tech.nmos)("MNB", d="nx1", g="B", s="nx2", b="VSS", w=tech.width(ws), l=tech.length(l))
        getattr(pdk, tech.nmos)("MNC", d="nx2", g="C", s="VSS", b="VSS", w=tech.width(ws), l=tech.length(l))
    m.set_behavioral_model(
        _make_comb_model(["A", "B", "C"], "Y", lambda a, b, c: ~(a & b & c)),
        params={"vdd": _VDD, "tp_s": _TP_NOM_PS["nand3"] * 1e-12})
    if with_tests:
        from characterization.testbenches import (
            attach_truth_test, attach_delay_test, attach_dff_timing_test,
        )
        attach_truth_test(m, in_ports=["A", "B", "C"], out_port="Y",
                          fn=nand3)
        attach_delay_test(m, in_ports=["A", "B", "C"], out_port="Y", toggle="A",
                          hold={"B": 1, "C": 1})
    return m


def build_mux2(*, tech=SKY130, variant="tg", wn=_WN, wp=_WP, l=_L, with_tests=True) -> Module:
    """Build a 2:1 mux from two transmission gates and a select inverter.

    S=0 connects A to Y; S=1 connects B to Y. The output has no restoring
    buffer, so its load matters when checking transistor-level timing.
    """
    pdk = tech.load()
    _require_variant(variant, "mux2")
    m = Module(tech.label, "/tmp", "mux2.cir", pdk_details=pdk,
               module_name="mux2")
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(),
        "A": Port.analog_input(), "B": Port.analog_input(),
        "S": Port.analog_input(), "Y": Port.analog_output(),
    })
    inv = build_inverter(wn=wn, wp=wp, l=l, with_tests=False, tech=tech)
    m.add_module(inv, "ginv", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "S", "Y": "sbar"})
    with m:
        # TG0: on when S=0 (NMOS gate = Sbar high, PMOS gate = S low) -> Y = A.
        getattr(pdk, tech.nmos)("MN0", d="A", g="sbar", s="Y", b="VSS", w=tech.width(wn), l=tech.length(l))
        getattr(pdk, tech.pmos)("MP0", d="A", g="S", s="Y", b="VDD", w=tech.width(wp), l=tech.length(l))
        # TG1: on when S=1 -> Y = B.
        getattr(pdk, tech.nmos)("MN1", d="B", g="S", s="Y", b="VSS", w=tech.width(wn), l=tech.length(l))
        getattr(pdk, tech.pmos)("MP1", d="B", g="sbar", s="Y", b="VDD", w=tech.width(wp), l=tech.length(l))
    m.set_behavioral_model(
        _make_comb_model(["A", "B", "S"], "Y",
                         lambda a, b, s: np.where(s, b, a)),
        params={"vdd": _VDD, "tp_s": _TP_NOM_PS["mux2"] * 1e-12})
    if with_tests:
        from characterization.testbenches import (
            attach_truth_test, attach_delay_test, attach_dff_timing_test,
        )
        attach_truth_test(m, in_ports=["A", "B", "S"], out_port="Y",
                          fn=mux2)
        attach_delay_test(m, in_ports=["A", "B", "S"], out_port="Y", toggle="A",
                          hold={"B": 0, "S": 0})
    return m


def build_dff(*, tech=SKY130, variant="x1", wn=_WN, wp=_WP, l=_L, with_tests=True) -> Module:
    """Positive-edge D flip-flop with active-low clear — the classic 6-NAND cell.

    The 7474's structure minus the preset (tie-offs folded away)::

        n1 = NAND2(n4, n2);  n2 = NAND3(n1, CLRB, CLK)
        n3 = NAND3(n2, CLK, n4);  n4 = NAND3(n3, CLRB, D)
        Q  = NAND2(n2, QB);  QB = NAND3(Q, n3, CLRB)

    ``CLRB = 0`` forces ``Q = 0`` asynchronously. Two NAND2s + four NAND3s = 32
    transistors. Composed from *this* file's gates. Behavioral twin captures D on
    CLK edges with the measured clk-to-Q delay (feed-forward use only — a flop in
    a feedback LFSR must run in SPICE).
    """
    pdk = tech.load()
    _require_variant(variant, "dff")
    m = Module(tech.label, "/tmp", "dff.cir", pdk_details=pdk,
               module_name="dff")
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(),
        "D": Port.analog_input(), "CLK": Port.analog_input(),
        "CLRB": Port.analog_input(),
        "Q": Port.analog_output(), "QB": Port.analog_output(),
    })
    nand2 = build_nand2(wn=wn, wp=wp, l=l, with_tests=False, tech=tech)
    nand3 = build_nand3(wn=wn, wp=wp, l=l, with_tests=False, tech=tech)
    m.add_module(nand2, "g1", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "n4", "B": "n2", "Y": "n1"})
    m.add_module(nand3, "g2", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "n1", "B": "CLRB", "C": "CLK", "Y": "n2"})
    m.add_module(nand3, "g3", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "n2", "B": "CLK", "C": "n4", "Y": "n3"})
    m.add_module(nand3, "g4", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "n3", "B": "CLRB", "C": "D", "Y": "n4"})
    m.add_module(nand2, "g5", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "n2", "B": "QB", "Y": "Q"})
    m.add_module(nand3, "g6", nets={"VDD": "VDD", "VSS": "VSS",
                                     "A": "Q", "B": "n3", "C": "CLRB", "Y": "QB"})
    m.set_behavioral_model(_dff_model,
                           params={"vdd": _VDD, "tcq_s": _CLKQ_NOM_PS * 1e-12})
    if with_tests:
        from characterization.testbenches import (
            attach_truth_test, attach_delay_test, attach_dff_timing_test,
        )
        attach_dff_timing_test(m)
    return m
