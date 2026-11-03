"""Local circuit code adapted from silk/examples/serdes_tx_example.py.

Source revision: 3252db2f37f71c0b3f8c19174f57f206e4fa1cc7
Copyright (c) 2026 Levant Labs. MIT license; see LICENSE.
CMOS input predrivers now isolate retiming storage nodes from the FFE gates.
Set cmos_predriver=False to reproduce the original extracted topology.
"""

from circuits.drivers import build_cmos_ffe_driver, build_cml_ffe_driver

from silk import Module, Port


from circuits.process import SKY130


from circuits import cml_cells as cml


_R_TERM = 100.0                  # differential termination at RX (ohm)


def build_serdes_tx(*, tech=SKY130, variant="cmos", n_words=3, structural=False,
                    cmos_predriver=True, eq_strength=1.0, db_path=None) -> Module:
    """Build the local serializer, retiming, driver and RC-channel hierarchy.

    CMOS uses input predrivers by default. ``cmos_predriver=False`` restores
    the extracted direct-load circuit for diagnosis; it has no effect on CML.
    Construction does not simulate. Both architectures use the shared link test.
    """
    if variant == "cml" and tech.name != "sky130":
        raise ValueError("CML process port is not supported; use CMOS for gf180mcu")
    pdk = tech.load()
    from circuits import serializer as ser
    from silk.elements import elements
    # Silk API: define a reusable circuit block with named ports and instances.
    mod = Module(tech.label, "/tmp", f"serdes_tx_{variant}.cir",
                 pdk_details=pdk, module_name=f"serdes_tx_{variant}", db_path=db_path)
    if variant == "cml":
        # CML signal path: serializer, three retiming stages, FFE, then channel.
        mod.define_module_ports({
            "VDD": Port.supply(), "VSS": Port.ground(), "IBIAS": Port.analog_input(),
            "CLKP": Port.analog_input(), "CLKN": Port.analog_input(),
            "LOADP": Port.analog_input(), "LOADN": Port.analog_input(),
            "PADP": Port.analog_output(), "PADN": Port.analog_output(),
            "RXP": Port.analog_output(), "RXN": Port.analog_output(),
            **{f"P{i}P": Port.analog_input() for i in range(ser.RATIO)},
            **{f"P{i}N": Port.analog_input() for i in range(ser.RATIO)}})
        smod = ser.build_serializer(variant="cml", ratio=ser.RATIO, tech=tech)
        # tap the serializer's DIFFERENTIAL serial output (SOUTP/SOUTN); SOUT is the
        # cml2cmos observation output, parked on sobs.
        snets = {"VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS", "CLKP": "CLKP",
                 "CLKN": "CLKN", "LOADP": "LOADP", "LOADN": "LOADN",
                 "SOUT": "sobs", "SOUTP": "soutp", "SOUTN": "soutn"}
        for i in range(ser.RATIO):
            snets[f"P{i}P"] = f"P{i}P"
            snets[f"P{i}N"] = f"P{i}N"
        mod.add_module(smod, "ser", nets=snets)
        # 3-stage CML DFF retime chain -> the FFE tap delays: d1/d2/d3 = the serial
        # output delayed 1/2/3 UI. The PRECURSOR tap uses the UN-retimed SOUTP/SOUTN
        # (the look-ahead bit b[n+1], relative to the main = d1 = b[n]).
        rt = cml.build_cml_dff(tech=tech)
        mod.add_module(rt, "rt1", nets={"VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "CLKP": "CLKP", "CLKN": "CLKN", "DP": "soutp", "DN": "soutn",
            "OUTP": "d1p", "OUTN": "d1n"})
        mod.add_module(rt, "rt2", nets={"VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "CLKP": "CLKP", "CLKN": "CLKN", "DP": "d1p", "DN": "d1n",
            "OUTP": "d2p", "OUTN": "d2n"})
        mod.add_module(rt, "rt3", nets={"VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "CLKP": "CLKP", "CLKN": "CLKN", "DP": "d2p", "DN": "d2n",
            "OUTP": "d3p", "OUTN": "d3n"})
        # Silk API: connect the locally defined FFE driver to the retimed bits.
        # PRE uses the serializer output; MAIN, POST1, POST2 use delays 1, 2, 3 UI.
        mod.add_module(build_cml_ffe_driver(tech=tech, eq_strength=eq_strength), "driver", nets={
            "VDD": "VDD", "VSS": "VSS", "IBIAS": "IBIAS",
            "PREP": "soutp", "PREN": "soutn", "MAINP": "d1p", "MAINN": "d1n",
            "POST1P": "d2p", "POST1N": "d2n", "POST2P": "d3p", "POST2N": "d3n",
            "OUTP": "PADP", "OUTN": "PADN"})
        with mod:
            # Silk API: add ideal channel resistors and capacitors.
            # CML has 50 ohms and 2 pF per leg; its driver supplies the loads.
            # There is no additional differential receiver termination here.
            elements.resistor("R_chp", p="PADP", n="RXP", value=50.0)
            elements.resistor("R_chn", p="PADN", n="RXN", value=50.0)
            elements.capacitor("C_chp", p="RXP", n="VSS", value=2e-12)
            elements.capacitor("C_chn", p="RXN", n="VSS", value=2e-12)
        return mod
    if variant == "cmos":
        mod.define_module_ports({
            "VDD": Port.supply(), "VSS": Port.ground(),
            "CLK": Port.analog_input(), "LOAD": Port.analog_input(),
            "PADP": Port.analog_output(), "PADN": Port.analog_output(),
            "RXP": Port.analog_output(), "RXN": Port.analog_output(),
            **{f"P{i}": Port.analog_input() for i in range(ser.RATIO)}})
        smod = ser.build_serializer(variant="cmos", ratio=ser.RATIO, tech=tech)
        snets = {"VDD": "VDD", "VSS": "VSS", "CLK": "CLK", "LOAD": "LOAD",
                 "SOUT": "sout"}
        for i in range(ser.RATIO):
            snets[f"P{i}"] = f"P{i}"
        mod.add_module(smod, "ser", nets=snets)
        # 4-tap FFE retime chain: main is the 1-UI-retimed bit (d1); the precursor
        # is the un-retimed serializer output (SOUT = the LOOK-AHEAD bit b[n+1]);
        # post1/post2 are two further DFF delays (d2, d3). The DFFs emit Q AND QB, so
        # the per-tap complements the driver needs are free (only the precursor's
        # complement soutb takes one extra inverter).
        from circuits.stdcells import build_dff, build_inverter
        dff = build_dff(with_tests=False, tech=tech)
        mod.add_module(dff, "rt1", nets={"VDD": "VDD", "VSS": "VSS", "D": "sout",
                        "CLK": "CLK", "CLRB": "VDD", "Q": "d1", "QB": "d1b"})
        mod.add_module(dff, "rt2", nets={"VDD": "VDD", "VSS": "VSS", "D": "d1",
                        "CLK": "CLK", "CLRB": "VDD", "Q": "d2", "QB": "d2b"})
        mod.add_module(dff, "rt3", nets={"VDD": "VDD", "VSS": "VSS", "D": "d2",
                        "CLK": "CLK", "CLRB": "VDD", "Q": "d3", "QB": "d3b"})
        inv_la = build_inverter(wn=20, wp=40, l=0.15, name="inv_la",
                                with_tests=False, tech=tech)
        mod.add_module(inv_la, "inv_soutb", nets={"VDD": "VDD", "VSS": "VSS",
                        "A": "sout", "Y": "soutb"})       # look-ahead complement b[n+1]b
        # Tap strengths use parallel transistor slices. Each tap receives a
        # bit and its complement: main=d1, precursor=sout, postcursors=d2/d3.
        # Negative tap signs are implemented inside the driver.
        mod.add_module(build_cmos_ffe_driver(buffered=cmos_predriver, tech=tech, eq_strength=eq_strength), "driver", nets={
            "VDD": "VDD", "VSS": "VSS",
            "MAINP": "d1", "MAINN": "d1b", "PREP": "sout", "PREN": "soutb",
            "POST1P": "d2", "POST1N": "d2b", "POST2P": "d3", "POST2N": "d3b",
            "OUTP": "PADP", "OUTN": "PADN"})
        with mod:
            # Silk API: add the explicit CMOS channel and receiver termination.
            # Each leg has 50 ohms and 2 pF; the receiver has 100 ohms differential.
            elements.resistor("R_chp", p="PADP", n="RXP", value=50.0)
            elements.resistor("R_chn", p="PADN", n="RXN", value=50.0)
            elements.capacitor("C_chp", p="RXP", n="VSS", value=2e-12)
            elements.capacitor("C_chn", p="RXN", n="VSS", value=2e-12)
            elements.resistor("R_term", p="RXP", n="RXN", value=_R_TERM)
    else:
        raise ValueError(f"unknown serdes_tx variant {variant!r}")
    return mod
