"""Coupled microrobot circuit bench with explicit digital/electrical abstraction.

PDK transistors: clock, first resettable DFF, reset level conversion, candidate
brownout and two drivers. XSPICE models implement the remaining binary counter;
its functional phases follow the RTL. A switched PDK-capacitor load proxies the
remaining digital power. It is not a transistor netlist or power signoff of RTL.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

from opentcad.device.compact import SingleDiodePV
from .electrical import header, run_deck

HERE = Path(__file__).resolve().parent


def phase_netlist(bits=12):
    """Binary ripple counter with reset and quarter-cycle phases, normalized I/O.

    In the coupled bench, its input is the inverted Q of the physical first DFF.
    Thus 12 modeled bits plus one transistor DFF give the RTL's 13-bit /8192.
    Digital delays are chosen functional-model values, not characterized timing.
    """
    if not 2 <= bits <= 16:
        raise ValueError("Two to sixteen modeled bits are supported")
    lines = [".subckt microrobot_event_phases clock_n reset_ok_n phase_a_n phase_b_n",
             "Ainput [clock_n reset_ok_n] [clock reset_ok] event_adc",
             "Arst reset_ok reset event_inv",
             ".model event_adc adc_bridge(in_low=0.5 in_high=0.5)",
             ".model event_inv d_inverter(rise_delay=1n fall_delay=1n)",
             ".model event_ff d_dff(ic=0 clk_delay=1n reset_delay=1n rise_delay=1n fall_delay=1n)",
             ".model event_xor d_xor(rise_delay=1n fall_delay=1n)",
             ".model event_and d_and(rise_delay=1n fall_delay=1n)",
             ".model event_dac dac_bridge(out_low=0 out_high=1 t_rise=1u t_fall=1u)"]
    for bit in range(bits):
        clock = 'clock' if bit == 0 else f'n{bit-1}'
        lines.append(f'Aff{bit} n{bit} {clock} NULL reset q{bit} n{bit} event_ff')
    lines += [f'Axor [q{bits-1} q{bits-2}] phase_b event_xor',
              f'Apa [n{bits-1} reset_ok] phase_a_valid event_and',
              'Apb [phase_b reset_ok] phase_b_valid event_and',
              'Aout [phase_a_valid phase_b_valid] [phase_a_n phase_b_n] event_dac',
              '.ends microrobot_event_phases']
    return '\n'.join(lines)+'\n'


def standard_cells(pdk):
    source = (pdk / 'libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice').read_text()
    selected = []
    for name in ['sky130_fd_sc_hd__dfrtp_1', 'sky130_fd_sc_hd__inv_1']:
        match = re.search(r'(?ms)^\.subckt '+name+r'\b.*?^\.ends[^\n]*', source)
        if match is None:
            raise ValueError(f'Missing PDK cell {name}')
        selected.append(match.group())
    first_cell = re.search(r'(?m)^\.subckt\b', source)
    preamble = source[:first_cell.start()]
    return preamble+'\n'.join(selected)+'\n'


def illumination_pwl(illumination_history=None, *, dark_interval=True):
    """SPICE PWL in seconds/W per m²; custom history replaces built-in timing."""
    if illumination_history is None:
        light = '0 0 100u 0 1m 1000'
        if dark_interval:
            light += ' 0.75 1000 0.751 0 0.85 0 0.851 1000'
        return light
    try:
        history = np.asarray(illumination_history, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError('Illumination history must contain numeric time/power pairs') from exc
    if history.ndim != 2 or history.shape[1] != 2 or len(history) < 2:
        raise ValueError('Illumination history needs at least two time/power pairs')
    if not np.isfinite(history).all():
        raise ValueError('Illumination history must be finite')
    if history[0, 0] != 0 or np.any(history[:, 0] < 0):
        raise ValueError('Illumination times must start at zero and be nonnegative')
    if np.any(np.diff(history[:, 0]) <= 0):
        raise ValueError('Illumination times must strictly increase')
    if np.any(history[:, 1] < 0):
        raise ValueError('Illumination power must be nonnegative')
    return ' '.join(format(float(value), '.17g') for value in history.flat)


def _configuration(options):
    result = dict(options)
    if result.get('illumination_history') is not None:
        result['illumination_history'] = np.asarray(result['illumination_history'], dtype=float).tolist()
    return result


def controller_deck(*, corner='tt', temperature_C=26.85, stop_s=1.5,
                    max_step_s=100e-9, output_step_s=20e-6, dark_interval=True,
                    adaptive_diagnostics=False, brownout_circuit="brownout_v2.spice",
                    ready_circuit="ready_levelshift.spice", illumination_history=None):
    """Build a finite-PV bench; diagnostics save native nodes without interpolation."""
    for candidate in [brownout_circuit, ready_circuit]:
        if Path(candidate).name != candidate:
            raise ValueError("Candidate circuits must name a file in circuits/")
    fit = json.loads((HERE / 'results/published/pv_fit.json').read_text())
    cell = replace(SingleDiodePV(**fit['fitted_terminal_model']), series_cells=1)
    logic = cell.scaled_current(150/540)
    pdk = Path(os.environ.get('PDK_ROOT','/usr/local/share/pdk'))/'sky130A'
    circuits = '\n'.join((HERE/'circuits'/n).read_text() for n in [
        'starved_clock.spice','actuator_driver.spice','electrochemical.spice',
        brownout_circuit,ready_circuit])
    light = illumination_pwl(illumination_history, dark_interval=dark_interval)
    deck = header(corner, temperature_C)+circuits+'\n'+standard_cells(pdk)+phase_netlist()
    deck += f'''
* PV temperature fixed to fit; no optical/PV temperature calibration.
.model pv D(IS={cell.saturation_A:.12g} N={cell.ideality:.12g} TNOM=26.85 EG=0 XTI=0)
.model pvlogic D(IS={logic.saturation_A:.12g} N={logic.ideality:.12g} TNOM=26.85 EG=0 XTI=0)
Vlight light 0 PWL({light})
Bph1 0 lp1 I={{{logic.photocurrent_A:.12g}*v(light)/1000}}
Bph2 lp1 lp2 I={{{logic.photocurrent_A:.12g}*v(light)/1000}}
Bph3 lp2 logic_raw I={{{logic.photocurrent_A:.12g}*v(light)/1000}}
Dlp1 lp1 0 pvlogic TEMP=26.85
Dlp2 lp2 lp1 pvlogic TEMP=26.85
Dlp3 logic_raw lp2 pvlogic TEMP=26.85
Clogic logic_raw 0 2p
Bphlo 0 celllo I={{{cell.photocurrent_A:.12g}*v(light)/1000}}
Dlo celllo 0 pv TEMP=26.85
Vpvlo celllo mid 0
Bphhi mid cellhi I={{{cell.photocurrent_A:.12g}*v(light)/1000}}
Dhi cellhi mid pv TEMP=26.85
Vpvhi cellhi act_raw 0
Cstorelo mid 0 1p
Cstorehi act_raw mid 1p
Vlogic logic_raw logic 0
Vact act_raw act 0
Vclock logic clock_supply 0
Xclock clk clock_supply 0 bn bp microrobot_clock
Vdigital logic digital_supply 0
Xff clk feedback reset_n 0 0 digital_supply digital_supply q0 sky130_fd_sc_hd__dfrtp_1
Xfeedback q0 0 0 digital_supply digital_supply feedback sky130_fd_sc_hd__inv_1
Vresetlogic logic reset_supply 0
Xready ready reset_n act reset_supply 0 microrobot_ready_levelshift
* Separate switched-capacitance proxy for remaining digital energy.
* Two PDK 2x2 um MIMs (~19 fF total); no claim of RTL power extraction.
Vproxy logic proxy_supply 0
Xproxy clk flop_load proxy_supply 0 micro_inv
Xcproxy1 flop_load 0 sky130_fd_pr__cap_mim_m3_1 w=2 l=2
Xcproxy2 flop_load 0 sky130_fd_pr__cap_mim_m3_1 w=2 l=2
Vmonitor act monitor_supply 0
Xmonitor bn ready monitor_supply 0 microrobot_brownout
Bclock_norm clock_n 0 V={{1-v(q0)/max(v(logic),0.1)}}
Breset_norm reset_ok_n 0 V={{v(reset_n)/max(v(logic),0.1)}}
Xphases clock_n reset_ok_n pan pbn microrobot_event_phases
Bpa pa_source 0 V={{v(pan)*v(logic)}}
Bpb pb_source 0 V={{v(pbn)*v(logic)}}
Vpa pa_source pa_buffer 0
Vpb pb_source pb_buffer 0
Rpa pa_buffer pa 10k
Rpb pb_buffer pb 10k
Xda pa ready ea logic act mid 0 microrobot_driver
Xdb pb ready eb logic act mid 0 microrobot_driver
Xea ea sa ta micro_electrode
Xeb eb sb tb micro_electrode
Xreturn mid sr tr micro_electrode cdl=400p qmax=2600p rf=1g
Rsa sa bulk 10meg
Rsb sb bulk 10meg
Rsr sr bulk 1meg
* Numerical power integrators: 1 V encodes 1 nJ, not physical capacitors.
'''
    powers = {'logic':'v(logic)*i(Vlogic)', 'actuator':'v(mid)*i(Vpvlo)+(v(act_raw)-v(mid))*i(Vpvhi)',
              'clock':'v(logic)*i(Vclock)', 'firstff':'v(logic)*i(Vdigital)',
              'proxy':'v(logic)*i(Vproxy)', 'resetlogic':'v(logic)*i(Vresetlogic)',
              'monitor':'v(act)*i(Vmonitor)', 'phase':'v(pa_source)*i(Vpa)+v(pb_source)*i(Vpb)'}
    for name,expr in powers.items():
        deck += (f'Benergy_{name} 0 en_{name} I={{{expr}}}\n'
                 f'Cenergy_{name} en_{name} 0 1n\nRenergy_{name} en_{name} 0 1e15\n')
    vectors = ['v(light)','v(logic)','v(act)','v(mid)','v(ready)','v(reset_n)',
               'v(pa)','v(pb)','v(ea)','v(eb)','v(sa)','v(sb)','v(ta)','v(tb)']
    vectors += [f'v(en_{k})' for k in powers]
    if adaptive_diagnostics:
        vectors += ['v(clk)', 'v(q0)', 'v(bn)']
    interpolation = '' if adaptive_diagnostics else ' interp'
    # INTERP only reduces saved data; internal integration is still adaptive.
    # Power states retain integrated energy from internal steps, avoiding aliasing
    # of sub-nanosecond current spikes in the coarse waveform output.
    deck += f'''.options method=gear maxord=2 reltol=1e-6 abstol=1e-15{interpolation}
.control
set wr_vecnames
set wr_singlescale
save {' '.join(vectors)}
tran {output_step_s} {stop_s} 0 {max_step_s}
wrdata controller.dat {' '.join(vectors)}
quit
.endc
.end
'''
    return deck, list(powers)


def validate_transient(data, expected_columns, stop_s):
    """Reject malformed, nonfinite or incomplete simulator output before reporting."""
    if (data.ndim != 2 or len(data) < 2 or data.shape[1] != expected_columns
            or not np.isfinite(data).all()):
        raise RuntimeError('Transient data have invalid shape or nonfinite values')
    if data[0, 0] < 0 or np.any(np.diff(data[:, 0]) < 0):
        raise RuntimeError('Transient time must not decrease from a nonnegative origin')
    if data[-1, 0] < stop_s * .999:
        raise RuntimeError('Transient did not reach its requested stop time')


def run(destination, **kwargs):
    deck, powers = controller_deck(**kwargs)
    dest = run_deck(destination, deck, timeout=3600)
    data = np.loadtxt(dest/'controller.dat',skiprows=1)
    columns = ['time_s','light_W_m2','logic_V','actuator_V','midpoint_V','ready_V','reset_n_V',
               'phase_A_V','phase_B_V','electrode_A_V','electrode_B_V','solution_A_V','solution_B_V',
               'theta_A','theta_B']+[k+'_energy_nJ' for k in powers]
    if kwargs.get('adaptive_diagnostics', False):
        columns += ['clock_V', 'first_DFF_Q_V', 'bias_n_V']
    validate_transient(data, len(columns), kwargs.get('stop_s', 1.5))
    np.savetxt(dest/'waveform.csv.gz',data,delimiter=',',header=','.join(columns),comments='')
    result={'scope':__doc__, 'netlist_sha256':hashlib.sha256(deck.encode()).hexdigest(),
            'configuration':_configuration(kwargs),'output_columns':columns,'simulation_executed':True,
            'actual_stop_s':float(data[-1, 0]), 'saved_rows':len(data),
            'status':'Exploratory integration; inspect electrical acceptance before promotion'}
    (dest/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    return result,data

def diagnostic_deck(*, ready_circuit='ready_levelshift_current_limited.spice',
                    ready_bias_p=True, driver_ready='independent', **kwargs):
    """Build the short adaptive diagnostic without auxiliary energy states.

    Defaults: 2 ms, 50 ns maximum step, no darkness interval. The current-limited
    candidate's sixth port explicitly uses native clock bp. Original ready still
    controls driver clamps by default (logic-only reference). qualified-lvt adds
    the measured AND receiver with real gate loading; neither is PVT signoff.
    """
    if driver_ready not in {'independent', 'qualified-lvt'}:
        raise ValueError('Unknown driver-ready diagnostic policy')
    options = dict(stop_s=.002, max_step_s=50e-9, output_step_s=1e-6,
                   dark_interval=False)
    options.update(kwargs)
    options['adaptive_diagnostics'] = True
    deck, _ = controller_deck(ready_circuit=ready_circuit, **options)
    original = 'Xready ready reset_n act reset_supply 0 microrobot_ready_levelshift'
    bias_port = ' bp' if ready_bias_p else ''
    replacement = ('Vresetact act reset_act_supply 0\n'
                   'Xready ready reset_n reset_act_supply reset_supply 0'
                   + bias_port + ' microrobot_ready_levelshift')
    deck = deck.replace(original, replacement)
    deck = re.sub(r'^(?:Benergy_|Cenergy_|Renergy_).*\n', '', deck, flags=re.M)
    deck = re.sub(r'v\(en_[^)]+\) ?', '', deck)
    deck = deck.replace('* Numerical power integrators: 1 V encodes 1 nJ, not physical capacitors.',
                        '* Signed source energy is integrated offline from adaptive currents.')
    extra = ('i(Vpvlo) i(Vpvhi) i(Vclock) i(Vproxy) i(Vmonitor) i(Vpa) i(Vpb) '
             'v(pa_source) v(pb_source) i(Vresetlogic) i(Vresetact) i(Vdigital) '
             'i(Vlogic) v(bp) v(xready.input_b)')
    deck = deck.replace('save ', f'save {extra} ', 1)
    deck = deck.replace('wrdata controller.dat ', f'wrdata controller.dat {extra} ', 1)
    if driver_ready == 'qualified-lvt':
        circuit = (HERE/'circuits/ready_driver_qualified_lvt.spice').read_text()
        deck = deck.replace('Xda pa ready ea', 'Xda pa driver_ready ea')
        deck = deck.replace('Xdb pb ready eb', 'Xdb pb driver_ready eb')
        branch = (circuit+'\nVdriverbuffer act driverbuffer_supply 0\n'
                  'Xdriverbuffer reset_n ready driver_ready driverbuffer_supply 0 '
                  'microrobot_ready_driver_qualified_lvt\n')
        deck = deck.replace('.options method=gear', branch+'.options method=gear', 1)
        extra = ('i(Vdriverbuffer) v(driver_ready) v(xdriverbuffer.nand_b) '
                 'v(xdriverbuffer.series) '
                 '@m.xdriverbuffer.xon.msky130_fd_pr__nfet_01v8_lvt[id]')
        deck = deck.replace('save ', f'save {extra} ', 1)
        deck = deck.replace('wrdata controller.dat ', f'wrdata controller.dat {extra} ', 1)
    return deck


def offline_source_energies(data, columns):
    """Signed nJ from adaptive source-port power; raw SPICE column names required.

    Phase power uses the ideal source terminals, including the series-resistor
    drop. These deliveries are not dissipated heat; ports may return charge.
    Fast-edge and small cancellation residuals need a timestep comparison.
    """
    validate_transient(data, len(columns), 0.)
    if len(set(columns)) != len(columns):
        raise ValueError('Diagnostic columns must be unique')
    values = dict(zip(columns, data.T))
    required = {'time', 'v(logic)', 'v(act)', 'v(mid)', 'v(pa_source)', 'v(pb_source)'}
    required.update('i('+n+')' for n in ['Vlogic', 'Vpvlo', 'Vpvhi', 'Vclock',
                    'Vdigital', 'Vproxy', 'Vresetlogic', 'Vmonitor', 'Vpa', 'Vpb',
                    'Vresetact'])
    missing = required - values.keys()
    if missing:
        raise ValueError('Missing diagnostic source columns: '+', '.join(sorted(missing)))
    v = values
    logic, act, mid = v['v(logic)'], v['v(act)'], v['v(mid)']
    powers = {
        'logic': logic*v['i(Vlogic)'],
        'actuator': mid*v['i(Vpvlo)']+(act-mid)*v['i(Vpvhi)'],
        'clock': logic*v['i(Vclock)'],
        'firstff': logic*v['i(Vdigital)'],
        'proxy': logic*v['i(Vproxy)'],
        'resetlogic': logic*v['i(Vresetlogic)'],
        'monitor': act*v['i(Vmonitor)'],
        'phase': v['v(pa_source)']*v['i(Vpa)']+v['v(pb_source)']*v['i(Vpb)'],
        'resetact': act*v['i(Vresetact)'],
    }
    if 'i(Vdriverbuffer)' in v:
        powers['driverbuffer'] = act*v['i(Vdriverbuffer)']
    return {name: float(np.trapezoid(power, v['time'])*1e9)
            for name, power in powers.items()}


def run_diagnostic(destination, *, ready_bias_p=True, **kwargs):
    """Run a fresh short circuit diagnostic with offline signed source energies.

    This explicit path omits numerical energy capacitors. Legacy run() retains
    its original exploratory integrators and default circuit. A successful
    transient is not a full-controller startup, clamp-policy or PVT acceptance.
    """
    dest = Path(destination).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError('Diagnostic destination must be fresh: '+str(dest))
    deck = diagnostic_deck(ready_bias_p=ready_bias_p, **kwargs)
    dest = run_deck(dest, deck, timeout=3600)
    with (dest/'controller.dat').open() as source:
        columns = source.readline().split()
    data = np.loadtxt(dest/'controller.dat', skiprows=1)
    validate_transient(data, len(columns), kwargs.get('stop_s', .002))
    energies = offline_source_energies(data, columns)
    np.savetxt(dest/'waveform.csv.gz', data, delimiter=',',
               header=','.join(columns), comments='')
    resolved = dict(stop_s=.002, max_step_s=50e-9, output_step_s=1e-6,
                    dark_interval=False, ready_circuit='ready_levelshift_current_limited.spice',
                    driver_ready='independent')
    resolved.update(kwargs)
    resolved.update(ready_bias_p=ready_bias_p, adaptive_diagnostics=True)
    result = {
        'scope': __doc__, 'energy_method': 'offline_adaptive_trapezoid',
        'netlist_sha256': hashlib.sha256(deck.encode()).hexdigest(),
        'configuration': _configuration(resolved),
        'actual_stop_s': float(data[-1, 0]), 'saved_rows': len(data),
        'output_columns': columns, 'source_energy_nJ': energies,
        'simulation_executed': True,
        'status': 'Exploratory nominal diagnostic; no autonomous-controller acceptance',
    }
    (dest/'metrics.json').write_text(json.dumps(result, indent=2)+'\n')
    return result, data


def main(argv=None):
    """CLI defaults to a short offline diagnostic; legacy integration is explicit."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        help='Fresh result directory (existing nonempty directories are rejected)')
    parser.add_argument('--stop', type=float, default=.002, help='Requested stop in seconds (default: .002)')
    parser.add_argument('--max-step', type=float, default=50e-9,
                        help='Maximum internal step in seconds (default: 50e-9)')
    parser.add_argument('--driver-ready', choices=['independent', 'qualified-lvt'],
                        default='independent', help='Diagnostic driver policy (default: independent, logic-only reference)')
    parser.add_argument('--legacy', action='store_true',
                        help='Explicitly use the legacy exploratory circuit and auxiliary energy states')
    args = parser.parse_args(argv)
    if args.legacy and args.driver_ready != 'independent':
        parser.error('--driver-ready applies only to the diagnostic path')
    if args.stop <= 0 or args.max_step <= 0:
        parser.error('--stop and --max-step must be positive')
    if args.output is None:
        args.output = HERE/'local_runs'/('controller_legacy' if args.legacy else 'controller_diagnostic')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output directory must be fresh: '+str(args.output))
    runner = run if args.legacy else run_diagnostic
    options = dict(stop_s=args.stop, max_step_s=args.max_step)
    if not args.legacy:
        options['driver_ready'] = args.driver_ready
    result, _ = runner(args.output, **options)
    print(f"Completed {result['actual_stop_s']:g} s; results: {args.output}")
    return result


if __name__ == '__main__':
    main()
