"""Recompute all twelve outcomes without replacing original measurements."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from audit_study_ip import rescore_trial
from study_protocol import digest,write_json


def summarize(experiment):
    experiment=Path(experiment).resolve()
    jobs=json.loads((experiment/'protocol.json').read_text())['generation']['jobs']
    if len(jobs)!=12 or len({job['id'] for job in jobs})!=12:
        raise ValueError('Expected the complete preregistered twelve-trial population')
    rows=[]
    for job in jobs:
        folder=experiment/'generation'/job['id'];source=folder/'results/result.json'
        if not source.is_file():raise ValueError('Scheduled trial is incomplete: '+job['id'])
        original=json.loads(source.read_text())
        revised=folder/'results/final-evaluator-v3.json'
        if not revised.exists():rescore_trial(folder)
        correction=json.loads(revised.read_text())
        if correction['original_result_sha256']!=digest(source):raise ValueError('Original trial record changed')
        usage=json.loads((folder/'results/usage.json').read_text())
        sessions=usage['sessions']
        contexts_match=bool(sessions) and all(s['model']=='gpt-6.1-sol' and s['reasoning_effort']=='high' for s in sessions)
        role_sessions={role:sorted({attempt['session_id'] for attempt in original['attempts']
            if attempt['role']==role and attempt['session_id']}) for role in ('study-designer','study-verifier')}
        identified=set().union(*(set(items) for items in role_sessions.values()))
        unassigned=sorted({session['session_id'] for session in sessions}-identified)
        independent=bool(role_sessions['study-designer']) and (job['roles']=='single' or
            bool(role_sessions['study-verifier']) and not set(role_sessions['study-designer'])&set(role_sessions['study-verifier']))
        row=dict(original,passed=correction['passed'],original_verdict=original['passed'],
                 corrected_evaluation=str(revised.relative_to(experiment)),model_contexts_match=contexts_match,
                 final_evaluator_version=3,role_sessions=role_sessions,
                 independent_role_contexts=independent,unassigned_model_sessions=unassigned)
        rows.append(row)
    cells=[]
    for entry in ('fresh','ip'):
        for roles in ('single','multi'):
            selected=[row for row in rows if row['job']['input']==entry and row['job']['roles']==roles]
            if len(selected)!=3:raise ValueError('Missing experimental cell')
            measured=[row for row in selected if row.get('tokens') is not None]
            cells.append({'input':entry,'roles':roles,'planned':3,'completed':len(selected),
                'passed':sum(row['passed'] for row in selected),
                'workflow_complete':sum(row['workflow_state']=='complete' for row in selected),
                'timeouts':sum(row['timed_out'] for row in selected),
                'median_engineering_seconds':statistics.median(row['engineering_seconds'] for row in selected),
                'measured_token_trials':len(measured),
                'median_uncached_input_tokens':statistics.median(row['tokens']['input_tokens']-row['tokens']['cached_input_tokens'] for row in measured) if measured else None,
                'median_output_tokens':statistics.median(row['tokens']['output_tokens'] for row in measured) if measured else None,
                'trusted_checker_repairs':sum(row['repair_iterations'] for row in selected),
                'manual_design_interventions':sum(row['manual_design_interventions'] for row in selected)})
    summary={'complete':True,'planned':12,'passed':sum(row['passed'] for row in rows),
             'protocol_model_contexts_match':all(row['model_contexts_match'] for row in rows),
             'independent_role_contexts_observed':all(row['independent_role_contexts'] for row in rows),
             'unassigned_model_sessions':sum(len(row['unassigned_model_sessions']) for row in rows),
             'rows':rows,'cells':cells,
             'correction':{'version':3,'original_results_preserved':True,'agent_inputs_or_feedback_changed':False,
                 'reason':'The original IP counter inspected a flattened synthesis netlist. The frozen four-original-PE criterion is measured using preserved hierarchy and actual result-data cones. All trial snapshots use the same corrected rule.'},
             'scope':'Small dot4 generation/integration task; three repeats per cell support descriptive comparisons, not general CPU/GDS success rates',
             'repair_definition':'Recorded public-check failure followed by changed RTL and another trusted public check; unchanged-source rechecks are separate'}
    write_json(experiment/'generation/analysis.json',summary)
    print(json.dumps({'complete':True,'passed':summary['passed'],'cells':cells},indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--experiment',type=Path,required=True)
    summarize(p.parse_args().experiment)
