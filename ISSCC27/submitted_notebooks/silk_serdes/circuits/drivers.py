"""Local circuit code adapted from silk/examples/serdes_tx_example.py.

Source revision: 3252db2f37f71c0b3f8c19174f57f206e4fa1cc7
Copyright (c) 2026 Levant Labs. MIT license; see LICENSE.
The unbuffered configuration preserves the original extraction.
The demo adds optional input predrivers to isolate storage-node loading.
"""

from circuits.cml_cells import build_cml_ffe_driver

from silk import Module, Port


from circuits.process import SKY130


_FFE_TAPS_NOM = (-0.385, 1.0, -0.610, 0.106)   # Starting coefficients; optimize them for the chosen channel.


_FFE_MAIN_UNITS = 10             # main-tap unit-slice count (FFE weight resolution)


_R_U1 = 1000.0                   # Unit-slice resistance (ohm); each tap uses R / slice count.


_INV_WN_U, _INV_WP_U = 20.0, 40.0   # unit inverter (small W -> in model bin; m scales it)


def _ffe_unit_counts(taps=_FFE_TAPS_NOM, main_units=_FFE_MAIN_UNITS):
    """Quantize |taps| to integer unit-slice counts (main tap = ``main_units``)."""
    cmain = abs(taps[1])
    return [max(1, int(round(abs(c) / cmain * main_units))) for c in taps]


def build_cmos_predriver(*, tech=SKY130, wn=1.0, wp=2.0, l=.15,
                         with_tests=False, output_dir=None, bit_rate_hz=600e6,
                         load_f=200e-15, stress_supply_v=1.8) -> Module:
    """Non-inverting four-stage taper: unit inverter multipliers 1, 4, 16, 64.

    A 1/2 um input pair isolates the DFF storage nodes from the segmented
    output gates. All tap legs get the same stages and nominal delay.

    With ``with_tests=True``, register sky130 ``timing`` and ``supply_stress``
    testbenches. Access them with ``get_test``; construction does not simulate.
    Timing uses 1.8 V, 50 ps input edges and ``load_f`` at 27 C. Its second
    pulse (6–10 UI) has illustrative half-UI delay and quarter-UI edge budgets.
    Stress independently uses ``stress_supply_v``, slow 2 ns edges and 200 fF.
    Leave tests disabled when placing this block in the transmitter hierarchy.
    """
    from pathlib import Path
    from math import isfinite
    if with_tests:
        from silk.exceptions import NotSupportedError
        if tech.name != 'sky130':
            raise NotSupportedError('Predriver test recipes are validated for sky130 only')
        if any(not isfinite(x) or x <= 0 for x in (bit_rate_hz, load_f, stress_supply_v)):
            raise ValueError('bit_rate_hz, load_f and stress_supply_v must be finite and positive')
    pdk = tech.load()
    from circuits.stdcells import build_inverter
    mod = Module(tech.label, str(Path(output_dir).resolve()) if output_dir is not None else "/tmp",
                 "cmos_predriver.cir", pdk_details=pdk,
                 module_name="cmos_predriver")
    mod.define_module_ports({"VDD": Port.supply(), "VSS": Port.ground(),
                             "A": Port.analog_input(), "Y": Port.analog_output()})
    # Silk API: add four locally defined inverter stages with increasing drive.
    for i, mult in enumerate((1, 4, 16, 64)):
        inv = build_inverter(wn=wn, wp=wp, l=l, m=mult,
                             name=f"predriver_inv_{mult}", with_tests=False, tech=tech)
        mod.add_module(inv, f"stage{i}", nets={"VDD":"VDD", "VSS":"VSS",
                       "A":"A" if i == 0 else f"n{i}",
                       "Y":"Y" if i == 3 else f"n{i+1}"})
    if with_tests:
        from silk import sources
        from silk.elements import elements
        from silk.metrics import propagation_delay, rise_time, fall_time
        from silk.simulation import Transient
        mod.set_output_options(mode='new')
        ui = 1 / bit_rate_hz
        # Silk API: register the timing bench on the predriver itself.
        tb = mod.create_test('timing', parameters=dict(
            bit_rate_hz=bit_rate_hz, load_f=load_f, edge_s=50e-12,
            measurement_start_s=6*ui, measurement_stop_s=10*ui))
        tb.add_module_under_test({'VDD':'vdd', 'VSS':'0', 'A':'din', 'Y':'dout'})
        tb.add_source(sources.VoltageSource('vdd', positive='vdd', negative='0', dc=1.8))
        tb.add_source(sources.VoltageSource('din', positive='din', negative='0',
            pulse=sources.Pulse(v1=0, v2=1.8, td=2*ui, tr=50e-12, tf=50e-12,
                                pw=2*ui, per=4*ui)))
        tb.add(elements.capacitor('load', p='dout', n='0', value=load_f))
        tb.set_supply_voltage(1.8, source='vdd')
        tb.set_temperature(27)
        tb.add_sim_type(Transient(step=5e-12, stop=16*ui, maxstep=5e-12))
        # Silk API: bind waveform probes to timing metrics and specifications.
        vin, vout = tb.probe('din'), tb.probe('dout')
        for edge in ('rising', 'falling'):
            name = f'{edge}_delay_s'
            tb.add_metric(name, propagation_delay, sig_in=vin, sig_out=vout,
                          in_threshold=.9, out_threshold=.9, in_edge=edge,
                          start=6*ui, end=10*ui)
            tb.add_spec(f'{edge} delay <= 0.5 UI', name, '<=', .5*ui)
        for name, metric in (('rise_s', rise_time), ('fall_s', fall_time)):
            tb.add_metric(name, metric, sig=vout, initial=0 if name=='rise_s' else 1.8,
                          final=1.8 if name=='rise_s' else 0, start=6*ui, end=10*ui)
            tb.add_spec(f'{name} <= 0.25 UI', name, '<=', .25*ui)

        # Silk API: register a separate bench for supply-induced device stress.
        tb=mod.create_test('supply_stress')
        tb.add_module_under_test({'VDD':'vdd','VSS':'0','A':'din','Y':'dout'})
        tb.add_source(sources.VoltageSource('vdd',positive='vdd',negative='0',dc=stress_supply_v))
        tb.add_source(sources.VoltageSource('din',positive='din',negative='0',
            pulse=sources.Pulse(v1=0,v2=stress_supply_v,td=5e-9,tr=2e-9,tf=2e-9,pw=10e-9,per=25e-9)))
        with tb.netlist:
            elements.capacitor('load',p='dout',n='0',value=200e-15)
        tb.set_temperature(27)
        tb.set_supply_voltage(stress_supply_v,source='vdd')
        tb.add_sim_type(Transient(step=20e-12,stop=80e-9,maxstep=20e-12))
    return mod


def build_cmos_ffe_driver(*, tech=SKY130, taps=_FFE_TAPS_NOM, main_units=_FFE_MAIN_UNITS,
                          r_u1=_R_U1, wn=_INV_WN_U, wp=_INV_WP_U, l=0.15,
                          buffered=True, eq_strength=1.0) -> Module:
    """Four-tap segmented CMOS driver with selectable input predrivers.

    Quantized tap magnitudes set inverter multipliers and inverse series
    resistances. A negative tap swaps output legs. Each tap accepts a true
    bit on P and its complement on N; OUTP/OUTN are the summed outputs.

    ``buffered=True`` isolates storage nodes with an equal four-stage taper
    on every input. False reproduces the original direct gate loading.
    The inherited weights target a different channel and are not optimized
    for this demo's RC link.
    """
    pdk = tech.load()
    from circuits.stdcells import build_inverter
    from silk.elements import elements
    names = ("pre", "main", "post1", "post2")
    N = _ffe_unit_counts(taps, main_units)
    mod = Module(tech.label, "/tmp", "cmos_ffe.cir", pdk_details=pdk,
                 module_name="cmos_ffe_driver_buffered" if buffered else "cmos_ffe_driver")
    ports = {"VDD": Port.supply(), "VSS": Port.ground(),
             "OUTP": Port.analog_output(), "OUTN": Port.analog_output()}
    for nm in names:
        ports[f"{nm.upper()}P"] = Port.analog_input()
        ports[f"{nm.upper()}N"] = Port.analog_input()
    mod.define_module_ports(ports)
    if buffered:
        predriver = build_cmos_predriver(tech=tech, with_tests=False)
        for nm in names:
            for leg in ("P", "N"):
                port = f"{nm.upper()}{leg}"
                mod.add_module(predriver, f"pre_{nm}_{leg.lower()}", nets={
                    "VDD":"VDD", "VSS":"VSS", "A":port, "Y":f"buf_{port}"})
    for nm, c, ni in zip(names, taps, N):
        # Each tap has its own inverter definition and multiplier. Distinct
        # module names identify these different circuits in the hierarchy.
        seg = build_inverter(wn=wn, wp=wp, l=l, m=ni, name=f"cmos_seg_{nm}",
                             with_tests=False, tech=tech)
        mod.add_module(seg, f"seg_{nm}_p", nets={"VDD": "VDD", "VSS": "VSS",
                        "A": f"buf_{nm.upper()}P" if buffered else f"{nm.upper()}P", "Y": f"d{nm}p"})
        mod.add_module(seg, f"seg_{nm}_n", nets={"VDD": "VDD", "VSS": "VSS",
                        "A": f"buf_{nm.upper()}N" if buffered else f"{nm.upper()}N", "Y": f"d{nm}n"})
    with mod:
        for nm, c, ni in zip(names, taps, N):
            r = r_u1 / ni
            if nm != "main":
                r = r / eq_strength
            # invP out = NOT({nm}P)=NOT bit; invN out = bit. Positive tap -> bit leg
            # (dN) to OUTP; negative tap -> swap legs (that IS the minus sign).
            hi_leg, lo_leg = ((f"d{nm}n", f"d{nm}p") if c >= 0
                              else (f"d{nm}p", f"d{nm}n"))
            elements.resistor(f"R_{nm}_p", p=hi_leg, n="OUTP", value=r)
            elements.resistor(f"R_{nm}_n", p=lo_leg, n="OUTN", value=r)
        elements.capacitor("C_padp", p="OUTP", n="VSS", value=50e-15)
        elements.capacitor("C_padn", p="OUTN", n="VSS", value=50e-15)
    return mod
