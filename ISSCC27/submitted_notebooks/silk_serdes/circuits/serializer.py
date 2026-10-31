"""Local circuit code adapted from silk/examples/serializer_example.py.

Source revision: 3252db2f37f71c0b3f8c19174f57f206e4fa1cc7
Copyright (c) 2026 Levant Labs. MIT license; see LICENSE.
Circuit definitions are local to this demo; simulation uses Silk APIs.
"""


from silk import Module, Port


from circuits.process import SKY130


from circuits import stdcells as sc


from circuits import cml_cells as cml


RATIO = 10


_CML_IMUL = 4.0


_CML_RL = 2000.0 / _CML_IMUL      # 500 ohm -> 0.4 V swing


def build_serializer(*, tech=SKY130, variant="cmos", ratio=RATIO) -> Module:
    """A ``ratio``:1 load-shift serializer in the chosen logic family.

    Stage i: ``mux(S=LOAD, A=shift_in, B=lane_i) -> DFF -> Q_i``; ``shift_in`` for
    stage i is ``Q_{i+1}`` (0 for the last stage); SOUT = Q0. On LOAD every stage
    captures its lane; otherwise the word shifts toward Q0. LOAD is the register's
    reset — the first LOAD forces a known state, so no async clear is needed.
    """
    if variant == "cmos":
        return _build_cmos_serializer(ratio, tech=tech)
    if variant == "cml":
        return _build_cml_serializer(ratio, tech=tech)
    raise ValueError(f"unknown serializer variant {variant!r}; use 'cmos' or 'cml'")


def _build_cmos_serializer(ratio, *, tech=SKY130) -> Module:
    pdk = tech.load()
    mod = Module(tech.label, "/tmp", "ser_cmos.cir", pdk_details=pdk,
                 module_name="ser_cmos")
    ports = {"VDD": Port.supply(), "VSS": Port.ground(),
             "CLK": Port.analog_input(), "LOAD": Port.analog_input(),
             "SOUT": Port.analog_output()}
    for i in range(ratio):
        ports[f"P{i}"] = Port.analog_input()
    # Silk API: declare the external pins and their electrical roles.
    mod.define_module_ports(ports)

    mux = sc.build_mux2(with_tests=False, tech=tech)
    dff = sc.build_dff(with_tests=False, tech=tech)
    for i in range(ratio):
        q = "SOUT" if i == 0 else f"q{i}"
        shift_in = f"q{i+1}" if i < ratio - 1 else "VSS"
        # Silk API: place the mux and flip-flop and connect their named ports.
        mod.add_module(mux, f"mux{i}", nets={
            "VDD": "VDD", "VSS": "VSS", "A": shift_in, "B": f"P{i}",
            "S": "LOAD", "Y": f"d{i}"})
        mod.add_module(dff, f"ff{i}", nets={
            "VDD": "VDD", "VSS": "VSS", "D": f"d{i}", "CLK": "CLK",
            "CLRB": "VDD", "Q": q, "QB": f"qb{i}"})
    return mod


def _build_cml_serializer(ratio, *, tech=SKY130, rl=_CML_RL, imul=_CML_IMUL) -> Module:
    """Differential mux and flip-flop stages with a shared external IBIAS port.

    A converter on stage 0 provides a CMOS SOUT for observation. Lower load
    resistance and higher tail current reduce the RC delay at similar swing.
    """
    pdk = tech.load()
    mod = Module(tech.label, "/tmp", "ser_cml.cir", pdk_details=pdk,
                 module_name="ser_cml")
    ports = {"VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
             "CLKP": Port.analog_input(), "CLKN": Port.analog_input(),
             "LOADP": Port.analog_input(), "LOADN": Port.analog_input(),
             # SOUT = the cml2cmos-converted observation output; SOUTP/SOUTN = the
             # datapath's own DIFFERENTIAL serial output (stage-0 Q) — the native
             # CML interface a downstream CML block (e.g. a TX driver) taps.
             "SOUT": Port.analog_output(),
             "SOUTP": Port.analog_output(), "SOUTN": Port.analog_output()}
    for i in range(ratio):
        ports[f"P{i}P"] = Port.analog_input()
        ports[f"P{i}N"] = Port.analog_input()
    # Silk API: declare the external pins and their electrical roles.
    mod.define_module_ports(ports)

    muxc = cml.build_cml_mux2(rl=rl, imul=imul, tech=tech)
    dffc = cml.build_cml_dff(rl=rl, imul=imul, tech=tech)
    for i in range(ratio):
        qp = "SOUTP" if i == 0 else f"qp{i}"
        qn = "SOUTN" if i == 0 else f"qn{i}"
        # last stage shifts in a logic 0: AP low / AN high (CML sign for 0)
        sip, sin = (f"qp{i+1}", f"qn{i+1}") if i < ratio - 1 else ("VSS", "VDD")
        # mux: A = shift-in (next stage Q), B = lane i, SEL = LOAD
        # Silk API: compose differential mux and flip-flop stages.
        mod.add_module(muxc, f"mux{i}", nets={
            "VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "AP": sip, "AN": sin, "BP": f"P{i}P", "BN": f"P{i}N",
            "SELP": "LOADP", "SELN": "LOADN", "OUTP": f"mp{i}", "OUTN": f"mn{i}"})
        mod.add_module(dffc, f"ff{i}", nets={
            "VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "CLKP": "CLKP", "CLKN": "CLKN", "DP": f"mp{i}", "DN": f"mn{i}",
            "OUTP": qp, "OUTN": qn})
    # cml2cmos on stage 0's differential Q (SOUTP/SOUTN) -> the single-ended SOUT
    mod.add_module(cml.build_cml2cmos(imul=imul, tech=tech), "obs", nets={
        "VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
        "INP": "SOUTP", "INM": "SOUTN", "Y": "SOUT"})
    return mod
