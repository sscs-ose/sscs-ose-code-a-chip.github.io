"""Explicit-budget entrypoints for a fresh task/workflow study; preview is the default."""
from __future__ import annotations

import argparse
import datetime
import json
import time
import traceback
from pathlib import Path

from benchmark_physical import run as benchmark_physical
from campaign_budget import finish,reserve
from evaluate_study_physical import evaluate
from freeze_benchmark_study import freeze
from qualify_benchmark import qualify
from qualify_benchmark_actions import qualify as qualify_actions
from run_benchmark_generation import run as generate
from run_benchmark_ppa import run_session
from run_study_physical import run as physical
from study_protocol import ranking,write_json
from summarize_benchmark_study import summarize

CASE=Path(__file__).resolve().parents[1]


def common(campaign,output,source,configuration,period,identity,category):
    if output.exists():raise ValueError('Previous attempt is retained: '+str(output))
    reserve(campaign,category,identity,output);started=time.monotonic()
    try:
        physical(output,source,configuration,period)
        row=evaluate(output)
        row['rtl_actions']=json.loads((source/'selected-delivery.json').read_text()).get(
            'rtl_actions',dict(operand_isolation=False,reduce_width=False))
    except Exception as error:
        output.mkdir(exist_ok=True)
        (output/'campaign-error.log').write_text(traceback.format_exc())
        row=dict(rank_eligible=False,error_class=type(error).__name__,error=str(error),
                 total_seconds=time.monotonic()-started)
    write_json(output/'campaign-evaluation.json',row)
    finish(campaign,identity,status='qualified' if row['rank_eligible'] else 'failed',
           evidence=str((output/'campaign-evaluation.json').relative_to(campaign)))
    return row


def run(campaign,phase,execute=False):
    campaign=Path(campaign).resolve()
    protocol=json.loads((campaign/'protocol.json').read_text())
    ledger=json.loads((campaign/'launch-ledger.json').read_text())
    preview=dict(phase=phase,execute=execute,limits=ledger['limits'],allocated=len(ledger['launches']),
        model='gpt-6.1-sol / high',
        budget='Three frontend trials: 1200 aggregate role seconds each; nine PPA sessions: 1200 role seconds and <=3 candidates each. Physical <=4 h plus <=30 min postprocessing per accepted attempt.',
        scope='This starts new paid model/EDA work only with --execute. Failed attempts are not reset or replaced.')
    print(json.dumps(preview,indent=2),flush=True)
    if not execute:return preview
    baseline=campaign/'baseline/common/campaign-evaluation.json'
    if phase=='actions':
        qualify_actions(campaign/'checks/rtl-actions')
    elif phase=='references':
        for entry in protocol['tasks']:
            task=campaign/'benchmark/tasks'/entry['id']
            if not (task/'qualification/qualification.json').exists():qualify(task,task/'qualification')
            if (task/'calibration.json').exists():continue
            output=campaign/'benchmark'/('reference-'+entry['id'])
            if output.exists():raise ValueError('Reference attempt failed previously; inspect evidence and calibration cap, no automatic replacement')
            benchmark_physical(campaign,task,task/'grader/reference',output,category='reference',identity='reference-'+entry['id'])
    elif phase=='baseline':
        if baseline.exists():raise ValueError('Common baseline already has a terminal record')
        common(campaign,baseline.parent,CASE/'released_design',protocol['ppa']['baseline_configuration'],
               10526,'common-95mhz','common_baseline')
    elif phase=='demonstrations':
        for label in protocol['demonstrations']:
            record=campaign/'benchmark/demonstrations'/label/'results/result.json'
            row=json.loads(record.read_text()) if record.exists() else generate(campaign,campaign/'benchmark/tasks'/label)
            output=record.parent.parent/'physical'
            if row['functional_qualified'] and not output.exists():
                benchmark_physical(campaign,campaign/'benchmark/tasks'/label,record.parent/'selected/rtl',
                                   output,category='demonstration',identity='demo-'+label)
    elif phase=='freeze':
        freeze(campaign,baseline)
    elif phase=='ppa':
        if not (campaign/'ppa/formal-freeze.json').exists():raise ValueError('Freeze qualified sources and baseline before scored sessions')
        for job in protocol['ppa_jobs']:
            root=campaign/'ppa'/job['id']
            if (root/'results/search-summary.json').exists():continue
            if root.exists():raise ValueError('Interrupted scored session is retained; no reset or replacement')
            run_session(campaign,baseline,job)
    elif phase=='high-frequency':
        data=summarize(campaign)
        if not data['ppa_complete']:raise ValueError('Representative selection requires all nine terminal sessions')
        entries=[dict(identity='high-frequency-common',source='public-released-design',
                      configuration=protocol['ppa']['baseline_configuration'])]
        for flow in ('F0','F1','F2'):
            candidates=[(c,r['job']['id']) for r in data['rows'] if r['job']['workflow']==flow
                        for c in r['candidates'] if c['rank_eligible']]
            if not candidates:continue
            candidate,session=min(candidates,key=lambda item:(*ranking(item[0]),item[1]))
            source=Path('ppa')/session/'candidates'/f'{candidate["candidate_index"]:02d}'/'source'
            entries.append(dict(identity='high-frequency-'+flow,source=str(source),
                configuration=candidate['configuration'],selected_session=session,candidate_index=candidate['candidate_index']))
        selected=dict(rule='lowest unrounded Q, energy, area, candidate index, session id; absent without new qualified candidate',entries=entries)
        path=campaign/'high-frequency/selection.json'
        if path.exists() and json.loads(path.read_text())!=selected:raise ValueError('Frozen representative selection differs')
        write_json(path,selected)
        for entry in entries:
            output=campaign/'high-frequency'/entry['identity']
            if (output/'campaign-evaluation.json').exists():continue
            source=CASE/'released_design' if entry['source']=='public-released-design' else campaign/entry['source']
            common(campaign,output,source,entry['configuration'],10000,entry['identity'],'high_frequency')
    elif phase=='report':
        summarize(campaign)
    return dict(phase=phase,finished=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--phase',choices=['actions','references','baseline','demonstrations','freeze','ppa','high-frequency','report'],required=True)
    parser.add_argument('--execute',action='store_true',help='Start this phase using the displayed frozen budget; otherwise only show the budget')
    args=parser.parse_args();run(args.campaign,args.phase,args.execute)
