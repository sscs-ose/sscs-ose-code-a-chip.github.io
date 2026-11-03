"""Predeclared node-voltage checks of the reset lesson, not a reset threshold model.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import copy
from datetime import datetime, timezone
import hashlib
import json
import uuid
import numpy as np
import matplotlib.pyplot as plt
from reset_sequence import HERE, specification, run_sequence, measure
from sequence_circuits import extended_history, generate_sequence
from sequence_analysis import ideal_rc

CONFIG = 'frozen_rc_sr'
DIPS = (.6, 1.2)
NODE_TOLERANCE_V = .020


def prediction_plan():
    """Freeze both node predictions before acquiring either new SPICE case."""
    spec = specification()
    config = next(c for c in spec['configurations'] if c['id'] == CONFIG)
    rows = []
    for low in DIPS:
        scenario = copy.deepcopy(spec['scenario'])
        scenario['recovery']['low_V'] = low
        scenario['normal_set']['skip_command'] = False
        points, windows = extended_history(scenario, spec['contract'])
        at = windows[1]['start_s']
        voltage = float(ideal_rc(points, config['resistance_ohm'], config['capacitance_F'], [at])[0])
        rows.append(dict(dip_V=low, at_s=at, predicted_c_V=voltage))
    names = ('mechanism_lab.py', 'sequence_analysis.py', 'reset_sequence.py',
             'sequence_circuits.py', 'sequence_spec.json', 'reset_contract.py')
    return dict(kind='predeclared lesson check', created_utc=datetime.now(timezone.utc).isoformat(),
                corner='tt', temperature_C=27, configuration=CONFIG,
                node_tolerance_V=NODE_TOLERANCE_V, predictions=rows,
                source_hashes={n: hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},
                scope='Unloaded RC predicts c at recovery start, not latch restoration. '
                      '20 mV is a declared lesson agreement criterion, not physical uncertainty. '
                      'Two finite dip levels; not a global holdout, threshold qualification or optimization.')


def vectors(record):
    if record['status'] != 'completed':
        raise ValueError('Unresolved acquisition has no mechanism verdict')
    row = next(r for r in record['cases'] if r['configuration']['id'] == CONFIG)
    folder = Path(record['output_dir'])/'raw'/row['case']
    data = np.loadtxt(folder/'cold.dat', skiprows=1)
    interface = np.loadtxt(folder/'interface.dat', skiprows=1)
    _, points, windows = generate_sequence(row['configuration'], record['scenario'], record['contract'], record['settings'])
    checked = measure(data, interface, row['configuration'], record['scenario'], record['contract'], points, windows)
    for key in ('observed_pass', 'declared_precondition_verified', 'alternate_state_exercised', 'sampled_restoration_observed'):
        if checked[key] != row[key]:
            raise ValueError('Raw vector and recorded verdict disagree: '+key)
    return row, data, windows


def score_prediction(prediction, record, tolerance=NODE_TOLERANCE_V):
    row, data, windows = vectors(record)
    at = windows[1]['start_s']
    if record['scenario']['corner'] != 'tt' or record['scenario']['temperature_C'] != 27 or record['scenario']['normal_set']['skip_command']:
        raise ValueError('The declared check requires TT/27 C and an ordinary write')
    if record['scenario']['recovery']['low_V'] != prediction['dip_V'] or abs(at-prediction['at_s']) > 1e-12:
        raise ValueError('Prediction does not identify this experiment')
    observed = float(np.interp(at, data[:, 0], data[:, 3]))
    error = observed-prediction['predicted_c_V']
    return dict(**prediction, measured_c_V=observed, signed_error_V=error,
                node_prediction_met=bool(abs(error) <= tolerance),
                prior_verified=row['declared_precondition_verified'],
                recovery_met=row['events'][1]['pass_contract'],
                restoration_observed=row['sampled_restoration_observed'],
                record=str(Path(record['output_dir'])/'run.json'))


def paired_control(retained, commanded):
    """Ordinary writing changes the stored state, with the same supply history."""
    ar, a, wa = vectors(retained)
    br, b, wb = vectors(commanded)
    sa, sb = copy.deepcopy(retained['scenario']), copy.deepcopy(commanded['scenario'])
    sa['normal_set'].pop('skip_command'); sb['normal_set'].pop('skip_command')
    if sa != sb or wa != wb or ar['configuration'] != br['configuration']:
        raise ValueError('The pair differs beyond the ordinary input command')
    stop = wa[1]['stop_s']; start = wa[1]['start_s']
    t = np.unique(np.concatenate((a[:, 0], b[:, 0])))
    valid = (t >= max(a[0,0],b[0,0])) & (t <= min(a[-1,0],b[-1,0]))
    t = t[valid]
    avdd = np.interp(t,a[:,0],a[:,5]); bvdd = np.interp(t,b[:,0],b[:,5])
    gate_delta = np.interp(t,a[:,0],a[:,3])-np.interp(t,b[:,0],b[:,3])
    mask = (t >= start) & (t <= stop)
    return dict(dip_V=sa['recovery']['low_V'], corner=sa['corner'], max_supply_difference_V=float(np.max(abs(avdd-bvdd))),
                max_recovery_reset_difference_V=float(np.max(abs(gate_delta[mask]))),
                retained_prior_verified=ar['declared_precondition_verified'],
                commanded_prior_verified=br['declared_precondition_verified'],
                retained_alternate_exercised=ar['alternate_state_exercised'],
                commanded_alternate_exercised=br['alternate_state_exercised'],
                retained_observed_pass=ar['observed_pass'], commanded_observed_pass=br['observed_pass'],
                scope='Measured similarity of the reset waveform is not a threshold or state-write equivalence proof.')


def run_lab(retained, commanded):
    folder = HERE/'results/mechanism_runs'/('run_'+uuid.uuid4().hex[:10])
    folder.mkdir(parents=True, exist_ok=False)
    plan = prediction_plan()
    (folder/'predictions_before_spice.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print('Predictions written before either new acquisition:')
    for p in plan['predictions']:
        print('dip',p['dip_V'],'V -> predicted initial reset c',round(p['predicted_c_V'],6),'V')
    runs, outcomes = [], []
    for p in plan['predictions']:
        record = run_sequence(low_V=p['dip_V'], command=True, variants=[CONFIG],
                              output=folder/('dip_'+str(p['dip_V']).replace('.','p')))
        runs.append(record)
        if record['status'] == 'completed':
            outcomes.append(score_prediction(p,record,plan['node_tolerance_V']))
        else:
            outcomes.append(dict(**p,node_prediction_met=None,status='unresolved',record=record['output_dir']))
    summary = dict(status='completed' if all(r['status']=='completed' for r in runs) else 'has_unresolved',
                   plan=plan, outcomes=outcomes, paired_control=paired_control(retained,commanded),
                   output_dir=str(folder), evidence_kind='two fresh real-PDK acquisitions and a separate unloaded-RC prediction')
    (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def report_markdown(summary):
    lines = ['| Dip, V | Predicted c, V | Measured c, V | Error, mV | Node check | Recovery met |',
             '|---:|---:|---:|---:|---|---|']
    for r in summary['outcomes']:
        if r['node_prediction_met'] is None:
            lines.append(f"| {r['dip_V']} | {r['predicted_c_V']:.6f} | unavailable | unavailable | unresolved | unassessed |")
        else:
            lines.append(f"| {r['dip_V']} | {r['predicted_c_V']:.6f} | {r['measured_c_V']:.6f} | {r['signed_error_V']*1e3:.3f} | {r['node_prediction_met']} | {r['recovery_met']} |")
    pair = summary['paired_control']
    lines += ['', f"At the main {pair['dip_V']:g} V dip ({pair['corner']}), the retained/commanded pair has a maximum measured supply difference of "
              f"{pair['max_supply_difference_V']*1e3:.4f} mV and recovery-reset difference of "
              f"{pair['max_recovery_reset_difference_V']*1e3:.4f} mV.",
              'The ordinary command changes which stored state must be restored. A similar reset waveform can therefore accompany a retained-state pass and an exercised restoration miss.',
              '', 'The node check uses the predeclared 20 mV criterion. It does not predict latch switching or certify a reset threshold. Every result, including a failed prediction or unresolved acquisition, remains visible.']
    return '\n'.join(lines)


def figure(summary, retained, commanded):
    fig, axes = plt.subplots(1,2,figsize=(11,3.8),layout='constrained')
    for record,label,color in [(retained,'Desired state already present','#777777'),(commanded,'Other state normally written','#086d94')]:
        row,d,w = vectors(record); mask=(d[:,0]>=w[1]['start_s'])&(d[:,0]<=w[1]['ramp_end_s']+.001)
        ms=(d[mask,0]-w[1]['start_s'])*1e3
        axes[0].plot(ms,d[mask,2],label=label,color=color)
    axes[0].axhline(1.44,color='black',ls=':',label='Desired b >= 1.44 V')
    axes[0].set(xlabel='Time from recovery start, ms',ylabel='Latch b, V',title='Same circuit/history, different prior state')
    axes[0].legend(fontsize=8)
    good=[r for r in summary['outcomes'] if r['node_prediction_met'] is not None]
    for r in good:
        axes[1].plot(r['dip_V'],r['predicted_c_V'],'x',ms=9,color='#222222')
        axes[1].plot(r['dip_V'],r['measured_c_V'],'o',ms=7,mfc='none',color='#086d94')
    axes[1].plot([],[],'x',color='#222222',label='Unloaded RC prediction')
    axes[1].plot([],[],'o',mfc='none',color='#086d94',label='Real-PDK node measurement')
    axes[1].set(xlabel='Declared dip level, V',ylabel='Reset c at recovery start, V',title='Predict a node, then check it')
    axes[1].legend(fontsize=8)
    for ax in axes: ax.grid(alpha=.2)
    return fig
