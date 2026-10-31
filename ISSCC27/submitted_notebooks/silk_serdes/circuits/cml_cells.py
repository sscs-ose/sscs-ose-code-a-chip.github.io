"""Local circuit code adapted from silk/examples/cml_cells.py.

Source revision: 3252db2f37f71c0b3f8c19174f57f206e4fa1cc7
Copyright (c) 2026 Levant Labs. MIT license; see LICENSE.
Circuit definitions are local to this demo; simulation uses Silk APIs.
"""


from silk import Module, Port


from silk.elements import elements


from circuits.process import SKY130


from circuits.stdcells import build_inverter


_RL = 2000.0             # load resistor (Ohm) -> swing ~ I*RL = 0.4 V


_WD, _LD = 4.0, 0.15     # differential / steering NMOS (um)


_WCK = 8.0               # clock-steering NMOS — wide, to fully commit the tail


_WH = 6.0                # cross-coupled hold NMOS — wide, for latch loop gain >1


_WT, _LT = 5.0, 0.5      # tail + mirror NMOS (um) — longer L for a cleaner mirror


def _sig_mul(imul):
    return max(1.0, round(imul ** 0.5))


def _suffix(imul):
    return "" if imul == 1.0 else f"_i{int(round(imul))}"


def build_cml_bias(*, tech=SKY130, imul=1.0) -> Module:
    """Generate a shared bias voltage with a diode-connected NMOS.

    The testbench supplies reference current at IBIAS. Tail-current ratios
    depend on each cell's transistor size relative to this reference device.
    """
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml_bias.cir", pdk_details=pdk,
               module_name="cml_bias" + _suffix(imul))
    m.define_module_ports({"VSS": Port.ground(), "IBIAS": Port.analog_input()})
    # Silk API: create the PDK device inside its owning module.
    with m:
        getattr(pdk, tech.nmos)("MBIAS", d="IBIAS", g="IBIAS", s="VSS", b="VSS",
                    w=tech.width(_WT * imul), l=tech.length(_LT))
    return m


def _tail(tail_net, imul=1.0, *, tech=SKY130):
    """The mirror tail NMOS shared by every steering cell (widens with current)."""
    pdk = tech.load()
    getattr(pdk, tech.nmos)("MT", d=tail_net, g="IBIAS", s="VSS", b="VSS", w=tech.width(_WT * imul), l=tech.length(_LT))


def _loads(outp, outn, rl=_RL):
    elements.resistor("RLP", p="VDD", n=outp, value=rl)
    elements.resistor("RLN", p="VDD", n=outn, value=rl)


def build_cml_latch(*, tech=SKY130, rl=_RL, imul=1.0) -> Module:
    """CML D-latch: transparent (tracks D) when ``CLKP > CLKN``, holds otherwise.

    A clock steering pair sends the tail current either to the **sample** pair
    (``DP``/``DN`` -> tracks D) or to the **hold** pair (cross-coupled, regenerates
    the stored differential). Both share the resistor loads. ``imul`` scales the
    tail current for speed (pair rl with rl/imul to hold the swing).
    """
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml_latch.cir", pdk_details=pdk,
               module_name="cml_latch" + _suffix(imul))
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
        "CLKP": Port.analog_input(), "CLKN": Port.analog_input(),
        "DP": Port.analog_input(), "DN": Port.analog_input(),
        "OUTP": Port.analog_output(), "OUTN": Port.analog_output(),
    })
    sm = _sig_mul(imul)
    wd, wck, wh = _WD * sm, _WCK * sm, _WH * sm
    with m:
        _tail("tail", imul, tech=tech)
        # clock steering: CLKP high -> current to sample pair; CLKN high -> hold.
        # Wider than the data pair so the clock swing fully COMMITS the tail to one
        # side (a partially-steered clock leaves both pairs live -> the latch stays
        # transparent and a master-slave built from it shifts through).
        getattr(pdk, tech.nmos)("MCKS", d="samp", g="CLKP", s="tail", b="VSS", w=tech.width(wck), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MCKH", d="hold", g="CLKN", s="tail", b="VSS", w=tech.width(wck), l=tech.length(_LD))
        # sample pair (tracks D)
        getattr(pdk, tech.nmos)("MSA", d="OUTN", g="DP", s="samp", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MSB", d="OUTP", g="DN", s="samp", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        # hold pair (cross-coupled) — wider for loop gain >1 so it truly latches.
        getattr(pdk, tech.nmos)("MHA", d="OUTN", g="OUTP", s="hold", b="VSS", w=tech.width(wh), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MHB", d="OUTP", g="OUTN", s="hold", b="VSS", w=tech.width(wh), l=tech.length(_LD))
        _loads("OUTP", "OUTN", rl)
    return m


def build_cml_dff(*, tech=SKY130, rl=_RL, imul=1.0) -> Module:
    """Master-slave CML D flip-flop from two latches — updates on the CLK **rising**
    edge. The master is transparent while CLK is LOW (it samples D), the slave
    while CLK is HIGH (it passes the master's held value), so the captured value
    appears at the output as CLK goes high. ``imul`` scales both latches for speed.
    """
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml_dff.cir", pdk_details=pdk,
               module_name="cml_dff" + _suffix(imul))
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
        "CLKP": Port.analog_input(), "CLKN": Port.analog_input(),
        "DP": Port.analog_input(), "DN": Port.analog_input(),
        "OUTP": Port.analog_output(), "OUTN": Port.analog_output(),
    })
    latch = build_cml_latch(rl=rl, imul=imul, tech=tech)
    # Silk API: place two latches and connect their named ports.
    # The master tracks while CLK is low, so its clock inputs are swapped.
    m.add_module(latch, "master", nets={
        "VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
        "CLKP": "CLKN", "CLKN": "CLKP", "DP": "DP", "DN": "DN",
        "OUTP": "mp", "OUTN": "mn"})
    # slave: transparent when CLK HIGH
    m.add_module(latch, "slave", nets={
        "VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
        "CLKP": "CLKP", "CLKN": "CLKN", "DP": "mp", "DN": "mn",
        "OUTP": "OUTP", "OUTN": "OUTN"})
    return m


def build_cml_mux2(*, tech=SKY130, rl=_RL, imul=1.0) -> Module:
    """CML 2:1 mux: a select steering pair routes the tail current to data pair A
    (``SELN`` high) or data pair B (``SELP`` high). ``OUT`` tracks the selected
    differential input — the serializer's load-vs-shift select, done in current.

    **Drive the SELECT wide.** SEL is a *control* signal, not CML data: at only
    ~0.4 V (CML data swing) the steering pair does not fully commit and the "off"
    data pair bleeds through (in the serializer: the register loads but never
    shifts). Drive SEL rail-ish (~0.6..1.8 V differential) so one data pair gets
    all the current. Data (A/B) stays at CML levels; only SEL goes wide.
    ``imul`` scales the tail current for speed (pair with rl/imul)."""
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml_mux2.cir", pdk_details=pdk,
               module_name="cml_mux2" + _suffix(imul))
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
        "AP": Port.analog_input(), "AN": Port.analog_input(),
        "BP": Port.analog_input(), "BN": Port.analog_input(),
        "SELP": Port.analog_input(), "SELN": Port.analog_input(),
        "OUTP": Port.analog_output(), "OUTN": Port.analog_output(),
    })
    sm = _sig_mul(imul)
    wd, wck = _WD * sm, _WCK * sm
    with m:
        _tail("tail", imul, tech=tech)
        # select steering: SELN high -> A pair; SELP high -> B pair. Wide, so the
        # select swing fully COMMITS the tail to one data pair — a partially
        # steered select leaves both pairs live and the "off" input bleeds
        # through (in the serializer: the register loads but never shifts).
        getattr(pdk, tech.nmos)("MSA", d="taila", g="SELN", s="tail", b="VSS", w=tech.width(wck), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MSB", d="tailb", g="SELP", s="tail", b="VSS", w=tech.width(wck), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MAA", d="OUTN", g="AP", s="taila", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MAB", d="OUTP", g="AN", s="taila", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MBA", d="OUTN", g="BP", s="tailb", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MBB", d="OUTP", g="BN", s="tailb", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        _loads("OUTP", "OUTN", rl)
    return m


def build_cml2cmos(*, tech=SKY130, rl=_RL, imul=1.0) -> Module:
    """CML differential ``INP``/``INM`` -> CMOS rail-to-rail ``Y``.

    A differential pair with a PMOS current-mirror load converts the small CML
    differential to a large single-ended swing; two inverters then restore it to
    full CMOS rails. ``Y`` follows ``INP``. ``imul`` scales it to keep up with a
    fast (speed-point) datapath output.
    """
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml2cmos.cir", pdk_details=pdk,
               module_name="cml2cmos" + _suffix(imul))
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
        "INP": Port.analog_input(), "INM": Port.analog_input(),
        "Y": Port.analog_output(),
    })
    sm = _sig_mul(imul)
    wd = _WD * sm
    with m:
        _tail("tail", imul, tech=tech)
        getattr(pdk, tech.nmos)("MA", d="nd", g="INP", s="tail", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("MB", d="se", g="INM", s="tail", b="VSS", w=tech.width(wd), l=tech.length(_LD))
        # PMOS current-mirror active load: mirror MA's branch into MB's -> gain
        getattr(pdk, tech.pmos)("MPL", d="nd", g="nd", s="VDD", b="VDD", w=tech.width(2 * wd), l=tech.length(_LD))
        getattr(pdk, tech.pmos)("MPR", d="se", g="nd", s="VDD", b="VDD", w=tech.width(2 * wd), l=tech.length(_LD))
    inv = build_inverter(with_tests=False, tech=tech)
    m.add_module(inv, "b1", nets={"VDD": "VDD", "VSS": "VSS", "A": "se", "Y": "ybar"})
    m.add_module(inv, "b2", nets={"VDD": "VDD", "VSS": "VSS", "A": "ybar", "Y": "Y"})
    return m


_DRV_RL = 50.0                    # channel-termination load (ohm)


_PD_IMUL = 4                      # 4 x IBIAS = 800 uA tail (fast into the 24 um gates)


_PD_RL = 875.0                    # -> I*rl = 0.70 V SE swing, output CM ~1.45 V


def build_cml_predriver(*, tech=SKY130, imul=_PD_IMUL, rl=_PD_RL) -> Module:
    """A shared-tail differential pair that increases the driver's input swing.

    The tail-device size scales with imul relative to the bias device. The loads set
    the output swing and common-mode voltage; transistor simulation checks
    the actual gain and settling under the output driver's gate load.
    """
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml_predriver.cir", pdk_details=pdk,
               module_name="cml_predriver")
    m.define_module_ports({
        "VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
        "INP": Port.analog_input(), "INM": Port.analog_input(),
        "OUTP": Port.analog_output(), "OUTN": Port.analog_output(),
    })
    sm = _sig_mul(imul)
    with m:
        _tail("tail", imul, tech=tech)
        getattr(pdk, tech.nmos)("M1", d="OUTN", g="INP", s="tail", b="VSS", w=tech.width(_WD * sm), l=tech.length(_LD))
        getattr(pdk, tech.nmos)("M2", d="OUTP", g="INM", s="tail", b="VSS", w=tech.width(_WD * sm), l=tech.length(_LD))
        _loads("OUTP", "OUTN", rl)
    return m


_FFE_TAPS = (-0.385, 1.0, -0.610, 0.106)   # Starting tap weights: precursor, main, postcursor 1 and 2.


_FFE_MAIN_MUL = 40                          # main slice tail = 40 x IBIAS = 8 mA


_FFE_PD_IMUL = 16                           # fast predriver (slews the wide output-pair gates)


_FFE_PD_RL = 200.0


_FFE_NAMES = ("pre", "main", "post1", "post2")


def build_cml_ffe_driver(*, tech=SKY130, taps=_FFE_TAPS, main_mul=_FFE_MAIN_MUL, rl=_DRV_RL,
                         pd_imul=_FFE_PD_IMUL, pd_rl=_FFE_PD_RL, eq_strength=1.0) -> Module:
    """Four current-steering taps with one predriver per tap.

    Rounded mirror multipliers approximate the requested tap weights. Swapping
    the output connections gives negative taps. Inputs provide each bit and
    its complement at delays -1, 0, +1 and +2 UI relative to the main tap.
    """
    pdk = tech.load()
    m = Module(tech.label, "/tmp", "cml_ffe_drv.cir", pdk_details=pdk,
               module_name="cml_ffe_driver")
    ports = {"VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
             "OUTP": Port.analog_output(), "OUTN": Port.analog_output()}
    for nm in _FFE_NAMES:
        ports[f"{nm.upper()}P"] = Port.analog_input()
        ports[f"{nm.upper()}N"] = Port.analog_input()
    m.define_module_ports(ports)
    with m:
        elements.resistor("RLP", p="VDD", n="OUTP", value=rl)
        elements.resistor("RLN", p="VDD", n="OUTN", value=rl)
    pd = build_cml_predriver(imul=pd_imul, rl=pd_rl, tech=tech)
    for nm, c in zip(_FFE_NAMES, taps):
        mm = max(1, round(abs(c) * main_mul))
        if nm != "main":
            mm = max(1, round(mm * eq_strength))
        m.add_module(pd, f"pd_{nm}", nets={"VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "INP": f"{nm.upper()}P", "INM": f"{nm.upper()}N",
            "OUTP": f"gp_{nm}", "OUTN": f"gn_{nm}"})
        with m:
            dA, dB = ("OUTN", "OUTP") if c > 0 else ("OUTP", "OUTN")   # swap = negative tap
            getattr(pdk, tech.nmos)(f"M{nm}A", d=dA, g=f"gp_{nm}", s=f"tail_{nm}", b="VSS", w=tech.width(_WD), l=tech.length(_LD), m=mm)
            getattr(pdk, tech.nmos)(f"M{nm}B", d=dB, g=f"gn_{nm}", s=f"tail_{nm}", b="VSS", w=tech.width(_WD), l=tech.length(_LD), m=mm)
            getattr(pdk, tech.nmos)(f"MT{nm}", d=f"tail_{nm}", g="IBIAS", s="VSS", b="VSS", w=tech.width(_WT), l=tech.length(_LT), m=mm)
    return m
