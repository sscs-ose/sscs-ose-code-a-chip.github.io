"""Complete public SKY130 LDO experiments with saved native evidence replay.

The regulator has transistor amplifier, bias, gate driver and pass device circuits.
VIN, VAA and the common reference voltage are declared external sources.
Saved mode needs only NumPy, pandas and Matplotlib. Fresh mode launches ngspice.
Set SKY130_MODEL or PDK_ROOT and, if needed, NGSPICE before native regeneration.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/ldo'
DEFAULT_CASE = 'tied_load50mA_cout100pF'
PARAMETERS = ('id', 'gm', 'gds', 'gmbs', 'vgs', 'vds', 'vdsat', 'vth')


def manifest(data_dir=DATA):
    return json.loads((Path(data_dir) / 'manifest.json').read_text(encoding='utf-8'))


def _folder(case, data_dir=DATA):
    if case not in manifest(data_dir)['all_cases']:
        raise ValueError('Choose a case listed in the evidence manifest')
    return Path(data_dir) / 'cases' / case


def _table(folder, filename):
    path = Path(folder) / filename
    if path.is_file():
        return np.atleast_2d(np.loadtxt(path, skiprows=1))
    with gzip.open(str(path) + '.gz', 'rt', encoding='utf-8') as stream:
        return np.atleast_2d(np.loadtxt(stream, skiprows=1))


def load_circuit(case=DEFAULT_CASE, data_dir=DATA):
    return json.loads((_folder(case, data_dir) / 'circuit.json').read_text(encoding='utf-8'))


def load_op(case=DEFAULT_CASE, data_dir=DATA):
    """All transistor operating points with ro replacing the raw output slope."""
    rows = pd.read_csv(_folder(case, data_dir) / 'operating_point.csv')
    rows['ro_ohm'] = 1 / rows['gds']
    return rows.drop(columns='gds')


def load_ac(case=DEFAULT_CASE, source='power', node='vout', data_dir=DATA):
    """Complex native transfer, with output impedance expressed in ohms."""
    if source not in ('power', 'auxiliary', 'reference', 'impedance', 'loop'):
        raise ValueError('Unknown native excitation')
    circuit = load_circuit(case, data_dir)
    data = _table(_folder(case, data_dir), source + '.tsv')
    column = 1 + 2 * circuit.get('ac_nodes', circuit['nodes']).index(node)
    value = data[:, column] + 1j * data[:, column + 1]
    if source == 'impedance':
        value = -value
    return pd.DataFrame({'frequency_hz': data[:, 0], 'real': value.real,
                         'imag': value.imag, 'magnitude': abs(value),
                         'magnitude_db': 20 * np.log10(np.maximum(abs(value), 1e-30)),
                         'phase_deg': np.unwrap(np.angle(value)) * 180 / np.pi})


def psr(case=DEFAULT_CASE, data_dir=DATA):
    return load_ac(case, 'power', data_dir=data_dir)


def auxiliary(case=DEFAULT_CASE, data_dir=DATA):
    return load_ac(case, 'auxiliary', data_dir=data_dir)


def reference(case=DEFAULT_CASE, data_dir=DATA):
    return load_ac(case, 'reference', data_dir=data_dir)


def output_impedance(case=DEFAULT_CASE, data_dir=DATA):
    return load_ac(case, 'impedance', data_dir=data_dir)


def loop_response(case=DEFAULT_CASE, data_dir=DATA):
    """Voltage injection return ratio estimate, retaining the connected fixture."""
    circuit = load_circuit(case, data_dir)
    raw = _table(_folder(case, data_dir), 'loop.tsv')
    def value(node):
        column = 1 + 2 * circuit.get('ac_nodes', circuit['nodes']).index(node)
        return raw[:, column] + 1j * raw[:, column + 1]
    loop = -value('vout') / value('vfb')
    return pd.DataFrame({'frequency_hz': raw[:, 0], 'real': loop.real, 'imag': loop.imag,
                         'magnitude_db': 20 * np.log10(abs(loop)),
                         'phase_deg': np.unwrap(np.angle(loop)) * 180 / np.pi})


def _crossings(curve):
    f = curve.frequency_hz.to_numpy()
    db = curve.magnitude_db.to_numpy()
    phase = curve.phase_deg.to_numpy()
    result = []
    for i in np.flatnonzero((db[:-1] > 0) & (db[1:] <= 0)):
        crossing = 10 ** np.interp(0, [db[i+1], db[i]], np.log10([f[i+1], f[i]]))
        reserve = 180 + np.interp(np.log10(crossing), np.log10(f), phase)
        result.append({'frequency_hz': float(crossing), 'phase_reserve_estimate_deg': float(reserve)})
    return result


def closed_poles(case=DEFAULT_CASE, data_dir=DATA):
    """Poles of the connected linear model extracted from native terminal currents.

    This recomputation is a linear reconstruction, not a new circuit simulation.
    It keeps all 15 internal states and uses no fitted behavioral controller.
    """
    with np.load(_folder(case, data_dir) / 'terminal_model/nodal_matrices.npz') as data:
        known = int(data['known_count'])
        dynamic = data['C'][known:, known:]
        static = data['G'][known:, known:]
    values = np.linalg.eigvals(-np.linalg.solve(dynamic, static))
    return pd.DataFrame({'real_rad_s': values.real, 'imag_rad_s': values.imag,
                         'natural_frequency_hz': abs(values) / (2 * np.pi)}).sort_values('natural_frequency_hz')


def reconstructed_response(case=DEFAULT_CASE, source='power', data_dir=DATA):
    """Compare terminal current reconstruction with the native connected AC result."""
    ports_by_source = {'power': 'vin', 'auxiliary': 'vaa', 'reference': 'reference'}
    if source not in ports_by_source:
        raise ValueError('Use power, auxiliary or reference')
    measured = load_ac(case, source, data_dir=data_dir)
    with np.load(_folder(case, data_dir) / 'terminal_model/nodal_matrices.npz') as data:
        known = int(data['known_count'])
        ports = data['ports'].tolist()
        static, dynamic = data['G'], data['C']
    input_index = ports.index(ports_by_source[source])
    output_index = ports.index('vout') - known
    matrix = static[None, :, :] + 2j*np.pi*measured.frequency_hz.to_numpy()[:, None, None]*dynamic[None, :, :]
    value = np.linalg.solve(matrix[:, known:, known:], -matrix[:, known:, input_index, None])[:, output_index, 0]
    native = measured.real.to_numpy() + 1j*measured.imag.to_numpy()
    return pd.DataFrame({'frequency_hz': measured.frequency_hz, 'native_real': native.real,
                         'native_imag': native.imag, 'reconstructed_real': value.real,
                         'reconstructed_imag': value.imag,
                         'relative_error': abs(value-native)/np.maximum(abs(native), 1e-20)})


def _summary_row(case, data_dir):
    folder = _folder(case, data_dir)
    circuit = load_circuit(case, data_dir)
    op = _table(folder, 'op.tsv')[0]
    nodes = circuit['nodes']
    voltages = dict(zip(nodes, op[1:1+len(nodes)]))
    input_current, amplifier_current = -op[1+len(nodes):3+len(nodes)]
    curve = psr(case, data_dir)
    worst = curve.iloc[curve.magnitude_db.argmax()]
    stored = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    poles_file = folder / 'terminal_model/nodal_matrices.npz'
    poles = closed_poles(case, data_dir) if poles_file.is_file() else None
    crossing = stored.get('voltage_return_crossings', stored.get('voltage_injection_crossings', []))
    capacitance = next(value for name,_,_,value in circuit['capacitors'] if name == 'Cout')
    row = {'case': case, 'corner': circuit['corner'], 'temperature_C': circuit['temperature'],
           'load_mA': circuit['load_a'] * 1e3, 'Cout_pF': capacitance * 1e12, 'output_V': voltages['vout'],
           'gate_V': voltages['gate'], 'amplifier_output_V': voltages['ea'],
           'VIN_current_mA': input_current * 1e3,
           'VAA_current_uA': amplifier_current * 1e6,
           'standing_current_uA': (input_current + amplifier_current - circuit['load_a']) * 1e6,
           'worst_PSR_dB': float(worst.magnitude_db), 'worst_PSR_frequency_Hz': float(worst.frequency_hz),
           'unstable_reconstructed_poles': int((poles.real_rad_s > 0).sum()) if poles is not None else np.nan,
           'worst_VAA_dB': stored.get('auxiliary_worst_dB', np.nan),
           'worst_VAA_frequency_Hz': stored.get('auxiliary_worst_Hz', np.nan),
           'loop_crossing_Hz': crossing[0].get('frequency_Hz', crossing[0].get('frequency_hz')) if crossing else np.nan,
           'phase_reserve_estimate_deg': crossing[0].get('voltage_injection_margin_deg', crossing[0].get('phase_reserve_deg')) if crossing else np.nan}
    for hz in (1e3, 1e4, 1e5, 1e6, 1e8, 1e9):
        row[f'PSR_at_{hz:g}_Hz_dB'] = float(np.interp(np.log10(hz), np.log10(curve.frequency_hz), curve.magnitude_db))
    return row


def dc_summary(data_dir=DATA, cases=None):
    cases = manifest(data_dir)['nominal_cases'] if cases is None else cases
    if not cases:
        return pd.DataFrame(columns=['case','corner','temperature_C','load_mA','Cout_pF','output_V','gate_V','standing_current_uA','worst_PSR_dB'])
    return pd.DataFrame([_summary_row(case, data_dir) for case in cases]).sort_values(['Cout_pF','load_mA']).reset_index(drop=True)


def capacitor_summary(data_dir=DATA):
    return dc_summary(data_dir, manifest(data_dir)['cap_cases'])


def corner_summary(data_dir=DATA):
    if not manifest(data_dir)['corner_cases']:
        return pd.DataFrame(columns=['case','corner','temperature_C','load_mA','Cout_pF','output_V','worst_PSR_dB'])
    return pd.DataFrame([_summary_row(case, data_dir) for case in manifest(data_dir)['corner_cases']]).sort_values(['corner','temperature_C','load_mA']).reset_index(drop=True)


def _bench(name, data_dir):
    record = manifest(data_dir)
    name = record.get('bench_aliases', {}).get(name, name)
    if name not in record['characteristics']:
        raise ValueError('Choose a listed native characteristic fixture')
    return Path(data_dir) / 'characteristics' / name


def load_transient(name='load_step_full', data_dir=DATA):
    raw = _table(_bench(name, data_dir), 'waveform.tsv')
    if raw.shape[1] == 5:
        return pd.DataFrame(raw, columns=['time_s','output_V','gate_V','amplifier_output_V','driver_H_V'])
    frame = pd.DataFrame(raw, columns=['time_s', 'output_V', 'gate_V', 'amplifier_output_V', 'VIN_source_current_A', 'VAA_source_current_A'])
    frame['VIN_draw_A'] = -frame.pop('VIN_source_current_A')
    frame['VAA_draw_A'] = -frame.pop('VAA_source_current_A')
    return frame


def transient_metrics(name='load_step_full', data_dir=DATA):
    frame = load_transient(name, data_dir)
    recorded = json.loads((_bench(name, data_dir) / 'bench_metrics.json').read_text(encoding='utf-8'))
    t, output = frame.time_s.to_numpy(), frame.output_V.to_numpy()
    first, second, end = 2e-6, 7e-6, float(t[-1])
    edge = recorded['edge_ns'] * 1e-9
    before = float(output[(t > first-.2e-6) & (t < first)].mean())
    heavy = float(output[(t > second-.2e-6) & (t < second)].mean())
    light = float(output[t > end-.2e-6].mean())
    def settled(start, stop, target, tolerance):
        mask = (t >= start) & (t < stop)
        times, levels = t[mask], output[mask]
        bad = np.flatnonzero(abs(levels-target) > tolerance)
        if not len(bad):
            return 0.0
        index = bad[-1] + 1
        return float((times[index]-start)*1e9) if index < len(times) else None
    return {'name': name, 'low_mA': recorded['low_mA'], 'high_mA': recorded['high_mA'],
            'edge_ns': recorded['edge_ns'], 'cout_pF': recorded['cout_pF'],
            'undershoot_mV': float((before-output[(t >= first) & (t < second)].min())*1e3),
            'overshoot_mV': float((output[t >= second].max()-light)*1e3),
            'heavy_steady_V': heavy, 'light_steady_V': light,
            'settling_to_1mV_ns': [settled(first+edge, second, heavy, .001), settled(second+edge, end, light, .001)],
            'settling_to_10mV_ns': [settled(first+edge, second, heavy, .01), settled(second+edge, end, light, .01)]}


def load_line(load_mA=50, data_dir=DATA):
    name = f'line_load{load_mA/1e3:.0e}'
    raw = _table(_bench(name, data_dir), 'line.tsv')
    frame = pd.DataFrame(raw, columns=['VIN_V', 'output_V', 'gate_V', 'VIN_source_current_A', 'VAA_source_current_A'])
    frame['VIN_draw_A'] = -frame.pop('VIN_source_current_A')
    frame['VAA_draw_A'] = -frame.pop('VAA_source_current_A')
    return frame


def startup(data_dir=DATA):
    raw = _table(_bench('startup_resistive_10mA', data_dir), 'waveform.tsv')
    if raw.shape[1] == 10:
        frame = pd.DataFrame(raw, columns=['time_s','output_V','gate_V','amplifier_output_V','driver_H_V','VIN_V','VAA_V','reference_V','VIN_source_current_A','VAA_source_current_A'])
        frame['VIN_draw_A'] = -frame.pop('VIN_source_current_A')
        frame['VAA_draw_A'] = -frame.pop('VAA_source_current_A')
        return frame
    return pd.DataFrame(raw, columns=['time_s','output_V','gate_V','amplifier_output_V','VIN_V','VAA_V'])


def load_noise(load_mA=50, data_dir=DATA):
    raw = _table(_bench(f'noise_load{load_mA/1e3:.0e}', data_dir), 'noise.tsv')
    return pd.DataFrame(raw, columns=['frequency_hz','output_V_per_sqrt_Hz','input_V_per_sqrt_Hz'])


def noise_summary(data_dir=DATA):
    records = []
    integrate = getattr(np, 'trapezoid', np.trapz) if hasattr(np, 'trapz') else np.trapezoid
    for load in manifest(data_dir).get('noise_load_mA', (.1, 10, 50)):
        curve = load_noise(load, data_dir)
        row = {'load_mA': load}
        for maximum in (1e5, min(1e9, float(curve.frequency_hz.max()))):
            selected = curve[(curve.frequency_hz >= 10*(1-1e-9)) & (curve.frequency_hz <= maximum*(1+1e-9))]
            row[f'noise_10_Hz_to_{maximum:g}_Hz_uVrms'] = float(np.sqrt(integrate(selected.output_V_per_sqrt_Hz**2, selected.frequency_hz))*1e6)
        folder = _bench(f'noise_load{load/1e3:.0e}',data_dir)
        if (folder/'integrated.tsv').is_file() or (folder/'integrated.tsv.gz').is_file():
            row[f'noise_10_Hz_to_{float(curve.frequency_hz.max()):g}_Hz_uVrms'] = float(_table(folder,'integrated.tsv')[0,1]*1e6)
        records.append(row)
    return pd.DataFrame(records)


def port_response(case=DEFAULT_CASE, data_dir=DATA):
    """Native input and output port impedance magnitudes with the precision path open."""
    if case not in manifest(data_dir).get('ports_cases', []):
        raise ValueError('This case has no retained port measurement')
    folder = Path(data_dir)/'ports'/case
    entering = _table(folder,'input.tsv')
    leaving = _table(folder,'output.tsv')
    if not np.allclose(entering[:,0],leaving[:,0]):
        raise ValueError('Port measurement frequency grids differ')
    zin = -(entering[:,1]+1j*entering[:,2])/(entering[:,3]+1j*entering[:,4])
    zout = -(leaving[:,1]+1j*leaving[:,2])
    return pd.DataFrame({'frequency_hz':entering[:,0], 'input_ohm':abs(zin),
                         'output_ohm':abs(zout),'input_to_output_ratio':abs(zin)/abs(zout)})


def port_summary(data_dir=DATA):
    records = []
    for case in manifest(data_dir).get('ports_cases', []):
        response = port_response(case,data_dir)
        crossings = _crossings(loop_response(case,data_dir))
        if not crossings:
            continue
        frequency = crossings[0]['frequency_hz']
        around = response[(response.frequency_hz >= frequency/2) & (response.frequency_hz <= frequency*2)]
        circuit = load_circuit(case,data_dir)
        cap = next(v for n,_,_,v in circuit['capacitors'] if n=='Cout')*1e12
        records.append({'case':case,'load_mA':circuit['load_a']*1e3,'Cout_pF':cap,
                        'crossing_Hz':frequency,
                        'minimum_input_to_output_ratio':float(around.input_to_output_ratio.min()),
                        'input_ohm_at_crossing':float(np.interp(np.log(frequency),np.log(response.frequency_hz),response.input_ohm)),
                        'output_ohm_at_crossing':float(np.interp(np.log(frequency),np.log(response.frequency_hz),response.output_ohm))})
    return pd.DataFrame(records)


def mechanism_ac(name='no_ripple_cap_load50mA', source='power', data_dir=DATA):
    if name not in manifest(data_dir).get('mechanism_cases', []) or source not in ('power','auxiliary','reference','impedance','loop'):
        raise ValueError('Choose a retained mechanism and excitation')
    raw = _table(Path(data_dir)/'mechanisms'/name,source+'.tsv')
    value = raw[:,1]+1j*raw[:,2]
    if source=='impedance':
        value=-value
    return pd.DataFrame({'frequency_hz':raw[:,0],'real':value.real,'imag':value.imag,
                         'magnitude':abs(value),'magnitude_db':20*np.log10(np.maximum(abs(value),1e-30)),
                         'phase_deg':np.unwrap(np.angle(value))*180/np.pi})


def mechanism_summary(data_dir=DATA):
    rows=[]
    for name in manifest(data_dir).get('mechanism_cases', []):
        folder=Path(data_dir)/'mechanisms'/name
        op=_table(folder,'op.tsv')[0]
        if name=='no_bleed_dc_guess':
            rows.append({'case':name,'change':'Output bleeder removed','load_mA':0.,'output_V':float(op[1]),
                         'amplifier_output_V':float(op[3]),'worst_PSR_dB':np.nan,'worst_VAA_dB':np.nan})
        else:
            load=0. if 'load0mA' in name else 50.
            # The native mechanism deck saves the same DC node order as the primary circuit.
            circuit=load_circuit(f'tied_load{load:g}mA_cout100pF',data_dir)
            rows.append({'case':name,'change':'VIN to H capacitor removed','load_mA':load,
                         'output_V':float(op[1+circuit['nodes'].index('vout')]),
                         'amplifier_output_V':float(op[1+circuit['nodes'].index('ea')]),
                         'worst_PSR_dB':float(mechanism_ac(name,'power',data_dir).magnitude_db.max()),
                         'worst_VAA_dB':float(mechanism_ac(name,'auxiliary',data_dir).magnitude_db.max())})
    return pd.DataFrame(rows)


def verify_saved_data(data_dir=DATA):
    data_dir = Path(data_dir)
    record = manifest(data_dir)
    for item in record['files']:
        path = data_dir / item['path']
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['published_sha256']:
            raise ValueError(f"Evidence hash differs: {item['path']}")
        if path.suffix == '.gz' and hashlib.sha256(gzip.decompress(raw)).hexdigest() != item['source_sha256']:
            raise ValueError('Lossless native table hash check failed')
    nominal, corners = dc_summary(data_dir), corner_summary(data_dir)
    assert len(nominal) == len(record['nominal_cases']) and len(corners) == len(record['corner_cases'])
    if record.get('data_origin') != 'regenerated_native':
        assert len(nominal) == 6 and len(corners) == 30
        assert np.isclose(nominal.worst_PSR_dB.max(), -18.5347, atol=.002)
        assert np.isclose(corners.worst_PSR_dB.max(), -15.4532, atol=.002)
    if record.get('bench_aliases', {}).get('load_step_full','load_step_full') in record['characteristics']:
        event = transient_metrics(data_dir=data_dir)
        if record.get('data_origin') != 'regenerated_native':
            assert np.isclose(event['undershoot_mV'], 363.52565, atol=.02)
    return {'files_verified': len(record['files']), 'nominal_cases': len(nominal),
            'process_temperature_endpoint_cases': len(corners),
            'nominal_worst_PSR_dB': float(nominal.worst_PSR_dB.max()),
            'corner_worst_PSR_dB': float(corners.worst_PSR_dB.max()),
            'capacitor_endpoint_cases': len(record.get('cap_cases', [])),
            'evidence_class': 'Replay of native ngspice 47 results for the complete tied reference regulator',
            'fresh_native_simulation_performed': False}


def native_tools():
    model_setting = os.environ.get('SKY130_MODEL')
    if model_setting:
        candidates = [Path(model_setting).expanduser()]
    else:
        root = os.environ.get('PDK_ROOT')
        if root:
            root = Path(root).expanduser()
            candidates = [root/'sky130A/libs.tech/ngspice/sky130.lib.spice',
                          root/'libs.tech/ngspice/sky130.lib.spice',
                          root/'share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice']
        else:
            try:
                from .sky130_models import ensure_models
            except ImportError:
                from sky130_models import ensure_models
            candidates = [Path(ensure_models())]
    model = next((p.resolve() for p in candidates if p.is_file()), None)
    executable = os.environ.get('NGSPICE') or shutil.which('ngspice')
    if model is None or not executable:
        raise RuntimeError('A native ngspice executable and public SKY130 model library are required')
    executable = Path(shutil.which(executable) or executable).expanduser().resolve()
    if not executable.is_file():
        raise FileNotFoundError('NGSPICE does not name an executable')
    return executable, model


def _run_deck(executable, folder, text):
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'fixture.spice').write_text(text, encoding='utf-8')
    initialization = folder/'init'
    initialization.mkdir(exist_ok=True)
    startup_text = 'set ngbehavior=hsa\nset ng_nomodcheck\n'
    for path in (initialization/'spinit', initialization/'.spiceinit', folder/'.spiceinit'):
        path.write_text(startup_text)
    environment = os.environ.copy()
    environment['SPICE_USERINIT_DIR'] = str(initialization)
    result = subprocess.run([str(executable), '-b', 'fixture.spice'], cwd=folder, env=environment,
                            capture_output=True, text=True, timeout=300)
    log = result.stdout + result.stderr
    (folder/'ngspice.log').write_text(log, encoding='utf-8')
    if result.returncode or re.search(r'(^|\n)\s*(fatal error|error:)', log, re.I):
        raise RuntimeError(f'Native ngspice failed in {folder.name}. Inspect its log')


def _fresh_op(folder, circuit):
    raw = _table(folder, 'op.tsv')[0]
    nodes = circuit['nodes']
    circuit['voltages'] = dict(zip(nodes, raw[1:1+len(nodes)].tolist()))
    rows = []
    parameters = circuit.get('op_parameters', PARAMETERS)
    for index, device in enumerate(circuit['devices']):
        start = 3 + len(nodes) + index*len(parameters)
        row = dict(zip(parameters, raw[start:start+len(parameters)].tolist()))
        row.update(name=device[0], drain=device[1], gate=device[2], source=device[3], body=device[4],
                   kind=device[5], width_um=device[6], length_um=device[7], multiplicity=device[8])
        row['margin_v'] = row['vds'] - row['vdsat']
        rows.append(row)
    pd.DataFrame(rows).to_csv(folder/'operating_point.csv', index=False)
    (folder/'circuit.json').write_text(json.dumps(circuit, indent=2)+'\n', encoding='utf-8')
    return circuit


def _fresh_terminal(executable, model, folder, circuit, source):
    """Rebias every independent terminal fixture at the new native operating point."""
    bias = {'0': 0.0, **circuit['voltages']}
    terminals = ('d','g','s','b')
    lines = ['Native transistor terminal current extraction', f'.lib "{model.as_posix()}" {circuit["corner"]}',
             '.option scale=1e-6', f'.temp {circuit["temperature"]}']
    instances = {line.split()[0].lower(): line.split() for line in
                 (source/'fixture.spice').read_text(encoding='utf-8').splitlines() if line.lower().startswith('x')}
    for index, device in enumerate(circuit['devices']):
        ports = [f'q{index}{terminal}' for terminal in terminals]
        for terminal, node in zip(terminals, device[1:5]):
            lines.append(f'Vq{index}{terminal} q{index}{terminal} 0 dc {bias[node]:.17g} ac 0')
        original = instances['x'+device[0].lower()]
        lines.append(' '.join([f'Xq{index}', *ports, *original[5:]]))
    lines += ['.control','set numdgt=15','set wr_singlescale','set wr_vecnames']
    for terminal in terminals:
        lines += [f'alter Vq{i}{terminal} acmag=1' for i in range(len(circuit['devices']))]
        lines += ['ac dec 1 10k 100Meg', 'wrdata '+terminal+'.tsv '+' '.join(
            f'real(-i(Vq{i}{t})) imag(-i(Vq{i}{t}))' for i in range(len(circuit['devices'])) for t in terminals)]
        lines += [f'alter Vq{i}{terminal} acmag=0' for i in range(len(circuit['devices']))]
    lines += ['quit','.endc','.end']
    work = folder/'terminal_model'
    _run_deck(executable, work, '\n'.join(lines)+'\n')
    count = len(circuit['devices'])
    static_device = np.zeros((count,4,4))
    charge_device = np.zeros_like(static_device)
    for column, terminal in enumerate(terminals):
        raw = _table(work, terminal+'.tsv')
        row = raw[np.argmin(abs(raw[:,0]-1e5))]
        values = (row[1::2]+1j*row[2::2]).reshape(count,4)
        static_device[:,:,column] = values.real
        charge_device[:,:,column] = values.imag/(2*np.pi*row[0])
    merge = lambda node: 'vout' if node == 'vfb' else node
    known = ['0','vin','vaa','reference']
    if 'bias_reference' in circuit['nodes']:
        known.append('bias_reference')
    ports = known + sorted({merge(n) for n in circuit['nodes']}-set(known))
    index = {node:i for i,node in enumerate(ports)}
    static = np.zeros((len(ports),len(ports)))
    dynamic = np.zeros_like(static)
    for device, dc, charge in zip(circuit['devices'],static_device,charge_device):
        for a, one in enumerate(device[1:5]):
            for b, two in enumerate(device[1:5]):
                static[index[merge(one)],index[merge(two)]] += dc[a,b]
                dynamic[index[merge(one)],index[merge(two)]] += charge[a,b]
    for matrix, elements, resistance in ((static,circuit['resistors'],True),(dynamic,circuit['capacitors'],False)):
        for _, one, two, value in elements:
            a,b = index[merge(one)],index[merge(two)]
            weight = 1/value if resistance else value
            matrix[a,a] += weight
            matrix[b,b] += weight
            matrix[a,b] -= weight
            matrix[b,a] -= weight
    np.savez(work/'nodal_matrices.npz', G=static, C=dynamic, ports=np.array(ports), known_count=len(known),
             Gdev=static_device, Cdev=charge_device)
    poles = np.linalg.eigvals(-np.linalg.solve(dynamic[len(known):,len(known):],static[len(known):,len(known):]))
    report = {'rhp_poles': int((poles.real>0).sum()),
              'poles_rad_s': [[float(p.real),float(p.imag)] for p in poles],
              'method': 'Connected linear reconstruction from fresh native terminal currents at the fresh native DC operating point'}
    (work/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def regenerate(output_dir, cases=None, include_characteristics=True, terminal_extraction=False):
    """Run real ngspice for six nominal loads and the listed characteristic benches.

    Pass manifest()['all_cases'] for all characterized cases. Every case is a complete
    physical regulator. No circuit simulator is replaced by a synthetic model.
    """
    executable, model = native_tools()
    record = manifest()
    cases = list(record['nominal_cases'] if cases is None else cases)
    if len(set(cases)) != len(cases) or any(c not in record['all_cases'] for c in cases):
        raise ValueError('Use unique case names from the manifest')
    destination = Path(output_dir).expanduser().resolve()
    if destination == DATA.resolve() or DATA.resolve() in destination.parents:
        raise ValueError('Use a new folder outside the included results')
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError('Fresh native output folder must be empty')
    if any(c in model.as_posix() for c in ('\n','\r','"')):
        raise ValueError('Model path contains unsupported quote or newline')
    destination.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([str(executable),'--version'], capture_output=True,text=True,timeout=20)
    results = []
    for case in cases:
        source, folder = _folder(case), destination/'cases'/case
        template = (source/'fixture.spice').read_text(encoding='utf-8')
        _run_deck(executable,folder,template.replace('${SKY130_MODEL}',model.as_posix()))
        circuit = _fresh_op(folder,load_circuit(case))
        native_curves = {}
        summary = {'name':case, 'native_simulator':'ngspice', 'voltage_return_crossings':[]}
        for label in ('power','auxiliary','reference','impedance','loop'):
            data = _table(folder,label+'.tsv')
            if data.shape[1] != 1+2*len(circuit.get('ac_nodes',circuit['nodes'])) or not np.isfinite(data).all():
                raise ValueError('Unexpected native AC table')
            if not (np.isclose(data[0,0],1) and np.isclose(data[-1,0],1e9)):
                raise ValueError('Unexpected native frequency range')
            native_curves[label] = int(len(data))
            nodes = circuit.get('ac_nodes',circuit['nodes'])
            column = 1+2*nodes.index('vout')
            value = data[:,column]+1j*data[:,column+1]
            peak = int(np.argmax(abs(value)))
            summary[label+'_worst_dB'] = float(20*np.log10(abs(value[peak])))
            summary[label+'_worst_Hz'] = float(data[peak,0])
            if label == 'loop':
                column = 1+2*nodes.index('vfb')
                ratio = -value/(data[:,column]+1j*data[:,column+1])
                curve = pd.DataFrame({'frequency_hz':data[:,0],'magnitude_db':20*np.log10(abs(ratio)),
                                      'phase_deg':np.unwrap(np.angle(ratio))*180/np.pi})
                summary['voltage_return_crossings'] = [
                    {'frequency_Hz':x['frequency_hz'],'voltage_injection_margin_deg':x['phase_reserve_estimate_deg']}
                    for x in _crossings(curve)]
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        item = {'case':case,'output_V':circuit['voltages']['vout'],'native_AC_points':native_curves}
        if terminal_extraction:
            item['terminal_reconstruction'] = _fresh_terminal(executable,model,folder,circuit,source)
        results.append(item)
    benches = []
    port_cases = []
    mechanisms = []
    if include_characteristics:
        for name in record['characteristics']:
            source = _bench(name,DATA)
            folder = destination/'characteristics'/name
            template = (source/'fixture.spice').read_text(encoding='utf-8')
            _run_deck(executable,folder,template.replace('${SKY130_MODEL}',model.as_posix()))
            filenames = list(folder.glob('*.tsv'))
            if not filenames:
                raise ValueError('Native characteristic produced no data')
            for filename in filenames:
                if not np.isfinite(_table(folder,filename.name)).all():
                    raise ValueError('Nonfinite native characteristic output')
            if (source/'bench_metrics.json').is_file():
                metadata = json.loads((source/'bench_metrics.json').read_text(encoding='utf-8'))
                specification = {key:metadata[key] for key in ('name','low_mA','high_mA','edge_ns','cout_pF') if key in metadata}
                (folder/'bench_metrics.json').write_text(json.dumps(specification,indent=2)+'\n',encoding='utf-8')
            benches.append(name)
        for case in record.get('ports_cases', []):
            if case not in cases:
                continue
            source = DATA/'ports'/case
            folder = destination/'ports'/case
            template = (source/'fixture.spice').read_text(encoding='utf-8')
            circuit = json.loads((destination/'cases'/case/'circuit.json').read_text(encoding='utf-8'))
            template = re.sub(r'(?m)^(Vinject\s+\S+\s+0\s+dc\s+)\S+',
                              lambda m:m[1]+format(circuit['voltages']['vout'],'.17g'),template)
            _run_deck(executable,folder,template.replace('${SKY130_MODEL}',model.as_posix()))
            for filename in ('input.tsv','output.tsv'):
                if not np.isfinite(_table(folder,filename)).all():
                    raise ValueError('Nonfinite native port data')
            port_cases.append(case)
        for name in record.get('mechanism_cases', []):
            source = DATA/'mechanisms'/name
            folder = destination/'mechanisms'/name
            template = (source/'fixture.spice').read_text(encoding='utf-8')
            _run_deck(executable,folder,template.replace('${SKY130_MODEL}',model.as_posix()))
            if not np.isfinite(_table(folder,'op.tsv')).all():
                raise ValueError('Nonfinite native mechanism data')
            mechanisms.append(name)
    report = {'evidence_class':'Fresh native ngspice complete regulator simulations',
              'simulator_version':version.stdout+version.stderr,
              'model_library_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
              'cases':results,'characteristics':benches,'port_cases':port_cases,'mechanisms':mechanisms,
              'analysis_source':'new native tables'}
    (destination/'native_run_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    run_data = {key:value for key,value in record.items() if key not in ('files','nominal_cases','cap_cases','corner_cases','all_cases','characteristics')}
    artifact_records = []
    for path in sorted(destination.rglob('*')):
        if path.is_file() and path.suffix in ('.spice','.log','.tsv','.csv','.json','.npz'):
            raw = path.read_bytes()
            artifact_records.append({'path':path.relative_to(destination).as_posix(),
                                     'published_sha256':hashlib.sha256(raw).hexdigest(),
                                     'published_bytes':len(raw),
                                     'transformation':'Generated by this native ngspice run'})
    run_data.update(evidence_class='Fresh native ngspice complete regulator results',
                    data_origin='regenerated_native',
                    all_cases=cases, nominal_cases=[c for c in record['nominal_cases'] if c in cases],
                    cap_cases=[c for c in record.get('cap_cases',[]) if c in cases],
                    corner_cases=[c for c in record['corner_cases'] if c in cases],
                    characteristics=benches, ports_cases=port_cases, mechanism_cases=mechanisms, files=artifact_records)
    (destination/'manifest.json').write_text(json.dumps(run_data,indent=2)+'\n',encoding='utf-8')
    return report


def figures(data_dir=DATA):
    import matplotlib.pyplot as plt
    results = {}
    rows = dc_summary(data_dir)
    fig,axes = plt.subplots(1,2,figsize=(10,3.7),constrained_layout=True)
    for case in rows.case:
        load = load_circuit(case,data_dir)['load_a']*1e3
        for axis,source in zip(axes,('power','auxiliary')):
            curve = load_ac(case,source,data_dir=data_dir)
            axis.semilogx(curve.frequency_hz,curve.magnitude_db,label=f'{load:g} mA')
    for axis,title in zip(axes,('VIN supply transfer','VAA supply transfer')):
        axis.set(title=title,xlabel='Frequency (Hz)',ylabel='20 log10 |Vout / Vsupply| (dB)',xlim=(1,1e9))
        axis.grid(alpha=.25)
        axis.legend(fontsize=8)
    results['supply_rejection'] = fig
    fig,axes = plt.subplots(1,2,figsize=(10,3.7),constrained_layout=True)
    for case in rows.case:
        curve = loop_response(case,data_dir)
        load = load_circuit(case,data_dir)['load_a']*1e3
        axes[0].semilogx(curve.frequency_hz,curve.magnitude_db,label=f'{load:g} mA')
        axes[1].semilogx(curve.frequency_hz,curve.phase_deg,label=f'{load:g} mA')
    for axis,title,ylabel in zip(axes,('Voltage injection loop estimate','Voltage injection loop phase'),('Magnitude (dB)','Phase (degrees)')):
        axis.set(title=title,xlabel='Frequency (Hz)',ylabel=ylabel,xlim=(1e3,1e9))
        axis.grid(alpha=.25)
    axes[0].axhline(0,color='grey',linewidth=.8)
    axes[1].axhline(-180,color='grey',linewidth=.8)
    axes[0].legend(fontsize=8)
    results['loop'] = fig
    fig,axes = plt.subplots(1,2,figsize=(10,3.7),constrained_layout=True)
    wave = load_transient(data_dir=data_dir)
    axes[0].plot(wave.time_s*1e6,wave.output_V)
    axes[0].set(title='0 to 50 mA and return, 10 ns edges',xlabel='Time (us)',ylabel='Vout (V)')
    start = startup(data_dir)
    for column,label in (('output_V','Vout'),('VIN_V','VIN'),('VAA_V','VAA')):
        axes[1].plot(start.time_s*1e6,start[column],label=label)
    axes[1].set(title='Simultaneous supply and reference ramps',xlabel='Time (us)',ylabel='Voltage (V)',xlim=(0,4))
    axes[1].legend(fontsize=8)
    for axis in axes:
        axis.grid(alpha=.25)
    results['transient_startup'] = fig
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('check','summary','regenerate'))
    parser.add_argument('--output',type=Path)
    parser.add_argument('--all-cases',action='store_true')
    args = parser.parse_args()
    if args.command == 'check':
        print(json.dumps(verify_saved_data(),indent=2))
    elif args.command == 'summary':
        print(dc_summary().to_string(index=False))
        print(json.dumps(transient_metrics(),indent=2))
    else:
        if args.output is None:
            parser.error('regenerate requires --output')
        cases = manifest()['all_cases'] if args.all_cases else None
        print(json.dumps(regenerate(args.output,cases=cases),indent=2))


if __name__ == '__main__':
    main()
