"""Evaluator-side grading of a source-bound snapshot; never called as an agent tool."""
from __future__ import annotations

import json
import shutil
import argparse
from pathlib import Path

from build_capacity_dot_integration import qualify as qualify_integration
from capacity_backends import Backends
from capacity_integration_physical import ROOT, verified_integration
from capacity_meter import TokenLedger
from capacity_physical_evidence import audit, checked_path
from capacity_protocol import GDS_GATES, CONSTRAINT_GATES, score
from capacity_toolbox import source_hashes
from qualify_capacity_tasks import simulate
from study_protocol import digest, write_json


def function(snapshot, task, output, *, task_package=None, deadline=None):
    """Final functional checks, generic synthesis and nine frozen CPU integrations."""
    snapshot,output=Path(snapshot),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    row=dict(function=False,integration=False,synthesis=False,evaluation_valid=True,checks=[],errors=[],
             source_sha256=source_hashes(snapshot),model_calls=0,physical_attempts=0)
    try:
        backend=Backends(output/'synthesis',task)
        # Invalid physical knobs must not be reported as an RTL functional failure.
        synthesis=backend.synthesis(snapshot,1,functional_only=True,deadline=deadline)
        if synthesis['status'] in ('timeout','infrastructure_error'):
            row['evaluation_valid']=False
        row['synthesis']=synthesis['status']=='passed'
        row['synthesis_evidence']=str(Path(synthesis['evidence']).relative_to(output))
        canonical=output/'synthesis/synthesis-0001/admitted/design.sv'
        if not canonical.exists():
            if synthesis['status']=='failed':
                row['errors'].append('Candidate source admission failed')
                write_json(output/'function.json',row)
                return row
            raise RuntimeError('Candidate canonical source missing after tool execution')
        # Final checks are not part of the model's tool budget and their results are not returned.
        if task_package is None:
            benches=[ROOT/'tasks'/task/'grader/final_tb.sv',
                     ROOT/'tasks'/task/'qualification/long-progress-v1/progress_tb.sv']
        else:
            task_package=Path(task_package)
            package=json.loads((task_package/'package.json').read_text())
            if package['task']!=task or not package['passed']:
                raise RuntimeError('Final checker package does not match the task')
            benches=[task_package/'grader/final_tb.sv',task_package/'grader/progress_tb.sv']
            if any(digest(p)!=package['source_sha256'][str(p.relative_to(task_package))] for p in benches):
                raise RuntimeError('Final checker changed after task qualification')
        for index,bench in enumerate(benches):
            checked=simulate(canonical,bench,output/f'function-{index}',deadline=deadline)
            row['checks'].append(checked)
        row['function']=row['synthesis'] and all(r['passed'] for r in row['checks'])
        source,_=verified_integration(task)
        integration=output/'integration';integration.mkdir()
        for name in ('rtl','verification','workloads'):
            shutil.copytree(source/name,integration/name)
        shutil.rmtree(integration/'rtl/candidate');(integration/'rtl/candidate').mkdir()
        shutil.copy2(canonical,integration/'rtl/candidate/design.sv')
        result=qualify_integration(integration,deadline=deadline)
        row['integration']=result['passed']
        row['integration_checks']=result['rows']
        row['canonical_rtl_sha256']=digest(canonical)
    except Exception as error:
        row['evaluation_valid']=False
        row['errors'].append(type(error).__name__+': '+str(error))
    write_json(output/'function.json',row)
    return row


def latest_physical(attempts, ledger, budget):
    """The most recent budget-admitted attempt, including failures; no best-of-history."""
    snapshots={r['id']:r for r in ledger.state['snapshots']}
    admitted=[]
    for attempt in attempts:
        capture=snapshots.get(attempt.get('capture_id'))
        if capture is None or not capture['budget_admissible'] or capture['tokens']>budget:
            continue
        if attempt.get('source_sha256')!=capture['source_sha256']:
            raise ValueError('Physical source and admitted capture disagree')
        admitted.append(attempt)
    return max(admitted,key=lambda r:r['tool_id']) if admitted else None


def checkpoint(runtime, task, budget, reference, output, *, task_package=None, deadline=None, physical_identity=None):
    """Grade latest eligible bytes at a checkpoint, rather than the hidden best result."""
    runtime,output=Path(runtime),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    ledger=TokenLedger(json.loads((runtime/'usage.json').read_text()))
    selected=ledger.at(budget)
    attempted=None
    f=dict(function=False,integration=False)
    g=dict.fromkeys(GDS_GATES,False);h=dict.fromkeys(CONSTRAINT_GATES,False)
    measurements=None
    row=dict(budget=budget,measurement_valid=ledger.state['valid'],snapshot_id=None,
             physical_attempt=physical_identity,errors=[],source_tokens=None,
             source_elapsed_seconds=None,delivery_elapsed_seconds=None,
             selection='physical_attempt_diagnostic' if physical_identity else 'latest_checkpoint',
             scope=('Diagnostic only; never replaces the final checkpoint' if physical_identity else
                    'Latest budget-admissible source; latest admitted physical attempt; no hidden-result selection'))
    try:
        attempts=[]
        for path in (runtime/'eda').glob('*-physical-*/result.json'):
            attempt=json.loads(path.read_text());attempt['run']=str(path.parent);attempts.append(attempt)
        if physical_identity:
            matches=[a for a in attempts if a['identity']==physical_identity]
            if len(matches)!=1:raise ValueError('Missing/ambiguous physical attempt for diagnostics')
            attempted=latest_physical(matches,ledger,budget)
            if attempted is None or not ledger.state['valid']:
                raise ValueError('Physical diagnostic has no valid budget-admitted source')
            selected=next(s for s in ledger.state['snapshots'] if s['id']==attempted['capture_id'])
        else:
            attempted=latest_physical(attempts,ledger,budget)
        if selected is not None:
            row['snapshot_id']=selected['id'];row['source_sha256']=selected['source_sha256']
            row['source_tokens']=selected['tokens']
            snapshot=checked_path(runtime/'tools/snapshots',selected['id'])
            if source_hashes(snapshot)!=selected['source_sha256']:
                raise ValueError('Budgeted source bytes changed')
            if (snapshot/'capture.json').exists() and (runtime/'clock.json').exists():
                captured=json.loads((snapshot/'capture.json').read_text())
                clock=json.loads((runtime/'clock.json').read_text())
                row['source_elapsed_seconds']=captured['capture_monotonic']-clock['start']
            f=function(snapshot,task,output/'function',task_package=task_package,deadline=deadline)
            if not f['evaluation_valid']:
                row['measurement_valid']=False
                row['errors'].append('Functional evaluation infrastructure or time limit failed')
            if attempted is not None:
                row['physical_attempt']=attempted['identity']
                if attempted.get('status')=='timeout' or attempted.get('timed_out') or attempted.get('seconds',float('inf'))>16200:
                    row['errors'].append('Physical delivery exceeded its budget; retained late artifacts are unscored')
                elif attempted['source_sha256']==selected['source_sha256']:
                    physical=audit(attempted['run'],output/'physical',expected_source=selected['source_sha256'])
                    if physical.get('task') not in (None,task):
                        raise ValueError('Physical attempt belongs to another task')
                    g,h,measurements=physical['gds'],physical['constraints'],physical['measurements']
                    row['physical_errors']=physical['errors']
                    if (runtime/'tools/tool-ledger.json').exists() and (runtime/'clock.json').exists():
                        tools=json.loads((runtime/'tools/tool-ledger.json').read_text())['attempts']
                        delivery=next((t for t in tools if t['kind']=='physical' and t['id']==attempted['tool_id']),None)
                        if delivery and 'monotonic_end' in delivery:
                            clock=json.loads((runtime/'clock.json').read_text())
                            row['delivery_elapsed_seconds']=max(row['source_elapsed_seconds'] or 0,
                                delivery['monotonic_end']-clock['start'])
                else:
                    row['errors'].append('Latest submission has no matching last-attempt GDS')
        if not ledger.state['valid']:
            row['errors'].append('Token/source measurement invalid')
    except Exception as error:
        row['measurement_valid']=False
        row['errors'].append(type(error).__name__+': '+str(error))
        f=dict(function=False,integration=False);g['provenance']=False;h['measurement_valid']=False
    row.update(score(f,g,h,measurements,reference))
    row.update(functional_evidence=f,gds_gates=g,constraint_gates=h,measurements=measurements,
               logical_tokens=ledger.state['actual_tokens'])
    write_json(output/'score.json',row)
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--request',required=True,type=Path)
    args=parser.parse_args();request=json.loads(args.request.read_text())
    print(json.dumps(checkpoint(**request)))
