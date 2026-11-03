#!/usr/bin/env python3
"""Collect only a qualified selected physical Delivery, preserving raw evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore


def collect(project,workflow,output,include_operators=False):
    if output.exists():raise ValueError('existing evidence directory is preserved')
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        task=f'{workflow}:physical'
        if store.task_state(task).value!='satisfied':raise ValueError('physical acceptance has not satisfied its frozen contract')
        delivery=store.deliveries(task).get('report')
        if not delivery:raise ValueError('no selected physical report Delivery')
        artifact=store.get_artifact(delivery.artifact_id)
        assert artifact.payload['verdict']=='passed'
        attempts=store.list_attempts(task)
        record=artifact.document()
    commit=artifact.content.commit
    roots=['build/rtl-to-gds']+(['build/operators'] if include_operators else [])
    entries=subprocess.run(['git','ls-tree','-r','--name-only',commit,*roots],cwd=project,
                           capture_output=True,text=True,check=True).stdout.splitlines()
    selected=[]
    for name in entries:
        path=Path(name)
        if name.startswith('build/operators/'):
            if path.suffix in ('.json','.jsonl','.log','.hex','.S','.elf'):selected.append(name)
            continue
        if path.suffix in ('.json','.rpt','.log','.lyrdb','.lvsdb') or (
            path.name.startswith('6_final') and path.suffix in ('.gds','.v','.spef','.sdc','.cdl')):
            selected.append(name)
    assert any(name.endswith('6_final.gds') for name in selected)
    output.mkdir(parents=True)
    files=[]
    for name in selected:
        data=subprocess.run(['git','show',f'{commit}:{name}'],cwd=project,capture_output=True,check=True).stdout
        relative=(Path('operators')/Path(name).relative_to('build/operators') if name.startswith('build/operators/') else Path(name).relative_to('build/rtl-to-gds'))
        destination=output/relative
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
        files.append({'path':str(relative),'source_path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    record['collected_files']=files
    record['scope']='selected report, raw logs/reports and final physical views; original full Git-backed artifact retained in the local project'
    operators=sum(item['path'].startswith('operators/') for item in files)
    if operators:record['scope']+='; auxiliary kernel evidence recovered from the same attempt commit'
    if include_operators:
        record['operator_evidence_files']=operators
        if not operators:record['functional_evidence_scope']='The declared physical delivery preserves the complete simulation log; separate kernel traces are outside its declared output paths.'
    (output/'selected-delivery.json').write_text(json.dumps(record,indent=2)+'\n')
    summary=dict(artifact.payload['raw_flow_summary'])
    assert summary['detailed_routing_violations']==0 and summary['drc_violations']==0 and summary['lvs']=='matched'
    assert summary['metrics']['setup_violations']==0 and summary['metrics']['hold_violations']==0
    summary.update(passed=True,artifact_id=artifact.id,artifact_digest=artifact.digest,
                   source_commit=commit,attempt_history=[{'id':a.id,'status':a.status.value} for a in attempts])
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'artifact':artifact.id,'qualified':True,'files':len(files),'output':str(output)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--workflow',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--include-operators',action='store_true')
    args=parser.parse_args();collect(args.project.resolve(),args.workflow,args.output.resolve(),args.include_operators)
