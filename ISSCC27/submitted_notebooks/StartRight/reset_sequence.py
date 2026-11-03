"""Run and measure a declared reset sequence without assuming a passing verdict.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse, copy, hashlib, json, math, time, uuid
import numpy as np
import pilot
from schematic_support import verify_models
from reset_contract import Band, Window, evaluate, source_work, waveform
from sequence_circuits import generate_sequence

HERE = Path(__file__).resolve().parent
SOURCES = ['reset_sequence.py', 'sequence_circuits.py', 'reset_contract.py', 'sequence_spec.json',
           'schematic_support.py', 'pilot.py']


def specification():
    return json.loads((HERE / 'sequence_spec.json').read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf8')


def validate(corner, low_V, command):
    if corner not in ('tt', 'sf'):
        raise ValueError('This lesson declares TT and SF, both at 27 C')
    if isinstance(low_V, bool) or not isinstance(low_V, (int, float)) or not math.isfinite(low_V) or not 0 <= low_V <= 1.8:
        raise ValueError('Dip voltage must be between 0 and 1.8 V')
    if not isinstance(command, bool):
        raise ValueError('Command must be True or False')


def measure(cold, interface, config, scenario, contract, points, windows):
    expected = 9 if config['variant'] == 'rc' else 11
    if cold.ndim != 2 or cold.shape[1] != expected or interface.ndim != 2 or interface.shape[1] != 10:
        raise ValueError('Unexpected or missing waveform columns')
    t, values = waveform(cold[:, 0], dict(a=cold[:, 1], b=cold[:, 2], c=cold[:, 3], vdd=cold[:, 5], vsg=cold[:, 5]-cold[:, 3]))
    if np.max(abs(cold[0, 1:4])) > 1e-5 or abs(cold[0, 5]) > 1e-8:
        raise ValueError('Charged initial state is outside this zero-supply protocol')
    ti, inputs = waveform(interface[:, 0], dict(vdd=interface[:, 1], setn=interface[:, 2]))
    if not np.array_equal(t, ti) or np.max(abs(interface[:, 3:6] - cold[:, [3, 1, 2]])) > 1e-10 or np.max(abs(interface[:, 1]-cold[:, 5])) > 1e-10:
        raise ValueError('The input and load vectors are not the same acquisition')
    f = scenario['normal_set']; V = scenario['supply_V']
    start = points[3][0] + f['delay_after_first_observation_s']; end = start + f['duration_s']; edge = f['edge_s']
    if f.get('skip_command'):
        ordinary = np.ones(len(ti), dtype=bool)
    else:
        low = (ti >= start+edge+2e-9) & (ti <= end-1e-9)
        if not np.any(low) or np.max(abs(inputs['setn'][low])) > .001:
            raise ValueError('The functional set command was not applied')
        ordinary = (ti <= start-1e-9) | (ti >= end+edge+2e-9)
    if not ordinary.any() or np.max(abs(inputs['setn'][ordinary]-inputs['vdd'][ordinary])) > .001:
        raise ValueError('The inactive functional input does not follow VDD')
    intended = [Band('a', upper=contract['logic_low_fraction']*V), Band('b', lower=contract['logic_high_fraction']*V)]
    opposite = [Band('a', lower=contract['logic_high_fraction']*V), Band('b', upper=contract['logic_low_fraction']*V)]
    rail = [Band('vdd', lower=contract['supply_ready_fraction']*V)]
    release = rail + [Band('c', lower=contract['reset_release_fraction']*V), Band('vsg', upper=.05*V)]
    before = points[4][0]-1e-7
    result = evaluate(t, values, supply_points=points, windows=[Window(w['id'], w['start_s'], w['ramp_end_s'], w['stop_s']) for w in windows],
                      state_bands=rail+intended, release_bands=release,
                      state_delay_s=contract['logic_deadline_after_ramp_s'], release_delay_s=contract['release_deadline_after_ramp_s'], hold_s=contract['hold_s'],
                      precondition_interval=(before-5e-6, before), prior_bands=intended if f.get('skip_command') else opposite, alternate_bands=opposite)
    work = source_work(t, dict(VDD=(cold[:, 5], cold[:, 4]), functional_input=(interface[:, 6], interface[:, 7]), command_marker=(interface[:, 8], interface[:, 9])))
    result.update(precondition_hold_s=5e-6, source_work=work,
                  eligible_delivered_J=work['delivered_J'] if result['observed_pass'] and result['declared_precondition_verified'] else None,
                  energy_scope='All independent voltage sources in this deck. Zero-volt current probes do no work. Delivery and returns are separate. No ranking of failed circuits or different loads.')
    return result


def run_sequence(*, corner='tt', low_V=.9, command=True, variants=None, output=None):
    validate(corner, low_V, command)
    spec = specification(); wanted = variants or ['frozen_rc_sr', 'detector_10M_sr']
    configs = {c['id']: c for c in spec['configurations']}
    if not wanted or len(set(wanted)) != len(wanted) or set(wanted)-set(configs):
        raise ValueError('Choose distinct declared reset variants')
    verify_models()
    destination = Path(output) if output else HERE/'results/sequence_runs'/('run_'+uuid.uuid4().hex[:10])
    destination.mkdir(parents=True, exist_ok=False)
    scenario = copy.deepcopy(spec['scenario']); scenario['corner'] = corner; scenario['recovery']['low_V'] = low_V
    scenario['normal_set']['skip_command'] = not command
    record = dict(status='in_progress', scenario=scenario, contract=spec['contract'], settings=spec['settings'],
                  source_hashes={n: hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
                  output_dir=str(destination), evidence_kind='fresh execution', cases=[])
    save(destination/'run.json', record)
    previous_out = pilot.OUT
    try:
        pilot.OUT = destination/'raw'; pilot.OUT.mkdir()
        for name in wanted:
            config = configs[name]; deck, points, windows = generate_sequence(config, scenario, spec['contract'], spec['settings'])
            actual = deck.replace('.control\n', '.control\nset numdgt=17\n')
            row = dict(configuration=config, solver=config.get('solver', 'klu'), case=name, deck_sha256=hashlib.sha256(actual.encode()).hexdigest())
            begin = time.perf_counter()
            try:
                raw = pilot.simulate(name, actual, compatibility='hsa', solver=row['solver'], threads=1)
                log = (raw/'ngspice.log').read_text(errors='replace')
                if 'Transient op started' in log or 'timestep too small' in log.lower():
                    raise ValueError('Incomplete transient or operating-point fallback')
                row.update(measure(np.loadtxt(raw/'cold.dat', skiprows=1), np.loadtxt(raw/'interface.dat', skiprows=1), config, scenario, spec['contract'], points, windows))
            except Exception as error:
                row.update(status='unresolved', observed_pass=None, sampled_restoration_observed=None, reason=type(error).__name__+': '+str(error))
            row['wall_s'] = time.perf_counter()-begin; record['cases'].append(row); save(destination/'run.json', record)
            print(name, row['status'], 'observed pass:', row['observed_pass'], 'alternate state:', row.get('alternate_state_exercised'), flush=True)
    finally:
        pilot.OUT = previous_out
    record['status'] = 'completed' if all(r['status']=='measured' for r in record['cases']) else 'has_unresolved'
    save(destination/'run.json', record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--corner', choices=['tt', 'sf'], default='tt'); p.add_argument('--dip-V', type=float, default=.9)
    p.add_argument('--retain-state', action='store_true'); p.add_argument('--include-mos-discharge', action='store_true'); a = p.parse_args()
    variants = [c['id'] for c in specification()['configurations']] if a.include_mos_discharge else None
    run_sequence(corner=a.corner, low_V=a.dip_V, command=not a.retain_state, variants=variants)


if __name__ == '__main__':
    main()
