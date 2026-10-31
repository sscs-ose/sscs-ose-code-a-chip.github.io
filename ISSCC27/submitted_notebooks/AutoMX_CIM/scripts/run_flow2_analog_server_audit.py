#!/usr/bin/env python3
"""Revalidate existing analog evidence; optionally run two bounded corner probes.

The optional native jobs are conditioner PEX zero-input tests at SS/FF, 25 C,
1.8 V, with driven held inputs and the original 2-pF loads. No ADC conversion,
physical extraction, archive export, or qualification status is changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_adc_finish as finish
from scripts import run_flow2_adc_operating_point as operating
from scripts import run_flow2_conditioner as conditioner
from scripts import flow2_live_spice as live

common = finish.common
CONDITION = 'mixed_wrapper_20261020_01_cond'
SOURCE = 'readout_progress_20261018_04'
CONTINUOUS = 'adc_continuous_20261019_08'


def proof(root, path):
    return {'path': str(Path(path).relative_to(root)), 'sha256': common._sha(path)}


def read_evidence(root):
    points, sources = operating.operating_points(root, CONDITION)
    block_path = root/common.BASE/CONDITION/'summary.json'
    block = json.loads(block_path.read_text())
    for item in block['views'].values():
        common._verified(root, item)
    measurements = []
    for job in block['electrical']['jobs']:
        raw = common._verified(root, job['raw'])
        measurements.append({'variant': job['variant'], 'column': job['selected_column'],
                             'raw': job['raw'], **conditioner.analyze_point(raw)})
    previous, net, model, pins, probes, source = finish.verify_source(
        root, SOURCE, check_fanout=False)
    binary = previous['branches']['adc']['runtime']['binary_sha256']
    loads = finish.verified_loads(root, 'adc_finish_20261018_06', model=model,
        net=net, pins=pins, probes=probes, binary_sha=binary,
        source_sha=source['source_summary_sha256'])
    continuous_path = root/common.BASE/CONTINUOUS/'summary.json'
    continuous = json.loads(continuous_path.read_text())
    conversions = []
    for job in continuous['jobs']:
        if job['task'] != 'conversion':
            continue
        session = job['native_session']
        item = session['observed_segments'][-1]
        raw = common._verified(root, item)
        receipt_path = raw.parent/'receipt.json'
        if json.loads(receipt_path.read_text()) != session:
            raise ValueError('conversion receipt differs from summary')
        common._verified(root, session['log'])
        vectors = finish.waves.read_raw(raw)
        t = vectors['time']
        edges = {}
        for name in ('eoc', 'eoc_osr', 'adc_clk_dig', 'adc_clk_comp'):
            a = vectors[f'v({name})']
            rises = np.flatnonzero((a[:-1] < .9) & (a[1:] >= .9) & (t[1:] > 22e-9))+1
            edges[name] = {'count': len(rises), 'first_s': float(t[rises[0]]) if len(rises) else None}
        result = {'case': job['case'], 'raw': item, 'receipt': proof(root, receipt_path),
                  'returncode': session['returncode'], 'samples': len(t),
                  'last_s': float(t[-1]), 'edges_after_22ns': edges}
        try:
            result['acceptance'] = finish.profile.analyze(vectors, {}, task='conversion',
                cm=.9, diff=-.1 if job['case'].endswith('negative') else .1)
        except ValueError as error:
            result['acceptance_error'] = str(error)
        conversions.append(result)
    core = []
    for job in previous['branches']['core']['jobs']:
        vectors = finish.waves.read_raw(common._verified(root, job['waveform']))
        stage = finish.core.analyze_waveform(vectors)
        core.append({k: job[k] for k in ('case', 'variant', 'maximum_capture_error_v',
                                         'capture_budget_met', 'waveform')})
        core[-1]['stage_diagnostic_reanalyzed'] = stage
    cap_path = root/'results/sky130/flow2_periphery_leaf/hold_cap_charge_tt_20261017_02/hold_cap_charge_tt_recovery.json'
    cap = json.loads(cap_path.read_text())
    return {'status': 'EXISTING_RAW_REVALIDATED_QUALIFICATION_PENDING',
        'conditioner': {'source': proof(root, block_path), 'proofs': sources,
                        'measurements': measurements, 'adc_operating_points': points},
        'adc_source': source,
        'adc_loads': {k: {'analysis': v['analysis'], 'reuse': v['reuse']} for k, v in loads.items()},
        'adc_conversions': {'source': proof(root, continuous_path), 'jobs': conversions},
        'core_acquisition': core,
        'hold_cap_diagnostic': {'source': proof(root, cap_path), **{k: cap[k] for k in (
            'pex_effective_capacitance_ff', 'schematic_effective_capacitance_ff',
            'substrate_reference_ohms', 'not_signoff')}},
        'scope': 'no native physical re-audit; reused measured core-bound physical status is scoped separately'}


def native_probes(root, tag, timeout_s):
    common.tag_ok(tag)
    work = root/common.BUILD/tag
    work.mkdir(parents=True, exist_ok=False)
    base = root/common.BUILD/CONDITION/'tt_pex_1'
    original = (base/'bench.spice').read_text()
    saved = json.loads((base/'receipt.json').read_text())
    if common._sha(base/'bench.spice') != saved['inputs']['deck']:
        raise ValueError('TT zero-point deck changed')
    tool = shutil.which('ngspice')
    if tool is None or common._sha(Path(tool)) != saved['inputs']['tool_binary']:
        raise ValueError('same measured conditioner binary required')
    version = subprocess.run([tool, '--version'], capture_output=True, text=True,
                             timeout=10, check=True).stdout.strip()
    model_line = next(s for s in original.splitlines() if s.startswith('.lib '))
    model = Path(model_line.split('"')[1])
    if common._sha(model) != saved['inputs']['model']:
        raise ValueError('conditioner model changed')
    report = {'status': 'STARTED', 'tag': tag, 'maximum_native_jobs': 2,
        'timeout_per_case_s': timeout_s, 'tool': {'path': tool, 'sha256': common._sha(Path(tool)),
        'version': version}, 'library': {'path': str(model), 'sha256': common._sha(model)},
        'original_tt_deck': proof(root, base/'bench.spice'), 'cases': [],
        'scope': 'SS/FF process only, 25 C and 1.8 V, column 1 zero differential; '
                 'driven held inputs and 2-pF loads; no coupled readout or ADC/reference/noise qualification'}
    try:
        for corner in ('ss', 'ff'):
            case = work/f'{corner}_pex_zero'
            case.mkdir()
            text = original.replace(model_line, model_line[:-2]+corner, 1)
            deck = case/'bench.spice'
            deck.write_text(text)
            inputs = {'deck': proof(root, deck), 'network_sha256': saved['inputs']['network'],
                      'model_sha256': common._sha(model), 'tool_sha256': common._sha(Path(tool)),
                      'corner': corner, 'temperature_c': 25, 'supply_v': 1.8,
                      'input_cm_v': 1.7, 'input_diff_v': 0., 'load_per_input_pf': 2.}
            (case/'inputs.json').write_text(json.dumps(inputs, indent=2)+'\n')
            begun = time.monotonic()
            result = live.run([tool, '-b', 'bench.spice'], case, timeout_s,
                              poll_s=.5, heartbeat_s=30.)
            item = {'inputs': inputs, 'returncode': result.returncode,
                    'wall_s': time.monotonic()-begun, 'log': proof(root, case/'ngspice.live.log'),
                    'status': 'INCOMPLETE_NATIVE_PROBE'}
            raw = case/'conditioner.raw'
            if raw.is_file():
                item['raw'] = proof(root, raw)
            if result.returncode == 0 and raw.is_file():
                try:
                    item['analysis'] = conditioner.analyze_point(raw)
                    item['status'] = 'MEASURED_PROCESS_CORNER_ZERO_POINT'
                except ValueError as error:
                    item['acceptance_error'] = str(error)
            (case/'receipt.json').write_text(json.dumps(item, indent=2)+'\n')
            report['cases'].append(item)
            print(corner, item['status'], flush=True)
            # An unresolved parser/model/time-budget problem merits inspection,
            # not spending the second native job automatically.
            if item['status'] != 'MEASURED_PROCESS_CORNER_ZERO_POINT':
                break
        report['status'] = ('TWO_PROCESS_CORNER_ZERO_POINTS_MEASURED' if len(report['cases']) == 2
            and all(c['status'] == 'MEASURED_PROCESS_CORNER_ZERO_POINT' for c in report['cases'])
            else 'PENDING_NATIVE_PROBE_EVIDENCE')
    finally:
        (work/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--run', action='store_true')
    p.add_argument('--tag', default='analog_server_audit_20261021')
    p.add_argument('--timeout-s', type=int, default=240)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if not 1 <= a.timeout_s <= 240:
        p.error('native budget must be between 1 and 240 seconds per case')
    root = a.root.resolve()
    report = {'format': 'automx-cim-analog-server-audit-v1',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'script': proof(root, Path(__file__)), 'evidence': read_evidence(root),
              'qualification': 'PENDING', 'new_ADC_conversions': 0}
    if a.run:
        report['native_conditioner_probes'] = native_probes(root, a.tag, a.timeout_s)
    if a.output:
        a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['evidence']['status'],
        'native': report.get('native_conditioner_probes', {}).get('status', 'NOT_REQUESTED'),
        'qualification': report['qualification'], 'output': str(a.output) if a.output else None}))


if __name__ == '__main__':
    main()
