"""Frozen representative selection, fixed-CPU integration and 100 MHz challenges."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from evaluate_study_physical import evaluate
from run_study_physical import run as physical
from study_protocol import BASELINE, digest, ranking, write_json

CASE = Path(__file__).resolve().parents[1]


def generation_representatives(analysis):
    if not analysis['complete'] or len(analysis['rows']) != 12:
        raise ValueError('Complete twelve-trial final evaluation is required')
    selected = []
    for entry in ('fresh', 'ip'):
        for roles in ('single', 'multi'):
            rows = [row for row in analysis['rows'] if row['job']['input'] == entry and
                    row['job']['roles'] == roles and row['passed']]
            winner = min(rows, key=lambda row: row['job']['repetition']) if rows else None
            selected.append({'cell': entry+'-'+roles, 'trial': winner['job']['id'] if winner else None})
    return selected


def prepare_representatives(experiment):
    analysis = json.loads((experiment/'generation/analysis.json').read_text())
    selection = generation_representatives(analysis)
    target = experiment/'representatives/selection.json'
    if target.exists():
        old = json.loads(target.read_text())
        if old['selected'] != selection or old['analysis_sha256'] != digest(experiment/'generation/analysis.json'):
            raise ValueError('Frozen representative selection changed')
        return old
    original = json.loads((CASE/'released_design/selected-delivery.json').read_text())
    records = []
    for choice in selection:
        if choice['trial'] is None:
            continue
        trial = experiment/'generation'/choice['trial']
        raw = json.loads((trial/'results/result.json').read_text())
        output = experiment/'representatives'/choice['cell']/'source'
        output.mkdir(parents=True, exist_ok=False)
        mapping = {}
        for name in ('rtl/cpu/rv32i_five_stage_cpu.sv', 'rtl/integration/nebula_cpu_npu_top.sv'):
            source = CASE/'released_design'/name
            if digest(source) != original['exported_source_sha256'][name]:
                raise ValueError('Fixed host CPU/top changed')
            destination = output/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            mapping[name] = {'from': 'common-cpu-top/'+name, 'sha256': digest(destination)}
        for name, expected in raw['final_checker']['source_sha256'].items():
            source = trial/'results/selected'/name
            if digest(source) != expected:
                raise ValueError('Frozen generated source changed')
            relative = Path(name)
            if relative.parts[0] not in ('rtl', 'ip') or '..' in relative.parts:
                raise ValueError('Unsafe generated source path')
            destination_name = relative if relative.parts[0] == 'rtl' else Path('rtl/vendor')/Path(*relative.parts[1:])
            destination = output/destination_name
            if destination.exists():
                raise ValueError('Generated source collides with the frozen CPU/top')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            mapping[str(destination_name)] = {'from': choice['trial']+'/'+name, 'sha256': expected}
        if raw['job']['input'] == 'ip':
            shutil.copy2(trial/'project/ip/LICENSE', output/'IP_LICENSE')
        delivery = {'id': 'fixed-cpu-integration-'+choice['trial'],
                    'exported_source_sha256': {name: item['sha256'] for name, item in mapping.items()},
                    'generation_source_delivery': raw['final_checker']['source_delivery'],
                    'common_cpu_source_delivery': original['id'], 'source_mapping': mapping,
                    'scope': 'Deterministic source-only integration; CPU/top and generated RTL bytes unchanged. IP source relocated under rtl/vendor for the physical loader.'}
        write_json(output/'selected-delivery.json', delivery)
        records.append(dict(choice, source=str(output.relative_to(experiment)), delivery=delivery['id']))
    record = {'selected': selection, 'integrations': records,
              'analysis_sha256': digest(experiment/'generation/analysis.json'),
              'policy': 'Lowest numbered functional pass per cell; one 100 ns, 40% physical attempt; no PPA-based replacement',
              'configuration': BASELINE, 'period_ps': 100000}
    write_json(target, record)
    return record


def representative_physical(experiment):
    selection = prepare_representatives(experiment)
    rows = []
    for item in selection['integrations']:
        run = experiment/'representatives'/item['cell']/'physical'
        if not run.exists():
            physical(run, experiment/item['source'], BASELINE, 100000)
        if not (run/'summary.json').exists():
            raise ValueError('Interrupted representative retained; inspect without replacing it')
        if not (run/'evaluation.json').exists():
            evaluate(run)
        rows.append(dict(item, evaluation=json.loads((run/'evaluation.json').read_text())))
    write_json(experiment/'representatives/summary.json', {'finished': True, 'selection': selection, 'rows': rows})


def high_frequency_selection(experiment):
    plan = json.loads((experiment/'protocol.json').read_text())
    choices = [{'name': 'common-baseline', 'configuration': BASELINE, 'source_candidate': 'common-baseline'}]
    absences = []
    for workflow in ('W0', 'W1', 'W2'):
        candidates = []
        for job in plan['ppa']['sessions']:
            if job['workflow'] != workflow:
                continue
            summary = json.loads((experiment/'ppa'/job['id']/'results/search-summary.json').read_text())
            if not summary['finished']:
                raise ValueError('PPA session not finished')
            candidates.extend(dict(row, session=job['id']) for row in summary['candidates'] if row['rank_eligible'])
        if not candidates:
            absences.append({'workflow': workflow, 'reason': 'No new qualified candidate'})
            continue
        winner = min(candidates, key=ranking)
        choices.append({'name': workflow, 'configuration': winner['configuration'],
                        'source_candidate': winner['session']+'/'+str(winner['candidate_index']),
                        'selected_95mhz_score': winner['score']})
    return {'choices': choices, 'absences': absences, 'period_ps': 10000,
            'policy': 'Best new qualified Q per workflow, frozen session order for exact cross-session ties; one 100 MHz attempt, no retuning'}


def high_frequency(experiment):
    selection = high_frequency_selection(experiment)
    target = experiment/'high-frequency/selection.json'
    if target.exists() and json.loads(target.read_text()) != selection:
        raise ValueError('Frozen high-frequency representative changed')
    write_json(target, selection)
    rows = []
    for item in selection['choices']:
        run = experiment/'high-frequency'/item['name']/'physical'
        if not run.exists():
            physical(run, CASE/'released_design', item['configuration'], 10000)
        if not (run/'summary.json').exists():
            raise ValueError('Interrupted high-frequency attempt retained; no rescue runs')
        if not (run/'evaluation.json').exists():
            evaluate(run)
        rows.append(dict(item, evaluation=json.loads((run/'evaluation.json').read_text())))
    write_json(experiment/'high-frequency/summary.json', {'finished': True, 'selection': selection, 'rows': rows,
        'scope': '100 MHz engineering qualification only; scores normalized to each challenge itself are not 95 MHz search scores'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True)
    parser.add_argument('--stage', choices=('prepare', 'representatives', 'high-frequency'), required=True)
    args = parser.parse_args()
    {'prepare': prepare_representatives, 'representatives': representative_physical,
     'high-frequency': high_frequency}[args.stage](args.experiment.resolve())
