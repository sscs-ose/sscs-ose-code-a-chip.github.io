"""Embedded CMOS/CML transmitter characterization using the local circuit hierarchy.

Stimulus scheduling adapted from silk/examples/serializer_example.py and
serdes_tx_example.py (MIT; see source_provenance.json). Original examples stay
unchanged. CMOS and CML use the same metrics, reference bits, and specifications.
"""
from math import isfinite
from numbers import Real
from pathlib import Path
from silk import Variable, sources
from silk.simulation import Transient
from circuits.transmitter import build_serdes_tx
from circuits.process import TECHNOLOGIES
from circuits.cml_cells import build_cml_bias
from characterization.stimulus import SERIALIZER_RATIO, prbs_stimulus
from characterization.link_metrics import (measure_link, measure_reference, supply_power,
                                           serdes_link_measurements)


DEFAULT_SETTINGS = {'variant': 'cmos',
 'cmos_predriver': True,
 'process': 'sky130',
 'eq_strength': 1.0,
 'prbs_offset': 0,
 'supply_v': 1.8,
 'temperature_c': 27,
 'bit_rate_hz': 600000000.0,
 'clock_edge_s': 5e-11,
 'run_length': 'quick',
 'min_eye_height_v': 0.1,
 'min_eye_width_ui': 0.4,
 'max_power_w': None}


def _validate_settings(settings):
    unknown = set(settings) - set(DEFAULT_SETTINGS)
    if unknown:
        raise ValueError(f"Unknown link settings: {sorted(unknown)}")
    if not isinstance(settings['cmos_predriver'], bool):
        raise ValueError('cmos_predriver must be a bool')
    if settings['variant'] not in ('cmos', 'cml'):
        raise ValueError('variant must be cmos or cml')
    if settings['process'] not in TECHNOLOGIES:
        raise ValueError('process must be sky130 or gf180mcu')
    if settings['variant'] == 'cml' and settings['process'] != 'sky130':
        raise ValueError('CML process port is not supported; use CMOS for gf180mcu')
    options = (1.7, 1.8, 1.9) if settings['process'] == 'sky130' else (3.0, 3.3, 3.6)
    if settings['supply_v'] not in options:
        raise ValueError(f'supply_v must be one of {options}')
    if isinstance(settings['eq_strength'], bool) or not isinstance(settings['eq_strength'], Real) or not .01 <= settings['eq_strength'] <= 1:
        raise ValueError('eq_strength must be between 0.01 and 1')
    if settings['temperature_c'] not in (-40, 27, 85):
        raise ValueError(f'temperature_c must be one of {(-40, 27, 85)}')
    if settings['run_length'] not in ('quick', 'full'):
        raise ValueError('run_length must be quick or full')
    for name in ('bit_rate_hz', 'clock_edge_s', 'min_eye_height_v', 'min_eye_width_ui', 'max_power_w'):
        value = settings[name]
        if name == 'max_power_w' and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be a finite positive number')
    if settings['min_eye_width_ui'] > 1:
        raise ValueError('min_eye_width_ui must be at most one UI')


def read_measurements(ckt, experiment):
    p, n = ckt.load_signal('rxp'), ckt.load_signal('rxn')
    differential = p - n.interpolate(p.x)
    result = measure_link(differential.x, differential.y, experiment, t0=2/experiment['bit_rate_hz'])
    result['average_power_w'] = supply_power(
        ckt.load_signal('vdd'), ckt.load_signal('vvdd', 'I'),
        result['measurement_start_s'], result['measurement_stop_s'])
    return result


def build_characterization(experiment, output_dir, *, eq_strength=None, dut=None, db_path=None,
                           supply_voltage=None, test_name="link"):
    """Build the transmitter and register its link verification recipe.

    Silk owns the sources, transient analysis, metrics, and specifications.
    Calling dut.run_test("link") executes that recipe; construction does not
    simulate. A supply Variable drives both the rail and stimulus levels.
    """
    if dut is not None and db_path is not None:
        raise ValueError("Pass db_path when constructing the supplied DUT, not alongside dut")
    experiment = DEFAULT_SETTINGS | experiment
    _validate_settings(experiment)
    bits = prbs_stimulus(experiment)["bits"]
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tech = TECHNOLOGIES[experiment['process']]
    dut = dut if dut is not None else build_serdes_tx(variant=experiment['variant'], cmos_predriver=experiment['cmos_predriver'],
                          tech=tech, eq_strength=experiment['eq_strength'] if eq_strength is None else eq_strength,
                          db_path=db_path)
    dut.dir_folder = str(out)
    dut.set_output_options(mode='new')
    parameters = {key: value for key, value in experiment.items()
                  if key not in ('temperature_c', 'supply_v')}
    if supply_voltage is not None and not isinstance(supply_voltage, Variable):
        raise TypeError("supply_voltage must be a silk Variable or None")
    ui = 1/experiment['bit_rate_hz']
    vdd = experiment['supply_v'] if supply_voltage is None else supply_voltage
    t0, edge = 2*ui, min(experiment['clock_edge_s'],ui/4)
    levels = {'': (0, vdd)} if experiment['variant'] == 'cmos' else {
        'p': (vdd-.4, vdd), 'n': (vdd, vdd-.4)}
    # Silk API: drive each parallel lane with a finite bit-pattern source.
    # Every tenth serial bit belongs to the same lane. CML also needs its inverse.
    data_sources = {
        f'p{lane}{leg}': sources.voltage.bitpattern(
            f'p{lane}{leg}', p=f'p{lane}{leg}', n='0',
            bits=bits[lane::SERIALIZER_RATIO], v1=lo, v2=hi,
            ui=SERIALIZER_RATIO*ui, td=t0-.4*ui, tr=.05*ui, tf=.05*ui)
        for leg, (lo, hi) in levels.items() for lane in range(SERIALIZER_RATIO)
    }
    parameters['data_sources'] = {name: src.waveform.as_parameters()
                                  for name, src in data_sources.items()}
    parameters['sequence'] = dict(kind='prbs', order=9, seed=0,
        convention='xnor-post-shift', length=len(bits)+experiment['prbs_offset'],
        offset=experiment['prbs_offset'])
    # Silk API: register stimulus metadata and the complete test on the circuit.
    tb = dut.create_test(test_name, parameters=parameters)
    ports = {'VDD':'vdd','VSS':'0','PADP':'padp','PADN':'padn','RXP':'rxp','RXN':'rxn'}
    tb.add_source(sources.VoltageSource('vdd',positive='vdd',negative='0',dc=vdd))
    if experiment['variant'] == 'cmos':
        ports.update(CLK='clk',LOAD='load')
        ports.update({f'P{i}':f'p{i}' for i in range(SERIALIZER_RATIO)})
        tb.add_module_under_test(ports)
        tb.add_source(sources.VoltageSource('clk',positive='clk',negative='0',dc=0,
            pulse=sources.Pulse(v1=0,v2=vdd,td=t0,tr=edge,tf=edge,pw=ui/2,per=ui)))
        tb.add_source(sources.VoltageSource('load',positive='load',negative='0',dc=0,
            pulse=sources.Pulse(v1=0,v2=vdd,td=t0-.3*ui,
                tr=.05*ui,tf=.05*ui,pw=.95*ui,per=SERIALIZER_RATIO*ui,
                np=len(bits)//SERIALIZER_RATIO)))

    else:
        ports.update(IBIAS='ibias',CLKP='clkp',CLKN='clkn',LOADP='loadp',LOADN='loadn')
        ports.update({f'P{i}{leg}':f'p{i}{leg.lower()}' for i in range(SERIALIZER_RATIO) for leg in ('P','N')})
        tb.add_module_under_test(ports)
        tb.add_module(build_cml_bias(imul=4,tech=tech),'bias',nets={'VSS':'0','IBIAS':'ibias'})
        tb.add_source(sources.CurrentSource('iref',positive='vdd',negative='ibias',dc=800e-6))
        for leg,invert in [('p',False),('n',True)]:
            lo,hi=(vdd-.4,vdd) if not invert else (vdd,vdd-.4)
            tb.add_source(sources.VoltageSource('clk'+leg,positive='clk'+leg,negative='0',
                pulse=sources.Pulse(v1=lo,v2=hi,td=t0,tr=edge,tf=edge,pw=ui/2,per=ui)))
            low,high=(vdd-1.2,vdd) if not invert else (vdd,vdd-1.2)
            tb.add_source(sources.VoltageSource('load'+leg,positive='load'+leg,negative='0',
                pulse=sources.Pulse(v1=low,v2=high,td=t0-.3*ui,
                    tr=.05*ui,tf=.05*ui,pw=.95*ui,per=SERIALIZER_RATIO*ui,
                    np=len(bits)//SERIALIZER_RATIO)))

    for source in data_sources.values():
        tb.add_source(source)
    tb.set_temperature(experiment['temperature_c'])
    # A shared Variable drives the rail AND all stimulus levels. A scalar
    # supply setter would override that binding during a native Variable sweep.
    if supply_voltage is None:
        tb.set_supply_voltage(vdd, source='vdd')
    step = min(ui/100, edge)
    # Silk API: specify the transient grid and maximum internal timestep.
    tb.add_sim_type(Transient(step=step, stop=t0+(len(bits)+8)*ui, maxstep=step))
    # Silk API: multi-output registration evaluates the link/eye once, then
    # exposes link.eye_height_v, link.eye_width_ui, etc. for independent specs.
    rx = tb.probe('rxp') - tb.probe('rxn')
    tb.add_metric('link', serdes_link_measurements, sig=rx,
                  bit_rate_hz=experiment['bit_rate_hz'], run_length=experiment['run_length'],
                  prbs_offset=experiment['prbs_offset'])
    def power_measurement(sig, voltage, current):
        # Independently derive the trained window; this does not compute an eye.
        window = measure_reference(sig.x, sig.y, experiment, t0=t0)
        return supply_power(voltage, current,
                            window['measurement_start_s'], window['measurement_stop_s'])
    power = tb.add_metric('average_power_w', power_measurement, sig=rx,
                          voltage=tb.probe('vdd'), current=tb.probe('i(vdd)'))
    tb.add_metric('energy_per_bit_j', power / experiment['bit_rate_hz'])
    # Silk API: use these same pass/fail targets for every circuit variant.
    tb.add_spec('bit_errors', 'link.bit_errors', '==', 0)
    tb.add_spec('eye_height_v', 'link.eye_height_v', '>=', experiment['min_eye_height_v'])
    tb.add_spec('eye_width_ui', 'link.eye_width_ui', '>=', experiment['min_eye_width_ui'])
    if experiment['max_power_w'] is not None:
        tb.add_spec('average_power_w', 'average_power_w', '<=', experiment['max_power_w'])
    return dut, tb


def save_figures(ckt, experiment, measurements, folder):
    """Save waveform and eye PNGs from the simulated link."""
    import matplotlib.pyplot as plt
    p,n=ckt.load_signal('rxp'),ckt.load_signal('rxn')
    rx = p - n.interpolate(p.x)
    ui=1/experiment['bit_rate_hz']
    start=measurements['measurement_start_s']
    fig,axes=plt.subplots(1,2,figsize=(11,3.4))
    from matplotlib.ticker import FuncFormatter
    ui_ticks = FuncFormatter(lambda seconds, _: f'{seconds/ui:g}')
    rx.window(start, start+12*ui).shift(start).plot(ax=axes[0])
    axes[0].xaxis.set_major_formatter(ui_ticks)
    axes[0].axhline(0,color='gray',lw=.6)
    axes[0].set(xlabel='Time from measurement start (UI)',ylabel='RXP − RXN (V)',title='Measured receiver waveform')
    from silk.metrics import eye_diagram
    rx = rx.window(start, measurements['measurement_stop_s'])
    # Silk API: calculate the eye; Matplotlib below only formats the picture.
    eye = eye_diagram(rx, period=ui, auto_center=True, threshold=0.0)
    for trace in eye.traces:
        trace.plot(ax=axes[1], color='#285f9e', alpha=.12, lw=.6)
    axes[1].xaxis.set_major_formatter(FuncFormatter(lambda seconds, _: f'{seconds/ui:g}'))
    axes[1].axvline(.5*ui, color='#b55c28', ls='--', lw=.8)
    axes[1].axhline(0, color='gray', lw=.6)
    axes[1].set(xlabel='Phase (UI); silk display center at 0.5',
                ylabel='Differential voltage (V)', xlim=(0, ui),
                title=f'silk auto-centered eye: {eye.height*1e3:.1f} mV, {eye.width/ui:.3f} UI')
    fig.tight_layout()
    fig.savefig(folder/'waveform_eye.png',dpi=150)
    plt.close(fig)
