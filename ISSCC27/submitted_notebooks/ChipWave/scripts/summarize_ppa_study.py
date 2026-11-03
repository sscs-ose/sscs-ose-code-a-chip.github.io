"""Account for every scheduled PPA session, including failures and unused slots."""
from __future__ import annotations

import argparse
import json
import statistics
import datetime
import math
from pathlib import Path

from study_protocol import digest, ranking, write_json


def infrastructure_costs(results):
    path=results/'infrastructure-failures/summary.json'
    record=json.loads(path.read_text()) if path.exists() else {'records':[]}
    seconds={}
    for row in record['records']:
        elapsed=row.get('interruption_wall_seconds')
        if elapsed is None:continue
        if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:
            raise ValueError('Invalid infrastructure interruption duration')
        seconds[row['original_job']]=seconds.get(row['original_job'],0)+elapsed
    return record,seconds


def context_audit(usage,workflow):
    sessions=usage.get('sessions',[])
    names=[session.get('session_id') for session in sessions]
    if workflow=='W0':
        totals=usage.get('totals')
        return {'passed':not sessions and (totals is None or all(type(v) is int and v==0 for v in totals.values())),
                'observed_model_sessions':len(sessions),'expected':'No model dispatches or model Tokens'}
    valid=bool(sessions) and len(names)==len(set(names)) and all(names)
    for session in sessions:
        tokens=session.get('tokens',{})
        keys=('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens')
        valid=valid and session.get('model')=='gpt-6.1-sol' and session.get('reasoning_effort')=='high'
        valid=valid and all(type(tokens.get(key)) is int and tokens[key]>=0 for key in keys)
        if valid:
            valid=tokens['cached_input_tokens']<=tokens['input_tokens'] and tokens['reasoning_output_tokens']<=tokens['output_tokens']
    if valid:
        valid=usage.get('totals')=={key:sum(s['tokens'][key] for s in sessions) for key in keys}
    return {'passed':bool(valid),'observed_model_sessions':len(sessions),
            'expected':'Requested gpt-6.1-sol/high; unique local sessions; valid cached/output subcounts and exact cumulative sums'}


def session_row(summary):
    candidates = sorted(summary['candidates'], key=lambda row:row['candidate_index'])
    qualified = [row for row in candidates if row['rank_eligible']]
    improved = [row for row in qualified if row['score'] < 1]
    best = min(qualified, key=ranking) if qualified else None
    budget = summary['budget']
    tokens = summary.get('usage',{}).get('tokens')
    return {'id':summary['job']['id'], 'workflow':summary['job']['workflow'],
        'workflow_state':summary.get('workflow_state','not recorded'), 'finished':summary['finished'],
        'physical_launches':summary['physical_launches'], 'evaluated':len(candidates),
        'incomplete_launches':sum(slot['status']=='launched_incomplete' for slot in summary['slots']),
        'qualified':len(qualified), 'unused_slots':summary['unused_candidate_slots'],
        'slots':summary['slots'], 'agent_seconds':budget['used_agent_seconds'],
        'reviewer_seconds':sum(row['elapsed_seconds'] for row in budget['dispatches'] if row['role']=='ppa-verifier'),
        'proposer_seconds':sum(row['elapsed_seconds'] for row in budget['dispatches'] if row['role']=='ppa-proposer'),
        'review_dispatches':sum(row['role']=='ppa-verifier' for row in budget['dispatches']),
        'proposal_dispatches':sum(row['role']=='ppa-proposer' for row in budget['dispatches']),
        'physical_seconds':sum(row['physical_wall_seconds'] for row in candidates),
        'postprocess_seconds':sum(row['postprocess_wall_seconds'] for row in candidates),
        'observed_wall_seconds':max((row['elapsed_search_seconds'] for row in candidates), default=0),
        'tokens':tokens, 'model_sessions':summary.get('usage',{}).get('model_sessions'),
        'best_new_score':None if best is None else best['score'],
        'best_incumbent_score':min(1,best['score']) if best else 1.,
        'best_new_candidate':None if best is None else best['candidate_index'],
        'first_new_qualified_seconds':qualified[0]['elapsed_search_seconds'] if qualified else None,
        'first_strict_improvement_seconds':improved[0]['elapsed_search_seconds'] if improved else None,
        'candidates':candidates}


def service_notes(results, summary):
    notes={'unreported_transport_requests':0,'transport_failure_agent_seconds':0.,
           'candidate_environment_failures':[],'service_event_records':[]}
    dispatches={row['attempt']:row['elapsed_seconds'] for row in summary['budget']['dispatches'] if 'attempt' in row}
    seen=set();seen_candidates=set();job=summary['job']['id']
    for pattern in ('model-transport-*.json','candidate-physical-*.json'):
        for path in sorted((results/'infrastructure-failures').glob(pattern)):
            event=json.loads(path.read_text())
            if event['job']!=job:continue
            if event['type']=='post-response-model-transport-failure':
                elapsed=0.
                for attempt in event['failed_role_attempts']:
                    identity=attempt['attempt'];seconds=attempt['role_seconds']
                    if (identity in seen or identity not in dispatches or type(seconds) not in (int,float)
                            or not math.isfinite(seconds) or seconds<0
                            or not math.isclose(seconds,dispatches[identity],abs_tol=1e-9)
                            or attempt['reported_usage_available'] is not False):
                        raise ValueError('Transport cost does not match unique recorded role dispatches')
                    seen.add(identity);elapsed+=seconds
                if (event['already_included_in_session_agent_and_wall_seconds'] is not True
                        or not math.isclose(elapsed,event['failed_role_seconds'],abs_tol=1e-9)):
                    raise ValueError('Invalid or double-added transport interruption cost')
                notes['unreported_transport_requests']+=len(event['failed_role_attempts'])
                notes['transport_failure_agent_seconds']+=elapsed
            elif event['type']=='physical-stage-environment-failure':
                index=event['candidate_index']
                if type(index) is not int or not 1<=index<=3 or index in seen_candidates:
                    raise ValueError('Invalid interrupted candidate index')
                evaluation=results/'ppa'/job/'candidates'/f'{index:02d}'/'evaluation.json'
                candidate=next((row for row in summary['candidates'] if row['candidate_index']==index),None)
                if (digest(evaluation)!=event['evaluation_sha256'] or candidate!=json.loads(evaluation.read_text())
                        or candidate['rank_eligible'] or candidate.get('energy_j')
                        or candidate.get('cell_area_um2') is not None
                        or event['already_included_in_session_wall_seconds'] is not True):
                    raise ValueError('Environment failure does not match an unqualified candidate')
                physical=evaluation.parent/'physical/summary.json'
                if physical.exists() and digest(physical)!=event['physical_summary_sha256']:
                    raise ValueError('Physical environment failure summary changed')
                seen_candidates.add(index)
                notes['candidate_environment_failures'].append({'candidate_index':index,
                    'failed_tool':event['failed_tool'],'record':str(path.relative_to(results))})
            else:raise ValueError('Unrecognized service interruption type')
            notes['service_event_records'].append(str(path.relative_to(results)))
    return notes


def summarize(results, require_complete=True):
    plan=json.loads((results/'protocol.json').read_text())
    baseline=json.loads((results/'baseline/mhz95-run03/evaluation-v4.json').read_text())
    infrastructure,startup_seconds=infrastructure_costs(results)
    execution_interruptions={}
    for path in sorted((results/'infrastructure-failures').glob('physical-*.json')):
        event=json.loads(path.read_text())
        if (event.get('type') not in ('post-response-physical-preflight-failure','physical-workflow-timeout') or event['job'] in execution_interruptions
                or event['job'] not in {job['id'] for job in plan['ppa']['sessions']}):
            raise ValueError('Invalid or duplicate physical workflow interruption')
        execution_interruptions[event['job']]=(path,event)
    if not baseline['rank_eligible']:
        raise ValueError('Unqualified normalization baseline')
    rows=[];pending=[];in_progress=[]
    for job in plan['ppa']['sessions']:
        path=results/'ppa'/job['id']/'results/search-summary.json'
        if not path.exists():
            pending.append(job['id'])
            launches=list((results/'ppa'/job['id']/'candidates').glob('*/launch.json'))
            evaluations=list((results/'ppa'/job['id']/'candidates').glob('*/evaluation.json'))
            if launches or (results/'ppa'/job['id']/'session.json').exists():
                in_progress.append({'id':job['id'],'physical_launches':len(launches),
                                    'completed_evaluations':len(evaluations)})
            continue
        summary=json.loads(path.read_text())
        if summary['job'] != job:
            raise ValueError('PPA job differs from frozen schedule')
        row=session_row(summary)
        row.update(service_notes(results,summary))
        row['execution_interruption']=None
        if job['id'] in execution_interruptions:
            event_path,event=execution_interruptions[job['id']]
            if digest(path)!=event['terminal_summary_sha256'] or not row['incomplete_launches']:
                raise ValueError('Physical workflow interruption does not match its terminal record')
            row['execution_interruption']={'record':str(event_path.relative_to(results)),
                'type':event['type'],'failed_tool':event['failed_tool'],
                'native_eda_workflow_started':event['native_eda_workflow_started']}
        if row['incomplete_launches'] and not row['execution_interruption']:
            raise ValueError('Incomplete terminal physical slot needs an explicit interruption record')
        metadata=json.loads((path.parents[1]/'session.json').read_text())
        usage_path=path.parent/'usage.json'
        usage=json.loads(usage_path.read_text()) if usage_path.exists() else {}
        row['model_context_audit']=context_audit(usage,job['workflow'])
        if job['workflow']=='W0':
            row['model_context_audit']['passed'] &= not summary['budget']['dispatches'] and row['agent_seconds']==0 and bool(
                row['tokens'] is not None and all(type(v) is int and v==0 for v in row['tokens'].values()))
        else:
            row['model_context_audit']['passed'] &= usage.get('totals')==row['tokens'] and len(usage.get('sessions',[]))==row['model_sessions']
        row['source_bindings_sha256']=metadata.get('source_bindings_sha256')
        legacy=path.parents[1]/'executed-source-binding.json'
        if row['source_bindings_sha256'] is None and legacy.exists():
            row['source_bindings_sha256']=json.loads(legacy.read_text())['bindings_sha256']
        started=datetime.datetime.fromisoformat(metadata['started_at']).timestamp()
        endpoint_path=path.parent/'end-time.json'
        if not endpoint_path.exists():
            write_json(endpoint_path,{'summary_sha256':digest(path),'final_write_epoch':path.stat().st_mtime,
                'scope':'Original protected final-summary write time, captured before evidence export'})
        endpoint=json.loads(endpoint_path.read_text())
        ended=endpoint['final_write_epoch']
        if (endpoint['summary_sha256']!=digest(path) or type(ended) not in (int,float)
                or not math.isfinite(ended) or ended<started):
            raise ValueError('Invalid source-bound search endpoint')
        row['total_wall_seconds']=ended-started
        row['infrastructure_startup_seconds']=startup_seconds.get(job['id'],0)
        row['total_wall_seconds_including_startup']=row['total_wall_seconds']+row['infrastructure_startup_seconds']
        for field in ('first_new_qualified_seconds','first_strict_improvement_seconds'):
            row[field+'_including_startup']=None if row[field] is None else row[field]+row['infrastructure_startup_seconds']
        row['time_endpoint']='Protected final summary write, preserved in source-bound end-time.json across export/extraction'
        if row['physical_launches']>3 or row['physical_launches']+row['unused_slots']!=3:
            raise ValueError('Candidate slot accounting mismatch')
        rows.append(row)
    if pending and require_complete:
        raise ValueError('PPA sessions not finished: '+', '.join(pending))
    groups=[]
    for workflow in ('W0','W1','W2'):
        group=[row for row in rows if row['workflow']==workflow]
        groups.append({'workflow':workflow,'sessions':len(group),'planned_sessions':1 if workflow=='W0' else 3,
            'physical_launches':sum(row['physical_launches'] for row in group),
            'qualified':sum(row['qualified'] for row in group),
            'infrastructure_aborted_sessions':sum(bool(row['execution_interruption']) for row in group),
            'median_best_incumbent_score':statistics.median(row['best_incumbent_score'] for row in group) if group else None,
            'median_agent_seconds':statistics.median(row['agent_seconds'] for row in group) if group else None,
            'median_reviewer_seconds':statistics.median(row['reviewer_seconds'] for row in group) if group else None,
            'strictly_improving_sessions':sum(row['best_incumbent_score']<1 for row in group)})
    revisions=[]
    for path in sorted((results/'baseline/mhz95-run03').glob('evaluation*.json')):
        if path.name!='evaluation-v4.json':
            data=json.loads(path.read_text());revisions.append({'record':path.name,
                'postprocess_seconds':data['postprocess_wall_seconds'],'rank_eligible':data['rank_eligible']})
    output={'complete':not pending,'planned_sessions':7,'sessions_completed':len(rows),'pending_sessions':pending,
        'infrastructure_aborted_sessions':sum(bool(row['execution_interruption']) for row in rows),
        'normally_finished_sessions':sum(not row['execution_interruption'] for row in rows),
        'incomplete_physical_launches':sum(row['incomplete_launches'] for row in rows),
        'unreported_transport_requests':sum(row['unreported_transport_requests'] for row in rows),
        'unreported_transport_unit':'Failed role/client invocations; internal HTTP retries are not separate model turns',
        'transport_failure_agent_seconds':sum(row['transport_failure_agent_seconds'] for row in rows),
        'baseline':baseline,'baseline_shared_seconds':baseline['total_wall_seconds'],
        'measurement_preflight_revisions':revisions,
        'measurement_preflight_seconds':sum(row['postprocess_seconds'] for row in revisions),
        'infrastructure_startup_failures':infrastructure,
        'infrastructure_interruption_seconds':sum(startup_seconds.values()),
        'completed_search_wall_seconds':sum(row['total_wall_seconds'] for row in rows),
        'rows':rows,'groups':groups,'in_progress':in_progress,
        'new_physical_launches':sum(row['physical_launches'] for row in rows)+sum(row['physical_launches'] for row in in_progress),
        'qualified_new_candidates':sum(row['qualified'] for row in rows),
        'scope':'One fixed CPU/NPU, one PDK corner, three bounded AI sessions per workflow; descriptive comparisons only',
        'time_scope':'Agent wall time includes role/model/tool interaction. Physical and measurement waits are outside the shared AI budget. Session total ends at the protected final summary write; first-qualified and first-improved times end at candidate evaluation. Raw productive-search clocks and clocks including recorded startup interruptions are both available. Interruption time already includes its failed retries and connectivity probes; do not add them again. Add the separately reported common baseline cost for a from-scratch budget.'}
    write_json(results/'ppa/analysis.json',output)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--allow-incomplete',action='store_true');args=parser.parse_args()
    data=summarize(args.results.resolve(),not args.allow_incomplete)
    print(json.dumps({key:data[key] for key in ('complete','sessions_completed','pending_sessions','new_physical_launches')},indent=2))
