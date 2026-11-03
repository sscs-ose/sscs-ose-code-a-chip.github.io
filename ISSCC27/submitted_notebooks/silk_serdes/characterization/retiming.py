"""Isolate a retiming DFF from the serializer, retaining its transistor load.

Local testbench construction; execution and reporting use silk's native APIs.
The ideal PRBS source makes setup time independent of serializer propagation.
"""
from pathlib import Path
import numpy as np
from silk import sources
from silk.elements import elements
from silk.simulation import Transient
from silk.metrics import sample
from circuits.stdcells import build_dff
from circuits.drivers import build_cmos_ffe_driver


def build_retiming_test(output_dir, *, loaded=True, setup_ui=.5,
                        buffered=False, bit_rate_hz=600e6):
    """Return a DFF and registered capture test at sky130 tt, 1.8 V, 27 C.

    Check Q and QB at 0.8 UI after each nominal clock edge, discarding the
    first 16 of 80 PRBS9 bits. ``setup_ui`` places the start of the 20 ps data
    transition before the nominal edge; the clock takes 50 ps to rise.
    The loaded case includes the actual main-tap gates and next DFF input.
    Other FFE inputs are driven independently to remove serializer timing.
    """
    if not 0 < setup_ui < 1 or not np.isfinite(bit_rate_hz) or bit_rate_hz <= 0:
        raise ValueError('Require 0 < setup_ui < 1 and a finite positive bit rate')
    dut = build_dff(with_tests=False)
    dut.dir_folder = str(Path(output_dir).resolve())
    dut.set_output_options(mode='new')
    ui, vdd = 1/bit_rate_hz, 1.8
    t0 = 2*ui
    # Silk API: drive an isolated flip-flop with a finite PRBS9 waveform.
    data = sources.PRBS(order=9, length=80, v1=0, v2=vdd,
                        ui=ui, td=t0-setup_ui*ui, tr=20e-12, tf=20e-12)
    bits = data.stream
    # Silk API: register stimulus settings and the capture checks on the DFF.
    tb = dut.create_test('capture', parameters=dict(loaded=loaded, setup_ui=setup_ui,
                         buffered=buffered, bit_rate_hz=bit_rate_hz,
                         stimulus=data.as_parameters()))
    tb.add_module_under_test({'VDD':'vdd','VSS':'0','CLK':'clk','CLRB':'vdd',
                             'D':'d','Q':'q','QB':'qb'})
    tb.add_source(sources.VoltageSource('vdd', positive='vdd', negative='0', dc=vdd))
    tb.add_source(sources.VoltageSource('clk', positive='clk', negative='0',
        pulse=sources.Pulse(v1=0,v2=vdd,td=t0,tr=50e-12,tf=50e-12,pw=ui/2,per=ui)))
    tb.add_source(sources.VoltageSource('d',positive='d',negative='0',waveform=data))
    if loaded:
        driver = build_cmos_ffe_driver(buffered=buffered)
        tb.add_module(driver, 'driver', nets={
            'VDD':'vdd','VSS':'0','MAINP':'q','MAINN':'qb',
            'PREP':'d','PREN':'0','POST1P':'d','POST1N':'0',
            'POST2P':'d','POST2N':'0','OUTP':'padp','OUTN':'padn'})
        tb.add_module(build_dff(with_tests=False), 'next', nets={
            'VDD':'vdd','VSS':'0','CLK':'clk','CLRB':'vdd','D':'q',
            'Q':'nextq','QB':'nextqb'})
        with tb.netlist:
            elements.resistor('term',p='padp',n='padn',value=200)
            elements.capacitor('cp',p='padp',n='0',value=2e-12)
            elements.capacitor('cn',p='padn',n='0',value=2e-12)
    tb.set_temperature(27)
    tb.set_supply_voltage(vdd, source='vdd')
    tb.add_sim_type(Transient(step=10e-12,stop=t0+81*ui,maxstep=10e-12))
    times = t0+(np.arange(16,80)+.8)*ui
    expected = np.asarray(bits[16:], dtype=bool)
    def errors(sig, complement):
        # Silk API: sample Q/QB; compare with the known bits using VDD/2.
        sampled = sample(sig, x_new=times).y > vdd/2
        return int(np.count_nonzero(sampled != (expected ^ complement)))
    for node, complement in [('q', False), ('qb', True)]:
        name = f'{node}_bit_errors'
        tb.add_metric(name, errors, sig=tb.probe(node), complement=complement)
        tb.add_spec(name, name, '==', 0)
    return dut, tb
